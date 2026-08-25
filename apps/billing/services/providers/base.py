"""Replaceable payment provider adapter boundary (docs/04 BillingService)."""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Protocol


@dataclass(frozen=True)
class CheckoutSessionRequest:
    tran_id: str
    amount: Decimal
    currency: str
    product_name: str
    product_category: str
    success_url: str
    fail_url: str
    cancel_url: str
    ipn_url: str
    customer_name: str
    customer_email: str
    customer_phone: str
    value_a: str = ""
    value_b: str = ""
    value_c: str = ""
    value_d: str = ""


@dataclass(frozen=True)
class CheckoutSessionResult:
    ok: bool
    gateway_url: str = ""
    session_key: str = ""
    error: str = ""
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ProviderValidationResult:
    ok: bool
    status: str = ""
    tran_id: str = ""
    val_id: str = ""
    amount: Decimal | None = None
    currency: str = ""
    error: str = ""
    raw: dict[str, Any] = field(default_factory=dict)


class PaymentProviderAdapter(Protocol):
    name: str

    def is_configured(self) -> bool: ...

    def create_checkout_session(
        self, request: CheckoutSessionRequest
    ) -> CheckoutSessionResult: ...

    def verify_callback_authenticity(self, payload: dict[str, Any]) -> bool: ...

    def validate_transaction(self, payload: dict[str, Any]) -> ProviderValidationResult: ...
