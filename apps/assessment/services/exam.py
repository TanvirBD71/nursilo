"""
ExamService — formal examination runtime (docs/05 §9, docs/09 §10–11).

Owns catalog eligibility, start/resume, timer enforcement, answer persistence,
submission / auto-submit on timeout, scoring, history. Templates never authorize
or score. Browser timer is presentation only.
"""
from __future__ import annotations

from dataclasses import dataclass

from django.db import transaction
from django.utils import timezone

from apps.assessment.models import Attempt, AttemptItem, ExamDefinition
from apps.assessment.services.access import EXAM_MODES, ExamAccessService
from apps.assessment.services.exceptions import (
    AttemptAlreadySubmitted,
    AttemptForbidden,
    AttemptNotActive,
    AttemptNotFound,
    ExamNotEntitled,
    ExamPoolEmpty,
    ExamUnavailable,
    InvalidNavigation,
)
from apps.assessment.services.exam_pool import ExamPoolService
from apps.assessment.services.practice import AnswerPersistResult, SubmitResult
from apps.assessment.services.scoring import score_attempt_items, selected_key
from apps.assessment.services.timer import compute_expires_at, is_timed_out, timer_snapshot
from apps.common.choices import AttemptState, EditorialState


# Learner-facing detail/catalog states derived from server facts (docs/09 §10).
STATE_AVAILABLE = "available"
STATE_LOCKED = "locked"
STATE_IN_PROGRESS = "in_progress"
STATE_COMPLETED = "completed"
STATE_UNAVAILABLE = "unavailable"


@dataclass(frozen=True)
class ExamEligibility:
    exam: ExamDefinition
    state: str
    entitled: bool
    requires_premium: bool
    in_progress_attempt: Attempt | None
    completed_count: int
    can_start: bool
    can_resume: bool
    question_count: int
    message: str


class ExamService:
    """Authoritative formal exam orchestrator."""

    @classmethod
    def list_catalog(cls, user) -> list[ExamDefinition]:
        """Published, non-archived exams only — no unpublished leakage."""
        if not ExamAccessService.user_may_take_exams(user):
            return []
        return list(
            ExamPoolService.published_definition_qs().order_by("title_key", "code")
        )

    @classmethod
    def get_catalog_exam(cls, user, exam_id) -> ExamDefinition | None:
        if not ExamAccessService.user_may_take_exams(user):
            return None
        return ExamPoolService.get_published_definition(exam_id)

    @classmethod
    def in_progress_for_exam(cls, user, exam: ExamDefinition) -> Attempt | None:
        return (
            Attempt.objects.filter(
                user=user,
                exam_definition=exam,
                state=AttemptState.IN_PROGRESS,
            )
            .order_by("-started_at", "-created_at")
            .first()
        )

    @classmethod
    def completed_count(cls, user, exam: ExamDefinition) -> int:
        return Attempt.objects.filter(
            user=user,
            exam_definition=exam,
            state=AttemptState.COMPLETED,
        ).count()

    @classmethod
    def question_count(cls, exam: ExamDefinition) -> int:
        try:
            return len(ExamPoolService.select_questions(exam))
        except (ExamPoolEmpty, ExamUnavailable):
            return 0

    @classmethod
    def eligibility(cls, user, exam: ExamDefinition) -> ExamEligibility:
        requires = ExamAccessService.exam_requires_premium(exam)
        entitled = ExamAccessService.is_exam_entitled(user, exam)
        active = cls.in_progress_for_exam(user, exam)
        # Enforce timeout on the active attempt before reporting state.
        if active is not None:
            active = cls.enforce_timeout(user, active)
            if active.state != AttemptState.IN_PROGRESS:
                active = None
        done = cls.completed_count(user, exam)
        qcount = cls.question_count(exam)

        if qcount == 0:
            return ExamEligibility(
                exam=exam,
                state=STATE_UNAVAILABLE,
                entitled=entitled,
                requires_premium=requires,
                in_progress_attempt=None,
                completed_count=done,
                can_start=False,
                can_resume=False,
                question_count=0,
                message="This exam is not available.",
            )
        if active is not None:
            return ExamEligibility(
                exam=exam,
                state=STATE_IN_PROGRESS,
                entitled=entitled,
                requires_premium=requires,
                in_progress_attempt=active,
                completed_count=done,
                can_start=False,
                can_resume=True,
                question_count=qcount,
                message="Resume your in-progress attempt.",
            )
        if not entitled:
            return ExamEligibility(
                exam=exam,
                state=STATE_LOCKED,
                entitled=False,
                requires_premium=requires,
                in_progress_attempt=None,
                completed_count=done,
                can_start=False,
                can_resume=False,
                question_count=qcount,
                message="Premium is required to start this exam.",
            )
        if done > 0:
            return ExamEligibility(
                exam=exam,
                state=STATE_COMPLETED,
                entitled=True,
                requires_premium=requires,
                in_progress_attempt=None,
                completed_count=done,
                can_start=ExamAccessService.may_start_new_attempt(user, exam),
                can_resume=False,
                question_count=qcount,
                message="You have completed this exam. You may start another attempt.",
            )
        return ExamEligibility(
            exam=exam,
            state=STATE_AVAILABLE,
            entitled=True,
            requires_premium=requires,
            in_progress_attempt=None,
            completed_count=0,
            can_start=True,
            can_resume=False,
            question_count=qcount,
            message="You can start this exam.",
        )

    @classmethod
    def require_owned_attempt(cls, user, attempt_id) -> Attempt:
        attempt = ExamAccessService.get_owned_attempt(user, attempt_id)
        decision = ExamAccessService.decide(user, attempt)
        if not decision.allowed:
            if decision.reason == "forbidden":
                raise AttemptForbidden()
            raise AttemptNotFound()
        assert attempt is not None
        if attempt.exam_definition_id is None and attempt.mode not in EXAM_MODES:
            raise AttemptNotFound()
        return attempt

    @classmethod
    def require_active_attempt(cls, user, attempt_id) -> Attempt:
        attempt = cls.require_owned_attempt(user, attempt_id)
        attempt = cls.enforce_timeout(user, attempt)
        if ExamAccessService.is_terminal(attempt):
            raise AttemptAlreadySubmitted()
        if not ExamAccessService.is_active(attempt):
            raise AttemptNotActive()
        return attempt

    @classmethod
    @transaction.atomic
    def enforce_timeout(cls, user, attempt: Attempt) -> Attempt:
        """
        Auto-submit on timeout (docs/09 §10, FEAT-EXM-02). Server-side only.
        No grace/extension — exact expires_at.
        """
        attempt = (
            Attempt.objects.select_for_update()
            .filter(pk=attempt.pk)
            .first()
        )
        if attempt is None:
            raise AttemptNotFound()
        decision = ExamAccessService.decide(user, attempt)
        if not decision.allowed:
            raise AttemptNotFound()

        if ExamAccessService.is_terminal(attempt):
            return attempt
        if not is_timed_out(attempt):
            return attempt

        return cls._finalize_locked(attempt, already_submitted=False)

    @classmethod
    def _finalize_locked(cls, attempt: Attempt, *, already_submitted: bool) -> Attempt:
        if attempt.state == AttemptState.COMPLETED:
            return attempt
        if attempt.state == AttemptState.SUBMITTED:
            if not attempt.score_summary:
                score_attempt_items(attempt)
            attempt.state = AttemptState.COMPLETED
            attempt.completed_at = attempt.completed_at or timezone.now()
            attempt.save(update_fields=["state", "completed_at", "score_summary"])
            return attempt

        now = timezone.now()
        attempt.state = AttemptState.SUBMITTED
        attempt.save(update_fields=["state"])
        score_attempt_items(attempt)
        attempt.state = AttemptState.COMPLETED
        attempt.completed_at = now
        attempt.save(update_fields=["state", "completed_at", "score_summary"])
        attempt.refresh_from_db()
        return attempt

    @classmethod
    @transaction.atomic
    def start_or_resume(cls, user, exam_id) -> Attempt:
        """
        Validate eligibility → resume InProgress or create new attempt with
        frozen QuestionVersion set and server timing state.
        Refresh never creates a duplicate while InProgress exists.
        """
        if not ExamAccessService.user_may_take_exams(user):
            raise AttemptForbidden("Exams require a student account.")

        exam = (
            ExamDefinition.objects.select_for_update()
            .filter(pk=exam_id)
            .first()
        )
        if exam is None:
            raise ExamUnavailable("This exam is not available.")
        if exam.editorial_state != EditorialState.PUBLISHED or exam.is_archived:
            raise ExamUnavailable("This exam is not available.")

        existing = (
            Attempt.objects.select_for_update()
            .filter(
                user=user,
                exam_definition=exam,
                state=AttemptState.IN_PROGRESS,
            )
            .order_by("-started_at", "-created_at")
            .first()
        )
        if existing is not None:
            existing = cls.enforce_timeout(user, existing)
            if existing.state == AttemptState.IN_PROGRESS:
                return existing
            # Timed out during resume path — fall through to new attempt if entitled.

        if not ExamAccessService.is_exam_entitled(user, exam):
            raise ExamNotEntitled()
        if not ExamAccessService.may_start_new_attempt(user, exam):
            raise ExamNotEntitled()

        questions = ExamPoolService.select_questions(exam)
        now = timezone.now()
        limit = exam.time_limit_seconds
        expires = compute_expires_at(started_at=now, time_limit_seconds=limit)

        attempt = Attempt.objects.create(
            user=user,
            mode=exam.mode,
            state=AttemptState.IN_PROGRESS,
            exam_definition=exam,
            time_limit_seconds=limit,
            started_at=now,
            expires_at=expires,
            score_summary={},
        )
        items = []
        for position, question in enumerate(questions, start=1):
            version = question.current_version
            if version is None:
                raise ExamUnavailable("A selected question has no published version.")
            items.append(
                AttemptItem(
                    attempt=attempt,
                    position=position,
                    question=question,
                    question_version=version,
                    selected_answer=None,
                    is_correct=None,
                )
            )
        AttemptItem.objects.bulk_create(items)
        return attempt

    @classmethod
    def get_item(cls, attempt: Attempt, position: int) -> AttemptItem:
        try:
            pos = int(position)
        except (TypeError, ValueError) as exc:
            raise InvalidNavigation() from exc
        item = (
            attempt.items.select_related(
                "question",
                "question_version",
            )
            .prefetch_related(
                "question_version__options",
                "question_version__options__translations",
                "question_version__translations",
            )
            .filter(position=pos)
            .first()
        )
        if item is None:
            raise InvalidNavigation()
        return item

    @classmethod
    def persist_answer(
        cls, user, attempt_id, *, position: int, option_key: str | None = None, truths=None
    ) -> AnswerPersistResult:
        try:
            attempt = cls.require_active_attempt(user, attempt_id)
        except AttemptNotFound:
            return AnswerPersistResult(False, "not_found", "Exam attempt not found.")
        except AttemptForbidden:
            return AnswerPersistResult(False, "forbidden", "You cannot update this attempt.")
        except AttemptAlreadySubmitted:
            return AnswerPersistResult(
                False, "already_submitted", "This exam attempt is already submitted."
            )
        except AttemptNotActive:
            return AnswerPersistResult(False, "not_active", "This exam attempt is not active.")

        try:
            item = cls.get_item(attempt, position)
        except InvalidNavigation:
            return AnswerPersistResult(
                False, "invalid_navigation", "That question is not part of this attempt."
            )

        from apps.assessment.services.answers import normalize_answer

        norm = normalize_answer(item, option_key=option_key, truths=truths)
        if not norm.ok:
            return AnswerPersistResult(False, norm.code, norm.message)
        if norm.clear:
            item.selected_answer = None
            item.answered_at = None
            item.save(update_fields=["selected_answer", "answered_at"])
            return AnswerPersistResult(True, "cleared", norm.message, item=item)

        item.selected_answer = norm.selected_answer
        item.answered_at = timezone.now()
        item.is_correct = None
        item.save(update_fields=["selected_answer", "answered_at", "is_correct"])
        return AnswerPersistResult(True, "saved", norm.message, item=item)

    @classmethod
    @transaction.atomic
    def submit(cls, user, attempt_id) -> SubmitResult:
        attempt = (
            Attempt.objects.select_for_update()
            .filter(pk=attempt_id)
            .first()
        )
        if attempt is None:
            raise AttemptNotFound()
        decision = ExamAccessService.decide(user, attempt)
        if not decision.allowed:
            if decision.reason == "forbidden":
                raise AttemptForbidden()
            raise AttemptNotFound()

        if attempt.state == AttemptState.COMPLETED:
            return SubmitResult(
                attempt=attempt,
                score_summary=dict(attempt.score_summary or {}),
                already_submitted=True,
            )
        if attempt.state == AttemptState.SUBMITTED:
            attempt = cls._finalize_locked(attempt, already_submitted=True)
            return SubmitResult(
                attempt=attempt,
                score_summary=dict(attempt.score_summary or {}),
                already_submitted=True,
            )

        if attempt.state not in {AttemptState.IN_PROGRESS, AttemptState.NOT_STARTED}:
            raise AttemptNotActive()

        # Timeout path may also call finalize; user submit uses the same finalize.
        attempt = cls._finalize_locked(attempt, already_submitted=False)
        return SubmitResult(
            attempt=attempt,
            score_summary=dict(attempt.score_summary or {}),
            already_submitted=False,
        )

    @classmethod
    def progress_counts(cls, attempt: Attempt) -> dict:
        items = list(attempt.items.values_list("selected_answer", flat=True))
        total = len(items)
        answered = sum(1 for a in items if selected_key(a) is not None)
        return {
            "total": total,
            "answered": answered,
            "unanswered": total - answered,
        }

    @classmethod
    def history_for_user(cls, user, *, page: int = 1, page_size: int = 20):
        if not ExamAccessService.user_may_take_exams(user):
            return [], 0
        try:
            page = max(1, int(page))
        except (TypeError, ValueError):
            page = 1
        try:
            page_size = min(50, max(1, int(page_size)))
        except (TypeError, ValueError):
            page_size = 20
        qs = (
            Attempt.objects.filter(user=user)
            .exclude(exam_definition__isnull=True)
            .select_related("exam_definition")
            .order_by("-created_at")
        )
        total = qs.count()
        start = (page - 1) * page_size
        rows = list(qs[start : start + page_size])
        return rows, total

    @classmethod
    def in_progress_for_user(cls, user) -> list[Attempt]:
        if not ExamAccessService.user_may_take_exams(user):
            return []
        rows = list(
            Attempt.objects.filter(
                user=user,
                state=AttemptState.IN_PROGRESS,
            )
            .exclude(exam_definition__isnull=True)
            .select_related("exam_definition")
            .order_by("-started_at", "-created_at")[:10]
        )
        # Drop any that auto-submit during listing.
        live = []
        for a in rows:
            a2 = cls.enforce_timeout(user, a)
            if a2.state == AttemptState.IN_PROGRESS:
                live.append(a2)
        return live

    @classmethod
    def timer_for(cls, attempt: Attempt):
        return timer_snapshot(attempt)
