from django.contrib import admin

from apps.billing.models import PaymentTransaction, Subscription


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ("user", "state", "premium_started_at", "premium_expires_at", "updated_at")
    list_filter = ("state",)
    raw_id_fields = ("user",)


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = (
        "gateway",
        "gateway_ref",
        "plan_code",
        "user",
        "amount",
        "currency",
        "status",
        "created_at",
    )
    list_filter = ("gateway", "status", "plan_code")
    raw_id_fields = ("user", "subscription")
    search_fields = ("gateway_ref", "plan_code")
