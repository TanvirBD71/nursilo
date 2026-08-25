"""Entitlement grant facts — evaluation services come in later units."""
from django.conf import settings
from django.db import models

from apps.common.models import CreatedOnlyModel, UUIDPrimaryKeyModel


class EntitlementGrant(UUIDPrimaryKeyModel, CreatedOnlyModel):
    """
    Explicit capability grant/period (docs/05 EntitlementGrant, docs/06 §7.2).

    No capability-evaluation or payment-activation logic lives on this model.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="entitlement_grants",
    )
    capability_code = models.CharField(max_length=64, db_index=True)
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    source = models.CharField(max_length=32, default="manual")  # manual | payment | system
    granted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="entitlement_grants_made",
    )
    is_active = models.BooleanField(default=True, db_index=True)
    notes = models.TextField(blank=True, default="")

    class Meta:
        db_table = "entitlement_grants"
        indexes = [
            models.Index(fields=["user", "capability_code", "is_active"]),
            models.Index(fields=["ends_at"]),
        ]

    def __str__(self):
        return f"Grant({self.user_id}:{self.capability_code})"
