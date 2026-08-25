"""Learning domain URL routes (UNIT-4)."""
from django.urls import path

from apps.learning import views

app_name = "learning"

urlpatterns = [
    path("", views.catalog, name="catalog"),
    path("progress/", views.progress_overview, name="progress"),
    path("courses/<uuid:course_id>/", views.course_detail, name="course"),
    path("subjects/<uuid:subject_id>/", views.subject_detail, name="subject"),
    path("units/<uuid:unit_id>/", views.unit_detail, name="unit"),
    path("chapters/<uuid:chapter_id>/", views.chapter_detail, name="chapter"),
    path("topics/<uuid:topic_id>/", views.topic_detail, name="topic"),
    path("lessons/<uuid:lesson_id>/", views.lesson_detail, name="lesson"),
    path(
        "lessons/<uuid:lesson_id>/complete/",
        views.lesson_complete,
        name="lesson_complete",
    ),
    path("materials/<uuid:material_id>/", views.material_detail, name="material"),
]
