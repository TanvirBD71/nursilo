"""Staff console URL routes (UNIT-9)."""
from django.urls import path

from apps.staff import views

app_name = "staff"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("users/", views.users_list, name="users"),
    path("users/create/", views.users_create, name="users_create"),
    path("users/<uuid:user_id>/", views.user_detail, name="user_detail"),
    path("learning/", views.learning_list, name="learning"),
    path("learning/create/<slug:kind>/", views.learning_create, name="learning_create"),
    path("learning/<slug:kind>/<uuid:node_id>/", views.learning_detail, name="learning_detail"),
    path(
        "learning/<slug:kind>/<uuid:node_id>/preview/",
        views.preview_learning,
        name="learning_preview",
    ),
    path("questions/", views.questions_list, name="questions"),
    path("questions/create/", views.questions_create, name="questions_create"),
    path("questions/import/", views.questions_import, name="questions_import"),
    path(
        "questions/import/template/",
        views.questions_import_template,
        name="questions_import_template",
    ),
    path(
        "questions/import/template/author/",
        views.questions_import_template_author,
        name="questions_import_template_author",
    ),
    path(
        "questions/import/history/",
        views.questions_import_history,
        name="questions_import_history",
    ),
    path(
        "questions/import/history/<uuid:batch_id>/",
        views.questions_import_batch,
        name="questions_import_batch",
    ),
    path("questions/reports/", views.question_reports, name="question_reports"),
    path("questions/<uuid:question_id>/", views.question_detail, name="question_detail"),
    path("blueprints/", views.blueprints_list, name="blueprints"),
    path("blueprints/<uuid:blueprint_id>/", views.blueprint_detail, name="blueprint_detail"),
    path("exams/", views.exams_list, name="exams"),
    path("exams/create/", views.exams_create, name="exams_create"),
    path("exams/<uuid:exam_id>/", views.exam_detail, name="exam_detail"),
    path("library/", views.library_list, name="library"),
    path("library/create/", views.library_create, name="library_create"),
    path("library/<uuid:book_id>/", views.library_detail, name="library_detail"),
    path("cms/", views.cms_home, name="cms"),
    path("cms/pages/create/", views.cms_page_create, name="cms_page_create"),
    path("cms/pages/<uuid:page_id>/", views.cms_page_detail, name="cms_page_detail"),
    path("cms/posts/create/", views.cms_post_create, name="cms_post_create"),
    path("cms/posts/<uuid:post_id>/", views.cms_post_detail, name="cms_post_detail"),
    path(
        "cms/contacts/<uuid:message_id>/",
        views.cms_contact_update,
        name="cms_contact_update",
    ),
    path("announcements/", views.announcements_list, name="announcements"),
    path("announcements/create/", views.announcements_create, name="announcements_create"),
    path(
        "announcements/<uuid:announcement_id>/",
        views.announcement_detail,
        name="announcement_detail",
    ),
    path("billing/", views.billing_home, name="billing"),
    path("audit/", views.audit_list, name="audit"),
    path("editorial/", views.editorial_queue, name="editorial_queue"),
]
