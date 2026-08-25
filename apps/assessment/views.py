"""Thin practice views — services own rules (docs/04, docs/15, docs/24)."""
from __future__ import annotations

from django.contrib import messages
from django.http import Http404
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods, require_POST

from apps.assessment.forms import PracticeAnswerForm, PracticeSetupForm, PracticeSubmitForm
from apps.assessment.services import (
    PracticeAccessService,
    PracticePresentationService,
    PracticeService,
)
from apps.assessment.services.exceptions import (
    AssessmentError,
    AttemptAlreadySubmitted,
    AttemptForbidden,
    AttemptNotActive,
    AttemptNotFound,
    InvalidNavigation,
    PracticeCapExceeded,
    PracticePoolEmpty,
    PracticeSetupError,
    PracticeUnavailable,
)
from apps.common.choices import AttemptState
from apps.portal.access import student_portal_required
from apps.portal.services import (
    NavigationService,
    NotificationPresentationService,
    SubscriptionPresentationService,
)


def _student_context(request, *, active: str = "practice", extra=None) -> dict:
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


def _practice_layout_context(request, *, extra=None) -> dict:
    """Reduced-chrome assessment session shell (docs/15–16)."""
    context = {
        "nav_items": [],
        "nav_active": "practice",
        "subscription_badge": SubscriptionPresentationService.for_user(request.user),
        "unread_notification_count": 0,
        "layout_family": "practice",
    }
    if extra:
        context.update(extra)
    return context


def _owned_attempt_or_404(request, attempt_id):
    try:
        return PracticeService.require_owned_attempt(request.user, attempt_id)
    except (AttemptNotFound, AttemptForbidden) as exc:
        raise Http404("Not found.") from exc


def _collect_truths(request):
    """
    Build a TRUE/FALSE statement map from posted ``truth_<key>`` fields.

    Returns None when no True/False fields are present so single-answer items
    keep their existing option_key path.
    """
    truths = {}
    for name, value in request.POST.items():
        if name.startswith("truth_") and value not in (None, ""):
            key = name[len("truth_"):].strip().lower()
            if key:
                truths[key] = value
    return truths or None


@student_portal_required
@require_http_methods(["GET"])
def entry(request):
    data = PracticePresentationService.entry(request.user)
    return render(
        request,
        "assessment/entry.html",
        _student_context(request, extra=data),
    )


@student_portal_required
@require_http_methods(["GET", "POST"])
def setup(request):
    prefills = {
        "scope_type": request.GET.get("scope_type", "topic"),
        "scope_id": request.GET.get("scope_id") or "",
        "difficulty": request.GET.get("difficulty", ""),
        "count": request.GET.get("count") or "",
    }
    if request.method == "POST":
        form = PracticeSetupForm(request.POST)
        if form.is_valid():
            try:
                attempt = PracticeService.start_practice(
                    request.user,
                    scope_type=form.cleaned_data["scope_type"],
                    scope_id=form.cleaned_data.get("scope_id"),
                    difficulty=form.cleaned_data.get("difficulty") or None,
                    count=form.cleaned_data.get("count"),
                )
            except PracticeSetupError as exc:
                messages.error(request, exc.message)
            except PracticeUnavailable as exc:
                messages.error(request, exc.message)
            except PracticePoolEmpty as exc:
                messages.error(request, exc.message)
            except PracticeCapExceeded as exc:
                messages.error(request, exc.message)
            except AttemptForbidden as exc:
                raise Http404("Not found.") from exc
            except AssessmentError as exc:
                messages.error(request, exc.message)
            else:
                messages.success(request, "Practice session started.")
                return redirect(
                    "assessment:session",
                    attempt_id=attempt.id,
                    position=1,
                )
        else:
            messages.error(request, "Please correct the practice setup and try again.")
    else:
        initial = {
            "scope_type": prefills["scope_type"] or "topic",
            "count": int(prefills["count"]) if str(prefills["count"]).isdigit() else 10,
        }
        if prefills["scope_id"]:
            initial["scope_id"] = prefills["scope_id"]
        if prefills["difficulty"]:
            initial["difficulty"] = prefills["difficulty"]
        form = PracticeSetupForm(initial=initial)

    data = PracticePresentationService.setup_context(
        request.user, form=form, prefills=prefills
    )
    return render(
        request,
        "assessment/setup.html",
        _student_context(request, extra=data),
    )


@student_portal_required
@require_http_methods(["GET"])
def session(request, attempt_id, position: int):
    attempt = _owned_attempt_or_404(request, attempt_id)
    if PracticeAccessService.is_terminal(attempt):
        return redirect("assessment:result", attempt_id=attempt.id)
    if not PracticeAccessService.is_active(attempt):
        raise Http404("Not found.")
    try:
        data = PracticePresentationService.session(request.user, attempt, position)
    except InvalidNavigation as exc:
        raise Http404("Not found.") from exc
    return render(
        request,
        "assessment/session.html",
        _practice_layout_context(request, extra=data),
    )


@student_portal_required
@require_POST
def answer(request, attempt_id, position: int):
    form = PracticeAnswerForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Invalid answer submission.")
        return redirect(
            "assessment:session", attempt_id=attempt_id, position=position
        )
    truths = _collect_truths(request)
    result = PracticeService.persist_answer(
        request.user,
        attempt_id,
        position=position,
        option_key=form.cleaned_data.get("option_key"),
        truths=truths,
    )
    if result.code == "not_found":
        raise Http404("Not found.")
    if result.code == "forbidden":
        raise Http404("Not found.")
    if result.code == "already_submitted":
        messages.info(request, result.message)
        return redirect("assessment:result", attempt_id=attempt_id)
    if not result.ok:
        messages.error(request, result.message)
    else:
        messages.success(request, result.message)

    # Navigate: prefer explicit next action from form, else stay on question.
    go = (request.POST.get("nav") or "stay").strip().lower()
    if go == "next":
        nxt = position + 1
        try:
            PracticeService.get_item(
                PracticeService.require_owned_attempt(request.user, attempt_id), nxt
            )
            return redirect(
                "assessment:session", attempt_id=attempt_id, position=nxt
            )
        except (InvalidNavigation, AttemptNotFound, AttemptForbidden):
            pass
    elif go == "prev" and position > 1:
        return redirect(
            "assessment:session", attempt_id=attempt_id, position=position - 1
        )
    return redirect("assessment:session", attempt_id=attempt_id, position=position)


@student_portal_required
@require_http_methods(["GET", "POST"])
def submit(request, attempt_id):
    attempt = _owned_attempt_or_404(request, attempt_id)
    if request.method == "GET":
        if PracticeAccessService.is_terminal(attempt):
            return redirect("assessment:result", attempt_id=attempt.id)
        progress = PracticeService.progress_counts(attempt)
        return render(
            request,
            "assessment/submit_confirm.html",
            _student_context(
                request,
                extra={
                    "page_heading": "Submit practice",
                    "attempt_id": attempt.id,
                    "progress": progress,
                    "scope_label": PracticePresentationService.scope_label(
                        attempt, PracticePresentationService.locale_for(request.user)
                    ),
                    "form": PracticeSubmitForm(),
                    "session_href": reverse_session(attempt.id, 1),
                },
            ),
        )

    form = PracticeSubmitForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Submission could not be confirmed.")
        return redirect("assessment:submit", attempt_id=attempt_id)
    try:
        result = PracticeService.submit(request.user, attempt_id)
    except AttemptNotFound as exc:
        raise Http404("Not found.") from exc
    except AttemptForbidden as exc:
        raise Http404("Not found.") from exc
    except AttemptAlreadySubmitted:
        messages.info(request, "This practice attempt was already submitted.")
        return redirect("assessment:result", attempt_id=attempt_id)
    except AttemptNotActive as exc:
        messages.error(request, exc.message)
        return redirect("assessment:entry")
    except AssessmentError as exc:
        messages.error(request, exc.message)
        return redirect("assessment:session", attempt_id=attempt_id, position=1)

    if result.already_submitted:
        messages.info(request, "Showing your saved practice result.")
    else:
        messages.success(request, "Practice submitted. Results are ready.")
    return redirect("assessment:result", attempt_id=attempt_id)


def reverse_session(attempt_id, position: int) -> str:
    from django.urls import reverse

    return reverse(
        "assessment:session",
        kwargs={"attempt_id": attempt_id, "position": position},
    )


@student_portal_required
@require_http_methods(["GET"])
def result(request, attempt_id):
    attempt = _owned_attempt_or_404(request, attempt_id)
    if attempt.state != AttemptState.COMPLETED:
        if PracticeAccessService.is_active(attempt):
            return redirect(
                "assessment:session", attempt_id=attempt.id, position=1
            )
        # Submitted-but-not-completed edge: try finalize via submit path
        if attempt.state == AttemptState.SUBMITTED:
            PracticeService.submit(request.user, attempt_id)
            attempt = _owned_attempt_or_404(request, attempt_id)
        else:
            raise Http404("Not found.")
    data = PracticePresentationService.result(request.user, attempt)
    return render(
        request,
        "assessment/result.html",
        _student_context(request, extra=data),
    )


@student_portal_required
@require_http_methods(["GET"])
def review(request, attempt_id):
    attempt = _owned_attempt_or_404(request, attempt_id)
    if not PracticeAccessService.may_reveal_answer_key(attempt):
        if PracticeAccessService.is_active(attempt):
            messages.info(request, "Finish and submit practice before reviewing answers.")
            return redirect(
                "assessment:session", attempt_id=attempt.id, position=1
            )
        return redirect("assessment:result", attempt_id=attempt.id)
    data = PracticePresentationService.review(request.user, attempt)
    return render(
        request,
        "assessment/review.html",
        _student_context(request, extra=data),
    )


@student_portal_required
@require_http_methods(["GET"])
def history(request):
    try:
        page = int(request.GET.get("page") or "1")
    except ValueError:
        page = 1
    data = PracticePresentationService.history(request.user, page=page)
    return render(
        request,
        "assessment/history.html",
        _student_context(request, extra=data),
    )
