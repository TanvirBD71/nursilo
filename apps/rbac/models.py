"""RBAC catalog — roles and assignments (docs/03, docs/05, docs/06 §8.3)."""
from django.conf import settings
from django.db import models

from apps.common.choices import RoleCode
from apps.common.models import UUIDPrimaryKeyModel


class Role(UUIDPrimaryKeyModel):
    code = models.CharField(max_length=32, unique=True, choices=RoleCode.choices)
    name = models.CharField(max_length=64)

    class Meta:
        db_table = "roles"
        ordering = ["code"]

    def __str__(self):
        return self.code


class RoleAssignment(UUIDPrimaryKeyModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="role_assignments",
    )
    role = models.ForeignKey(
        Role,
        on_delete=models.PROTECT,
        related_name="assignments",
    )
    assigned_at = models.DateTimeField(auto_now_add=True)
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="role_assignments_made",
    )

    class Meta:
        db_table = "role_assignments"
        constraints = [
            models.UniqueConstraint(fields=["user", "role"], name="uq_role_assignments_user_role"),
        ]
        indexes = [
            models.Index(fields=["user", "role"]),
        ]

    def __str__(self):
        return f"{self.user_id}:{self.role_id}"
