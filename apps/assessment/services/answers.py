"""
Server-authoritative answer normalization + validation (UNIT-11).

The client never scores and never receives the answer key. This module accepts
raw client input for the current attempt item and produces a safe, persistable
``selected_answer`` payload without consulting correctness.

Supported shapes:
  * single-answer (BEST_ANSWER / MCQ / clinical / image): ``{"key": "b"}``
  * TRUE_FALSE: ``{"truths": {"a": true, "b": false, ...}}`` — each statement is
    independent; omitted/None statements are simply unanswered.
"""
from __future__ import annotations

from dataclasses import dataclass

from apps.assessment.models import AttemptItem
from apps.assessment.services.scoring import is_true_false_spec

_TRUE_TOKENS = {"true", "t", "1", "yes", "y", "on"}
_FALSE_TOKENS = {"false", "f", "0", "no", "n", "off"}


@dataclass(frozen=True)
class NormalizedAnswer:
    ok: bool
    code: str  # cleared | saved | invalid_answer
    message: str
    selected_answer: dict | None = None
    clear: bool = False


def coerce_bool(value):
    if isinstance(value, bool):
        return value
    if value is None:
        return None
    token = str(value).strip().lower()
    if token in _TRUE_TOKENS:
        return True
    if token in _FALSE_TOKENS:
        return False
    return None


def normalize_answer(item: AttemptItem, *, option_key=None, truths=None) -> NormalizedAnswer:
    version = item.question_version
    valid_keys = {opt.key for opt in version.options.all()}
    valid_keys_lower = {k.lower(): k for k in valid_keys}
    spec = version.correct_answer_spec or {}

    if is_true_false_spec(spec):
        if truths in (None, "", {}):
            return NormalizedAnswer(True, "cleared", "Answer cleared.", None, clear=True)
        if not isinstance(truths, dict):
            return NormalizedAnswer(
                False, "invalid_answer", "Invalid True/False answer."
            )
        cleaned: dict[str, bool] = {}
        for raw_key, raw_val in truths.items():
            key = str(raw_key).strip().lower()
            if key not in valid_keys_lower:
                return NormalizedAnswer(
                    False,
                    "invalid_answer",
                    "The selected statement is not valid for this question.",
                )
            value = coerce_bool(raw_val)
            if value is None:
                continue
            cleaned[key] = value
        if not cleaned:
            return NormalizedAnswer(True, "cleared", "Answer cleared.", None, clear=True)
        return NormalizedAnswer(True, "saved", "Answer saved.", {"truths": cleaned})

    key = (option_key or "").strip()
    if key == "":
        return NormalizedAnswer(True, "cleared", "Answer cleared.", None, clear=True)
    if key not in valid_keys:
        return NormalizedAnswer(
            False,
            "invalid_answer",
            "The selected answer is not valid for this question.",
        )
    return NormalizedAnswer(True, "saved", "Answer saved.", {"key": key})
