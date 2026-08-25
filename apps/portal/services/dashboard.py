"""Dashboard presentation assembly — real data only (docs/15 §7)."""
from __future__ import annotations

from dataclasses import dataclass

from apps.accounts.models import AcademicProfile
from apps.learning.services.progress import LearningProgressService
from apps.portal.services.notifications import NotificationPresentationService
from apps.portal.services.subscription import SubscriptionPresentationService


@dataclass(frozen=True)
class DashboardSection:
    key: str
    title: str
    available: bool
    empty: bool
    unavailable_reason: str = ""
    data: dict | None = None


class DashboardPresentationService:
    """
    Compose dashboard sections in docs/15 visual priority order.
    Domains not yet implemented → available=False with honest reason.
    Never fabricate progress, exams, streaks, or premium state.
    """

    UNAVAILABLE = "This area will be available when the module is ready."

    @classmethod
    def build(cls, user) -> dict:
        subscription = SubscriptionPresentationService.for_user(user)
        notifications = NotificationPresentationService.recent_for_dashboard(user)
        unread = NotificationPresentationService.unread_count(user)
        profile = cls._profile_summary(user)
        # Lazy import avoids circular dependency with library.access → portal.subscription.
        from apps.library.services.presentation import LibraryPresentationService

        continue_learning = LearningProgressService.continue_learning_for(
            user, locale=profile.get("ui_locale") or "en"
        )
        library_bookmarks = LibraryPresentationService.dashboard_bookmarks(user)

        sections = [
            DashboardSection(
                key="continue_learning",
                title="Continue Learning",
                available=True,
                empty=continue_learning.empty,
                data={
                    "lesson_title": continue_learning.lesson_title,
                    "course_title": continue_learning.course_title,
                    "href": continue_learning.href,
                    "message": continue_learning.message,
                },
            ),
            DashboardSection(
                key="todays_goal",
                title="Today's Goal",
                available=False,
                empty=True,
                unavailable_reason=cls.UNAVAILABLE,
            ),
            DashboardSection(
                key="primary_study_action",
                title="Primary Study Action",
                available=False,
                empty=True,
                unavailable_reason=cls.UNAVAILABLE,
            ),
            DashboardSection(
                key="progress",
                title="Progress",
                available=False,
                empty=True,
                unavailable_reason=cls.UNAVAILABLE,
            ),
            DashboardSection(
                key="exam_history",
                title="Exam History",
                available=False,
                empty=True,
                unavailable_reason=cls.UNAVAILABLE,
            ),
            DashboardSection(
                key="weak_strong_topics",
                title="Weak / Strong Topics",
                available=False,
                empty=True,
                unavailable_reason=cls.UNAVAILABLE,
            ),
            DashboardSection(
                key="bookmarks",
                title="Bookmarks",
                available=True,
                empty=library_bookmarks["empty"],
                data=library_bookmarks,
            ),
            DashboardSection(
                key="notes",
                title="Notes",
                available=False,
                empty=True,
                unavailable_reason=cls.UNAVAILABLE,
            ),
            DashboardSection(
                key="activity",
                title="Activity",
                available=False,
                empty=True,
                unavailable_reason=cls.UNAVAILABLE,
            ),
            DashboardSection(
                key="streak",
                title="Streak",
                available=False,
                empty=True,
                unavailable_reason=cls.UNAVAILABLE,
            ),
            DashboardSection(
                key="subscription",
                title="Subscription",
                available=True,
                empty=False,
                data={
                    "state": subscription.state,
                    "label": subscription.label,
                    "is_premium": subscription.is_premium,
                    "premium_expires_at": subscription.premium_expires_at,
                    "source": subscription.source,
                },
            ),
            DashboardSection(
                key="notifications",
                title="Notifications",
                available=True,
                empty=len(notifications) == 0,
                data={
                    "unread_count": unread,
                    "items": notifications,
                },
            ),
        ]

        return {
            "profile": profile,
            "subscription": subscription,
            "sections": sections,
            "has_any_learning_data": not continue_learning.empty,
        }

    @staticmethod
    def _profile_summary(user) -> dict:
        academic = None
        try:
            academic = user.academic_profile
        except AcademicProfile.DoesNotExist:
            academic = None
        return {
            "full_name": user.full_name or "",
            "email": user.email,
            "ui_locale": user.ui_locale,
            "email_verified": user.is_email_verified,
            "has_academic_profile": academic is not None,
        }
