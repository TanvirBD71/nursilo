"""Announcement staff management (docs/03 §4.9)."""
from __future__ import annotations

from django.db import transaction
from django.db.models import Q

from apps.audit.services import AuditService
from apps.cms.services import EditorialWorkflowService
from apps.common.choices import EditorialState, LocaleCode
from apps.notifications.models import Announcement, AnnouncementTranslation
from apps.rbac.services import AccessControlService
from apps.staff.services.pagination import paginate_queryset


class AnnouncementStaffError(Exception):
    def __init__(self, message: str, *, code: str = "announcement_error"):
        super().__init__(message)
        self.code = code


class AnnouncementStaffService:
    @classmethod
    def list_announcements(cls, actor, *, q: str = "", page=1):
        if not (
            AccessControlService.has_permission(actor, "announcements.create")
            or AccessControlService.has_permission(actor, "announcements.publish")
        ):
            raise PermissionError("Permission denied.")
        qs = Announcement.objects.all().order_by("-updated_at")
        if q:
            qs = qs.filter(
                Q(code__icontains=q) | Q(translations__title__icontains=q)
            ).distinct()
        return paginate_queryset(qs.prefetch_related("translations"), page=page)

    @classmethod
    def get(cls, actor, announcement_id) -> Announcement:
        if not (
            AccessControlService.has_permission(actor, "announcements.create")
            or AccessControlService.has_permission(actor, "announcements.publish")
        ):
            raise PermissionError("Permission denied.")
        try:
            return Announcement.objects.prefetch_related("translations").get(
                pk=announcement_id
            )
        except Announcement.DoesNotExist as exc:
            raise AnnouncementStaffError("Not found.", code="not_found") from exc

    @classmethod
    @transaction.atomic
    def create(
        cls,
        *,
        actor,
        code: str,
        title: str,
        body: str,
        locale: str = LocaleCode.EN,
    ) -> Announcement:
        AccessControlService.require_permission(actor, "announcements.create")
        code = (code or "").strip().lower()
        if not code:
            raise AnnouncementStaffError("Code required.", code="validation")
        row = Announcement.objects.create(
            code=code,
            editorial_state=EditorialState.DRAFT,
            created_by=actor,
            updated_by=actor,
            targeting={},
        )
        AnnouncementTranslation.objects.create(
            announcement=row,
            locale=locale,
            title=(title or "").strip() or code,
            body=body or "",
        )
        AuditService.record(
            action="announcement_created",
            actor_user=actor,
            target_type="announcement",
            target_id=str(row.id),
            metadata={"code": code},
        )
        return row

    @classmethod
    def workflow(cls, *, actor, announcement_id, action: str, notes: str = ""):
        row = cls.get(actor, announcement_id)
        if action == "publish":
            AccessControlService.require_permission(actor, "announcements.publish")
        return EditorialWorkflowService.transition(
            obj=row,
            action=action,
            actor=actor,
            domain="content",
            target_type="announcement",
            notes=notes,
        )
