"""Thin learning views — services own access, progress, and presentation (docs/04, docs/15)."""
from __future__ import annotations

from django.contrib import messages
from django.http import Http404
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods, require_POST

from apps.learning.forms import LessonCompleteForm
from apps.learning.services import (
    LearningAccessService,
    LearningCatalogService,
    LearningPresentationService,
    LearningProgressService,
)
from apps.learning.services.progress import CompletionResult
from apps.portal.access import student_portal_required
from apps.portal.services import (
    NavigationService,
    NotificationPresentationService,
    SubscriptionPresentationService,
)


def _student_context(request, *, active: str = "learn", extra=None) -> dict:
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


def _raise_if_hidden(decision) -> None:
    if decision.allowed:
        return
    if LearningAccessService.hide_as_not_found(decision):
        raise Http404("Not found.")
    raise Http404("Not found.")


def _require_visible_course(user, course_id):
    course = LearningCatalogService.get_course(course_id)
    decision = LearningAccessService.decide_node(user, course)
    _raise_if_hidden(decision)
    return course


def _require_visible_subject(user, subject_id):
    subject = LearningCatalogService.get_subject(subject_id)
    decision = LearningAccessService.decide_node(user, subject)
    if decision.allowed and subject is not None:
        parent = LearningAccessService.decide_node(user, subject.course)
        if not parent.allowed:
            decision = parent
    _raise_if_hidden(decision)
    return subject


def _require_visible_unit(user, unit_id):
    unit = LearningCatalogService.get_unit(unit_id)
    decision = LearningAccessService.decide_node(user, unit)
    if decision.allowed and unit is not None:
        for node in (unit.subject, unit.subject.course):
            parent = LearningAccessService.decide_node(user, node)
            if not parent.allowed:
                decision = parent
                break
    _raise_if_hidden(decision)
    return unit


def _require_visible_chapter(user, chapter_id):
    chapter = LearningCatalogService.get_chapter(chapter_id)
    decision = LearningAccessService.decide_node(user, chapter)
    if decision.allowed and chapter is not None:
        for node in (
            chapter.unit,
            chapter.unit.subject,
            chapter.unit.subject.course,
        ):
            parent = LearningAccessService.decide_node(user, node)
            if not parent.allowed:
                decision = parent
                break
    _raise_if_hidden(decision)
    return chapter


def _require_visible_topic(user, topic_id):
    topic = LearningCatalogService.get_topic(topic_id)
    decision = LearningAccessService.decide_node(user, topic)
    if decision.allowed and topic is not None:
        for node in (
            topic.chapter,
            topic.chapter.unit,
            topic.chapter.unit.subject,
            topic.chapter.unit.subject.course,
        ):
            parent = LearningAccessService.decide_node(user, node)
            if not parent.allowed:
                decision = parent
                break
    _raise_if_hidden(decision)
    return topic


def _require_visible_lesson(user, lesson_id):
    lesson = LearningCatalogService.get_lesson(lesson_id)
    decision = LearningAccessService.decide_lesson(user, lesson)
    _raise_if_hidden(decision)
    return lesson


@student_portal_required
@require_http_methods(["GET"])
def catalog(request):
    page = LearningPresentationService.catalog(request.user)
    return render(
        request,
        "learning/catalog.html",
        _student_context(request, extra=page),
    )


@student_portal_required
@require_http_methods(["GET"])
def course_detail(request, course_id):
    course = _require_visible_course(request.user, course_id)
    page = LearningPresentationService.course_overview(request.user, course)
    return render(
        request,
        "learning/course_overview.html",
        _student_context(request, extra=page),
    )


@student_portal_required
@require_http_methods(["GET"])
def subject_detail(request, subject_id):
    subject = _require_visible_subject(request.user, subject_id)
    page = LearningPresentationService.subject_page(request.user, subject)
    return render(
        request,
        "learning/hierarchy.html",
        _student_context(request, extra=page),
    )


@student_portal_required
@require_http_methods(["GET"])
def unit_detail(request, unit_id):
    unit = _require_visible_unit(request.user, unit_id)
    page = LearningPresentationService.unit_page(request.user, unit)
    return render(
        request,
        "learning/hierarchy.html",
        _student_context(request, extra=page),
    )


@student_portal_required
@require_http_methods(["GET"])
def chapter_detail(request, chapter_id):
    chapter = _require_visible_chapter(request.user, chapter_id)
    page = LearningPresentationService.chapter_page(request.user, chapter)
    return render(
        request,
        "learning/hierarchy.html",
        _student_context(request, extra=page),
    )


@student_portal_required
@require_http_methods(["GET"])
def topic_detail(request, topic_id):
    topic = _require_visible_topic(request.user, topic_id)
    page = LearningPresentationService.topic_page(request.user, topic)
    return render(
        request,
        "learning/hierarchy.html",
        _student_context(request, extra=page),
    )


@student_portal_required
@require_http_methods(["GET"])
def lesson_detail(request, lesson_id):
    lesson = _require_visible_lesson(request.user, lesson_id)
    LearningProgressService.record_lesson_visit(user=request.user, lesson=lesson)
    page = LearningPresentationService.lesson_page(request.user, lesson)
    page["complete_form"] = LessonCompleteForm()
    return render(
        request,
        "learning/lesson.html",
        _student_context(request, extra=page),
    )


@student_portal_required
@require_POST
def lesson_complete(request, lesson_id):
    form = LessonCompleteForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Could not mark the lesson complete. Please try again.")
        return redirect("learning:lesson", lesson_id=lesson_id)

    lesson = LearningCatalogService.get_lesson(lesson_id)
    result = LearningProgressService.complete_lesson(user=request.user, lesson=lesson)

    if result == CompletionResult.COMPLETED:
        messages.success(request, "Lesson marked complete.")
    elif result == CompletionResult.ALREADY_COMPLETED:
        messages.info(request, "Lesson was already complete.")
    elif result == CompletionResult.UNAUTHORIZED:
        messages.error(request, "You must be signed in to mark progress.")
        return redirect("accounts:login")
    elif result in {CompletionResult.NOT_FOUND, CompletionResult.UNAVAILABLE}:
        raise Http404("Not found.")
    else:
        messages.error(request, "Could not update progress. Please try again.")

    return redirect("learning:lesson", lesson_id=lesson_id)


@student_portal_required
@require_http_methods(["GET"])
def progress_overview(request):
    page = LearningPresentationService.progress_overview(request.user)
    return render(
        request,
        "learning/progress.html",
        _student_context(request, extra=page),
    )


@student_portal_required
@require_http_methods(["GET"])
def material_detail(request, material_id):
    material = LearningCatalogService.get_material(material_id)
    via_lesson = None
    lesson_id = request.GET.get("lesson")
    if lesson_id:
        via_lesson = LearningCatalogService.get_lesson(lesson_id)
        if via_lesson is not None:
            lesson_decision = LearningAccessService.decide_lesson(
                request.user, via_lesson
            )
            if not lesson_decision.allowed:
                via_lesson = None

    page = LearningPresentationService.material_page(
        request.user, material, via_lesson=via_lesson
    )
    if page is None:
        raise Http404("Not found.")
    # Premium locked page is honest (no body), not a 404.
    return render(
        request,
        "learning/material.html",
        _student_context(request, extra=page),
    )
