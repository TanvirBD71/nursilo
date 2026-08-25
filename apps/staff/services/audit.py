"""Audit log presentation — reuses AuditEvent only (no parallel architecture)."""
from __future__ import annotations

from django.db.models import Q

from apps.audit.models import AuditEvent
from apps.rbac.services import AccessControlService
from apps.staff.services.pagination import paginate_queryset


class AuditStaffService:
    @classmethod
    def list_events(cls, actor, *, q: str = "", action: str = "", page=1):
        AccessControlService.require_permission(actor, "audit.view")
        qs = AuditEvent.objects.select_related("actor_user").order_by("-created_at")
        if action:
            qs = qs.filter(action__icontains=action)
        if q:
            qs = qs.filter(
                Q(action__icontains=q)
                | Q(target_type__icontains=q)
                | Q(target_id__icontains=q)
                | Q(actor_user__email__icontains=q)
            )
        return paginate_queryset(qs, page=page, per_page=50)

    @classmethod
    def get_event(cls, actor, event_id) -> AuditEvent:
        AccessControlService.require_permission(actor, "audit.view")
        return AuditEvent.objects.select_related("actor_user").get(pk=event_id)
