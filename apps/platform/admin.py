from django.contrib import admin

from apps.platform.models import FeatureToggle, PlatformSetting


@admin.register(PlatformSetting)
class PlatformSettingAdmin(admin.ModelAdmin):
    list_display = ("key", "updated_at", "updated_by")
    search_fields = ("key",)


@admin.register(FeatureToggle)
class FeatureToggleAdmin(admin.ModelAdmin):
    list_display = ("code", "is_enabled", "updated_at")
    list_filter = ("is_enabled",)
