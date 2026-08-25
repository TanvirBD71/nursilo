"""Billing / subscription checkout routes (UNIT-8)."""
from django.urls import path

from apps.billing import views

app_name = "billing"

urlpatterns = [
    path("pricing/", views.pricing, name="pricing"),
    path("current/", views.current_subscription, name="current"),
    path("checkout/", views.checkout, name="checkout"),
    path("pending/<uuid:payment_id>/", views.pending, name="pending"),
    path("success/<uuid:payment_id>/", views.success, name="success"),
    path("failure/<uuid:payment_id>/", views.failure, name="failure"),
    path("history/", views.history, name="history"),
    path("return/success/", views.return_success, name="return_success"),
    path("return/fail/", views.return_fail, name="return_fail"),
    path("return/cancel/", views.return_cancel, name="return_cancel"),
    path("ipn/", views.ipn, name="ipn"),
]
