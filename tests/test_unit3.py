"""UNIT-3 Student Portal Foundation tests (docs/11–24 presentation boundaries)."""
from __future__ import annotations

import unittest

from django.db import connection
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from apps.accounts.models import AcademicProfile, UserAccount
from apps.accounts.services import AccountService
from apps.billing.models import Subscription
from apps.common.choices import RoleCode, SubscriptionState
from apps.notifications.models import Notification
from apps.portal.access import user_may_access_student_portal
from apps.portal.services import (
    DashboardPresentationService,
    NavigationService,
    SubscriptionPresentationService,
)
from apps.rbac.models import Role, RoleAssignment
from apps.rbac.services import AccessControlService


STRONG_PASSWORD = "Str0ng-Pass!Unit3"


def setUpModule():
    try:
        connection.ensure_connection()
    except Exception as exc:  # pragma: no cover
        raise unittest.SkipTest(f"PostgreSQL unavailable for UNIT-3: {exc}") from exc


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"],
)
class StudentPortalAccessTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user, _ = AccountService.register(
            email="student3@example.com",
            password=STRONG_PASSWORD,
            full_name="Unit Three",
        )

    def _login(self, email="student3@example.com"):
        return self.client.post(
            reverse("accounts:login"),
            {"email": email, "password": STRONG_PASSWORD, "next": ""},
        )

    def test_anonymous_cannot_access_dashboard(self):
        resp = self.client.get(reverse("portal:dashboard"))
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/accounts/login/", resp["Location"])

    def test_authenticated_student_can_access_dashboard(self):
        self._login()
        resp = self.client.get(reverse("portal:dashboard"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Dashboard")
        self.assertContains(resp, "Nursilo")

    def test_authenticated_student_can_access_profile(self):
        self._login()
        resp = self.client.get(reverse("portal:profile"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "student3@example.com")
        self.assertContains(resp, "Profile")

    def test_staff_without_student_role_denied(self):
        admin = UserAccount.objects.create_user(
            email="admin-only@example.com",
            password=STRONG_PASSWORD,
            is_staff=True,
        )
        role = Role.objects.get(code=RoleCode.ADMIN)
        RoleAssignment.objects.create(user=admin, role=role)
        self.assertFalse(user_may_access_student_portal(admin))
        self.client.post(
            reverse("accounts:login"),
            {
                "email": "admin-only@example.com",
                "password": STRONG_PASSWORD,
                "next": "",
            },
        )
        resp = self.client.get(reverse("portal:dashboard"))
        self.assertEqual(resp.status_code, 403)
        body = resp.content.decode("utf-8").lower()
        self.assertNotIn("traceback", body)
        self.assertNotIn("secret", body)


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"],
)
class DashboardFoundationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user, _ = AccountService.register(
            email="dash@example.com",
            password=STRONG_PASSWORD,
            full_name="Dash User",
        )
        self.client.post(
            reverse("accounts:login"),
            {"email": "dash@example.com", "password": STRONG_PASSWORD, "next": ""},
        )

    def test_dashboard_renders_empty_and_unavailable_honestly(self):
        resp = self.client.get(reverse("portal:dashboard"))
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode("utf-8")
        self.assertIn("Continue Learning", content)
        # Learning module is live: continue-learning is available with honest empty.
        self.assertIn("no lesson in progress", content.lower())
        self.assertIn("browse courses", content.lower())
        # Domains still deferred remain honest.
        self.assertIn("coming later", content.lower())
        # Must not fabricate learner metrics
        forbidden_fake = [
            "streak: 7",
            "score 100%",
            "fabricated",
            "mock progress",
        ]
        for token in forbidden_fake:
            self.assertNotIn(token, content.lower())

    def test_dashboard_service_uses_real_notification_and_subscription(self):
        Notification.objects.create(
            user=self.user,
            kind="system",
            title="Welcome notice",
            body="Hello from Nursilo",
            is_read=False,
        )
        Subscription.objects.create(
            user=self.user,
            state=SubscriptionState.FREE,
        )
        data = DashboardPresentationService.build(self.user)
        notif_section = next(s for s in data["sections"] if s.key == "notifications")
        sub_section = next(s for s in data["sections"] if s.key == "subscription")
        self.assertTrue(notif_section.available)
        self.assertFalse(notif_section.empty)
        self.assertEqual(notif_section.data["unread_count"], 1)
        self.assertTrue(sub_section.available)
        self.assertEqual(sub_section.data["state"], SubscriptionState.FREE)
        self.assertFalse(data["has_any_learning_data"])

        resp = self.client.get(reverse("portal:dashboard"))
        self.assertContains(resp, "Welcome notice")


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"],
)
class ProfileFoundationTests(TestCase):
    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)
        self.user, _ = AccountService.register(
            email="profile3@example.com",
            password=STRONG_PASSWORD,
            full_name="Before Name",
        )
        self._login()

    def _login(self):
        login_url = reverse("accounts:login")
        self.client.get(login_url)
        self.client.post(
            login_url,
            {
                "email": "profile3@example.com",
                "password": STRONG_PASSWORD,
                "next": "",
                "csrfmiddlewaretoken": self.client.cookies["csrftoken"].value,
            },
        )

    def _csrf_post(self, url, data):
        self.client.get(url)
        payload = dict(data)
        payload["csrfmiddlewaretoken"] = self.client.cookies["csrftoken"].value
        return self.client.post(url, payload)

    def test_profile_display_and_edit(self):
        resp = self.client.get(reverse("portal:profile"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Before Name")
        self.assertContains(resp, "<h1")

        resp = self._csrf_post(
            reverse("portal:profile_edit"),
            {
                "full_name": "After Name",
                "ui_locale": "en",
                "mobile_number": "01712345678",
                "academic_session": "2024-2025",
                "blood_group": "B+",
                "address": "",
                "social_profile_url": "",
                "linkedin_url": "",
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.user.refresh_from_db()
        self.assertEqual(self.user.full_name, "After Name")
        self.assertEqual(self.user.ui_locale, "en")

        edit_page = self.client.get(reverse("portal:profile_edit"))
        self.assertContains(edit_page, '<label for="id_full_name"')
        self.assertContains(edit_page, "<h1")

    def test_academic_profile_edit(self):
        resp = self._csrf_post(
            reverse("portal:academic_profile_edit"),
            {
                "academic_program": "BSc Nursing",
                "institution": "Test College",
                "current_semester_year": "3rd year",
                "expected_graduation_year": "2027",
                "current_study_goal": "Licensing exam",
            },
        )
        self.assertEqual(resp.status_code, 302)
        academic = AcademicProfile.objects.get(user=self.user)
        self.assertEqual(academic.academic_program, "BSc Nursing")
        self.assertEqual(academic.institution, "Test College")
        self.assertEqual(academic.expected_graduation_year, 2027)

    def test_profile_requires_authentication(self):
        anon = Client()
        resp = anon.get(reverse("portal:profile"))
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/accounts/login/", resp["Location"])


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"],
)
class NavigationAndNotificationsTests(TestCase):
    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)
        self.user, _ = AccountService.register(
            email="nav@example.com",
            password=STRONG_PASSWORD,
        )
        login_url = reverse("accounts:login")
        self.client.get(login_url)
        self.client.post(
            login_url,
            {
                "email": "nav@example.com",
                "password": STRONG_PASSWORD,
                "next": "",
                "csrfmiddlewaretoken": self.client.cookies["csrftoken"].value,
            },
        )

    def test_navigation_honesty(self):
        items = NavigationService.items(active="dashboard")
        by_key = {i.key: i for i in items}
        self.assertTrue(by_key["dashboard"].available)
        self.assertTrue(by_key["learn"].available)
        self.assertTrue(by_key["profile"].available)
        self.assertTrue(by_key["notifications"].available)
        self.assertTrue(by_key["subscription"].available)
        self.assertTrue(by_key["security"].available)
        self.assertTrue(by_key["settings"].available)
        self.assertEqual(by_key["learn"].href, reverse("learning:catalog"))
        self.assertTrue(by_key["practice"].available)
        self.assertEqual(by_key["practice"].href, reverse("assessment:entry"))
        self.assertTrue(by_key["exams"].available)
        self.assertEqual(by_key["exams"].href, reverse("exams:catalog"))
        self.assertTrue(by_key["library"].available)
        self.assertEqual(by_key["library"].href, reverse("library:catalog"))
        self.assertFalse(by_key["search"].available)
        self.assertIn("/unavailable/", by_key["search"].href)

        resp = self.client.get(
            reverse("portal:unavailable", kwargs={"feature": "search"})
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "not available yet")
        self.assertNotContains(resp, "Start exam")

    def test_notifications_list_read_empty(self):
        empty = self.client.get(reverse("portal:notifications"))
        self.assertEqual(empty.status_code, 200)
        self.assertContains(empty, "No notifications")

        note = Notification.objects.create(
            user=self.user,
            kind="system",
            title="Read me",
            body="Body text",
            is_read=False,
        )
        listed = self.client.get(reverse("portal:notifications"))
        self.assertContains(listed, "Read me")
        self.assertContains(listed, "Unread")

        self.client.get(reverse("portal:notifications"))
        token = self.client.cookies["csrftoken"].value
        resp = self.client.post(
            reverse("portal:notification_mark_read", kwargs={"notification_id": note.id}),
            {"csrfmiddlewaretoken": token},
        )
        self.assertEqual(resp.status_code, 302)
        note.refresh_from_db()
        self.assertTrue(note.is_read)

    def test_subscription_presentation_default_free_and_row(self):
        presentation = SubscriptionPresentationService.for_user(self.user)
        self.assertEqual(presentation.state, SubscriptionState.FREE)
        self.assertEqual(presentation.source, "default_free")
        self.assertFalse(presentation.is_premium)

        Subscription.objects.create(
            user=self.user, state=SubscriptionState.PREMIUM_ACTIVE
        )
        presentation = SubscriptionPresentationService.for_user(self.user)
        self.assertTrue(presentation.is_premium)
        self.assertEqual(presentation.source, "subscription_row")

        resp = self.client.get(reverse("portal:subscription"))
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, reverse("billing:current"))
        current = self.client.get(reverse("billing:current"))
        self.assertEqual(current.status_code, 200)
        self.assertContains(current, "Premium")


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"],
)
class PortalSecurityAndErrorTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user, _ = AccountService.register(
            email="sec3@example.com",
            password=STRONG_PASSWORD,
        )
        self.client.post(
            reverse("accounts:login"),
            {"email": "sec3@example.com", "password": STRONG_PASSWORD, "next": ""},
        )

    def test_cannot_mark_another_users_notification(self):
        other, _ = AccountService.register(
            email="other3@example.com", password=STRONG_PASSWORD
        )
        note = Notification.objects.create(
            user=other,
            kind="system",
            title="Private",
            body="Secret-ish body for other user",
            is_read=False,
        )
        resp = self.client.post(
            reverse("portal:notification_mark_read", kwargs={"notification_id": note.id})
        )
        self.assertEqual(resp.status_code, 404)
        note.refresh_from_db()
        self.assertFalse(note.is_read)

    def test_error_pages_do_not_leak_internals(self):
        resp = self.client.get("/this-route-does-not-exist-unit3/")
        self.assertEqual(resp.status_code, 404)
        body = resp.content.decode("utf-8").lower()
        for token in ("traceback", "secret_key", "db_password", "exception type"):
            self.assertNotIn(token, body)

    def test_home_redirects_authenticated_to_dashboard(self):
        resp = self.client.get(reverse("home"))
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp["Location"], reverse("portal:dashboard"))

    def test_home_serves_public_landing_for_anonymous(self):
        anon = Client()
        resp = anon.get(reverse("home"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Nursilo")
        self.assertContains(resp, "Get Started")
        self.assertContains(resp, 'id="main-content"')
        self.assertContains(resp, "Skip to main content")
        body = resp.content.decode("utf-8")
        self.assertIn("/accounts/login/", body)
        self.assertIn("/accounts/register/", body)
        self.assertNotIn("traceback", body.lower())

    def test_a11y_basics_on_dashboard_and_forms(self):
        resp = self.client.get(reverse("portal:dashboard"))
        self.assertContains(resp, 'id="main-content"')
        self.assertContains(resp, "Skip to main content")
        self.assertContains(resp, "<nav")
        self.assertContains(resp, "<h1")

        form_page = self.client.get(reverse("portal:profile_edit"))
        self.assertContains(form_page, '<label for="id_full_name"')
        self.assertContains(form_page, "<title>")

    def test_login_shows_session_expired_reason(self):
        anon = Client()
        resp = anon.get(reverse("accounts:login") + "?reason=session_expired")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "session expired")

    def test_student_permission_foundation_unchanged(self):
        self.assertTrue(
            AccessControlService.has_permission(self.user, "account.view_own")
        )
        self.assertTrue(
            AccessControlService.has_permission(self.user, "account.edit_own_profile")
        )
