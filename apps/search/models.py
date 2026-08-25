"""Search projection read model (docs/05 §14, docs/06 §12)."""
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField
from django.db import models

from apps.common.choices import SearchEntityType
from apps.common.models import LocaleField, UUIDPrimaryKeyModel


class SearchDocument(UUIDPrimaryKeyModel):
    """Rebuildable projection — not a write source of truth."""

    entity_type = models.CharField(max_length=32, choices=SearchEntityType.choices, db_index=True)
    entity_id = models.UUIDField()
    locale = LocaleField()
    title = models.CharField(max_length=512)
    body_text = models.TextField(blank=True, default="")
    is_published = models.BooleanField(default=False)
    is_archived = models.BooleanField(default=False)
    is_premium = models.BooleanField(default=False)
    search_vector = SearchVectorField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "search_documents"
        constraints = [
            models.UniqueConstraint(
                fields=["entity_type", "entity_id", "locale"],
                name="uq_search_documents_entity_locale",
            ),
        ]
        indexes = [
            GinIndex(fields=["search_vector"], name="search_documents_vector_gin"),
            models.Index(fields=["entity_type"]),
            models.Index(fields=["is_published", "is_archived"]),
        ]
