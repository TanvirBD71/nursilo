from django.contrib import admin

from apps.notifications.models import Announcement, Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "kind", "title", "is_read", "created_at")
    list_filter = ("kind", "is_read")
    raw_id_fields = ("user", "announcement")


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ("code", "editorial_state", "is_archived", "updated_at")
    list_filter = ("editorial_state", "is_archived")
