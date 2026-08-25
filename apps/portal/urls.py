"""Student Portal URL routes (UNIT-3)."""
from django.urls import path

from apps.portal import views

app_name = "portal"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("profile/", views.profile, name="profile"),
    path("profile/edit/", views.profile_edit, name="profile_edit"),
    path(
        "profile/academic/",
        views.academic_profile_edit,
        name="academic_profile_edit",
    ),
    path("notifications/", views.notifications, name="notifications"),
    path(
        "notifications/<uuid:notification_id>/read/",
        views.notification_mark_read,
        name="notification_mark_read",
    ),
    path("subscription/", views.subscription, name="subscription"),
    path("settings/", views.settings, name="settings"),
    path("unavailable/<slug:feature>/", views.unavailable, name="unavailable"),
]
