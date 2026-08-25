"""UNIT-7 Library & Reader Domain tests."""
from __future__ import annotations

import unittest
import uuid
from pathlib import Path

from django.conf import settings
from django.db import connection
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from apps.accounts.services import AccountService
from apps.billing.models import Subscription
from apps.common.choices import BookFormat, EditorialState, LocaleCode, SubscriptionState
from apps.engagement.models import Bookmark
from apps.library.models import Book, BookAsset, BookTranslation
from apps.library.services import (
    LibraryAccessService,
    LibraryBookmarkService,
    LibraryCatalogService,
)
from apps.portal.services import DashboardPresentationService, NavigationService


STRONG_PASSWORD = "Str0ng-Pass!Unit7"


def setUpModule():
    try:
        connection.ensure_connection()
    except Exception as exc:  # pragma: no cover
        raise unittest.SkipTest(f"PostgreSQL unavailable for UNIT-7: {exc}") from exc


def _publish(book: Book, **kwargs) -> Book:
    book.editorial_state = EditorialState.PUBLISHED
    book.is_archived = False
    for key, value in kwargs.items():
        setattr(book, key, value)
    book.save()
    return book


def _write_media(rel_key: str, content: str | bytes) -> str:
    path = Path(settings.MEDIA_ROOT) / rel_key
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, bytes):
        path.write_bytes(content)
    else:
        path.write_text(content, encoding="utf-8")
    return rel_key


def build_library_fixture(*, prefix="Unit7"):
    free_html_key = _write_media(
        f"library/{prefix.lower()}/free.html",
        f"<p>{prefix} free protected body SECRET_FREE</p>",
    )
    premium_html_key = _write_media(
        f"library/{prefix.lower()}/premium.html",
        f"<p>{prefix} premium protected body SECRET_PREMIUM</p>",
    )
    free_pdf_key = _write_media(
        f"library/{prefix.lower()}/free.pdf",
        b"%PDF-1.4 free-asset-bytes",
    )
    cover_key = _write_media(
        f"library/{prefix.lower()}/cover.png",
        b"\x89PNG\r\n\x1a\ncover",
    )

    free_book = _publish(
        Book.objects.create(
            category="Anatomy",
            author_name=f"{prefix} Free Author",
            edition="1st",
            publisher="Nursilo Press",
            cover_storage_key=cover_key,
            is_premium=False,
        )
    )
    BookTranslation.objects.create(
        book=free_book,
        locale=LocaleCode.EN,
        title=f"{prefix} Free Book",
        blurb="Free catalog blurb for nursing basics.",
    )
    free_html = BookAsset.objects.create(
        book=free_book, format=BookFormat.HTML, storage_key=free_html_key, sort_order=0
    )
    free_pdf = BookAsset.objects.create(
        book=free_book, format=BookFormat.PDF, storage_key=free_pdf_key, sort_order=1
    )

    premium_book = _publish(
        Book.objects.create(
            category="Pharmacology",
            author_name=f"{prefix} Premium Author",
            edition="2nd",
            publisher="Nursilo Premium",
            is_premium=True,
        )
    )
    BookTranslation.objects.create(
        book=premium_book,
        locale=LocaleCode.EN,
        title=f"{prefix} Premium Book",
        blurb="Premium catalog blurb teaser only.",
    )
    premium_html = BookAsset.objects.create(
        book=premium_book,
        format=BookFormat.HTML,
        storage_key=premium_html_key,
        sort_order=0,
    )

    draft = Book.objects.create(
        category="Hidden",
        author_name="Draft Author",
        editorial_state=EditorialState.DRAFT,
        is_premium=False,
    )
    BookTranslation.objects.create(
        book=draft, locale=LocaleCode.EN, title=f"{prefix} Draft Hidden Book"
    )
    draft_key = _write_media(
        f"library/{prefix.lower()}/draft.html",
        "<p>DRAFT_SECRET_BODY</p>",
    )
    draft_asset = BookAsset.objects.create(
        book=draft, format=BookFormat.HTML, storage_key=draft_key, sort_order=0
    )

    archived = Book.objects.create(
        category="Archive",
        author_name="Archived Author",
        is_premium=False,
        is_archived=True,
        editorial_state=EditorialState.ARCHIVED,
    )
    BookTranslation.objects.create(
        book=archived, locale=LocaleCode.EN, title=f"{prefix} Archived Book"
    )

    return {
        "free_book": free_book,
        "premium_book": premium_book,
        "draft": draft,
        "archived": archived,
        "free_html": free_html,
        "free_pdf": free_pdf,
        "premium_html": premium_html,
        "draft_asset": draft_asset,
    }


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"],
)
class LibraryCatalogAndReaderTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user, _ = AccountService.register(
            email="lib7@example.com",
            password=STRONG_PASSWORD,
            full_name="Library Seven",
        )
        self.fixture = build_library_fixture()
        self._login("lib7@example.com")

    def _login(self, email):
        self.client.post(
            reverse("accounts:login"),
            {"email": email, "password": STRONG_PASSWORD, "next": ""},
        )

    def test_anonymous_redirected_from_library(self):
        anon = Client()
        urls = [
            reverse("library:catalog"),
            reverse(
                "library:detail", kwargs={"book_id": self.fixture["free_book"].id}
            ),
            reverse(
                "library:reader", kwargs={"book_id": self.fixture["free_book"].id}
            ),
            reverse("library:bookmarks"),
            reverse("library:downloads"),
        ]
        for url in urls:
            resp = anon.get(url)
            self.assertEqual(resp.status_code, 302, url)
            self.assertIn("/accounts/login/", resp["Location"])

    def test_catalog_lists_published_only(self):
        resp = self.client.get(reverse("library:catalog"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Unit7 Free Book")
        self.assertContains(resp, "Unit7 Premium Book")
        self.assertNotContains(resp, "Unit7 Draft Hidden Book")
        self.assertNotContains(resp, "Unit7 Archived Book")
        self.assertNotContains(resp, "SECRET_FREE")
        self.assertNotContains(resp, "SECRET_PREMIUM")
        self.assertContains(resp, 'id="main-content"')
        self.assertContains(resp, "Skip to main content")

    def test_search_filter_and_pagination(self):
        for i in range(22):
            book = _publish(
                Book.objects.create(
                    category="Anatomy",
                    author_name=f"Pager {i}",
                    is_premium=False,
                )
            )
            BookTranslation.objects.create(
                book=book, locale=LocaleCode.EN, title=f"Unit7 Pager Book {i:02d}"
            )

        resp = self.client.get(reverse("library:catalog"), {"q": "Pager", "page": 1})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Page 1 of")
        self.assertContains(resp, "Next")

        filtered = self.client.get(
            reverse("library:catalog"),
            {"category": "Pharmacology", "access": "premium"},
        )
        self.assertContains(filtered, "Unit7 Premium Book")
        self.assertNotContains(filtered, "Unit7 Free Book")

        free_only = self.client.get(
            reverse("library:catalog"), {"access": "free", "q": "Unit7 Free"}
        )
        self.assertContains(free_only, "Unit7 Free Book")
        self.assertNotContains(free_only, "Unit7 Premium Book")

    def test_detail_metadata_without_protected_body(self):
        resp = self.client.get(
            reverse("library:detail", kwargs={"book_id": self.fixture["free_book"].id})
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Unit7 Free Book")
        self.assertContains(resp, "Free catalog blurb")
        self.assertContains(resp, "Open reader")
        self.assertNotContains(resp, "SECRET_FREE")

        premium = self.client.get(
            reverse(
                "library:detail", kwargs={"book_id": self.fixture["premium_book"].id}
            )
        )
        self.assertEqual(premium.status_code, 200)
        self.assertContains(premium, "Premium required")
        self.assertContains(premium, "Premium catalog blurb teaser")
        self.assertNotContains(premium, "SECRET_PREMIUM")
        self.assertNotContains(premium, "premium protected body")

    def test_reader_serves_entitled_html_content(self):
        resp = self.client.get(
            reverse("library:reader", kwargs={"book_id": self.fixture["free_book"].id})
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "SECRET_FREE")
        self.assertContains(resp, "Reading state: reading")
        self.assertContains(resp, "Bookmark")

    def test_empty_catalog_honest(self):
        Book.objects.all().update(
            editorial_state=EditorialState.ARCHIVED, is_archived=True
        )
        resp = self.client.get(reverse("library:catalog"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "No books found")


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"],
)
class LibraryEntitlementAndSecurityTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.free_user, _ = AccountService.register(
            email="lib7free@example.com",
            password=STRONG_PASSWORD,
            full_name="Free Lib",
        )
        self.premium_user, _ = AccountService.register(
            email="lib7prem@example.com",
            password=STRONG_PASSWORD,
            full_name="Premium Lib",
        )
        Subscription.objects.create(
            user=self.premium_user, state=SubscriptionState.PREMIUM_ACTIVE
        )
        self.fixture = build_library_fixture(prefix="Sec7")
        self.client.post(
            reverse("accounts:login"),
            {"email": "lib7free@example.com", "password": STRONG_PASSWORD, "next": ""},
        )

    def test_free_user_cannot_read_or_download_premium(self):
        reader = self.client.get(
            reverse(
                "library:reader", kwargs={"book_id": self.fixture["premium_book"].id}
            )
        )
        self.assertEqual(reader.status_code, 200)
        self.assertContains(reader, "Premium required")
        self.assertNotContains(reader, "SECRET_PREMIUM")

        dl = self.client.get(
            reverse(
                "library:asset_download",
                kwargs={"asset_id": self.fixture["premium_html"].id},
            )
        )
        self.assertEqual(dl.status_code, 404)

        stream = self.client.get(
            reverse(
                "library:asset_stream",
                kwargs={"asset_id": self.fixture["premium_html"].id},
            )
        )
        self.assertEqual(stream.status_code, 404)

        downloads_page = self.client.get(reverse("library:downloads"))
        self.assertEqual(downloads_page.status_code, 200)
        self.assertNotContains(downloads_page, "Sec7 Premium Book")
        self.assertContains(downloads_page, "Sec7 Free Book")

    def test_premium_user_can_read_and_download_premium(self):
        self.client.logout()
        self.client.post(
            reverse("accounts:login"),
            {"email": "lib7prem@example.com", "password": STRONG_PASSWORD, "next": ""},
        )
        reader = self.client.get(
            reverse(
                "library:reader", kwargs={"book_id": self.fixture["premium_book"].id}
            )
        )
        self.assertEqual(reader.status_code, 200)
        self.assertContains(reader, "SECRET_PREMIUM")

        dl = self.client.get(
            reverse(
                "library:asset_download",
                kwargs={"asset_id": self.fixture["premium_html"].id},
            )
        )
        self.assertEqual(dl.status_code, 200)
        payload = b"".join(dl.streaming_content)
        self.assertIn(b"SECRET_PREMIUM", payload)

    def test_unpublished_and_archived_hidden(self):
        for book in (self.fixture["draft"], self.fixture["archived"]):
            detail = self.client.get(
                reverse("library:detail", kwargs={"book_id": book.id})
            )
            self.assertEqual(detail.status_code, 404, book.id)
            reader = self.client.get(
                reverse("library:reader", kwargs={"book_id": book.id})
            )
            self.assertEqual(reader.status_code, 404, book.id)

        draft_dl = self.client.get(
            reverse(
                "library:asset_download",
                kwargs={"asset_id": self.fixture["draft_asset"].id},
            )
        )
        self.assertEqual(draft_dl.status_code, 404)

        # Direct storage key is not an authorized library route.
        self.assertFalse(
            reverse("library:catalog").startswith("/media/"),
        )

    def test_unknown_ids_404(self):
        missing = uuid.uuid4()
        self.assertEqual(
            self.client.get(reverse("library:detail", kwargs={"book_id": missing})).status_code,
            404,
        )
        self.assertEqual(
            self.client.get(
                reverse("library:asset_download", kwargs={"asset_id": missing})
            ).status_code,
            404,
        )

    def test_access_service_states(self):
        free = self.fixture["free_book"]
        premium = self.fixture["premium_book"]
        self.assertEqual(
            LibraryAccessService.access_state(self.free_user, free), "free"
        )
        self.assertEqual(
            LibraryAccessService.access_state(self.free_user, premium), "locked"
        )
        self.assertEqual(
            LibraryAccessService.access_state(self.premium_user, premium), "premium"
        )
        self.assertFalse(
            LibraryAccessService.decide_read(self.free_user, premium).allowed
        )
        self.assertTrue(
            LibraryAccessService.decide_download(self.premium_user, premium).allowed
        )


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"],
)
class LibraryBookmarkOwnershipTests(TestCase):
    def setUp(self):
        self.client_a = Client()
        self.client_b = Client()
        self.user_a, _ = AccountService.register(
            email="lib7a@example.com",
            password=STRONG_PASSWORD,
            full_name="Lib A",
        )
        self.user_b, _ = AccountService.register(
            email="lib7b@example.com",
            password=STRONG_PASSWORD,
            full_name="Lib B",
        )
        self.fixture = build_library_fixture(prefix="Bm7")
        self.client_a.post(
            reverse("accounts:login"),
            {"email": "lib7a@example.com", "password": STRONG_PASSWORD, "next": ""},
        )
        self.client_b.post(
            reverse("accounts:login"),
            {"email": "lib7b@example.com", "password": STRONG_PASSWORD, "next": ""},
        )

    def test_bookmark_add_remove_list_isolation(self):
        book = self.fixture["free_book"]
        toggle_url = reverse("library:bookmark_toggle", kwargs={"book_id": book.id})
        resp = self.client_a.post(toggle_url, {"next": reverse("library:bookmarks")})
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(LibraryBookmarkService.is_bookmarked(self.user_a, book))
        self.assertFalse(LibraryBookmarkService.is_bookmarked(self.user_b, book))

        list_a = self.client_a.get(reverse("library:bookmarks"))
        self.assertContains(list_a, "Bm7 Free Book")
        list_b = self.client_b.get(reverse("library:bookmarks"))
        self.assertContains(list_b, "No bookmarks yet")
        self.assertNotContains(list_b, "Bm7 Free Book")

        # Cross-user: B cannot see A's bookmark rows
        self.assertEqual(
            Bookmark.objects.filter(user=self.user_a, target_type="book").count(), 1
        )
        self.assertEqual(
            Bookmark.objects.filter(user=self.user_b, target_type="book").count(), 0
        )

        remove = self.client_a.post(toggle_url, {"next": reverse("library:bookmarks")})
        self.assertEqual(remove.status_code, 302)
        self.assertFalse(LibraryBookmarkService.is_bookmarked(self.user_a, book))

    def test_cannot_bookmark_unpublished(self):
        draft = self.fixture["draft"]
        result = LibraryBookmarkService.add(self.user_a, draft)
        self.assertFalse(result.ok)
        self.assertEqual(
            self.client_a.post(
                reverse("library:bookmark_toggle", kwargs={"book_id": draft.id})
            ).status_code,
            404,
        )

    def test_dashboard_and_nav_library_live(self):
        book = self.fixture["free_book"]
        LibraryBookmarkService.add(self.user_a, book)
        data = DashboardPresentationService.build(self.user_a)
        bookmarks = next(s for s in data["sections"] if s.key == "bookmarks")
        self.assertTrue(bookmarks.available)
        self.assertFalse(bookmarks.empty)
        self.assertEqual(bookmarks.data["items"][0]["title"], "Bm7 Free Book")

        nav = {i.key: i for i in NavigationService.items(active="library")}
        self.assertTrue(nav["library"].available)
        self.assertEqual(nav["library"].href, reverse("library:catalog"))

        catalog_count = LibraryCatalogService.published_qs().count()
        self.assertGreaterEqual(catalog_count, 2)
