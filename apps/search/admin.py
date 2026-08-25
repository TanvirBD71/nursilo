from django.contrib import admin

from apps.search.models import SearchDocument


@admin.register(SearchDocument)
class SearchDocumentAdmin(admin.ModelAdmin):
    list_display = ("entity_type", "entity_id", "locale", "title", "is_published", "is_archived")
    list_filter = ("entity_type", "locale", "is_published", "is_archived")
    search_fields = ("title",)
