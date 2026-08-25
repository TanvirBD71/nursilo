"""Authoritative subscription plan catalog (V1 — Annual Premium only).

Pricing and duration live here (and settings overrides), not as scattered
literals inside payment/subscription/entitlement workflows.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from django.conf import settings


@dataclass(frozen=True)
class PlanDefinition:
    code: str
    name: str
    amount: Decimal
    currency: str
    duration_days: int
    description: str

    @property
    def display_price(self) -> str:
        quantized = self.amount.quantize(Decimal("0.01"))
        if quantized == quantized.to_integral():
            return f"৳{int(quantized)}"
        return f"৳{quantized}"


class PlanCatalog:
    """Single source of plan data for checkout, activation, and presentation."""

    ANNUAL_PREMIUM = "annual_premium"

    @classmethod
    def _annual_premium(cls) -> PlanDefinition:
        amount = Decimal(str(getattr(settings, "NURSILO_PLAN_ANNUAL_PREMIUM_AMOUNT", "199")))
        duration = int(getattr(settings, "NURSILO_PLAN_ANNUAL_PREMIUM_DURATION_DAYS", 365))
        code = str(
            getattr(settings, "NURSILO_PLAN_ANNUAL_PREMIUM_CODE", cls.ANNUAL_PREMIUM)
        ).strip() or cls.ANNUAL_PREMIUM
        name = str(
            getattr(settings, "NURSILO_PLAN_ANNUAL_PREMIUM_NAME", "Annual Premium")
        ).strip() or "Annual Premium"
        return PlanDefinition(
            code=code,
            name=name,
            amount=amount,
            currency="BDT",
            duration_days=duration,
            description=f"{name} — {duration} days of Premium library and premium features.",
        )

    @classmethod
    def all_active(cls) -> list[PlanDefinition]:
        """V1: only Annual Premium is offered."""
        return [cls._annual_premium()]

    @classmethod
    def get(cls, plan_code: str) -> PlanDefinition | None:
        code = (plan_code or "").strip()
        for plan in cls.all_active():
            if plan.code == code:
                return plan
        return None

    @classmethod
    def require(cls, plan_code: str) -> PlanDefinition:
        plan = cls.get(plan_code)
        if plan is None:
            raise LookupError(f"Unknown or inactive plan: {plan_code}")
        return plan

    @classmethod
    def default_plan(cls) -> PlanDefinition:
        return cls._annual_premium()
