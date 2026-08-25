"""Notifications and announcements foundation (docs/05 §12, docs/06 §8.14)."""
from django.conf import settings
from django.db import models

from apps.common.models import (
    ActorTrackedModel,
    ArchivableModel,
    EditorialModel,
    LocaleField,
    OptimisticConcurrencyModel,
    TimeStampedModel,
    UUIDPrimaryKeyModel,
)


class Notification(UUIDPrimaryKeyModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="notifications",
    )
    kind = models.CharField(max_length=64, db_index=True)
    title = models.CharField(max_length=255)
    body = models.TextField(blank=True, default="")
    is_read = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    announcement = models.ForeignKey(
        "Announcement",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notifications",
    )

    class Meta:
        db_table = "notifications"
        indexes = [
            models.Index(fields=["user", "is_read", "-created_at"]),
        ]


class Announcement(
    UUIDPrimaryKeyModel,
    TimeStampedModel,
    ActorTrackedModel,
    OptimisticConcurrencyModel,
    ArchivableModel,
    EditorialModel,
):
    code = models.CharField(max_length=64, unique=True)
    targeting = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "announcements"
        indexes = [
            models.Index(fields=["editorial_state", "is_archived"]),
        ]


class AnnouncementTranslation(UUIDPrimaryKeyModel):
    announcement = models.ForeignKey(
        Announcement,
        on_delete=models.CASCADE,
        related_name="translations",
    )
    locale = LocaleField()
    title = models.CharField(max_length=255)
    body = models.TextField()

    class Meta:
        db_table = "announcement_translations"
        constraints = [
            models.UniqueConstraint(
                fields=["announcement", "locale"],
                name="uq_announcement_translations_locale",
            ),
        ]
