"""
Server-authoritative exam question set from ExamDefinition (docs/05 §8–9, docs/06 §16).

Uses explicit ExamDefinitionItem membership ordered by sort_order.
Blueprint rules JSONB filter semantics are not fully specified in locked docs —
this unit does not invent topic/difficulty mix interpreters; only the explicit
item list (published questions with a current version) is used.
"""
from __future__ import annotations

from apps.assessment.models import ExamDefinition, ExamDefinitionItem, Question
from apps.assessment.services.exceptions import ExamPoolEmpty, ExamUnavailable
from apps.common.choices import EditorialState


class ExamPoolService:
    """Resolve the frozen-capable question list for a published exam definition."""

    @classmethod
    def published_definition_qs(cls):
        return ExamDefinition.objects.filter(
            editorial_state=EditorialState.PUBLISHED,
            is_archived=False,
        )

    @classmethod
    def get_published_definition(cls, exam_id) -> ExamDefinition | None:
        return cls.published_definition_qs().filter(pk=exam_id).first()

    @classmethod
    def select_questions(cls, exam: ExamDefinition) -> list[Question]:
        if exam.editorial_state != EditorialState.PUBLISHED or exam.is_archived:
            raise ExamUnavailable("This exam is not available.")

        item_rows = list(
            ExamDefinitionItem.objects.filter(exam_definition=exam)
            .select_related("question", "question__current_version")
            .order_by("sort_order", "id")
        )
        if not item_rows:
            raise ExamPoolEmpty("This exam has no questions configured.")

        questions: list[Question] = []
        for row in item_rows:
            q = row.question
            if q.editorial_state != EditorialState.PUBLISHED or q.is_archived:
                continue
            if q.current_version_id is None:
                continue
            questions.append(q)

        if not questions:
            raise ExamPoolEmpty("This exam has no published questions available.")
        return questions
