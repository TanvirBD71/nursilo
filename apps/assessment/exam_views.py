"""Thin exam views — ExamService owns rules (docs/04, docs/15, docs/24)."""
from __future__ import annotations

from django.contrib import messages
from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods, require_POST

from apps.assessment.forms import ExamAnswerForm, ExamStartForm, ExamSubmitForm
from apps.assessment.services import (
    ExamAccessService,
    ExamPresentationService,
    ExamService,
)
from apps.assessment.services.exceptions import (
    AssessmentError,
    AttemptAlreadySubmitted,
    AttemptForbidden,
    AttemptNotActive,
    AttemptNotFound,
    ExamNotEntitled,
    ExamPoolEmpty,
    ExamUnavailable,
    InvalidNavigation,
)
from apps.common.choices import AttemptState
from apps.portal.access import student_portal_required
from apps.portal.services import (
    NavigationService,
    NotificationPresentationService,
    SubscriptionPresentationService,
)


def _student_context(request, *, active: str = "exams", extra=None) -> dict:
    subscription = SubscriptionPresentationService.for_user(request.user)
    context = {
        "nav_items": NavigationService.items(active=active),
        "nav_active": active,
        "subscription_badge": subscription,
        "unread_notification_count": NotificationPresentationService.unread_count(
            request.user
        ),
        "layout_family": "student",
    }
    if extra:
        context.update(extra)
    return context


def _exam_layout_context(request, *, extra=None) -> dict:
    context = {
        "nav_items": [],
        "nav_active": "exams",
        "subscription_badge": SubscriptionPresentationService.for_user(request.user),
        "unread_notification_count": 0,
        "layout_family": "exam",
    }
    if extra:
        context.update(extra)
    return context


def _owned_attempt_or_404(request, attempt_id):
    try:
        return ExamService.require_owned_attempt(request.user, attempt_id)
    except (AttemptNotFound, AttemptForbidden) as exc:
        raise Http404("Not found.") from exc


def _catalog_exam_or_404(request, exam_id):
    exam = ExamService.get_catalog_exam(request.user, exam_id)
    if exam is None:
        raise Http404("Not found.")
    return exam


def _collect_truths(request):
    """Build a TRUE/FALSE statement map from posted ``truth_<key>`` fields."""
    truths = {}
    for name, value in request.POST.items():
        if name.startswith("truth_") and value not in (None, ""):
            key = name[len("truth_"):].strip().lower()
            if key:
                truths[key] = value
    return truths or None


@student_portal_required
@require_http_methods(["GET"])
def catalog(request):
    data = ExamPresentationService.catalog(request.user)
    return render(
        request,
        "assessment/exam_catalog.html",
        _student_context(request, extra=data),
    )


@student_portal_required
@require_http_methods(["GET"])
def detail(request, exam_id):
    exam = _catalog_exam_or_404(request, exam_id)
    data = ExamPresentationService.detail(request.user, exam)
    return render(
        request,
        "assessment/exam_detail.html",
        _student_context(request, extra=data),
    )


@student_portal_required
@require_http_methods(["GET", "POST"])
def start(request, exam_id):
    exam = _catalog_exam_or_404(request, exam_id)
    if request.method == "GET":
        data = ExamPresentationService.detail(request.user, exam)
        data["form"] = ExamStartForm()
        data["page_heading"] = f"Start — {data['title']}"
        return render(
            request,
            "assessment/exam_start.html",
            _student_context(request, extra=data),
        )

    form = ExamStartForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Could not confirm exam start.")
        return redirect("exams:detail", exam_id=exam_id)

    try:
        attempt = ExamService.start_or_resume(request.user, exam_id)
    except ExamNotEntitled as exc:
        messages.error(request, exc.message)
        return redirect("exams:detail", exam_id=exam_id)
    except ExamUnavailable as exc:
        messages.error(request, exc.message)
        return redirect("exams:catalog")
    except ExamPoolEmpty as exc:
        messages.error(request, exc.message)
        return redirect("exams:detail", exam_id=exam_id)
    except AttemptForbidden as exc:
        raise Http404("Not found.") from exc
    except AssessmentError as exc:
        messages.error(request, exc.message)
        return redirect("exams:detail", exam_id=exam_id)

    messages.success(request, "Exam session ready.")
    return redirect("exams:session", attempt_id=attempt.id, position=1)


@student_portal_required
@require_http_methods(["GET"])
def session(request, attempt_id, position: int):
    attempt = _owned_attempt_or_404(request, attempt_id)
    attempt = ExamService.enforce_timeout(request.user, attempt)
    if ExamAccessService.is_terminal(attempt):
        messages.info(request, "This exam attempt is complete.")
        return redirect("exams:result", attempt_id=attempt.id)
    if not ExamAccessService.is_active(attempt):
        raise Http404("Not found.")
    try:
        data = ExamPresentationService.session(request.user, attempt, position)
    except InvalidNavigation as exc:
        raise Http404("Not found.") from exc
    return render(
        request,
        "assessment/exam_session.html",
        _exam_layout_context(request, extra=data),
    )


@student_portal_required
@require_POST
def answer(request, attempt_id, position: int):
    form = ExamAnswerForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Invalid answer submission.")
        return redirect(
            "exams:session", attempt_id=attempt_id, position=position
        )
    truths = _collect_truths(request)
    result = ExamService.persist_answer(
        request.user,
        attempt_id,
        position=position,
        option_key=form.cleaned_data.get("option_key"),
        truths=truths,
    )
    if result.code in {"not_found", "forbidden"}:
        raise Http404("Not found.")
    if result.code == "already_submitted":
        messages.info(request, result.message)
        return redirect("exams:result", attempt_id=attempt_id)
    if not result.ok:
        messages.error(request, result.message)
    else:
        messages.success(request, result.message)

    go = (request.POST.get("nav") or "stay").strip().lower()
    if go == "next":
        nxt = position + 1
        try:
            ExamService.get_item(
                ExamService.require_owned_attempt(request.user, attempt_id), nxt
            )
            return redirect(
                "exams:session", attempt_id=attempt_id, position=nxt
            )
        except (InvalidNavigation, AttemptNotFound, AttemptForbidden):
            pass
    elif go == "prev" and position > 1:
        return redirect(
            "exams:session", attempt_id=attempt_id, position=position - 1
        )
    return redirect("exams:session", attempt_id=attempt_id, position=position)


@student_portal_required
@require_http_methods(["GET", "POST"])
def submit(request, attempt_id):
    attempt = _owned_attempt_or_404(request, attempt_id)
    attempt = ExamService.enforce_timeout(request.user, attempt)
    if request.method == "GET":
        if ExamAccessService.is_terminal(attempt):
            return redirect("exams:result", attempt_id=attempt.id)
        progress = ExamService.progress_counts(attempt)
        exam = attempt.exam_definition
        title = ExamPresentationService.exam_title(exam) if exam else "Exam"
        return render(
            request,
            "assessment/exam_submit_confirm.html",
            _student_context(
                request,
                extra={
                    "page_heading": "Submit exam",
                    "attempt_id": attempt.id,
                    "progress": progress,
                    "exam_title": title,
                    "form": ExamSubmitForm(),
                    "session_href": reverse(
                        "exams:session",
                        kwargs={"attempt_id": attempt.id, "position": 1},
                    ),
                },
            ),
        )

    form = ExamSubmitForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Submission could not be confirmed.")
        return redirect("exams:submit", attempt_id=attempt_id)
    try:
        result = ExamService.submit(request.user, attempt_id)
    except AttemptNotFound as exc:
        raise Http404("Not found.") from exc
    except AttemptForbidden as exc:
        raise Http404("Not found.") from exc
    except AttemptAlreadySubmitted:
        messages.info(request, "This exam attempt was already submitted.")
        return redirect("exams:result", attempt_id=attempt_id)
    except AttemptNotActive as exc:
        messages.error(request, exc.message)
        return redirect("exams:catalog")
    except AssessmentError as exc:
        messages.error(request, exc.message)
        return redirect("exams:session", attempt_id=attempt_id, position=1)

    if result.already_submitted:
        messages.info(request, "Showing your saved exam result.")
    else:
        messages.success(request, "Exam submitted. Results are ready.")
    return redirect("exams:result", attempt_id=attempt_id)


@student_portal_required
@require_http_methods(["GET"])
def result(request, attempt_id):
    attempt = _owned_attempt_or_404(request, attempt_id)
    attempt = ExamService.enforce_timeout(request.user, attempt)
    if attempt.state != AttemptState.COMPLETED:
        if ExamAccessService.is_active(attempt):
            return redirect(
                "exams:session", attempt_id=attempt.id, position=1
            )
        if attempt.state == AttemptState.SUBMITTED:
            ExamService.submit(request.user, attempt_id)
            attempt = _owned_attempt_or_404(request, attempt_id)
        else:
            raise Http404("Not found.")
    data = ExamPresentationService.result(request.user, attempt)
    return render(
        request,
        "assessment/exam_result.html",
        _student_context(request, extra=data),
    )


@student_portal_required
@require_http_methods(["GET"])
def review(request, attempt_id):
    attempt = _owned_attempt_or_404(request, attempt_id)
    if not ExamAccessService.may_reveal_answer_key(attempt):
        if ExamAccessService.is_active(attempt):
            messages.info(
                request, "Finish and submit the exam before reviewing answers."
            )
            return redirect(
                "exams:session", attempt_id=attempt.id, position=1
            )
        return redirect("exams:result", attempt_id=attempt.id)
    data = ExamPresentationService.review(request.user, attempt)
    return render(
        request,
        "assessment/exam_review.html",
        _student_context(request, extra=data),
    )


@student_portal_required
@require_http_methods(["GET"])
def history(request):
    try:
        page = int(request.GET.get("page") or "1")
    except ValueError:
        page = 1
    data = ExamPresentationService.history(request.user, page=page)
    return render(
        request,
        "assessment/exam_history.html",
        _student_context(request, extra=data),
    )
