"""Learner book bookmarks via engagement aggregate (docs/05 §10–§11, docs/06 §8.13)."""
from __future__ import annotations

from dataclasses import dataclass

from apps.engagement.models import Bookmark
from apps.library.models import Book
from apps.library.services.access import LibraryAccessService
from apps.library.services.catalog import LibraryCatalogService


BOOK_TARGET_TYPE = "book"


@dataclass(frozen=True)
class BookmarkMutationResult:
    ok: bool
    bookmarked: bool
    reason: str = ""


class LibraryBookmarkService:
    """
    Book-level bookmarks only (engagement.Bookmark target_type=book).

    Reading-position persistence is not stored in approved V1 schema
    (docs/06 bookmarks have no position column; FEAT-LIB-05 positions → V1.1).
    Ownership is always the authenticated user — no cross-user access.
    """

    TARGET_TYPE = BOOK_TARGET_TYPE

    @classmethod
    def is_bookmarked(cls, user, book: Book) -> bool:
        if user is None or not getattr(user, "is_authenticated", False):
            return False
        return Bookmark.objects.filter(
            user=user, target_type=cls.TARGET_TYPE, target_id=book.id
        ).exists()

    @classmethod
    def add(cls, user, book: Book) -> BookmarkMutationResult:
        visibility = LibraryAccessService.decide_catalog_visibility(user, book)
        if LibraryAccessService.hide_as_not_found(visibility):
            return BookmarkMutationResult(False, False, visibility.reason or "not_found")
        if not visibility.allowed:
            return BookmarkMutationResult(False, False, visibility.reason or "forbidden")
        Bookmark.objects.get_or_create(
            user=user,
            target_type=cls.TARGET_TYPE,
            target_id=book.id,
        )
        return BookmarkMutationResult(True, True)

    @classmethod
    def remove(cls, user, book: Book) -> BookmarkMutationResult:
        if user is None or not getattr(user, "is_authenticated", False):
            return BookmarkMutationResult(False, False, "forbidden")
        deleted, _ = Bookmark.objects.filter(
            user=user, target_type=cls.TARGET_TYPE, target_id=book.id
        ).delete()
        return BookmarkMutationResult(True, False if deleted else cls.is_bookmarked(user, book))

    @classmethod
    def toggle(cls, user, book: Book) -> BookmarkMutationResult:
        if cls.is_bookmarked(user, book):
            return cls.remove(user, book)
        return cls.add(user, book)

    @classmethod
    def list_books_for_user(cls, user) -> list[Book]:
        if user is None or not getattr(user, "is_authenticated", False):
            return []
        ids = list(
            Bookmark.objects.filter(user=user, target_type=cls.TARGET_TYPE)
            .order_by("-updated_at")
            .values_list("target_id", flat=True)
        )
        if not ids:
            return []
        published = {
            b.id: b
            for b in LibraryCatalogService.published_qs()
            .prefetch_related("translations", "assets")
            .filter(pk__in=ids)
        }
        # Preserve bookmark order; drop unpublished/archived silently.
        return [published[i] for i in ids if i in published]
