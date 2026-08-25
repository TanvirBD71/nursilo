"""Staff-facing blueprint inspection + generation preview (UNIT-11)."""
from __future__ import annotations

from apps.assessment.models import ExamBlueprint
from apps.assessment.services.blueprint import BlueprintService
from apps.rbac.services import AccessControlService


class BlueprintStaffError(Exception):
    def __init__(self, message: str, *, code: str = "blueprint_error"):
        super().__init__(message)
        self.code = code


class BlueprintStaffService:
    """Read-only blueprint views for staff; generation is a planning preview."""

    VIEW_PERMISSIONS = ("questions.view_unpublished", "exams.view", "questions.import")

    @classmethod
    def _require_view(cls, actor):
        if any(
            AccessControlService.has_permission(actor, perm)
            for perm in cls.VIEW_PERMISSIONS
        ):
            return
        raise PermissionError("Permission denied.")

    @classmethod
    def list_blueprints(cls, actor):
        cls._require_view(actor)
        return list(ExamBlueprint.objects.all().order_by("-is_active", "-created_at"))

    @classmethod
    def get_blueprint(cls, actor, blueprint_id) -> ExamBlueprint:
        cls._require_view(actor)
        obj = (
            ExamBlueprint.objects.filter(pk=blueprint_id)
            .prefetch_related(
                "categories__competencies", "cognitive_allocations"
            )
            .first()
        )
        if obj is None:
            raise BlueprintStaffError("Not found.", code="not_found")
        return obj

    @classmethod
    def active_blueprint(cls, actor) -> ExamBlueprint | None:
        cls._require_view(actor)
        return BlueprintService.active_blueprint()

    @classmethod
    def generation_plan(cls, actor, blueprint: ExamBlueprint):
        """Compliance / shortage plan over the published pool (no persistence)."""
        cls._require_view(actor)
        return BlueprintService.generate(blueprint)
