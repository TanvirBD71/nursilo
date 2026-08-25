"""Thin library views — services own access, content, bookmarks (docs/04, docs/15)."""
from __future__ import annotations

from django.contrib import messages
from django.http import FileResponse, Http404
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods, require_POST

from apps.library.forms import LibraryBookmarkForm, LibraryCatalogFilterForm
from apps.library.services import (
    LibraryAccessService,
    LibraryBookmarkService,
    LibraryCatalogService,
    LibraryContentService,
    LibraryPresentationService,
)
from apps.portal.access import student_portal_required
from apps.portal.services import (
    NavigationService,
    NotificationPresentationService,
    SubscriptionPresentationService,
)


def _student_context(request, *, active: str = "library", extra=None) -> dict:
    subscription = SubscriptionPresentationService.for_user(request.user)
    context = {
        "nav_items": NavigationService.items(active=active),
        "nav_active": active,
        "subscription_badge": subscription,
        "unread_notification_count": NotificationPresentationService.unread_count(
            request.user
        ),
        "layout_family": "student",
    }
    if extra:
        context.update(extra)
    return context


def _reader_context(request, *, extra=None) -> dict:
    context = {
        "nav_items": [],
        "nav_active": "library",
        "subscription_badge": SubscriptionPresentationService.for_user(request.user),
        "unread_notification_count": 0,
        "layout_family": "reader",
    }
    if extra:
        context.update(extra)
    return context


def _visible_book_or_404(user, book_id):
    book = LibraryCatalogService.get_book_any_state(book_id)
    decision = LibraryAccessService.decide_catalog_visibility(user, book)
    if LibraryAccessService.hide_as_not_found(decision) or not decision.allowed:
        raise Http404("Not found.")
    return book


def _safe_next(raw: str, fallback: str) -> str:
    value = (raw or "").strip()
    if value.startswith("/") and not value.startswith("//"):
        return value
    return fallback


@student_portal_required
@require_http_methods(["GET"])
def catalog(request):
    form = LibraryCatalogFilterForm(request.GET or None)
    if form.is_valid():
        data = form.cleaned_data
    else:
        data = {"q": "", "category": "", "access": "all", "page": 1}
    page_data = LibraryPresentationService.catalog(
        request.user,
        q=data.get("q") or "",
        category=data.get("category") or "",
        access=data.get("access") or "all",
        page=data.get("page") or 1,
    )
    context = _student_context(request, extra=page_data)
    context["filter_form"] = form
    template = "library/partials/book_list.html" if request.headers.get("HX-Request") else "library/catalog.html"
    return render(request, template, context)


@student_portal_required
@require_http_methods(["GET"])
def detail(request, book_id):
    book = _visible_book_or_404(request.user, book_id)
    page_data = LibraryPresentationService.detail(request.user, book)
    if page_data is None:
        raise Http404("Not found.")
    return render(
        request,
        "library/detail.html",
        _student_context(request, extra=page_data),
    )


@student_portal_required
@require_http_methods(["GET"])
def reader(request, book_id):
    book = _visible_book_or_404(request.user, book_id)
    page_data = LibraryPresentationService.reader(request.user, book)
    if page_data is None:
        raise Http404("Not found.")
    return render(
        request,
        "library/reader.html",
        _reader_context(request, extra=page_data),
    )


@student_portal_required
@require_http_methods(["GET"])
def bookmarks(request):
    page_data = LibraryPresentationService.bookmarks(request.user)
    return render(
        request,
        "library/bookmarks.html",
        _student_context(request, extra=page_data),
    )


@student_portal_required
@require_http_methods(["GET"])
def downloads(request):
    page_data = LibraryPresentationService.downloads(request.user)
    return render(
        request,
        "library/downloads.html",
        _student_context(request, extra=page_data),
    )


@student_portal_required
@require_POST
def bookmark_toggle(request, book_id):
    book = _visible_book_or_404(request.user, book_id)
    form = LibraryBookmarkForm(request.POST)
    next_url = ""
    if form.is_valid():
        next_url = form.cleaned_data.get("next") or ""
    result = LibraryBookmarkService.toggle(request.user, book)
    if not result.ok:
        raise Http404("Not found.")
    if result.bookmarked:
        messages.success(request, "Bookmarked.")
    else:
        messages.success(request, "Bookmark removed.")
    fallback = reverse("library:detail", kwargs={"book_id": book.id})
    return redirect(_safe_next(next_url, fallback))


@student_portal_required
@require_http_methods(["GET"])
def cover(request, book_id):
    book = _visible_book_or_404(request.user, book_id)
    resolved = LibraryContentService.resolve_cover(book)
    if resolved is None or not resolved.exists:
        raise Http404("Not found.")
    return FileResponse(
        resolved.path.open("rb"),
        content_type=resolved.content_type,
        filename=resolved.filename,
        as_attachment=False,
    )


@student_portal_required
@require_http_methods(["GET"])
def asset_stream(request, asset_id):
    asset = LibraryCatalogService.get_asset(asset_id)
    decision = LibraryAccessService.decide_asset_read(request.user, asset)
    if LibraryAccessService.hide_as_not_found(decision):
        raise Http404("Not found.")
    if not decision.allowed:
        raise Http404("Not found.")
    assert asset is not None
    resolved = LibraryContentService.resolve_asset(asset)
    if not resolved.exists:
        raise Http404("Not found.")
    return FileResponse(
        resolved.path.open("rb"),
        content_type=resolved.content_type,
        filename=resolved.filename,
        as_attachment=False,
    )


@student_portal_required
@require_http_methods(["GET"])
def asset_download(request, asset_id):
    asset = LibraryCatalogService.get_asset(asset_id)
    decision = LibraryAccessService.decide_asset_download(request.user, asset)
    if LibraryAccessService.hide_as_not_found(decision):
        raise Http404("Not found.")
    if not decision.allowed:
        # Fail closed without leaking existence of premium/protected assets via 403 body.
        raise Http404("Not found.")
    assert asset is not None
    resolved = LibraryContentService.resolve_asset(asset)
    if not resolved.exists:
        raise Http404("Not found.")
    return FileResponse(
        resolved.path.open("rb"),
        content_type=resolved.content_type,
        filename=resolved.filename,
        as_attachment=True,
    )
