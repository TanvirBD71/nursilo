"""Billing/subscription page presentation (read models only)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from apps.billing.models import PaymentTransaction
from apps.billing.plans import PlanCatalog, PlanDefinition
from apps.billing.services.billing import BillingService
from apps.common.choices import PaymentStatus
from apps.entitlements.services import EntitlementService
from apps.portal.services.subscription import SubscriptionPresentationService


@dataclass(frozen=True)
class PlanCard:
    code: str
    name: str
    amount: Decimal
    currency: str
    duration_days: int
    display_price: str
    description: str
    is_v1_offer: bool = True


@dataclass(frozen=True)
class PaymentRow:
    id: str
    plan_code: str
    plan_name: str
    amount: Decimal
    currency: str
    status: str
    status_label: str
    created_at: datetime
    confirmed_at: datetime | None
    gateway_ref: str


STATUS_LABELS = {
    PaymentStatus.INITIATED: "Pending",
    PaymentStatus.CONFIRMED: "Success",
    PaymentStatus.FAILED: "Failed",
}


class BillingPresentationService:
    @classmethod
    def plan_cards(cls) -> list[PlanCard]:
        cards: list[PlanCard] = []
        for plan in PlanCatalog.all_active():
            cards.append(
                PlanCard(
                    code=plan.code,
                    name=plan.name,
                    amount=plan.amount,
                    currency=plan.currency,
                    duration_days=plan.duration_days,
                    display_price=plan.display_price,
                    description=plan.description,
                )
            )
        return cards

    @classmethod
    def current_subscription_context(cls, user) -> dict:
        presentation = SubscriptionPresentationService.for_user(user)
        entitlement = EntitlementService.snapshot(user)
        provider_ready = BillingService.provider_configured()
        email_verified = bool(getattr(user, "is_email_verified", False))
        return {
            "subscription": presentation,
            "entitlement": entitlement,
            "plans": cls.plan_cards(),
            "provider_configured": provider_ready,
            "email_verified": email_verified,
            "checkout_available": provider_ready and email_verified,
        }

    @classmethod
    def payment_row(cls, payment: PaymentTransaction) -> PaymentRow:
        plan = PlanCatalog.get(payment.plan_code)
        return PaymentRow(
            id=str(payment.id),
            plan_code=payment.plan_code,
            plan_name=plan.name if plan else payment.plan_code or "Plan",
            amount=payment.amount,
            currency=payment.currency,
            status=payment.status,
            status_label=STATUS_LABELS.get(payment.status, payment.status),
            created_at=payment.created_at,
            confirmed_at=payment.confirmed_at,
            gateway_ref=payment.gateway_ref,
        )

    @classmethod
    def history_rows(cls, user) -> list[PaymentRow]:
        return [cls.payment_row(p) for p in BillingService.billing_history(user)]

    @classmethod
    def result_context(cls, payment: PaymentTransaction) -> dict:
        row = cls.payment_row(payment)
        entitlement = EntitlementService.snapshot(payment.user)
        is_success = payment.status == PaymentStatus.CONFIRMED
        is_failed = payment.status == PaymentStatus.FAILED
        is_pending = payment.status == PaymentStatus.INITIATED
        return {
            "payment": row,
            "entitlement": entitlement,
            "is_success": is_success,
            "is_failed": is_failed,
            "is_pending": is_pending,
        }
