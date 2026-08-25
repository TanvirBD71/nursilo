"""UNIT-9 Staff/Admin + CMS Editorial Foundation tests."""
from __future__ import annotations

import unittest

from django.db import connection
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from apps.accounts.models import UserAccount
from apps.accounts.services import AccountService
from apps.assessment.models import Question
from apps.audit.models import AuditEvent
from apps.billing.models import Subscription
from apps.billing.plans import PlanCatalog
from apps.cms.models import CmsPage
from apps.cms.services import EditorialWorkflowError, EditorialWorkflowService
from apps.common.choices import EditorialState, RoleCode, SubscriptionState
from apps.learning.models import Course
from apps.library.models import Book
from apps.notifications.models import Announcement
from apps.rbac.models import Role, RoleAssignment
from apps.rbac.services import AccessControlService
from apps.staff.access import user_may_access_staff_console
from apps.staff.services import (
    BillingStaffService,
    LearningStaffService,
    QuestionStaffService,
    UserStaffService,
)
from apps.staff.services.users import UserStaffError


STRONG_PASSWORD = "Str0ng-Pass!Unit9"


def setUpModule():
    try:
        connection.ensure_connection()
    except Exception as exc:  # pragma: no cover
        raise unittest.SkipTest(f"PostgreSQL unavailable for UNIT-9: {exc}") from exc


def _assign(user, *role_codes):
    for code in role_codes:
        role = Role.objects.get(code=code)
        RoleAssignment.objects.get_or_create(user=user, role=role)


def _staff_user(email, *role_codes):
    user = UserAccount.objects.create_user(
        email=email, password=STRONG_PASSWORD, full_name="Staff Nine"
    )
    _assign(user, *role_codes)
    return user


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"],
)
class StaffAuthzBoundaryTests(TestCase):
    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)
        self.student, _ = AccountService.register(
            email="student9@example.com",
            password=STRONG_PASSWORD,
            full_name="Student Nine",
        )
        self.admin = _staff_user("admin9@example.com", RoleCode.ADMIN)
        self.author = _staff_user("author9@example.com", RoleCode.AUTHOR)
        self.reviewer = _staff_user("reviewer9@example.com", RoleCode.REVIEWER)

    def _login(self, email):
        url = reverse("accounts:login")
        self.client.get(url)
        return self.client.post(
            url,
            {
                "email": email,
                "password": STRONG_PASSWORD,
                "next": "",
                "csrfmiddlewaretoken": self.client.cookies["csrftoken"].value,
            },
        )

    def test_student_denied_staff_console(self):
        self.assertFalse(user_may_access_staff_console(self.student))
        self._login(self.student.email)
        resp = self.client.get(reverse("staff:dashboard"))
        self.assertEqual(resp.status_code, 403)

    def test_admin_can_access_staff_dashboard(self):
        self.assertTrue(user_may_access_staff_console(self.admin))
        self._login(self.admin.email)
        resp = self.client.get(reverse("staff:dashboard"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Staff dashboard")
        self.assertContains(resp, "Nursilo")

    def test_author_cannot_open_users_or_audit(self):
        self._login(self.author.email)
        self.assertEqual(self.client.get(reverse("staff:users")).status_code, 403)
        self.assertEqual(self.client.get(reverse("staff:audit")).status_code, 403)

    def test_reviewer_cannot_publish_permission(self):
        self.assertFalse(
            AccessControlService.has_permission(self.reviewer, "content.publish")
        )
        self.assertTrue(
            AccessControlService.has_permission(self.reviewer, "content.approve")
        )

    def test_home_redirects_staff_only_to_staff(self):
        self._login(self.admin.email)
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/staff/", resp["Location"])

    def test_login_redirects_staff_only_to_staff(self):
        self.client.logout()
        resp = self._login(self.admin.email)
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/staff/", resp["Location"])


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"],
)
class UserManagementTests(TestCase):
    def setUp(self):
        self.admin = _staff_user("um-admin@example.com", RoleCode.ADMIN)
        self.super = _staff_user("um-super@example.com", RoleCode.SUPER_ADMIN)

    def test_admin_creates_author_and_cannot_grant_super_admin(self):
        user = UserStaffService.create_user(
            actor=self.admin,
            email="new-author@example.com",
            password=STRONG_PASSWORD,
            full_name="New Author",
            role_code=RoleCode.AUTHOR,
        )
        self.assertTrue(AccessControlService.has_role(user, RoleCode.AUTHOR))
        self.assertFalse(
            AccessControlService.may_assign_role(
                actor=self.admin, role_code=RoleCode.SUPER_ADMIN
            )
        )
        with self.assertRaises(UserStaffError):
            UserStaffService.set_roles(
                actor=self.admin,
                user=user,
                role_codes=[RoleCode.SUPER_ADMIN],
            )

    def test_cannot_remove_last_super_admin(self):
        with self.assertRaises(UserStaffError):
            UserStaffService.set_roles(
                actor=self.super,
                user=self.super,
                role_codes=[RoleCode.ADMIN],
            )


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"],
)
class EditorialWorkflowTests(TestCase):
    def setUp(self):
        self.author = _staff_user("ed-author@example.com", RoleCode.AUTHOR)
        self.reviewer = _staff_user("ed-reviewer@example.com", RoleCode.REVIEWER)
        self.editor = _staff_user("ed-editor@example.com", RoleCode.EDITOR)
        self.student, _ = AccountService.register(
            email="ed-student@example.com",
            password=STRONG_PASSWORD,
            full_name="Ed Student",
        )

    def test_full_happy_path_and_learner_visibility(self):
        course = LearningStaffService.create_node(
            actor=self.author,
            kind="course",
            title_en="UNIT9 Course",
            title_bn="ইউনিট৯",
        )
        self.assertEqual(course.editorial_state, EditorialState.DRAFT)
        EditorialWorkflowService.transition(
            obj=course, action="submit_review", actor=self.author, target_type="course"
        )
        course.refresh_from_db()
        self.assertEqual(course.editorial_state, EditorialState.REVIEW)
        with self.assertRaises(EditorialWorkflowError):
            EditorialWorkflowService.transition(
                obj=course, action="publish", actor=self.reviewer, target_type="course"
            )
        EditorialWorkflowService.transition(
            obj=course, action="approve", actor=self.reviewer, target_type="course"
        )
        course.refresh_from_db()
        self.assertEqual(course.editorial_state, EditorialState.APPROVED)
        EditorialWorkflowService.transition(
            obj=course, action="publish", actor=self.editor, target_type="course"
        )
        course.refresh_from_db()
        self.assertEqual(course.editorial_state, EditorialState.PUBLISHED)
        self.assertIsNotNone(course.published_at)
        # Learner catalog only sees published (UNIT-4 access invariant).
        from apps.learning.models import Course
        from apps.learning.services.catalog import LearningCatalogService

        published_ids = set(
            LearningCatalogService.published_qs(Course).values_list("id", flat=True)
        )
        self.assertIn(course.id, published_ids)
        actions = AuditEvent.objects.filter(
            target_id=str(course.id), action__startswith="editorial_"
        ).values_list("action", flat=True)
        self.assertIn("editorial_publish", set(actions))

    def test_reject_returns_to_draft(self):
        course = LearningStaffService.create_node(
            actor=self.author, kind="course", title_en="Reject Me"
        )
        EditorialWorkflowService.transition(
            obj=course, action="submit_review", actor=self.author, target_type="course"
        )
        EditorialWorkflowService.transition(
            obj=course, action="reject", actor=self.reviewer, target_type="course"
        )
        course.refresh_from_db()
        self.assertEqual(course.editorial_state, EditorialState.DRAFT)

    def test_student_preview_idor(self):
        course = LearningStaffService.create_node(
            actor=self.author, kind="course", title_en="Hidden Draft"
        )
        client = Client()
        client.force_login(self.student)
        resp = client.get(
            reverse("staff:learning_preview", kwargs={"kind": "course", "node_id": course.id})
        )
        self.assertEqual(resp.status_code, 403)


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"],
)
class QuestionExamLibraryStaffTests(TestCase):
    def setUp(self):
        self.editor = _staff_user("q-editor@example.com", RoleCode.EDITOR)
        self.reviewer = _staff_user("q-reviewer@example.com", RoleCode.REVIEWER)

    def test_question_create_and_publish_flow(self):
        q = QuestionStaffService.create_question(
            actor=self.editor,
            stem="What is asepsis?",
            explanation="Infection control",
            options=[
                {"key": "A", "label": "Sterile technique"},
                {"key": "B", "label": "Wrong"},
            ],
            correct_key="A",
        )
        self.assertEqual(q.editorial_state, EditorialState.DRAFT)
        self.assertIsNotNone(q.current_version)
        EditorialWorkflowService.transition(
            obj=q, action="submit_review", actor=self.editor, domain="questions"
        )
        EditorialWorkflowService.transition(
            obj=q, action="approve", actor=self.reviewer, domain="questions"
        )
        EditorialWorkflowService.transition(
            obj=q, action="publish", actor=self.editor, domain="questions"
        )
        q.refresh_from_db()
        self.assertEqual(q.editorial_state, EditorialState.PUBLISHED)
        # Scoring keys preserved on frozen version.
        from apps.assessment.services.scoring import correct_keys_for_version

        self.assertEqual(correct_keys_for_version(q.current_version), {"A"})

    def test_exam_and_book_staff_crud(self):
        from apps.staff.services import ExamStaffService, LibraryStaffService

        exam = ExamStaffService.create_exam(
            actor=self.editor, code="unit9-mock", title_key="Unit9 Mock"
        )
        self.assertEqual(exam.editorial_state, EditorialState.DRAFT)
        book = LibraryStaffService.create_book(
            actor=self.editor, title_en="Staff Book", is_premium=True
        )
        LibraryStaffService.add_asset(
            actor=self.editor,
            book=book,
            format="pdf",
            storage_key="library/unit9/demo.pdf",
        )
        self.assertEqual(book.assets.count(), 1)


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"],
)
class CmsAnnouncementBillingAuditTests(TestCase):
    def setUp(self):
        self.admin = _staff_user("cms-admin@example.com", RoleCode.ADMIN)
        self.student, _ = AccountService.register(
            email="bill-student@example.com",
            password=STRONG_PASSWORD,
            full_name="Bill Student",
        )
        self.client = Client(enforce_csrf_checks=True)

    def _login(self, email):
        url = reverse("accounts:login")
        self.client.get(url)
        self.client.post(
            url,
            {
                "email": email,
                "password": STRONG_PASSWORD,
                "next": "",
                "csrfmiddlewaretoken": self.client.cookies["csrftoken"].value,
            },
        )

    def test_cms_and_announcement_workflow(self):
        from apps.staff.services import AnnouncementStaffService, CmsStaffService

        page = CmsStaffService.create_page(
            actor=self.admin, code="about-unit9", title="About"
        )
        self.assertEqual(page.editorial_state, EditorialState.DRAFT)
        ann = AnnouncementStaffService.create(
            actor=self.admin,
            code="ann-unit9",
            title="Hello",
            body="Body",
        )
        EditorialWorkflowService.transition(
            obj=ann, action="submit_review", actor=self.admin, target_type="announcement"
        )
        EditorialWorkflowService.transition(
            obj=ann, action="approve", actor=self.admin, target_type="announcement"
        )
        EditorialWorkflowService.transition(
            obj=ann, action="publish", actor=self.admin, target_type="announcement"
        )
        ann.refresh_from_db()
        self.assertEqual(ann.editorial_state, EditorialState.PUBLISHED)

    def test_manual_grant_uses_plan_duration_and_audits(self):
        plan = PlanCatalog.default_plan()
        sub = BillingStaffService.manual_grant_premium(
            actor=self.admin, user_id=self.student.id, notes="support"
        )
        self.assertEqual(sub.state, SubscriptionState.PREMIUM_ACTIVE)
        self.assertIsNotNone(sub.premium_expires_at)
        delta = (sub.premium_expires_at - sub.premium_started_at).days
        self.assertEqual(delta, plan.duration_days)
        self.assertTrue(
            AuditEvent.objects.filter(action="subscription_manual_grant").exists()
        )
        BillingStaffService.manual_revoke_premium(
            actor=self.admin, user_id=self.student.id
        )
        sub.refresh_from_db()
        self.assertEqual(sub.state, SubscriptionState.REVOKED)

    def test_author_cannot_view_billing_or_audit(self):
        author = _staff_user("no-bill@example.com", RoleCode.AUTHOR)
        self._login(author.email)
        self.assertEqual(self.client.get(reverse("staff:billing")).status_code, 403)
        self.assertEqual(self.client.get(reverse("staff:audit")).status_code, 403)

    def test_admin_audit_list(self):
        self._login(self.admin.email)
        resp = self.client.get(reverse("staff:audit"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Audit")


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"],
)
class StaffIdorAndRegressionSmokeTests(TestCase):
    def setUp(self):
        self.author_a = _staff_user("idor-a@example.com", RoleCode.AUTHOR)
        self.author_b = _staff_user("idor-b@example.com", RoleCode.AUTHOR)
        self.client = Client()

    def test_author_cannot_edit_other_author_draft(self):
        course = LearningStaffService.create_node(
            actor=self.author_a, kind="course", title_en="Private Draft"
        )
        from apps.staff.services.learning import LearningStaffError

        with self.assertRaises((PermissionError, LearningStaffError)):
            LearningStaffService.update_node(
                actor=self.author_b,
                kind="course",
                node_id=course.id,
                title_en="Hijack",
            )

    def test_student_facing_portal_still_works(self):
        student, _ = AccountService.register(
            email="reg9@example.com",
            password=STRONG_PASSWORD,
            full_name="Reg Nine",
        )
        self.client.force_login(student)
        resp = self.client.get(reverse("portal:dashboard"))
        self.assertEqual(resp.status_code, 200)

    def test_bulk_safe_archive_permission_enforced(self):
        editor = _staff_user("bulk-ed@example.com", RoleCode.EDITOR)
        author = _staff_user("bulk-au@example.com", RoleCode.AUTHOR)
        course = LearningStaffService.create_node(
            actor=editor, kind="course", title_en="To Archive"
        )
        # Move to published first via editor privileges.
        course.editorial_state = EditorialState.PUBLISHED
        course.save(update_fields=["editorial_state", "updated_at"])
        with self.assertRaises(EditorialWorkflowError):
            EditorialWorkflowService.transition(
                obj=course, action="archive", actor=author, target_type="course"
            )
        EditorialWorkflowService.transition(
            obj=course, action="archive", actor=editor, target_type="course"
        )
        course.refresh_from_db()
        self.assertEqual(course.editorial_state, EditorialState.ARCHIVED)
        self.assertTrue(course.is_archived)
