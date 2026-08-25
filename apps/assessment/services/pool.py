"""
Server-authoritative practice question pool selection (docs/09 §9).

Never trusts client-supplied question IDs. Resolves published entitled questions
linked to the learning hierarchy scope via Question ↔ Topic M:N.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass

from django.db.models import QuerySet

from apps.assessment.models import Question
from apps.common.choices import DifficultyLevel, EditorialState
from apps.learning.models import Chapter, Course, Subject, Topic, Unit


ALLOWED_SCOPE_TYPES = frozenset(
    {"course", "subject", "unit", "chapter", "topic", "random"}
)
ALLOWED_DIFFICULTIES = frozenset(d.value for d in DifficultyLevel)
DEFAULT_QUESTION_COUNT = 10
MAX_QUESTION_COUNT = 50
MIN_QUESTION_COUNT = 1


@dataclass(frozen=True)
class PracticeScope:
    scope_type: str
    scope_id: uuid.UUID | None
    difficulty: str | None
    count: int

    @property
    def label_key(self) -> str:
        return self.scope_type


class PracticePoolService:
    """Resolve and sample the entitled published question pool for practice."""

    @classmethod
    def validate_setup(
        cls,
        *,
        scope_type: str,
        scope_id: str | uuid.UUID | None,
        difficulty: str | None,
        count: int | str | None,
        user,
    ) -> PracticeScope:
        from apps.assessment.services.exceptions import PracticeSetupError, PracticeUnavailable

        st = (scope_type or "").strip().lower()
        if st not in ALLOWED_SCOPE_TYPES:
            raise PracticeSetupError("Choose a valid practice scope.")

        parsed_id: uuid.UUID | None = None
        if st != "random":
            if not scope_id:
                raise PracticeSetupError("Select a learning scope for practice.")
            try:
                parsed_id = uuid.UUID(str(scope_id))
            except (TypeError, ValueError) as exc:
                raise PracticeSetupError("Invalid practice scope.") from exc
            if not cls._scope_node_visible(user, st, parsed_id):
                raise PracticeUnavailable("Practice is not available for this scope.")
        else:
            parsed_id = None

        diff = (difficulty or "").strip().lower() or None
        if diff is not None and diff not in ALLOWED_DIFFICULTIES:
            raise PracticeSetupError("Choose a valid difficulty, or leave it open.")

        try:
            n = int(count) if count not in (None, "") else DEFAULT_QUESTION_COUNT
        except (TypeError, ValueError) as exc:
            raise PracticeSetupError("Question count must be a number.") from exc
        if n < MIN_QUESTION_COUNT or n > MAX_QUESTION_COUNT:
            raise PracticeSetupError(
                f"Question count must be between {MIN_QUESTION_COUNT} and {MAX_QUESTION_COUNT}."
            )

        return PracticeScope(
            scope_type=st,
            scope_id=parsed_id,
            difficulty=diff,
            count=n,
        )

    @classmethod
    def _scope_node_visible(cls, user, scope_type: str, scope_id: uuid.UUID) -> bool:
        # Lazy import avoids assessment ↔ portal ↔ learning package cycles.
        from apps.learning.services.access import LearningAccessService

        node = cls._load_scope_node(scope_type, scope_id)
        if node is None:
            return False
        decision = LearningAccessService.decide_node(user, node)
        if not decision.allowed:
            return False
        # Ancestry must also be published for hierarchy scopes.
        ancestors = cls._ancestors_for(node)
        return all(LearningAccessService.is_learner_visible_node(a) for a in ancestors)

    @classmethod
    def _load_scope_node(cls, scope_type: str, scope_id: uuid.UUID):
        model = {
            "course": Course,
            "subject": Subject,
            "unit": Unit,
            "chapter": Chapter,
            "topic": Topic,
        }.get(scope_type)
        if model is None:
            return None
        return model.objects.filter(pk=scope_id).first()

    @classmethod
    def _ancestors_for(cls, node) -> list:
        if isinstance(node, Course):
            return []
        if isinstance(node, Subject):
            return [node.course]
        if isinstance(node, Unit):
            return [node.subject, node.subject.course]
        if isinstance(node, Chapter):
            return [node.unit, node.unit.subject, node.unit.subject.course]
        if isinstance(node, Topic):
            ch = node.chapter
            return [
                ch,
                ch.unit,
                ch.unit.subject,
                ch.unit.subject.course,
            ]
        return []

    @classmethod
    def topic_ids_for_scope(cls, scope: PracticeScope) -> list[uuid.UUID] | None:
        """Return topic UUID list for hierarchy scopes; None means all topics (random)."""
        if scope.scope_type == "random":
            return None
        if scope.scope_type == "topic":
            return [scope.scope_id] if scope.scope_id else []
        if scope.scope_type == "chapter":
            return list(
                Topic.objects.filter(
                    chapter_id=scope.scope_id,
                    editorial_state=EditorialState.PUBLISHED,
                    is_archived=False,
                ).values_list("id", flat=True)
            )
        if scope.scope_type == "unit":
            return list(
                Topic.objects.filter(
                    chapter__unit_id=scope.scope_id,
                    editorial_state=EditorialState.PUBLISHED,
                    is_archived=False,
                    chapter__editorial_state=EditorialState.PUBLISHED,
                    chapter__is_archived=False,
                ).values_list("id", flat=True)
            )
        if scope.scope_type == "subject":
            return list(
                Topic.objects.filter(
                    chapter__unit__subject_id=scope.scope_id,
                    editorial_state=EditorialState.PUBLISHED,
                    is_archived=False,
                    chapter__editorial_state=EditorialState.PUBLISHED,
                    chapter__is_archived=False,
                    chapter__unit__editorial_state=EditorialState.PUBLISHED,
                    chapter__unit__is_archived=False,
                ).values_list("id", flat=True)
            )
        if scope.scope_type == "course":
            return list(
                Topic.objects.filter(
                    chapter__unit__subject__course_id=scope.scope_id,
                    editorial_state=EditorialState.PUBLISHED,
                    is_archived=False,
                    chapter__editorial_state=EditorialState.PUBLISHED,
                    chapter__is_archived=False,
                    chapter__unit__editorial_state=EditorialState.PUBLISHED,
                    chapter__unit__is_archived=False,
                    chapter__unit__subject__editorial_state=EditorialState.PUBLISHED,
                    chapter__unit__subject__is_archived=False,
                ).values_list("id", flat=True)
            )
        return []

    @classmethod
    def published_pool_qs(cls, scope: PracticeScope) -> QuerySet[Question]:
        qs = (
            Question.objects.filter(
                editorial_state=EditorialState.PUBLISHED,
                is_archived=False,
                current_version__isnull=False,
            )
            .select_related("current_version")
            .distinct()
        )
        topic_ids = cls.topic_ids_for_scope(scope)
        if topic_ids is not None:
            if not topic_ids:
                return qs.none()
            qs = qs.filter(topics__id__in=topic_ids)
        # Random / hierarchy: only questions linked to at least one published topic
        # whose full ancestry is published (random draws from global entitled pool).
        if scope.scope_type == "random":
            qs = qs.filter(
                topics__editorial_state=EditorialState.PUBLISHED,
                topics__is_archived=False,
                topics__chapter__editorial_state=EditorialState.PUBLISHED,
                topics__chapter__is_archived=False,
                topics__chapter__unit__editorial_state=EditorialState.PUBLISHED,
                topics__chapter__unit__is_archived=False,
                topics__chapter__unit__subject__editorial_state=EditorialState.PUBLISHED,
                topics__chapter__unit__subject__is_archived=False,
                topics__chapter__unit__subject__course__editorial_state=EditorialState.PUBLISHED,
                topics__chapter__unit__subject__course__is_archived=False,
            )
        if scope.difficulty:
            qs = qs.filter(difficulty=scope.difficulty)
        return qs

    @classmethod
    def select_questions(cls, scope: PracticeScope) -> list[Question]:
        from apps.assessment.services.exceptions import PracticePoolEmpty

        qs = cls.published_pool_qs(scope)
        # Deterministic-enough random sample without trusting client IDs.
        ids = list(qs.values_list("id", flat=True))
        if not ids:
            raise PracticePoolEmpty()
        import random

        sample_size = min(scope.count, len(ids))
        chosen_ids = random.sample(ids, sample_size)
        # Preserve sampled order as attempt sequence.
        by_id = {
            q.id: q
            for q in Question.objects.filter(id__in=chosen_ids).select_related(
                "current_version"
            )
        }
        return [by_id[i] for i in chosen_ids if i in by_id]
