"""Learning page presentation assembly — real server data only (docs/15 §8)."""
from __future__ import annotations

from dataclasses import dataclass

from django.urls import reverse

from apps.learning.models import (
    Chapter,
    Course,
    LearningMaterial,
    Lesson,
    Subject,
    Topic,
    Unit,
)
from apps.learning.services.access import LearningAccessService
from apps.learning.services.catalog import LearningCatalogService
from apps.learning.services.progress import LearningProgressService


@dataclass(frozen=True)
class BreadcrumbItem:
    label: str
    href: str | None = None


@dataclass(frozen=True)
class ChildItem:
    id: object
    title: str
    summary: str
    href: str
    completed: bool = False
    locked: bool = False
    lock_reason: str = ""


class LearningPresentationService:
    @classmethod
    def locale_for(cls, user) -> str:
        return getattr(user, "ui_locale", None) or "en"

    @classmethod
    def _crumb(cls, label: str, url_name: str | None = None, **kwargs) -> BreadcrumbItem:
        if url_name is None:
            return BreadcrumbItem(label=label, href=None)
        return BreadcrumbItem(label=label, href=reverse(url_name, kwargs=kwargs))

    @classmethod
    def _course_crumbs(cls, locale: str, course: Course) -> list[BreadcrumbItem]:
        return [
            cls._crumb("Learn", "learning:catalog"),
            cls._crumb(
                LearningCatalogService.title_for(course, locale),
                "learning:course",
                course_id=course.id,
            ),
        ]

    @classmethod
    def catalog(cls, user) -> dict:
        locale = cls.locale_for(user)
        courses = list(LearningCatalogService.list_courses())
        items = []
        for course in courses:
            progress = LearningProgressService.snapshot_for_course(user, course)
            items.append(
                {
                    "id": course.id,
                    "title": LearningCatalogService.title_for(course, locale),
                    "summary": LearningCatalogService.summary_for(course, locale),
                    "href": reverse("learning:course", kwargs={"course_id": course.id}),
                    "progress": progress,
                }
            )
        return {
            "page_heading": "Courses",
            "courses": items,
            "is_empty": len(items) == 0,
            "breadcrumbs": [cls._crumb("Learn", "learning:catalog")],
        }

    @classmethod
    def course_overview(cls, user, course: Course) -> dict:
        locale = cls.locale_for(user)
        subjects = LearningCatalogService.published_children(course, Subject, "course")
        progress = LearningProgressService.snapshot_for_course(user, course)
        children = [
            ChildItem(
                id=s.id,
                title=LearningCatalogService.title_for(s, locale),
                summary=LearningCatalogService.summary_for(s, locale),
                href=reverse("learning:subject", kwargs={"subject_id": s.id}),
            )
            for s in subjects
        ]
        return {
            "page_heading": LearningCatalogService.title_for(course, locale),
            "summary": LearningCatalogService.summary_for(course, locale),
            "node_kind": "course",
            "progress": progress,
            "children": children,
            "children_empty": len(children) == 0,
            "child_label": "Subjects",
            "breadcrumbs": cls._course_crumbs(locale, course),
            "practice_href": cls._practice_href("course", course.id),
        }

    @classmethod
    def subject_page(cls, user, subject: Subject) -> dict:
        locale = cls.locale_for(user)
        course = subject.course
        units = LearningCatalogService.published_children(subject, Unit, "subject")
        progress = LearningProgressService.snapshot_for_subtree(user, subject=subject)
        children = [
            ChildItem(
                id=u.id,
                title=LearningCatalogService.title_for(u, locale),
                summary=LearningCatalogService.summary_for(u, locale),
                href=reverse("learning:unit", kwargs={"unit_id": u.id}),
            )
            for u in units
        ]
        crumbs = cls._course_crumbs(locale, course)
        crumbs.append(
            cls._crumb(
                LearningCatalogService.title_for(subject, locale),
                "learning:subject",
                subject_id=subject.id,
            )
        )
        return cls._hierarchy_page(
            heading=LearningCatalogService.title_for(subject, locale),
            summary=LearningCatalogService.summary_for(subject, locale),
            node_kind="subject",
            child_label="Units",
            children=children,
            progress=progress,
            breadcrumbs=crumbs,
            scope_id=subject.id,
        )

    @classmethod
    def unit_page(cls, user, unit: Unit) -> dict:
        locale = cls.locale_for(user)
        subject = unit.subject
        course = subject.course
        chapters = LearningCatalogService.published_children(unit, Chapter, "unit")
        progress = LearningProgressService.snapshot_for_subtree(user, unit=unit)
        children = [
            ChildItem(
                id=c.id,
                title=LearningCatalogService.title_for(c, locale),
                summary=LearningCatalogService.summary_for(c, locale),
                href=reverse("learning:chapter", kwargs={"chapter_id": c.id}),
            )
            for c in chapters
        ]
        crumbs = cls._course_crumbs(locale, course)
        crumbs.extend(
            [
                cls._crumb(
                    LearningCatalogService.title_for(subject, locale),
                    "learning:subject",
                    subject_id=subject.id,
                ),
                cls._crumb(
                    LearningCatalogService.title_for(unit, locale),
                    "learning:unit",
                    unit_id=unit.id,
                ),
            ]
        )
        return cls._hierarchy_page(
            heading=LearningCatalogService.title_for(unit, locale),
            summary=LearningCatalogService.summary_for(unit, locale),
            node_kind="unit",
            child_label="Chapters",
            children=children,
            progress=progress,
            breadcrumbs=crumbs,
            scope_id=unit.id,
        )

    @classmethod
    def chapter_page(cls, user, chapter: Chapter) -> dict:
        locale = cls.locale_for(user)
        unit = chapter.unit
        subject = unit.subject
        course = subject.course
        topics = LearningCatalogService.published_children(chapter, Topic, "chapter")
        progress = LearningProgressService.snapshot_for_subtree(user, chapter=chapter)
        children = [
            ChildItem(
                id=t.id,
                title=LearningCatalogService.title_for(t, locale),
                summary=LearningCatalogService.summary_for(t, locale),
                href=reverse("learning:topic", kwargs={"topic_id": t.id}),
            )
            for t in topics
        ]
        crumbs = cls._course_crumbs(locale, course)
        crumbs.extend(
            [
                cls._crumb(
                    LearningCatalogService.title_for(subject, locale),
                    "learning:subject",
                    subject_id=subject.id,
                ),
                cls._crumb(
                    LearningCatalogService.title_for(unit, locale),
                    "learning:unit",
                    unit_id=unit.id,
                ),
                cls._crumb(
                    LearningCatalogService.title_for(chapter, locale),
                    "learning:chapter",
                    chapter_id=chapter.id,
                ),
            ]
        )
        return cls._hierarchy_page(
            heading=LearningCatalogService.title_for(chapter, locale),
            summary=LearningCatalogService.summary_for(chapter, locale),
            node_kind="chapter",
            child_label="Topics",
            children=children,
            progress=progress,
            breadcrumbs=crumbs,
            scope_id=chapter.id,
        )

    @classmethod
    def topic_page(cls, user, topic: Topic) -> dict:
        locale = cls.locale_for(user)
        chapter = topic.chapter
        unit = chapter.unit
        subject = unit.subject
        course = subject.course
        lessons = list(LearningCatalogService.published_lessons_for_topic(topic))
        lesson_ids = [lesson.id for lesson in lessons]
        completed_ids = LearningProgressService.completed_lesson_ids(user, lesson_ids)
        progress = LearningProgressService.snapshot_for_lessons(user, lesson_ids)
        children = [
            ChildItem(
                id=lesson.id,
                title=LearningCatalogService.title_for(lesson, locale),
                summary="",
                href=reverse("learning:lesson", kwargs={"lesson_id": lesson.id}),
                completed=lesson.id in completed_ids,
            )
            for lesson in lessons
        ]
        crumbs = cls._course_crumbs(locale, course)
        crumbs.extend(
            [
                cls._crumb(
                    LearningCatalogService.title_for(subject, locale),
                    "learning:subject",
                    subject_id=subject.id,
                ),
                cls._crumb(
                    LearningCatalogService.title_for(unit, locale),
                    "learning:unit",
                    unit_id=unit.id,
                ),
                cls._crumb(
                    LearningCatalogService.title_for(chapter, locale),
                    "learning:chapter",
                    chapter_id=chapter.id,
                ),
                cls._crumb(
                    LearningCatalogService.title_for(topic, locale),
                    "learning:topic",
                    topic_id=topic.id,
                ),
            ]
        )
        return cls._hierarchy_page(
            heading=LearningCatalogService.title_for(topic, locale),
            summary=LearningCatalogService.summary_for(topic, locale),
            node_kind="topic",
            child_label="Lessons",
            children=children,
            progress=progress,
            breadcrumbs=crumbs,
            scope_id=topic.id,
        )

    @classmethod
    def lesson_page(cls, user, lesson: Lesson) -> dict:
        locale = cls.locale_for(user)
        topic = lesson.topic
        chapter = topic.chapter
        unit = chapter.unit
        subject = unit.subject
        course = subject.course
        prev_lesson, next_lesson = LearningCatalogService.prev_next_lessons(lesson)
        completed = LearningProgressService.is_lesson_completed(user, lesson)

        materials = []
        for link in lesson.lessonlearningmaterial_set.all():
            material = link.learning_material
            decision = LearningAccessService.decide_material(
                user, material, via_lesson=lesson
            )
            item = {
                "id": material.id,
                "title": LearningCatalogService.title_for(material, locale),
                "is_premium": material.is_premium,
                "available": decision.allowed,
                "locked": decision.reason == "premium_required",
                "href": reverse(
                    "learning:material", kwargs={"material_id": material.id}
                )
                + f"?lesson={lesson.id}",
                "body": "",
            }
            if decision.allowed:
                item["body"] = LearningCatalogService.body_for(material, locale)
            elif decision.reason == "premium_required":
                item["lock_message"] = (
                    "Premium material. Upgrade your subscription to read this content."
                )
            else:
                continue
            materials.append(item)

        crumbs = cls._course_crumbs(locale, course)
        crumbs.extend(
            [
                cls._crumb(
                    LearningCatalogService.title_for(subject, locale),
                    "learning:subject",
                    subject_id=subject.id,
                ),
                cls._crumb(
                    LearningCatalogService.title_for(unit, locale),
                    "learning:unit",
                    unit_id=unit.id,
                ),
                cls._crumb(
                    LearningCatalogService.title_for(chapter, locale),
                    "learning:chapter",
                    chapter_id=chapter.id,
                ),
                cls._crumb(
                    LearningCatalogService.title_for(topic, locale),
                    "learning:topic",
                    topic_id=topic.id,
                ),
                cls._crumb(LearningCatalogService.title_for(lesson, locale)),
            ]
        )
        return {
            "page_heading": LearningCatalogService.title_for(lesson, locale),
            "body": LearningCatalogService.body_for(lesson, locale),
            "node_kind": "lesson",
            "is_completed": completed,
            "materials": materials,
            "materials_empty": len(materials) == 0,
            "prev_lesson": (
                {
                    "id": prev_lesson.id,
                    "title": LearningCatalogService.title_for(prev_lesson, locale),
                    "href": reverse(
                        "learning:lesson", kwargs={"lesson_id": prev_lesson.id}
                    ),
                }
                if prev_lesson
                else None
            ),
            "next_lesson": (
                {
                    "id": next_lesson.id,
                    "title": LearningCatalogService.title_for(next_lesson, locale),
                    "href": reverse(
                        "learning:lesson", kwargs={"lesson_id": next_lesson.id}
                    ),
                }
                if next_lesson
                else None
            ),
            "breadcrumbs": crumbs,
            "lesson_id": lesson.id,
        }

    @classmethod
    def progress_overview(cls, user) -> dict:
        locale = cls.locale_for(user)
        continue_learning = LearningProgressService.continue_learning_for(
            user, locale=locale
        )
        courses = []
        for course in LearningCatalogService.list_courses():
            progress = LearningProgressService.snapshot_for_course(user, course)
            courses.append(
                {
                    "id": course.id,
                    "title": LearningCatalogService.title_for(course, locale),
                    "href": reverse("learning:course", kwargs={"course_id": course.id}),
                    "progress": progress,
                }
            )
        return {
            "page_heading": "Learning progress",
            "continue_learning": continue_learning,
            "courses": courses,
            "is_empty": len(courses) == 0 and continue_learning.empty,
            "breadcrumbs": [
                cls._crumb("Learn", "learning:catalog"),
                cls._crumb("Progress", "learning:progress"),
            ],
        }

    @classmethod
    def material_page(
        cls, user, material: LearningMaterial, *, via_lesson: Lesson | None = None
    ) -> dict | None:
        locale = cls.locale_for(user)
        decision = LearningAccessService.decide_material(
            user, material, via_lesson=via_lesson
        )
        if LearningAccessService.hide_as_not_found(decision):
            return None
        title = LearningCatalogService.title_for(material, locale)
        crumbs = [cls._crumb("Learn", "learning:catalog")]
        if via_lesson is not None:
            crumbs.append(
                cls._crumb(
                    LearningCatalogService.title_for(via_lesson, locale),
                    "learning:lesson",
                    lesson_id=via_lesson.id,
                )
            )
        crumbs.append(cls._crumb(title))
        return {
            "page_heading": title,
            "is_premium": material.is_premium,
            "locked": decision.reason == "premium_required",
            "available": decision.allowed,
            "body": (
                LearningCatalogService.body_for(material, locale)
                if decision.allowed
                else ""
            ),
            "lock_message": (
                "Premium material. Upgrade your subscription to read this content."
                if decision.reason == "premium_required"
                else ""
            ),
            "breadcrumbs": crumbs,
            "via_lesson_id": via_lesson.id if via_lesson else None,
        }

    @classmethod
    def _practice_href(cls, scope_type: str, scope_id) -> str:
        return (
            reverse("assessment:setup")
            + f"?scope_type={scope_type}&scope_id={scope_id}"
        )

    @classmethod
    def _hierarchy_page(
        cls,
        *,
        heading: str,
        summary: str,
        node_kind: str,
        child_label: str,
        children: list[ChildItem],
        progress,
        breadcrumbs: list[BreadcrumbItem],
        scope_id=None,
    ) -> dict:
        data = {
            "page_heading": heading,
            "summary": summary,
            "node_kind": node_kind,
            "progress": progress,
            "children": children,
            "children_empty": len(children) == 0,
            "child_label": child_label,
            "breadcrumbs": breadcrumbs,
        }
        if scope_id is not None:
            data["practice_href"] = cls._practice_href(node_kind, scope_id)
        return data
