"""Assessment catalog + runtime shells (docs/05 §8–9, docs/06 §8.8–8.11, §16)."""
from django.conf import settings
from django.db import models

from apps.common.choices import (
    AttemptMode,
    AttemptState,
    CognitiveLevel,
    DifficultyLevel,
    LocaleCode,
    QuestionErrorReportStatus,
    QuestionSourceType,
    QuestionType,
)
from apps.common.models import (
    ActorTrackedModel,
    ArchivableModel,
    CreatedOnlyModel,
    EditorialModel,
    LocaleField,
    OptimisticConcurrencyModel,
    TimeStampedModel,
    UUIDPrimaryKeyModel,
)


class Tag(UUIDPrimaryKeyModel, TimeStampedModel):
    code = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=128)

    class Meta:
        db_table = "tags"

    def __str__(self):
        return self.code


class ExamBlueprint(UUIDPrimaryKeyModel, TimeStampedModel, ActorTrackedModel):
    """
    Versioned exam distribution config (UNIT-11).

    Data/config representation of a published examination blueprint — NOT a
    hard-coded view. Seeded from the BNMC Comprehensive Registration Examination
    Blueprint (November 2018); never asserted to be the latest revision.
    """

    code = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=255)
    version_label = models.CharField(max_length=64, blank=True, default="")
    source_authority = models.CharField(max_length=255, blank=True, default="")
    total_questions = models.PositiveIntegerField(default=100)
    is_active = models.BooleanField(default=False, db_index=True)
    notes = models.TextField(blank=True, default="")

    class Meta:
        db_table = "exam_blueprints"
        indexes = [
            models.Index(fields=["is_active"]),
        ]

    def __str__(self):
        return self.code


class BlueprintCategory(UUIDPrimaryKeyModel):
    """A competency category with its exam-question allocation (e.g. Fundamentals=30)."""

    blueprint = models.ForeignKey(
        ExamBlueprint,
        on_delete=models.CASCADE,
        related_name="categories",
    )
    code = models.CharField(max_length=64)
    name = models.CharField(max_length=255)
    percent = models.PositiveIntegerField(default=0)
    question_count = models.PositiveIntegerField(default=0)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "blueprint_categories"
        constraints = [
            models.UniqueConstraint(
                fields=["blueprint", "code"],
                name="uq_blueprint_categories_code",
            ),
        ]
        indexes = [
            models.Index(fields=["blueprint", "sort_order"]),
        ]

    def __str__(self):
        return f"{self.code}({self.question_count})"


class BlueprintCompetency(UUIDPrimaryKeyModel):
    """An exact competency statement from the blueprint (never invented)."""

    category = models.ForeignKey(
        BlueprintCategory,
        on_delete=models.CASCADE,
        related_name="competencies",
    )
    code = models.CharField(max_length=64)
    number = models.PositiveIntegerField(default=0)
    text = models.TextField()
    percent = models.PositiveIntegerField(default=0)
    question_count = models.PositiveIntegerField(default=0)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "blueprint_competencies"
        constraints = [
            models.UniqueConstraint(
                fields=["category", "code"],
                name="uq_blueprint_competencies_code",
            ),
        ]
        indexes = [
            models.Index(fields=["category", "sort_order"]),
        ]

    def __str__(self):
        return f"{self.code}"


class BlueprintCognitiveAllocation(UUIDPrimaryKeyModel):
    """Cognitive-level weighting for the blueprint (Recall 50 / Understanding 25 / Application 25)."""

    blueprint = models.ForeignKey(
        ExamBlueprint,
        on_delete=models.CASCADE,
        related_name="cognitive_allocations",
    )
    cognitive_level = models.CharField(max_length=32, choices=CognitiveLevel.choices)
    percent = models.PositiveIntegerField(default=0)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "blueprint_cognitive_allocations"
        constraints = [
            models.UniqueConstraint(
                fields=["blueprint", "cognitive_level"],
                name="uq_blueprint_cognitive_level",
            ),
        ]

    def __str__(self):
        return f"{self.cognitive_level}={self.percent}%"


class Question(
    UUIDPrimaryKeyModel,
    TimeStampedModel,
    ActorTrackedModel,
    OptimisticConcurrencyModel,
    ArchivableModel,
    EditorialModel,
):
    """Stable question aggregate identity (docs/05 §8.1, docs/06 §8.8)."""

    question_type = models.CharField(max_length=32, choices=QuestionType.choices, db_index=True)
    difficulty = models.CharField(
        max_length=16,
        choices=DifficultyLevel.choices,
        null=True,
        blank=True,
        db_index=True,
    )
    primary_locale = LocaleField(default=LocaleCode.BN)
    current_version = models.ForeignKey(
        "QuestionVersion",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    reference_citation = models.TextField(blank=True, default="")

    # --- UNIT-11 metadata (stable/external id, taxonomy, blueprint, provenance) ---
    question_code = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        unique=True,
        db_index=True,
        help_text="Stable external identifier — idempotency key for bulk import.",
    )
    scenario_based = models.BooleanField(default=False, db_index=True)
    cognitive_level = models.CharField(
        max_length=32,
        choices=CognitiveLevel.choices,
        null=True,
        blank=True,
        db_index=True,
        help_text="Recall/Understanding/Application; null = unclassified (admin review).",
    )
    # Content taxonomy — deliberately separate from the exam blueprint (docs item 6).
    content_subject = models.CharField(max_length=255, blank=True, default="", db_index=True)
    content_topic = models.CharField(max_length=255, blank=True, default="", db_index=True)
    # Exam blueprint classification (nullable — not every question maps to the blueprint).
    blueprint_category = models.ForeignKey(
        BlueprintCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="questions",
    )
    blueprint_competency = models.ForeignKey(
        BlueprintCompetency,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="questions",
    )
    needs_review = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Flagged for admin review (e.g. uncertain cognitive level on import).",
    )
    classification_origin = models.CharField(
        max_length=16,
        blank=True,
        default="",
        db_index=True,
        help_text=(
            "suggested = blueprint assistance accepted (not authority); "
            "approved = staff confirmed. Blank = import/legacy/unspecified."
        ),
    )
    # Provenance — ADMIN-ONLY. Never surfaced in any student-facing payload/template.
    source_type = models.CharField(
        max_length=32,
        choices=QuestionSourceType.choices,
        default=QuestionSourceType.STAFF_CREATED,
    )
    source_name = models.CharField(max_length=255, blank=True, default="")
    source_page = models.CharField(max_length=64, blank=True, default="")
    source_reference = models.CharField(max_length=255, blank=True, default="")
    topics = models.ManyToManyField(
        "learning.Topic",
        through="QuestionTopic",
        related_name="questions",
        blank=True,
    )
    tags = models.ManyToManyField(
        Tag,
        through="QuestionTag",
        related_name="questions",
        blank=True,
    )

    class Meta:
        db_table = "questions"
        indexes = [
            models.Index(fields=["editorial_state", "is_archived"]),
            models.Index(fields=["difficulty"]),
            models.Index(fields=["question_type"]),
            models.Index(fields=["current_version"]),
        ]

    def __str__(self):
        return f"Question({self.pk})"


class QuestionVersion(UUIDPrimaryKeyModel, CreatedOnlyModel):
    """Append-only scored revision — immutability enforced by services later."""

    question = models.ForeignKey(Question, on_delete=models.PROTECT, related_name="versions")
    version_no = models.PositiveIntegerField()
    clinical_scenario_body = models.TextField(null=True, blank=True)
    media_asset_key = models.CharField(max_length=512, null=True, blank=True)
    correct_answer_spec = models.JSONField(default=dict, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    class Meta:
        db_table = "question_versions"
        constraints = [
            models.UniqueConstraint(
                fields=["question", "version_no"],
                name="uq_question_versions_question_version_no",
            ),
        ]
        indexes = [
            models.Index(fields=["question", "version_no"]),
        ]

    def __str__(self):
        return f"QVersion({self.question_id}#{self.version_no})"


class QuestionVersionTranslation(UUIDPrimaryKeyModel):
    version = models.ForeignKey(
        QuestionVersion,
        on_delete=models.CASCADE,
        related_name="translations",
    )
    locale = LocaleField()
    stem = models.TextField()
    explanation = models.TextField(blank=True, default="")

    class Meta:
        db_table = "question_version_translations"
        constraints = [
            models.UniqueConstraint(
                fields=["version", "locale"],
                name="uq_question_version_translations_locale",
            ),
        ]


class QuestionOption(UUIDPrimaryKeyModel):
    question_version = models.ForeignKey(
        QuestionVersion,
        on_delete=models.CASCADE,
        related_name="options",
    )
    key = models.CharField(max_length=16)
    is_correct = models.BooleanField(default=False)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "question_options"
        constraints = [
            models.UniqueConstraint(
                fields=["question_version", "key"],
                name="uq_question_options_version_key",
            ),
        ]
        indexes = [
            models.Index(fields=["question_version", "sort_order"]),
        ]


class QuestionOptionTranslation(UUIDPrimaryKeyModel):
    option = models.ForeignKey(
        QuestionOption,
        on_delete=models.CASCADE,
        related_name="translations",
    )
    locale = LocaleField()
    label = models.TextField()

    class Meta:
        db_table = "question_option_translations"
        constraints = [
            models.UniqueConstraint(
                fields=["option", "locale"],
                name="uq_question_option_translations_locale",
            ),
        ]


class QuestionTopic(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    topic = models.ForeignKey("learning.Topic", on_delete=models.CASCADE)

    class Meta:
        db_table = "questions_topics"
        constraints = [
            models.UniqueConstraint(fields=["question", "topic"], name="uq_questions_topics"),
        ]
        indexes = [
            models.Index(fields=["topic"]),
            models.Index(fields=["question"]),
        ]


class QuestionTag(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE)

    class Meta:
        db_table = "questions_tags"
        constraints = [
            models.UniqueConstraint(fields=["question", "tag"], name="uq_questions_tags"),
        ]


class ExamDefinition(
    UUIDPrimaryKeyModel,
    TimeStampedModel,
    ActorTrackedModel,
    OptimisticConcurrencyModel,
    ArchivableModel,
    EditorialModel,
):
    """Exam/mock blueprint catalog (docs/06 §16)."""

    code = models.CharField(max_length=64, unique=True)
    title_key = models.CharField(max_length=128)
    mode = models.CharField(max_length=32, choices=AttemptMode.choices)
    time_limit_seconds = models.PositiveIntegerField(null=True, blank=True)
    is_premium = models.BooleanField(default=False)
    track_code = models.CharField(max_length=64, null=True, blank=True, db_index=True)
    rules = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "exam_definitions"
        indexes = [
            models.Index(fields=["editorial_state", "is_archived"]),
            models.Index(fields=["is_premium"]),
        ]

    def __str__(self):
        return self.code


class ExamDefinitionItem(UUIDPrimaryKeyModel):
    """Explicit pool membership link (optional complement to rules JSONB)."""

    exam_definition = models.ForeignKey(
        ExamDefinition,
        on_delete=models.CASCADE,
        related_name="items",
    )
    question = models.ForeignKey(Question, on_delete=models.PROTECT, related_name="exam_definition_items")
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "exam_definition_items"
        constraints = [
            models.UniqueConstraint(
                fields=["exam_definition", "question"],
                name="uq_exam_definition_items",
            ),
        ]
        indexes = [
            models.Index(fields=["exam_definition", "sort_order"]),
        ]


class QuestionImportBatch(UUIDPrimaryKeyModel, CreatedOnlyModel):
    """
    Post-import report row (UNIT-12). Records committed and rejected workbook
    attempts. Never stores student-facing content; codes and counts only.
    """

    STATUS_COMMITTED = "committed"
    STATUS_REJECTED = "rejected"

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="question_import_batches",
    )
    filename = models.CharField(max_length=255, blank=True, default="")
    status = models.CharField(max_length=32, db_index=True, default=STATUS_COMMITTED)
    total_rows = models.PositiveIntegerField(default=0)
    created_count = models.PositiveIntegerField(default=0)
    skipped_duplicate = models.PositiveIntegerField(default=0)
    invalid_count = models.PositiveIntegerField(default=0)
    needs_review_count = models.PositiveIntegerField(default=0)
    type_counts = models.JSONField(default=dict, blank=True)
    blueprint_counts = models.JSONField(default=dict, blank=True)
    cognitive_counts = models.JSONField(default=dict, blank=True)
    created_codes = models.JSONField(default=list, blank=True)
    skipped_codes = models.JSONField(default=list, blank=True)
    errors = models.JSONField(default=list, blank=True)
    warnings = models.JSONField(default=list, blank=True)
    report = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "question_import_batches"
        indexes = [
            models.Index(fields=["-created_at"]),
            models.Index(fields=["status", "-created_at"]),
        ]

    def __str__(self):
        return f"ImportBatch({self.status}:{self.created_count})"


class QuestionErrorReport(UUIDPrimaryKeyModel, TimeStampedModel):
    question = models.ForeignKey(Question, on_delete=models.PROTECT, related_name="error_reports")
    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="question_error_reports",
    )
    body = models.TextField()
    status = models.CharField(
        max_length=32,
        choices=QuestionErrorReportStatus.choices,
        default=QuestionErrorReportStatus.OPEN,
        db_index=True,
    )
    triage_notes = models.TextField(blank=True, default="")

    class Meta:
        db_table = "question_error_reports"
        indexes = [
            models.Index(fields=["question", "status"]),
        ]


class Attempt(UUIDPrimaryKeyModel, CreatedOnlyModel):
    """
    Practice/exam attempt shell (docs/05 §9, docs/06 §8.11).

    No scoring, timer authority, or submission workflow logic on this model.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="attempts",
    )
    mode = models.CharField(max_length=32, choices=AttemptMode.choices, db_index=True)
    state = models.CharField(
        max_length=32,
        choices=AttemptState.choices,
        default=AttemptState.NOT_STARTED,
        db_index=True,
    )
    scope_type = models.CharField(max_length=64, null=True, blank=True)
    scope_id = models.UUIDField(null=True, blank=True)
    exam_definition = models.ForeignKey(
        ExamDefinition,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="attempts",
    )
    time_limit_seconds = models.PositiveIntegerField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    score_summary = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "attempts"
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["state"]),
            models.Index(fields=["exam_definition"]),
            models.Index(fields=["mode"]),
        ]

    def __str__(self):
        return f"Attempt({self.pk}:{self.mode}:{self.state})"


class AttemptItem(UUIDPrimaryKeyModel):
    """Per-question slot with frozen QuestionVersion reference."""

    attempt = models.ForeignKey(Attempt, on_delete=models.PROTECT, related_name="items")
    position = models.PositiveIntegerField()
    question = models.ForeignKey(Question, on_delete=models.PROTECT, related_name="attempt_items")
    question_version = models.ForeignKey(
        QuestionVersion,
        on_delete=models.PROTECT,
        related_name="attempt_items",
    )
    selected_answer = models.JSONField(null=True, blank=True)
    is_correct = models.BooleanField(null=True, blank=True)
    # Numeric marks earned for this item (0.0–1.0). Supports partial True/False
    # scoring (+0.2 per correct statement). Null until finalized. Server-owned.
    score = models.FloatField(null=True, blank=True)
    answered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "attempt_items"
        constraints = [
            models.UniqueConstraint(
                fields=["attempt", "position"],
                name="uq_attempt_items_attempt_position",
            ),
        ]
        indexes = [
            models.Index(fields=["attempt", "position"]),
            models.Index(fields=["question"]),
            models.Index(fields=["question_version"]),
        ]
