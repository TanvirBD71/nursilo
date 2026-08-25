"""Minimal admin registration for identity inspection."""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from apps.accounts.models import AcademicProfile, UserAccount


@admin.register(UserAccount)
class UserAccountAdmin(DjangoUserAdmin):
    ordering = ("email",)
    list_display = ("email", "full_name", "ui_locale", "is_active", "is_staff", "date_joined")
    list_filter = ("is_active", "is_staff", "ui_locale")
    search_fields = ("email", "full_name")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Profile", {"fields": ("full_name", "ui_locale", "email_verified_at")}),
        ("Flags", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "password1", "password2", "is_staff", "is_superuser"),
            },
        ),
    )
    filter_horizontal = ("groups", "user_permissions")


@admin.register(AcademicProfile)
class AcademicProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "academic_program", "institution", "current_semester_year")
    search_fields = ("user__email", "institution", "academic_program")
    raw_id_fields = ("user",)
