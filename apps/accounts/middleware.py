"""Server-authoritative session idle/absolute enforcement (docs/07)."""
from __future__ import annotations

from django.contrib.auth import logout as django_logout
from django.shortcuts import redirect
from django.urls import reverse

from apps.accounts.policy import SESSION_TRACKING_KEY
from apps.accounts.services.sessions import SessionService


class UserSessionMiddleware:
    """
    Touch tracked UserSession rows; expire idle/absolute sessions server-side.
    Does not invent client-side session authority. Admin logins without a
    tracked UserSession are left alone.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if user is not None and getattr(user, "is_authenticated", False):
            tracked = request.session.get(SESSION_TRACKING_KEY)
            current = SessionService.get_current(request) if tracked else None
            expired = False
            if tracked and current is None:
                django_logout(request)
                expired = True
            elif current is not None:
                if SessionService.touch(current) is None:
                    django_logout(request)
                    expired = True
            if expired and not self._is_auth_path(request.path):
                login_url = reverse("accounts:login")
                return redirect(f"{login_url}?reason=session_expired")
        return self.get_response(request)

    @staticmethod
    def _is_auth_path(path: str) -> bool:
        return path.startswith("/accounts/") or path.startswith("/health/")
