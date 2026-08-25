"""Server-side library access decisions (docs/05 §10, docs/09 §12, docs/24)."""
from __future__ import annotations

from dataclasses import dataclass

from apps.common.choices import EditorialState
from apps.entitlements.services import EntitlementService
from apps.library.models import Book, BookAsset


@dataclass(frozen=True)
class AccessDecision:
    allowed: bool
    reason: str = ""
    # not_found | unpublished | archived | premium_required | forbidden


class LibraryAccessService:
    """
    Fail-closed learner visibility and read/download gates.

    Download authorization mirrors read: Published + non-archived + entitlement
    (docs/05 §10 invariants; FEAT-LIB-04). No per-book download flag or
    access-request workflow exists in approved docs — those are not invented here.
    Storage keys are never authorization (docs/06 §15, docs/24).
    Premium evaluation is owned by EntitlementService (UNIT-8) — not a second system.
    """

    @classmethod
    def user_is_premium(cls, user) -> bool:
        if user is None or not getattr(user, "is_authenticated", False):
            return False
        return EntitlementService.is_premium(user)

    @classmethod
    def is_learner_visible_book(cls, book: Book | None) -> bool:
        if book is None:
            return False
        if getattr(book, "is_archived", True):
            return False
        return getattr(book, "editorial_state", None) == EditorialState.PUBLISHED

    @classmethod
    def decide_catalog_visibility(cls, user, book: Book | None) -> AccessDecision:
        """Published books may appear in catalog; body still gated separately."""
        if book is None:
            return AccessDecision(False, "not_found")
        if user is None or not getattr(user, "is_authenticated", False):
            return AccessDecision(False, "forbidden")
        if getattr(book, "is_archived", False):
            return AccessDecision(False, "archived")
        if getattr(book, "editorial_state", None) != EditorialState.PUBLISHED:
            return AccessDecision(False, "unpublished")
        return AccessDecision(True)

    @classmethod
    def decide_read(cls, user, book: Book | None) -> AccessDecision:
        base = cls.decide_catalog_visibility(user, book)
        if not base.allowed:
            return base
        assert book is not None
        if book.is_premium and not cls.user_is_premium(user):
            return AccessDecision(False, "premium_required")
        return AccessDecision(True)

    @classmethod
    def decide_download(cls, user, book: Book | None) -> AccessDecision:
        """Same gate as read — entitlement + Published (docs/05 §10)."""
        return cls.decide_read(user, book)

    @classmethod
    def decide_asset_read(cls, user, asset: BookAsset | None) -> AccessDecision:
        if asset is None:
            return AccessDecision(False, "not_found")
        return cls.decide_read(user, asset.book)

    @classmethod
    def decide_asset_download(cls, user, asset: BookAsset | None) -> AccessDecision:
        if asset is None:
            return AccessDecision(False, "not_found")
        return cls.decide_download(user, asset.book)

    @classmethod
    def hide_as_not_found(cls, decision: AccessDecision) -> bool:
        return decision.reason in {"not_found", "unpublished", "archived"}

    @classmethod
    def access_state(cls, user, book: Book) -> str:
        """
        Presentation access state for entitled catalog surfaces.
        free | premium | locked | unavailable
        """
        visibility = cls.decide_catalog_visibility(user, book)
        if not visibility.allowed:
            return "unavailable"
        if book.is_premium and not cls.user_is_premium(user):
            return "locked"
        if book.is_premium:
            return "premium"
        return "free"
