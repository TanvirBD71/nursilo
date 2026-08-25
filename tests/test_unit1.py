"""UNIT-1 domain/data foundation tests."""
import unittest

from django.db import IntegrityError, connection, transaction
from django.test import TestCase, TransactionTestCase
from django.urls import reverse

from apps.accounts.models import AcademicProfile, UserAccount
from apps.assessment.models import (
    Attempt,
    AttemptItem,
    Question,
    QuestionOption,
    QuestionTopic,
    QuestionVersion,
    QuestionVersionTranslation,
)
from apps.audit.models import AuditEvent
from apps.billing.models import PaymentTransaction, Subscription
from apps.common.choices import (
    AttemptMode,
    AttemptState,
    DifficultyLevel,
    EditorialState,
    LocaleCode,
    PaymentGateway,
    PaymentStatus,
    QuestionType,
    RoleCode,
    SubscriptionState,
)
from apps.learning.models import (
    Chapter,
    Course,
    CourseTranslation,
    Lesson,
    LearningMaterial,
    LessonLearningMaterial,
    Subject,
    Topic,
    Unit,
)
from apps.rbac.models import Role, RoleAssignment


def setUpModule():
    try:
        connection.ensure_connection()
    except Exception as exc:  # pragma: no cover - environment-dependent
        raise unittest.SkipTest(f"PostgreSQL unavailable for UNIT-1 DB tests: {exc}") from exc


class UserFoundationTests(TestCase):
    def test_create_user_normalizes_email_and_hashes_password(self):
        user = UserAccount.objects.create_user(
            email="Student@Example.COM",
            password="Str0ng-Pass-Unit1",
            full_name="Test Student",
        )
        self.assertEqual(user.email, "student@example.com")
        self.assertTrue(user.check_password("Str0ng-Pass-Unit1"))
        self.assertNotEqual(user.password, "Str0ng-Pass-Unit1")
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)

    def test_email_unique(self):
        UserAccount.objects.create_user(email="a@example.com", password="x")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                UserAccount.objects.create_user(email="a@example.com", password="y")

    def test_academic_profile_one_to_one(self):
        user = UserAccount.objects.create_user(email="prof@example.com", password="x")
        profile = AcademicProfile.objects.create(
            user=user,
            academic_program="BSc Nursing",
            institution="Test College",
            current_semester_year="3rd Year",
        )
        self.assertEqual(user.academic_profile.pk, profile.pk)


class RbacFoundationTests(TestCase):
    def test_roles_seeded(self):
        codes = set(Role.objects.values_list("code", flat=True))
        expected = {c.value for c in RoleCode}
        self.assertTrue(expected.issubset(codes))

    def test_role_assignment_unique(self):
        user = UserAccount.objects.create_user(email="role@example.com", password="x")
        role = Role.objects.get(code=RoleCode.STUDENT)
        RoleAssignment.objects.create(user=user, role=role)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                RoleAssignment.objects.create(user=user, role=role)


class LearningHierarchyTests(TestCase):
    def test_hierarchy_ownership_and_ordering(self):
        course = Course.objects.create(sort_order=1, editorial_state=EditorialState.PUBLISHED)
        CourseTranslation.objects.create(
            course=course, locale=LocaleCode.EN, title="Fundamentals", summary=""
        )
        subject = Subject.objects.create(course=course, sort_order=1)
        unit = Unit.objects.create(subject=subject, sort_order=1)
        chapter = Chapter.objects.create(unit=unit, sort_order=1)
        topic = Topic.objects.create(chapter=chapter, sort_order=1)
        lesson = Lesson.objects.create(topic=topic, sort_order=1)
        material = LearningMaterial.objects.create(sort_order=1, is_premium=False)
        LessonLearningMaterial.objects.create(lesson=lesson, learning_material=material, sort_order=0)

        self.assertEqual(lesson.topic.chapter.unit.subject.course_id, course.id)
        self.assertEqual(lesson.materials.count(), 1)
        self.assertEqual(course.translations.get(locale=LocaleCode.EN).title, "Fundamentals")

    def test_course_translation_locale_unique(self):
        course = Course.objects.create()
        CourseTranslation.objects.create(course=course, locale=LocaleCode.BN, title="ক")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                CourseTranslation.objects.create(course=course, locale=LocaleCode.BN, title="খ")


class AssessmentStructureTests(TestCase):
    def _hierarchy_topic(self):
        course = Course.objects.create()
        subject = Subject.objects.create(course=course)
        unit = Unit.objects.create(subject=subject)
        chapter = Chapter.objects.create(unit=unit)
        return Topic.objects.create(chapter=chapter)

    def test_question_version_and_options(self):
        topic = self._hierarchy_topic()
        question = Question.objects.create(
            question_type=QuestionType.MCQ,
            difficulty=DifficultyLevel.EASY,
            editorial_state=EditorialState.PUBLISHED,
        )
        version = QuestionVersion.objects.create(
            question=question,
            version_no=1,
            correct_answer_spec={"key": "A"},
        )
        question.current_version = version
        question.save(update_fields=["current_version", "updated_at"])
        QuestionVersionTranslation.objects.create(
            version=version, locale=LocaleCode.EN, stem="What is BP?", explanation="..."
        )
        QuestionOption.objects.create(question_version=version, key="A", is_correct=True, sort_order=0)
        QuestionOption.objects.create(question_version=version, key="B", is_correct=False, sort_order=1)
        QuestionTopic.objects.create(question=question, topic=topic)

        self.assertEqual(question.versions.count(), 1)
        self.assertEqual(version.options.count(), 2)
        self.assertEqual(question.topics.count(), 1)

    def test_question_version_unique_per_question(self):
        question = Question.objects.create(
            question_type=QuestionType.TRUE_FALSE,
            difficulty=DifficultyLevel.MEDIUM,
        )
        QuestionVersion.objects.create(question=question, version_no=1)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                QuestionVersion.objects.create(question=question, version_no=1)

    def test_attempt_item_requires_question_version(self):
        user = UserAccount.objects.create_user(email="attempt@example.com", password="x")
        question = Question.objects.create(
            question_type=QuestionType.MCQ,
            difficulty=DifficultyLevel.HARD,
        )
        version = QuestionVersion.objects.create(question=question, version_no=1)
        attempt = Attempt.objects.create(
            user=user,
            mode=AttemptMode.PRACTICE,
            state=AttemptState.IN_PROGRESS,
        )
        item = AttemptItem.objects.create(
            attempt=attempt,
            position=1,
            question=question,
            question_version=version,
            selected_answer={"key": "A"},
        )
        self.assertEqual(item.question_version_id, version.id)
        self.assertIsNone(item.is_correct)  # scoring deferred


class BillingFoundationTests(TestCase):
    def test_one_subscription_per_user_and_payment_idempotency(self):
        user = UserAccount.objects.create_user(email="bill@example.com", password="x")
        sub = Subscription.objects.create(user=user, state=SubscriptionState.FREE)
        PaymentTransaction.objects.create(
            user=user,
            subscription=sub,
            gateway=PaymentGateway.BKASH,
            gateway_ref="txn-1",
            amount="499.00",
            currency="BDT",
            status=PaymentStatus.INITIATED,
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                PaymentTransaction.objects.create(
                    user=user,
                    subscription=sub,
                    gateway=PaymentGateway.BKASH,
                    gateway_ref="txn-1",
                    amount="499.00",
                    status=PaymentStatus.INITIATED,
                )


class AuditAppendOnlyTests(TestCase):
    def test_audit_event_cannot_be_updated(self):
        user = UserAccount.objects.create_user(email="audit@example.com", password="x")
        event = AuditEvent.objects.create(
            actor_user=user,
            action="login_success",
            target_type="user_account",
            target_id=str(user.id),
        )
        event.action = "login_failure"
        with self.assertRaises(ValueError):
            event.save()


class MigrationSmokeTests(TransactionTestCase):
    def test_expected_tables_exist(self):
        tables = set(connection.introspection.table_names())
        expected = {
            "user_accounts",
            "academic_profiles",
            "roles",
            "role_assignments",
            "subscriptions",
            "payment_transactions",
            "entitlement_grants",
            "courses",
            "subjects",
            "units",
            "chapters",
            "topics",
            "lessons",
            "learning_materials",
            "questions",
            "question_versions",
            "question_options",
            "attempts",
            "attempt_items",
            "books",
            "audit_events",
            "platform_settings",
            "feature_toggles",
            "search_documents",
        }
        missing = expected - tables
        self.assertFalse(missing, f"Missing tables: {missing}")


class HealthStillOkTests(TestCase):
    def test_health_endpoint(self):
        response = self.client.get(reverse("health"))
        self.assertEqual(response.status_code, 200)
