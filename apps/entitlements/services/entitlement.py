"""Central Free/Premium entitlement evaluation (docs/05, docs/09 §6).

EntitlementService alone decides capability allow/deny. Assessment/Library
never grant Premium; they ask this service (via access helpers).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from django.db import transaction
from django.utils import timezone

from apps.billing.models import Subscription
from apps.common.choices import SubscriptionState


CAPABILITY_PREMIUM = "premium"


@dataclass(frozen=True)
class EntitlementSnapshot:
    """Honest entitlement presentation for library/subscription UX matrices."""

    tier: str  # free | pending | active | expired | revoked
    is_premium: bool
    state: str
    premium_expires_at: datetime | None
    has_row: bool


class EntitlementService:
    """
    Single Premium evaluation path for web (and future API).

    Source of truth: effective Subscription row + server clock.
    Pending payment never grants Premium. Expired-by-time fails closed.
    """

    @classmethod
    def refresh_expiry(cls, user) -> Subscription | None:
        """Flip PremiumActive → Expired when premium_expires_at is past (server time)."""
        if user is None or not getattr(user, "is_authenticated", False):
            return None
        try:
            sub = Subscription.objects.get(user=user)
        except Subscription.DoesNotExist:
            return None
        now = timezone.now()
        if (
            sub.state == SubscriptionState.PREMIUM_ACTIVE
            and sub.premium_expires_at is not None
            and sub.premium_expires_at <= now
        ):
            with transaction.atomic():
                locked = Subscription.objects.select_for_update().get(pk=sub.pk)
                if (
                    locked.state == SubscriptionState.PREMIUM_ACTIVE
                    and locked.premium_expires_at is not None
                    and locked.premium_expires_at <= now
                ):
                    locked.state = SubscriptionState.EXPIRED
                    locked.save(update_fields=["state", "updated_at"])
                    return locked
        return sub

    @classmethod
    def snapshot(cls, user) -> EntitlementSnapshot:
        if user is None or not getattr(user, "is_authenticated", False):
            return EntitlementSnapshot(
                tier="free",
                is_premium=False,
                state=SubscriptionState.FREE,
                premium_expires_at=None,
                has_row=False,
            )
        sub = cls.refresh_expiry(user)
        if sub is None:
            return EntitlementSnapshot(
                tier="free",
                is_premium=False,
                state=SubscriptionState.FREE,
                premium_expires_at=None,
                has_row=False,
            )
        state = sub.state
        now = timezone.now()
        is_premium = state == SubscriptionState.PREMIUM_ACTIVE and (
            sub.premium_expires_at is None or sub.premium_expires_at > now
        )
        if is_premium:
            tier = "active"
        elif state == SubscriptionState.PENDING_PAYMENT:
            tier = "pending"
        elif state == SubscriptionState.EXPIRED:
            tier = "expired"
        elif state == SubscriptionState.REVOKED:
            tier = "revoked"
        else:
            tier = "free"
        return EntitlementSnapshot(
            tier=tier,
            is_premium=is_premium,
            state=state,
            premium_expires_at=sub.premium_expires_at,
            has_row=True,
        )

    @classmethod
    def is_premium(cls, user) -> bool:
        return cls.snapshot(user).is_premium

    @classmethod
    def has_capability(cls, user, capability_code: str) -> bool:
        code = (capability_code or "").strip().lower()
        if code != CAPABILITY_PREMIUM:
            return False
        return cls.is_premium(user)

    @classmethod
    def decide_premium(cls, user) -> bool:
        """Alias used by domain access services."""
        return cls.is_premium(user)
