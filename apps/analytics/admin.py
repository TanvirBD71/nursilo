from django.contrib import admin

from apps.analytics.models import ContentPerformanceStat, LearnerTopicStat, QuestionUsageStat


@admin.register(LearnerTopicStat)
class LearnerTopicStatAdmin(admin.ModelAdmin):
    list_display = ("user", "topic", "attempt_count", "correct_count", "accuracy_rate")
    raw_id_fields = ("user", "topic")


@admin.register(QuestionUsageStat)
class QuestionUsageStatAdmin(admin.ModelAdmin):
    list_display = ("question", "attempt_count", "correct_count", "accuracy_rate")
    raw_id_fields = ("question",)


@admin.register(ContentPerformanceStat)
class ContentPerformanceStatAdmin(admin.ModelAdmin):
    list_display = ("content_type", "content_id", "views_or_starts", "completions")
