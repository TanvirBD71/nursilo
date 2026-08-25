"""Identity foundation — UserAccount + AcademicProfile + session/token security (docs/05, docs/07)."""
import uuid

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone

from apps.accounts.profile import BloodGroup, academic_session_choices
from apps.common.choices import LocaleCode
from apps.common.models import TimeStampedModel, UUIDPrimaryKeyModel


class UserAccountManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email).lower()
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        extra_fields.setdefault("is_active", True)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self._create_user(email, password, **extra_fields)


class UserAccount(AbstractBaseUser, PermissionsMixin, TimeStampedModel):
    """
    Authenticatable principal (docs/05 UserAccount).

    Domain RBAC lives in apps.rbac.RoleAssignment — not Django Groups.
    is_staff / is_superuser exist only for Django admin bootstrap compatibility.
    Account availability uses is_active (suspension); email_verified_at tracks verification.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(max_length=254, unique=True, db_index=True)
    full_name = models.CharField(max_length=255, blank=True, default="")
    ui_locale = models.CharField(
        max_length=5,
        choices=LocaleCode.choices,
        default=LocaleCode.BN,
    )
    is_active = models.BooleanField(default=True, db_index=True)
    is_staff = models.BooleanField(default=False)
    email_verified_at = models.DateTimeField(null=True, blank=True)
    date_joined = models.DateTimeField(default=timezone.now)
    # Login abuse protection (docs/07 §7) — not a second identity model
    failed_login_count = models.PositiveIntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)

    objects = UserAccountManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []

    class Meta:
        db_table = "user_accounts"
        indexes = [
            models.Index(fields=["is_active"]),
        ]

    def __str__(self):
        return self.email

    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.email.strip().lower()
        super().save(*args, **kwargs)

    @property
    def is_email_verified(self) -> bool:
        return self.email_verified_at is not None

    def is_locked(self, *, now=None) -> bool:
        now = now or timezone.now()
        return bool(self.locked_until and self.locked_until > now)


class AcademicProfile(UUIDPrimaryKeyModel, TimeStampedModel):
    """Owned child of UserAccount (docs/05 §5.1, docs/06 §8.2)."""

    user = models.OneToOneField(
        UserAccount,
        on_delete=models.PROTECT,
        related_name="academic_profile",
    )
    academic_program = models.TextField(blank=True, default="")
    institution = models.TextField(blank=True, default="")
    current_semester_year = models.TextField(blank=True, default="")
    expected_graduation_year = models.PositiveIntegerField(null=True, blank=True)
    current_study_goal = models.TextField(null=True, blank=True)
    # Gate D learner profile (additive; not a second identity model)
    mobile_number = models.CharField(max_length=32, blank=True, default="")
    academic_session = models.CharField(
        max_length=16,
        blank=True,
        default="",
        choices=academic_session_choices(),
    )
    blood_group = models.CharField(
        max_length=8,
        blank=True,
        default="",
        choices=BloodGroup.choices,
    )
    social_profile_url = models.URLField(blank=True, default="")
    linkedin_url = models.URLField(blank=True, default="")
    address = models.TextField(blank=True, default="")

    class Meta:
        db_table = "academic_profiles"

    def __str__(self):
        return f"AcademicProfile({self.user_id})"


class UserSessionStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    REVOKED = "revoked", "Revoked"
    EXPIRED = "expired", "Expired"


class UserSession(UUIDPrimaryKeyModel, TimeStampedModel):
    """
    Server-side session/device tracking (docs/07 §6 logical UserSession).

    Additive persistence justified by concurrent-session policy (docs/07 §4).
    Does not replace Django's session store — links to it via session_key.
    """

    user = models.ForeignKey(
        UserAccount,
        on_delete=models.CASCADE,
        related_name="sessions",
    )
    session_key = models.CharField(max_length=40, unique=True, db_index=True)
    device_name = models.CharField(max_length=128, blank=True, default="")
    browser = models.CharField(max_length=64, blank=True, default="")
    operating_system = models.CharField(max_length=64, blank=True, default="")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    country = models.CharField(max_length=64, blank=True, default="")
    user_agent = models.TextField(blank=True, default="")
    created_time = models.DateTimeField(default=timezone.now, db_index=True)
    last_activity = models.DateTimeField(default=timezone.now, db_index=True)
    expires_at = models.DateTimeField(db_index=True)
    remember_me = models.BooleanField(default=False)
    status = models.CharField(
        max_length=16,
        choices=UserSessionStatus.choices,
        default=UserSessionStatus.ACTIVE,
        db_index=True,
    )

    class Meta:
        db_table = "user_sessions"
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["user", "last_activity"]),
        ]

    def __str__(self):
        return f"UserSession({self.user_id}:{self.status})"

    @property
    def is_active_status(self) -> bool:
        return self.status == UserSessionStatus.ACTIVE


class AuthTokenPurpose(models.TextChoices):
    PASSWORD_RESET = "password_reset", "Password Reset"
    EMAIL_VERIFICATION = "email_verification", "Email Verification"


class AuthToken(UUIDPrimaryKeyModel):
    """
    Secure single-use tokens (docs/07 §16, §20).

    Only a one-way hash of the token is stored. Never log raw tokens.
    """

    user = models.ForeignKey(
        UserAccount,
        on_delete=models.CASCADE,
        related_name="auth_tokens",
    )
    purpose = models.CharField(max_length=32, choices=AuthTokenPurpose.choices, db_index=True)
    token_hash = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    expires_at = models.DateTimeField(db_index=True)
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "auth_tokens"
        indexes = [
            models.Index(fields=["user", "purpose", "-created_at"]),
        ]

    def __str__(self):
        return f"AuthToken({self.purpose}:{self.user_id})"

    @property
    def is_used(self) -> bool:
        return self.used_at is not None

    def is_expired(self, *, now=None) -> bool:
        now = now or timezone.now()
        return now >= self.expires_at

    def is_valid(self, *, now=None) -> bool:
        return not self.is_used and not self.is_expired(now=now)
