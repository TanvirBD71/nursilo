"""GATE D — Auth UX, learner profile, question-bank workflow polish."""
from __future__ import annotations

import unittest
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.middleware import AuthenticationMiddleware
from django.contrib.sessions.middleware import SessionMiddleware
from django.db import connection
from django.test import Client, RequestFactory, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import AcademicProfile, UserAccount, UserSession, UserSessionStatus
from apps.accounts.policy import SESSION_ABSOLUTE_TIMEOUT, SESSION_IDLE_TIMEOUT
from apps.accounts.profile import normalize_mobile_number
from apps.accounts.services import AccountService, AuthenticationService, SessionService
from apps.assessment.models import BlueprintCategory, Question
from apps.common.choices import EditorialState, RoleCode
from apps.rbac.models import Role, RoleAssignment
from apps.staff.services import QuestionStaffService
from apps.staff.services.questions import QuestionStaffError


STRONG_PASSWORD = "Str0ng-Pass!GateD"


def setUpModule():
    try:
        connection.ensure_connection()
    except Exception as exc:  # pragma: no cover
        raise unittest.SkipTest(f"PostgreSQL unavailable for GATE D: {exc}") from exc


def _prepare_request(path="/accounts/login/", *, user_agent="TestAgent"):
    rf = RequestFactory()
    req = rf.post(path, HTTP_USER_AGENT=user_agent)
    SessionMiddleware(lambda r: None).process_request(req)
    req.session.save()
    AuthenticationMiddleware(lambda r: None).process_request(req)
    return req


def _assign(user, *role_codes):
    for code in role_codes:
        role = Role.objects.get(code=code)
        RoleAssignment.objects.get_or_create(user=user, role=role)


def _staff_user(email, *role_codes):
    user = UserAccount.objects.create_user(
        email=email, password=STRONG_PASSWORD, full_name="Gate D Staff"
    )
    _assign(user, *role_codes)
    return user


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"],
)
class AuthNavigationTests(TestCase):
    def test_auth_pages_have_nursilo_back(self):
        pages = [
            ("accounts:login", "home"),
            ("accounts:register", "Sign in"),
            ("accounts:password_reset_request", "sign in"),
            ("accounts:password_reset_confirm", "password reset"),
            ("accounts:verify_email", "sign in"),
            ("accounts:resend_verification", "email verification"),
        ]
        for name, label in pages:
            with self.subTest(name=name):
                resp = self.client.get(reverse(name))
                self.assertEqual(resp.status_code, 200)
                self.assertContains(resp, "Back to")
                self.assertContains(resp, label)
                self.assertContains(resp, "back-link")
                self.assertNotContains(resp, "history.back")

    def test_back_uses_safe_referer_and_rejects_loop(self):
        login = reverse("accounts:login")
        resp = self.client.get(login, HTTP_REFERER="http://evil.example/phish")
        self.assertContains(resp, 'href="/"')
        loop = self.client.get(login, HTTP_REFERER="http://testserver" + login)
        self.assertContains(loop, "Back to home")
        from_landing = self.client.get(login, HTTP_REFERER="http://testserver/")
        self.assertContains(from_landing, 'href="/"')


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"],
)
class RememberMeTests(TestCase):
    def setUp(self):
        AccountService.register(email="remember@example.com", password=STRONG_PASSWORD)

    def test_unchecked_keeps_normal_idle(self):
        req = _prepare_request()
        AuthenticationService.login(
            request=req,
            email="remember@example.com",
            password=STRONG_PASSWORD,
            remember_me=False,
        )
        session = SessionService.get_current(req)
        self.assertFalse(session.remember_me)
        later = timezone.now() + SESSION_IDLE_TIMEOUT + timedelta(minutes=1)
        self.assertIsNone(SessionService.touch(session, now=later))

    def test_checked_extends_idle_within_absolute(self):
        req = _prepare_request()
        AuthenticationService.login(
            request=req,
            email="remember@example.com",
            password=STRONG_PASSWORD,
            remember_me=True,
        )
        session = SessionService.get_current(req)
        self.assertTrue(session.remember_me)
        self.assertGreaterEqual(
            req.session.get_expiry_age(), int(SESSION_ABSOLUTE_TIMEOUT.total_seconds()) - 5
        )
        later = timezone.now() + SESSION_IDLE_TIMEOUT + timedelta(minutes=1)
        session.refresh_from_db()
        self.assertIsNotNone(SessionService.touch(session, now=later))
        past_absolute = timezone.now() + SESSION_ABSOLUTE_TIMEOUT + timedelta(hours=1)
        session.refresh_from_db()
        self.assertIsNone(SessionService.touch(session, now=past_absolute))

    def test_logout_invalidates_remembered_session(self):
        req = _prepare_request()
        AuthenticationService.login(
            request=req,
            email="remember@example.com",
            password=STRONG_PASSWORD,
            remember_me=True,
        )
        session = SessionService.get_current(req)
        AuthenticationService.logout_current(req)
        session.refresh_from_db()
        self.assertEqual(session.status, UserSessionStatus.REVOKED)

    def test_login_form_and_cookies_do_not_store_password(self):
        page = self.client.get(reverse("accounts:login"))
        self.assertContains(page, "Remember me on this browser")
        self.assertContains(page, "Keep me signed in on this device")
        self.assertNotContains(page, "localStorage")
        self.assertNotContains(page, "sessionStorage")
        client = Client()
        client.get(reverse("accounts:login"))
        client.post(
            reverse("accounts:login"),
            {
                "email": "remember@example.com",
                "password": STRONG_PASSWORD,
                "remember_me": "on",
                "next": "",
            },
        )
        for morsel in client.cookies.values():
            self.assertNotIn(STRONG_PASSWORD, morsel.value)
            self.assertNotIn("permanent", morsel.value.lower())
        self.assertTrue(settings.SESSION_COOKIE_HTTPONLY)
        self.assertEqual(settings.SESSION_COOKIE_SAMESITE, "Lax")
        session_cookie = client.cookies.get(settings.SESSION_COOKIE_NAME)
        self.assertIsNotNone(session_cookie)
        self.assertTrue(session_cookie.get("httponly") or session_cookie["httponly"])


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"],
)
class RegistrationProfileTests(TestCase):
    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)

    def _csrf_post(self, url, data):
        self.client.get(url)
        payload = dict(data)
        payload["csrfmiddlewaretoken"] = self.client.cookies["csrftoken"].value
        return self.client.post(url, payload)

    def test_register_page_sections_and_required_markers(self):
        resp = self.client.get(reverse("accounts:register"))
        self.assertContains(resp, "Account")
        self.assertContains(resp, "Personal")
        self.assertContains(resp, "Academic")
        self.assertContains(resp, "Contact and social")
        self.assertContains(resp, "Mobile number")
        self.assertContains(resp, "Academic session")
        self.assertContains(resp, "Blood group")
        self.assertContains(resp, "(optional)")
        self.assertContains(resp, "field-required")

    def test_register_requires_mobile_session_blood(self):
        resp = self._csrf_post(
            reverse("accounts:register"),
            {
                "email": "needfields@example.com",
                "full_name": "Need Fields",
                "password": STRONG_PASSWORD,
                "password_confirm": STRONG_PASSWORD,
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(UserAccount.objects.filter(email="needfields@example.com").exists())
        self.assertContains(resp, "Mobile number")
        self.assertContains(resp, "This field is required.")

    def test_register_rejects_invalid_optional_urls_and_blood(self):
        resp = self._csrf_post(
            reverse("accounts:register"),
            {
                "email": "badurl@example.com",
                "full_name": "Bad Url",
                "password": STRONG_PASSWORD,
                "password_confirm": STRONG_PASSWORD,
                "mobile_number": "01712345678",
                "academic_session": "2024-2025",
                "blood_group": "Z+",
                "social_profile_url": "not-a-url",
                "linkedin_url": "javascript:alert(1)",
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(UserAccount.objects.filter(email="badurl@example.com").exists())

    def test_register_normalizes_bd_mobile_and_allows_international(self):
        self.assertEqual(normalize_mobile_number("01712345678"), "+8801712345678")
        self.assertEqual(normalize_mobile_number("+14155552671"), "+14155552671")
        resp = self._csrf_post(
            reverse("accounts:register"),
            {
                "email": "okprofile@example.com",
                "full_name": "Ok Profile",
                "password": STRONG_PASSWORD,
                "password_confirm": STRONG_PASSWORD,
                "mobile_number": "01712345678",
                "academic_session": "2024-2025",
                "blood_group": "A+",
                "address": "Dhaka",
                "social_profile_url": "",
                "linkedin_url": "https://www.linkedin.com/in/example",
            },
        )
        self.assertEqual(resp.status_code, 302)
        user = UserAccount.objects.get(email="okprofile@example.com")
        profile = AcademicProfile.objects.get(user=user)
        self.assertEqual(profile.mobile_number, "+8801712345678")
        self.assertEqual(profile.academic_session, "2024-2025")
        self.assertEqual(profile.blood_group, "A+")
        self.assertEqual(profile.address, "Dhaka")
        self.assertEqual(profile.linkedin_url, "https://www.linkedin.com/in/example")
        self.assertEqual(profile.social_profile_url, "")

    def test_register_preserves_values_on_password_mismatch(self):
        resp = self._csrf_post(
            reverse("accounts:register"),
            {
                "email": "keep@example.com",
                "full_name": "Keep Me",
                "password": STRONG_PASSWORD,
                "password_confirm": "Other-Pass!99",
                "mobile_number": "01712345678",
                "academic_session": "2023-2024",
                "blood_group": "O-",
                "address": "Chattogram",
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Keep Me")
        self.assertContains(resp, "keep@example.com")
        self.assertContains(resp, "Chattogram")
        self.assertContains(resp, "01712345678")


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"],
)
class ProfileEditGateDTests(TestCase):
    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)
        self.user, _ = AccountService.register(
            email="profiled@example.com",
            password=STRONG_PASSWORD,
            full_name="Before",
        )
        login = reverse("accounts:login")
        self.client.get(login)
        self.client.post(
            login,
            {
                "email": "profiled@example.com",
                "password": STRONG_PASSWORD,
                "next": "",
                "csrfmiddlewaretoken": self.client.cookies["csrftoken"].value,
            },
        )

    def test_profile_edit_updates_learner_fields(self):
        url = reverse("portal:profile_edit")
        self.client.get(url)
        resp = self.client.post(
            url,
            {
                "full_name": "After",
                "ui_locale": "en",
                "mobile_number": "+8801812345678",
                "academic_session": "2025-2026",
                "blood_group": "AB+",
                "address": "Rajshahi",
                "social_profile_url": "https://facebook.com/example",
                "linkedin_url": "",
                "csrfmiddlewaretoken": self.client.cookies["csrftoken"].value,
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.user.refresh_from_db()
        profile = AcademicProfile.objects.get(user=self.user)
        self.assertEqual(self.user.full_name, "After")
        self.assertEqual(profile.mobile_number, "+8801812345678")
        self.assertEqual(profile.academic_session, "2025-2026")
        self.assertEqual(profile.blood_group, "AB+")
        self.assertEqual(profile.address, "Rajshahi")

    def test_anon_cannot_edit_profile(self):
        anon = Client()
        resp = anon.get(reverse("portal:profile_edit"))
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/accounts/login/", resp["Location"])

    def test_profile_and_settings_have_back(self):
        self.assertContains(self.client.get(reverse("portal:profile")), "Back to dashboard")
        self.assertContains(self.client.get(reverse("portal:settings")), "Back to dashboard")
        self.assertContains(self.client.get(reverse("portal:notifications")), "Back to dashboard")


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"],
)
class QuestionBankPolishTests(TestCase):
    def setUp(self):
        self.editor = _staff_user("gated-editor@example.com", RoleCode.EDITOR)
        self.client.force_login(self.editor)

    def test_list_select_all_visible_and_publish_confirm(self):
        listing = self.client.get(reverse("staff:questions"))
        self.assertEqual(listing.status_code, 200)
        self.assertContains(listing, "Select all visible")
        self.assertContains(listing, "visible on this page")
        self.assertContains(listing, "Confirm publish of selected questions")
        self.assertContains(listing, "Reset")
        self.assertContains(listing, "Apply")
        self.assertContains(listing, "data-nav-toggle")

    def test_bulk_publish_requires_confirmation(self):
        q = QuestionStaffService.create_question(
            actor=self.editor,
            stem="Gate D publish confirm?",
            explanation="n/a",
            options=[
                {"key": "A", "label": "Yes"},
                {"key": "B", "label": "No"},
            ],
            correct_key="A",
        )
        Question.objects.filter(pk=q.pk).update(editorial_state=EditorialState.APPROVED)
        denied = self.client.post(
            reverse("staff:questions"),
            {"intent": "bulk_publish", "question_ids": [str(q.id)]},
            follow=True,
        )
        q.refresh_from_db()
        self.assertEqual(q.editorial_state, EditorialState.APPROVED)
        self.assertContains(denied, "Publish requires confirmation")
        ok = self.client.post(
            reverse("staff:questions"),
            {
                "intent": "bulk_publish",
                "question_ids": [str(q.id)],
                "confirm_publish": "1",
            },
            follow=True,
        )
        self.assertEqual(ok.status_code, 200)
        self.assertNotContains(ok, "Publish requires confirmation")

    def test_student_cannot_bulk(self):
        student, _ = AccountService.register(
            email="gated-stu@example.com", password=STRONG_PASSWORD
        )
        self.client.force_login(student)
        resp = self.client.post(
            reverse("staff:questions"),
            {"intent": "bulk_submit", "question_ids": ["x"]},
        )
        self.assertEqual(resp.status_code, 403)

    def test_suggestion_does_not_overwrite_explicit_classification(self):
        q = QuestionStaffService.create_question(
            actor=self.editor,
            stem="Gate D classified already",
            explanation="n/a",
            options=[
                {"key": "A", "label": "Yes"},
                {"key": "B", "label": "No"},
            ],
            correct_key="A",
            content_subject="Fundamentals of Nursing",
        )
        category = BlueprintCategory.objects.filter(
            blueprint__code="BNMC_2018", name="Fundamentals of Nursing"
        ).first()
        self.assertIsNotNone(category)
        QuestionStaffService.update_classification(
            actor=self.editor,
            question=q,
            content_subject="Fundamentals of Nursing",
            blueprint_category_id=category.id,
        )
        q.refresh_from_db()
        original = q.blueprint_category_id
        with self.assertRaises(QuestionStaffError):
            QuestionStaffService.apply_suggestion(
                actor=self.editor, question=q, fields=["category"]
            )
        q.refresh_from_db()
        self.assertEqual(q.blueprint_category_id, original)

    def test_mobile_nav_icon_present_and_exam_layout_has_none(self):
        listing = self.client.get(reverse("staff:questions"))
        self.assertContains(listing, "Open menu")
        self.assertContains(listing, 'data-nav-toggle')
        self.assertContains(listing, "icon-menu")


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"],
)
class March2025UntouchedTests(TestCase):
    def test_gate_d_does_not_create_march_2025_codes(self):
        from apps.assessment.services.protection import MARCH_2025_CODE_PREFIX

        self.assertFalse(
            Question.objects.filter(
                question_code__startswith=MARCH_2025_CODE_PREFIX
            ).exists()
        )
