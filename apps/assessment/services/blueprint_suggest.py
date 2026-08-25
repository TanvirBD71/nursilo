"""
Deterministic blueprint assistance for staff review (suggestion ≠ authority).

Only exact, already-known mappings are offered:
  * content subject name equals a blueprint category name (case-insensitive)
  * already-stored cognitive level is echoed, never invented
  * competency is never guessed from subject/topic text

If those rules do not fire: "No confident suggestion".
"""
from __future__ import annotations

from dataclasses import dataclass

from apps.assessment.models import BlueprintCategory, ExamBlueprint
from apps.assessment.taxonomy import canonicalize_subject
from apps.audit.models import AuditEvent


DISMISS_SUGGESTION_ACTION = "question_suggestion_dismissed"


@dataclass(frozen=True)
class BlueprintSuggestion:
    confident: bool
    reason: str
    category_id: str = ""
    category_name: str = ""
    competency_id: str = ""
    competency_label: str = ""
    cognitive_level: str = ""
    cognitive_label: str = ""


_NO = BlueprintSuggestion(confident=False, reason="No confident suggestion")


class BlueprintSuggestionService:
    @classmethod
    def suggest(cls, question, *, blueprint: ExamBlueprint | None = None) -> BlueprintSuggestion:
        if cls._dismissed(question):
            return BlueprintSuggestion(
                confident=False,
                reason="Suggestion rejected by reviewer. Classify manually if needed.",
            )
        blueprint = blueprint or ExamBlueprint.objects.filter(is_active=True).first()
        if blueprint is None:
            return _NO
        subject, known = canonicalize_subject(question.content_subject or "")
        category = None
        if known and subject:
            category = BlueprintCategory.objects.filter(
                blueprint=blueprint, name__iexact=subject
            ).first()
        if category is None:
            return _NO
        return BlueprintSuggestion(
            confident=True,
            reason=(
                f"Subject matches blueprint category “{category.name}” exactly. "
                "Suggestion is not final authority."
            ),
            category_id=str(category.id),
            category_name=category.name,
        )

    @classmethod
    def _dismissed(cls, question) -> bool:
        return AuditEvent.objects.filter(
            action=DISMISS_SUGGESTION_ACTION,
            target_type="question",
            target_id=str(question.id),
        ).exists()
