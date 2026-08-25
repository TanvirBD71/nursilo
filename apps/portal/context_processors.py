"""Presentation chrome flags for authenticated shells (not authorization)."""


def chrome_flags(request):
    user = getattr(request, "user", None)
    show_staff = False
    if user is not None and getattr(user, "is_authenticated", False):
        from apps.staff.access import user_may_access_staff_console

        show_staff = user_may_access_staff_console(user)
    return {"show_staff_console_link": show_staff}
