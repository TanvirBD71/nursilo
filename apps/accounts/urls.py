"""Auth URL routes — identity flows only (UNIT-2)."""
from django.urls import path

from apps.accounts import views

app_name = "accounts"

urlpatterns = [
    path("register/", views.register, name="register"),
    path("login/", views.login, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("password/change/", views.password_change, name="password_change"),
    path("password/reset/", views.password_reset_request, name="password_reset_request"),
    path(
        "password/reset/confirm/",
        views.password_reset_confirm,
        name="password_reset_confirm",
    ),
    path("email/verify/", views.verify_email, name="verify_email"),
    path("email/resend/", views.resend_verification, name="resend_verification"),
    path("reauth/", views.reauth, name="reauth"),
    path("devices/", views.devices, name="devices"),
    path("devices/<uuid:session_id>/revoke/", views.revoke_device, name="revoke_device"),
    path("logout/all/", views.logout_all, name="logout_all"),
    path("logout/others/", views.logout_others, name="logout_others"),
]
