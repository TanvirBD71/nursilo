"""Role-aware post-auth destinations — presentation routing only (not authorization)."""
from __future__ import annotations

from django.urls import reverse

from apps.portal.access import user_may_access_student_portal
from apps.rbac.services import AccessControlService
from apps.staff.access import user_may_access_staff_console


def authenticated_destination(user) -> str:
    """
    Preferred app home after sign-in when no safe ``next`` is provided.

    Staff-only accounts → staff console; student portal users → portal;
    dual-capable staff who also have student access → portal (staff remains
    reachable at /staff/). Authorization is enforced by view decorators.
    """
    if user is None or not getattr(user, "is_authenticated", False):
        return reverse("home")

    staff_ok = user_may_access_staff_console(user) or AccessControlService.is_staff_user(
        user
    )
    student_ok = user_may_access_student_portal(user)

    if staff_ok and not student_ok:
        return reverse("staff:dashboard")
    if student_ok:
        return reverse("portal:dashboard")
    if staff_ok:
        return reverse("staff:dashboard")
    return reverse("portal:dashboard")
