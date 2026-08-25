"""Append-only audit events (docs/05 §15, docs/06 §8.15 / §10)."""
from django.conf import settings
from django.db import models

from apps.common.models import UUIDPrimaryKeyModel


class AuditEvent(UUIDPrimaryKeyModel):
    """No updated_at — append-only by policy (services must not update rows)."""

    actor_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_events",
    )
    action = models.CharField(max_length=64, db_index=True)
    target_type = models.CharField(max_length=64, blank=True, default="")
    target_id = models.CharField(max_length=64, blank=True, default="")
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "audit_events"
        indexes = [
            models.Index(fields=["-created_at"]),
            models.Index(fields=["actor_user", "-created_at"]),
            models.Index(fields=["action", "-created_at"]),
            models.Index(fields=["target_type", "target_id"]),
        ]

    def __str__(self):
        return f"Audit({self.action}@{self.created_at})"

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValueError("AuditEvent rows are append-only and cannot be updated.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("AuditEvent rows are append-only and cannot be deleted.")
