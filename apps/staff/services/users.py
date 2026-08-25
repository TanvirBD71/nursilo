"""Staff user management — docs/03 §4.1–4.2 (server-authoritative)."""
from __future__ import annotations

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Q

from apps.accounts.models import AcademicProfile, UserAccount
from apps.audit.services import AuditService
from apps.common.choices import RoleCode
from apps.rbac.models import Role, RoleAssignment
from apps.rbac.services import AccessControlService
from apps.staff.services.pagination import paginate_queryset


class UserStaffError(Exception):
    def __init__(self, message: str, *, code: str = "user_error"):
        super().__init__(message)
        self.code = code


class UserStaffService:
    ASSIGNABLE_DISPLAY = [
        RoleCode.STUDENT,
        RoleCode.AUTHOR,
        RoleCode.REVIEWER,
        RoleCode.EDITOR,
        RoleCode.ADMIN,
        RoleCode.SUPER_ADMIN,
    ]

    @classmethod
    def list_users(cls, actor, *, q: str = "", page=1, per_page=25):
        AccessControlService.require_permission(actor, "users.view")
        qs = UserAccount.objects.all().order_by("-date_joined")
        q = (q or "").strip()
        if q:
            qs = qs.filter(Q(email__icontains=q) | Q(full_name__icontains=q))
        page_obj = paginate_queryset(qs, page=page, per_page=per_page)
        rows = []
        for user in page_obj.object_list:
            rows.append(
                {
                    "user": user,
                    "roles": sorted(AccessControlService.role_codes_for(user)),
                }
            )
        return page_obj, rows

    @classmethod
    def get_user(cls, actor, user_id) -> UserAccount:
        AccessControlService.require_permission(actor, "users.view")
        try:
            return UserAccount.objects.get(pk=user_id)
        except UserAccount.DoesNotExist as exc:
            raise UserStaffError("User not found.", code="not_found") from exc

    @classmethod
    @transaction.atomic
    def create_user(
        cls,
        *,
        actor,
        email: str,
        password: str,
        full_name: str = "",
        role_code: str = RoleCode.STUDENT,
    ) -> UserAccount:
        AccessControlService.require_permission(actor, "users.create")
        if not AccessControlService.may_assign_role(actor=actor, role_code=role_code):
            raise UserStaffError("Cannot assign that role.", code="forbidden")
        email = (email or "").strip().lower()
        probe = UserAccount(email=email, full_name=full_name or "")
        try:
            validate_password(password, user=probe)
        except ValidationError as exc:
            raise UserStaffError("; ".join(exc.messages), code="password") from exc
        if UserAccount.objects.filter(email=email).exists():
            raise UserStaffError("Email already registered.", code="duplicate")
        try:
            user = UserAccount.objects.create_user(
                email=email,
                password=password,
                full_name=(full_name or "").strip(),
                is_active=True,
            )
        except IntegrityError as exc:
            raise UserStaffError("Email already registered.", code="duplicate") from exc
        AcademicProfile.objects.get_or_create(user=user)
        AccessControlService.assign_role(
            user=user, role_code=role_code, assigned_by=actor
        )
        AuditService.record(
            action="user_created",
            actor_user=actor,
            target_type="user_account",
            target_id=str(user.id),
            metadata={"email": user.email, "role": role_code},
        )
        return user

    @classmethod
    @transaction.atomic
    def update_user(cls, *, actor, user: UserAccount, full_name: str, is_active: bool):
        AccessControlService.require_permission(actor, "users.edit")
        cls._guard_super_admin_target(actor, user)
        user.full_name = (full_name or "").strip()
        # Disable uses users.disable; reactivation uses users.edit.
        if user.is_active and not is_active:
            AccessControlService.require_permission(actor, "users.disable")
        user.is_active = bool(is_active)
        user.save(update_fields=["full_name", "is_active", "updated_at"])
        AuditService.record(
            action="user_updated",
            actor_user=actor,
            target_type="user_account",
            target_id=str(user.id),
            metadata={"is_active": user.is_active},
        )
        return user

    @classmethod
    @transaction.atomic
    def set_roles(cls, *, actor, user: UserAccount, role_codes: list[str]):
        AccessControlService.require_permission(actor, "roles.assign")
        cls._guard_super_admin_target(actor, user)
        desired = set(role_codes or [])
        for code in desired:
            if not AccessControlService.may_assign_role(actor=actor, role_code=code):
                raise UserStaffError(f"Cannot assign role '{code}'.", code="forbidden")
        current = AccessControlService.role_codes_for(user)
        # Protect last Super Admin (docs/03 §4.1 notes).
        if RoleCode.SUPER_ADMIN in current and RoleCode.SUPER_ADMIN not in desired:
            remaining = (
                RoleAssignment.objects.filter(role__code=RoleCode.SUPER_ADMIN)
                .exclude(user=user)
                .count()
            )
            if remaining < 1:
                raise UserStaffError(
                    "Cannot remove the last Super Admin.",
                    code="last_super_admin",
                )
            if not AccessControlService.is_super_admin(actor):
                raise UserStaffError(
                    "Only Super Admin may revoke Super Admin.",
                    code="forbidden",
                )
        for code in current - desired:
            if code == RoleCode.SUPER_ADMIN and not AccessControlService.is_super_admin(
                actor
            ):
                raise UserStaffError(
                    "Only Super Admin may revoke Super Admin.",
                    code="forbidden",
                )
            AccessControlService.revoke_role(
                user=user, role_code=code, revoked_by=actor
            )
        for code in desired - current:
            AccessControlService.assign_role(
                user=user, role_code=code, assigned_by=actor
            )
        return sorted(AccessControlService.role_codes_for(user))

    @classmethod
    def assignable_roles_for(cls, actor) -> list[tuple[str, str]]:
        choices = []
        for code in cls.ASSIGNABLE_DISPLAY:
            if AccessControlService.may_assign_role(actor=actor, role_code=code):
                choices.append((code, dict(RoleCode.choices).get(code, code)))
        return choices

    @classmethod
    def _guard_super_admin_target(cls, actor, user):
        if AccessControlService.is_super_admin(user) and not AccessControlService.is_super_admin(
            actor
        ):
            raise UserStaffError(
                "Cannot modify a Super Admin account.",
                code="forbidden",
            )
