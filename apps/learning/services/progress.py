"""Server-owned learner progress and continue-learning cursor (docs/05 §7.2, docs/09 §7)."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from apps.common.choices import LocaleCode
from apps.learning.models import ContinueLearningCursor, LearnerProgress, Lesson
from apps.learning.services.access import LearningAccessService
from apps.learning.services.catalog import LearningCatalogService


class CompletionResult(str, Enum):
    COMPLETED = "completed"
    ALREADY_COMPLETED = "already_completed"
    UNAUTHORIZED = "unauthorized"
    UNAVAILABLE = "unavailable"
    NOT_FOUND = "not_found"


@dataclass(frozen=True)
class ProgressSnapshot:
    completed_count: int
    total_count: int
    percent: int

    @property
    def empty(self) -> bool:
        return self.total_count == 0


@dataclass(frozen=True)
class ContinueLearningState:
    available: bool
    empty: bool
    lesson: Lesson | None
    lesson_title: str
    course_title: str
    href: str
    message: str


class LearningProgressService:
    """Lesson completion + hierarchy progress + continue-learning source of truth."""

    @classmethod
    def snapshot_for_lessons(cls, user, lesson_ids: list) -> ProgressSnapshot:
        total = len(lesson_ids)
        if total == 0:
            return ProgressSnapshot(0, 0, 0)
        if user is None or not getattr(user, "is_authenticated", False):
            return ProgressSnapshot(0, total, 0)
        completed = LearnerProgress.objects.filter(
            user=user,
            lesson_id__in=lesson_ids,
            is_completed=True,
        ).count()
        percent = int(round((completed / total) * 100)) if total else 0
        return ProgressSnapshot(completed, total, percent)

    @classmethod
    def snapshot_for_course(cls, user, course) -> ProgressSnapshot:
        lesson_ids = list(
            LearningCatalogService.published_lessons_in_course(course).values_list(
                "id", flat=True
            )
        )
        return cls.snapshot_for_lessons(user, lesson_ids)

    @classmethod
    def snapshot_for_subtree(cls, user, **filters) -> ProgressSnapshot:
        lesson_ids = list(
            LearningCatalogService.published_lessons_in_subtree(**filters).values_list(
                "id", flat=True
            )
        )
        return cls.snapshot_for_lessons(user, lesson_ids)

    @classmethod
    def is_lesson_completed(cls, user, lesson: Lesson) -> bool:
        if user is None or not getattr(user, "is_authenticated", False):
            return False
        return LearnerProgress.objects.filter(
            user=user, lesson=lesson, is_completed=True
        ).exists()

    @classmethod
    def completed_lesson_ids(cls, user, lesson_ids: list) -> set:
        if not lesson_ids or user is None or not getattr(user, "is_authenticated", False):
            return set()
        return set(
            LearnerProgress.objects.filter(
                user=user,
                lesson_id__in=lesson_ids,
                is_completed=True,
            ).values_list("lesson_id", flat=True)
        )

    @classmethod
    @transaction.atomic
    def complete_lesson(cls, *, user, lesson: Lesson | None) -> CompletionResult:
        if lesson is None:
            return CompletionResult.NOT_FOUND
        decision = LearningAccessService.can_complete_lesson(user, lesson)
        if not decision.allowed:
            if decision.reason == "forbidden":
                return CompletionResult.UNAUTHORIZED
            if LearningAccessService.hide_as_not_found(decision):
                return CompletionResult.NOT_FOUND
            return CompletionResult.UNAVAILABLE

        existing = (
            LearnerProgress.objects.select_for_update()
            .filter(user=user, lesson=lesson)
            .first()
        )
        now = timezone.now()
        if existing and existing.is_completed:
            cls._touch_continue_cursor(user=user, lesson=lesson)
            return CompletionResult.ALREADY_COMPLETED

        if existing is None:
            LearnerProgress.objects.create(
                user=user,
                lesson=lesson,
                topic=lesson.topic,
                is_completed=True,
                completed_at=now,
                progress_percent=100,
            )
        else:
            existing.is_completed = True
            existing.completed_at = now
            existing.progress_percent = 100
            existing.topic = lesson.topic
            existing.save(
                update_fields=[
                    "is_completed",
                    "completed_at",
                    "progress_percent",
                    "topic",
                    "updated_at",
                ]
            )
        cls._touch_continue_cursor(user=user, lesson=lesson)
        return CompletionResult.COMPLETED

    @classmethod
    @transaction.atomic
    def record_lesson_visit(cls, *, user, lesson: Lesson) -> None:
        """Update continue-learning cursor when a learner opens an available lesson."""
        decision = LearningAccessService.decide_lesson(user, lesson)
        if not decision.allowed:
            return
        cls._touch_continue_cursor(user=user, lesson=lesson)

    @classmethod
    def _touch_continue_cursor(cls, *, user, lesson: Lesson) -> None:
        ContinueLearningCursor.objects.update_or_create(
            user=user,
            defaults={
                "lesson": lesson,
                "topic": lesson.topic,
                "last_position_meta": {
                    "lesson_id": str(lesson.id),
                    "topic_id": str(lesson.topic_id),
                },
            },
        )

    @classmethod
    def continue_learning_for(cls, user, *, locale: str) -> ContinueLearningState:
        """
        Honest continue-learning: available once Learning module is live.
        Empty when no valid published resume target exists.
        """
        empty = ContinueLearningState(
            available=True,
            empty=True,
            lesson=None,
            lesson_title="",
            course_title="",
            href=reverse("learning:catalog"),
            message="No learning progress yet. Browse the course catalog to begin.",
        )
        if user is None or not getattr(user, "is_authenticated", False):
            return empty

        try:
            cursor = ContinueLearningCursor.objects.select_related(
                "lesson",
                "lesson__topic",
                "lesson__topic__chapter",
                "lesson__topic__chapter__unit",
                "lesson__topic__chapter__unit__subject",
                "lesson__topic__chapter__unit__subject__course",
            ).get(user=user)
        except ContinueLearningCursor.DoesNotExist:
            return empty

        lesson = cursor.lesson
        if lesson is None:
            return empty
        decision = LearningAccessService.decide_lesson(user, lesson)
        if not decision.allowed:
            return empty

        locale = locale or getattr(user, "ui_locale", LocaleCode.EN)
        lesson_title = LearningCatalogService.title_for(lesson, locale)
        course = lesson.topic.chapter.unit.subject.course
        course_title = LearningCatalogService.title_for(course, locale)
        return ContinueLearningState(
            available=True,
            empty=False,
            lesson=lesson,
            lesson_title=lesson_title,
            course_title=course_title,
            href=reverse("learning:lesson", kwargs={"lesson_id": lesson.id}),
            message="",
        )
