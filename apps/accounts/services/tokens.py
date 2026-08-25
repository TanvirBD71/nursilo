"""Secure single-use auth tokens — hash only; never log raw tokens (docs/07)."""
from __future__ import annotations

import hashlib
import secrets
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from apps.accounts.exceptions import InvalidToken, RateLimited
from apps.accounts.models import AuthToken, AuthTokenPurpose, UserAccount
from apps.accounts.policy import (
    EMAIL_VERIFICATION_RESEND_COOLDOWN,
    EMAIL_VERIFICATION_TOKEN_TTL,
    PASSWORD_RESET_REQUEST_COOLDOWN,
    PASSWORD_RESET_TOKEN_TTL,
)


def hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


class TokenService:
    @staticmethod
    def _issue(
        *,
        user: UserAccount,
        purpose: str,
        ttl: timedelta,
        cooldown: timedelta | None = None,
    ) -> tuple[AuthToken, str]:
        now = timezone.now()
        if cooldown is not None:
            recent = (
                AuthToken.objects.filter(user=user, purpose=purpose, created_at__gte=now - cooldown)
                .order_by("-created_at")
                .first()
            )
            if recent is not None:
                raise RateLimited()

        # Invalidate outstanding unused tokens of same purpose (single active path)
        AuthToken.objects.filter(
            user=user, purpose=purpose, used_at__isnull=True
        ).update(used_at=now)

        raw = secrets.token_urlsafe(32)
        token = AuthToken.objects.create(
            user=user,
            purpose=purpose,
            token_hash=hash_token(raw),
            expires_at=now + ttl,
        )
        return token, raw

    @classmethod
    def issue_password_reset(cls, user: UserAccount) -> tuple[AuthToken, str]:
        return cls._issue(
            user=user,
            purpose=AuthTokenPurpose.PASSWORD_RESET,
            ttl=PASSWORD_RESET_TOKEN_TTL,
            cooldown=PASSWORD_RESET_REQUEST_COOLDOWN,
        )

    @classmethod
    def issue_email_verification(
        cls, user: UserAccount, *, enforce_cooldown: bool = True
    ) -> tuple[AuthToken, str]:
        return cls._issue(
            user=user,
            purpose=AuthTokenPurpose.EMAIL_VERIFICATION,
            ttl=EMAIL_VERIFICATION_TOKEN_TTL,
            cooldown=EMAIL_VERIFICATION_RESEND_COOLDOWN if enforce_cooldown else None,
        )

    @staticmethod
    @transaction.atomic
    def consume(*, raw_token: str, purpose: str) -> AuthToken:
        token_hash = hash_token(raw_token)
        try:
            token = AuthToken.objects.select_for_update().get(
                token_hash=token_hash, purpose=purpose
            )
        except AuthToken.DoesNotExist as exc:
            raise InvalidToken() from exc
        if not token.is_valid():
            raise InvalidToken()
        token.used_at = timezone.now()
        token.save(update_fields=["used_at"])
        return token
