"""Practice / assessment runtime URL routes (UNIT-5)."""
from django.urls import path

from apps.assessment import views

app_name = "assessment"

urlpatterns = [
    path("", views.entry, name="entry"),
    path("setup/", views.setup, name="setup"),
    path("history/", views.history, name="history"),
    path("attempts/<uuid:attempt_id>/session/<int:position>/", views.session, name="session"),
    path("attempts/<uuid:attempt_id>/answer/<int:position>/", views.answer, name="answer"),
    path("attempts/<uuid:attempt_id>/submit/", views.submit, name="submit"),
    path("attempts/<uuid:attempt_id>/result/", views.result, name="result"),
    path("attempts/<uuid:attempt_id>/review/", views.review, name="review"),
]
