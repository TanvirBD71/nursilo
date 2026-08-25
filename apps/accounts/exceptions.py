"""Account / authentication domain exceptions (no secrets in messages)."""


class AccountError(Exception):
    """Base account/auth error with a safe user-facing message."""

    default_message = "The request could not be completed."

    def __init__(self, message: str | None = None):
        self.message = message or self.default_message
        super().__init__(self.message)


class AuthenticationFailed(AccountError):
    default_message = "Invalid email or password."


class AccountInactive(AccountError):
    default_message = "This account is not available."


class AccountLocked(AccountError):
    default_message = "Too many failed attempts. Please try again later."


class SessionLimitExceeded(AccountError):
    default_message = "Maximum concurrent sessions reached. Sign out another device first."


class InvalidToken(AccountError):
    default_message = "This link is invalid or has expired."


class PasswordPolicyError(AccountError):
    default_message = "Password does not meet security requirements."


class ReauthenticationRequired(AccountError):
    default_message = "Please confirm your password to continue."


class ReauthenticationFailed(AccountError):
    default_message = "Password confirmation failed."


class RateLimited(AccountError):
    default_message = "Please wait before trying again."


class EmailAlreadyVerified(AccountError):
    default_message = "Email is already verified."


class EmailAlreadyRegistered(AccountError):
    default_message = "An account with this email already exists."
