"""Open-redirect prevention helpers for auth flows."""
from __future__ import annotations

from urllib.parse import urlparse

from django.conf import settings
from django.utils.http import url_has_allowed_host_and_scheme


def safe_redirect_url(candidate: str | None, *, fallback: str = "/") -> str:
    """Return candidate only when it is a same-host relative/absolute path."""
    if not candidate:
        return fallback
    allowed_hosts = {request_host for request_host in settings.ALLOWED_HOSTS if request_host}
    # Empty ALLOWED_HOSTS with DEBUG can appear in some test setups — still require relative.
    if url_has_allowed_host_and_scheme(
        url=candidate,
        allowed_hosts=allowed_hosts or None,
        require_https=False,
    ):
        return candidate
    return fallback


def safe_back_url(request, *, fallback: str) -> str:
    """
    Same-host previous page for Nursilo Back controls.

    Ignores the current path (no self-loop) and unsafe/external referers.
    Falls back to a sensible parent rather than a generic browser control.
    """
    referer = request.META.get("HTTP_REFERER") or ""
    if not referer:
        return fallback
    parsed = urlparse(referer)
    path = parsed.path or ""
    if not path:
        return fallback
    current = (request.path or "").rstrip("/") or "/"
    candidate_path = path.rstrip("/") or "/"
    if candidate_path == current:
        return fallback
    candidate = path
    if parsed.query:
        candidate = f"{path}?{parsed.query}"
    return safe_redirect_url(candidate, fallback=fallback)
