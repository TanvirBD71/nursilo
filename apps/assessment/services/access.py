"""Attempt ownership and answer-key disclosure rules (docs/09 §11, docs/24)."""
from __future__ import annotations

from dataclasses import dataclass

from apps.assessment.models import Attempt, ExamDefinition
from apps.common.choices import AttemptMode, AttemptState
from apps.portal.access import user_may_access_student_portal


TERMINAL_STATES = frozenset({AttemptState.SUBMITTED, AttemptState.COMPLETED})
ACTIVE_STATES = frozenset({AttemptState.NOT_STARTED, AttemptState.IN_PROGRESS})

# Premium-gated tracks (docs/09 §10, docs/06 §16, FR-EXM-05).
PREMIUM_TRACK_CODES = frozenset({"licensing", "govt_job", "nclex", "prometric"})

EXAM_MODES = frozenset(
    {
        AttemptMode.CHAPTER_EXAM,
        AttemptMode.SUBJECT_EXAM,
        AttemptMode.TIMED_EXAM,
        AttemptMode.MOCK,
        AttemptMode.CUSTOM,
    }
)


@dataclass(frozen=True)
class AttemptAccessDecision:
    allowed: bool
    reason: str = ""  # not_found | forbidden | not_active | ok


class PracticeAccessService:
    """Fail-closed ownership + disclosure decisions for practice attempts."""

    @classmethod
    def user_may_practice(cls, user) -> bool:
        return user_may_access_student_portal(user)

    @classmethod
    def get_owned_attempt(cls, user, attempt_id) -> Attempt | None:
        if user is None or not getattr(user, "is_authenticated", False):
            return None
        return (
            Attempt.objects.filter(pk=attempt_id, user=user)
            .select_related("user", "exam_definition")
            .first()
        )

    @classmethod
    def decide(cls, user, attempt: Attempt | None) -> AttemptAccessDecision:
        if attempt is None:
            return AttemptAccessDecision(False, "not_found")
        if user is None or not getattr(user, "is_authenticated", False):
            return AttemptAccessDecision(False, "forbidden")
        if attempt.user_id != user.id:
            # Do not distinguish existence for other users.
            return AttemptAccessDecision(False, "not_found")
        return AttemptAccessDecision(True, "ok")

    @classmethod
    def is_active(cls, attempt: Attempt) -> bool:
        return attempt.state in ACTIVE_STATES

    @classmethod
    def is_terminal(cls, attempt: Attempt) -> bool:
        return attempt.state in TERMINAL_STATES

    @classmethod
    def may_reveal_answer_key(cls, attempt: Attempt) -> bool:
        """
        Correct answers / explanations only after completion.
        No approved immediate-feedback practice mode in locked docs.
        """
        return attempt.state == AttemptState.COMPLETED


class ExamAccessService:
    """
    Fail-closed ownership + entitlement + disclosure for formal exams (docs/09 §10).

    Entitlement evaluation uses EntitlementService (PremiumActive + expiry).
    Assessment never grants Premium capabilities itself.
    """

    @classmethod
    def user_may_take_exams(cls, user) -> bool:
        return user_may_access_student_portal(user)

    @classmethod
    def get_owned_attempt(cls, user, attempt_id) -> Attempt | None:
        attempt = PracticeAccessService.get_owned_attempt(user, attempt_id)
        if attempt is None:
            return None
        if attempt.mode not in EXAM_MODES and attempt.exam_definition_id is None:
            return None
        return attempt

    @classmethod
    def decide(cls, user, attempt: Attempt | None) -> AttemptAccessDecision:
        return PracticeAccessService.decide(user, attempt)

    @classmethod
    def is_active(cls, attempt: Attempt) -> bool:
        return PracticeAccessService.is_active(attempt)

    @classmethod
    def is_terminal(cls, attempt: Attempt) -> bool:
        return PracticeAccessService.is_terminal(attempt)

    @classmethod
    def may_reveal_answer_key(cls, attempt: Attempt) -> bool:
        return PracticeAccessService.may_reveal_answer_key(attempt)

    @classmethod
    def user_is_premium(cls, user) -> bool:
        from apps.entitlements.services import EntitlementService

        return EntitlementService.is_premium(user)

    @classmethod
    def exam_requires_premium(cls, exam: ExamDefinition) -> bool:
        """Premium when definition is premium-flagged or on a premium track."""
        if exam.is_premium:
            return True
        track = (exam.track_code or "").strip().lower()
        return bool(track and track in PREMIUM_TRACK_CODES)

    @classmethod
    def is_exam_entitled(cls, user, exam: ExamDefinition) -> bool:
        if not cls.user_may_take_exams(user):
            return False
        if not cls.exam_requires_premium(exam):
            return True
        return cls.user_is_premium(user)

    @classmethod
    def may_start_new_attempt(cls, user, exam: ExamDefinition) -> bool:
        """
        Entitled learners may start a new attempt (docs/09 §10 retake via
        exam/entitlement policy). Numeric max-attempt caps are not defined in
        locked docs — do not invent them. InProgress attempts are resumed
        separately and never duplicated by refresh.
        """
        return cls.is_exam_entitled(user, exam)
