"""Server-side staff console access helpers (docs/03, docs/07, docs/24)."""
from __future__ import annotations

from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

from apps.rbac.services import AccessControlService


def user_may_access_staff_console(user) -> bool:
    if user is None or not getattr(user, "is_authenticated", False):
        return False
    if not getattr(user, "is_active", False):
        return False
    if AccessControlService.has_permission(user, "staff.access"):
        return True
    return AccessControlService.is_staff_user(user)


def staff_console_required(view_func):
    """login_required + server-side staff boundary. Hidden UI ≠ authZ."""

    @login_required
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not user_may_access_staff_console(request.user):
            raise PermissionDenied("Staff console access denied.")
        return view_func(request, *args, **kwargs)

    return _wrapped


def permission_required(permission: str):
    """Decorator: staff console + named permission (fail closed)."""

    def decorator(view_func):
        @staff_console_required
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if not AccessControlService.has_permission(request.user, permission):
                raise PermissionDenied("Permission denied.")
            return view_func(request, *args, **kwargs)

        return _wrapped

    return decorator


def any_permission_required(*permissions: str):
    def decorator(view_func):
        @staff_console_required
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if not any(
                AccessControlService.has_permission(request.user, p) for p in permissions
            ):
                raise PermissionDenied("Permission denied.")
            return view_func(request, *args, **kwargs)

        return _wrapped

    return decorator
