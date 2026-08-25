"""Shared editorial workflow transitions (docs/03 §5, docs/05, docs/09).

Authoritative lifecycle:
  Draft → Review → Approved → Published → Archived
  Reject/return: Review → Draft
  Restore: Archived → Draft (re-entry to editorial cycle — docs/05)
"""
from __future__ import annotations

from dataclasses import dataclass

from django.db import transaction
from django.utils import timezone

from apps.audit.services import AuditService
from apps.common.choices import EditorialState
from apps.rbac.services import AccessControlService


class EditorialWorkflowError(Exception):
    """Illegal or unauthorized editorial transition."""

    def __init__(self, message: str, *, code: str = "workflow_error"):
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class TransitionResult:
    previous_state: str
    new_state: str
    action: str


# action → (from_states, to_state, required_permission)
_TRANSITIONS: dict[str, tuple[frozenset[str], str, str]] = {
    "submit_review": (
        frozenset({EditorialState.DRAFT}),
        EditorialState.REVIEW,
        "content.submit_review",
    ),
    "approve": (
        frozenset({EditorialState.REVIEW}),
        EditorialState.APPROVED,
        "content.approve",
    ),
    "reject": (
        frozenset({EditorialState.REVIEW}),
        EditorialState.DRAFT,
        "content.reject",
    ),
    "publish": (
        frozenset({EditorialState.APPROVED}),
        EditorialState.PUBLISHED,
        "content.publish",
    ),
    "archive": (
        frozenset({EditorialState.PUBLISHED}),
        EditorialState.ARCHIVED,
        "content.archive",
    ),
    "restore": (
        frozenset({EditorialState.ARCHIVED}),
        EditorialState.DRAFT,
        "content.restore",
    ),
}

# Question-bank transitions use questions.* permissions where distinct.
_QUESTION_PERM_MAP = {
    "approve": "questions.approve",
    "publish": "questions.publish",
    "archive": "questions.archive",
    "restore": "questions.restore",
    "submit_review": "content.submit_review",
    "reject": "content.reject",
}


class EditorialWorkflowService:
    """Server-side editorial state machine. UI never authorizes transitions."""

    @classmethod
    def allowed_actions(cls, user, obj, *, domain: str = "content") -> list[str]:
        state = getattr(obj, "editorial_state", None)
        actions = []
        for action, (from_states, _to, perm) in _TRANSITIONS.items():
            if state not in from_states:
                continue
            needed = cls._permission_for(action, domain=domain, default=perm)
            if cls._may_act(user, obj, action=action, permission=needed, domain=domain):
                actions.append(action)
        return actions

    @classmethod
    def transition(
        cls,
        *,
        obj,
        action: str,
        actor,
        domain: str = "content",
        target_type: str = "",
        notes: str = "",
    ) -> TransitionResult:
        if action not in _TRANSITIONS:
            raise EditorialWorkflowError("Unknown editorial action.", code="unknown_action")
        from_states, to_state, default_perm = _TRANSITIONS[action]
        permission = cls._permission_for(action, domain=domain, default=default_perm)
        if not cls._may_act(actor, obj, action=action, permission=permission, domain=domain):
            raise EditorialWorkflowError("Permission denied.", code="forbidden")
        previous = obj.editorial_state
        if previous not in from_states:
            raise EditorialWorkflowError(
                f"Cannot {action} from state '{previous}'.",
                code="illegal_transition",
            )
        with transaction.atomic():
            obj.editorial_state = to_state
            fields = ["editorial_state", "updated_at"]
            if hasattr(obj, "version_number"):
                obj.version_number = int(getattr(obj, "version_number", 1) or 1) + 1
                fields.append("version_number")
            now = timezone.now()
            if action == "publish":
                obj.published_at = now
                fields.append("published_at")
                if hasattr(obj, "is_archived"):
                    obj.is_archived = False
                    obj.archived_at = None
                    fields.extend(["is_archived", "archived_at"])
            elif action == "archive":
                if hasattr(obj, "is_archived"):
                    obj.mark_archived(at=now)
                    fields.extend(["is_archived", "archived_at"])
            elif action == "restore":
                if hasattr(obj, "is_archived"):
                    obj.is_archived = False
                    obj.archived_at = None
                    fields.extend(["is_archived", "archived_at"])
                if hasattr(obj, "published_at"):
                    obj.published_at = None
                    fields.append("published_at")
            if hasattr(obj, "updated_by_id"):
                obj.updated_by = actor
                fields.append("updated_by")
            obj.save(update_fields=list(dict.fromkeys(fields)))
            AuditService.record(
                action=f"editorial_{action}",
                actor_user=actor,
                target_type=target_type or obj.__class__.__name__.lower(),
                target_id=str(obj.pk),
                metadata={
                    "from": previous,
                    "to": to_state,
                    "domain": domain,
                    "notes": (notes or "")[:500],
                },
            )
        return TransitionResult(previous_state=previous, new_state=to_state, action=action)

    @classmethod
    def _permission_for(cls, action: str, *, domain: str, default: str) -> str:
        if domain == "questions":
            return _QUESTION_PERM_MAP.get(action, default)
        if domain == "exams" and action in {"publish", "archive"}:
            return f"exams.{action}"
        return default

    @classmethod
    def _may_act(cls, user, obj, *, action: str, permission: str, domain: str) -> bool:
        if AccessControlService.has_permission(user, permission):
            return True
        # Author limited paths (docs/03 L scopes): own drafts only.
        if action == "submit_review" and AccessControlService.has_permission(
            user, "content.submit_review"
        ):
            return cls._is_own(user, obj)
        if action in {"submit_review"} and domain == "content":
            if AccessControlService.has_permission(user, "content.edit_own_draft"):
                return cls._is_own(user, obj) and obj.editorial_state == EditorialState.DRAFT
        return False

    @staticmethod
    def _is_own(user, obj) -> bool:
        created_by_id = getattr(obj, "created_by_id", None)
        return bool(user and created_by_id and created_by_id == getattr(user, "id", None))
