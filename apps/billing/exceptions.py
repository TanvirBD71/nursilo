"""Billing-domain errors (presentation maps these; no payment proof from clients)."""


class BillingError(Exception):
    def __init__(self, message: str = "Billing error."):
        self.message = message
        super().__init__(message)


class PlanNotFound(BillingError):
    def __init__(self, message: str = "Selected plan is not available."):
        super().__init__(message)


class PaymentNotConfigured(BillingError):
    def __init__(
        self,
        message: str = "Payment gateway is not configured. Checkout is unavailable.",
    ):
        super().__init__(message)


class PaymentProviderError(BillingError):
    def __init__(self, message: str = "Payment provider request failed."):
        super().__init__(message)


class PaymentVerificationFailed(BillingError):
    def __init__(self, message: str = "Payment could not be verified."):
        super().__init__(message)


class PaymentNotFound(BillingError):
    def __init__(self, message: str = "Payment transaction not found."):
        super().__init__(message)


class PaymentForbidden(BillingError):
    def __init__(self, message: str = "You cannot access this payment."):
        super().__init__(message)


class EmailVerificationRequired(BillingError):
    def __init__(
        self,
        message: str = "Verify your email before starting premium checkout.",
    ):
        super().__init__(message)
