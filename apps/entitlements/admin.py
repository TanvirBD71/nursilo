from django.contrib import admin

from apps.entitlements.models import EntitlementGrant


@admin.register(EntitlementGrant)
class EntitlementGrantAdmin(admin.ModelAdmin):
    list_display = ("user", "capability_code", "is_active", "starts_at", "ends_at", "source")
    list_filter = ("is_active", "source", "capability_code")
    raw_id_fields = ("user", "granted_by")
