"""Subscription lifecycle mutations owned by billing (docs/05, docs/09)."""
from __future__ import annotations

from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from apps.audit.services import AuditService
from apps.billing.models import PaymentTransaction, Subscription
from apps.billing.plans import PlanCatalog, PlanDefinition
from apps.common.choices import SubscriptionState
from apps.entitlements.models import EntitlementGrant
from apps.entitlements.services import CAPABILITY_PREMIUM


class SubscriptionService:
    @classmethod
    def get_or_create_for_user(cls, user) -> Subscription:
        sub, _created = Subscription.objects.get_or_create(
            user=user,
            defaults={"state": SubscriptionState.FREE},
        )
        return sub

    @classmethod
    def mark_pending_checkout(cls, user) -> Subscription:
        """
        Enter PendingPayment only when the learner is not currently PremiumActive.
        Active Premium renewals must keep access during checkout.
        """
        with transaction.atomic():
            sub = cls.get_or_create_for_user(user)
            locked = Subscription.objects.select_for_update().get(pk=sub.pk)
            if locked.state == SubscriptionState.PREMIUM_ACTIVE:
                return locked
            if locked.state != SubscriptionState.PENDING_PAYMENT:
                locked.state = SubscriptionState.PENDING_PAYMENT
                locked.save(update_fields=["state", "updated_at"])
                AuditService.record(
                    action="subscription_changed",
                    actor_user=user,
                    target_type="subscription",
                    target_id=str(locked.id),
                    metadata={"state": locked.state, "reason": "checkout_started"},
                )
            return locked

    @classmethod
    def mark_checkout_failed(cls, user) -> Subscription:
        """Failed payment does not grant Premium; restore Free/Expired honestly."""
        with transaction.atomic():
            sub = cls.get_or_create_for_user(user)
            locked = Subscription.objects.select_for_update().get(pk=sub.pk)
            if locked.state == SubscriptionState.PREMIUM_ACTIVE:
                return locked
            if locked.state == SubscriptionState.PENDING_PAYMENT:
                # Prefer expired if they previously had an expiry in the past.
                if (
                    locked.premium_expires_at is not None
                    and locked.premium_expires_at <= timezone.now()
                ):
                    locked.state = SubscriptionState.EXPIRED
                else:
                    locked.state = SubscriptionState.FREE
                locked.save(update_fields=["state", "updated_at"])
                AuditService.record(
                    action="subscription_changed",
                    actor_user=user,
                    target_type="subscription",
                    target_id=str(locked.id),
                    metadata={"state": locked.state, "reason": "payment_failed"},
                )
            return locked

    @classmethod
    def activate_from_confirmed_payment(
        cls,
        *,
        payment: PaymentTransaction,
        plan: PlanDefinition,
    ) -> Subscription:
        """
        Idempotent Premium activation/renewal using server time only.

        - Active Premium → expires_at + plan.duration_days
        - Otherwise → now + plan.duration_days
        """
        now = timezone.now()
        duration = timedelta(days=plan.duration_days)
        grant_notes = f"payment:{payment.id}"
        with transaction.atomic():
            sub = Subscription.objects.select_for_update().get(pk=payment.subscription_id)
            # Idempotent: same payment must never double-extend.
            if EntitlementGrant.objects.filter(
                user=payment.user, notes=grant_notes
            ).exists():
                return sub
            if (
                sub.state == SubscriptionState.PREMIUM_ACTIVE
                and sub.premium_expires_at is not None
                and sub.premium_expires_at > now
            ):
                new_expiry = sub.premium_expires_at + duration
                started = sub.premium_started_at or now
            else:
                new_expiry = now + duration
                started = now
            sub.state = SubscriptionState.PREMIUM_ACTIVE
            sub.premium_started_at = started
            sub.premium_expires_at = new_expiry
            sub.save(
                update_fields=[
                    "state",
                    "premium_started_at",
                    "premium_expires_at",
                    "updated_at",
                ]
            )
            EntitlementGrant.objects.create(
                user=payment.user,
                capability_code=CAPABILITY_PREMIUM,
                starts_at=now,
                ends_at=new_expiry,
                source="payment",
                is_active=True,
                notes=grant_notes,
            )
            AuditService.record(
                action="subscription_changed",
                actor_user=payment.user,
                target_type="subscription",
                target_id=str(sub.id),
                metadata={
                    "state": sub.state,
                    "plan_code": plan.code,
                    "premium_expires_at": new_expiry.isoformat(),
                    "payment_id": str(payment.id),
                    "reason": "payment_confirmed",
                },
            )
            return sub

    @classmethod
    def plan_for_payment(cls, payment: PaymentTransaction) -> PlanDefinition:
        return PlanCatalog.require(payment.plan_code or PlanCatalog.default_plan().code)
