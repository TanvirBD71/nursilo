"""
Non-destructive duplicate / similarity warnings for the question bank.

Exact match: identical normalized stem.
Safe heuristic: same normalized stem prefix (min 40 chars, compared at 80).
Never deletes, merges, or auto-resolves. Dismiss is recorded in the existing
append-only audit log.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from apps.assessment.models import Question, QuestionVersionTranslation
from apps.audit.models import AuditEvent
from apps.audit.services import AuditService

DISMISS_ACTION = "question_duplicate_dismissed"
_PREFIX_LEN = 80
_MIN_HEURISTIC = 40


def normalize_stem(text: str) -> str:
    value = unicodedata.normalize("NFKC", text or "")
    value = value.casefold()
    value = re.sub(r"[^\w\s]", " ", value, flags=re.UNICODE)
    value = re.sub(r"\s+", " ", value).strip()
    return value


@dataclass(frozen=True)
class DuplicateHit:
    other_id: str
    other_code: str
    other_stem: str
    match_kind: str  # exact | similar
    reason: str


class QuestionDuplicateService:
    @classmethod
    def stem_for(cls, question: Question) -> str:
        version = question.current_version
        if version is None:
            return ""
        tr = version.translations.first()
        return getattr(tr, "stem", "") or ""

    @classmethod
    def find_for(cls, question: Question, *, limit: int = 8) -> list[DuplicateHit]:
        stem = cls.stem_for(question)
        normalized = normalize_stem(stem)
        if len(normalized) < 12:
            return []
        dismissed = cls._dismissed_ids(question)
        snippet = (stem or "").strip()[:32]
        qs = QuestionVersionTranslation.objects.exclude(
            version__question_id=question.id
        ).select_related("version__question")
        if snippet:
            qs = qs.filter(stem__icontains=snippet[:24])
        else:
            return []
        hits: list[DuplicateHit] = []
        seen: set[str] = set()
        prefix = normalized[:_PREFIX_LEN]
        for row in qs[:200]:
            other = row.version.question
            other_id = str(other.id)
            if other_id in seen or other_id in dismissed:
                continue
            other_norm = normalize_stem(row.stem or "")
            if not other_norm:
                continue
            kind = ""
            reason = ""
            if other_norm == normalized:
                kind = "exact"
                reason = "Normalized stem is an exact match."
            elif (
                len(normalized) >= _MIN_HEURISTIC
                and len(other_norm) >= _MIN_HEURISTIC
                and other_norm[:_PREFIX_LEN] == prefix
            ):
                kind = "similar"
                reason = "Normalized stem prefix matches (safe heuristic)."
            if not kind:
                continue
            seen.add(other_id)
            hits.append(
                DuplicateHit(
                    other_id=other_id,
                    other_code=other.question_code or "",
                    other_stem=(row.stem or "")[:180],
                    match_kind=kind,
                    reason=reason,
                )
            )
            if len(hits) >= limit:
                break
        return hits

    @classmethod
    def dismiss(cls, *, actor, question: Question, other: Question) -> None:
        AuditService.record(
            action=DISMISS_ACTION,
            actor_user=actor,
            target_type="question",
            target_id=str(question.id),
            metadata={
                "other_id": str(other.id),
                "reason": "user dismissed possible duplicate (keep both)",
            },
        )

    @classmethod
    def _dismissed_ids(cls, question: Question) -> set[str]:
        rows = AuditEvent.objects.filter(
            action=DISMISS_ACTION, target_type="question", target_id=str(question.id)
        ).values_list("metadata", flat=True)
        out: set[str] = set()
        for meta in rows:
            other = (meta or {}).get("other_id")
            if other:
                out.add(str(other))
        return out
