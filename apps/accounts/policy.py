"""Auth/session policy defaults aligned to docs/07 (configurable where noted)."""
from datetime import timedelta

from django.conf import settings

# Concurrent sessions (docs/07 §4)
MAX_CONCURRENT_SESSIONS = getattr(settings, "NURSILO_MAX_CONCURRENT_SESSIONS", 3)
# "terminate_oldest" | "reject"
FOURTH_LOGIN_BEHAVIOR = getattr(
    settings, "NURSILO_FOURTH_LOGIN_BEHAVIOR", "terminate_oldest"
)

# Timeouts (docs/07 §10)
SESSION_IDLE_TIMEOUT = getattr(
    settings, "NURSILO_SESSION_IDLE_TIMEOUT", timedelta(minutes=30)
)
SESSION_ABSOLUTE_TIMEOUT = getattr(
    settings, "NURSILO_SESSION_ABSOLUTE_TIMEOUT", timedelta(days=30)
)
# Remember-me idle is longer but never exceeds the absolute bound already permitted.
SESSION_REMEMBER_IDLE_TIMEOUT = getattr(
    settings, "NURSILO_SESSION_REMEMBER_IDLE_TIMEOUT", SESSION_ABSOLUTE_TIMEOUT
)

# Login lockout example thresholds (docs/07 §7.2) — Super Admin configurable later
FAILED_LOGIN_THRESHOLD = getattr(settings, "NURSILO_FAILED_LOGIN_THRESHOLD", 5)
ACCOUNT_LOCK_DURATION = getattr(
    settings, "NURSILO_ACCOUNT_LOCK_DURATION", timedelta(minutes=15)
)

# Tokens (docs/07 §16, §20) — short-lived, single-use
PASSWORD_RESET_TOKEN_TTL = getattr(
    settings, "NURSILO_PASSWORD_RESET_TOKEN_TTL", timedelta(hours=1)
)
EMAIL_VERIFICATION_TOKEN_TTL = getattr(
    settings, "NURSILO_EMAIL_VERIFICATION_TOKEN_TTL", timedelta(hours=24)
)

# Rate limits (foundation)
PASSWORD_RESET_REQUEST_COOLDOWN = getattr(
    settings, "NURSILO_PASSWORD_RESET_COOLDOWN", timedelta(minutes=1)
)
EMAIL_VERIFICATION_RESEND_COOLDOWN = getattr(
    settings, "NURSILO_EMAIL_VERIFICATION_RESEND_COOLDOWN", timedelta(minutes=1)
)

# Re-authentication window for sensitive actions (docs/07 §26B)
REAUTH_WINDOW = getattr(settings, "NURSILO_REAUTH_WINDOW", timedelta(minutes=10))

# Password policy minimum length (docs/07 §8) — not trivially short
PASSWORD_MIN_LENGTH = getattr(settings, "NURSILO_PASSWORD_MIN_LENGTH", 10)

# Session / reauth keys stored in Django session (never log these as secrets)
SESSION_TRACKING_KEY = "nursilo_user_session_id"
REAUTH_AT_SESSION_KEY = "nursilo_reauth_at"

# Generic public messages (anti-enumeration)
GENERIC_PASSWORD_RESET_MESSAGE = (
    "If an account exists for that email, password reset instructions have been sent."
)
GENERIC_VERIFICATION_RESEND_MESSAGE = (
    "If your account needs verification, a new email has been sent."
)
GENERIC_AUTH_FAILURE_MESSAGE = "Invalid email or password."
