"""
Excel question import (UNIT-11 foundation + UNIT-12 content review).

Pipeline:
  UPLOAD → PARSE → STRUCTURAL VALIDATION → CONTENT VALIDATION →
  BLUEPRINT VALIDATION → PREVIEW → ADMIN REVIEW → ADMIN CONFIRM →
  TRANSACTIONAL COMMIT → POST-IMPORT REPORT

Hard rules:
  * A structurally malformed workbook (missing/duplicate required columns) yields
    NO import at all.
  * Commit is all-or-nothing inside a single transaction; if ANY row is invalid,
    nothing is written (no partial import).
  * Idempotency is keyed on the stable ``question_code``. A code already present
    in the bank is reported as a duplicate and SKIPPED — never silently
    overwritten (published rows are especially protected).
  * The importer never scores and never trusts client correctness — the server
    stores the answer key from the workbook.
  * Uncertain blueprint mapping is imported as DRAFT + needs_review; it is never
    silently substituted. Invalid supplied mappings reject the workbook.
  * UNIT-11 column contract (option_a–e + correct_answer) is preserved; extra
    columns are optional aliases.

The March 2025 exam PDF is not parsed here; staff prepare workbooks, then this
service loads them.
"""
from __future__ import annotations

import os
import tempfile
import uuid
from dataclasses import dataclass, field

from django.db import transaction
from django.utils import timezone

from apps.assessment.models import (
    BlueprintCategory,
    BlueprintCompetency,
    ExamBlueprint,
    Question,
    QuestionImportBatch,
    QuestionOption,
    QuestionOptionTranslation,
    QuestionVersion,
    QuestionVersionTranslation,
)
from apps.assessment.services.answers import coerce_bool
from apps.assessment.taxonomy import canonicalize_subject, canonicalize_topic
from apps.common.choices import (
    CognitiveLevel,
    DifficultyLevel,
    EditorialState,
    LocaleCode,
    QuestionSourceType,
    QuestionType,
)

REQUIRED_COLUMNS = (
    "question_code",
    "question_type",
    "question_text",
    "scenario",
    "option_a",
    "option_b",
    "option_c",
    "option_d",
    "option_e",
    "correct_answer",
    "explanation",
    "blueprint_category",
    "blueprint_competency",
    "subject",
    "topic",
    "cognitive_level",
    "difficulty",
    "scenario_based",
    "source_name",
    "source_page",
    "source_reference",
    "status",
)

# Optional aliases / UNIT-12 extras. Presence is not required; UNIT-11 workbooks
# remain valid. Values map onto the required contract without replacing it.
OPTIONAL_COLUMNS = (
    "statement_a",
    "statement_b",
    "statement_c",
    "statement_d",
    "statement_e",
    "truth_a",
    "truth_b",
    "truth_c",
    "truth_d",
    "truth_e",
    "correct_option",
    "content_subject",
    "content_topic",
    "source_type",
    "needs_review",
)

# Accepted when present; not part of the generated UNIT-11/12 templates.
COMPAT_COLUMNS = (
    "notes",
    "stem",
    "type",
    "page",
    "reference",
)

# Map alternate headers onto the UNIT-11 contract when the canonical name is absent.
HEADER_ALIASES = {
    "stem": "question_text",
    "type": "question_type",
    "page": "source_page",
    "reference": "source_reference",
}

PREVIEW_DISPLAY_LIMIT = 50
ERROR_DISPLAY_LIMIT = 100
BULK_INSERT_BATCH = 100
STASH_PREFIX = "nursilo-qimport-"

_TF_ALIASES = {"true_false", "true/false", "truefalse", "tf", "true false"}
_BA_ALIASES = {"best_answer", "best answer", "bestanswer", "ba", "single_best", "best"}

_SOURCE_TYPE_ALIASES = {
    "official_exam": QuestionSourceType.OFFICIAL_EXAM,
    "official exam": QuestionSourceType.OFFICIAL_EXAM,
    "blueprint": QuestionSourceType.BLUEPRINT,
    "textbook": QuestionSourceType.TEXTBOOK,
    "staff_created": QuestionSourceType.STAFF_CREATED,
    "staff created": QuestionSourceType.STAFF_CREATED,
    "imported": QuestionSourceType.IMPORTED,
    "other": QuestionSourceType.OTHER,
}

_COGNITIVE_ALIASES = {
    "recall": CognitiveLevel.RECALL,
    "understanding": CognitiveLevel.UNDERSTANDING,
    "application": CognitiveLevel.APPLICATION,
}

STATUS_VALID = "valid"
STATUS_INVALID = "invalid"
STATUS_DUPLICATE = "duplicate"

_IMPORTABLE_STATES = {
    EditorialState.DRAFT,
    EditorialState.REVIEW,
    EditorialState.APPROVED,
    EditorialState.PUBLISHED,
}


class ImportStructureError(Exception):
    """Workbook cannot be parsed (missing/duplicate columns, unreadable)."""


class ImportCommitError(Exception):
    """Commit refused (invalid rows present) — no partial import performed."""


@dataclass
class RowResult:
    index: int  # 1-based data row number (excludes header)
    question_code: str
    question_type: str
    status: str
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    data: dict = field(default_factory=dict)


@dataclass
class ImportPreview:
    total: int = 0
    valid: int = 0
    invalid: int = 0
    duplicate: int = 0
    needs_review: int = 0
    type_counts: dict = field(default_factory=dict)
    blueprint_counts: dict = field(default_factory=dict)
    cognitive_counts: dict = field(default_factory=dict)
    subject_counts: dict = field(default_factory=dict)
    source_counts: dict = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    rows: list[RowResult] = field(default_factory=list)

    @property
    def has_invalid(self) -> bool:
        return self.invalid > 0

    @property
    def importable(self) -> bool:
        return not self.has_invalid and self.valid > 0

    @property
    def attention_rows(self) -> list[RowResult]:
        return [r for r in self.rows if r.status != STATUS_VALID or r.warnings]

    @property
    def display_rows(self) -> list[RowResult]:
        attention = self.attention_rows
        if len(attention) >= PREVIEW_DISPLAY_LIMIT:
            return attention[:PREVIEW_DISPLAY_LIMIT]
        chosen = list(attention)
        seen = {id(r) for r in chosen}
        for row in self.rows:
            if id(row) in seen:
                continue
            chosen.append(row)
            if len(chosen) >= PREVIEW_DISPLAY_LIMIT:
                break
        return chosen

    @property
    def hidden_row_count(self) -> int:
        return max(0, len(self.rows) - len(self.display_rows))

    @property
    def display_errors(self) -> list[str]:
        return self.errors[:ERROR_DISPLAY_LIMIT]

    @property
    def hidden_error_count(self) -> int:
        return max(0, len(self.errors) - ERROR_DISPLAY_LIMIT)

    @property
    def display_warnings(self) -> list[str]:
        return self.warnings[:ERROR_DISPLAY_LIMIT]

    @property
    def hidden_warning_count(self) -> int:
        return max(0, len(self.warnings) - ERROR_DISPLAY_LIMIT)


@dataclass
class ImportCommitReport:
    created: int = 0
    skipped_duplicate: int = 0
    needs_review: int = 0
    created_codes: list[str] = field(default_factory=list)
    skipped_codes: list[str] = field(default_factory=list)
    batch_id: str | None = None
    batch_status: str = QuestionImportBatch.STATUS_COMMITTED


class QuestionImportService:
    # ---- PARSE -------------------------------------------------------------

    @classmethod
    def parse(cls, file_or_path) -> list[dict]:
        """Read a workbook into a list of row dicts keyed by normalized headers."""
        try:
            from openpyxl import load_workbook
        except ImportError as exc:  # pragma: no cover
            raise ImportStructureError(
                "openpyxl is required to import questions."
            ) from exc
        try:
            wb = load_workbook(filename=file_or_path, read_only=True, data_only=True)
        except Exception as exc:
            raise ImportStructureError(f"Workbook could not be read: {exc}") from exc

        ws = wb.active
        rows_iter = ws.iter_rows(values_only=True)
        try:
            header = next(rows_iter)
        except StopIteration as extra:
            wb.close()
            raise ImportStructureError("Workbook is empty.") from extra

        norm_header = [
            (str(h).strip().lower() if h is not None else "") for h in header
        ]
        seen: dict[str, int] = {}
        for name in norm_header:
            if not name:
                continue
            seen[name] = seen.get(name, 0) + 1
        duplicates = sorted(n for n, c in seen.items() if c > 1 and n in REQUIRED_COLUMNS)
        if duplicates:
            wb.close()
            raise ImportStructureError(
                "Duplicate columns: " + ", ".join(duplicates)
            )
        index_of = {name: i for i, name in enumerate(norm_header) if name}
        for alias, target in HEADER_ALIASES.items():
            if target not in index_of and alias in index_of:
                index_of[target] = index_of[alias]
        missing = [c for c in REQUIRED_COLUMNS if c not in index_of]
        if missing:
            wb.close()
            raise ImportStructureError("Missing columns: " + ", ".join(missing))

        wanted = list(REQUIRED_COLUMNS) + [
            c
            for c in list(OPTIONAL_COLUMNS) + list(COMPAT_COLUMNS)
            if c in index_of and c not in REQUIRED_COLUMNS
        ]
        rows: list[dict] = []
        for raw in rows_iter:
            if raw is None:
                continue
            values = list(raw)
            record = {}
            non_empty = False
            for col in wanted:
                idx = index_of[col]
                value = values[idx] if idx < len(values) else None
                text = "" if value is None else str(value).strip()
                record[col] = text
                if text:
                    non_empty = True
            if non_empty:
                cls._apply_aliases(record)
                rows.append(record)
        wb.close()
        return rows

    @staticmethod
    def _apply_aliases(record: dict) -> None:
        """Map UNIT-12 optional columns onto the UNIT-11 contract in-place."""
        for key in ("a", "b", "c", "d", "e"):
            option_key = f"option_{key}"
            statement_key = f"statement_{key}"
            if not (record.get(option_key) or "").strip() and (
                record.get(statement_key) or ""
            ).strip():
                record[option_key] = (record.get(statement_key) or "").strip()
        if not (record.get("correct_answer") or "").strip():
            if (record.get("correct_option") or "").strip():
                record["correct_answer"] = (record.get("correct_option") or "").strip()
            elif any((record.get(f"truth_{k}") or "").strip() for k in ("a", "b", "c", "d", "e")):
                parts = []
                for key in ("a", "b", "c", "d", "e"):
                    val = (record.get(f"truth_{key}") or "").strip()
                    if val:
                        parts.append(f"{key.upper()}={val}")
                if parts:
                    record["correct_answer"] = ",".join(parts)
        if not (record.get("subject") or "").strip() and (
            record.get("content_subject") or ""
        ).strip():
            record["subject"] = (record.get("content_subject") or "").strip()
        if not (record.get("topic") or "").strip() and (
            record.get("content_topic") or ""
        ).strip():
            record["topic"] = (record.get("content_topic") or "").strip()
        if not (record.get("explanation") or "").strip() and (
            record.get("notes") or ""
        ).strip():
            record["explanation"] = (record.get("notes") or "").strip()

    # ---- VALIDATE ----------------------------------------------------------

    @classmethod
    def validate(cls, rows: list[dict], *, blueprint: ExamBlueprint | None = None) -> ImportPreview:
        if blueprint is None:
            blueprint = ExamBlueprint.objects.filter(is_active=True).first()
        categories = cls._category_index(blueprint)
        competencies = cls._competency_index(blueprint)

        preview = ImportPreview(total=len(rows))
        seen_codes: dict[str, int] = {}
        existing_codes = set(
            Question.objects.exclude(question_code__isnull=True)
            .exclude(question_code="")
            .values_list("question_code", flat=True)
        )

        for i, record in enumerate(rows, start=1):
            result = cls._validate_row(
                i,
                record,
                categories=categories,
                competencies=competencies,
                blueprint=blueprint,
            )
            code = result.question_code
            # In-file duplicate detection (only meaningful when a code is present).
            if code:
                seen_codes[code] = seen_codes.get(code, 0) + 1
                if seen_codes[code] > 1 and result.status != STATUS_INVALID:
                    result.status = STATUS_INVALID
                    result.errors.append(
                        f"Duplicate question_code '{code}' appears more than once in the file."
                    )
                elif code in existing_codes and result.status == STATUS_VALID:
                    result.status = STATUS_DUPLICATE
                    result.warnings.append(
                        f"question_code '{code}' already exists — it will be skipped."
                    )
            cls._tally(preview, result)
            preview.rows.append(result)

        return preview

    @classmethod
    def preview(cls, file_or_path, *, blueprint: ExamBlueprint | None = None) -> ImportPreview:
        rows = cls.parse(file_or_path)
        return cls.validate(rows, blueprint=blueprint)

    @classmethod
    def _tally(cls, preview: ImportPreview, result: RowResult) -> None:
        if result.status == STATUS_VALID:
            preview.valid += 1
        elif result.status == STATUS_DUPLICATE:
            preview.duplicate += 1
        else:
            preview.invalid += 1
        for err in result.errors:
            preview.errors.append(f"Row {result.index}: {err}")
        for warn in result.warnings:
            preview.warnings.append(f"Row {result.index}: {warn}")
        if result.status != STATUS_INVALID:
            qtype = result.data.get("question_type")
            if qtype:
                preview.type_counts[qtype] = preview.type_counts.get(qtype, 0) + 1
            cat = result.data.get("blueprint_category_name")
            if cat:
                preview.blueprint_counts[cat] = preview.blueprint_counts.get(cat, 0) + 1
            cog = result.data.get("cognitive_level")
            if cog:
                preview.cognitive_counts[cog] = preview.cognitive_counts.get(cog, 0) + 1
            subject = result.data.get("content_subject")
            if subject:
                preview.subject_counts[subject] = preview.subject_counts.get(subject, 0) + 1
            if result.data.get("needs_review"):
                preview.needs_review += 1
            source_name = result.data.get("source_name") or ""
            if source_name:
                preview.source_counts[source_name] = (
                    preview.source_counts.get(source_name, 0) + 1
                )

    @classmethod
    def _validate_row(
        cls, index, record, *, categories, competencies, blueprint
    ) -> RowResult:
        errors: list[str] = []
        warnings: list[str] = []
        data: dict = {}

        code = (record.get("question_code") or "").strip()
        raw_type = (record.get("question_type") or "").strip().lower()
        result = RowResult(index=index, question_code=code, question_type=raw_type, status=STATUS_VALID)

        if not code:
            errors.append("question_code is required.")

        text = (record.get("question_text") or "").strip()
        if not text:
            errors.append("question_text is required.")
        data["question_text"] = text

        if raw_type in _TF_ALIASES:
            qtype = QuestionType.TRUE_FALSE
        elif raw_type in _BA_ALIASES:
            qtype = QuestionType.BEST_ANSWER
        else:
            errors.append(
                f"question_type must be TRUE/FALSE or BEST_ANSWER (got '{record.get('question_type')}')."
            )
            qtype = None
        data["question_type"] = qtype

        options = {
            key: (record.get(f"option_{key}") or "").strip()
            for key in ("a", "b", "c", "d", "e")
        }
        correct_raw = (record.get("correct_answer") or "").strip()

        if qtype == QuestionType.TRUE_FALSE:
            cls._validate_true_false(options, correct_raw, errors, data)
        elif qtype == QuestionType.BEST_ANSWER:
            cls._validate_best_answer(options, correct_raw, errors, data)

        # Blueprint category / competency (no silent substitution).
        cat_name = (record.get("blueprint_category") or "").strip()
        category = None
        if cat_name:
            category = categories.get(cat_name.lower())
            if category is None:
                errors.append(f"Unknown blueprint category '{cat_name}'.")
            else:
                data["blueprint_category_id"] = category.id
                data["blueprint_category_name"] = category.name
        else:
            warnings.append("No blueprint category (unclassified) — flagged for review.")

        comp_name = (record.get("blueprint_competency") or "").strip()
        if comp_name:
            comp = competencies.get(comp_name.lower())
            if comp is None:
                errors.append(f"Unknown blueprint competency '{comp_name}'.")
            elif category is not None and comp.category_id != category.id:
                errors.append(
                    f"Competency '{comp_name}' does not belong to category '{cat_name}'."
                )
            else:
                data["blueprint_competency_id"] = comp.id
                if category is None:
                    # Competency uniquely determines its category — clearly supported.
                    category = getattr(comp, "category", None)
                    if category is not None:
                        data["blueprint_category_id"] = category.id
                        data["blueprint_category_name"] = category.name

        # Cognitive level
        cog = (record.get("cognitive_level") or "").strip().lower()
        if cog:
            mapped = _COGNITIVE_ALIASES.get(cog)
            if mapped is None:
                errors.append(f"Unknown cognitive_level '{cog}'.")
            else:
                data["cognitive_level"] = mapped
        else:
            data["cognitive_level"] = None
            warnings.append("No cognitive level — flagged for review.")

        # Difficulty (optional / nullable)
        diff = (record.get("difficulty") or "").strip().lower()
        if diff:
            if diff not in {d.value for d in DifficultyLevel}:
                errors.append(f"Unknown difficulty '{diff}'.")
            else:
                data["difficulty"] = diff
        else:
            data["difficulty"] = None

        # Status
        status_raw = (record.get("status") or "").strip().lower() or EditorialState.DRAFT
        if status_raw not in {s.value for s in EditorialState}:
            errors.append(f"Unknown status '{status_raw}'.")
        elif status_raw not in _IMPORTABLE_STATES:
            errors.append(f"status '{status_raw}' is not importable.")
        else:
            data["status"] = status_raw

        # Source (admin-only provenance)
        source_name = (record.get("source_name") or "").strip()
        source_page = (record.get("source_page") or "").strip()
        source_reference = (record.get("source_reference") or "").strip()
        if len(source_page) > 64:
            errors.append("source_page is too long (max 64 characters).")
        if len(source_name) > 255:
            errors.append("source_name is too long (max 255 characters).")
        data["source_name"] = source_name
        data["source_page"] = source_page
        data["source_reference"] = source_reference
        data["source_type"] = cls._parse_source_type(
            record.get("source_type"), errors
        )

        # Taxonomy + scenario — preserve source wording; canonicalize only when known.
        subject_raw = (record.get("subject") or "").strip()
        subject, subject_known = canonicalize_subject(subject_raw)
        data["content_subject"] = subject
        data["subject_known"] = subject_known
        if subject_raw and not subject_known:
            warnings.append(
                f"Subject '{subject_raw}' is not in the content taxonomy — flagged for review."
            )

        topic_raw = (record.get("topic") or "").strip()
        topic, topic_known = canonicalize_topic(topic_raw)
        data["content_topic"] = topic
        data["topic_known"] = topic_known

        scenario = (record.get("scenario") or "").strip()
        data["scenario"] = scenario
        scenario_flag = coerce_bool(record.get("scenario_based"))
        data["scenario_based"] = bool(scenario_flag) if scenario_flag is not None else bool(scenario)
        data["explanation"] = (record.get("explanation") or "").strip()

        explicit_review = coerce_bool(record.get("needs_review"))
        uncertain_mapping = (
            data.get("cognitive_level") is None
            or data.get("blueprint_category_id") is None
        )
        unknown_subject = bool(subject_raw) and not subject_known
        data["needs_review"] = bool(explicit_review) or uncertain_mapping or unknown_subject
        # Uncertain blueprint mapping (or an explicit review flag) must not
        # become student-visible. Unknown subject is flagged but does not
        # override an explicit published status when mapping is otherwise valid.
        if (uncertain_mapping or explicit_review) and data.get("status") == EditorialState.PUBLISHED:
            data["status"] = EditorialState.DRAFT
            warnings.append("status forced to draft because the row needs review.")
        elif data["needs_review"] and not explicit_review:
            warnings.append("Row flagged for admin review.")

        result.errors = errors
        result.warnings = warnings
        result.data = data
        if errors:
            result.status = STATUS_INVALID
        return result

    @staticmethod
    def _parse_source_type(raw, errors: list[str]) -> str:
        text = (raw or "").strip().lower()
        if not text:
            return QuestionSourceType.IMPORTED
        mapped = _SOURCE_TYPE_ALIASES.get(text)
        if mapped is None:
            errors.append(f"Unknown source_type '{raw}'.")
            return QuestionSourceType.IMPORTED
        return mapped

    @classmethod
    def _validate_true_false(cls, options, correct_raw, errors, data) -> None:
        statements = {k: options[k] for k in ("a", "b", "c", "d", "e")}
        missing = [k for k in ("a", "b", "c", "d", "e") if not statements[k]]
        if missing:
            errors.append(
                "TRUE/FALSE requires exactly 5 statements (option_a–option_e)."
            )
        truths = cls._parse_truths(correct_raw)
        if truths is None or len(truths) != 5 or set(truths) != {"a", "b", "c", "d", "e"}:
            errors.append(
                "TRUE/FALSE correct_answer must supply 5 truth values for a–e "
                "(e.g. 'A=TRUE,B=FALSE,C=TRUE,D=FALSE,E=TRUE')."
            )
        else:
            data["truths"] = truths
        data["statements"] = statements

    @classmethod
    def _validate_best_answer(cls, options, correct_raw, errors, data) -> None:
        opts = {k: options[k] for k in ("a", "b", "c", "d")}
        missing = [k for k in ("a", "b", "c", "d") if not opts[k]]
        if missing:
            errors.append("BEST_ANSWER requires exactly 4 options (option_a–option_d).")
        if options.get("e"):
            errors.append("BEST_ANSWER must not use option_e (leave it blank).")
        key = correct_raw.strip().lower().replace(" ", "")
        if key not in {"a", "b", "c", "d"}:
            errors.append(
                "BEST_ANSWER correct_answer must be exactly one of A, B, C, D."
            )
        else:
            data["correct_key"] = key
        data["options"] = opts

    @staticmethod
    def _parse_truths(correct_raw: str):
        raw = (correct_raw or "").strip()
        if not raw:
            return None
        tokens = [t for t in raw.replace(";", ",").split(",") if t.strip()]
        truths: dict[str, bool] = {}
        if all("=" in t for t in tokens) and tokens:
            for token in tokens:
                key, _, val = token.partition("=")
                key = key.strip().lower()
                b = coerce_bool(val)
                if key not in {"a", "b", "c", "d", "e"} or b is None:
                    return None
                truths[key] = b
            return truths
        # Positional: 5 values mapped to a–e.
        if len(tokens) != 5:
            return None
        for key, token in zip(("a", "b", "c", "d", "e"), tokens):
            b = coerce_bool(token)
            if b is None:
                return None
            truths[key] = b
        return truths

    @classmethod
    def _category_index(cls, blueprint) -> dict:
        if blueprint is None:
            return {}
        index = {}
        for cat in BlueprintCategory.objects.filter(blueprint=blueprint):
            index[cat.name.strip().lower()] = cat
            index[cat.code.strip().lower()] = cat
        return index

    @classmethod
    def _competency_index(cls, blueprint) -> dict:
        if blueprint is None:
            return {}
        index = {}
        qs = BlueprintCompetency.objects.filter(
            category__blueprint=blueprint
        ).select_related("category")
        for comp in qs:
            index[comp.code.strip().lower()] = comp
            if comp.number:
                index[str(comp.number)] = comp
            text = (comp.text or "").strip().lower()
            if text:
                index[text] = comp
        return index

    # ---- COMMIT ------------------------------------------------------------

    @classmethod
    def commit(
        cls,
        file_or_path,
        *,
        actor,
        blueprint: ExamBlueprint | None = None,
        locale: str = LocaleCode.EN,
        filename: str = "",
    ) -> ImportCommitReport:
        """Re-parse + re-validate the workbook, then import transactionally."""
        rows = cls.parse(file_or_path)
        if blueprint is None:
            blueprint = ExamBlueprint.objects.filter(is_active=True).first()
        preview = cls.validate(rows, blueprint=blueprint)
        fname = filename or getattr(file_or_path, "name", "") or ""
        fname = str(fname).replace("\\", "/").rsplit("/", 1)[-1][:255]
        if preview.has_invalid:
            # Invalid workbook → zero writes (no questions, no history row).
            raise ImportCommitError(
                f"{preview.invalid} invalid row(s) — no questions were imported."
            )
        report = ImportCommitReport()
        to_create: list[RowResult] = []
        with transaction.atomic():
            for result in preview.rows:
                if result.status == STATUS_DUPLICATE:
                    report.skipped_duplicate += 1
                    report.skipped_codes.append(result.question_code)
                    continue
                if result.status != STATUS_VALID:
                    continue
                to_create.append(result)
                report.created += 1
                report.created_codes.append(result.question_code)
                if result.data.get("needs_review"):
                    report.needs_review += 1
            if to_create:
                cls._bulk_insert_questions(to_create, actor=actor, locale=locale)
            batch = cls._record_batch(
                actor=actor,
                filename=fname,
                preview=preview,
                report=report,
                status=QuestionImportBatch.STATUS_COMMITTED,
            )
            report.batch_id = str(batch.id)
            report.batch_status = batch.status
        return report

    @classmethod
    def _record_batch(cls, *, actor, filename, preview: ImportPreview, report: ImportCommitReport, status: str):
        return QuestionImportBatch.objects.create(
            created_by=actor,
            filename=filename or "",
            status=status,
            total_rows=preview.total,
            created_count=report.created,
            skipped_duplicate=report.skipped_duplicate,
            invalid_count=preview.invalid,
            needs_review_count=preview.needs_review,
            type_counts=dict(preview.type_counts),
            blueprint_counts=dict(preview.blueprint_counts),
            cognitive_counts=dict(preview.cognitive_counts),
            created_codes=list(report.created_codes),
            skipped_codes=list(report.skipped_codes),
            errors=list(preview.errors),
            warnings=list(preview.warnings),
            report={
                "valid": preview.valid,
                "invalid": preview.invalid,
                "duplicate": preview.duplicate,
                "needs_review": preview.needs_review,
                "subject_counts": dict(preview.subject_counts),
                "source_counts": dict(preview.source_counts),
            },
        )

    @classmethod
    def _create_question(cls, result: RowResult, *, actor, locale: str) -> Question:
        created = cls._bulk_insert_questions([result], actor=actor, locale=locale)
        return created[0]

    @classmethod
    def _bulk_insert_questions(
        cls, results: list[RowResult], *, actor, locale: str
    ) -> list[Question]:
        """Insert a batch of already-validated rows without per-row round-trips."""
        now = timezone.now()
        questions: list[Question] = []
        pending: list[tuple[Question, RowResult]] = []
        for result in results:
            data = result.data
            status = data.get("status", EditorialState.DRAFT)
            question = Question(
                id=uuid.uuid4(),
                question_type=data["question_type"],
                difficulty=data.get("difficulty"),
                primary_locale=locale,
                editorial_state=status,
                question_code=result.question_code or None,
                scenario_based=data.get("scenario_based", False),
                cognitive_level=data.get("cognitive_level"),
                content_subject=data.get("content_subject", ""),
                content_topic=data.get("content_topic", ""),
                blueprint_category_id=data.get("blueprint_category_id"),
                blueprint_competency_id=data.get("blueprint_competency_id"),
                needs_review=data.get("needs_review", False),
                source_type=data.get("source_type") or QuestionSourceType.IMPORTED,
                source_name=data.get("source_name", ""),
                source_page=data.get("source_page", ""),
                source_reference=data.get("source_reference", ""),
                created_by=actor,
                updated_by=actor,
                created_at=now,
                updated_at=now,
                published_at=now if status == EditorialState.PUBLISHED else None,
            )
            questions.append(question)
            pending.append((question, result))
        Question.objects.bulk_create(questions, batch_size=BULK_INSERT_BATCH)

        versions: list[QuestionVersion] = []
        version_for: list[tuple[Question, QuestionVersion, RowResult]] = []
        for question, result in pending:
            data = result.data
            qtype = data["question_type"]
            if qtype == QuestionType.TRUE_FALSE:
                spec = {"type": "true_false", "truths": data["truths"]}
            else:
                spec = {"key": data["correct_key"]}
            version = QuestionVersion(
                id=uuid.uuid4(),
                question=question,
                version_no=1,
                correct_answer_spec=spec,
                clinical_scenario_body=data.get("scenario") or None,
                created_by=actor,
                created_at=now,
            )
            versions.append(version)
            version_for.append((question, version, result))
        QuestionVersion.objects.bulk_create(versions, batch_size=BULK_INSERT_BATCH)

        translations: list[QuestionVersionTranslation] = []
        options: list[QuestionOption] = []
        option_plan: list[tuple[QuestionOption, str]] = []
        for question, version, result in version_for:
            data = result.data
            translations.append(
                QuestionVersionTranslation(
                    id=uuid.uuid4(),
                    version=version,
                    locale=locale,
                    stem=data["question_text"],
                    explanation=data.get("explanation", ""),
                )
            )
            qtype = data["question_type"]
            if qtype == QuestionType.TRUE_FALSE:
                statements = data["statements"]
                truths = data["truths"]
                for order, key in enumerate(("a", "b", "c", "d", "e")):
                    opt = QuestionOption(
                        id=uuid.uuid4(),
                        question_version=version,
                        key=key,
                        is_correct=bool(truths.get(key)),
                        sort_order=order,
                    )
                    options.append(opt)
                    option_plan.append((opt, statements[key]))
            else:
                opts = data["options"]
                correct_key = data["correct_key"]
                for order, key in enumerate(("a", "b", "c", "d")):
                    opt = QuestionOption(
                        id=uuid.uuid4(),
                        question_version=version,
                        key=key,
                        is_correct=(key == correct_key),
                        sort_order=order,
                    )
                    options.append(opt)
                    option_plan.append((opt, opts[key]))
            question.current_version = version
            question.updated_at = now

        QuestionVersionTranslation.objects.bulk_create(
            translations, batch_size=BULK_INSERT_BATCH
        )
        QuestionOption.objects.bulk_create(options, batch_size=BULK_INSERT_BATCH)
        QuestionOptionTranslation.objects.bulk_create(
            [
                QuestionOptionTranslation(
                    id=uuid.uuid4(),
                    option=opt,
                    locale=locale,
                    label=label,
                )
                for opt, label in option_plan
            ],
            batch_size=BULK_INSERT_BATCH,
        )
        Question.objects.bulk_update(
            [q for q, _ in pending],
            ["current_version", "updated_at"],
            batch_size=BULK_INSERT_BATCH,
        )
        return [q for q, _ in pending]


def stash_workbook(file_or_path) -> tuple[str, str]:
    """Persist an upload to a temp file so confirm need not re-attach the workbook."""
    filename = getattr(file_or_path, "name", "") or "workbook.xlsx"
    filename = str(filename).replace("\\", "/").rsplit("/", 1)[-1][:255]
    if hasattr(file_or_path, "read"):
        data = file_or_path.read()
        if hasattr(file_or_path, "seek"):
            try:
                file_or_path.seek(0)
            except Exception:
                pass
    else:
        with open(file_or_path, "rb") as handle:
            data = handle.read()
    handle, path = tempfile.mkstemp(prefix=STASH_PREFIX, suffix=".xlsx")
    with os.fdopen(handle, "wb") as out:
        out.write(data)
    return path, filename


def is_valid_stash_path(path: str) -> bool:
    if not path:
        return False
    try:
        real = os.path.realpath(path)
        temp_root = os.path.realpath(tempfile.gettempdir())
    except OSError:
        return False
    name = os.path.basename(real)
    return real.startswith(temp_root + os.sep) and name.startswith(STASH_PREFIX)


def clear_stash(path: str) -> None:
    if not is_valid_stash_path(path):
        return
    try:
        os.remove(path)
    except OSError:
        return
