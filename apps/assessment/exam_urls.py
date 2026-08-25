"""Formal exam URL routes (UNIT-6)."""
from django.urls import path

from apps.assessment import exam_views

app_name = "exams"

urlpatterns = [
    path("", exam_views.catalog, name="catalog"),
    path("history/", exam_views.history, name="history"),
    path("<uuid:exam_id>/", exam_views.detail, name="detail"),
    path("<uuid:exam_id>/start/", exam_views.start, name="start"),
    path(
        "attempts/<uuid:attempt_id>/session/<int:position>/",
        exam_views.session,
        name="session",
    ),
    path(
        "attempts/<uuid:attempt_id>/answer/<int:position>/",
        exam_views.answer,
        name="answer",
    ),
    path("attempts/<uuid:attempt_id>/submit/", exam_views.submit, name="submit"),
    path("attempts/<uuid:attempt_id>/result/", exam_views.result, name="result"),
    path("attempts/<uuid:attempt_id>/review/", exam_views.review, name="review"),
]
