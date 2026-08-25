from django.contrib import admin

from apps.learning import models as m


class TranslationInlineBase(admin.TabularInline):
    extra = 0


@admin.register(m.Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("id", "editorial_state", "is_archived", "sort_order", "updated_at")
    list_filter = ("editorial_state", "is_archived")


@admin.register(m.Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ("id", "course", "editorial_state", "sort_order")
    list_filter = ("editorial_state", "is_archived")
    raw_id_fields = ("course",)


@admin.register(m.Unit)
class UnitAdmin(admin.ModelAdmin):
    list_display = ("id", "subject", "editorial_state", "sort_order")
    raw_id_fields = ("subject",)


@admin.register(m.Chapter)
class ChapterAdmin(admin.ModelAdmin):
    list_display = ("id", "unit", "editorial_state", "sort_order")
    raw_id_fields = ("unit",)


@admin.register(m.Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ("id", "chapter", "editorial_state", "sort_order")
    raw_id_fields = ("chapter",)


@admin.register(m.Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ("id", "topic", "editorial_state", "sort_order")
    raw_id_fields = ("topic",)


@admin.register(m.LearningMaterial)
class LearningMaterialAdmin(admin.ModelAdmin):
    list_display = ("id", "editorial_state", "is_premium", "is_archived")
    list_filter = ("editorial_state", "is_premium", "is_archived")
