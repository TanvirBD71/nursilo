"""Billing foundation — subscriptions and payment facts (docs/05 §6, docs/06 §8.4–8.5)."""
from django.conf import settings
from django.db import models

from apps.common.choices import PaymentGateway, PaymentStatus, SubscriptionState
from apps.common.models import CreatedOnlyModel, TimeStampedModel, UUIDPrimaryKeyModel


class Subscription(UUIDPrimaryKeyModel, TimeStampedModel):
    """One effective subscription row per user in V1 (docs/06 §22)."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="subscription",
    )
    state = models.CharField(
        max_length=32,
        choices=SubscriptionState.choices,
        default=SubscriptionState.FREE,
        db_index=True,
    )
    premium_started_at = models.DateTimeField(null=True, blank=True)
    premium_expires_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        db_table = "subscriptions"
        indexes = [
            models.Index(fields=["state"]),
            models.Index(fields=["premium_expires_at"]),
        ]

    def __str__(self):
        return f"Subscription({self.user_id}:{self.state})"


class PaymentTransaction(UUIDPrimaryKeyModel, CreatedOnlyModel):
    """Append-oriented payment fact — no entitlement grant logic here."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="payment_transactions",
    )
    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.PROTECT,
        related_name="payment_transactions",
    )
    gateway = models.CharField(max_length=32, choices=PaymentGateway.choices)
    gateway_ref = models.CharField(max_length=255)
    plan_code = models.CharField(max_length=64, db_index=True, default="")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=8, default="BDT")
    status = models.CharField(
        max_length=32,
        choices=PaymentStatus.choices,
        default=PaymentStatus.INITIATED,
        db_index=True,
    )
    raw_event_fingerprint = models.TextField(blank=True, default="")
    confirmed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "payment_transactions"
        constraints = [
            models.UniqueConstraint(
                fields=["gateway", "gateway_ref"],
                name="uq_payment_transactions_gateway_ref",
            ),
        ]
        indexes = [
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"Payment({self.gateway}:{self.gateway_ref})"
