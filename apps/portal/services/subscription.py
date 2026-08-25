"""Subscription status presentation — read-only (docs/05, docs/09)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from apps.common.choices import SubscriptionState
from apps.entitlements.services import EntitlementService


@dataclass(frozen=True)
class SubscriptionPresentation:
    state: str
    label: str
    is_premium: bool
    premium_expires_at: datetime | None
    has_row: bool
    source: str  # "subscription_row" | "default_free"
    tier: str = "free"  # free | pending | active | expired | revoked


class SubscriptionPresentationService:
    """
    Present effective entitlement/subscription honestly.
    Premium comes from EntitlementService — never invent Premium from the client.
    """

    STATE_LABELS = {
        SubscriptionState.FREE: "Free",
        SubscriptionState.PENDING_PAYMENT: "Pending payment",
        SubscriptionState.PREMIUM_ACTIVE: "Premium",
        SubscriptionState.EXPIRED: "Expired",
        SubscriptionState.REVOKED: "Revoked",
    }

    @classmethod
    def for_user(cls, user) -> SubscriptionPresentation:
        snap = EntitlementService.snapshot(user)
        # If premium by time but state label should still say Premium when active.
        state = snap.state
        if snap.is_premium:
            label = cls.STATE_LABELS[SubscriptionState.PREMIUM_ACTIVE]
        else:
            label = cls.STATE_LABELS.get(state, state)
        return SubscriptionPresentation(
            state=state,
            label=label,
            is_premium=snap.is_premium,
            premium_expires_at=snap.premium_expires_at,
            has_row=snap.has_row,
            source="subscription_row" if snap.has_row else "default_free",
            tier=snap.tier,
        )
