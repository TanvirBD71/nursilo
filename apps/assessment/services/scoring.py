"""
Server-side attempt scoring against frozen QuestionVersion (docs/05 §9, docs/09 §10).

UNIT-11 makes question types first-class for scoring while preserving the
UNIT-5/6 ScoreSummary contract (``score`` = full-mark item count; ``percent_correct``
= full-mark items / total). New ``points`` / ``percent`` keys carry partial marks.

Scoring rules (server owns the answer key; the client never scores):
  * BEST_ANSWER / MCQ / single-key: 1.0 if the selected key is correct, else 0.0.
    No negative marking. Unanswered = 0.0, is_correct = None.
  * TRUE_FALSE: exactly 5 statements, each independently True/False. +0.2 per
    statement that matches the frozen answer key, capped at 1.0. No negative
    marking; an unanswered statement simply earns 0. A fully-unanswered item is
    is_correct = None; an answered item is is_correct = True only when all
    statements are correct.
"""
from __future__ import annotations

from apps.assessment.models import Attempt, AttemptItem, QuestionOption, QuestionVersion

TRUE_FALSE_STATEMENT_MARK = 0.2


def is_true_false_spec(spec) -> bool:
    return (
        isinstance(spec, dict)
        and isinstance(spec.get("truths"), dict)
        and len(spec["truths"]) > 0
    )


def correct_keys_for_version(version: QuestionVersion) -> set[str]:
    """Resolve single-answer correctness keys from frozen options + correct_answer_spec."""
    keys = {opt.key for opt in version.options.all() if opt.is_correct}
    spec = version.correct_answer_spec or {}
    if isinstance(spec, dict):
        if spec.get("key"):
            keys.add(str(spec["key"]))
        raw_keys = spec.get("keys")
        if isinstance(raw_keys, (list, tuple)):
            keys.update(str(k) for k in raw_keys if k)
    return keys


def correct_truths_for_version(version: QuestionVersion) -> dict[str, bool]:
    """Frozen True/False answer key: statement key -> expected truth value."""
    spec = version.correct_answer_spec or {}
    truths = spec.get("truths") if isinstance(spec, dict) else None
    result: dict[str, bool] = {}
    if isinstance(truths, dict):
        for key, value in truths.items():
            result[str(key).strip().lower()] = bool(value)
    return result


def selected_key(selected_answer) -> str | None:
    if not isinstance(selected_answer, dict):
        return None
    key = selected_answer.get("key")
    if key is None or key == "":
        return None
    return str(key)


def selected_truths(selected_answer) -> dict[str, bool]:
    """Student's per-statement True/False selections; missing/None = unanswered."""
    if not isinstance(selected_answer, dict):
        return {}
    truths = selected_answer.get("truths")
    out: dict[str, bool] = {}
    if isinstance(truths, dict):
        for key, value in truths.items():
            if value is None:
                continue
            out[str(key).strip().lower()] = bool(value)
    return out


def score_item_detail(
    item: AttemptItem, *, version: QuestionVersion | None = None
) -> tuple[bool | None, float]:
    """
    Return (is_correct, points) for an item scored against its frozen version.

    is_correct is None for fully-unanswered items; points is in [0.0, 1.0].
    """
    version = version or item.question_version
    spec = version.correct_answer_spec or {}
    if is_true_false_spec(spec):
        correct = correct_truths_for_version(version)
        selected = selected_truths(item.selected_answer)
        if not selected:
            return (None, 0.0)
        total_statements = len(correct) or 1
        earned = sum(
            1
            for key, expected in correct.items()
            if key in selected and selected[key] == expected
        )
        points = round(min(earned, total_statements) * TRUE_FALSE_STATEMENT_MARK, 4)
        points = min(points, 1.0)
        is_correct = earned == total_statements
        return (is_correct, points)
    key = selected_key(item.selected_answer)
    if key is None:
        return (None, 0.0)
    ok = key in correct_keys_for_version(version)
    return (ok, 1.0 if ok else 0.0)


def score_item(item: AttemptItem, *, version: QuestionVersion | None = None) -> bool | None:
    """Binary correctness for an item (True/False/None). Backwards-compatible."""
    return score_item_detail(item, version=version)[0]


def build_score_summary(items: list[AttemptItem]) -> dict:
    """
    Persistable ScoreSummary (docs/05 ScoreSummary; docs/06 score_summary JSONB).

    Preserves the UNIT-5/6 contract:
      * ``score`` = count of fully-correct items
      * ``percent_correct`` = fully-correct / total * 100
    Adds partial-aware marks:
      * ``points`` = sum of per-item marks (True/False partials included)
      * ``max_points`` = total item count (each item is worth up to 1.0)
      * ``percent`` = points / total * 100
    No weighted or negative marking.
    """
    total = len(items)
    correct = 0
    incorrect = 0
    unanswered = 0
    points = 0.0
    for item in items:
        item_points = item.score
        if item_points is None:
            item_points = 1.0 if item.is_correct is True else 0.0
        points += item_points
        if item.is_correct is True:
            correct += 1
        elif item.is_correct is False:
            incorrect += 1
        else:
            unanswered += 1
    answered = correct + incorrect
    percent_correct = round((correct / total) * 100, 2) if total else 0.0
    points = round(points, 2)
    percent = round((points / total) * 100, 2) if total else 0.0
    return {
        "total": total,
        "answered": answered,
        "correct": correct,
        "incorrect": incorrect,
        "unanswered": unanswered,
        "score": correct,
        "percent_correct": percent_correct,
        "points": points,
        "max_points": total,
        "percent": percent,
    }


def score_attempt_items(attempt: Attempt) -> dict:
    """
    Finalize per-item correctness + marks and the attempt score_summary from
    frozen versions. Callers ensure the attempt is being submitted; persists
    item is_correct + score fields.
    """
    items = list(
        attempt.items.select_related("question_version")
        .prefetch_related("question_version__options")
        .order_by("position")
    )
    for item in items:
        is_correct, points = score_item_detail(item)
        item.is_correct = is_correct
        item.score = points
    AttemptItem.objects.bulk_update(items, ["is_correct", "score"])
    summary = build_score_summary(items)
    attempt.score_summary = summary
    attempt.save(update_fields=["score_summary"])
    return summary


def option_is_correct_for_review(option: QuestionOption) -> bool:
    """Review-time only helper — never call for active-attempt presentation."""
    return bool(option.is_correct)
