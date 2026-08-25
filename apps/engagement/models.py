"""Learner-owned engagement aggregates (docs/05 §11, docs/06 §8.13)."""
from django.conf import settings
from django.db import models

from apps.common.models import TimeStampedModel, UUIDPrimaryKeyModel


class PersonalNote(UUIDPrimaryKeyModel, TimeStampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="personal_notes",
    )
    target_type = models.CharField(max_length=64)
    target_id = models.UUIDField()
    body = models.TextField()

    class Meta:
        db_table = "personal_notes"
        indexes = [
            models.Index(fields=["user", "target_type", "target_id"]),
            models.Index(fields=["user", "-updated_at"]),
        ]


class Bookmark(UUIDPrimaryKeyModel, TimeStampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="bookmarks",
    )
    target_type = models.CharField(max_length=64)
    target_id = models.UUIDField()

    class Meta:
        db_table = "bookmarks"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "target_type", "target_id"],
                name="uq_bookmarks_user_target",
            ),
        ]


class StudyGoal(UUIDPrimaryKeyModel, TimeStampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="study_goals",
    )
    title = models.CharField(max_length=255)
    target_count = models.PositiveIntegerField(default=0)
    progress_count = models.PositiveIntegerField(default=0)
    period_start = models.DateField(null=True, blank=True)
    period_end = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "study_goals"
        indexes = [
            models.Index(fields=["user", "is_active"]),
        ]


class StudyStreak(UUIDPrimaryKeyModel, TimeStampedModel):
    """One streak row per user (docs/06 §22)."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="study_streak",
    )
    current_streak_days = models.PositiveIntegerField(default=0)
    longest_streak_days = models.PositiveIntegerField(default=0)
    last_activity_date = models.DateField(null=True, blank=True)

    class Meta:
        db_table = "study_streaks"
