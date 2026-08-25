"""Question bank staff management — preserves versioning/scoring integrity."""
from __future__ import annotations

from django.db import transaction
from django.db.models import Q

from dataclasses import dataclass, field
import os

from apps.assessment.models import (
    BlueprintCategory,
    BlueprintCompetency,
    Question,
    QuestionErrorReport,
    QuestionImportBatch,
    QuestionOption,
    QuestionOptionTranslation,
    QuestionTopic,
    QuestionVersion,
    QuestionVersionTranslation,
)
from apps.assessment.services.blueprint_suggest import BlueprintSuggestionService
from apps.assessment.services.duplicates import QuestionDuplicateService
from apps.assessment.services.import_questions import (
    QuestionImportService,
    clear_stash,
    is_valid_stash_path,
    stash_workbook,
)
from apps.assessment.services.import_template import (
    AUTHOR_TEMPLATE_FILENAME,
    TEMPLATE_FILENAME,
    build_author_workbook,
    build_example_workbook,
)
from apps.assessment.services.protection import (
    MARCH_2025_BULK_REASON,
    is_march_2025_protected,
)
from apps.audit.services import AuditService
from apps.cms.services import EditorialWorkflowService
from apps.cms.services.editorial import EditorialWorkflowError
from apps.common.choices import (
    ClassificationOrigin,
    CognitiveLevel,
    DifficultyLevel,
    EditorialState,
    LocaleCode,
    QuestionErrorReportStatus,
    QuestionType,
    RoleCode,
)
from apps.learning.models import Topic
from apps.rbac.services import AccessControlService
from apps.staff.services.pagination import paginate_queryset


class QuestionStaffError(Exception):
    def __init__(self, message: str, *, code: str = "question_error"):
        super().__init__(message)
        self.code = code


@dataclass
class BulkItemFailure:
    question_id: str
    question_code: str
    reason: str


@dataclass
class BulkActionResult:
    action: str
    selected: int
    succeeded: int
    failed: int
    successes: list[str] = field(default_factory=list)
    failures: list[BulkItemFailure] = field(default_factory=list)


class QuestionStaffService:
    @classmethod
    def list_questions(
        cls,
        actor,
        *,
        q: str = "",
        state: str = "",
        question_type: str = "",
        cognitive: str = "",
        blueprint_category: str = "",
        blueprint_competency: str = "",
        content_subject: str = "",
        content_topic: str = "",
        scenario_based=None,
        needs_review=None,
        source_type: str = "",
        source_name: str = "",
        created_from: str = "",
        created_to: str = "",
        import_batch_id: str = "",
        difficulty: str = "",
        classification_origin: str = "",
        page=1,
    ):
        """
        Server-side paginated + filtered question-bank listing.

        Filtering/pagination run in the database so the console scales to
        thousands of questions. Non-privileged staff only ever see their own
        drafts plus published rows (see ``_scope``).
        """
        cls._require_view(actor)
        qs = Question.objects.all().order_by("-updated_at")
        qs = cls._scope(actor, qs)
        if state:
            qs = qs.filter(editorial_state=state)
        if question_type:
            qs = qs.filter(question_type=question_type)
        if cognitive:
            qs = qs.filter(cognitive_level=cognitive)
        if blueprint_category:
            qs = qs.filter(blueprint_category_id=blueprint_category)
        if blueprint_competency:
            qs = qs.filter(blueprint_competency_id=blueprint_competency)
        if content_subject:
            qs = qs.filter(content_subject__icontains=content_subject.strip())
        if content_topic:
            qs = qs.filter(content_topic__icontains=content_topic.strip())
        if scenario_based is not None:
            qs = qs.filter(scenario_based=bool(scenario_based))
        if needs_review is not None:
            qs = qs.filter(needs_review=bool(needs_review))
        if source_type:
            qs = qs.filter(source_type=source_type)
        if source_name:
            qs = qs.filter(source_name__icontains=source_name.strip())
        if difficulty:
            qs = qs.filter(difficulty=difficulty)
        if classification_origin:
            qs = qs.filter(classification_origin=classification_origin)
        if created_from:
            parsed = cls._parse_date(created_from)
            if parsed:
                qs = qs.filter(created_at__date__gte=parsed)
        if created_to:
            parsed = cls._parse_date(created_to)
            if parsed:
                qs = qs.filter(created_at__date__lte=parsed)
        if import_batch_id:
            batch = QuestionImportBatch.objects.filter(pk=import_batch_id).first()
            codes = list((batch.created_codes or []) if batch else [])
            qs = qs.filter(question_code__in=codes) if codes else qs.none()
        if q:
            qs = qs.filter(
                Q(versions__translations__stem__icontains=q)
                | Q(id__icontains=q)
                | Q(question_code__icontains=q)
                | Q(content_subject__icontains=q)
                | Q(content_topic__icontains=q)
            ).distinct()
        return paginate_queryset(
            qs.select_related(
                "current_version", "blueprint_category", "blueprint_competency"
            ).prefetch_related("current_version__translations"),
            page=page,
        )

    @classmethod
    def get_question(cls, actor, question_id) -> Question:
        cls._require_view(actor)
        try:
            q = Question.objects.select_related("current_version").get(pk=question_id)
        except Question.DoesNotExist as exc:
            raise QuestionStaffError("Not found.", code="not_found") from exc
        if not cls._can_view(actor, q):
            raise QuestionStaffError("Not found.", code="not_found")
        return q

    @classmethod
    @transaction.atomic
    def create_question(
        cls,
        *,
        actor,
        stem: str,
        explanation: str = "",
        question_type: str = QuestionType.MCQ,
        difficulty: str = DifficultyLevel.MEDIUM,
        locale: str = LocaleCode.EN,
        options: list[dict],
        correct_key: str,
        topic_id=None,
        question_code: str | None = None,
        cognitive_level: str | None = None,
        blueprint_category_id=None,
        blueprint_competency_id=None,
        content_subject: str = "",
        content_topic: str = "",
        scenario_based: bool = False,
        scenario_body: str = "",
        source_type: str | None = None,
        source_name: str = "",
        source_page: str = "",
        source_reference: str = "",
    ) -> Question:
        if not AccessControlService.has_permission(actor, "questions.create"):
            raise PermissionError("Permission denied.")
        if not options or not correct_key:
            raise QuestionStaffError("Options and correct key required.", code="validation")
        keys = [str(o.get("key", "")).strip() for o in options]
        if correct_key not in keys:
            raise QuestionStaffError("Correct key must match an option.", code="validation")
        from apps.common.choices import QuestionSourceType

        question = Question.objects.create(
            question_type=question_type,
            difficulty=difficulty or None,
            primary_locale=locale,
            editorial_state=EditorialState.DRAFT,
            question_code=(question_code or None),
            cognitive_level=(cognitive_level or None),
            blueprint_category_id=blueprint_category_id,
            blueprint_competency_id=blueprint_competency_id,
            content_subject=content_subject or "",
            content_topic=content_topic or "",
            scenario_based=bool(scenario_based),
            needs_review=(cognitive_level is None or blueprint_category_id is None),
            source_type=source_type or QuestionSourceType.STAFF_CREATED,
            source_name=source_name or "",
            source_page=source_page or "",
            source_reference=source_reference or "",
            created_by=actor,
            updated_by=actor,
        )
        version = QuestionVersion.objects.create(
            question=question,
            version_no=1,
            correct_answer_spec={"key": correct_key},
            clinical_scenario_body=(scenario_body or None),
            created_by=actor,
        )
        QuestionVersionTranslation.objects.create(
            version=version,
            locale=locale,
            stem=(stem or "").strip(),
            explanation=explanation or "",
        )
        for i, opt in enumerate(options):
            key = str(opt.get("key", "")).strip()
            label = str(opt.get("label", "")).strip() or key
            row = QuestionOption.objects.create(
                question_version=version,
                key=key,
                is_correct=(key == correct_key),
                sort_order=i,
            )
            QuestionOptionTranslation.objects.create(
                option=row, locale=locale, label=label
            )
        question.current_version = version
        question.save(update_fields=["current_version", "updated_at"])
        if topic_id:
            topic = Topic.objects.filter(pk=topic_id).first()
            if topic:
                QuestionTopic.objects.get_or_create(question=question, topic=topic)
        AuditService.record(
            action="question_created",
            actor_user=actor,
            target_type="question",
            target_id=str(question.id),
            metadata={"type": question_type, "difficulty": difficulty},
        )
        return question

    @classmethod
    @transaction.atomic
    def edit_question_draft(
        cls,
        *,
        actor,
        question: Question,
        stem: str,
        explanation: str = "",
        difficulty: str | None = None,
        options: list[dict] | None = None,
        correct_key: str | None = None,
    ) -> Question:
        cls._require_edit(actor, question)
        # Published meaning changes must create a new version (docs/09 §8).
        create_new_version = question.editorial_state == EditorialState.PUBLISHED
        if create_new_version and not AccessControlService.has_permission(
            actor, "questions.edit"
        ):
            raise PermissionError("Permission denied.")
        locale = question.primary_locale or LocaleCode.EN
        if create_new_version:
            next_no = (question.versions.order_by("-version_no").first().version_no) + 1
            version = QuestionVersion.objects.create(
                question=question,
                version_no=next_no,
                correct_answer_spec={"key": correct_key}
                if correct_key
                else dict(question.current_version.correct_answer_spec or {}),
                created_by=actor,
            )
            QuestionVersionTranslation.objects.create(
                version=version,
                locale=locale,
                stem=(stem or "").strip(),
                explanation=explanation or "",
            )
            opts = options or []
            if not opts and question.current_version:
                for old in question.current_version.options.all().order_by("sort_order"):
                    label = old.translations.filter(locale=locale).first()
                    opts.append(
                        {
                            "key": old.key,
                            "label": getattr(label, "label", old.key),
                        }
                    )
                    if correct_key is None and old.is_correct:
                        correct_key = old.key
            for i, opt in enumerate(opts):
                key = str(opt.get("key", "")).strip()
                row = QuestionOption.objects.create(
                    question_version=version,
                    key=key,
                    is_correct=(key == correct_key),
                    sort_order=i,
                )
                QuestionOptionTranslation.objects.create(
                    option=row,
                    locale=locale,
                    label=str(opt.get("label", key)).strip() or key,
                )
            if correct_key:
                version.correct_answer_spec = {"key": correct_key}
                version.save(update_fields=["correct_answer_spec"])
            question.current_version = version
            question.updated_by = actor
            question.version_number = int(question.version_number or 1) + 1
            question.save(
                update_fields=[
                    "current_version",
                    "updated_by",
                    "version_number",
                    "updated_at",
                ]
            )
        else:
            version = question.current_version
            if version is None:
                raise QuestionStaffError("Question has no version.", code="validation")
            tr = version.translations.filter(locale=locale).first()
            if tr:
                tr.stem = (stem or "").strip()
                tr.explanation = explanation or ""
                tr.save(update_fields=["stem", "explanation"])
            if difficulty:
                question.difficulty = difficulty
            if options and correct_key:
                version.options.all().delete()
                for i, opt in enumerate(options):
                    key = str(opt.get("key", "")).strip()
                    row = QuestionOption.objects.create(
                        question_version=version,
                        key=key,
                        is_correct=(key == correct_key),
                        sort_order=i,
                    )
                    QuestionOptionTranslation.objects.create(
                        option=row,
                        locale=locale,
                        label=str(opt.get("label", key)).strip() or key,
                    )
                version.correct_answer_spec = {"key": correct_key}
                version.save(update_fields=["correct_answer_spec"])
            question.updated_by = actor
            question.save(update_fields=["difficulty", "updated_by", "updated_at"])
        AuditService.record(
            action="question_edited",
            actor_user=actor,
            target_type="question",
            target_id=str(question.id),
            metadata={"new_version": create_new_version},
        )
        return question

    @classmethod
    def workflow(cls, *, actor, question_id, action: str, notes: str = ""):
        question = cls.get_question(actor, question_id)
        if action == "publish":
            blockers = cls.publish_blockers(question)
            if blockers:
                raise QuestionStaffError(
                    "Cannot publish: " + " ".join(blockers),
                    code="publish_blocked",
                )
        return EditorialWorkflowService.transition(
            obj=question,
            action=action,
            actor=actor,
            domain="questions",
            target_type="question",
            notes=notes,
        )

    @classmethod
    def publish_blockers(cls, question: Question) -> list[str]:
        """
        Publishing safety: structure + answer key + type valid; no blocking
        errors; review satisfied. Blueprint mapping must be present and valid
        when the question is offered as exam-eligible.
        """
        return cls.validation_problems(question)

    @classmethod
    @transaction.atomic
    def update_classification(
        cls,
        *,
        actor,
        question: Question,
        content_subject: str = "",
        content_topic: str = "",
        cognitive_level: str | None = None,
        difficulty: str | None = None,
        blueprint_category_id=None,
        blueprint_competency_id=None,
        scenario_based: bool | None = None,
        needs_review: bool | None = None,
        classification_origin: str | None = None,
    ) -> Question:
        cls._require_edit(actor, question)
        if cognitive_level and cognitive_level not in {c.value for c in CognitiveLevel}:
            raise QuestionStaffError("Unknown cognitive level.", code="validation")
        if difficulty and difficulty not in {d.value for d in DifficultyLevel}:
            raise QuestionStaffError("Unknown difficulty.", code="validation")
        category = None
        if blueprint_category_id:
            category = BlueprintCategory.objects.filter(pk=blueprint_category_id).first()
            if category is None:
                raise QuestionStaffError("Unknown blueprint category.", code="validation")
        competency = None
        if blueprint_competency_id:
            competency = BlueprintCompetency.objects.filter(
                pk=blueprint_competency_id
            ).first()
            if competency is None:
                raise QuestionStaffError(
                    "Unknown blueprint competency.", code="validation"
                )
            if category is not None and competency.category_id != category.id:
                raise QuestionStaffError(
                    "Competency does not belong to the selected category.",
                    code="validation",
                )
        question.content_subject = (content_subject or "").strip()
        question.content_topic = (content_topic or "").strip()
        question.cognitive_level = cognitive_level or None
        if difficulty is not None:
            question.difficulty = difficulty or None
        question.blueprint_category = category
        question.blueprint_competency = competency
        if scenario_based is not None:
            question.scenario_based = bool(scenario_based)
        auto_review = question.cognitive_level is None or question.blueprint_category_id is None
        if needs_review is None:
            question.needs_review = auto_review
        else:
            question.needs_review = bool(needs_review) or auto_review
        if classification_origin is not None:
            if classification_origin not in {
                "",
                ClassificationOrigin.SUGGESTED,
                ClassificationOrigin.APPROVED,
            }:
                raise QuestionStaffError("Unknown classification origin.", code="validation")
            question.classification_origin = classification_origin
        question.updated_by = actor
        question.save()
        AuditService.record(
            action="question_classification_updated",
            actor_user=actor,
            target_type="question",
            target_id=str(question.id),
            metadata={
                "subject": question.content_subject,
                "topic": question.content_topic,
                "cognitive_level": question.cognitive_level or "",
                "needs_review": question.needs_review,
            },
        )
        return question

    @classmethod
    @transaction.atomic
    def update_review_state(cls, *, actor, question: Question, needs_review: bool) -> Question:
        cls._require_edit(actor, question)
        if not needs_review:
            leftover = [
                p
                for p in cls.validation_problems(question)
                if p != "Flagged for admin review."
            ]
            if leftover:
                raise QuestionStaffError(
                    "Cannot clear review while blocking problems remain: "
                    + " ".join(leftover),
                    code="validation",
                )
        question.needs_review = bool(needs_review)
        question.updated_by = actor
        question.save(update_fields=["needs_review", "updated_by", "updated_at"])
        AuditService.record(
            action="question_review_updated",
            actor_user=actor,
            target_type="question",
            target_id=str(question.id),
            metadata={"needs_review": question.needs_review},
        )
        return question

    @classmethod
    def queue_counts(cls, actor) -> dict:
        cls._require_view(actor)
        qs = cls._scope(actor, Question.objects.all())
        return {
            "total": qs.count(),
            "draft": qs.filter(editorial_state=EditorialState.DRAFT).count(),
            "review": qs.filter(editorial_state=EditorialState.REVIEW).count(),
            "approved": qs.filter(editorial_state=EditorialState.APPROVED).count(),
            "published": qs.filter(editorial_state=EditorialState.PUBLISHED).count(),
            "archived": qs.filter(editorial_state=EditorialState.ARCHIVED).count(),
            "needs_review": qs.filter(needs_review=True).count(),
            "suggested": qs.filter(
                classification_origin=ClassificationOrigin.SUGGESTED
            ).count(),
        }

    @classmethod
    def bank_dashboard_counts(cls, actor=None) -> dict:
        """High-level question-bank counts from the database (no estimated analytics)."""
        from django.db.models import Count, Q

        qs = Question.objects.all()
        if actor is not None:
            cls._require_view(actor)
            qs = cls._scope(actor, qs)
        type_rows = qs.values("question_type").annotate(n=Count("id"))
        subject_rows = (
            qs.exclude(content_subject="")
            .values("content_subject")
            .annotate(n=Count("id"))
            .order_by("-n", "content_subject")
        )
        blueprint_rows = (
            qs.values("blueprint_category__name")
            .annotate(n=Count("id"))
            .order_by("-n")
        )
        return {
            "total": qs.count(),
            "draft": qs.filter(editorial_state=EditorialState.DRAFT).count(),
            "needs_review": qs.filter(needs_review=True).count(),
            "submitted": qs.filter(editorial_state=EditorialState.REVIEW).count(),
            "approved": qs.filter(editorial_state=EditorialState.APPROVED).count(),
            "published": qs.filter(editorial_state=EditorialState.PUBLISHED).count(),
            "invalid": qs.filter(current_version__isnull=True).count(),
            "unclassified": qs.filter(
                Q(blueprint_category_id__isnull=True)
                | Q(cognitive_level__isnull=True)
                | Q(cognitive_level="")
            ).count(),
            "suggested": qs.filter(
                classification_origin=ClassificationOrigin.SUGGESTED
            ).count(),
            "by_type": {
                row["question_type"] or "unspecified": row["n"] for row in type_rows
            },
            "by_subject": {
                row["content_subject"]: row["n"] for row in subject_rows[:20]
            },
            "by_blueprint": {
                row["blueprint_category__name"] or "Unclassified": row["n"]
                for row in blueprint_rows
            },
        }

    @classmethod
    def structure_problems(cls, question: Question) -> list[str]:
        """Answer structure / key only — classification gaps are review work, not submit blockers."""
        return [
            p
            for p in cls.validation_problems(question)
            if p
            not in {
                "No blueprint category assigned (unclassified).",
                "No cognitive level assigned (unclassified).",
                "Flagged for admin review.",
            }
        ]

    @classmethod
    def bulk_submit_review(cls, *, actor, question_ids: list) -> BulkActionResult:
        return cls._bulk_workflow(
            actor=actor,
            question_ids=question_ids,
            action="submit_review",
            eligible_state=EditorialState.DRAFT,
            extra_check=cls._submit_eligibility,
        )

    @classmethod
    def bulk_approve(cls, *, actor, question_ids: list) -> BulkActionResult:
        return cls._bulk_workflow(
            actor=actor,
            question_ids=question_ids,
            action="approve",
            eligible_state=EditorialState.REVIEW,
        )

    @classmethod
    def bulk_publish(cls, *, actor, question_ids: list) -> BulkActionResult:
        return cls._bulk_workflow(
            actor=actor,
            question_ids=question_ids,
            action="publish",
            eligible_state=EditorialState.APPROVED,
            extra_check=cls._publish_eligibility,
        )

    @classmethod
    @transaction.atomic
    def bulk_classify(
        cls,
        *,
        actor,
        question_ids: list,
        content_subject: str = "",
        content_topic: str = "",
        cognitive_level: str | None = None,
        blueprint_category_id=None,
        blueprint_competency_id=None,
    ) -> BulkActionResult:
        if not AccessControlService.has_permission(actor, "questions.edit"):
            raise PermissionError("Permission denied.")
        provided = any(
            [
                (content_subject or "").strip(),
                (content_topic or "").strip(),
                cognitive_level,
                blueprint_category_id,
                blueprint_competency_id,
            ]
        )
        if not provided:
            raise QuestionStaffError(
                "Select at least one classification field to apply.",
                code="validation",
            )
        ids = cls._normalize_ids(question_ids)
        result = BulkActionResult(action="classify", selected=len(ids), succeeded=0, failed=0)
        if blueprint_category_id and blueprint_competency_id:
            competency = BlueprintCompetency.objects.filter(
                pk=blueprint_competency_id
            ).first()
            if competency is None:
                raise QuestionStaffError(
                    "Unknown blueprint competency.", code="validation"
                )
            if str(competency.category_id) != str(blueprint_category_id):
                raise QuestionStaffError(
                    "Competency does not belong to the selected category.",
                    code="validation",
                )
        for qid in ids:
            question = Question.objects.filter(pk=qid).first()
            if question is None:
                result.failed += 1
                result.failures.append(
                    BulkItemFailure(str(qid), "", "Question not found.")
                )
                continue
            if is_march_2025_protected(question):
                result.failed += 1
                result.failures.append(
                    BulkItemFailure(
                        str(question.id),
                        question.question_code or "",
                        MARCH_2025_BULK_REASON,
                    )
                )
                continue
            try:
                cls._require_edit(actor, question)
                next_category = blueprint_category_id or question.blueprint_category_id
                next_competency = (
                    blueprint_competency_id or question.blueprint_competency_id
                )
                if (
                    blueprint_category_id
                    and str(blueprint_category_id)
                    != str(question.blueprint_category_id or "")
                    and not blueprint_competency_id
                ):
                    next_competency = None
                cls.update_classification(
                    actor=actor,
                    question=question,
                    content_subject=content_subject or question.content_subject,
                    content_topic=content_topic or question.content_topic,
                    cognitive_level=cognitive_level or question.cognitive_level,
                    blueprint_category_id=next_category,
                    blueprint_competency_id=next_competency,
                    needs_review=question.needs_review,
                    classification_origin=ClassificationOrigin.APPROVED,
                )
                result.succeeded += 1
                result.successes.append(question.question_code or str(question.id))
            except (QuestionStaffError, PermissionError) as exc:
                result.failed += 1
                result.failures.append(
                    BulkItemFailure(
                        str(question.id),
                        question.question_code or "",
                        str(exc),
                    )
                )
        AuditService.record(
            action="questions_bulk_classified",
            actor_user=actor,
            target_type="question_bulk",
            target_id="classify",
            metadata={
                "selected": result.selected,
                "succeeded": result.succeeded,
                "failed": result.failed,
            },
        )
        return result

    @classmethod
    def apply_suggestion(cls, *, actor, question: Question, fields: list[str]) -> Question:
        suggestion = BlueprintSuggestionService.suggest(question)
        if not suggestion.confident:
            raise QuestionStaffError("No confident suggestion.", code="validation")
        if is_march_2025_protected(question):
            raise QuestionStaffError(MARCH_2025_BULK_REASON, code="protected")
        kwargs = {
            "content_subject": question.content_subject,
            "content_topic": question.content_topic,
            "cognitive_level": question.cognitive_level,
            "blueprint_category_id": question.blueprint_category_id,
            "blueprint_competency_id": question.blueprint_competency_id,
            "needs_review": True,
            "classification_origin": ClassificationOrigin.SUGGESTED,
        }
        wanted = {f.strip() for f in fields if f.strip()}
        skipped = []
        if "category" in wanted and suggestion.category_id:
            if question.blueprint_category_id:
                skipped.append("category")
            else:
                kwargs["blueprint_category_id"] = suggestion.category_id
                kwargs["blueprint_competency_id"] = None
        if "cognitive" in wanted and suggestion.cognitive_level:
            if question.cognitive_level:
                skipped.append("cognitive")
            else:
                kwargs["cognitive_level"] = suggestion.cognitive_level
        if skipped and len(skipped) == len(wanted):
            raise QuestionStaffError(
                "Existing classification was kept. Suggestions never overwrite explicit values.",
                code="validation",
            )
        return cls.update_classification(actor=actor, question=question, **kwargs)

    @classmethod
    def dismiss_suggestion(cls, *, actor, question: Question) -> None:
        cls._require_edit(actor, question)
        if is_march_2025_protected(question):
            raise QuestionStaffError(MARCH_2025_BULK_REASON, code="protected")
        from apps.assessment.services.blueprint_suggest import (
            DISMISS_SUGGESTION_ACTION,
        )

        AuditService.record(
            action=DISMISS_SUGGESTION_ACTION,
            actor_user=actor,
            target_type="question",
            target_id=str(question.id),
            metadata={"reason": "staff rejected suggestion (not applied)"},
        )

    @classmethod
    def dismiss_duplicate(cls, *, actor, question: Question, other_id) -> None:
        cls._require_edit(actor, question)
        other = Question.objects.filter(pk=other_id).first()
        if other is None:
            raise QuestionStaffError("Not found.", code="not_found")
        QuestionDuplicateService.dismiss(actor=actor, question=question, other=other)

    @classmethod
    def _bulk_workflow(
        cls,
        *,
        actor,
        question_ids: list,
        action: str,
        eligible_state: str,
        extra_check=None,
    ) -> BulkActionResult:
        ids = cls._normalize_ids(question_ids)
        result = BulkActionResult(action=action, selected=len(ids), succeeded=0, failed=0)
        for qid in ids:
            question = Question.objects.filter(pk=qid).first()
            if question is None:
                result.failed += 1
                result.failures.append(
                    BulkItemFailure(str(qid), "", "Question not found.")
                )
                continue
            if is_march_2025_protected(question):
                result.failed += 1
                result.failures.append(
                    BulkItemFailure(
                        str(question.id),
                        question.question_code or "",
                        MARCH_2025_BULK_REASON,
                    )
                )
                continue
            if question.editorial_state != eligible_state:
                result.failed += 1
                result.failures.append(
                    BulkItemFailure(
                        str(question.id),
                        question.question_code or "",
                        f"Not eligible: state is {question.editorial_state}.",
                    )
                )
                continue
            if extra_check:
                blocker = extra_check(question)
                if blocker:
                    result.failed += 1
                    result.failures.append(
                        BulkItemFailure(
                            str(question.id),
                            question.question_code or "",
                            blocker,
                        )
                    )
                    continue
            try:
                cls.workflow(actor=actor, question_id=question.id, action=action)
                result.succeeded += 1
                result.successes.append(question.question_code or str(question.id))
            except (QuestionStaffError, PermissionError, EditorialWorkflowError) as exc:
                result.failed += 1
                result.failures.append(
                    BulkItemFailure(
                        str(question.id),
                        question.question_code or "",
                        str(exc),
                    )
                )
        AuditService.record(
            action=f"questions_bulk_{action}",
            actor_user=actor,
            target_type="question_bulk",
            target_id=action,
            metadata={
                "selected": result.selected,
                "succeeded": result.succeeded,
                "failed": result.failed,
            },
        )
        return result

    @classmethod
    def _submit_eligibility(cls, question: Question) -> str:
        problems = cls.structure_problems(question)
        if problems:
            return "Validation failed: " + " ".join(problems)
        return ""

    @classmethod
    def _publish_eligibility(cls, question: Question) -> str:
        problems = cls.publish_blockers(question)
        if problems:
            return "Cannot publish: " + " ".join(problems)
        return ""

    @staticmethod
    def _normalize_ids(question_ids: list) -> list:
        seen: set[str] = set()
        out: list[str] = []
        for raw in question_ids or []:
            value = str(raw or "").strip()
            if not value or value in seen:
                continue
            seen.add(value)
            out.append(value)
        return out

    @staticmethod
    def _parse_date(raw: str):
        from datetime import date

        text = (raw or "").strip()
        if not text:
            return None
        try:
            return date.fromisoformat(text)
        except ValueError:
            return None

    @classmethod
    def list_error_reports(cls, actor, *, status: str = "", page=1):
        if not (
            AccessControlService.has_permission(actor, "questions.view_error_reports")
            or AccessControlService.has_permission(
                actor, "questions.view_own_error_reports"
            )
        ):
            raise PermissionError("Permission denied.")
        qs = QuestionErrorReport.objects.select_related("question", "reporter").order_by(
            "-created_at"
        )
        if status:
            qs = qs.filter(status=status)
        if not AccessControlService.has_permission(
            actor, "questions.view_error_reports"
        ):
            qs = qs.filter(question__created_by=actor)
        return paginate_queryset(qs, page=page)

    @classmethod
    @transaction.atomic
    def resolve_error_report(cls, *, actor, report_id, status: str, notes: str = ""):
        if not AccessControlService.has_permission(
            actor, "questions.resolve_error_reports"
        ):
            raise PermissionError("Permission denied.")
        if status not in {
            QuestionErrorReportStatus.TRIAGED,
            QuestionErrorReportStatus.RESOLVED,
            QuestionErrorReportStatus.DISMISSED,
        }:
            raise QuestionStaffError("Invalid status.", code="validation")
        try:
            report = QuestionErrorReport.objects.select_for_update().get(pk=report_id)
        except QuestionErrorReport.DoesNotExist as exc:
            raise QuestionStaffError("Not found.", code="not_found") from exc
        report.status = status
        report.triage_notes = notes or ""
        report.save(update_fields=["status", "triage_notes", "updated_at"])
        AuditService.record(
            action="question_error_report_updated",
            actor_user=actor,
            target_type="question_error_report",
            target_id=str(report.id),
            metadata={"status": status},
        )
        return report

    @classmethod
    def stem_for(cls, question: Question) -> str:
        version = question.current_version
        if not version:
            return str(question.pk)
        tr = version.translations.first()
        return getattr(tr, "stem", None) or str(question.pk)

    @classmethod
    def validation_problems(cls, question: Question) -> list[str]:
        """
        Surface structural/classification problems for an admin (never students).

        Foundation checks: TRUE/FALSE needs exactly 5 statements + 5 truth values;
        BEST_ANSWER needs exactly 4 options and exactly one correct; plus
        classification gaps (blueprint category / cognitive level).
        """
        problems: list[str] = []
        version = question.current_version
        if version is None:
            return ["Question has no current version."]
        options = list(version.options.all())
        spec = version.correct_answer_spec or {}
        if question.question_type == QuestionType.TRUE_FALSE:
            if len(options) != 5:
                problems.append(
                    f"TRUE/FALSE must have exactly 5 statements (has {len(options)})."
                )
            truths = spec.get("truths") if isinstance(spec, dict) else None
            if not isinstance(truths, dict) or len(truths) != 5:
                problems.append("TRUE/FALSE must define 5 statement truth values.")
        elif question.question_type == QuestionType.BEST_ANSWER:
            if len(options) != 4:
                problems.append(
                    f"BEST_ANSWER must have exactly 4 options (has {len(options)})."
                )
            correct = [o for o in options if o.is_correct]
            if len(correct) != 1:
                problems.append(
                    f"BEST_ANSWER must have exactly one correct option (has {len(correct)})."
                )
        if question.blueprint_category_id is None:
            problems.append("No blueprint category assigned (unclassified).")
        if not question.cognitive_level:
            problems.append("No cognitive level assigned (unclassified).")
        if question.needs_review:
            problems.append("Flagged for admin review.")
        return problems

    @classmethod
    def can_view_provenance(cls, actor) -> bool:
        """Provenance is admin/super-admin only (never students, never authors)."""
        return AccessControlService.has_any_role(
            actor, {RoleCode.ADMIN, RoleCode.SUPER_ADMIN}
        ) or AccessControlService.is_super_admin(actor)

    @classmethod
    def admin_source_view(cls, actor, question: Question) -> dict:
        """
        ADMIN-ONLY provenance snapshot. Callers must be authorized staff; this is
        never included in any student-facing payload.
        """
        cls._require_view(actor)
        return {
            "source_type": question.source_type,
            "source_name": question.source_name,
            "source_page": question.source_page,
            "source_reference": question.source_reference,
            "question_code": question.question_code or "",
        }

    @classmethod
    def provenance_for(cls, actor, question: Question) -> dict | None:
        """Return provenance only for admin/super-admin; otherwise None."""
        cls._require_view(actor)
        if not cls.can_view_provenance(actor):
            return None
        return cls.admin_source_view(actor, question)

    @classmethod
    def staff_answer_key(cls, actor, question: Question) -> dict:
        """Staff-only answer key + options. Never sent to student presentation."""
        cls._require_view(actor)
        version = question.current_version
        if version is None:
            return {"options": [], "explanation": "", "spec": {}, "scenario": ""}
        locale = question.primary_locale or LocaleCode.EN
        tr = version.translations.filter(locale=locale).first() or version.translations.first()
        options = []
        for opt in version.options.all().order_by("sort_order"):
            label = opt.translations.filter(locale=locale).first()
            if label is None:
                label = opt.translations.first()
            options.append(
                {
                    "key": opt.key,
                    "label": getattr(label, "label", opt.key),
                    "is_correct": bool(opt.is_correct),
                }
            )
        return {
            "options": options,
            "explanation": getattr(tr, "explanation", "") if tr else "",
            "spec": dict(version.correct_answer_spec or {}),
            "scenario": version.clinical_scenario_body or "",
        }

    # ---- Excel import (bulk foundation) ------------------------------------

    @classmethod
    def import_preview(cls, actor, file_or_path):
        if not AccessControlService.has_permission(actor, "questions.import"):
            raise PermissionError("Permission denied.")
        return QuestionImportService.preview(file_or_path)

    @classmethod
    def import_commit(cls, actor, file_or_path, *, filename: str = ""):
        if not AccessControlService.has_permission(actor, "questions.import"):
            raise PermissionError("Permission denied.")
        filename = filename or getattr(file_or_path, "name", "") or ""
        report = QuestionImportService.commit(
            file_or_path, actor=actor, filename=filename
        )
        AuditService.record(
            action="questions_imported",
            actor_user=actor,
            target_type="question_import",
            target_id=report.batch_id or "bulk",
            metadata={
                "created": report.created,
                "skipped_duplicate": report.skipped_duplicate,
                "needs_review": report.needs_review,
                "filename": filename,
            },
        )
        return report

    IMPORT_STASH_SESSION_KEY = "question_import_stash"

    @classmethod
    def stash_import_upload(cls, actor, upload) -> dict:
        if not AccessControlService.has_permission(actor, "questions.import"):
            raise PermissionError("Permission denied.")
        path, filename = stash_workbook(upload)
        return {
            "path": path,
            "filename": filename,
            "user_id": str(actor.id),
        }

    @classmethod
    def resolve_import_source(cls, actor, upload=None, stash: dict | None = None):
        if not AccessControlService.has_permission(actor, "questions.import"):
            raise PermissionError("Permission denied.")
        if upload:
            return upload, getattr(upload, "name", "") or ""
        if not stash or str(stash.get("user_id") or "") != str(actor.id):
            return None, ""
        path = stash.get("path") or ""
        if not is_valid_stash_path(path) or not os.path.exists(path):
            return None, ""
        return path, stash.get("filename") or ""

    @classmethod
    def clear_import_stash(cls, stash: dict | None) -> None:
        if not stash:
            return
        clear_stash(stash.get("path") or "")

    @classmethod
    def list_import_batches(cls, actor, *, page=1):
        if not AccessControlService.has_permission(actor, "questions.import"):
            raise PermissionError("Permission denied.")
        qs = QuestionImportBatch.objects.select_related("created_by").order_by(
            "-created_at"
        )
        return paginate_queryset(qs, page=page)

    @classmethod
    def get_import_batch(cls, actor, batch_id) -> QuestionImportBatch:
        if not AccessControlService.has_permission(actor, "questions.import"):
            raise PermissionError("Permission denied.")
        try:
            return QuestionImportBatch.objects.select_related("created_by").get(
                pk=batch_id
            )
        except QuestionImportBatch.DoesNotExist as exc:
            raise QuestionStaffError("Not found.", code="not_found") from exc

    @classmethod
    def example_workbook(cls, actor) -> tuple[str, bytes]:
        if not AccessControlService.has_permission(actor, "questions.import"):
            raise PermissionError("Permission denied.")
        return TEMPLATE_FILENAME, build_example_workbook()

    @classmethod
    def author_workbook(cls, actor) -> tuple[str, bytes]:
        if not AccessControlService.has_permission(actor, "questions.import"):
            raise PermissionError("Permission denied.")
        return AUTHOR_TEMPLATE_FILENAME, build_author_workbook()

    @classmethod
    def _require_view(cls, actor):
        if AccessControlService.has_permission(actor, "questions.view_unpublished"):
            return
        if AccessControlService.has_permission(actor, "questions.create"):
            return
        raise PermissionError("Permission denied.")

    @classmethod
    def _require_edit(cls, actor, question: Question):
        if AccessControlService.has_permission(actor, "questions.edit"):
            return
        if AccessControlService.has_permission(actor, "questions.edit_own"):
            if (
                question.created_by_id == actor.id
                and question.editorial_state
                in {EditorialState.DRAFT, EditorialState.REVIEW}
            ):
                # Authors edit draft/returned; returned is Draft after reject.
                if question.editorial_state == EditorialState.DRAFT:
                    return
        raise PermissionError("Permission denied.")

    @classmethod
    def _can_view(cls, actor, question: Question) -> bool:
        if AccessControlService.has_permission(actor, "questions.view_unpublished"):
            return True
        if question.created_by_id == actor.id:
            return True
        return (
            question.editorial_state == EditorialState.PUBLISHED
            and not question.is_archived
        )

    @classmethod
    def _scope(cls, actor, qs):
        if AccessControlService.has_permission(actor, "questions.view_unpublished"):
            return qs
        return qs.filter(
            Q(created_by=actor)
            | Q(editorial_state=EditorialState.PUBLISHED, is_archived=False)
        )
