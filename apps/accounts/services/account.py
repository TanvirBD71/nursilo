"""AccountService — registration and profile (docs/04, docs/09 §3)."""
from __future__ import annotations

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.accounts.exceptions import EmailAlreadyRegistered, PasswordPolicyError
from apps.accounts.models import AcademicProfile, UserAccount
from apps.accounts.services.email_delivery import EmailDeliveryService
from apps.accounts.services.tokens import TokenService
from apps.audit.services import AuditService
from apps.common.choices import RoleCode
from apps.rbac.services import AccessControlService


class AccountService:
    @staticmethod
    @transaction.atomic
    def register(
        *,
        email: str,
        password: str,
        full_name: str = "",
        request=None,
        mobile_number: str = "",
        academic_session: str = "",
        blood_group: str = "",
        social_profile_url: str = "",
        linkedin_url: str = "",
        address: str = "",
    ) -> tuple[UserAccount, str | None]:
        """
        Create a Student account and issue email verification.
        Returns (user, raw_verification_token_or_None).
        Raw token is for delivery only — never log/store plaintext.
        """
        email = (email or "").strip().lower()
        try:
            # Validate against a transient user for similarity checks
            probe = UserAccount(email=email, full_name=full_name or "")
            validate_password(password, user=probe)
        except ValidationError as exc:
            raise PasswordPolicyError("; ".join(exc.messages)) from exc

        if UserAccount.objects.filter(email=email).exists():
            raise EmailAlreadyRegistered()

        try:
            user = UserAccount.objects.create_user(
                email=email,
                password=password,
                full_name=(full_name or "").strip(),
                is_active=True,
            )
        except IntegrityError as exc:
            raise EmailAlreadyRegistered() from exc
        AcademicProfile.objects.create(
            user=user,
            mobile_number=(mobile_number or "").strip(),
            academic_session=(academic_session or "").strip(),
            blood_group=(blood_group or "").strip(),
            social_profile_url=(social_profile_url or "").strip(),
            linkedin_url=(linkedin_url or "").strip(),
            address=(address or "").strip(),
        )
        AccessControlService.assign_role(
            user=user, role_code=RoleCode.STUDENT, assigned_by=None
        )

        raw_token = None
        try:
            _token_row, raw_token = TokenService.issue_email_verification(
                user, enforce_cooldown=False
            )
            EmailDeliveryService.send(
                subject="Verify your Nursilo email",
                message=(
                    "Welcome to Nursilo.\n\n"
                    "Use this verification token in the verification form:\n"
                    f"{raw_token}\n\n"
                    "This link expires soon and can be used once."
                ),
                recipient=user.email,
            )
        except Exception:
            # Registration succeeds even if email backend fails; token remains issuable via resend.
            raw_token = raw_token  # noqa: B018 — keep for tests when send works

        AuditService.record(
            action="account_registered",
            actor_user=user,
            target_type="user_account",
            target_id=str(user.id),
            metadata={"email_domain": email.split("@")[-1]},
        )
        return user, raw_token

    @staticmethod
    def mark_email_verified(user: UserAccount, *, actor=None) -> UserAccount:
        if user.email_verified_at is None:
            user.email_verified_at = timezone.now()
            user.save(update_fields=["email_verified_at", "updated_at"])
            AuditService.record(
                action="email_verified",
                actor_user=actor or user,
                target_type="user_account",
                target_id=str(user.id),
            )
        return user

    @staticmethod
    def manual_verify_email(*, actor, user: UserAccount) -> UserAccount:
        AccessControlService.require_permission(actor, "account.manual_verify_email")
        return AccountService.mark_email_verified(user, actor=actor)

    @staticmethod
    def set_active(*, actor, user: UserAccount, is_active: bool) -> UserAccount:
        """Admin/Super Admin suspension or reactivation (docs/09)."""
        AccessControlService.require_permission(actor, "users.disable")
        user.is_active = is_active
        user.save(update_fields=["is_active", "updated_at"])
        AuditService.record(
            action="user_activation_changed",
            actor_user=actor,
            target_type="user_account",
            target_id=str(user.id),
            metadata={"is_active": is_active},
        )
        return user

    @staticmethod
    def update_profile(*, user: UserAccount, full_name: str | None = None, ui_locale: str | None = None):
        fields = []
        if full_name is not None:
            user.full_name = full_name.strip()
            fields.append("full_name")
        if ui_locale is not None:
            user.ui_locale = ui_locale
            fields.append("ui_locale")
        if fields:
            fields.append("updated_at")
            user.save(update_fields=fields)
            AuditService.record(
                action="profile_updated",
                actor_user=user,
                target_type="user_account",
                target_id=str(user.id),
                metadata={"fields": [f for f in fields if f != "updated_at"]},
            )
        return user

    @staticmethod
    def update_academic_profile(
        *,
        user: UserAccount,
        academic_program: str = "",
        institution: str = "",
        current_semester_year: str = "",
        expected_graduation_year: int | None = None,
        current_study_goal: str | None = None,
    ) -> AcademicProfile:
        profile, _created = AcademicProfile.objects.get_or_create(user=user)
        profile.academic_program = (academic_program or "").strip()
        profile.institution = (institution or "").strip()
        profile.current_semester_year = (current_semester_year or "").strip()
        profile.expected_graduation_year = expected_graduation_year
        if current_study_goal is not None:
            cleaned = current_study_goal.strip()
            profile.current_study_goal = cleaned or None
        profile.save()
        AuditService.record(
            action="academic_profile_updated",
            actor_user=user,
            target_type="academic_profile",
            target_id=str(profile.id),
        )
        return profile

    @staticmethod
    def update_learner_profile(
        *,
        user: UserAccount,
        mobile_number: str = "",
        academic_session: str = "",
        blood_group: str = "",
        social_profile_url: str = "",
        linkedin_url: str = "",
        address: str = "",
    ) -> AcademicProfile:
        profile, _created = AcademicProfile.objects.get_or_create(user=user)
        profile.mobile_number = (mobile_number or "").strip()
        profile.academic_session = (academic_session or "").strip()
        profile.blood_group = (blood_group or "").strip()
        profile.social_profile_url = (social_profile_url or "").strip()
        profile.linkedin_url = (linkedin_url or "").strip()
        profile.address = (address or "").strip()
        profile.save(
            update_fields=[
                "mobile_number",
                "academic_session",
                "blood_group",
                "social_profile_url",
                "linkedin_url",
                "address",
                "updated_at",
            ]
        )
        AuditService.record(
            action="learner_profile_updated",
            actor_user=user,
            target_type="academic_profile",
            target_id=str(profile.id),
            metadata={
                "fields": [
                    "mobile_number",
                    "academic_session",
                    "blood_group",
                    "social_profile_url",
                    "linkedin_url",
                    "address",
                ]
            },
        )
        return profile
