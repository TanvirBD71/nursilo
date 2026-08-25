"""Sensitive-action re-authentication (docs/07 §26B) — server decides."""
from __future__ import annotations

from django.utils import timezone
from django.utils.dateparse import parse_datetime

from apps.accounts.exceptions import ReauthenticationFailed, ReauthenticationRequired
from apps.accounts.policy import REAUTH_AT_SESSION_KEY, REAUTH_WINDOW


# Actions that require recent password confirmation
SENSITIVE_ACTIONS = frozenset(
    {
        "change_password",
        "change_email",
        "view_devices",
        "logout_all_devices",
        "purchase_premium",
    }
)


class ReauthService:
    @staticmethod
    def confirm_password(*, user, password: str, request) -> None:
        if not user.check_password(password):
            raise ReauthenticationFailed()
        request.session[REAUTH_AT_SESSION_KEY] = timezone.now().isoformat()
        request.session.modified = True

    @staticmethod
    def is_fresh(request, *, now=None) -> bool:
        now = now or timezone.now()
        raw = request.session.get(REAUTH_AT_SESSION_KEY)
        if not raw:
            return False
        confirmed_at = parse_datetime(raw) if isinstance(raw, str) else raw
        if confirmed_at is None:
            return False
        if timezone.is_naive(confirmed_at):
            confirmed_at = timezone.make_aware(confirmed_at, timezone.get_current_timezone())
        return (now - confirmed_at) <= REAUTH_WINDOW

    @classmethod
    def require_fresh(cls, request, *, action: str | None = None) -> None:
        if action and action not in SENSITIVE_ACTIONS:
            return
        if not cls.is_fresh(request):
            raise ReauthenticationRequired()

    @staticmethod
    def clear(request) -> None:
        if REAUTH_AT_SESSION_KEY in request.session:
            del request.session[REAUTH_AT_SESSION_KEY]
            request.session.modified = True
