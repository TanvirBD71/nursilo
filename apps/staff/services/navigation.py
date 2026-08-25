"""Role-aware staff navigation (docs/11 §5.3, docs/15). Presentation only."""
from __future__ import annotations

from dataclasses import dataclass

from django.urls import reverse

from apps.rbac.services import AccessControlService


@dataclass(frozen=True)
class StaffNavItem:
    key: str
    label: str
    href: str | None
    available: bool
    current: bool = False


class StaffNavigationService:
    """
    Modules appear only when the actor has a relevant permission.
    Absence of a nav link is not authorization — views still enforce.
    """

    MODULES = (
        ("dashboard", "Dashboard", "staff:dashboard", ("staff.access",)),
        ("users", "Users", "staff:users", ("users.view",)),
        ("learning", "Learning", "staff:learning", ("content.create_draft", "content.view_unpublished", "content.edit", "content.publish")),
        ("questions", "Questions", "staff:questions", ("questions.create", "questions.view_unpublished", "questions.edit", "questions.publish")),
        ("exams", "Exams", "staff:exams", ("exams.view", "exams.create", "exams.edit")),
        ("library", "Library", "staff:library", ("library.manage", "content.create_draft", "content.publish")),
        ("cms", "CMS", "staff:cms", ("cms.manage", "content.publish")),
        ("announcements", "Announcements", "staff:announcements", ("announcements.create", "announcements.publish")),
        ("billing", "Billing", "staff:billing", ("billing.view_subscriptions", "billing.view_payments")),
        ("audit", "Audit", "staff:audit", ("audit.view",)),
        ("editorial", "Editorial queue", "staff:editorial_queue", ("content.approve", "content.publish", "content.submit_review", "questions.approve")),
    )

    @classmethod
    def items(cls, user, *, active: str | None = None) -> list[StaffNavItem]:
        perms = AccessControlService.effective_permissions(user)
        items: list[StaffNavItem] = []
        for key, label, route, needed in cls.MODULES:
            available = AccessControlService.is_super_admin(user) or bool(
                perms.intersection(needed)
            )
            href = reverse(route) if available else None
            items.append(
                StaffNavItem(
                    key=key,
                    label=label,
                    href=href,
                    available=available,
                    current=active == key,
                )
            )
        return items
