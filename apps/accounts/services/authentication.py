"""Authentication flows — login/logout/password/email (docs/07, docs/09)."""
from __future__ import annotations

from django.contrib.auth import login as django_login
from django.contrib.auth import logout as django_logout
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.accounts.exceptions import (
    AccountInactive,
    AccountLocked,
    AuthenticationFailed,
    EmailAlreadyVerified,
    InvalidToken,
    PasswordPolicyError,
    RateLimited,
)
from apps.accounts.models import AuthTokenPurpose, UserAccount
from apps.accounts.policy import (
    ACCOUNT_LOCK_DURATION,
    FAILED_LOGIN_THRESHOLD,
    GENERIC_AUTH_FAILURE_MESSAGE,
    GENERIC_PASSWORD_RESET_MESSAGE,
    GENERIC_VERIFICATION_RESEND_MESSAGE,
)
from apps.accounts.services.email_delivery import EmailDeliveryService
from apps.accounts.services.reauth import ReauthService
from apps.accounts.services.sessions import SessionService
from apps.accounts.services.tokens import TokenService
from apps.accounts.services.account import AccountService
from apps.audit.services import AuditService


class AuthenticationService:
    @staticmethod
    def _validate_new_password(user: UserAccount, password: str) -> None:
        try:
            validate_password(password, user=user)
        except ValidationError as exc:
            raise PasswordPolicyError("; ".join(exc.messages)) from exc

    @classmethod
    def _record_login_failure(cls, *, user: UserAccount | None, request, email: str) -> None:
        AuditService.record(
            action="login_failure",
            actor_user=user,
            target_type="user_account",
            target_id=str(user.id) if user else "",
            metadata={"email_domain": (email or "").split("@")[-1]},
        )
        if user is None:
            return
        user.failed_login_count = (user.failed_login_count or 0) + 1
        updates = ["failed_login_count", "updated_at"]
        if user.failed_login_count >= FAILED_LOGIN_THRESHOLD:
            user.locked_until = timezone.now() + ACCOUNT_LOCK_DURATION
            updates.append("locked_until")
            AuditService.record(
                action="account_locked",
                actor_user=user,
                target_type="user_account",
                target_id=str(user.id),
                metadata={"threshold": FAILED_LOGIN_THRESHOLD},
            )
        user.save(update_fields=updates)

    @classmethod
    def _clear_lockout(cls, user: UserAccount) -> None:
        if user.failed_login_count or user.locked_until:
            user.failed_login_count = 0
            user.locked_until = None
            user.save(update_fields=["failed_login_count", "locked_until", "updated_at"])

    @classmethod
    def login(cls, *, request, email: str, password: str, remember_me: bool = False) -> UserAccount:
        email = (email or "").strip().lower()
        user = UserAccount.objects.filter(email=email).first()

        if user is not None and user.is_locked():
            cls._record_login_failure(user=user, request=request, email=email)
            raise AccountLocked()

        if user is None or not user.check_password(password):
            cls._record_login_failure(user=user, request=request, email=email)
            raise AuthenticationFailed(GENERIC_AUTH_FAILURE_MESSAGE)

        if not user.is_active:
            cls._record_login_failure(user=user, request=request, email=email)
            raise AccountInactive()

        # Session fixation protection: rotate session key before binding UserSession
        if request.session.session_key:
            request.session.cycle_key()
        else:
            request.session.save()
            request.session.cycle_key()

        django_login(request, user)
        # Ensure request.user is bound even when AuthenticationMiddleware has not run
        # (e.g. service-level RequestFactory tests).
        request.user = user
        with transaction.atomic():
            SessionService.create_for_request(
                user=user, request=request, remember_me=bool(remember_me)
            )
            cls._clear_lockout(user)
        ReauthService.clear(request)

        AuditService.record(
            action="login_success",
            actor_user=user,
            target_type="user_account",
            target_id=str(user.id),
            metadata={
                "device_hint": request.META.get("HTTP_USER_AGENT", "")[:80],
                "remember_me": bool(remember_me),
            },
        )
        return user

    @classmethod
    def logout_current(cls, request) -> None:
        user = request.user if getattr(request.user, "is_authenticated", False) else None
        current = SessionService.get_current(request)
        if current is not None:
            SessionService.revoke_session(current, reason="logout_current", actor=user)
        django_logout(request)
        if user is not None:
            AuditService.record(
                action="logout",
                actor_user=user,
                target_type="user_account",
                target_id=str(user.id),
                metadata={"scope": "current"},
            )

    @classmethod
    def logout_all_devices(cls, request, *, password: str) -> None:
        """Requires re-auth (docs/07 §22, §26B). Ends all sessions; user must log in again."""
        user = request.user
        ReauthService.confirm_password(user=user, password=password, request=request)
        SessionService.revoke_all_for_user(user, reason="logout_all", actor=user)
        django_logout(request)
        AuditService.record(
            action="logout",
            actor_user=user,
            target_type="user_account",
            target_id=str(user.id),
            metadata={"scope": "all"},
        )

    @classmethod
    def logout_other_devices(cls, request, *, password: str) -> int:
        user = request.user
        ReauthService.confirm_password(user=user, password=password, request=request)
        ReauthService.require_fresh(request, action="logout_all_devices")
        current = SessionService.get_current(request)
        count = SessionService.revoke_all_for_user(
            user, reason="logout_others", actor=user, except_session=current
        )
        return count

    @classmethod
    @transaction.atomic
    def change_password(
        cls, *, request, current_password: str, new_password: str
    ) -> UserAccount:
        user = request.user
        ReauthService.confirm_password(user=user, password=current_password, request=request)
        cls._validate_new_password(user, new_password)
        user.set_password(new_password)
        user.save(update_fields=["password", "updated_at"])

        current = SessionService.get_current(request)
        SessionService.revoke_all_for_user(
            user, reason="password_change", actor=user, except_session=current
        )
        if current is not None:
            SessionService.rotate_current_session_key(request, current)
        # Keep auth backend session valid after set_password
        from django.contrib.auth import update_session_auth_hash

        update_session_auth_hash(request, user)

        AuditService.record(
            action="password_changed",
            actor_user=user,
            target_type="user_account",
            target_id=str(user.id),
        )
        return user

    @classmethod
    def request_password_reset(cls, *, email: str) -> str:
        """Always returns generic message — no account enumeration (docs/07 §7, §16)."""
        email = (email or "").strip().lower()
        user = UserAccount.objects.filter(email=email, is_active=True).first()
        if user is not None:
            try:
                _row, raw = TokenService.issue_password_reset(user)
                EmailDeliveryService.send(
                    subject="Reset your Nursilo password",
                    message=(
                        "A password reset was requested for your Nursilo account.\n\n"
                        f"Reset token: {raw}\n\n"
                        "If you did not request this, you can ignore this message."
                    ),
                    recipient=user.email,
                )
            except RateLimited:
                pass
            except Exception:
                pass
        return GENERIC_PASSWORD_RESET_MESSAGE

    @classmethod
    @transaction.atomic
    def reset_password(cls, *, raw_token: str, new_password: str) -> UserAccount:
        token = TokenService.consume(
            raw_token=raw_token, purpose=AuthTokenPurpose.PASSWORD_RESET
        )
        user = token.user
        if not user.is_active:
            raise InvalidToken()
        cls._validate_new_password(user, new_password)
        user.set_password(new_password)
        user.save(update_fields=["password", "updated_at"])
        cls._clear_lockout(user)
        # Password reset invalidates all other sessions (docs/07 §4) — no live request session
        SessionService.revoke_all_for_user(user, reason="password_reset", actor=user)
        AuditService.record(
            action="password_reset",
            actor_user=user,
            target_type="user_account",
            target_id=str(user.id),
        )
        return user

    @classmethod
    def resend_email_verification(cls, *, email: str) -> str:
        """Generic response — avoid revealing verification state to strangers."""
        email = (email or "").strip().lower()
        user = UserAccount.objects.filter(email=email, is_active=True).first()
        if user is not None and not user.is_email_verified:
            try:
                _row, raw = TokenService.issue_email_verification(user, enforce_cooldown=True)
                EmailDeliveryService.send(
                    subject="Verify your Nursilo email",
                    message=f"Your verification token: {raw}\n",
                    recipient=user.email,
                )
            except RateLimited:
                pass
            except Exception:
                pass
        return GENERIC_VERIFICATION_RESEND_MESSAGE

    @classmethod
    @transaction.atomic
    def verify_email(cls, *, raw_token: str) -> UserAccount:
        token = TokenService.consume(
            raw_token=raw_token, purpose=AuthTokenPurpose.EMAIL_VERIFICATION
        )
        user = token.user
        if user.is_email_verified:
            raise EmailAlreadyVerified()
        return AccountService.mark_email_verified(user)
