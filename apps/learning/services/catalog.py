"""Published learning catalog queries and translation resolution (docs/05 §7)."""
from __future__ import annotations

from typing import Iterable

from django.db.models import Prefetch, QuerySet

from apps.common.choices import EditorialState, LocaleCode
from apps.learning.models import (
    Chapter,
    Course,
    CourseTranslation,
    LearningMaterial,
    LearningMaterialTranslation,
    Lesson,
    LessonLearningMaterial,
    LessonTranslation,
    Subject,
    Topic,
    Unit,
)


class LearningCatalogService:
    """Read-side catalog helpers. Never invent content; only Published + non-archived."""

    FALLBACK_LOCALES = (LocaleCode.EN, LocaleCode.BN)

    @classmethod
    def published_qs(cls, model) -> QuerySet:
        return model.objects.filter(
            editorial_state=EditorialState.PUBLISHED,
            is_archived=False,
        )

    @classmethod
    def resolve_translation(cls, translations: Iterable, locale: str):
        by_locale = {t.locale: t for t in translations}
        if locale in by_locale:
            return by_locale[locale]
        for code in cls.FALLBACK_LOCALES:
            if code in by_locale:
                return by_locale[code]
        return next(iter(by_locale.values()), None)

    @classmethod
    def title_for(cls, node, locale: str, *, blank: str = "Untitled") -> str:
        translation = cls.resolve_translation(node.translations.all(), locale)
        if translation is None:
            return blank
        return getattr(translation, "title", None) or blank

    @classmethod
    def summary_for(cls, node, locale: str) -> str:
        translation = cls.resolve_translation(node.translations.all(), locale)
        if translation is None:
            return ""
        return getattr(translation, "summary", None) or getattr(translation, "body", None) or ""

    @classmethod
    def body_for(cls, node, locale: str) -> str:
        translation = cls.resolve_translation(node.translations.all(), locale)
        if translation is None:
            return ""
        return getattr(translation, "body", None) or ""

    @classmethod
    def list_courses(cls) -> QuerySet:
        return (
            cls.published_qs(Course)
            .prefetch_related(
                Prefetch(
                    "translations",
                    queryset=CourseTranslation.objects.order_by("locale"),
                )
            )
            .order_by("sort_order", "created_at")
        )

    @classmethod
    def get_course(cls, course_id) -> Course | None:
        return (
            cls.published_qs(Course)
            .prefetch_related("translations")
            .filter(pk=course_id)
            .first()
        )

    @classmethod
    def get_subject(cls, subject_id) -> Subject | None:
        return (
            cls.published_qs(Subject)
            .select_related("course")
            .prefetch_related("translations", "course__translations")
            .filter(pk=subject_id)
            .first()
        )

    @classmethod
    def get_unit(cls, unit_id) -> Unit | None:
        return (
            cls.published_qs(Unit)
            .select_related("subject", "subject__course")
            .prefetch_related(
                "translations",
                "subject__translations",
                "subject__course__translations",
            )
            .filter(pk=unit_id)
            .first()
        )

    @classmethod
    def get_chapter(cls, chapter_id) -> Chapter | None:
        return (
            cls.published_qs(Chapter)
            .select_related("unit", "unit__subject", "unit__subject__course")
            .prefetch_related(
                "translations",
                "unit__translations",
                "unit__subject__translations",
                "unit__subject__course__translations",
            )
            .filter(pk=chapter_id)
            .first()
        )

    @classmethod
    def get_topic(cls, topic_id) -> Topic | None:
        return (
            cls.published_qs(Topic)
            .select_related(
                "chapter",
                "chapter__unit",
                "chapter__unit__subject",
                "chapter__unit__subject__course",
            )
            .prefetch_related(
                "translations",
                "chapter__translations",
                "chapter__unit__translations",
                "chapter__unit__subject__translations",
                "chapter__unit__subject__course__translations",
            )
            .filter(pk=topic_id)
            .first()
        )

    @classmethod
    def get_lesson(cls, lesson_id) -> Lesson | None:
        return (
            Lesson.objects.select_related(
                "topic",
                "topic__chapter",
                "topic__chapter__unit",
                "topic__chapter__unit__subject",
                "topic__chapter__unit__subject__course",
            )
            .prefetch_related(
                Prefetch(
                    "translations",
                    queryset=LessonTranslation.objects.order_by("locale"),
                ),
                Prefetch(
                    "lessonlearningmaterial_set",
                    queryset=LessonLearningMaterial.objects.select_related(
                        "learning_material"
                    )
                    .prefetch_related(
                        Prefetch(
                            "learning_material__translations",
                            queryset=LearningMaterialTranslation.objects.order_by(
                                "locale"
                            ),
                        )
                    )
                    .order_by("sort_order"),
                ),
                "topic__translations",
                "topic__chapter__translations",
                "topic__chapter__unit__translations",
                "topic__chapter__unit__subject__translations",
                "topic__chapter__unit__subject__course__translations",
            )
            .filter(pk=lesson_id)
            .first()
        )

    @classmethod
    def get_material(cls, material_id) -> LearningMaterial | None:
        return (
            LearningMaterial.objects.prefetch_related("translations")
            .filter(pk=material_id)
            .first()
        )

    @classmethod
    def published_children(cls, parent, child_model, fk_field: str) -> QuerySet:
        return (
            cls.published_qs(child_model)
            .filter(**{fk_field: parent})
            .prefetch_related("translations")
            .order_by("sort_order", "created_at")
        )

    @classmethod
    def published_lessons_for_topic(cls, topic: Topic) -> QuerySet:
        return cls.published_children(topic, Lesson, "topic")

    @classmethod
    def published_lessons_in_course(cls, course: Course) -> QuerySet:
        return (
            cls.published_qs(Lesson)
            .filter(
                topic__editorial_state=EditorialState.PUBLISHED,
                topic__is_archived=False,
                topic__chapter__editorial_state=EditorialState.PUBLISHED,
                topic__chapter__is_archived=False,
                topic__chapter__unit__editorial_state=EditorialState.PUBLISHED,
                topic__chapter__unit__is_archived=False,
                topic__chapter__unit__subject__editorial_state=EditorialState.PUBLISHED,
                topic__chapter__unit__subject__is_archived=False,
                topic__chapter__unit__subject__course=course,
                topic__chapter__unit__subject__course__editorial_state=EditorialState.PUBLISHED,
                topic__chapter__unit__subject__course__is_archived=False,
            )
            .order_by(
                "topic__chapter__unit__subject__sort_order",
                "topic__chapter__unit__sort_order",
                "topic__chapter__sort_order",
                "topic__sort_order",
                "sort_order",
                "created_at",
            )
        )

    @classmethod
    def published_lessons_in_subtree(cls, *, subject=None, unit=None, chapter=None, topic=None) -> QuerySet:
        qs = cls.published_qs(Lesson).filter(
            topic__editorial_state=EditorialState.PUBLISHED,
            topic__is_archived=False,
            topic__chapter__editorial_state=EditorialState.PUBLISHED,
            topic__chapter__is_archived=False,
            topic__chapter__unit__editorial_state=EditorialState.PUBLISHED,
            topic__chapter__unit__is_archived=False,
            topic__chapter__unit__subject__editorial_state=EditorialState.PUBLISHED,
            topic__chapter__unit__subject__is_archived=False,
            topic__chapter__unit__subject__course__editorial_state=EditorialState.PUBLISHED,
            topic__chapter__unit__subject__course__is_archived=False,
        )
        if topic is not None:
            qs = qs.filter(topic=topic)
        elif chapter is not None:
            qs = qs.filter(topic__chapter=chapter)
        elif unit is not None:
            qs = qs.filter(topic__chapter__unit=unit)
        elif subject is not None:
            qs = qs.filter(topic__chapter__unit__subject=subject)
        return qs.order_by("sort_order", "created_at")

    @classmethod
    def sibling_lessons(cls, lesson: Lesson) -> list[Lesson]:
        return list(cls.published_lessons_for_topic(lesson.topic))

    @classmethod
    def prev_next_lessons(cls, lesson: Lesson) -> tuple[Lesson | None, Lesson | None]:
        siblings = cls.sibling_lessons(lesson)
        ids = [s.id for s in siblings]
        try:
            idx = ids.index(lesson.id)
        except ValueError:
            return None, None
        prev_lesson = siblings[idx - 1] if idx > 0 else None
        next_lesson = siblings[idx + 1] if idx + 1 < len(siblings) else None
        return prev_lesson, next_lesson
