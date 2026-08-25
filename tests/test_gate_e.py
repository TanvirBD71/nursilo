"""GATE E — large-scale question bank ingestion + rapid review workflow."""
from __future__ import annotations

import io
import unittest

from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from apps.accounts.models import UserAccount
from apps.accounts.services import AccountService
from apps.assessment.models import ExamBlueprint, ExamDefinition, Question
from apps.assessment.services.import_questions import (
    COMPAT_COLUMNS,
    HEADER_ALIASES,
    ImportCommitError,
    PREVIEW_DISPLAY_LIMIT,
    QuestionImportService,
    REQUIRED_COLUMNS,
)
from apps.assessment.services.import_template import build_example_workbook
from apps.assessment.services.protection import MARCH_2025_CODE_PREFIX
from apps.common.choices import (
    AttemptMode,
    ClassificationOrigin,
    EditorialState,
    QuestionType,
    RoleCode,
)
from apps.rbac.models import Role, RoleAssignment
from apps.staff.services import QuestionStaffService, StaffDashboardService
from apps.staff.services.questions import QuestionStaffError


STRONG_PASSWORD = "Str0ng-Pass!GateE"


def setUpModule():
    try:
        connection.ensure_connection()
    except Exception as exc:  # pragma: no cover
        raise unittest.SkipTest(f"PostgreSQL unavailable for GATE E: {exc}") from exc


def _assign(user, *role_codes):
    for code in role_codes:
        role = Role.objects.get(code=code)
        RoleAssignment.objects.get_or_create(user=user, role=role)


def _staff_user(email, *role_codes):
    user = UserAccount.objects.create_user(
        email=email, password=STRONG_PASSWORD, full_name="Gate E Staff"
    )
    _assign(user, *role_codes)
    return user


def _xlsx_bytes(rows, *, header=None):
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    header = header or list(REQUIRED_COLUMNS)
    ws.append(header)
    for row in rows:
        ws.append([row.get(col, "") for col in header])
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


def _tf_row(code, **overrides):
    row = {
        "question_code": code,
        "question_type": "TRUE/FALSE",
        "question_text": "GATE-E synthetic — mark each statement true or false.",
        "scenario": "",
        "option_a": "GE statement A",
        "option_b": "GE statement B",
        "option_c": "GE statement C",
        "option_d": "GE statement D",
        "option_e": "GE statement E",
        "correct_answer": "A=TRUE,B=FALSE,C=TRUE,D=FALSE,E=TRUE",
        "explanation": "GATE-E synthetic rationale.",
        "blueprint_category": "Nursing Process",
        "blueprint_competency": "C1",
        "subject": "Fundamentals of Nursing",
        "topic": "Growth and Development",
        "cognitive_level": "recall",
        "difficulty": "easy",
        "scenario_based": "false",
        "source_name": "GATE-E synthetic fixture",
        "source_page": "1",
        "source_reference": code,
        "status": "draft",
    }
    row.update(overrides)
    return row


def _ba_row(code, **overrides):
    row = {
        "question_code": code,
        "question_type": "BEST_ANSWER",
        "question_text": "GATE-E synthetic — pick the best answer.",
        "scenario": "",
        "option_a": "GE Alpha",
        "option_b": "GE Beta",
        "option_c": "GE Gamma",
        "option_d": "GE Delta",
        "option_e": "",
        "correct_answer": "B",
        "explanation": "GATE-E Beta is the synthetic key.",
        "blueprint_category": "Communication",
        "blueprint_competency": "C32",
        "subject": "Psychiatric and Mental Health Nursing",
        "topic": "",
        "cognitive_level": "understanding",
        "difficulty": "medium",
        "scenario_based": "false",
        "source_name": "GATE-E synthetic fixture",
        "source_page": "2",
        "source_reference": code,
        "status": "draft",
    }
    row.update(overrides)
    return row


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"],
)
class ExcelCompatibilityTests(TestCase):
    def setUp(self):
        self.editor = _staff_user("gatee-xl@example.com", RoleCode.EDITOR)
        self.blueprint = ExamBlueprint.objects.get(code="BNMC_2018")

    def test_attached_style_template_still_imports(self):
        preview = QuestionImportService.preview(
            io.BytesIO(build_example_workbook()), blueprint=self.blueprint
        )
        self.assertFalse(preview.has_invalid, preview.errors[:5])
        self.assertGreaterEqual(preview.valid, 2)

    def test_stem_alias_and_notes_fill_explanation(self):
        header = ["stem" if c == "question_text" else c for c in REQUIRED_COLUMNS] + [
            "notes"
        ]
        row = _tf_row("GATEE-ALIAS-1", explanation="")
        row["stem"] = row.pop("question_text")
        row["notes"] = "Staff note stored as explanation."
        preview = QuestionImportService.preview(
            _xlsx_bytes([row], header=header), blueprint=self.blueprint
        )
        self.assertEqual(preview.valid, 1, preview.errors[:5])
        report = QuestionImportService.commit(
            _xlsx_bytes([row], header=header),
            actor=self.editor,
            blueprint=self.blueprint,
        )
        self.assertEqual(report.created, 1)
        q = Question.objects.get(question_code="GATEE-ALIAS-1")
        tr = q.current_version.translations.first()
        self.assertEqual(tr.explanation, "Staff note stored as explanation.")

    def test_compat_columns_are_not_required_on_generated_templates(self):
        self.assertTrue(set(COMPAT_COLUMNS).isdisjoint(REQUIRED_COLUMNS))
        self.assertIn("stem", HEADER_ALIASES)


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"],
)
class LargeScaleImportTests(TestCase):
    def setUp(self):
        self.editor = _staff_user("gatee-ls@example.com", RoleCode.EDITOR)
        self.blueprint = ExamBlueprint.objects.get(code="BNMC_2018")

    def _batch(self, prefix, n):
        rows = []
        for i in range(n):
            if i % 2 == 0:
                rows.append(_tf_row(f"{prefix}-TF-{i:04d}"))
            else:
                rows.append(_ba_row(f"{prefix}-BA-{i:04d}"))
        return rows

    def test_fifty_question_import(self):
        rows = self._batch("GATEE50", 50)
        report = QuestionImportService.commit(
            _xlsx_bytes(rows), actor=self.editor, blueprint=self.blueprint
        )
        self.assertEqual(report.created, 50)
        self.assertEqual(report.skipped_duplicate, 0)
        self.assertEqual(
            Question.objects.filter(question_code__startswith="GATEE50-").count(), 50
        )

    def test_hundred_question_import(self):
        rows = self._batch("GATEE100", 100)
        report = QuestionImportService.commit(
            _xlsx_bytes(rows), actor=self.editor, blueprint=self.blueprint
        )
        self.assertEqual(report.created, 100)
        self.assertIsNotNone(report.batch_id)

    def test_large_batch_validation_caps_preview_html_rows(self):
        rows = self._batch("GATEE500", 500)
        preview = QuestionImportService.preview(
            _xlsx_bytes(rows), blueprint=self.blueprint
        )
        self.assertEqual(preview.total, 500)
        self.assertEqual(preview.valid, 500)
        self.assertLessEqual(len(preview.display_rows), PREVIEW_DISPLAY_LIMIT)
        self.assertEqual(preview.hidden_row_count, 500 - PREVIEW_DISPLAY_LIMIT)

    def test_duplicate_detection_and_idempotent_reimport(self):
        first = _xlsx_bytes([_tf_row("GATEE-IDEM-1"), _ba_row("GATEE-IDEM-2")])
        QuestionImportService.commit(
            first, actor=self.editor, blueprint=self.blueprint
        )
        again = _xlsx_bytes([_tf_row("GATEE-IDEM-1"), _ba_row("GATEE-IDEM-2")])
        report = QuestionImportService.commit(
            again, actor=self.editor, blueprint=self.blueprint
        )
        self.assertEqual(report.created, 0)
        self.assertEqual(report.skipped_duplicate, 2)
        self.assertEqual(
            Question.objects.filter(question_code__startswith="GATEE-IDEM-").count(), 2
        )

    def test_invalid_workbook_zero_write(self):
        before = Question.objects.count()
        rows = [_tf_row("GATEE-OK-1"), _tf_row("GATEE-BAD", option_e="")]
        with self.assertRaises(ImportCommitError):
            QuestionImportService.commit(
                _xlsx_bytes(rows), actor=self.editor, blueprint=self.blueprint
            )
        self.assertEqual(Question.objects.count(), before)
        self.assertFalse(Question.objects.filter(question_code="GATEE-OK-1").exists())

    def test_tf_and_ba_validation(self):
        preview = QuestionImportService.preview(
            _xlsx_bytes(
                [
                    _tf_row("GATEE-TF-BAD", correct_answer="A=TRUE"),
                    _ba_row("GATEE-BA-BAD", option_e="extra"),
                ]
            ),
            blueprint=self.blueprint,
        )
        self.assertEqual(preview.invalid, 2)
        self.assertFalse(preview.importable)


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"],
)
class ClassificationAndBulkTests(TestCase):
    def setUp(self):
        self.editor = _staff_user("gatee-cl@example.com", RoleCode.EDITOR)
        self.author = _staff_user("gatee-au@example.com", RoleCode.AUTHOR)
        self.blueprint = ExamBlueprint.objects.get(code="BNMC_2018")

    def test_suggestion_accept_reject_does_not_auto_convert(self):
        QuestionImportService.commit(
            _xlsx_bytes(
                [
                    _tf_row(
                        "GATEE-SUG-1",
                        blueprint_category="",
                        blueprint_competency="",
                        cognitive_level="",
                    )
                ]
            ),
            actor=self.editor,
            blueprint=self.blueprint,
        )
        q = Question.objects.get(question_code="GATEE-SUG-1")
        self.assertEqual(q.classification_origin, "")
        QuestionStaffService.apply_suggestion(
            actor=self.editor, question=q, fields=["category"]
        )
        q.refresh_from_db()
        self.assertEqual(q.classification_origin, ClassificationOrigin.SUGGESTED)
        self.assertTrue(q.needs_review)
        self.assertIsNotNone(q.blueprint_category_id)

        other = Question.objects.get(question_code="GATEE-SUG-1")
        QuestionStaffService.dismiss_suggestion(actor=self.editor, question=other)
        from apps.assessment.services.blueprint_suggest import BlueprintSuggestionService

        dismissed = BlueprintSuggestionService.suggest(other)
        self.assertFalse(dismissed.confident)

    def test_staff_save_marks_approved_not_suggested(self):
        QuestionImportService.commit(
            _xlsx_bytes([_ba_row("GATEE-APP-1")]),
            actor=self.editor,
            blueprint=self.blueprint,
        )
        q = Question.objects.get(question_code="GATEE-APP-1")
        QuestionStaffService.update_classification(
            actor=self.editor,
            question=q,
            content_subject=q.content_subject,
            content_topic=q.content_topic,
            cognitive_level=q.cognitive_level,
            blueprint_category_id=q.blueprint_category_id,
            blueprint_competency_id=q.blueprint_competency_id,
            classification_origin=ClassificationOrigin.APPROVED,
        )
        q.refresh_from_db()
        self.assertEqual(q.classification_origin, ClassificationOrigin.APPROVED)

    def test_bulk_classify_requires_a_field_and_sets_approved(self):
        QuestionImportService.commit(
            _xlsx_bytes([_tf_row("GATEE-BC-1")]),
            actor=self.editor,
            blueprint=self.blueprint,
        )
        q = Question.objects.get(question_code="GATEE-BC-1")
        with self.assertRaises(QuestionStaffError):
            QuestionStaffService.bulk_classify(
                actor=self.editor, question_ids=[q.id]
            )
        result = QuestionStaffService.bulk_classify(
            actor=self.editor,
            question_ids=[q.id],
            cognitive_level="application",
        )
        self.assertEqual(result.succeeded, 1)
        q.refresh_from_db()
        self.assertEqual(q.cognitive_level, "application")
        self.assertEqual(q.classification_origin, ClassificationOrigin.APPROVED)

    def test_bulk_submit_approve_publish(self):
        QuestionImportService.commit(
            _xlsx_bytes([_ba_row("GATEE-WF-1")]),
            actor=self.editor,
            blueprint=self.blueprint,
        )
        q = Question.objects.get(question_code="GATEE-WF-1")
        submitted = QuestionStaffService.bulk_submit_review(
            actor=self.editor, question_ids=[q.id]
        )
        self.assertEqual(submitted.succeeded, 1)
        approved = QuestionStaffService.bulk_approve(
            actor=self.editor, question_ids=[q.id]
        )
        self.assertEqual(approved.succeeded, 1)
        published = QuestionStaffService.bulk_publish(
            actor=self.editor, question_ids=[q.id]
        )
        self.assertEqual(published.succeeded, 1)
        q.refresh_from_db()
        self.assertEqual(q.editorial_state, EditorialState.PUBLISHED)

    def test_author_cannot_bulk_approve(self):
        QuestionImportService.commit(
            _xlsx_bytes([_tf_row("GATEE-AU-1")]),
            actor=self.editor,
            blueprint=self.blueprint,
        )
        q = Question.objects.get(question_code="GATEE-AU-1")
        Question.objects.filter(pk=q.pk).update(editorial_state=EditorialState.REVIEW)
        result = QuestionStaffService.bulk_approve(
            actor=self.author, question_ids=[q.id]
        )
        self.assertEqual(result.succeeded, 0)
        q.refresh_from_db()
        self.assertEqual(q.editorial_state, EditorialState.REVIEW)


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"],
)
class ReviewQueueDashboardSecurityTests(TestCase):
    def setUp(self):
        self.editor = _staff_user("gatee-ui@example.com", RoleCode.EDITOR)
        self.admin = _staff_user("gatee-ad@example.com", RoleCode.ADMIN)
        self.blueprint = ExamBlueprint.objects.get(code="BNMC_2018")
        QuestionImportService.commit(
            _xlsx_bytes([_tf_row("GATEE-UI-1", difficulty="hard")]),
            actor=self.editor,
            blueprint=self.blueprint,
        )
        self.client = Client()
        self.client.force_login(self.editor)

    def test_queue_has_organization_columns_and_difficulty_filter(self):
        listing = self.client.get(reverse("staff:questions"))
        self.assertContains(listing, "Topic")
        self.assertContains(listing, "Category")
        self.assertContains(listing, "Cognitive")
        self.assertContains(listing, "Difficulty")
        filtered = self.client.get(reverse("staff:questions"), {"difficulty": "hard"})
        self.assertContains(filtered, "GATEE-UI-1")
        missed = self.client.get(reverse("staff:questions"), {"difficulty": "easy"})
        self.assertNotContains(missed, "GATEE-UI-1")

    def test_dashboard_counts_come_from_db(self):
        data = StaffDashboardService.build(self.editor)
        self.assertEqual(data.question_bank["total"], Question.objects.count())
        self.assertIn("draft", data.question_bank)
        self.assertIn("needs_review", data.question_bank)
        self.assertIn("by_type", data.question_bank)
        page = self.client.get(reverse("staff:dashboard"))
        self.assertContains(page, "Needs review")
        self.assertContains(page, "Bank total")

    def test_import_redirects_to_report(self):
        payload = _xlsx_bytes([_ba_row("GATEE-REP-1")]).read()
        upload = SimpleUploadedFile(
            "gate-e.xlsx",
            payload,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        preview = self.client.post(
            reverse("staff:questions_import"),
            {"file": upload},
        )
        self.assertEqual(preview.status_code, 200)
        confirm = self.client.post(
            reverse("staff:questions_import"),
            {"confirm": "on"},
        )
        self.assertEqual(confirm.status_code, 302)
        self.assertIn("/questions/import/history/", confirm["Location"])

    def test_student_cannot_access_staff_qb_or_import(self):
        student, _ = AccountService.register(
            email="gatee-stu@example.com", password=STRONG_PASSWORD
        )
        self.client.force_login(student)
        self.assertEqual(self.client.get(reverse("staff:questions")).status_code, 403)
        self.assertEqual(
            self.client.get(reverse("staff:questions_import")).status_code, 403
        )

    def test_provenance_and_answer_key_are_staff_only(self):
        q = Question.objects.get(question_code="GATEE-UI-1")
        student, _ = AccountService.register(
            email="gatee-stu2@example.com", password=STRONG_PASSWORD
        )
        self.assertIsNone(QuestionStaffService.provenance_for(self.editor, q))
        admin_view = QuestionStaffService.provenance_for(self.admin, q)
        self.assertIsNotNone(admin_view)
        self.assertEqual(admin_view["source_name"], "GATE-E synthetic fixture")
        with self.assertRaises(PermissionError):
            QuestionStaffService.staff_answer_key(student, q)
        key = QuestionStaffService.staff_answer_key(self.editor, q)
        self.assertTrue(key["options"])
        self.assertTrue(any(o["is_correct"] for o in key["options"]))

    def test_imported_draft_not_exam_eligible(self):
        q = Question.objects.get(question_code="GATEE-UI-1")
        self.assertEqual(q.editorial_state, EditorialState.DRAFT)
        exam = ExamDefinition.objects.create(
            code="gatee-exam",
            title_key="GATE E exam",
            mode=AttemptMode.TIMED_EXAM,
            editorial_state=EditorialState.PUBLISHED,
        )
        from apps.assessment.models import ExamDefinitionItem
        from apps.assessment.services.exam_pool import ExamPoolEmpty, ExamPoolService

        ExamDefinitionItem.objects.create(
            exam_definition=exam, question=q, sort_order=1
        )
        with self.assertRaises(ExamPoolEmpty):
            ExamPoolService.select_questions(exam)

    def test_march_2025_untouched_and_q64_q80_absent(self):
        self.assertFalse(
            Question.objects.filter(
                question_code__startswith=MARCH_2025_CODE_PREFIX
            ).exists()
        )
        self.assertFalse(Question.objects.filter(question_code__icontains="Q64").exists())
        self.assertFalse(Question.objects.filter(question_code__icontains="Q80").exists())
        self.assertFalse(
            Question.objects.filter(question_type=QuestionType.TRUE_FALSE)
            .exclude(question_code__startswith="GATEE")
            .filter(question_code__in={"Q64", "Q80"})
            .exists()
        )
