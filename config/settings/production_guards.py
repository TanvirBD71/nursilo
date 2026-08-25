"""Production fail-closed validators (safe to import without loading production settings)."""
from __future__ import annotations

from django.core.exceptions import ImproperlyConfigured


def validate_production_secret(candidate) -> str:
    """
    Fail closed: refuse missing/empty/insecure/dev-placeholder secrets.
    Error messages must never include the secret value.
    """
    value = (candidate or "").strip() if isinstance(candidate, str) else ""
    if not value:
        raise ImproperlyConfigured(
            "SECRET_KEY must be set to a strong value for production."
        )
    lowered = value.lower()
    insecure_markers = (
        "insecure-",
        "django-insecure",
        "change-me",
        "changeme",
        "dev-only",
        "unit0",
        "your-secret",
        "placeholder",
    )
    if any(marker in lowered for marker in insecure_markers):
        raise ImproperlyConfigured(
            "SECRET_KEY is insecure or a development placeholder; refuse production start."
        )
    if len(value) < 50 or len(set(value)) < 5:
        raise ImproperlyConfigured(
            "SECRET_KEY is too weak for production; refuse production start."
        )
    return value


def validate_production_hosts(hosts: list[str]) -> list[str]:
    if not hosts:
        raise ImproperlyConfigured(
            "ALLOWED_HOSTS must be set via environment for production."
        )
    return list(hosts)


def validate_csrf_trusted_origins(origins: list[str]) -> list[str]:
    if not origins:
        raise ImproperlyConfigured(
            "CSRF_TRUSTED_ORIGINS must be set via environment for production."
        )
    cleaned: list[str] = []
    for origin in origins:
        if not (origin.startswith("https://") or origin.startswith("http://")):
            raise ImproperlyConfigured(
                "CSRF_TRUSTED_ORIGINS entries must be absolute origins with http/https scheme."
            )
        cleaned.append(origin)
    return cleaned
