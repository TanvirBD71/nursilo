"""Development demo seed/cleanup tests — does not weaken UNIT-0–10 suite."""
from __future__ import annotations

import unittest
from unittest import mock

from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.test import TestCase, override_settings

from apps.assessment.models import ExamDefinition, Question
from apps.billing.models import Subscription
from apps.common.choices import EditorialState, RoleCode, SubscriptionState
from apps.library.models import Book
from apps.platform.demo_seed import (
    DEMO_COURSE_TITLE,
    DEMO_EXAM_CODE,
    DEMO_PREMIUM_EMAIL,
    DEMO_STAFF_EMAIL,
    DEMO_STUDENT_EMAIL,
    DemoSeedError,
    assert_safe_demo_environment,
    cleanup_demo_data,
    seed_demo_data,
)
from apps.rbac.services import AccessControlService


def setUpModule():
    try:
        connection.ensure_connection()
    except Exception as exc:  # pragma: no cover
        raise unittest.SkipTest(f"PostgreSQL unavailable for demo seed: {exc}") from exc


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"],
    DEBUG=True,
)
class DemoSeedGuardTests(TestCase):
    def test_refuses_when_debug_false(self):
        with override_settings(DEBUG=False):
            with self.assertRaises(DemoSeedError):
                assert_safe_demo_environment()

    def test_refuses_wrong_database_name(self):
        from django.conf import settings as dj_settings

        databases = {
            "default": {
                **dj_settings.DATABASES["default"],
                "NAME": "production_like_db",
            }
        }
        with override_settings(DATABASES=databases):
            with self.assertRaises(DemoSeedError):
                assert_safe_demo_environment()


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"],
    DEBUG=True,
)
class DemoSeedCommandTests(TestCase):
    def setUp(self):
        from django.conf import settings as dj_settings

        self.assertIn(
            dj_settings.DATABASES["default"]["NAME"],
            {"nursilo_dev", "test_nursilo_dev"},
        )

    def test_seed_is_idempotent_and_creates_demo_pack(self):
        report1 = seed_demo_data(password="Str0ng-Pass!Demo1")
        self.assertTrue(report1.created)

        from apps.learning.models import CourseTranslation

        self.assertTrue(
            CourseTranslation.objects.filter(title=DEMO_COURSE_TITLE).exists()
        )
        self.assertEqual(
            Question.objects.filter(tags__code="nursilo_demo")
            .distinct()
            .count(),
            12,
        )
        exam = ExamDefinition.objects.get(code=DEMO_EXAM_CODE)
        self.assertEqual(exam.editorial_state, EditorialState.PUBLISHED)
        self.assertGreaterEqual(exam.items.count(), 8)
        self.assertEqual(
            Book.objects.filter(
                translations__title__startswith="Nursilo Demo",
                editorial_state=EditorialState.PUBLISHED,
            )
            .distinct()
            .count(),
            2,
        )

        from apps.accounts.models import UserAccount

        free = UserAccount.objects.get(email=DEMO_STUDENT_EMAIL)
        premium = UserAccount.objects.get(email=DEMO_PREMIUM_EMAIL)
        staff = UserAccount.objects.get(email=DEMO_STAFF_EMAIL)
        self.assertTrue(free.is_email_verified)
        self.assertTrue(AccessControlService.has_role(staff, RoleCode.ADMIN))
        self.assertEqual(
            Subscription.objects.get(user=free).state, SubscriptionState.FREE
        )
        self.assertEqual(
            Subscription.objects.get(user=premium).state,
            SubscriptionState.PREMIUM_ACTIVE,
        )

        report2 = seed_demo_data(password="Str0ng-Pass!Demo1")
        self.assertEqual(
            Question.objects.filter(tags__code="nursilo_demo")
            .distinct()
            .count(),
            12,
        )
        # Second run should mostly skip rather than duplicate content.
        self.assertTrue(report2.skipped or report2.updated)

    def test_cleanup_removes_only_demo_records(self):
        seed_demo_data(password="Str0ng-Pass!Demo1")
        cleanup_demo_data()
        from apps.accounts.models import UserAccount
        from apps.learning.models import CourseTranslation

        self.assertFalse(UserAccount.objects.filter(email=DEMO_STUDENT_EMAIL).exists())
        self.assertFalse(CourseTranslation.objects.filter(title=DEMO_COURSE_TITLE).exists())
        self.assertFalse(ExamDefinition.objects.filter(code=DEMO_EXAM_CODE).exists())
        self.assertFalse(
            Question.objects.filter(tags__code="nursilo_demo").exists()
        )

    def test_management_command_wires_through(self):
        call_command("seed_demo_data")
        call_command("cleanup_demo_data")

    def test_management_command_surfaces_guard_failure(self):
        with mock.patch(
            "apps.platform.management.commands.seed_demo_data.seed_demo_data",
            side_effect=DemoSeedError("refused"),
        ):
            with self.assertRaises(CommandError):
                call_command("seed_demo_data")
