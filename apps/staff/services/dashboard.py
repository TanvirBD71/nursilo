"""Staff dashboard presentation aggregates (read-only counts)."""
from __future__ import annotations

from dataclasses import dataclass

from apps.assessment.models import ExamDefinition, Question
from apps.billing.models import PaymentTransaction, Subscription
from apps.cms.models import BlogPost, CmsPage, ContactMessage
from apps.common.choices import ContactMessageStatus, EditorialState, PaymentStatus
from apps.learning.models import Course
from apps.library.models import Book
from apps.notifications.models import Announcement
from apps.rbac.services import AccessControlService
from apps.staff.services.questions import QuestionStaffService


@dataclass(frozen=True)
class StaffDashboardData:
    courses_total: int
    courses_in_review: int
    questions_total: int
    questions_in_review: int
    exams_published: int
    books_total: int
    announcements_published: int
    open_contact: int
    premium_active: int
    payments_pending: int
    can_users: bool
    can_billing: bool
    can_audit: bool
    question_bank: dict


class StaffDashboardService:
    @classmethod
    def build(cls, user) -> StaffDashboardData:
        return StaffDashboardData(
            courses_total=Course.objects.count(),
            courses_in_review=Course.objects.filter(
                editorial_state=EditorialState.REVIEW, is_archived=False
            ).count(),
            questions_total=Question.objects.count(),
            questions_in_review=Question.objects.filter(
                editorial_state=EditorialState.REVIEW, is_archived=False
            ).count(),
            exams_published=ExamDefinition.objects.filter(
                editorial_state=EditorialState.PUBLISHED, is_archived=False
            ).count(),
            books_total=Book.objects.count(),
            announcements_published=Announcement.objects.filter(
                editorial_state=EditorialState.PUBLISHED, is_archived=False
            ).count(),
            open_contact=ContactMessage.objects.filter(
                status=ContactMessageStatus.NEW
            ).count()
            + BlogPost.objects.filter(editorial_state=EditorialState.REVIEW).count()
            + CmsPage.objects.filter(editorial_state=EditorialState.REVIEW).count(),
            premium_active=Subscription.objects.filter(state="premium_active").count(),
            payments_pending=PaymentTransaction.objects.filter(
                status=PaymentStatus.INITIATED
            ).count(),
            can_users=AccessControlService.has_permission(user, "users.view"),
            can_billing=AccessControlService.has_permission(
                user, "billing.view_subscriptions"
            ),
            can_audit=AccessControlService.has_permission(user, "audit.view"),
            question_bank=cls._question_bank(user),
        )

    @classmethod
    def _question_bank(cls, user) -> dict:
        try:
            return QuestionStaffService.bank_dashboard_counts(user)
        except PermissionError:
            return {}
