"""Server-side student portal access helpers (docs/03, docs/07, docs/24)."""
from __future__ import annotations

from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

from apps.common.choices import RoleCode
from apps.rbac.services import AccessControlService


def user_may_access_student_portal(user) -> bool:
    """
    Own-account student portal surfaces require an authenticated active user
    with Student role (or account.view_own). Staff-only accounts without
    Student are fail-closed here — use the staff console instead.
    """
    if user is None or not getattr(user, "is_authenticated", False):
        return False
    if not getattr(user, "is_active", False):
        return False
    if AccessControlService.has_permission(user, "account.view_own"):
        return True
    return AccessControlService.has_role(user, RoleCode.STUDENT)


def student_portal_required(view_func):
    """login_required + server-side student portal boundary."""

    @login_required
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not user_may_access_student_portal(request.user):
            raise PermissionDenied(
                "Student portal access requires a student account."
            )
        return view_func(request, *args, **kwargs)

    return _wrapped
