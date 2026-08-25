"""UNIT-2 Authentication & Identity tests (docs/07)."""
from __future__ import annotations

import re
import unittest

from django.contrib.auth.middleware import AuthenticationMiddleware
from django.contrib.sessions.middleware import SessionMiddleware
from django.core import mail
from django.db import connection
from django.test import Client, RequestFactory, TestCase, override_settings
from django.urls import reverse

from apps.accounts.exceptions import (
    AccountLocked,
    AuthenticationFailed,
    InvalidToken,
)
from apps.accounts.models import (
    AuthToken,
    AuthTokenPurpose,
    UserAccount,
    UserSession,
    UserSessionStatus,
)
from apps.accounts.policy import (
    FAILED_LOGIN_THRESHOLD,
    GENERIC_AUTH_FAILURE_MESSAGE,
    GENERIC_PASSWORD_RESET_MESSAGE,
    GENERIC_VERIFICATION_RESEND_MESSAGE,
    MAX_CONCURRENT_SESSIONS,
)
from apps.accounts.services import (
    AccountService,
    AuthenticationService,
    ReauthService,
    SessionService,
    TokenService,
)
from apps.accounts.services.tokens import hash_token
from apps.common.choices import RoleCode
from apps.rbac.models import RoleAssignment


STRONG_PASSWORD = "Str0ng-Pass!Unit2"
NEW_PASSWORD = "N3w-Str0ng-Pass!"


def setUpModule():
    try:
        connection.ensure_connection()
    except Exception as exc:  # pragma: no cover
        raise unittest.SkipTest(f"PostgreSQL unavailable for UNIT-2: {exc}") from exc


def _prepare_request(path="/accounts/login/", *, user_agent="TestAgent"):
    rf = RequestFactory()
    req = rf.post(path, HTTP_USER_AGENT=user_agent)
    SessionMiddleware(lambda r: None).process_request(req)
    req.session.save()
    AuthenticationMiddleware(lambda r: None).process_request(req)
    return req


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"],
)
class AuthServiceTests(TestCase):
    def test_register_hashes_password_assigns_student_issues_token(self):
        user, raw = AccountService.register(
            email="Student@Example.COM",
            password=STRONG_PASSWORD,
            full_name="Unit Two",
        )
        self.assertEqual(user.email, "student@example.com")
        self.assertTrue(user.check_password(STRONG_PASSWORD))
        self.assertNotEqual(user.password, STRONG_PASSWORD)
        self.assertTrue(
            RoleAssignment.objects.filter(user=user, role__code=RoleCode.STUDENT).exists()
        )
        self.assertIsNotNone(raw)
        self.assertFalse(AuthToken.objects.filter(token_hash=raw).exists())
        self.assertTrue(
            AuthToken.objects.filter(
                user=user,
                purpose=AuthTokenPurpose.EMAIL_VERIFICATION,
                token_hash=hash_token(raw),
            ).exists()
        )
        self.assertEqual(len(mail.outbox), 1)

    def test_login_logout_and_session_tracking(self):
        AccountService.register(email="login@example.com", password=STRONG_PASSWORD)
        req = _prepare_request()
        AuthenticationService.login(
            request=req, email="login@example.com", password=STRONG_PASSWORD
        )
        self.assertTrue(req.user.is_authenticated)
        self.assertEqual(
            UserSession.objects.filter(
                user=req.user, status=UserSessionStatus.ACTIVE
            ).count(),
            1,
        )
        AuthenticationService.logout_current(req)
        self.assertFalse(req.user.is_authenticated)

    def test_failed_login_generic_and_lockout(self):
        AccountService.register(email="lock@example.com", password=STRONG_PASSWORD)

        for _ in range(FAILED_LOGIN_THRESHOLD - 1):
            with self.assertRaises(AuthenticationFailed) as ctx:
                AuthenticationService.login(
                    request=_prepare_request(),
                    email="lock@example.com",
                    password="Wrong-Pass!1",
                )
            self.assertEqual(str(ctx.exception), GENERIC_AUTH_FAILURE_MESSAGE)

        with self.assertRaises(AuthenticationFailed):
            AuthenticationService.login(
                request=_prepare_request(),
                email="lock@example.com",
                password="Wrong-Pass!1",
            )
        user = UserAccount.objects.get(email="lock@example.com")
        self.assertTrue(user.is_locked())

        with self.assertRaises(AccountLocked):
            AuthenticationService.login(
                request=_prepare_request(),
                email="lock@example.com",
                password=STRONG_PASSWORD,
            )

        with self.assertRaises(AuthenticationFailed) as ctx:
            AuthenticationService.login(
                request=_prepare_request(),
                email="nobody@example.com",
                password="x",
            )
        self.assertEqual(str(ctx.exception), GENERIC_AUTH_FAILURE_MESSAGE)

    def test_password_reset_token_single_use_and_enumeration_safe(self):
        AccountService.register(email="reset@example.com", password=STRONG_PASSWORD)
        mail.outbox.clear()
        msg = AuthenticationService.request_password_reset(email="reset@example.com")
        self.assertEqual(msg, GENERIC_PASSWORD_RESET_MESSAGE)
        self.assertEqual(len(mail.outbox), 1)
        raw = re.search(r"Reset token:\s*(\S+)", mail.outbox[0].body).group(1)
        self.assertNotIn(raw, msg)

        mail.outbox.clear()
        msg2 = AuthenticationService.request_password_reset(email="missing@example.com")
        self.assertEqual(msg2, GENERIC_PASSWORD_RESET_MESSAGE)
        self.assertEqual(len(mail.outbox), 0)

        AuthenticationService.reset_password(raw_token=raw, new_password=NEW_PASSWORD)
        user = UserAccount.objects.get(email="reset@example.com")
        self.assertTrue(user.check_password(NEW_PASSWORD))
        with self.assertRaises(InvalidToken):
            AuthenticationService.reset_password(raw_token=raw, new_password=STRONG_PASSWORD)

    def test_email_verification_and_resend_generic(self):
        user, raw = AccountService.register(
            email="verify@example.com", password=STRONG_PASSWORD
        )
        self.assertFalse(user.is_email_verified)
        AuthenticationService.verify_email(raw_token=raw)
        user.refresh_from_db()
        self.assertTrue(user.is_email_verified)
        with self.assertRaises(InvalidToken):
            AuthenticationService.verify_email(raw_token=raw)

        msg = AuthenticationService.resend_email_verification(email="verify@example.com")
        self.assertEqual(msg, GENERIC_VERIFICATION_RESEND_MESSAGE)
        msg2 = AuthenticationService.resend_email_verification(email="ghost@example.com")
        self.assertEqual(msg2, GENERIC_VERIFICATION_RESEND_MESSAGE)

    def test_concurrent_session_cap_terminates_oldest(self):
        user, _ = AccountService.register(
            email="sessions@example.com", password=STRONG_PASSWORD
        )
        first = None
        for i in range(MAX_CONCURRENT_SESSIONS + 1):
            req = _prepare_request(user_agent=f"Agent/{i}")
            AuthenticationService.login(
                request=req, email="sessions@example.com", password=STRONG_PASSWORD
            )
            current = SessionService.get_current(req)
            if i == 0:
                first = current

        active = UserSession.objects.filter(user=user, status=UserSessionStatus.ACTIVE)
        self.assertEqual(active.count(), MAX_CONCURRENT_SESSIONS)
        first.refresh_from_db()
        self.assertEqual(first.status, UserSessionStatus.REVOKED)

    def test_password_change_revokes_other_sessions(self):
        AccountService.register(email="chg@example.com", password=STRONG_PASSWORD)

        req_a = _prepare_request(user_agent="A")
        AuthenticationService.login(
            request=req_a, email="chg@example.com", password=STRONG_PASSWORD
        )
        req_b = _prepare_request(user_agent="B")
        AuthenticationService.login(
            request=req_b, email="chg@example.com", password=STRONG_PASSWORD
        )
        sid_b = SessionService.get_current(req_b).id

        AuthenticationService.change_password(
            request=req_a,
            current_password=STRONG_PASSWORD,
            new_password=NEW_PASSWORD,
        )
        other = UserSession.objects.get(id=sid_b)
        self.assertEqual(other.status, UserSessionStatus.REVOKED)
        user = UserAccount.objects.get(email="chg@example.com")
        self.assertTrue(user.check_password(NEW_PASSWORD))

    def test_reauth_window(self):
        AccountService.register(email="re@example.com", password=STRONG_PASSWORD)
        req = _prepare_request("/accounts/reauth/")
        AuthenticationService.login(
            request=req, email="re@example.com", password=STRONG_PASSWORD
        )
        self.assertFalse(ReauthService.is_fresh(req))
        ReauthService.confirm_password(
            user=req.user, password=STRONG_PASSWORD, request=req
        )
        self.assertTrue(ReauthService.is_fresh(req))
        ReauthService.clear(req)
        self.assertFalse(ReauthService.is_fresh(req))

    def test_token_never_stored_plaintext(self):
        user, raw = AccountService.register(
            email="hash@example.com", password=STRONG_PASSWORD
        )
        row = AuthToken.objects.get(user=user, purpose=AuthTokenPurpose.EMAIL_VERIFICATION)
        self.assertEqual(row.token_hash, hash_token(raw))
        self.assertNotEqual(row.token_hash, raw)

    def test_expired_token_rejected(self):
        user, raw = AccountService.register(
            email="exp@example.com", password=STRONG_PASSWORD
        )
        row = AuthToken.objects.get(user=user, purpose=AuthTokenPurpose.EMAIL_VERIFICATION)
        row.expires_at = row.created_at - __import__("datetime").timedelta(seconds=1)
        row.save(update_fields=["expires_at"])
        with self.assertRaises(InvalidToken):
            TokenService.consume(
                raw_token=raw, purpose=AuthTokenPurpose.EMAIL_VERIFICATION
            )


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"],
)
class AuthViewTests(TestCase):
    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)

    def _csrf_post(self, client, url, data):
        client.get(url)
        payload = dict(data)
        payload["csrfmiddlewaretoken"] = client.cookies["csrftoken"].value
        return client.post(url, payload)

    def test_register_login_logout_flow(self):
        resp = self._csrf_post(
            self.client,
            reverse("accounts:register"),
            {
                "email": "flow@example.com",
                "full_name": "Flow User",
                "password": STRONG_PASSWORD,
                "password_confirm": STRONG_PASSWORD,
                "mobile_number": "01712345678",
                "academic_session": "2024-2025",
                "blood_group": "O+",
            },
        )
        self.assertEqual(resp.status_code, 302)

        resp = self._csrf_post(
            self.client,
            reverse("accounts:login"),
            {"email": "flow@example.com", "password": STRONG_PASSWORD, "next": ""},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(UserSession.objects.filter(status=UserSessionStatus.ACTIVE).exists())

        resp = self._csrf_post(self.client, reverse("accounts:logout"), {})
        self.assertEqual(resp.status_code, 302)

    def test_csrf_required_on_login(self):
        AccountService.register(email="csrf@example.com", password=STRONG_PASSWORD)
        resp = self.client.post(
            reverse("accounts:login"),
            {"email": "csrf@example.com", "password": STRONG_PASSWORD},
        )
        self.assertEqual(resp.status_code, 403)

    def test_open_redirect_blocked(self):
        AccountService.register(email="redir@example.com", password=STRONG_PASSWORD)

        c1 = Client(enforce_csrf_checks=True)
        resp = self._csrf_post(
            c1,
            reverse("accounts:login"),
            {
                "email": "redir@example.com",
                "password": STRONG_PASSWORD,
                "next": "https://evil.example/phish",
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp["Location"], reverse("portal:dashboard"))

        c2 = Client(enforce_csrf_checks=True)
        resp = self._csrf_post(
            c2,
            reverse("accounts:login"),
            {
                "email": "redir@example.com",
                "password": STRONG_PASSWORD,
                "next": "//evil.example/phish",
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp["Location"], reverse("portal:dashboard"))

        c3 = Client(enforce_csrf_checks=True)
        resp = self._csrf_post(
            c3,
            reverse("accounts:login"),
            {
                "email": "redir@example.com",
                "password": STRONG_PASSWORD,
                "next": "/health/",
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp["Location"], "/health/")

    def test_password_reset_view_enumeration_safe_and_no_token_leak(self):
        AccountService.register(email="pr@example.com", password=STRONG_PASSWORD)
        resp = self._csrf_post(
            self.client,
            reverse("accounts:password_reset_request"),
            {"email": "pr@example.com"},
        )
        self.assertEqual(resp.status_code, 302)
        follow = self.client.get(reverse("accounts:password_reset_request"))
        content = follow.content.decode("utf-8")
        self.assertIn(GENERIC_PASSWORD_RESET_MESSAGE, content)
        raw = re.search(r"Reset token:\s*(\S+)", mail.outbox[-1].body).group(1)
        self.assertNotIn(raw, content)

        resp2 = self._csrf_post(
            self.client,
            reverse("accounts:password_reset_request"),
            {"email": "nope@example.com"},
        )
        self.assertEqual(resp2.status_code, 302)
        follow2 = self.client.get(reverse("accounts:password_reset_request"))
        self.assertIn(GENERIC_PASSWORD_RESET_MESSAGE, follow2.content.decode("utf-8"))

    def test_verify_email_view(self):
        user, raw = AccountService.register(
            email="vv@example.com", password=STRONG_PASSWORD
        )
        resp = self._csrf_post(
            self.client, reverse("accounts:verify_email"), {"token": raw}
        )
        self.assertEqual(resp.status_code, 302)
        user.refresh_from_db()
        self.assertTrue(user.is_email_verified)

    def test_login_failure_message_no_enumeration(self):
        AccountService.register(email="enum@example.com", password=STRONG_PASSWORD)
        resp = self._csrf_post(
            self.client,
            reverse("accounts:login"),
            {"email": "enum@example.com", "password": "Wrong-Pass!99", "next": ""},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, GENERIC_AUTH_FAILURE_MESSAGE)

        resp2 = self._csrf_post(
            self.client,
            reverse("accounts:login"),
            {
                "email": "missing-enum@example.com",
                "password": "Wrong-Pass!99",
                "next": "",
            },
        )
        self.assertEqual(resp2.status_code, 200)
        self.assertContains(resp2, GENERIC_AUTH_FAILURE_MESSAGE)

    def test_devices_requires_reauth(self):
        AccountService.register(email="dev@example.com", password=STRONG_PASSWORD)
        soft = Client()
        soft.post(
            reverse("accounts:login"),
            {"email": "dev@example.com", "password": STRONG_PASSWORD, "next": ""},
        )
        resp = soft.get(reverse("accounts:devices"))
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/accounts/reauth/", resp["Location"])
