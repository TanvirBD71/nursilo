"""Safe HTTP error handlers — no secrets or stack traces (docs/22)."""
from __future__ import annotations

from django.shortcuts import render
from django.urls import reverse


def bad_request(request, exception=None):
    return render(
        request,
        "errors/400.html",
        {
            "page_heading": "Bad request",
            "error_code": "400",
        },
        status=400,
    )


def permission_denied(request, exception=None):
    recovery_href = reverse("home")
    recovery_label = "Home"
    user = getattr(request, "user", None)
    if user is not None and getattr(user, "is_authenticated", False):
        from apps.portal.destinations import authenticated_destination

        recovery_href = authenticated_destination(user)
        if recovery_href.startswith("/staff/"):
            recovery_label = "Staff console"
        elif recovery_href.startswith("/portal/"):
            recovery_label = "Go to dashboard"
        else:
            recovery_label = "Continue"
    return render(
        request,
        "errors/403.html",
        {
            "page_heading": "Access denied",
            "error_code": "403",
            "recovery_href": recovery_href,
            "recovery_label": recovery_label,
        },
        status=403,
    )


def page_not_found(request, exception=None):
    return render(
        request,
        "errors/404.html",
        {
            "page_heading": "Page not found",
            "error_code": "404",
        },
        status=404,
    )


def server_error(request):
    return render(
        request,
        "errors/500.html",
        {
            "page_heading": "Something went wrong",
            "error_code": "500",
        },
        status=500,
    )
