"""Production settings for Nursilo (cPanel / Passenger)."""
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

from config.settings.base import *  # noqa: F403
from config.settings.base import BASE_DIR, env, env_bool, env_list
from config.settings.production_guards import (
    validate_csrf_trusted_origins,
    validate_production_hosts,
    validate_production_secret,
)

DEBUG = False

# Re-read from environment at production import (do not trust a stale base default).
SECRET_KEY = validate_production_secret(env("SECRET_KEY", ""))
ALLOWED_HOSTS = validate_production_hosts(env_list("ALLOWED_HOSTS", []))
CSRF_TRUSTED_ORIGINS = validate_csrf_trusted_origins(env_list("CSRF_TRUSTED_ORIGINS", []))

# Static: collectstatic target must not be the source static/ tree.
_static_root_raw = (env("STATIC_ROOT", "") or "").strip()
STATIC_ROOT = Path(_static_root_raw) if _static_root_raw else (BASE_DIR / "staticfiles")
_source_static = (BASE_DIR / "static").resolve()
if STATIC_ROOT.resolve() == _source_static:
    raise ImproperlyConfigured(
        "STATIC_ROOT must not point at the source static/ directory."
    )

# Media: disk root for storage keys. Protected books are NOT public Alias targets.
_media_root_raw = (env("MEDIA_ROOT", "") or "").strip()
MEDIA_ROOT = Path(_media_root_raw) if _media_root_raw else (BASE_DIR / "media")

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"

# Config-ready only — INTENTIONAL DEPLOYMENT DECISION (Cloudflare SSL/HSTS pending).
# Do not auto-enable; ops may set via env after edge SSL mode is confirmed.
SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", False)
SECURE_HSTS_SECONDS = int(env("SECURE_HSTS_SECONDS", "0") or "0")
SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool("SECURE_HSTS_INCLUDE_SUBDOMAINS", False)
SECURE_HSTS_PRELOAD = env_bool("SECURE_HSTS_PRELOAD", False)

# Minimal production logging — errors + security warnings; console/stream for Passenger.
# Do not log secrets, passwords, tokens, sessions, or payment credentials.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "console": {
            "format": "[{levelname}] {asctime} {name}: {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "console",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "WARNING",
    },
    "loggers": {
        "django.request": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
        "django.security": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
    },
}
