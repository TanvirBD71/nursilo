"""Payment provider factory — SSLCommerz sandbox by default; fake for tests."""
from __future__ import annotations

from django.conf import settings

from apps.billing.services.providers.base import PaymentProviderAdapter
from apps.billing.services.providers.fake import FakePaymentProvider
from apps.billing.services.providers.sslcommerz import SSLCommerzSandboxAdapter


def get_payment_provider() -> PaymentProviderAdapter:
    name = str(getattr(settings, "NURSILO_PAYMENT_PROVIDER", "sslcommerz")).strip().lower()
    if name == "fake":
        return FakePaymentProvider()
    return SSLCommerzSandboxAdapter()


__all__ = [
    "FakePaymentProvider",
    "SSLCommerzSandboxAdapter",
    "get_payment_provider",
]
