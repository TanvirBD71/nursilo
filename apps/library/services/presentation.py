"""Library page presentation — server truth only (docs/15 §11, docs/14)."""
from __future__ import annotations

from dataclasses import dataclass

from django.urls import reverse

from apps.library.models import Book
from apps.library.services.access import LibraryAccessService
from apps.library.services.bookmarks import LibraryBookmarkService
from apps.library.services.catalog import LibraryCatalogService
from apps.library.services.content import LibraryContentService


@dataclass(frozen=True)
class BreadcrumbItem:
    label: str
    href: str | None = None


class LibraryPresentationService:
    @classmethod
    def locale_for(cls, user) -> str:
        return getattr(user, "ui_locale", None) or "en"

    @classmethod
    def _crumb(cls, label: str, url_name: str | None = None, **kwargs) -> BreadcrumbItem:
        if url_name is None:
            return BreadcrumbItem(label=label, href=None)
        return BreadcrumbItem(label=label, href=reverse(url_name, kwargs=kwargs))

    @classmethod
    def _book_card(cls, user, book: Book, locale: str) -> dict:
        access_state = LibraryAccessService.access_state(user, book)
        read = LibraryAccessService.decide_read(user, book)
        download = LibraryAccessService.decide_download(user, book)
        return {
            "id": book.id,
            "title": LibraryCatalogService.title_for(book, locale),
            "blurb": LibraryCatalogService.blurb_for(book, locale),
            "author_name": book.author_name,
            "edition": book.edition,
            "publisher": book.publisher,
            "category": book.category,
            "is_premium": book.is_premium,
            "access_state": access_state,
            "can_read": read.allowed,
            "can_download": download.allowed,
            "locked": access_state == "locked",
            "bookmarked": LibraryBookmarkService.is_bookmarked(user, book),
            "href": reverse("library:detail", kwargs={"book_id": book.id}),
            "reader_href": reverse("library:reader", kwargs={"book_id": book.id}),
            "cover_href": (
                reverse("library:cover", kwargs={"book_id": book.id})
                if book.cover_storage_key
                else ""
            ),
        }

    @classmethod
    def catalog(
        cls,
        user,
        *,
        q: str = "",
        category: str = "",
        access: str = "all",
        page: int = 1,
    ) -> dict:
        locale = cls.locale_for(user)
        books, total, page, page_size = LibraryCatalogService.search(
            q=q,
            category=category,
            access=access,
            page=page,
            locale=locale,
        )
        items = [cls._book_card(user, book, locale) for book in books]
        total_pages = max(1, (total + page_size - 1) // page_size) if total else 1
        categories = LibraryCatalogService.list_categories()
        return {
            "page_heading": "Library",
            "books": items,
            "is_empty": total == 0,
            "q": q or "",
            "category": category or "",
            "access": access or "all",
            "categories": categories,
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": total_pages,
            "has_prev": page > 1,
            "has_next": page < total_pages,
            "prev_page": page - 1 if page > 1 else None,
            "next_page": page + 1 if page < total_pages else None,
            "breadcrumbs": [cls._crumb("Library", "library:catalog")],
            "bookmarks_href": reverse("library:bookmarks"),
            "downloads_href": reverse("library:downloads"),
        }

    @classmethod
    def detail(cls, user, book: Book) -> dict | None:
        visibility = LibraryAccessService.decide_catalog_visibility(user, book)
        if LibraryAccessService.hide_as_not_found(visibility):
            return None
        if not visibility.allowed:
            return None
        locale = cls.locale_for(user)
        card = cls._book_card(user, book, locale)
        read = LibraryAccessService.decide_read(user, book)
        download = LibraryAccessService.decide_download(user, book)
        assets = []
        for asset in LibraryCatalogService.ordered_assets(book):
            assets.append(
                {
                    "id": asset.id,
                    "format": asset.format,
                    "can_download": download.allowed,
                    "download_href": reverse(
                        "library:asset_download", kwargs={"asset_id": asset.id}
                    ),
                }
            )
        return {
            "page_heading": card["title"],
            "book": card,
            "blurb": card["blurb"],
            "assets": assets,
            "assets_empty": len(assets) == 0,
            "can_read": read.allowed,
            "can_download": download.allowed,
            "locked": read.reason == "premium_required",
            "lock_message": (
                "Premium book. Upgrade your subscription to read or download."
                if read.reason == "premium_required"
                else ""
            ),
            "bookmarked": card["bookmarked"],
            # Detail never includes protected reader body.
            "reader_body": "",
            "breadcrumbs": [
                cls._crumb("Library", "library:catalog"),
                cls._crumb(card["title"]),
            ],
            "permitted_actions": {
                "read": read.allowed,
                "download": download.allowed,
                "bookmark": True,
                "upgrade": read.reason == "premium_required",
            },
        }

    @classmethod
    def reader(cls, user, book: Book) -> dict | None:
        visibility = LibraryAccessService.decide_catalog_visibility(user, book)
        if LibraryAccessService.hide_as_not_found(visibility):
            return None
        locale = cls.locale_for(user)
        title = LibraryCatalogService.title_for(book, locale)
        read = LibraryAccessService.decide_read(user, book)
        asset = LibraryCatalogService.primary_readable_asset(book)
        content = LibraryContentService.reader_payload(user, book, asset)
        download = LibraryAccessService.decide_download(user, book)
        stream_href = ""
        if content.get("stream_available") and asset is not None:
            stream_href = reverse(
                "library:asset_stream", kwargs={"asset_id": asset.id}
            )
        return {
            "page_heading": title,
            "book_id": book.id,
            "title": title,
            "author_name": book.author_name,
            "is_premium": book.is_premium,
            "allowed": read.allowed,
            "locked": read.reason == "premium_required",
            "lock_message": (
                "Premium book. Upgrade your subscription to continue reading."
                if read.reason == "premium_required"
                else ""
            ),
            "format": content.get("format") or "",
            "body_text": content.get("body_text") or "",
            "body_html": content.get("body_html") or "",
            "stream_href": stream_href,
            "missing_file": content.get("missing_file", False),
            "bookmarked": LibraryBookmarkService.is_bookmarked(user, book),
            "can_download": download.allowed,
            "download_href": (
                reverse("library:asset_download", kwargs={"asset_id": asset.id})
                if download.allowed and asset is not None
                else ""
            ),
            "detail_href": reverse("library:detail", kwargs={"book_id": book.id}),
            "catalog_href": reverse("library:catalog"),
            "bookmark_href": reverse(
                "library:bookmark_toggle", kwargs={"book_id": book.id}
            ),
            "reading_state": "reading" if read.allowed else "locked",
        }

    @classmethod
    def bookmarks(cls, user) -> dict:
        locale = cls.locale_for(user)
        books = LibraryBookmarkService.list_books_for_user(user)
        items = [cls._book_card(user, book, locale) for book in books]
        return {
            "page_heading": "Library bookmarks",
            "books": items,
            "is_empty": len(items) == 0,
            "breadcrumbs": [
                cls._crumb("Library", "library:catalog"),
                cls._crumb("Bookmarks"),
            ],
        }

    @classmethod
    def downloads(cls, user) -> dict:
        """Books the learner is currently entitled to download."""
        locale = cls.locale_for(user)
        books = list(
            LibraryCatalogService.published_qs()
            .prefetch_related("translations", "assets")
            .order_by("category", "created_at")
        )
        items = []
        for book in books:
            download = LibraryAccessService.decide_download(user, book)
            if not download.allowed:
                continue
            card = cls._book_card(user, book, locale)
            assets = [
                {
                    "id": asset.id,
                    "format": asset.format,
                    "download_href": reverse(
                        "library:asset_download", kwargs={"asset_id": asset.id}
                    ),
                }
                for asset in LibraryCatalogService.ordered_assets(book)
            ]
            if not assets:
                continue
            card["assets"] = assets
            items.append(card)
        return {
            "page_heading": "Downloads",
            "books": items,
            "is_empty": len(items) == 0,
            "total_entitled": len(items),
            "breadcrumbs": [
                cls._crumb("Library", "library:catalog"),
                cls._crumb("Downloads"),
            ],
        }

    @classmethod
    def dashboard_bookmarks(cls, user) -> dict:
        locale = cls.locale_for(user)
        books = LibraryBookmarkService.list_books_for_user(user)[:5]
        items = [
            {
                "id": book.id,
                "title": LibraryCatalogService.title_for(book, locale),
                "href": reverse("library:detail", kwargs={"book_id": book.id}),
            }
            for book in books
        ]
        return {
            "items": items,
            "empty": len(items) == 0,
            "href": reverse("library:bookmarks"),
        }
