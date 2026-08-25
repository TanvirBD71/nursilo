"""Thin billing presentation views — services own payment/subscription truth."""
from __future__ import annotations

from django.contrib import messages
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods, require_POST

from apps.accounts.exceptions import ReauthenticationRequired
from apps.accounts.services import ReauthService
from apps.billing.exceptions import (
    BillingError,
    EmailVerificationRequired,
    PaymentForbidden,
    PaymentNotConfigured,
    PaymentNotFound,
    PaymentProviderError,
    PaymentVerificationFailed,
    PlanNotFound,
)
from apps.billing.services import BillingPresentationService, BillingService
from apps.common.choices import PaymentStatus
from apps.portal.access import student_portal_required
from apps.portal.services import (
    NavigationService,
    NotificationPresentationService,
    SubscriptionPresentationService,
)


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


def _payload_from_request(request) -> dict:
    data = {}
    data.update(request.GET.dict())
    data.update(request.POST.dict())
    return data


@student_portal_required
@require_http_methods(["GET"])
def pricing(request):
    ctx = BillingPresentationService.current_subscription_context(request.user)
    return render(
        request,
        "billing/pricing.html",
        _student_context(
            request,
            active="subscription",
            extra={
                "page_heading": "Pricing",
                **ctx,
            },
        ),
    )


@student_portal_required
@require_http_methods(["GET"])
def current_subscription(request):
    ctx = BillingPresentationService.current_subscription_context(request.user)
    return render(
        request,
        "billing/current.html",
        _student_context(
            request,
            active="subscription",
            extra={
                "page_heading": "Subscription",
                **ctx,
            },
        ),
    )


@student_portal_required
@require_http_methods(["GET", "POST"])
def checkout(request):
    if not request.user.is_email_verified:
        messages.error(
            request,
            "Verify your email before starting premium checkout.",
        )
        return redirect("accounts:resend_verification")

    try:
        ReauthService.require_fresh(request, action="purchase_premium")
    except ReauthenticationRequired:
        next_url = request.get_full_path()
        return redirect(f"{reverse('accounts:reauth')}?next={next_url}")

    default_plan = BillingService.list_plans()[0]
    plan_code = (
        request.POST.get("plan_code")
        or request.GET.get("plan_code")
        or default_plan.code
    )
    ctx = BillingPresentationService.current_subscription_context(request.user)
    plan = None
    try:
        plan = BillingService.get_plan(plan_code)
    except PlanNotFound:
        messages.error(request, "Selected plan is not available.")
        return redirect("billing:pricing")

    if request.method == "POST":
        try:
            _payment, gateway_url = BillingService.start_checkout(
                user=request.user,
                plan_code=plan_code,
                request=request,
            )
        except EmailVerificationRequired as exc:
            messages.error(request, exc.message)
            return redirect("accounts:resend_verification")
        except PaymentNotConfigured as exc:
            messages.error(request, exc.message)
            return redirect("billing:checkout")
        except (PlanNotFound, PaymentProviderError, BillingError) as exc:
            messages.error(request, getattr(exc, "message", str(exc)))
            return redirect("billing:checkout")
        # External gateway redirect (provider URL only — not user-controlled).
        return redirect(gateway_url)

    return render(
        request,
        "billing/checkout.html",
        _student_context(
            request,
            active="subscription",
            extra={
                "page_heading": "Checkout",
                "plan": plan,
                **ctx,
            },
        ),
    )


@student_portal_required
@require_http_methods(["GET"])
def pending(request, payment_id):
    try:
        payment = BillingService.get_own_payment(request.user, payment_id)
    except PaymentForbidden:
        return HttpResponseForbidden("Forbidden")
    except PaymentNotFound:
        messages.error(request, "Payment not found.")
        return redirect("billing:history")
    result = BillingPresentationService.result_context(payment)
    if result["is_success"]:
        return redirect("billing:success", payment_id=payment.id)
    if result["is_failed"]:
        return redirect("billing:failure", payment_id=payment.id)
    return render(
        request,
        "billing/pending.html",
        _student_context(
            request,
            active="subscription",
            extra={"page_heading": "Payment pending", **result},
        ),
    )


@student_portal_required
@require_http_methods(["GET"])
def success(request, payment_id):
    try:
        payment = BillingService.get_own_payment(request.user, payment_id)
    except PaymentForbidden:
        return HttpResponseForbidden("Forbidden")
    except PaymentNotFound:
        messages.error(request, "Payment not found.")
        return redirect("billing:history")
    result = BillingPresentationService.result_context(payment)
    # Honest UX: success page only after server confirm.
    if not result["is_success"]:
        if result["is_failed"]:
            return redirect("billing:failure", payment_id=payment.id)
        return redirect("billing:pending", payment_id=payment.id)
    return render(
        request,
        "billing/success.html",
        _student_context(
            request,
            active="subscription",
            extra={"page_heading": "Payment successful", **result},
        ),
    )


@student_portal_required
@require_http_methods(["GET"])
def failure(request, payment_id):
    try:
        payment = BillingService.get_own_payment(request.user, payment_id)
    except PaymentForbidden:
        return HttpResponseForbidden("Forbidden")
    except PaymentNotFound:
        messages.error(request, "Payment not found.")
        return redirect("billing:history")
    result = BillingPresentationService.result_context(payment)
    return render(
        request,
        "billing/failure.html",
        _student_context(
            request,
            active="subscription",
            extra={
                "page_heading": "Payment failed",
                "checkout_available": BillingService.provider_configured(),
                **result,
            },
        ),
    )


@student_portal_required
@require_http_methods(["GET"])
def history(request):
    rows = BillingPresentationService.history_rows(request.user)
    return render(
        request,
        "billing/history.html",
        _student_context(
            request,
            active="subscription",
            extra={
                "page_heading": "Billing history",
                "payments": rows,
                "is_empty": len(rows) == 0,
            },
        ),
    )


def _owned_or_lookup_redirect(request, payment, *, success_name: str):
    if request.user.is_authenticated and payment.user_id == request.user.id:
        if payment.status == PaymentStatus.CONFIRMED:
            return redirect("billing:success", payment_id=payment.id)
        if payment.status == PaymentStatus.FAILED:
            return redirect("billing:failure", payment_id=payment.id)
        return redirect("billing:pending", payment_id=payment.id)
    # Unauthenticated return from gateway — send to login then history.
    messages.info(request, "Sign in to view your payment status.")
    return redirect(reverse("accounts:login") + "?next=" + reverse("billing:history"))


@require_http_methods(["GET", "POST"])
def return_success(request):
    payload = _payload_from_request(request)
    try:
        payment = BillingService.process_return(payload, failed=False)
    except PaymentNotFound:
        messages.error(request, "Payment not found.")
        return redirect("billing:history")
    except PaymentVerificationFailed:
        # Stay honest — pending until IPN/validation confirms.
        payment = BillingService.get_by_gateway_ref(str(payload.get("tran_id") or ""))
        if payment is None:
            messages.error(request, "Payment could not be verified yet.")
            return redirect("billing:history")
        return _owned_or_lookup_redirect(request, payment, success_name="success")
    except PaymentNotConfigured:
        messages.error(request, "Payment gateway is not configured.")
        return redirect("billing:history")
    return _owned_or_lookup_redirect(request, payment, success_name="success")


@require_http_methods(["GET", "POST"])
def return_fail(request):
    payload = _payload_from_request(request)
    try:
        payment = BillingService.process_return(payload, failed=True)
    except PaymentNotFound:
        messages.error(request, "Payment not found.")
        return redirect("billing:history")
    return _owned_or_lookup_redirect(request, payment, success_name="failure")


@require_http_methods(["GET", "POST"])
def return_cancel(request):
    payload = _payload_from_request(request)
    try:
        payment = BillingService.process_return(payload, failed=True)
    except PaymentNotFound:
        messages.error(request, "Payment not found.")
        return redirect("billing:history")
    return _owned_or_lookup_redirect(request, payment, success_name="failure")


@csrf_exempt
@require_POST
def ipn(request):
    """
    SSLCommerz IPN listener — untrusted POST; hash + Order Validation required.
    CSRF exempt (server-to-server); authenticity is provider-verified.
    """
    payload = request.POST.dict()
    try:
        BillingService.handle_provider_callback(
            payload, require_hash=True, mark_failed_on_error=True
        )
    except PaymentNotFound:
        return HttpResponse("INVALID", status=404)
    except PaymentNotConfigured:
        return HttpResponse("NOT_CONFIGURED", status=503)
    except PaymentVerificationFailed:
        return HttpResponse("FAILED", status=400)
    except BillingError:
        return HttpResponse("ERROR", status=400)
    return HttpResponse("OK", status=200)
