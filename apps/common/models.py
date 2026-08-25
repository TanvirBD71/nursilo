"""Abstract model mixins — structure/invariants only; no domain workflows."""
import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.common.choices import EditorialState, LocaleCode


class UUIDPrimaryKeyModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class CreatedOnlyModel(models.Model):
    """Append-only / log-like rows (no updated_at mutation channel)."""

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        abstract = True


class ActorTrackedModel(models.Model):
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(app_label)s_%(class)s_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(app_label)s_%(class)s_updated",
    )

    class Meta:
        abstract = True


class OptimisticConcurrencyModel(models.Model):
    """Monotonic token for mutable catalog heads (docs/06 §19)."""

    version_number = models.PositiveIntegerField(default=1)

    class Meta:
        abstract = True


class ArchivableModel(models.Model):
    is_archived = models.BooleanField(default=False, db_index=True)
    archived_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True

    def mark_archived(self, *, at=None):
        """Structural helper only — callers/services own policy."""
        self.is_archived = True
        self.archived_at = at or timezone.now()


class EditorialModel(models.Model):
    editorial_state = models.CharField(
        max_length=20,
        choices=EditorialState.choices,
        default=EditorialState.DRAFT,
        db_index=True,
    )
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True


class CatalogNodeModel(
    UUIDPrimaryKeyModel,
    TimeStampedModel,
    ActorTrackedModel,
    OptimisticConcurrencyModel,
    ArchivableModel,
    EditorialModel,
):
    """Shared pattern for learning hierarchy and similar publishable catalog rows."""

    sort_order = models.PositiveIntegerField(default=0, db_index=True)

    class Meta:
        abstract = True


class LocaleField(models.CharField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("max_length", 5)
        kwargs.setdefault("choices", LocaleCode.choices)
        super().__init__(*args, **kwargs)
