"""Billing/subscription staff visibility + audited manual grant/revoke.

Does not invent payment success. Does not configure gateways or touch secrets.
Uses approved PlanCatalog duration for manual grants (docs/09 §6).
"""
from __future__ import annotations

from datetime import timedelta

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.accounts.models import UserAccount
from apps.audit.services import AuditService
from apps.billing.models import PaymentTransaction, Subscription
from apps.billing.plans import PlanCatalog
from apps.billing.services.subscription import SubscriptionService
from apps.common.choices import SubscriptionState
from apps.entitlements.models import EntitlementGrant
from apps.entitlements.services import CAPABILITY_PREMIUM
from apps.rbac.services import AccessControlService
from apps.staff.services.pagination import paginate_queryset


class BillingStaffError(Exception):
    def __init__(self, message: str, *, code: str = "billing_error"):
        super().__init__(message)
        self.code = code


class BillingStaffService:
    @classmethod
    def list_subscriptions(cls, actor, *, q: str = "", state: str = "", page=1):
        AccessControlService.require_permission(actor, "billing.view_subscriptions")
        qs = Subscription.objects.select_related("user").order_by("-updated_at")
        if state:
            qs = qs.filter(state=state)
        if q:
            qs = qs.filter(
                Q(user__email__icontains=q) | Q(user__full_name__icontains=q)
            )
        return paginate_queryset(qs, page=page)

    @classmethod
    def list_payments(cls, actor, *, q: str = "", status: str = "", page=1):
        AccessControlService.require_permission(actor, "billing.view_payments")
        qs = PaymentTransaction.objects.select_related("user", "subscription").order_by(
            "-created_at"
        )
        if status:
            qs = qs.filter(status=status)
        if q:
            qs = qs.filter(
                Q(user__email__icontains=q)
                | Q(gateway_ref__icontains=q)
                | Q(plan_code__icontains=q)
            )
        return paginate_queryset(qs, page=page)

    @classmethod
    def get_subscription(cls, actor, subscription_id) -> Subscription:
        AccessControlService.require_permission(actor, "billing.view_subscriptions")
        try:
            return Subscription.objects.select_related("user").get(pk=subscription_id)
        except Subscription.DoesNotExist as exc:
            raise BillingStaffError("Not found.", code="not_found") from exc

    @classmethod
    @transaction.atomic
    def manual_grant_premium(cls, *, actor, user_id, notes: str = "") -> Subscription:
        """
        Audited Admin/Super Admin grant (docs/03 §4.11, docs/09 §6).
        Duration = approved PlanCatalog default plan days — not invented.
        """
        AccessControlService.require_permission(actor, "billing.manual_grant")
        try:
            user = UserAccount.objects.get(pk=user_id)
        except UserAccount.DoesNotExist as exc:
            raise BillingStaffError("User not found.", code="not_found") from exc
        plan = PlanCatalog.default_plan()
        now = timezone.now()
        duration = timedelta(days=plan.duration_days)
        sub = SubscriptionService.get_or_create_for_user(user)
        locked = Subscription.objects.select_for_update().get(pk=sub.pk)
        if (
            locked.state == SubscriptionState.PREMIUM_ACTIVE
            and locked.premium_expires_at is not None
            and locked.premium_expires_at > now
        ):
            new_expiry = locked.premium_expires_at + duration
            started = locked.premium_started_at or now
        else:
            new_expiry = now + duration
            started = now
        locked.state = SubscriptionState.PREMIUM_ACTIVE
        locked.premium_started_at = started
        locked.premium_expires_at = new_expiry
        locked.save(
            update_fields=[
                "state",
                "premium_started_at",
                "premium_expires_at",
                "updated_at",
            ]
        )
        EntitlementGrant.objects.create(
            user=user,
            capability_code=CAPABILITY_PREMIUM,
            starts_at=now,
            ends_at=new_expiry,
            source="manual",
            granted_by=actor,
            is_active=True,
            notes=(notes or f"manual_grant:{actor.id}")[:500],
        )
        AuditService.record(
            action="subscription_manual_grant",
            actor_user=actor,
            target_type="subscription",
            target_id=str(locked.id),
            metadata={
                "user_id": str(user.id),
                "plan_code": plan.code,
                "premium_expires_at": new_expiry.isoformat(),
                "duration_days": plan.duration_days,
            },
        )
        return locked

    @classmethod
    @transaction.atomic
    def manual_revoke_premium(cls, *, actor, user_id, notes: str = "") -> Subscription:
        AccessControlService.require_permission(actor, "billing.manual_grant")
        try:
            user = UserAccount.objects.get(pk=user_id)
        except UserAccount.DoesNotExist as exc:
            raise BillingStaffError("User not found.", code="not_found") from exc
        sub = SubscriptionService.get_or_create_for_user(user)
        locked = Subscription.objects.select_for_update().get(pk=sub.pk)
        locked.state = SubscriptionState.REVOKED
        locked.save(update_fields=["state", "updated_at"])
        EntitlementGrant.objects.filter(
            user=user, capability_code=CAPABILITY_PREMIUM, is_active=True
        ).update(is_active=False)
        AuditService.record(
            action="subscription_manual_revoke",
            actor_user=actor,
            target_type="subscription",
            target_id=str(locked.id),
            metadata={"user_id": str(user.id), "notes": (notes or "")[:200]},
        )
        return locked
