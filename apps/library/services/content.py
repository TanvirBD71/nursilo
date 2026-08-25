"""Mediated book asset storage access (docs/06 §15, docs/24)."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from django.conf import settings

from apps.common.choices import BookFormat
from apps.library.models import Book, BookAsset
from apps.library.services.access import LibraryAccessService


@dataclass(frozen=True)
class ResolvedAssetFile:
    path: Path
    content_type: str
    filename: str
    exists: bool


class LibraryContentService:
    """
    Resolve storage_key to filesystem paths under MEDIA_ROOT.
    Callers must already have AccessDecision.allowed — this never grants access.
    """

    CONTENT_TYPES = {
        BookFormat.PDF: "application/pdf",
        BookFormat.EPUB: "application/epub+zip",
        BookFormat.HTML: "text/html; charset=utf-8",
        BookFormat.IMAGE: "application/octet-stream",
    }
    IMAGE_SUFFIX_TYPES = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".svg": "image/svg+xml",
    }

    @classmethod
    def media_root(cls) -> Path:
        root = getattr(settings, "MEDIA_ROOT", None)
        if root is None:
            return Path(settings.BASE_DIR) / "media"
        return Path(root)

    @classmethod
    def _safe_resolve(cls, storage_key: str) -> Path | None:
        key = (storage_key or "").strip().replace("\\", "/")
        if not key or key.startswith("/") or ".." in key.split("/"):
            return None
        root = cls.media_root().resolve()
        candidate = (root / key).resolve()
        try:
            candidate.relative_to(root)
        except ValueError:
            return None
        return candidate

    @classmethod
    def resolve_asset(cls, asset: BookAsset) -> ResolvedAssetFile:
        path = cls._safe_resolve(asset.storage_key)
        filename = Path(asset.storage_key).name if asset.storage_key else "asset"
        content_type = cls.CONTENT_TYPES.get(asset.format, "application/octet-stream")
        if asset.format == BookFormat.IMAGE and path is not None:
            content_type = cls.IMAGE_SUFFIX_TYPES.get(
                path.suffix.lower(), content_type
            )
        exists = bool(path and path.is_file())
        return ResolvedAssetFile(
            path=path if path is not None else Path(),
            content_type=content_type,
            filename=filename,
            exists=exists,
        )

    @classmethod
    def resolve_cover(cls, book: Book) -> ResolvedAssetFile | None:
        key = (book.cover_storage_key or "").strip()
        if not key:
            return None
        path = cls._safe_resolve(key)
        filename = Path(key).name
        content_type = "application/octet-stream"
        if path is not None:
            content_type = cls.IMAGE_SUFFIX_TYPES.get(
                path.suffix.lower(), content_type
            )
        return ResolvedAssetFile(
            path=path if path is not None else Path(),
            content_type=content_type,
            filename=filename,
            exists=bool(path and path.is_file()),
        )

    @classmethod
    def read_text_asset(cls, asset: BookAsset) -> str | None:
        resolved = cls.resolve_asset(asset)
        if not resolved.exists:
            return None
        try:
            return resolved.path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            return None

    @classmethod
    def reader_payload(cls, user, book: Book, asset: BookAsset | None) -> dict:
        """
        Authorized reader content payload. Empty body when denied or missing file.
        Never returns protected content for unauthorized users.
        """
        decision = LibraryAccessService.decide_read(user, book)
        if not decision.allowed:
            return {
                "allowed": False,
                "reason": decision.reason,
                "format": asset.format if asset else "",
                "body_text": "",
                "body_html": "",
                "stream_available": False,
                "asset_id": asset.id if asset else None,
                "missing_file": False,
            }
        if asset is None:
            return {
                "allowed": True,
                "reason": "",
                "format": "",
                "body_text": "",
                "body_html": "",
                "stream_available": False,
                "asset_id": None,
                "missing_file": True,
            }
        resolved = cls.resolve_asset(asset)
        body_text = ""
        body_html = ""
        if asset.format == BookFormat.HTML and resolved.exists:
            raw = cls.read_text_asset(asset) or ""
            # Prefer plain-text safe display when content has no markup.
            if "<" in raw and ">" in raw:
                body_html = raw
            else:
                body_text = raw
        return {
            "allowed": True,
            "reason": "",
            "format": asset.format,
            "body_text": body_text,
            "body_html": body_html,
            "stream_available": resolved.exists
            and asset.format in {BookFormat.PDF, BookFormat.EPUB, BookFormat.IMAGE},
            "asset_id": asset.id,
            "missing_file": not resolved.exists,
        }
