"""
PracticeService — formative practice runtime (docs/05 §9, docs/09 §9–11).

Owns setup validation, pool selection, attempt lifecycle, answer persistence,
submission/scoring, history listing. Templates/views never score or authorize.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from apps.assessment.models import Attempt, AttemptItem
from apps.assessment.services.access import PracticeAccessService
from apps.assessment.services.exceptions import (
    AttemptAlreadySubmitted,
    AttemptForbidden,
    AttemptNotActive,
    AttemptNotFound,
    InvalidAnswer,
    InvalidNavigation,
    PracticeCapExceeded,
    PracticeUnavailable,
)
from apps.assessment.services.pool import PracticePoolService, PracticeScope
from apps.assessment.services.scoring import score_attempt_items, selected_key
from apps.common.choices import AttemptMode, AttemptState
from apps.platform.models import PlatformSetting


# Configurable via PlatformSetting key; default aligns with freemium intent (docs/09 §9).
FREE_PRACTICE_CAP_SETTING_KEY = "practice.free_daily_question_cap"
DEFAULT_FREE_DAILY_QUESTION_CAP = 50


@dataclass(frozen=True)
class AnswerPersistResult:
    ok: bool
    code: str
    message: str
    item: AttemptItem | None = None


@dataclass(frozen=True)
class SubmitResult:
    attempt: Attempt
    score_summary: dict
    already_submitted: bool = False


class PracticeService:
    """Authoritative practice attempt orchestrator."""

    @classmethod
    def free_daily_question_cap(cls) -> int:
        row = PlatformSetting.objects.filter(pk=FREE_PRACTICE_CAP_SETTING_KEY).first()
        if row is None:
            return DEFAULT_FREE_DAILY_QUESTION_CAP
        value = row.value or {}
        try:
            limit = int(value.get("limit", DEFAULT_FREE_DAILY_QUESTION_CAP))
        except (TypeError, ValueError):
            return DEFAULT_FREE_DAILY_QUESTION_CAP
        return max(0, limit)

    @classmethod
    def questions_practiced_today(cls, user) -> int:
        start = timezone.localtime(timezone.now()).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        end = start + timedelta(days=1)
        return (
            AttemptItem.objects.filter(
                attempt__user=user,
                attempt__mode=AttemptMode.PRACTICE,
                attempt__started_at__gte=start,
                attempt__started_at__lt=end,
            ).count()
        )

    @classmethod
    def assert_practice_entitled(cls, user, *, requested_count: int) -> None:
        if not PracticeAccessService.user_may_practice(user):
            raise AttemptForbidden("Practice requires a student account.")
        from apps.portal.services.subscription import SubscriptionPresentationService

        sub = SubscriptionPresentationService.for_user(user)
        if sub.is_premium:
            return
        cap = cls.free_daily_question_cap()
        used = cls.questions_practiced_today(user)
        if used + requested_count > cap:
            raise PracticeCapExceeded(
                "Free practice limit reached for today. Upgrade to Premium or try again later."
            )

    @classmethod
    def validate_setup(cls, user, *, scope_type, scope_id, difficulty, count) -> PracticeScope:
        if not PracticeAccessService.user_may_practice(user):
            raise AttemptForbidden("Practice requires a student account.")
        return PracticePoolService.validate_setup(
            scope_type=scope_type,
            scope_id=scope_id,
            difficulty=difficulty,
            count=count,
            user=user,
        )

    @classmethod
    @transaction.atomic
    def start_practice(
        cls,
        user,
        *,
        scope_type,
        scope_id=None,
        difficulty=None,
        count=None,
    ) -> Attempt:
        scope = cls.validate_setup(
            user,
            scope_type=scope_type,
            scope_id=scope_id,
            difficulty=difficulty,
            count=count,
        )
        questions = PracticePoolService.select_questions(scope)
        cls.assert_practice_entitled(user, requested_count=len(questions))

        now = timezone.now()
        attempt = Attempt.objects.create(
            user=user,
            mode=AttemptMode.PRACTICE,
            state=AttemptState.IN_PROGRESS,
            scope_type=scope.scope_type,
            scope_id=scope.scope_id,
            started_at=now,
            score_summary={},
        )
        items = []
        for position, question in enumerate(questions, start=1):
            version = question.current_version
            if version is None:
                raise PracticeUnavailable("A selected question has no published version.")
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
    def require_owned_attempt(cls, user, attempt_id) -> Attempt:
        attempt = PracticeAccessService.get_owned_attempt(user, attempt_id)
        decision = PracticeAccessService.decide(user, attempt)
        if not decision.allowed:
            if decision.reason == "forbidden":
                raise AttemptForbidden()
            raise AttemptNotFound()
        assert attempt is not None
        return attempt

    @classmethod
    def require_active_attempt(cls, user, attempt_id) -> Attempt:
        attempt = cls.require_owned_attempt(user, attempt_id)
        if PracticeAccessService.is_terminal(attempt):
            raise AttemptAlreadySubmitted()
        if not PracticeAccessService.is_active(attempt):
            raise AttemptNotActive()
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
            return AnswerPersistResult(False, "not_found", "Practice attempt not found.")
        except AttemptForbidden:
            return AnswerPersistResult(False, "forbidden", "You cannot update this attempt.")
        except AttemptAlreadySubmitted:
            return AnswerPersistResult(
                False, "already_submitted", "This practice attempt is already submitted."
            )
        except AttemptNotActive:
            return AnswerPersistResult(False, "not_active", "This practice attempt is not active.")

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
        # Never set is_correct during active attempt (no answer-key side channel).
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
        decision = PracticeAccessService.decide(user, attempt)
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
            # Recover incomplete finalize if needed.
            if not attempt.score_summary:
                summary = score_attempt_items(attempt)
                attempt.state = AttemptState.COMPLETED
                attempt.completed_at = attempt.completed_at or timezone.now()
                attempt.save(update_fields=["state", "completed_at", "score_summary"])
                return SubmitResult(attempt=attempt, score_summary=summary, already_submitted=True)
            attempt.state = AttemptState.COMPLETED
            attempt.completed_at = attempt.completed_at or timezone.now()
            attempt.save(update_fields=["state", "completed_at"])
            return SubmitResult(
                attempt=attempt,
                score_summary=dict(attempt.score_summary or {}),
                already_submitted=True,
            )

        if attempt.state not in {AttemptState.IN_PROGRESS, AttemptState.NOT_STARTED}:
            raise AttemptNotActive()

        now = timezone.now()
        attempt.state = AttemptState.SUBMITTED
        attempt.save(update_fields=["state"])
        summary = score_attempt_items(attempt)
        attempt.state = AttemptState.COMPLETED
        attempt.completed_at = now
        attempt.save(update_fields=["state", "completed_at", "score_summary"])
        attempt.refresh_from_db()
        return SubmitResult(attempt=attempt, score_summary=summary, already_submitted=False)

    @classmethod
    def history_for_user(cls, user, *, page: int = 1, page_size: int = 20):
        """Own completed/in-progress practice attempts; no cross-user leakage."""
        if not PracticeAccessService.user_may_practice(user):
            return [], 0
        try:
            page = max(1, int(page))
        except (TypeError, ValueError):
            page = 1
        try:
            page_size = min(50, max(1, int(page_size)))
        except (TypeError, ValueError):
            page_size = 20
        qs = Attempt.objects.filter(user=user, mode=AttemptMode.PRACTICE).order_by(
            "-created_at"
        )
        total = qs.count()
        start = (page - 1) * page_size
        rows = list(qs[start : start + page_size])
        return rows, total

    @classmethod
    def in_progress_for_user(cls, user) -> list[Attempt]:
        if not PracticeAccessService.user_may_practice(user):
            return []
        return list(
            Attempt.objects.filter(
                user=user,
                mode=AttemptMode.PRACTICE,
                state=AttemptState.IN_PROGRESS,
            ).order_by("-started_at", "-created_at")[:10]
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
