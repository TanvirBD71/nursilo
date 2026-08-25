"""
Practice presentation assembly — server-prepared view models only (docs/15–16, docs/24).

Active attempts never include correct-answer keys, explanations, or is_correct flags.
"""
from __future__ import annotations

from dataclasses import dataclass

from django.urls import reverse

from apps.assessment.models import Attempt, AttemptItem
from apps.assessment.services.access import PracticeAccessService
from apps.assessment.services.pool import ALLOWED_DIFFICULTIES, DEFAULT_QUESTION_COUNT
from apps.assessment.services.practice import PracticeService
from apps.assessment.services.scoring import (
    correct_keys_for_version,
    correct_truths_for_version,
    is_true_false_spec,
    selected_key,
    selected_truths,
)
from apps.common.choices import AttemptState, DifficultyLevel, QuestionType
from apps.learning.models import Chapter, Course, Subject, Topic, Unit


@dataclass(frozen=True)
class OptionView:
    key: str
    label: str
    selected: bool
    # Review-only fields — always False/empty during active attempts.
    is_correct: bool = False
    show_correctness: bool = False


class PracticePresentationService:
    @classmethod
    def _catalog(cls):
        from apps.learning.services.catalog import LearningCatalogService

        return LearningCatalogService

    @classmethod
    def locale_for(cls, user) -> str:
        return getattr(user, "ui_locale", None) or "en"

    @classmethod
    def scope_label(cls, attempt: Attempt, locale: str) -> str:
        st = attempt.scope_type or "practice"
        if st == "random":
            return "Random practice"
        if not attempt.scope_id:
            return st.replace("_", " ").title()
        model = {
            "course": Course,
            "subject": Subject,
            "unit": Unit,
            "chapter": Chapter,
            "topic": Topic,
        }.get(st)
        if model is None:
            return st.title()
        node = model.objects.filter(pk=attempt.scope_id).first()
        if node is None:
            return st.title()
        title = cls._catalog().title_for(node, locale)
        return f"{st.title()}: {title}"

    @classmethod
    def entry(cls, user) -> dict:
        locale = cls.locale_for(user)
        in_progress = PracticeService.in_progress_for_user(user)
        resume_items = [
            {
                "id": a.id,
                "scope_label": cls.scope_label(a, locale),
                "href": reverse(
                    "assessment:session",
                    kwargs={"attempt_id": a.id, "position": 1},
                ),
                "started_at": a.started_at,
                "progress": PracticeService.progress_counts(a),
            }
            for a in in_progress
        ]
        return {
            "page_heading": "Practice",
            "tagline": "Build exam readiness with focused practice.",
            "setup_href": reverse("assessment:setup"),
            "history_href": reverse("assessment:history"),
            "resume_items": resume_items,
            "has_resume": bool(resume_items),
        }

    @classmethod
    def setup_context(cls, user, *, form=None, prefills: dict | None = None) -> dict:
        locale = cls.locale_for(user)
        prefills = prefills or {}
        catalog = cls._catalog()
        courses = list(catalog.list_courses())
        course_choices = [
            {
                "id": c.id,
                "title": catalog.title_for(c, locale),
            }
            for c in courses
        ]
        # Hierarchy picks for setup — published nodes only via catalog service.
        subjects = []
        units = []
        chapters = []
        topics = []
        for course in courses:
            for subject in catalog.published_children(course, Subject, "course"):
                subjects.append(
                    {
                        "id": subject.id,
                        "title": catalog.title_for(subject, locale),
                        "course_id": course.id,
                    }
                )
                for unit in catalog.published_children(subject, Unit, "subject"):
                    units.append(
                        {
                            "id": unit.id,
                            "title": catalog.title_for(unit, locale),
                            "subject_id": subject.id,
                        }
                    )
                    for chapter in catalog.published_children(unit, Chapter, "unit"):
                        chapters.append(
                            {
                                "id": chapter.id,
                                "title": catalog.title_for(chapter, locale),
                                "unit_id": unit.id,
                            }
                        )
                        for topic in catalog.published_children(chapter, Topic, "chapter"):
                            topics.append(
                                {
                                    "id": topic.id,
                                    "title": catalog.title_for(topic, locale),
                                    "chapter_id": chapter.id,
                                }
                            )

        difficulties = [
            {"value": d.value, "label": d.label}
            for d in DifficultyLevel
            if d.value in ALLOWED_DIFFICULTIES
        ]
        return {
            "page_heading": "Practice setup",
            "form": form,
            "course_choices": course_choices,
            "subject_choices": subjects,
            "unit_choices": units,
            "chapter_choices": chapters,
            "topic_choices": topics,
            "difficulty_choices": difficulties,
            "default_count": DEFAULT_QUESTION_COUNT,
            "prefills": prefills,
            "entry_href": reverse("assessment:entry"),
        }

    @classmethod
    def _stem_and_explanation(cls, item: AttemptItem, locale: str) -> tuple[str, str]:
        translations = {t.locale: t for t in item.question_version.translations.all()}
        tr = translations.get(locale) or translations.get("en") or translations.get("bn")
        if tr is None and translations:
            tr = next(iter(translations.values()))
        if tr is None:
            return ("", "")
        return (tr.stem, tr.explanation or "")

    @classmethod
    def _option_label(cls, option, locale: str) -> str:
        translations = {t.locale: t for t in option.translations.all()}
        tr = translations.get(locale) or translations.get("en") or translations.get("bn")
        if tr is None and translations:
            tr = next(iter(translations.values()))
        return tr.label if tr else option.key

    @classmethod
    def options_for_item(
        cls, item: AttemptItem, locale: str, *, reveal: bool
    ) -> list[OptionView]:
        selected = selected_key(item.selected_answer)
        correct_keys = correct_keys_for_version(item.question_version) if reveal else set()
        options = sorted(item.question_version.options.all(), key=lambda o: o.sort_order)
        views = []
        for opt in options:
            is_correct = opt.key in correct_keys if reveal else False
            views.append(
                OptionView(
                    key=opt.key,
                    label=cls._option_label(opt, locale),
                    selected=selected == opt.key,
                    is_correct=is_correct,
                    show_correctness=reveal,
                )
            )
        return views

    @classmethod
    def true_false_statements(cls, item: AttemptItem, locale: str, *, reveal: bool) -> list[dict]:
        """
        Per-statement view for a TRUE/FALSE item. Correct truths only when reveal
        (post-completion). Active sessions never receive the answer key.
        """
        correct = correct_truths_for_version(item.question_version) if reveal else {}
        selected = selected_truths(item.selected_answer)
        options = sorted(item.question_version.options.all(), key=lambda o: o.sort_order)
        rows = []
        for opt in options:
            key = opt.key.lower()
            sel = selected.get(key)
            cor = correct.get(key) if reveal else None
            rows.append(
                {
                    "key": opt.key,
                    "text": cls._option_label(opt, locale),
                    "selected": sel,
                    "correct": cor,
                    "is_correct": bool(reveal and sel is not None and sel == cor),
                    "show_correctness": reveal,
                }
            )
        return rows

    @classmethod
    def session(cls, user, attempt: Attempt, position: int) -> dict:
        locale = cls.locale_for(user)
        item = PracticeService.get_item(attempt, position)
        reveal = False  # never during active session
        stem, _explanation = cls._stem_and_explanation(item, locale)
        is_true_false = is_true_false_spec(item.question_version.correct_answer_spec)
        options = cls.options_for_item(item, locale, reveal=reveal)
        statements = (
            cls.true_false_statements(item, locale, reveal=False)
            if is_true_false
            else []
        )
        progress = PracticeService.progress_counts(attempt)
        positions = list(
            attempt.items.order_by("position").values_list("position", flat=True)
        )
        answered_positions = set(
            attempt.items.exclude(selected_answer=None).values_list("position", flat=True)
        )
        nav = [
            {
                "position": p,
                "answered": p in answered_positions,
                "current": p == item.position,
                "href": reverse(
                    "assessment:session",
                    kwargs={"attempt_id": attempt.id, "position": p},
                ),
            }
            for p in positions
        ]
        prev_pos = item.position - 1 if item.position > 1 else None
        next_pos = item.position + 1 if item.position < progress["total"] else None
        clinical = item.question_version.clinical_scenario_body or ""
        return {
            "page_heading": "Practice session",
            "layout_family": "practice",
            "attempt_id": attempt.id,
            "scope_label": cls.scope_label(attempt, locale),
            "position": item.position,
            "total": progress["total"],
            "answered": progress["answered"],
            "stem": stem,
            "clinical_scenario_body": clinical,
            "options": options,
            "is_true_false": is_true_false,
            "statements": statements,
            "question_type": item.question.question_type,
            "selected_key": selected_key(item.selected_answer),
            "navigator": nav,
            "prev_href": (
                reverse(
                    "assessment:session",
                    kwargs={"attempt_id": attempt.id, "position": prev_pos},
                )
                if prev_pos
                else None
            ),
            "next_href": (
                reverse(
                    "assessment:session",
                    kwargs={"attempt_id": attempt.id, "position": next_pos},
                )
                if next_pos
                else None
            ),
            "submit_href": reverse(
                "assessment:submit", kwargs={"attempt_id": attempt.id}
            ),
            "answer_href": reverse(
                "assessment:answer",
                kwargs={"attempt_id": attempt.id, "position": item.position},
            ),
            # Explicitly omit explanation / correctness for active attempts.
            "reveal_answers": False,
            "explanation": "",
        }

    @classmethod
    def result(cls, user, attempt: Attempt) -> dict:
        locale = cls.locale_for(user)
        summary = dict(attempt.score_summary or {})
        return {
            "page_heading": "Practice result",
            "attempt_id": attempt.id,
            "scope_label": cls.scope_label(attempt, locale),
            "state": attempt.state,
            "completed_at": attempt.completed_at,
            "score_summary": summary,
            "review_href": reverse(
                "assessment:review", kwargs={"attempt_id": attempt.id}
            ),
            "history_href": reverse("assessment:history"),
            "setup_href": reverse("assessment:setup"),
            "entry_href": reverse("assessment:entry"),
        }

    @classmethod
    def review(cls, user, attempt: Attempt) -> dict:
        locale = cls.locale_for(user)
        if not PracticeAccessService.may_reveal_answer_key(attempt):
            # Caller should redirect; provide empty safe payload.
            return {
                "page_heading": "Practice review",
                "reveal_answers": False,
                "items": [],
                "attempt_id": attempt.id,
            }
        items_qs = (
            attempt.items.select_related("question", "question_version")
            .prefetch_related(
                "question_version__options",
                "question_version__options__translations",
                "question_version__translations",
            )
            .order_by("position")
        )
        items = []
        for item in items_qs:
            stem, explanation = cls._stem_and_explanation(item, locale)
            is_true_false = is_true_false_spec(item.question_version.correct_answer_spec)
            options = [] if is_true_false else cls.options_for_item(item, locale, reveal=True)
            statements = (
                cls.true_false_statements(item, locale, reveal=True)
                if is_true_false
                else []
            )
            sel = selected_key(item.selected_answer)
            points = item.score if item.score is not None else (
                1.0 if item.is_correct is True else 0.0
            )
            if item.is_correct is True:
                outcome = "correct"
                outcome_label = "Correct"
            elif item.is_correct is False:
                # A partly-correct True/False item earns marks but is not full.
                if is_true_false and points > 0:
                    outcome = "partial"
                    outcome_label = "Partially correct"
                else:
                    outcome = "incorrect"
                    outcome_label = "Incorrect"
            else:
                outcome = "unanswered"
                outcome_label = "Unanswered"
            items.append(
                {
                    "position": item.position,
                    "stem": stem,
                    "clinical_scenario_body": item.question_version.clinical_scenario_body
                    or "",
                    "options": options,
                    "is_true_false": is_true_false,
                    "statements": statements,
                    "question_type": item.question.question_type,
                    "selected_key": sel,
                    "explanation": explanation,
                    "outcome": outcome,
                    "outcome_label": outcome_label,
                    "is_correct": item.is_correct,
                    "points": round(points, 2),
                    "max_points": 1.0,
                }
            )
        return {
            "page_heading": "Practice review",
            "attempt_id": attempt.id,
            "scope_label": cls.scope_label(attempt, locale),
            "score_summary": dict(attempt.score_summary or {}),
            "items": items,
            "reveal_answers": True,
            "result_href": reverse(
                "assessment:result", kwargs={"attempt_id": attempt.id}
            ),
            "history_href": reverse("assessment:history"),
        }

    @classmethod
    def history(cls, user, *, page: int = 1) -> dict:
        locale = cls.locale_for(user)
        rows, total = PracticeService.history_for_user(user, page=page, page_size=20)
        page_size = 20
        total_pages = max(1, (total + page_size - 1) // page_size) if total else 1
        page = min(max(1, page), total_pages)
        items = []
        for a in rows:
            summary = dict(a.score_summary or {})
            if a.state == AttemptState.IN_PROGRESS:
                href = reverse(
                    "assessment:session",
                    kwargs={"attempt_id": a.id, "position": 1},
                )
            elif a.state == AttemptState.COMPLETED:
                href = reverse("assessment:result", kwargs={"attempt_id": a.id})
            else:
                href = reverse("assessment:result", kwargs={"attempt_id": a.id})
            items.append(
                {
                    "id": a.id,
                    "scope_label": cls.scope_label(a, locale),
                    "state": a.state,
                    "started_at": a.started_at,
                    "completed_at": a.completed_at,
                    "score_summary": summary,
                    "href": href,
                }
            )
        return {
            "page_heading": "Practice history",
            "items": items,
            "is_empty": len(items) == 0,
            "page": page,
            "total": total,
            "total_pages": total_pages,
            "has_prev": page > 1,
            "has_next": page < total_pages,
            "prev_href": reverse("assessment:history") + f"?page={page - 1}"
            if page > 1
            else None,
            "next_href": reverse("assessment:history") + f"?page={page + 1}"
            if page < total_pages
            else None,
            "entry_href": reverse("assessment:entry"),
            "setup_href": reverse("assessment:setup"),
        }
