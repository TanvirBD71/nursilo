"""
Server-authoritative exam timer helpers (docs/09 §10, docs/07, docs/11 §16.3).

No grace period or extension policy is defined in locked docs — expiry is exact
against Attempt.expires_at. Browser countdown is presentation only.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from django.utils import timezone

from apps.assessment.models import Attempt
from apps.common.choices import AttemptState


@dataclass(frozen=True)
class TimerSnapshot:
    """Server-truth timer state for an attempt."""

    is_timed: bool
    expires_at: datetime | None
    remaining_seconds: int | None
    is_expired: bool
    time_limit_seconds: int | None


# Allowed per-question pacing options (UNIT-11 timer config). Server-authoritative;
# the browser countdown remains presentation-only against Attempt.expires_at.
ALLOWED_SECONDS_PER_QUESTION = (30, 45, 60)
DEFAULT_SECONDS_PER_QUESTION = 60


def compute_time_limit_seconds(*, question_count: int, seconds_per_question: int) -> int:
    """
    Total exam time = question_count × seconds_per_question.

    Rejects out-of-range pacing and non-positive counts so exam configuration
    cannot silently produce an unusable timer.
    """
    try:
        count = int(question_count)
        per_q = int(seconds_per_question)
    except (TypeError, ValueError) as exc:
        raise ValueError("Question count and seconds-per-question must be integers.") from exc
    if per_q not in ALLOWED_SECONDS_PER_QUESTION:
        raise ValueError(
            f"Seconds per question must be one of {ALLOWED_SECONDS_PER_QUESTION}."
        )
    if count < 1:
        raise ValueError("Question count must be at least 1.")
    return count * per_q


def compute_expires_at(*, started_at: datetime, time_limit_seconds: int | None) -> datetime | None:
    if time_limit_seconds is None:
        return None
    if time_limit_seconds <= 0:
        return started_at
    return started_at + timedelta(seconds=int(time_limit_seconds))


def timer_snapshot(attempt: Attempt, *, now: datetime | None = None) -> TimerSnapshot:
    now = now or timezone.now()
    limit = attempt.time_limit_seconds
    expires = attempt.expires_at
    is_timed = expires is not None or (limit is not None and limit >= 0)
    if expires is None:
        return TimerSnapshot(
            is_timed=False,
            expires_at=None,
            remaining_seconds=None,
            is_expired=False,
            time_limit_seconds=limit,
        )
    remaining = int((expires - now).total_seconds())
    if remaining < 0:
        remaining = 0
    expired = now >= expires and attempt.state in {
        AttemptState.NOT_STARTED,
        AttemptState.IN_PROGRESS,
    }
    # Also treat already-past expires as expired for active attempts.
    if attempt.state in {AttemptState.NOT_STARTED, AttemptState.IN_PROGRESS} and now >= expires:
        expired = True
        remaining = 0
    return TimerSnapshot(
        is_timed=True,
        expires_at=expires,
        remaining_seconds=remaining,
        is_expired=expired,
        time_limit_seconds=limit,
    )


def is_timed_out(attempt: Attempt, *, now: datetime | None = None) -> bool:
    snap = timer_snapshot(attempt, now=now)
    return bool(snap.is_timed and snap.is_expired)
