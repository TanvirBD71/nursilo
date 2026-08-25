"""Book library catalog foundation (docs/05 §10, docs/06 §8.12)."""
from django.db import models

from apps.common.choices import BookFormat
from apps.common.models import (
    ActorTrackedModel,
    ArchivableModel,
    EditorialModel,
    LocaleField,
    OptimisticConcurrencyModel,
    TimeStampedModel,
    UUIDPrimaryKeyModel,
)


class Book(
    UUIDPrimaryKeyModel,
    TimeStampedModel,
    ActorTrackedModel,
    OptimisticConcurrencyModel,
    ArchivableModel,
    EditorialModel,
):
    category = models.CharField(max_length=128, blank=True, default="")
    author_name = models.CharField(max_length=255, blank=True, default="")
    edition = models.CharField(max_length=64, blank=True, default="")
    publisher = models.CharField(max_length=255, blank=True, default="")
    cover_storage_key = models.CharField(max_length=512, blank=True, default="")
    is_premium = models.BooleanField(default=False, db_index=True)
    courses = models.ManyToManyField(
        "learning.Course",
        through="BookCourse",
        related_name="books",
        blank=True,
    )

    class Meta:
        db_table = "books"
        indexes = [
            models.Index(fields=["editorial_state", "is_archived"]),
        ]

    def __str__(self):
        return f"Book({self.pk})"


class BookTranslation(UUIDPrimaryKeyModel):
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="translations")
    locale = LocaleField()
    title = models.CharField(max_length=255)
    blurb = models.TextField(blank=True, default="")

    class Meta:
        db_table = "book_translations"
        constraints = [
            models.UniqueConstraint(fields=["book", "locale"], name="uq_book_translations_locale"),
        ]


class BookAsset(UUIDPrimaryKeyModel, TimeStampedModel):
    book = models.ForeignKey(Book, on_delete=models.PROTECT, related_name="assets")
    format = models.CharField(max_length=16, choices=BookFormat.choices)
    storage_key = models.CharField(max_length=512)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "book_assets"
        indexes = [
            models.Index(fields=["book", "sort_order"]),
            models.Index(fields=["format"]),
        ]


class BookCourse(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    course = models.ForeignKey("learning.Course", on_delete=models.CASCADE)

    class Meta:
        db_table = "books_courses"
        constraints = [
            models.UniqueConstraint(fields=["book", "course"], name="uq_books_courses"),
        ]
