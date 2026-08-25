"""Published book catalog queries (docs/05 §10, docs/09 §12)."""
from __future__ import annotations

from typing import Iterable

from django.db.models import Prefetch, Q, QuerySet

from apps.common.choices import EditorialState, LocaleCode
from apps.library.models import Book, BookAsset, BookTranslation


class LibraryCatalogService:
    """Read-side catalog helpers. Learners see Published + non-archived only."""

    FALLBACK_LOCALES = (LocaleCode.EN, LocaleCode.BN)
    DEFAULT_PAGE_SIZE = 20
    MAX_PAGE_SIZE = 50

    @classmethod
    def published_qs(cls) -> QuerySet:
        return Book.objects.filter(
            editorial_state=EditorialState.PUBLISHED,
            is_archived=False,
        )

    @classmethod
    def resolve_translation(cls, translations: Iterable, locale: str):
        by_locale = {t.locale: t for t in translations}
        if locale in by_locale:
            return by_locale[locale]
        for code in cls.FALLBACK_LOCALES:
            if code in by_locale:
                return by_locale[code]
        return next(iter(by_locale.values()), None)

    @classmethod
    def title_for(cls, book: Book, locale: str, *, blank: str = "Untitled book") -> str:
        translation = cls.resolve_translation(book.translations.all(), locale)
        if translation is None:
            return blank
        return translation.title or blank

    @classmethod
    def blurb_for(cls, book: Book, locale: str) -> str:
        translation = cls.resolve_translation(book.translations.all(), locale)
        if translation is None:
            return ""
        return translation.blurb or ""

    @classmethod
    def _prefetch(cls) -> Prefetch:
        return Prefetch(
            "translations",
            queryset=BookTranslation.objects.order_by("locale"),
        )

    @classmethod
    def list_categories(cls) -> list[str]:
        rows = (
            cls.published_qs()
            .exclude(category="")
            .order_by("category")
            .values_list("category", flat=True)
            .distinct()
        )
        return list(rows)

    @classmethod
    def search(
        cls,
        *,
        q: str = "",
        category: str = "",
        access: str = "all",
        page: int = 1,
        page_size: int = DEFAULT_PAGE_SIZE,
        locale: str = LocaleCode.EN,
    ) -> tuple[list[Book], int, int, int]:
        """
        Server-side search/filter + pagination.
        access: all | free | premium (catalog flags only — not entitlement grant)
        Returns (books, total, page, page_size).
        """
        try:
            page = max(1, int(page))
        except (TypeError, ValueError):
            page = 1
        try:
            page_size = min(cls.MAX_PAGE_SIZE, max(1, int(page_size)))
        except (TypeError, ValueError):
            page_size = cls.DEFAULT_PAGE_SIZE

        qs = cls.published_qs().prefetch_related(cls._prefetch(), "assets")
        query = (q or "").strip()
        if query:
            qs = qs.filter(
                Q(translations__title__icontains=query)
                | Q(translations__blurb__icontains=query)
                | Q(author_name__icontains=query)
                | Q(publisher__icontains=query)
                | Q(category__icontains=query)
            ).distinct()
        cat = (category or "").strip()
        if cat:
            qs = qs.filter(category=cat)
        access_key = (access or "all").strip().lower()
        if access_key == "free":
            qs = qs.filter(is_premium=False)
        elif access_key == "premium":
            qs = qs.filter(is_premium=True)

        # Stable ordering: title for locale when available, else created_at
        qs = qs.order_by("category", "created_at")
        total = qs.count()
        start = (page - 1) * page_size
        books = list(qs[start : start + page_size])
        # Touch locale for callers that resolve titles (kept for API symmetry)
        _ = locale
        return books, total, page, page_size

    @classmethod
    def get_published_book(cls, book_id) -> Book | None:
        return (
            cls.published_qs()
            .prefetch_related(cls._prefetch(), "assets", "courses")
            .filter(pk=book_id)
            .first()
        )

    @classmethod
    def get_book_any_state(cls, book_id) -> Book | None:
        """Staff/debug only — learner views must not use this for discovery."""
        return (
            Book.objects.prefetch_related(cls._prefetch(), "assets")
            .filter(pk=book_id)
            .first()
        )

    @classmethod
    def get_asset(cls, asset_id) -> BookAsset | None:
        return (
            BookAsset.objects.select_related("book")
            .prefetch_related("book__translations")
            .filter(pk=asset_id)
            .first()
        )

    @classmethod
    def ordered_assets(cls, book: Book) -> list[BookAsset]:
        return list(book.assets.order_by("sort_order", "created_at"))

    @classmethod
    def primary_readable_asset(cls, book: Book) -> BookAsset | None:
        assets = cls.ordered_assets(book)
        if not assets:
            return None
        # Prefer HTML for server-rendered reader, then others.
        for fmt in ("html", "image", "pdf", "epub"):
            for asset in assets:
                if asset.format == fmt:
                    return asset
        return assets[0]
