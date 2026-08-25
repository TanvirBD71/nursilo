"""Learning catalog hierarchy and learner progress shells (docs/05 §7, docs/06 §8.6–8.7)."""
from django.conf import settings
from django.db import models

from apps.common.models import (
    CatalogNodeModel,
    LocaleField,
    TimeStampedModel,
    UUIDPrimaryKeyModel,
)


class Course(CatalogNodeModel):
    class Meta:
        db_table = "courses"
        indexes = [
            models.Index(fields=["editorial_state", "is_archived"]),
            models.Index(
                fields=["sort_order"],
                name="courses_published_sort_idx",
                condition=models.Q(editorial_state="published", is_archived=False),
            ),
        ]

    def __str__(self):
        return f"Course({self.pk})"


class CourseTranslation(UUIDPrimaryKeyModel):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="translations")
    locale = LocaleField()
    title = models.CharField(max_length=255)
    summary = models.TextField(blank=True, default="")

    class Meta:
        db_table = "course_translations"
        constraints = [
            models.UniqueConstraint(fields=["course", "locale"], name="uq_course_translations_locale"),
        ]

    def __str__(self):
        return f"{self.course_id}:{self.locale}"


class Subject(CatalogNodeModel):
    course = models.ForeignKey(Course, on_delete=models.PROTECT, related_name="subjects")

    class Meta:
        db_table = "subjects"
        indexes = [
            models.Index(fields=["course", "sort_order"]),
            models.Index(fields=["editorial_state", "is_archived"]),
        ]

    def __str__(self):
        return f"Subject({self.pk})"


class SubjectTranslation(UUIDPrimaryKeyModel):
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name="translations")
    locale = LocaleField()
    title = models.CharField(max_length=255)
    summary = models.TextField(blank=True, default="")

    class Meta:
        db_table = "subject_translations"
        constraints = [
            models.UniqueConstraint(fields=["subject", "locale"], name="uq_subject_translations_locale"),
        ]


class Unit(CatalogNodeModel):
    subject = models.ForeignKey(Subject, on_delete=models.PROTECT, related_name="units")

    class Meta:
        db_table = "units"
        indexes = [
            models.Index(fields=["subject", "sort_order"]),
            models.Index(fields=["editorial_state", "is_archived"]),
        ]


class UnitTranslation(UUIDPrimaryKeyModel):
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name="translations")
    locale = LocaleField()
    title = models.CharField(max_length=255)
    summary = models.TextField(blank=True, default="")

    class Meta:
        db_table = "unit_translations"
        constraints = [
            models.UniqueConstraint(fields=["unit", "locale"], name="uq_unit_translations_locale"),
        ]


class Chapter(CatalogNodeModel):
    unit = models.ForeignKey(Unit, on_delete=models.PROTECT, related_name="chapters")

    class Meta:
        db_table = "chapters"
        indexes = [
            models.Index(fields=["unit", "sort_order"]),
            models.Index(fields=["editorial_state", "is_archived"]),
        ]


class ChapterTranslation(UUIDPrimaryKeyModel):
    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE, related_name="translations")
    locale = LocaleField()
    title = models.CharField(max_length=255)
    summary = models.TextField(blank=True, default="")

    class Meta:
        db_table = "chapter_translations"
        constraints = [
            models.UniqueConstraint(fields=["chapter", "locale"], name="uq_chapter_translations_locale"),
        ]


class Topic(CatalogNodeModel):
    chapter = models.ForeignKey(Chapter, on_delete=models.PROTECT, related_name="topics")

    class Meta:
        db_table = "topics"
        indexes = [
            models.Index(fields=["chapter", "sort_order"]),
            models.Index(fields=["editorial_state", "is_archived"]),
        ]


class TopicTranslation(UUIDPrimaryKeyModel):
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name="translations")
    locale = LocaleField()
    title = models.CharField(max_length=255)
    summary = models.TextField(blank=True, default="")

    class Meta:
        db_table = "topic_translations"
        constraints = [
            models.UniqueConstraint(fields=["topic", "locale"], name="uq_topic_translations_locale"),
        ]


class Lesson(CatalogNodeModel):
    topic = models.ForeignKey(Topic, on_delete=models.PROTECT, related_name="lessons")
    materials = models.ManyToManyField(
        "LearningMaterial",
        through="LessonLearningMaterial",
        related_name="lessons",
        blank=True,
    )
    extra_subjects = models.ManyToManyField(
        Subject,
        through="LessonSubject",
        related_name="extra_lessons",
        blank=True,
    )

    class Meta:
        db_table = "lessons"
        indexes = [
            models.Index(fields=["topic", "sort_order"]),
            models.Index(fields=["editorial_state", "is_archived"]),
        ]


class LessonTranslation(UUIDPrimaryKeyModel):
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="translations")
    locale = LocaleField()
    title = models.CharField(max_length=255)
    body = models.TextField(blank=True, default="")

    class Meta:
        db_table = "lesson_translations"
        constraints = [
            models.UniqueConstraint(fields=["lesson", "locale"], name="uq_lesson_translations_locale"),
        ]


class LearningMaterial(CatalogNodeModel):
    """Reusable composable asset — may link from multiple lessons (docs/05 §7.1)."""

    is_premium = models.BooleanField(default=False)

    class Meta:
        db_table = "learning_materials"
        indexes = [
            models.Index(fields=["editorial_state", "is_archived"]),
            models.Index(fields=["is_premium"]),
        ]


class LearningMaterialTranslation(UUIDPrimaryKeyModel):
    learning_material = models.ForeignKey(
        LearningMaterial,
        on_delete=models.CASCADE,
        related_name="translations",
    )
    locale = LocaleField()
    title = models.CharField(max_length=255)
    body = models.TextField(blank=True, default="")

    class Meta:
        db_table = "learning_material_translations"
        constraints = [
            models.UniqueConstraint(
                fields=["learning_material", "locale"],
                name="uq_learning_material_translations_locale",
            ),
        ]


class LessonLearningMaterial(models.Model):
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE)
    learning_material = models.ForeignKey(LearningMaterial, on_delete=models.CASCADE)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "lessons_learning_materials"
        constraints = [
            models.UniqueConstraint(
                fields=["lesson", "learning_material"],
                name="uq_lessons_learning_materials",
            ),
        ]
        indexes = [
            models.Index(fields=["lesson", "sort_order"]),
            models.Index(fields=["learning_material"]),
        ]


class LessonSubject(models.Model):
    """Optional academic M:N beyond strict tree (docs/05 §7.3, docs/06 §7.3)."""

    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)

    class Meta:
        db_table = "lessons_subjects"
        constraints = [
            models.UniqueConstraint(fields=["lesson", "subject"], name="uq_lessons_subjects"),
        ]


class LearnerProgress(UUIDPrimaryKeyModel, TimeStampedModel):
    """Per-user lesson/topic progress pointer (learner-owned)."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="learner_progress",
    )
    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="progress_rows",
    )
    topic = models.ForeignKey(
        Topic,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="progress_rows",
    )
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    progress_percent = models.PositiveSmallIntegerField(default=0)

    class Meta:
        db_table = "learner_progress"
        indexes = [
            models.Index(fields=["user", "updated_at"]),
            models.Index(fields=["user", "lesson"]),
            models.Index(fields=["user", "topic"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(lesson__isnull=False) | models.Q(topic__isnull=False),
                name="ck_learner_progress_has_target",
            ),
            models.UniqueConstraint(
                fields=["user", "lesson"],
                condition=models.Q(lesson__isnull=False),
                name="uq_learner_progress_user_lesson",
            ),
        ]


class ContinueLearningCursor(UUIDPrimaryKeyModel, TimeStampedModel):
    """One continue-learning cursor per user (docs/06 §22)."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="continue_learning_cursor",
    )
    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    topic = models.ForeignKey(
        Topic,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    last_position_meta = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "continue_learning_cursors"
