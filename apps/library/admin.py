from django.contrib import admin

from apps.library.models import Book, BookAsset


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ("id", "author_name", "editorial_state", "is_premium", "is_archived")
    list_filter = ("editorial_state", "is_premium", "is_archived")


@admin.register(BookAsset)
class BookAssetAdmin(admin.ModelAdmin):
    list_display = ("id", "book", "format", "storage_key", "sort_order")
    list_filter = ("format",)
    raw_id_fields = ("book",)
