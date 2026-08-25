"""Exam definition staff management — no attempt/timer/score authority changes."""
from __future__ import annotations

from django.db import transaction
from django.db.models import Q

from apps.assessment.models import ExamDefinition, ExamDefinitionItem, Question
from apps.audit.services import AuditService
from apps.cms.services import EditorialWorkflowService
from apps.common.choices import AttemptMode, EditorialState
from apps.rbac.services import AccessControlService
from apps.staff.services.pagination import paginate_queryset


class ExamStaffError(Exception):
    def __init__(self, message: str, *, code: str = "exam_error"):
        super().__init__(message)
        self.code = code


class ExamStaffService:
    @classmethod
    def list_exams(cls, actor, *, q: str = "", state: str = "", page=1):
        AccessControlService.require_permission(actor, "exams.view")
        qs = ExamDefinition.objects.all().order_by("-updated_at")
        if state:
            qs = qs.filter(editorial_state=state)
        if q:
            qs = qs.filter(Q(code__icontains=q) | Q(title_key__icontains=q))
        return paginate_queryset(qs, page=page)

    @classmethod
    def get_exam(cls, actor, exam_id) -> ExamDefinition:
        AccessControlService.require_permission(actor, "exams.view")
        try:
            return ExamDefinition.objects.prefetch_related("items__question").get(
                pk=exam_id
            )
        except ExamDefinition.DoesNotExist as exc:
            raise ExamStaffError("Not found.", code="not_found") from exc

    @classmethod
    @transaction.atomic
    def create_exam(
        cls,
        *,
        actor,
        code: str,
        title_key: str,
        mode: str = AttemptMode.MOCK,
        time_limit_seconds: int | None = None,
        is_premium: bool = False,
        track_code: str = "",
    ) -> ExamDefinition:
        if not (
            AccessControlService.has_permission(actor, "exams.create")
            or AccessControlService.has_permission(actor, "exams.create_limited")
        ):
            raise PermissionError("Permission denied.")
        code = (code or "").strip().lower()
        if not code:
            raise ExamStaffError("Code required.", code="validation")
        if ExamDefinition.objects.filter(code=code).exists():
            raise ExamStaffError("Code already exists.", code="duplicate")
        exam = ExamDefinition.objects.create(
            code=code,
            title_key=(title_key or code).strip(),
            mode=mode,
            time_limit_seconds=time_limit_seconds,
            is_premium=bool(is_premium),
            track_code=(track_code or "").strip() or None,
            editorial_state=EditorialState.DRAFT,
            created_by=actor,
            updated_by=actor,
        )
        AuditService.record(
            action="exam_created",
            actor_user=actor,
            target_type="exam_definition",
            target_id=str(exam.id),
            metadata={"code": exam.code, "mode": exam.mode},
        )
        return exam

    @classmethod
    @transaction.atomic
    def update_exam(
        cls,
        *,
        actor,
        exam: ExamDefinition,
        title_key: str,
        time_limit_seconds: int | None,
        is_premium: bool,
        track_code: str = "",
    ) -> ExamDefinition:
        if not (
            AccessControlService.has_permission(actor, "exams.edit")
            or (
                AccessControlService.has_permission(actor, "exams.edit_limited")
                and exam.created_by_id == actor.id
                and exam.editorial_state == EditorialState.DRAFT
            )
        ):
            raise PermissionError("Permission denied.")
        exam.title_key = (title_key or exam.title_key).strip()
        exam.time_limit_seconds = time_limit_seconds
        exam.is_premium = bool(is_premium)
        exam.track_code = (track_code or "").strip() or None
        exam.updated_by = actor
        exam.version_number = int(exam.version_number or 1) + 1
        exam.save(
            update_fields=[
                "title_key",
                "time_limit_seconds",
                "is_premium",
                "track_code",
                "updated_by",
                "version_number",
                "updated_at",
            ]
        )
        AuditService.record(
            action="exam_edited",
            actor_user=actor,
            target_type="exam_definition",
            target_id=str(exam.id),
            metadata={"code": exam.code},
        )
        return exam

    @classmethod
    @transaction.atomic
    def add_question(cls, *, actor, exam: ExamDefinition, question_id, sort_order: int = 0):
        AccessControlService.require_permission(actor, "exams.edit")
        try:
            question = Question.objects.get(pk=question_id)
        except Question.DoesNotExist as exc:
            raise ExamStaffError("Question not found.", code="not_found") from exc
        item, created = ExamDefinitionItem.objects.get_or_create(
            exam_definition=exam,
            question=question,
            defaults={"sort_order": int(sort_order or 0)},
        )
        return item, created

    @classmethod
    def workflow(cls, *, actor, exam_id, action: str, notes: str = ""):
        exam = cls.get_exam(actor, exam_id)
        # Publish/archive use exams.* via domain mapping; submit/approve use content.*
        domain = "exams" if action in {"publish", "archive"} else "content"
        # Ensure publish permission maps correctly for exams domain.
        if action == "publish":
            AccessControlService.require_permission(actor, "exams.publish")
        if action == "archive":
            AccessControlService.require_permission(actor, "exams.archive")
        return EditorialWorkflowService.transition(
            obj=exam,
            action=action,
            actor=actor,
            domain=domain,
            target_type="exam_definition",
            notes=notes,
        )
