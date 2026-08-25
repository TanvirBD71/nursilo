"""Thin student portal views — services own presentation assembly (docs/04, docs/15)."""
from __future__ import annotations

from django.contrib import messages
from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods, require_POST

from apps.accounts.models import AcademicProfile
from apps.accounts.services import AccountService
from apps.common.choices import LocaleCode
from apps.portal.access import student_portal_required
from apps.portal.forms import AcademicProfileForm, ProfileEditForm
from apps.portal.services import (
    DashboardPresentationService,
    NavigationService,
    NotificationPresentationService,
    SubscriptionPresentationService,
)

FEATURE_LABELS = {
    "learn": "Learning",
    "practice": "Practice",
    "exams": "Exams",
    "library": "Library",
    "search": "Search",
}


def _student_context(request, *, active: str, extra=None) -> dict:
    subscription = SubscriptionPresentationService.for_user(request.user)
    context = {
        "nav_items": NavigationService.items(active=active),
        "nav_active": active,
        "subscription_badge": subscription,
        "unread_notification_count": NotificationPresentationService.unread_count(
            request.user
        ),
        "layout_family": "student",
    }
    if extra:
        context.update(extra)
    return context


@student_portal_required
@require_http_methods(["GET"])
def dashboard(request):
    dashboard_data = DashboardPresentationService.build(request.user)
    return render(
        request,
        "portal/dashboard.html",
        _student_context(
            request,
            active="dashboard",
            extra={"dashboard": dashboard_data, "page_heading": "Dashboard"},
        ),
    )


@student_portal_required
@require_http_methods(["GET"])
def profile(request):
    academic = None
    try:
        academic = request.user.academic_profile
    except AcademicProfile.DoesNotExist:
        academic = None
    return render(
        request,
        "portal/profile.html",
        _student_context(
            request,
            active="profile",
            extra={
                "page_heading": "Profile",
                "academic": academic,
                "locale_label": dict(LocaleCode.choices).get(
                    request.user.ui_locale, request.user.ui_locale
                ),
            },
        ),
    )


@student_portal_required
@require_http_methods(["GET", "POST"])
def profile_edit(request):
    initial = {
        "full_name": request.user.full_name,
        "ui_locale": request.user.ui_locale,
        "mobile_number": "",
        "academic_session": "",
        "blood_group": "",
        "address": "",
        "social_profile_url": "",
        "linkedin_url": "",
    }
    try:
        academic = request.user.academic_profile
        initial.update(
            {
                "mobile_number": academic.mobile_number,
                "academic_session": academic.academic_session,
                "blood_group": academic.blood_group,
                "address": academic.address,
                "social_profile_url": academic.social_profile_url,
                "linkedin_url": academic.linkedin_url,
            }
        )
    except AcademicProfile.DoesNotExist:
        academic = None
    form = ProfileEditForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        AccountService.update_profile(
            user=request.user,
            full_name=form.cleaned_data["full_name"],
            ui_locale=form.cleaned_data["ui_locale"],
        )
        AccountService.update_learner_profile(
            user=request.user,
            mobile_number=form.cleaned_data["mobile_number"],
            academic_session=form.cleaned_data["academic_session"],
            blood_group=form.cleaned_data["blood_group"],
            social_profile_url=form.cleaned_data["social_profile_url"],
            linkedin_url=form.cleaned_data["linkedin_url"],
            address=form.cleaned_data["address"],
        )
        messages.success(request, "Profile updated.")
        return redirect("portal:profile")
    return render(
        request,
        "portal/profile_edit.html",
        _student_context(
            request,
            active="profile",
            extra={"form": form, "page_heading": "Edit profile"},
        ),
    )


@student_portal_required
@require_http_methods(["GET", "POST"])
def academic_profile_edit(request):
    academic, _created = AcademicProfile.objects.get_or_create(user=request.user)
    initial = {
        "academic_program": academic.academic_program,
        "institution": academic.institution,
        "current_semester_year": academic.current_semester_year,
        "expected_graduation_year": academic.expected_graduation_year,
        "current_study_goal": academic.current_study_goal or "",
    }
    form = AcademicProfileForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        AccountService.update_academic_profile(
            user=request.user,
            academic_program=form.cleaned_data["academic_program"],
            institution=form.cleaned_data["institution"],
            current_semester_year=form.cleaned_data["current_semester_year"],
            expected_graduation_year=form.cleaned_data["expected_graduation_year"],
            current_study_goal=form.cleaned_data["current_study_goal"],
        )
        messages.success(request, "Academic profile updated.")
        return redirect("portal:profile")
    return render(
        request,
        "portal/academic_profile_edit.html",
        _student_context(
            request,
            active="profile",
            extra={"form": form, "page_heading": "Edit academic profile"},
        ),
    )


@student_portal_required
@require_http_methods(["GET"])
def notifications(request):
    items = NotificationPresentationService.list_for_user(request.user)
    return render(
        request,
        "portal/notifications.html",
        _student_context(
            request,
            active="notifications",
            extra={
                "page_heading": "Notifications",
                "notifications": items,
                "is_empty": len(items) == 0,
            },
        ),
    )


@student_portal_required
@require_POST
def notification_mark_read(request, notification_id):
    notification = NotificationPresentationService.get_own(
        request.user, notification_id
    )
    if notification is None:
        raise Http404("Notification not found.")
    NotificationPresentationService.mark_read(
        user=request.user, notification=notification
    )
    messages.info(request, "Notification marked as read.")
    return redirect("portal:notifications")


@student_portal_required
@require_http_methods(["GET"])
def subscription(request):
    """Compatibility route — UNIT-8 billing owns subscription surfaces."""
    return redirect("billing:current")


@student_portal_required
@require_http_methods(["GET", "POST"])
def settings(request):
    """Language preference settings — subset of profile fields (docs/15 family H)."""
    initial = {"ui_locale": request.user.ui_locale, "full_name": request.user.full_name}
    form = ProfileEditForm(
        request.POST or None, initial=initial, include_learner_profile=False
    )
    if request.method == "POST" and form.is_valid():
        AccountService.update_profile(
            user=request.user,
            full_name=form.cleaned_data["full_name"],
            ui_locale=form.cleaned_data["ui_locale"],
        )
        messages.success(request, "Settings saved.")
        return redirect("portal:settings")
    return render(
        request,
        "portal/settings.html",
        _student_context(
            request,
            active="settings",
            extra={"form": form, "page_heading": "Settings"},
        ),
    )


@student_portal_required
@require_http_methods(["GET"])
def unavailable(request, feature: str):
    label = FEATURE_LABELS.get(feature)
    if label is None:
        raise Http404("Feature not found.")
    return render(
        request,
        "portal/unavailable.html",
        _student_context(
            request,
            active=feature,
            extra={
                "page_heading": label,
                "feature_key": feature,
                "feature_label": label,
            },
        ),
        status=200,
    )


def home_entry(request):
    """Root entry: staff-only to staff; students to portal; guests to public landing."""
    if request.user.is_authenticated:
        from apps.portal.destinations import authenticated_destination

        return redirect(authenticated_destination(request.user))

    from apps.common.choices import LocaleCode
    from apps.portal.services import LandingPresentationService

    locale = LocaleCode.EN
    landing = LandingPresentationService.build(locale=locale)
    return render(
        request,
        "portal/landing.html",
        {
            "layout_family": "public",
            "landing": landing,
            "page_heading": "Nursilo",
            "html_lang": locale,
        },
    )
