"""SSLCommerz sandbox adapter — initiate session + IPN hash + Order Validation API.

Contract source: https://developer.sslcommerz.com/doc/v4/
V1 uses sandbox endpoints only. Credentials come from settings/env — never logged.
"""
from __future__ import annotations

import hashlib
import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from decimal import Decimal, InvalidOperation
from typing import Any

from django.conf import settings

from apps.billing.services.providers.base import (
    CheckoutSessionRequest,
    CheckoutSessionResult,
    ProviderValidationResult,
)

logger = logging.getLogger(__name__)


def _md5_hex(value: str) -> str:
    return hashlib.md5(value.encode("utf-8"), usedforsecurity=False).hexdigest()


class SSLCommerzSandboxAdapter:
    """Sandbox-only SSLCommerz provider. Live mode is intentionally unsupported in V1."""

    name = "sslcommerz"

    def __init__(
        self,
        *,
        store_id: str | None = None,
        store_passwd: str | None = None,
        session_url: str | None = None,
        validation_url: str | None = None,
        timeout: float = 30.0,
    ):
        self.store_id = (store_id if store_id is not None else settings.SSLCOMMERZ_STORE_ID) or ""
        self.store_passwd = (
            store_passwd if store_passwd is not None else settings.SSLCOMMERZ_STORE_PASSWD
        ) or ""
        self.session_url = session_url or settings.SSLCOMMERZ_SESSION_URL
        self.validation_url = validation_url or settings.SSLCOMMERZ_VALIDATION_URL
        self.timeout = timeout

    def is_configured(self) -> bool:
        return bool(self.store_id.strip() and self.store_passwd.strip())

    def create_checkout_session(
        self, request: CheckoutSessionRequest
    ) -> CheckoutSessionResult:
        if not self.is_configured():
            return CheckoutSessionResult(ok=False, error="SSLCommerz credentials are not configured.")

        payload = {
            "store_id": self.store_id,
            "store_passwd": self.store_passwd,
            "total_amount": f"{request.amount.quantize(Decimal('0.01'))}",
            "currency": request.currency,
            "tran_id": request.tran_id,
            "success_url": request.success_url,
            "fail_url": request.fail_url,
            "cancel_url": request.cancel_url,
            "ipn_url": request.ipn_url,
            "cus_name": request.customer_name or "Nursilo Learner",
            "cus_email": request.customer_email,
            "cus_add1": "Dhaka",
            "cus_city": "Dhaka",
            "cus_postcode": "1000",
            "cus_country": "Bangladesh",
            "cus_phone": request.customer_phone or "01700000000",
            "shipping_method": "NO",
            "num_of_item": "1",
            "product_name": request.product_name,
            "product_category": request.product_category,
            "product_profile": "non-physical-goods",
            "value_a": request.value_a,
            "value_b": request.value_b,
            "value_c": request.value_c,
            "value_d": request.value_d,
        }
        try:
            raw = self._post_form(self.session_url, payload)
        except Exception as exc:  # network / parse
            logger.warning("sslcommerz_session_failed reason=%s", type(exc).__name__)
            return CheckoutSessionResult(ok=False, error="Could not start payment session.")

        status = str(raw.get("status", "")).upper()
        gateway_url = str(raw.get("GatewayPageURL") or "").strip()
        if status != "SUCCESS" or not gateway_url:
            reason = str(raw.get("failedreason") or "Gateway session failed.")
            return CheckoutSessionResult(ok=False, error=reason, raw=raw)

        return CheckoutSessionResult(
            ok=True,
            gateway_url=gateway_url,
            session_key=str(raw.get("sessionkey") or ""),
            raw=self._safe_raw(raw),
        )

    def verify_callback_authenticity(self, payload: dict[str, Any]) -> bool:
        """IPN verify_sign check per SSLCommerz hash validation rules."""
        if not self.is_configured():
            return False
        verify_sign = str(payload.get("verify_sign") or "").strip()
        verify_key = str(payload.get("verify_key") or "").strip()
        if not verify_sign or not verify_key:
            return False
        keys = [k.strip() for k in verify_key.split(",") if k.strip()]
        if not keys:
            return False
        sorted_keys = sorted(keys)
        parts: list[str] = []
        for key in sorted_keys:
            parts.append(f"{key}={payload.get(key, '')}")
        parts.append(f"store_passwd={_md5_hex(self.store_passwd)}")
        digest = _md5_hex("&".join(parts))
        return digest == verify_sign

    def validate_transaction(self, payload: dict[str, Any]) -> ProviderValidationResult:
        """Server-to-server Order Validation API (authoritative success proof)."""
        if not self.is_configured():
            return ProviderValidationResult(ok=False, error="SSLCommerz credentials are not configured.")

        val_id = str(payload.get("val_id") or "").strip()
        tran_id = str(payload.get("tran_id") or "").strip()
        if not val_id:
            return ProviderValidationResult(
                ok=False, tran_id=tran_id, error="Missing validation id."
            )

        query = {
            "val_id": val_id,
            "store_id": self.store_id,
            "store_passwd": self.store_passwd,
            "format": "json",
        }
        try:
            raw = self._get_json(self.validation_url, query)
        except Exception as exc:
            logger.warning("sslcommerz_validate_failed reason=%s", type(exc).__name__)
            return ProviderValidationResult(
                ok=False, tran_id=tran_id, val_id=val_id, error="Validation API failed."
            )

        status = str(raw.get("status") or "").upper()
        amount = self._parse_amount(raw.get("amount") or raw.get("currency_amount"))
        currency = str(
            raw.get("currency_type") or raw.get("currency") or ""
        ).upper()
        ok = status in {"VALID", "VALIDATED"} and amount is not None
        return ProviderValidationResult(
            ok=ok,
            status=status,
            tran_id=str(raw.get("tran_id") or tran_id),
            val_id=str(raw.get("val_id") or val_id),
            amount=amount,
            currency=currency,
            error="" if ok else f"Provider status {status or 'unknown'}",
            raw=self._safe_raw(raw),
        )

    def _post_form(self, url: str, data: dict[str, str]) -> dict[str, Any]:
        if not url.startswith(("http://", "https://")):
            raise ValueError("Invalid scheme")
        encoded = urllib.parse.urlencode(data).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=encoded,
            method="POST",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:  # nosec B310
            body = resp.read().decode("utf-8")
        return json.loads(body)

    def _get_json(self, url: str, params: dict[str, str]) -> dict[str, Any]:
        if not url.startswith(("http://", "https://")):
            raise ValueError("Invalid scheme")
        full = f"{url}?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(full, method="GET")
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:  # nosec B310
            body = resp.read().decode("utf-8")
        return json.loads(body)

    @staticmethod
    def _parse_amount(value: Any) -> Decimal | None:
        if value is None or value == "":
            return None
        try:
            return Decimal(str(value)).quantize(Decimal("0.01"))
        except (InvalidOperation, ValueError):
            return None

    @staticmethod
    def _safe_raw(raw: dict[str, Any]) -> dict[str, Any]:
        """Strip credential-like keys before any persistence/logging path."""
        blocked = {
            "store_passwd",
            "store_pass",
            "password",
            "verify_sign",
            "card_no",
        }
        return {k: v for k, v in raw.items() if k not in blocked}
