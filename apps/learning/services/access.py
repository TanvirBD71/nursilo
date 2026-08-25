"""Server-side learning access decisions (docs/09 §7, docs/24)."""
from __future__ import annotations

from dataclasses import dataclass
from apps.common.choices import EditorialState
from apps.entitlements.services import EntitlementService
from apps.learning.models import LearningMaterial, Lesson


@dataclass(frozen=True)
class AccessDecision:
    allowed: bool
    reason: str = ""  # not_found | unpublished | archived | premium_required | forbidden


class LearningAccessService:
    """
    Fail-closed learner visibility for catalog nodes and materials.
    Frontend visibility never grants access — callers must use these decisions.
    Premium evaluation is owned by EntitlementService (UNIT-8).
    """

    @classmethod
    def user_is_premium(cls, user) -> bool:
        if user is None or not getattr(user, "is_authenticated", False):
            return False
        return EntitlementService.is_premium(user)

    @classmethod
    def is_learner_visible_node(cls, node) -> bool:
        if node is None:
            return False
        if getattr(node, "is_archived", True):
            return False
        return getattr(node, "editorial_state", None) == EditorialState.PUBLISHED

    @classmethod
    def ancestors_visible(cls, lesson: Lesson) -> bool:
        """Lesson available only when itself and full ancestry are published/non-archived."""
        topic = lesson.topic
        chapter = topic.chapter
        unit = chapter.unit
        subject = unit.subject
        course = subject.course
        return all(
            cls.is_learner_visible_node(n)
            for n in (lesson, topic, chapter, unit, subject, course)
        )

    @classmethod
    def decide_node(cls, user, node) -> AccessDecision:
        if node is None:
            return AccessDecision(False, "not_found")
        if user is None or not getattr(user, "is_authenticated", False):
            return AccessDecision(False, "forbidden")
        if getattr(node, "is_archived", False):
            return AccessDecision(False, "archived")
        if getattr(node, "editorial_state", None) != EditorialState.PUBLISHED:
            return AccessDecision(False, "unpublished")
        return AccessDecision(True)

    @classmethod
    def decide_lesson(cls, user, lesson: Lesson | None) -> AccessDecision:
        base = cls.decide_node(user, lesson)
        if not base.allowed:
            return base
        assert lesson is not None
        if not cls.ancestors_visible(lesson):
            # Treat broken ancestry as not discoverable — no leakage.
            return AccessDecision(False, "unpublished")
        return AccessDecision(True)

    @classmethod
    def decide_material(
        cls, user, material: LearningMaterial | None, *, via_lesson: Lesson | None = None
    ) -> AccessDecision:
        base = cls.decide_node(user, material)
        if not base.allowed:
            return base
        assert material is not None
        if via_lesson is not None:
            lesson_decision = cls.decide_lesson(user, via_lesson)
            if not lesson_decision.allowed:
                return lesson_decision
        if material.is_premium and not cls.user_is_premium(user):
            return AccessDecision(False, "premium_required")
        return AccessDecision(True)

    @classmethod
    def can_complete_lesson(cls, user, lesson: Lesson | None) -> AccessDecision:
        return cls.decide_lesson(user, lesson)

    @classmethod
    def hide_as_not_found(cls, decision: AccessDecision) -> bool:
        """Unpublished/archived/missing must not reveal existence to learners."""
        return decision.reason in {"not_found", "unpublished", "archived"}
