"""Thin auth views — services own security decisions (docs/04, docs/07, docs/19)."""
from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods, require_POST

from apps.accounts.exceptions import (
    AccountError,
    AccountInactive,
    AccountLocked,
    AuthenticationFailed,
    EmailAlreadyRegistered,
    EmailAlreadyVerified,
    InvalidToken,
    PasswordPolicyError,
    ReauthenticationFailed,
    ReauthenticationRequired,
)
from apps.accounts.forms import (
    EmailVerificationForm,
    LoginForm,
    LogoutAllForm,
    LogoutOthersForm,
    PasswordChangeForm,
    PasswordResetConfirmForm,
    PasswordResetRequestForm,
    ReauthForm,
    RegisterForm,
    ResendVerificationForm,
)
from apps.accounts.models import UserSession, UserSessionStatus
from apps.accounts.redirects import safe_back_url, safe_redirect_url
from apps.portal.destinations import authenticated_destination
from apps.accounts.services import (
    AccountService,
    AuthenticationService,
    ReauthService,
    SessionService,
)


def _focus_first_error(form) -> None:
    if not getattr(form, "errors", None):
        return
    for name in form.fields:
        if name in form.errors:
            form.fields[name].widget.attrs["autofocus"] = True
            break


def _render_form(request, template, form, *, status=200, extra=None):
    _focus_first_error(form)
    context = {"form": form}
    if extra:
        context.update(extra)
    return render(request, template, context, status=status)


def _auth_back(request, *, fallback: str, label: str) -> dict:
    return {
        "back_href": safe_back_url(request, fallback=fallback),
        "back_label": label,
    }


@require_http_methods(["GET", "POST"])
def register(request):
    if request.user.is_authenticated:
        return redirect(
            safe_redirect_url(None, fallback=authenticated_destination(request.user))
        )
    form = RegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            AccountService.register(
                email=form.cleaned_data["email"],
                password=form.cleaned_data["password"],
                full_name=form.cleaned_data.get("full_name") or "",
                request=request,
                mobile_number=form.cleaned_data.get("mobile_number") or "",
                academic_session=form.cleaned_data.get("academic_session") or "",
                blood_group=form.cleaned_data.get("blood_group") or "",
                social_profile_url=form.cleaned_data.get("social_profile_url") or "",
                linkedin_url=form.cleaned_data.get("linkedin_url") or "",
                address=form.cleaned_data.get("address") or "",
            )
        except EmailAlreadyRegistered as exc:
            form.add_error("email", exc.message)
        except PasswordPolicyError as exc:
            form.add_error("password", exc.message)
        else:
            messages.success(
                request,
                "Account created. Please verify your email to unlock sensitive actions.",
            )
            return redirect("accounts:verify_email")
    return _render_form(
        request,
        "auth/register.html",
        form,
        extra=_auth_back(
            request, fallback=reverse("accounts:login"), label="Sign in"
        ),
    )


@require_http_methods(["GET", "POST"])
def login_view(request):
    if request.user.is_authenticated:
        return redirect(
            safe_redirect_url(
                request.GET.get("next"),
                fallback=authenticated_destination(request.user),
            )
        )
    initial = {"next": request.GET.get("next", "")}
    form = LoginForm(request.POST or None, initial=initial)
    session_expired = request.GET.get("reason") == "session_expired"
    if request.method == "POST" and form.is_valid():
        try:
            AuthenticationService.login(
                request=request,
                email=form.cleaned_data["email"],
                password=form.cleaned_data["password"],
                remember_me=bool(form.cleaned_data.get("remember_me")),
            )
        except (AuthenticationFailed, AccountLocked, AccountInactive) as exc:
            form.add_error(None, exc.message)
        else:
            nxt = safe_redirect_url(
                form.cleaned_data.get("next") or request.GET.get("next"),
                fallback=authenticated_destination(request.user),
            )
            return redirect(nxt)
    return _render_form(
        request,
        "auth/login.html",
        form,
        extra={
            "session_expired": session_expired,
            **_auth_back(request, fallback=reverse("home"), label="home"),
        },
    )


@require_http_methods(["GET", "POST"])
@login_required
def logout_view(request):
    if request.method == "POST":
        AuthenticationService.logout_current(request)
        messages.info(request, "You have been signed out.")
        return redirect("accounts:login")
    return render(
        request,
        "auth/logout_confirm.html",
        _auth_back(
            request,
            fallback=authenticated_destination(request.user),
            label="dashboard",
        ),
    )


@require_http_methods(["GET", "POST"])
@login_required
def password_change(request):
    form = PasswordChangeForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            AuthenticationService.change_password(
                request=request,
                current_password=form.cleaned_data["current_password"],
                new_password=form.cleaned_data["new_password"],
            )
        except (ReauthenticationFailed, PasswordPolicyError, AccountError) as exc:
            form.add_error(None, exc.message)
        else:
            messages.success(request, "Password updated.")
            return redirect("accounts:password_change")
    return _render_form(
        request,
        "auth/password_change.html",
        form,
        extra=_auth_back(
            request,
            fallback=authenticated_destination(request.user),
            label="your account",
        ),
    )


@require_http_methods(["GET", "POST"])
def password_reset_request(request):
    form = PasswordResetRequestForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        msg = AuthenticationService.request_password_reset(email=form.cleaned_data["email"])
        messages.info(request, msg)
        return redirect("accounts:password_reset_request")
    return _render_form(
        request,
        "auth/password_reset_request.html",
        form,
        extra=_auth_back(
            request, fallback=reverse("accounts:login"), label="sign in"
        ),
    )


@require_http_methods(["GET", "POST"])
def password_reset_confirm(request):
    initial = {"token": request.GET.get("token", "")}
    form = PasswordResetConfirmForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        try:
            AuthenticationService.reset_password(
                raw_token=form.cleaned_data["token"],
                new_password=form.cleaned_data["new_password"],
            )
        except (InvalidToken, PasswordPolicyError, AccountError) as exc:
            form.add_error(None, exc.message)
        else:
            messages.success(request, "Password reset complete. Please sign in.")
            return redirect("accounts:login")
    return _render_form(
        request,
        "auth/password_reset_confirm.html",
        form,
        extra=_auth_back(
            request,
            fallback=reverse("accounts:password_reset_request"),
            label="password reset",
        ),
    )


@require_http_methods(["GET", "POST"])
def verify_email(request):
    initial = {"token": request.GET.get("token", "")}
    form = EmailVerificationForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        try:
            AuthenticationService.verify_email(raw_token=form.cleaned_data["token"])
        except (InvalidToken, EmailAlreadyVerified, AccountError) as exc:
            form.add_error(None, exc.message)
        else:
            messages.success(request, "Email verified.")
            return redirect("accounts:login")
    return _render_form(
        request,
        "auth/verify_email.html",
        form,
        extra=_auth_back(
            request, fallback=reverse("accounts:login"), label="sign in"
        ),
    )


@require_http_methods(["GET", "POST"])
def resend_verification(request):
    form = ResendVerificationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        msg = AuthenticationService.resend_email_verification(
            email=form.cleaned_data["email"]
        )
        messages.info(request, msg)
        return redirect("accounts:resend_verification")
    return _render_form(
        request,
        "auth/resend_verification.html",
        form,
        extra=_auth_back(
            request,
            fallback=reverse("accounts:verify_email"),
            label="email verification",
        ),
    )


@require_http_methods(["GET", "POST"])
@login_required
def reauth(request):
    initial = {"next": request.GET.get("next", "")}
    form = ReauthForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        try:
            ReauthService.confirm_password(
                user=request.user,
                password=form.cleaned_data["password"],
                request=request,
            )
        except ReauthenticationFailed as exc:
            form.add_error("password", exc.message)
        else:
            nxt = safe_redirect_url(
                form.cleaned_data.get("next") or reverse("accounts:devices"),
                fallback=reverse("accounts:devices"),
            )
            return redirect(nxt)
    return _render_form(
        request,
        "auth/reauth.html",
        form,
        extra=_auth_back(
            request, fallback=reverse("accounts:devices"), label="devices"
        ),
    )


@login_required
@require_http_methods(["GET"])
def devices(request):
    try:
        ReauthService.require_fresh(request, action="view_devices")
    except ReauthenticationRequired:
        return redirect(
            f"{reverse('accounts:reauth')}?next={reverse('accounts:devices')}"
        )
    sessions = SessionService.active_sessions_qs(request.user).order_by("-last_activity")
    current = SessionService.get_current(request)
    return render(
        request,
        "auth/devices.html",
        {"sessions": sessions, "current_session": current}
        | _auth_back(
            request,
            fallback=authenticated_destination(request.user),
            label="your account",
        ),
    )


@login_required
@require_POST
def revoke_device(request, session_id):
    try:
        ReauthService.require_fresh(request, action="view_devices")
    except ReauthenticationRequired:
        return redirect(
            f"{reverse('accounts:reauth')}?next={reverse('accounts:devices')}"
        )
    user_session = get_object_or_404(
        UserSession,
        id=session_id,
        user=request.user,
        status=UserSessionStatus.ACTIVE,
    )
    current = SessionService.get_current(request)
    if current is not None and current.id == user_session.id:
        AuthenticationService.logout_current(request)
        messages.info(request, "Current device signed out.")
        return redirect("accounts:login")
    SessionService.revoke_session(user_session, reason="user_revoke", actor=request.user)
    messages.info(request, "Device signed out.")
    return redirect("accounts:devices")


@login_required
@require_http_methods(["GET", "POST"])
def logout_all(request):
    form = LogoutAllForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            AuthenticationService.logout_all_devices(
                request, password=form.cleaned_data["password"]
            )
        except (ReauthenticationFailed, AccountError) as exc:
            form.add_error(None, exc.message)
        else:
            messages.info(request, "All devices signed out.")
            return redirect("accounts:login")
    return _render_form(
        request,
        "auth/logout_all.html",
        form,
        extra=_auth_back(
            request, fallback=reverse("accounts:devices"), label="devices"
        ),
    )


@login_required
@require_http_methods(["GET", "POST"])
def logout_others(request):
    form = LogoutOthersForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            count = AuthenticationService.logout_other_devices(
                request, password=form.cleaned_data["password"]
            )
        except (ReauthenticationFailed, ReauthenticationRequired, AccountError) as exc:
            form.add_error(None, exc.message)
        else:
            messages.info(request, f"Signed out {count} other device(s).")
            return redirect("accounts:devices")
    return _render_form(
        request,
        "auth/logout_others.html",
        form,
        extra=_auth_back(
            request, fallback=reverse("accounts:devices"), label="devices"
        ),
    )


# Avoid shadowing django.contrib.auth.login import name in URLconfs
login = login_view
