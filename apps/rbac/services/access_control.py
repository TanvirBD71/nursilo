"""RBAC permission checks — server-side authority (docs/03, docs/04 AccessControlService)."""
from __future__ import annotations

from apps.common.choices import RoleCode
from apps.rbac.models import RoleAssignment

# Named permissions derived from docs/03 matrices (V1). Absence = deny.
PERMISSIONS_BY_ROLE: dict[str, frozenset[str]] = {
    RoleCode.SUPER_ADMIN: frozenset(
        {
            # Filled by union at runtime via is_super_admin short-circuit;
            # keep explicit super-only + foundation codes for effective_permissions UI.
            "users.view",
            "users.create",
            "users.edit",
            "users.disable",
            "users.delete",
            "roles.view",
            "roles.assign",
            "roles.define",
            "roles.grant_super_admin",
            "audit.view",
            "audit.export",
            "system.settings",
            "sessions.admin_revoke",
            "account.manual_verify_email",
            "content.view_unpublished",
            "content.create_draft",
            "content.edit",
            "content.submit_review",
            "content.approve",
            "content.reject",
            "content.publish",
            "content.archive",
            "content.restore",
            "content.preview_unpublished",
            "content.import",
            "content.export",
            "questions.view_unpublished",
            "questions.create",
            "questions.edit",
            "questions.approve",
            "questions.publish",
            "questions.archive",
            "questions.restore",
            "questions.import",
            "questions.export",
            "questions.view_error_reports",
            "questions.resolve_error_reports",
            "exams.view",
            "exams.create",
            "exams.edit",
            "exams.publish",
            "exams.archive",
            "exams.view_attempts",
            "library.manage",
            "cms.manage",
            "cms.contact_triage",
            "announcements.create",
            "announcements.publish",
            "billing.view_subscriptions",
            "billing.manual_grant",
            "billing.view_payments",
            "billing.configure_gateways",
            "staff.access",
        }
    ),
    RoleCode.ADMIN: frozenset(
        {
            "users.view",
            "users.create",
            "users.edit",
            "users.disable",
            "users.delete",
            "roles.view",
            "roles.assign",
            "audit.view",
            "sessions.admin_revoke",
            "content.view_unpublished",
            "content.create_draft",
            "content.edit",
            "content.submit_review",
            "content.approve",
            "content.reject",
            "content.publish",
            "content.archive",
            "content.restore",
            "content.preview_unpublished",
            "content.import",
            "content.export",
            "questions.view_unpublished",
            "questions.create",
            "questions.edit",
            "questions.approve",
            "questions.publish",
            "questions.archive",
            "questions.restore",
            "questions.import",
            "questions.export",
            "questions.view_error_reports",
            "questions.resolve_error_reports",
            "exams.view",
            "exams.create",
            "exams.edit",
            "exams.publish",
            "exams.archive",
            "exams.view_attempts",
            "library.manage",
            "cms.manage",
            "cms.contact_triage",
            "announcements.create",
            "announcements.publish",
            "billing.view_subscriptions",
            "billing.manual_grant",
            "billing.view_payments",
            "staff.access",
        }
    ),
    RoleCode.EDITOR: frozenset(
        {
            "content.view_unpublished",
            "content.create_draft",
            "content.edit",
            "content.submit_review",
            "content.approve",  # Limited: senior content lead path (docs/03 §5)
            "content.reject",
            "content.publish",
            "content.archive",
            "content.restore",
            "content.preview_unpublished",
            "content.import",
            "content.export",
            "questions.view_unpublished",
            "questions.create",
            "questions.edit",
            "questions.approve",
            "questions.publish",
            "questions.archive",
            "questions.restore",
            "questions.import",
            "questions.export",
            "questions.view_error_reports",
            "questions.resolve_error_reports",
            "exams.view",
            "exams.create",
            "exams.edit",
            "exams.publish",
            "exams.archive",
            "exams.view_attempts",
            "library.manage",
            "cms.manage",
            "announcements.create",
            "announcements.publish",
            "staff.access",
        }
    ),
    RoleCode.REVIEWER: frozenset(
        {
            "content.view_unpublished",
            "content.approve",
            "content.reject",
            "content.preview_unpublished",
            "questions.view_unpublished",
            "questions.approve",
            "questions.view_error_reports",
            "questions.resolve_error_reports",
            "exams.view",
            "staff.access",
        }
    ),
    RoleCode.AUTHOR: frozenset(
        {
            "content.create_draft",
            "content.edit_own_draft",
            "content.submit_review",
            "content.preview_own",
            "questions.create",
            "questions.edit_own",
            "questions.view_own_error_reports",
            "exams.view",
            "exams.create_limited",
            "exams.edit_limited",
            "staff.access",
        }
    ),
    RoleCode.STUDENT: frozenset(
        {
            "account.view_own",
            "account.edit_own_profile",
            "learning.consume_published",
        }
    ),
}

STAFF_ROLES = frozenset(
    {
        RoleCode.SUPER_ADMIN,
        RoleCode.ADMIN,
        RoleCode.EDITOR,
        RoleCode.REVIEWER,
        RoleCode.AUTHOR,
    }
)

# Roles Admin may assign (docs/03 §4.2 — Admin cannot grant Super Admin).
ADMIN_ASSIGNABLE_ROLES = frozenset(
    {
        RoleCode.ADMIN,
        RoleCode.EDITOR,
        RoleCode.REVIEWER,
        RoleCode.AUTHOR,
        RoleCode.STUDENT,
    }
)


class AccessControlService:
    """Fail-closed RBAC checks. UI hiding is not authorization."""

    @staticmethod
    def role_codes_for(user) -> set[str]:
        if user is None or not getattr(user, "is_authenticated", False):
            return set()
        if not getattr(user, "is_active", False):
            return set()
        return set(
            RoleAssignment.objects.filter(user=user).values_list("role__code", flat=True)
        )

    @classmethod
    def has_role(cls, user, role_code: str) -> bool:
        return role_code in cls.role_codes_for(user)

    @classmethod
    def has_any_role(cls, user, role_codes) -> bool:
        codes = cls.role_codes_for(user)
        return bool(codes.intersection(role_codes))

    @classmethod
    def is_super_admin(cls, user) -> bool:
        return cls.has_role(user, RoleCode.SUPER_ADMIN)

    @classmethod
    def is_staff_user(cls, user) -> bool:
        return cls.has_any_role(user, STAFF_ROLES)

    @classmethod
    def effective_permissions(cls, user) -> set[str]:
        if cls.is_super_admin(user):
            # Super Admin inherits all catalogued operational permissions (docs/03 §9.1).
            perms: set[str] = set()
            for role_perms in PERMISSIONS_BY_ROLE.values():
                perms |= set(role_perms)
            perms |= set(PERMISSIONS_BY_ROLE[RoleCode.SUPER_ADMIN])
            return perms
        perms = set()
        for code in cls.role_codes_for(user):
            perms |= set(PERMISSIONS_BY_ROLE.get(code, frozenset()))
        return perms

    @classmethod
    def has_permission(cls, user, permission: str) -> bool:
        if not permission:
            return False
        if cls.is_super_admin(user):
            return True
        return permission in cls.effective_permissions(user)

    @classmethod
    def require_permission(cls, user, permission: str) -> None:
        if not cls.has_permission(user, permission):
            raise PermissionError("Permission denied.")

    @classmethod
    def require_staff(cls, user) -> None:
        if not cls.is_staff_user(user):
            raise PermissionError("Staff access denied.")

    @classmethod
    def may_assign_role(cls, *, actor, role_code: str) -> bool:
        """Role assignment authority (docs/03 §4.2, §8)."""
        if not actor or not getattr(actor, "is_authenticated", False):
            return False
        if cls.is_super_admin(actor):
            return True
        if not cls.has_permission(actor, "roles.assign"):
            return False
        if role_code == RoleCode.SUPER_ADMIN:
            return False
        return role_code in ADMIN_ASSIGNABLE_ROLES

    @classmethod
    def assign_role(cls, *, user, role_code: str, assigned_by=None):
        """Assign a catalog role. Callers must enforce who may assign what."""
        from apps.audit.services import AuditService
        from apps.rbac.models import Role, RoleAssignment

        role = Role.objects.get(code=role_code)
        assignment, created = RoleAssignment.objects.get_or_create(
            user=user,
            role=role,
            defaults={"assigned_by": assigned_by},
        )
        if created:
            AuditService.record(
                action="role_changed",
                actor_user=assigned_by,
                target_type="user_account",
                target_id=str(user.id),
                metadata={"role": role_code, "op": "assign"},
            )
        return assignment

    @classmethod
    def revoke_role(cls, *, user, role_code: str, revoked_by=None):
        from apps.audit.services import AuditService
        from apps.rbac.models import Role, RoleAssignment

        role = Role.objects.get(code=role_code)
        deleted, _ = RoleAssignment.objects.filter(user=user, role=role).delete()
        if deleted:
            AuditService.record(
                action="role_changed",
                actor_user=revoked_by,
                target_type="user_account",
                target_id=str(user.id),
                metadata={"role": role_code, "op": "revoke"},
            )
        return deleted
