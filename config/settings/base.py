"""Shared Django settings for Nursilo (env-driven; no hard-coded secrets)."""
from pathlib import Path
import os

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env")


def env(key, default=None):
    return os.environ.get(key, default)


def env_bool(key, default=False):
    value = os.environ.get(key)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_list(key, default=None):
    value = os.environ.get(key)
    if not value:
        return list(default or [])
    return [item.strip() for item in value.split(",") if item.strip()]


SECRET_KEY = env("SECRET_KEY", "insecure-unit0-dev-only-change-me")
DEBUG = env_bool("DEBUG", False)
ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", ["localhost", "127.0.0.1"])
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS", [])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",
    # Domain apps (docs/04) — models landed in UNIT-1
    "apps.accounts",
    "apps.rbac",
    "apps.entitlements",
    "apps.billing",
    "apps.learning",
    "apps.assessment",
    "apps.analytics",
    "apps.library",
    "apps.search",
    "apps.engagement",
    "apps.notifications",
    "apps.cms",
    "apps.audit",
    "apps.platform",
    "apps.portal",
    "apps.staff",
]

# Custom user must be set before first domain migrations (docs/05 Identity).
AUTH_USER_MODEL = "accounts.UserAccount"

TEST_RUNNER = "config.test_runner.NursiloDiscoverRunner"

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "apps.accounts.middleware.UserSessionMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.portal.context_processors.chrome_flags",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# PostgreSQL — engine configured; connectivity not verified in UNIT-0
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("DB_NAME", "nursilo"),
        "USER": env("DB_USER", "nursilo"),
        "PASSWORD": env("DB_PASSWORD", ""),
        "HOST": env("DB_HOST", "127.0.0.1"),
        "PORT": env("DB_PORT", "5432"),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "apps.accounts.validators.MinimumLengthValidator"},
    {"NAME": "apps.accounts.validators.ComplexityValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Auth URLs / redirects (docs/07 — no open redirects in views)
LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "portal:dashboard"
LOGOUT_REDIRECT_URL = "accounts:login"

# Static assets (design tokens / portal shell — docs/12–17)
# STATIC_ROOT is collectstatic output (default: BASE_DIR/staticfiles) — never the source tree.
STATIC_URL = env("STATIC_URL", "/static/")
STATICFILES_DIRS = [BASE_DIR / "static"]
_static_root = (env("STATIC_ROOT", "") or "").strip()
STATIC_ROOT = Path(_static_root) if _static_root else (BASE_DIR / "staticfiles")

# Mediated media storage keys (docs/06 §15) — never authorization by themselves.
# Protected library assets are served only via library views; do not public-map MEDIA_ROOT.
MEDIA_URL = env("MEDIA_URL", "/media/")
_media_root = (env("MEDIA_ROOT", "") or "").strip()
MEDIA_ROOT = Path(_media_root) if _media_root else (BASE_DIR / "media")

LANGUAGE_CODE = "en"
TIME_ZONE = "Asia/Dhaka"
USE_I18N = True
USE_TZ = True

# Session cookie posture (docs/07 §3 / §15). Secure flag is env/production-aware.
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = env_bool("SESSION_COOKIE_SECURE", False)
CSRF_COOKIE_SECURE = env_bool("CSRF_COOKIE_SECURE", False)

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Email (console locally; SMTP when EMAIL_HOST is set)
EMAIL_HOST = env("EMAIL_HOST", "")
EMAIL_PORT = int(env("EMAIL_PORT", "587") or "587")
EMAIL_HOST_USER = env("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", True)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", "noreply@example.com")
EMAIL_BACKEND = env(
    "EMAIL_BACKEND",
    (
        "django.core.mail.backends.smtp.EmailBackend"
        if EMAIL_HOST
        else "django.core.mail.backends.console.EmailBackend"
    ),
)

# --- UNIT-8 Billing / SSLCommerz (sandbox only; credentials via env) ---
# Authoritative V1 plan defaults (override without rewriting billing workflows).
NURSILO_PLAN_ANNUAL_PREMIUM_CODE = env("NURSILO_PLAN_ANNUAL_PREMIUM_CODE", "annual_premium")
NURSILO_PLAN_ANNUAL_PREMIUM_NAME = env("NURSILO_PLAN_ANNUAL_PREMIUM_NAME", "Annual Premium")
NURSILO_PLAN_ANNUAL_PREMIUM_AMOUNT = env("NURSILO_PLAN_ANNUAL_PREMIUM_AMOUNT", "199")
NURSILO_PLAN_ANNUAL_PREMIUM_DURATION_DAYS = int(
    env("NURSILO_PLAN_ANNUAL_PREMIUM_DURATION_DAYS", "365") or "365"
)

# Payment provider: "sslcommerz" (default) or "fake" (tests only).
NURSILO_PAYMENT_PROVIDER = env("NURSILO_PAYMENT_PROVIDER", "sslcommerz")

# SSLCommerz — sandbox only for V1. Never log or commit these values.
SSLCOMMERZ_STORE_ID = env("SSLCOMMERZ_STORE_ID", "")
SSLCOMMERZ_STORE_PASSWD = env("SSLCOMMERZ_STORE_PASSWD", "")
# V1 gate: sandbox only. Live endpoints are not selected regardless of env.
SSLCOMMERZ_SANDBOX = True
SSLCOMMERZ_SESSION_URL = env(
    "SSLCOMMERZ_SESSION_URL",
    "https://sandbox.sslcommerz.com/gwprocess/v4/api.php",
)
SSLCOMMERZ_VALIDATION_URL = env(
    "SSLCOMMERZ_VALIDATION_URL",
    "https://sandbox.sslcommerz.com/validator/api/validationserverAPI.php",
)
