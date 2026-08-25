"""Deterministic fake payment provider for UNIT-8 tests (no network)."""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any, ClassVar

from apps.billing.services.providers.base import (
    CheckoutSessionRequest,
    CheckoutSessionResult,
    ProviderValidationResult,
)


class FakePaymentProvider:
    """
    Test double. Configure outcomes via class-level flags between tests.

    validate_mode:
      - "success" → VALID with payload amount/currency
      - "fail" → failed validation
      - "amount_mismatch" → VALID but amount 0.01
    """

    name = "fake"
    configured: ClassVar[bool] = True
    validate_mode: ClassVar[str] = "success"
    require_hash: ClassVar[bool] = False
    last_session: ClassVar[CheckoutSessionRequest | None] = None

    @classmethod
    def reset(cls) -> None:
        cls.configured = True
        cls.validate_mode = "success"
        cls.require_hash = False
        cls.last_session = None

    def is_configured(self) -> bool:
        return bool(self.configured)

    def create_checkout_session(
        self, request: CheckoutSessionRequest
    ) -> CheckoutSessionResult:
        type(self).last_session = request
        if not self.is_configured():
            return CheckoutSessionResult(ok=False, error="Fake provider not configured.")
        return CheckoutSessionResult(
            ok=True,
            gateway_url=f"https://fake-gateway.test/pay/{request.tran_id}",
            session_key=f"fake-session-{request.tran_id}",
            raw={"status": "SUCCESS"},
        )

    def verify_callback_authenticity(self, payload: dict[str, Any]) -> bool:
        if not self.require_hash:
            return True
        return str(payload.get("verify_sign") or "") == "valid-fake-sign"

    def validate_transaction(self, payload: dict[str, Any]) -> ProviderValidationResult:
        tran_id = str(payload.get("tran_id") or "")
        val_id = str(payload.get("val_id") or f"VAL-{tran_id}")
        mode = self.validate_mode
        if mode == "fail":
            return ProviderValidationResult(
                ok=False,
                status="FAILED",
                tran_id=tran_id,
                val_id=val_id,
                error="Fake validation failed.",
            )
        try:
            amount = Decimal(str(payload.get("amount", "0"))).quantize(Decimal("0.01"))
        except (InvalidOperation, ValueError):
            amount = Decimal("0.00")
        if mode == "amount_mismatch":
            amount = Decimal("0.01")
        currency = str(payload.get("currency") or payload.get("currency_type") or "BDT")
        return ProviderValidationResult(
            ok=True,
            status="VALID",
            tran_id=tran_id,
            val_id=val_id,
            amount=amount,
            currency=currency.upper(),
            raw={"status": "VALID", "tran_id": tran_id, "val_id": val_id},
        )
