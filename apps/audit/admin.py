from django.contrib import admin

from apps.audit.models import AuditEvent


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = ("action", "actor_user", "target_type", "target_id", "created_at")
    list_filter = ("action",)
    search_fields = ("action", "target_type", "target_id")
    raw_id_fields = ("actor_user",)
    readonly_fields = ("id", "actor_user", "action", "target_type", "target_id", "metadata", "created_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
