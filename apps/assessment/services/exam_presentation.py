"""
Exam presentation assembly — server-prepared view models (docs/15–16, docs/24).

Active exams never include correct-answer keys, explanations, or is_correct flags.
Timer values are server snapshots for display only.
"""
from __future__ import annotations

from django.urls import reverse

from apps.assessment.models import Attempt, ExamDefinition
from apps.assessment.services.access import ExamAccessService
from apps.assessment.services.exam import (
    STATE_AVAILABLE,
    STATE_COMPLETED,
    STATE_IN_PROGRESS,
    STATE_LOCKED,
    STATE_UNAVAILABLE,
    ExamService,
)
from apps.assessment.services.presentation import PracticePresentationService
from apps.assessment.services.scoring import is_true_false_spec, selected_key
from apps.common.choices import AttemptState


STATE_LABELS = {
    STATE_AVAILABLE: "Available",
    STATE_LOCKED: "Locked — Premium required",
    STATE_IN_PROGRESS: "In progress",
    STATE_COMPLETED: "Completed",
    STATE_UNAVAILABLE: "Unavailable",
}


class ExamPresentationService:
    @classmethod
    def locale_for(cls, user) -> str:
        return PracticePresentationService.locale_for(user)

    @classmethod
    def exam_title(cls, exam: ExamDefinition) -> str:
        key = (exam.title_key or exam.code or "Exam").strip()
        return key.replace("_", " ").replace("-", " ").title()

    @classmethod
    def mode_label(cls, mode: str) -> str:
        return (mode or "exam").replace("_", " ").title()

    @classmethod
    def catalog(cls, user) -> dict:
        exams = ExamService.list_catalog(user)
        items = []
        for exam in exams:
            elig = ExamService.eligibility(user, exam)
            items.append(
                {
                    "id": exam.id,
                    "title": cls.exam_title(exam),
                    "mode": exam.mode,
                    "mode_label": cls.mode_label(exam.mode),
                    "state": elig.state,
                    "state_label": STATE_LABELS.get(elig.state, elig.state),
                    "requires_premium": elig.requires_premium,
                    "is_timed": exam.time_limit_seconds is not None,
                    "time_limit_seconds": exam.time_limit_seconds,
                    "question_count": elig.question_count,
                    "track_code": exam.track_code or "",
                    "href": reverse("exams:detail", kwargs={"exam_id": exam.id}),
                }
            )
        return {
            "page_heading": "Exams",
            "tagline": "Timed and structured exams with server-confirmed results.",
            "items": items,
            "is_empty": len(items) == 0,
            "history_href": reverse("exams:history"),
        }

    @classmethod
    def detail(cls, user, exam: ExamDefinition) -> dict:
        elig = ExamService.eligibility(user, exam)
        resume_href = None
        if elig.in_progress_attempt is not None:
            resume_href = reverse(
                "exams:session",
                kwargs={
                    "attempt_id": elig.in_progress_attempt.id,
                    "position": 1,
                },
            )
        timer = None
        if elig.in_progress_attempt is not None:
            snap = ExamService.timer_for(elig.in_progress_attempt)
            timer = {
                "is_timed": snap.is_timed,
                "remaining_seconds": snap.remaining_seconds,
            }
        return {
            "page_heading": cls.exam_title(exam),
            "exam_id": exam.id,
            "title": cls.exam_title(exam),
            "mode_label": cls.mode_label(exam.mode),
            "state": elig.state,
            "state_label": STATE_LABELS.get(elig.state, elig.state),
            "message": elig.message,
            "requires_premium": elig.requires_premium,
            "entitled": elig.entitled,
            "can_start": elig.can_start,
            "can_resume": elig.can_resume,
            "completed_count": elig.completed_count,
            "question_count": elig.question_count,
            "is_timed": exam.time_limit_seconds is not None,
            "time_limit_seconds": exam.time_limit_seconds,
            "track_code": exam.track_code or "",
            "start_href": reverse("exams:start", kwargs={"exam_id": exam.id}),
            "resume_href": resume_href,
            "timer": timer,
            "catalog_href": reverse("exams:catalog"),
            "history_href": reverse("exams:history"),
        }

    @classmethod
    def session(cls, user, attempt: Attempt, position: int) -> dict:
        locale = cls.locale_for(user)
        item = ExamService.get_item(attempt, position)
        stem, _explanation = PracticePresentationService._stem_and_explanation(
            item, locale
        )
        options = PracticePresentationService.options_for_item(
            item, locale, reveal=False
        )
        is_true_false = is_true_false_spec(item.question_version.correct_answer_spec)
        statements = (
            PracticePresentationService.true_false_statements(item, locale, reveal=False)
            if is_true_false
            else []
        )
        progress = ExamService.progress_counts(attempt)
        positions = list(
            attempt.items.order_by("position").values_list("position", flat=True)
        )
        answered_positions = set(
            attempt.items.exclude(selected_answer=None).values_list(
                "position", flat=True
            )
        )
        nav = [
            {
                "position": p,
                "answered": p in answered_positions,
                "current": p == item.position,
                "href": reverse(
                    "exams:session",
                    kwargs={"attempt_id": attempt.id, "position": p},
                ),
            }
            for p in positions
        ]
        prev_pos = item.position - 1 if item.position > 1 else None
        next_pos = item.position + 1 if item.position < progress["total"] else None
        snap = ExamService.timer_for(attempt)
        exam = attempt.exam_definition
        title = cls.exam_title(exam) if exam else "Exam"
        expires_iso = ""
        if snap.expires_at is not None:
            expires_iso = snap.expires_at.isoformat()
        return {
            "page_heading": "Exam session",
            "layout_family": "exam",
            "attempt_id": attempt.id,
            "exam_title": title,
            "position": item.position,
            "total": progress["total"],
            "answered": progress["answered"],
            "stem": stem,
            "clinical_scenario_body": item.question_version.clinical_scenario_body
            or "",
            "options": options,
            "is_true_false": is_true_false,
            "statements": statements,
            "question_type": item.question.question_type,
            "selected_key": selected_key(item.selected_answer),
            "navigator": nav,
            "prev_href": (
                reverse(
                    "exams:session",
                    kwargs={"attempt_id": attempt.id, "position": prev_pos},
                )
                if prev_pos
                else None
            ),
            "next_href": (
                reverse(
                    "exams:session",
                    kwargs={"attempt_id": attempt.id, "position": next_pos},
                )
                if next_pos
                else None
            ),
            "submit_href": reverse(
                "exams:submit", kwargs={"attempt_id": attempt.id}
            ),
            "answer_href": reverse(
                "exams:answer",
                kwargs={"attempt_id": attempt.id, "position": item.position},
            ),
            "reveal_answers": False,
            "explanation": "",
            "timer_is_timed": snap.is_timed,
            "timer_remaining_seconds": snap.remaining_seconds
            if snap.remaining_seconds is not None
            else None,
            "timer_expires_at": expires_iso,
            "timer_sync_href": reverse(
                "exams:session",
                kwargs={"attempt_id": attempt.id, "position": item.position},
            ),
        }

    @classmethod
    def result(cls, user, attempt: Attempt) -> dict:
        exam = attempt.exam_definition
        title = cls.exam_title(exam) if exam else "Exam"
        summary = dict(attempt.score_summary or {})
        return {
            "page_heading": "Exam result",
            "attempt_id": attempt.id,
            "exam_title": title,
            "state": attempt.state,
            "completed_at": attempt.completed_at,
            "score_summary": summary,
            "review_href": reverse(
                "exams:review", kwargs={"attempt_id": attempt.id}
            ),
            "history_href": reverse("exams:history"),
            "catalog_href": reverse("exams:catalog"),
            "detail_href": (
                reverse("exams:detail", kwargs={"exam_id": exam.id})
                if exam
                else reverse("exams:catalog")
            ),
        }

    @classmethod
    def review(cls, user, attempt: Attempt) -> dict:
        if not ExamAccessService.may_reveal_answer_key(attempt):
            return {
                "page_heading": "Exam review",
                "reveal_answers": False,
                "items": [],
                "attempt_id": attempt.id,
            }
        # Reuse practice review item assembly for identical scoring disclosure rules.
        base = PracticePresentationService.review(user, attempt)
        exam = attempt.exam_definition
        title = cls.exam_title(exam) if exam else "Exam"
        base["page_heading"] = "Exam review"
        base["exam_title"] = title
        base["result_href"] = reverse(
            "exams:result", kwargs={"attempt_id": attempt.id}
        )
        base["history_href"] = reverse("exams:history")
        base["scope_label"] = title
        return base

    @classmethod
    def history(cls, user, *, page: int = 1) -> dict:
        rows, total = ExamService.history_for_user(user, page=page, page_size=20)
        page_size = 20
        total_pages = max(1, (total + page_size - 1) // page_size) if total else 1
        page = min(max(1, page), total_pages)
        items = []
        for a in rows:
            summary = dict(a.score_summary or {})
            exam = a.exam_definition
            title = cls.exam_title(exam) if exam else "Exam"
            if a.state == AttemptState.IN_PROGRESS:
                href = reverse(
                    "exams:session",
                    kwargs={"attempt_id": a.id, "position": 1},
                )
            else:
                href = reverse("exams:result", kwargs={"attempt_id": a.id})
            items.append(
                {
                    "id": a.id,
                    "title": title,
                    "state": a.state,
                    "started_at": a.started_at,
                    "completed_at": a.completed_at,
                    "score_summary": summary,
                    "href": href,
                }
            )
        return {
            "page_heading": "Exam history",
            "items": items,
            "is_empty": len(items) == 0,
            "page": page,
            "total": total,
            "total_pages": total_pages,
            "has_prev": page > 1,
            "has_next": page < total_pages,
            "prev_href": reverse("exams:history") + f"?page={page - 1}"
            if page > 1
            else None,
            "next_href": reverse("exams:history") + f"?page={page + 1}"
            if page < total_pages
            else None,
            "catalog_href": reverse("exams:catalog"),
        }
