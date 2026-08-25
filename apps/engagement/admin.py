from django.contrib import admin

from apps.engagement.models import Bookmark, PersonalNote, StudyGoal, StudyStreak


@admin.register(PersonalNote)
class PersonalNoteAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "target_type", "target_id", "updated_at")
    raw_id_fields = ("user",)


@admin.register(Bookmark)
class BookmarkAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "target_type", "target_id")
    raw_id_fields = ("user",)


@admin.register(StudyGoal)
class StudyGoalAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "title", "is_active", "progress_count", "target_count")
    raw_id_fields = ("user",)


@admin.register(StudyStreak)
class StudyStreakAdmin(admin.ModelAdmin):
    list_display = ("user", "current_streak_days", "longest_streak_days", "last_activity_date")
    raw_id_fields = ("user",)
