"""Billing orchestration — checkout, verify, idempotent confirm (docs/04, docs/09 §17)."""
from __future__ import annotations

import hashlib
import json
import uuid
from decimal import Decimal
from typing import Any
from urllib.parse import urlencode

from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from apps.audit.services import AuditService
from apps.billing.exceptions import (
    EmailVerificationRequired,
    PaymentForbidden,
    PaymentNotConfigured,
    PaymentNotFound,
    PaymentProviderError,
    PaymentVerificationFailed,
    PlanNotFound,
)
from apps.billing.models import PaymentTransaction
from apps.billing.plans import PlanCatalog, PlanDefinition
from apps.billing.services.providers import get_payment_provider
from apps.billing.services.providers.base import CheckoutSessionRequest
from apps.billing.services.subscription import SubscriptionService
from apps.common.choices import PaymentGateway, PaymentStatus


class BillingService:
    GATEWAY = PaymentGateway.SSLCOMMERZ

    @classmethod
    def provider_configured(cls) -> bool:
        return get_payment_provider().is_configured()

    @classmethod
    def list_plans(cls) -> list[PlanDefinition]:
        return PlanCatalog.all_active()

    @classmethod
    def get_plan(cls, plan_code: str) -> PlanDefinition:
        plan = PlanCatalog.get(plan_code)
        if plan is None:
            raise PlanNotFound()
        return plan

    @classmethod
    def get_own_payment(cls, user, payment_id) -> PaymentTransaction:
        try:
            payment = PaymentTransaction.objects.select_related("subscription").get(
                id=payment_id
            )
        except (PaymentTransaction.DoesNotExist, ValueError, TypeError) as exc:
            raise PaymentNotFound() from exc
        if payment.user_id != user.id:
            raise PaymentForbidden()
        return payment

    @classmethod
    def get_by_gateway_ref(cls, gateway_ref: str) -> PaymentTransaction | None:
        ref = (gateway_ref or "").strip()
        if not ref:
            return None
        return (
            PaymentTransaction.objects.select_related("subscription", "user")
            .filter(gateway=cls.GATEWAY, gateway_ref=ref)
            .first()
        )

    @classmethod
    def billing_history(cls, user, *, limit: int = 50):
        return list(
            PaymentTransaction.objects.filter(user=user)
            .order_by("-created_at")[:limit]
        )

    @classmethod
    def start_checkout(cls, *, user, plan_code: str, request) -> tuple[PaymentTransaction, str]:
        """
        Load authoritative plan → create initiated txn → provider session → gateway URL.

        Returns (payment, gateway_redirect_url).
        Email verification is required for premium purchase (docs/09).
        """
        if not getattr(user, "is_email_verified", False):
            raise EmailVerificationRequired()

        plan = cls.get_plan(plan_code)
        provider = get_payment_provider()
        if not provider.is_configured():
            raise PaymentNotConfigured()

        absolute = request.build_absolute_uri
        with transaction.atomic():
            subscription = SubscriptionService.mark_pending_checkout(user)
            gateway_ref = cls._new_tran_id()
            payment = PaymentTransaction.objects.create(
                user=user,
                subscription=subscription,
                gateway=cls.GATEWAY,
                gateway_ref=gateway_ref,
                plan_code=plan.code,
                amount=plan.amount,
                currency=plan.currency,
                status=PaymentStatus.INITIATED,
            )

        success_url = absolute(
            reverse("billing:return_success") + "?" + urlencode({"tran_id": payment.gateway_ref})
        )
        fail_url = absolute(
            reverse("billing:return_fail") + "?" + urlencode({"tran_id": payment.gateway_ref})
        )
        cancel_url = absolute(
            reverse("billing:return_cancel") + "?" + urlencode({"tran_id": payment.gateway_ref})
        )
        ipn_url = absolute(reverse("billing:ipn"))

        session = provider.create_checkout_session(
            CheckoutSessionRequest(
                tran_id=payment.gateway_ref,
                amount=payment.amount,
                currency=payment.currency,
                product_name=plan.name,
                product_category="education",
                success_url=success_url,
                fail_url=fail_url,
                cancel_url=cancel_url,
                ipn_url=ipn_url,
                customer_name=(user.full_name or user.email.split("@")[0])[:50],
                customer_email=user.email,
                customer_phone="01700000000",
                value_a=str(user.id),
                value_b=plan.code,
                value_c=str(payment.id),
            )
        )
        if not session.ok or not session.gateway_url:
            cls.mark_failed(payment, reason=session.error or "session_failed")
            raise PaymentProviderError(session.error or "Could not start checkout.")
        if not cls._is_allowed_gateway_url(session.gateway_url):
            cls.mark_failed(payment, reason="unsafe_gateway_url")
            raise PaymentProviderError("Payment gateway returned an unsafe redirect.")

        fingerprint = cls._fingerprint(
            {
                "event": "session_created",
                "session_key": session.session_key,
                "plan_code": plan.code,
            }
        )
        PaymentTransaction.objects.filter(pk=payment.pk).update(
            raw_event_fingerprint=fingerprint
        )
        AuditService.record(
            action="payment_initiated",
            actor_user=user,
            target_type="payment_transaction",
            target_id=str(payment.id),
            metadata={
                "gateway": payment.gateway,
                "plan_code": plan.code,
                "amount": str(payment.amount),
                "currency": payment.currency,
            },
        )
        return payment, session.gateway_url

    @classmethod
    def handle_provider_callback(
        cls,
        payload: dict[str, Any],
        *,
        require_hash: bool = True,
        mark_failed_on_error: bool = False,
    ) -> PaymentTransaction:
        """
        Untrusted callback/IPN/return handler.

        Browser redirect is never payment proof — Order Validation API is.
        Idempotent: already-confirmed payments are returned without re-extension.
        """
        provider = get_payment_provider()
        if not provider.is_configured():
            raise PaymentNotConfigured()

        tran_id = str(payload.get("tran_id") or "").strip()
        payment = cls.get_by_gateway_ref(tran_id)
        if payment is None:
            raise PaymentNotFound()

        with transaction.atomic():
            locked = PaymentTransaction.objects.select_for_update().get(pk=payment.pk)
            if locked.status == PaymentStatus.CONFIRMED:
                return locked

            if require_hash and not provider.verify_callback_authenticity(payload):
                if mark_failed_on_error:
                    cls._fail_locked(locked, reason="hash_mismatch")
                raise PaymentVerificationFailed("Callback authenticity check failed.")

            status_hint = str(payload.get("status") or "").upper()
            if status_hint in {"FAILED", "CANCELLED", "EXPIRED", "UNATTEMPTED"}:
                cls._fail_locked(locked, reason=status_hint.lower())
                SubscriptionService.mark_checkout_failed(locked.user)
                return locked

            validation = provider.validate_transaction(payload)
            if not validation.ok:
                if mark_failed_on_error or status_hint in {"FAILED", "CANCELLED"}:
                    cls._fail_locked(locked, reason=validation.error or "validation_failed")
                    SubscriptionService.mark_checkout_failed(locked.user)
                raise PaymentVerificationFailed(validation.error or "Validation failed.")

            if validation.tran_id and validation.tran_id != locked.gateway_ref:
                cls._fail_locked(locked, reason="tran_id_mismatch")
                raise PaymentVerificationFailed("Transaction id mismatch.")

            if validation.amount is None or validation.amount != locked.amount:
                cls._fail_locked(locked, reason="amount_mismatch")
                raise PaymentVerificationFailed("Amount mismatch.")

            if validation.currency and validation.currency != locked.currency.upper():
                cls._fail_locked(locked, reason="currency_mismatch")
                raise PaymentVerificationFailed("Currency mismatch.")

            value_a = str(payload.get("value_a") or "")
            value_b = str(payload.get("value_b") or "")
            if value_a and value_a != str(locked.user_id):
                cls._fail_locked(locked, reason="user_mismatch")
                raise PaymentVerificationFailed("User mismatch.")
            if value_b and value_b != locked.plan_code:
                cls._fail_locked(locked, reason="plan_mismatch")
                raise PaymentVerificationFailed("Plan mismatch.")

            # Re-check idempotency after validation (duplicate IPN race).
            locked.refresh_from_db()
            if locked.status == PaymentStatus.CONFIRMED:
                return locked

            plan = PlanCatalog.require(locked.plan_code)
            SubscriptionService.activate_from_confirmed_payment(payment=locked, plan=plan)
            now = timezone.now()
            locked.status = PaymentStatus.CONFIRMED
            locked.confirmed_at = now
            locked.raw_event_fingerprint = cls._fingerprint(
                {
                    "event": "confirmed",
                    "val_id": validation.val_id,
                    "status": validation.status,
                    "amount": str(validation.amount),
                }
            )
            locked.save(
                update_fields=[
                    "status",
                    "confirmed_at",
                    "raw_event_fingerprint",
                ]
            )
            AuditService.record(
                action="payment_confirmed",
                actor_user=locked.user,
                target_type="payment_transaction",
                target_id=str(locked.id),
                metadata={
                    "gateway": locked.gateway,
                    "plan_code": locked.plan_code,
                    "amount": str(locked.amount),
                    "currency": locked.currency,
                    "val_id": validation.val_id,
                },
            )
            return locked

    @classmethod
    def mark_failed(cls, payment: PaymentTransaction, *, reason: str = "failed") -> PaymentTransaction:
        with transaction.atomic():
            locked = PaymentTransaction.objects.select_for_update().get(pk=payment.pk)
            if locked.status == PaymentStatus.CONFIRMED:
                return locked
            cls._fail_locked(locked, reason=reason)
            SubscriptionService.mark_checkout_failed(locked.user)
            return locked

    @classmethod
    def process_return(cls, payload: dict[str, Any], *, failed: bool = False) -> PaymentTransaction:
        """
        User browser return — still verifies via provider; never trusts redirect alone.
        Success page callers must check payment.status == confirmed.
        """
        if failed:
            tran_id = str(payload.get("tran_id") or "").strip()
            payment = cls.get_by_gateway_ref(tran_id)
            if payment is None:
                raise PaymentNotFound()
            return cls.mark_failed(payment, reason="return_failed")
        # Return URLs often omit verify_sign; Order Validation still required when val_id present.
        has_val = bool(str(payload.get("val_id") or "").strip())
        if not has_val:
            tran_id = str(payload.get("tran_id") or "").strip()
            payment = cls.get_by_gateway_ref(tran_id)
            if payment is None:
                raise PaymentNotFound()
            # Honest pending — no client-side success.
            return payment
        return cls.handle_provider_callback(
            payload, require_hash=False, mark_failed_on_error=False
        )

    @classmethod
    def _fail_locked(cls, locked: PaymentTransaction, *, reason: str) -> None:
        if locked.status == PaymentStatus.CONFIRMED:
            return
        locked.status = PaymentStatus.FAILED
        locked.raw_event_fingerprint = cls._fingerprint(
            {"event": "failed", "reason": reason}
        )
        locked.save(update_fields=["status", "raw_event_fingerprint"])
        AuditService.record(
            action="payment_failed",
            actor_user=locked.user,
            target_type="payment_transaction",
            target_id=str(locked.id),
            metadata={"reason": reason, "plan_code": locked.plan_code},
        )

    @staticmethod
    def _new_tran_id() -> str:
        # SSLCommerz tran_id max length 30
        return uuid.uuid4().hex[:30]

    @staticmethod
    def _fingerprint(data: dict[str, Any]) -> str:
        raw = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    @staticmethod
    def _is_allowed_gateway_url(url: str) -> bool:
        """Prevent open redirects from a compromised/malformed provider response."""
        allowed_prefixes = (
            "https://sandbox.sslcommerz.com/",
            "https://fake-gateway.test/",
        )
        return isinstance(url, str) and url.startswith(allowed_prefixes)
