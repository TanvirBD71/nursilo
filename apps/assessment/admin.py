from django.contrib import admin

from apps.assessment import models as m


@admin.register(m.Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("code", "name")
    search_fields = ("code", "name")


@admin.register(m.Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("id", "question_type", "difficulty", "editorial_state", "is_archived")
    list_filter = ("question_type", "difficulty", "editorial_state", "is_archived")
    raw_id_fields = ("current_version",)


@admin.register(m.QuestionVersion)
class QuestionVersionAdmin(admin.ModelAdmin):
    list_display = ("id", "question", "version_no", "created_at")
    raw_id_fields = ("question", "created_by")


@admin.register(m.ExamDefinition)
class ExamDefinitionAdmin(admin.ModelAdmin):
    list_display = ("code", "mode", "editorial_state", "is_premium", "track_code")
    list_filter = ("mode", "editorial_state", "is_premium")


@admin.register(m.Attempt)
class AttemptAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "mode", "state", "created_at")
    list_filter = ("mode", "state")
    raw_id_fields = ("user", "exam_definition")


@admin.register(m.QuestionErrorReport)
class QuestionErrorReportAdmin(admin.ModelAdmin):
    list_display = ("id", "question", "reporter", "status", "created_at")
    list_filter = ("status",)
    raw_id_fields = ("question", "reporter")
