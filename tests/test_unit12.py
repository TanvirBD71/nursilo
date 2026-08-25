"""
UNIT-12 — Real Licensing Question Bank Ingestion & Content Review tests.

Covers the extended Excel import pipeline (aliases, taxonomy, review flags,
transactional safety, import history), staff classification/review workflow,
publishing safety, published-only eligibility, Practice/Exam/timer behaviour
for imported TF/BA items, and student/admin security boundaries.

Synthetic UNIT-12 records are clearly marked (codes prefixed U12- / EXAMPLE-)
and are never treated as real exam content. These tests do not weaken UNIT-5/6/11.
"""
from __future__ import annotations

import io
import unittest

from django.db import connection
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from apps.accounts.models import UserAccount
from apps.accounts.services import AccountService
from apps.assessment.models import (
    Attempt,
    AttemptItem,
    ExamBlueprint,
    ExamDefinition,
    ExamDefinitionItem,
    Question,
    QuestionImportBatch,
)
from apps.assessment.services.blueprint import (
    STATUS_COMPLIANT,
    STATUS_INSUFFICIENT,
    BlueprintService,
)
from apps.assessment.services.exam_pool import ExamPoolService
from apps.assessment.services.import_questions import (
    ImportCommitError,
    ImportStructureError,
    QuestionImportService,
    REQUIRED_COLUMNS,
)
from apps.assessment.services.import_template import build_example_workbook
from apps.assessment.services.presentation import PracticePresentationService
from apps.assessment.services.scoring import (
    TRUE_FALSE_STATEMENT_MARK,
    score_item_detail,
)
from apps.assessment.services.timer import (
    ALLOWED_SECONDS_PER_QUESTION,
    compute_time_limit_seconds,
)
from apps.assessment.taxonomy import CONTENT_SUBJECTS, CROSS_CUTTING_TOPICS
from apps.common.choices import (
    AttemptMode,
    AttemptState,
    CognitiveLevel,
    EditorialState,
    LocaleCode,
    QuestionSourceType,
    QuestionType,
    RoleCode,
)
from apps.rbac.models import Role, RoleAssignment
from apps.staff.services import QuestionStaffService
from apps.staff.services.questions import QuestionStaffError


STRONG_PASSWORD = "Str0ng-Pass!Unit12"


def setUpModule():
    try:
        connection.ensure_connection()
    except Exception as exc:  # pragma: no cover
        raise unittest.SkipTest(f"PostgreSQL unavailable for UNIT-12: {exc}") from exc


def _assign(user, *role_codes):
    for code in role_codes:
        role = Role.objects.get(code=code)
        RoleAssignment.objects.get_or_create(user=user, role=role)


def _staff_user(email, *role_codes):
    user = UserAccount.objects.create_user(
        email=email, password=STRONG_PASSWORD, full_name="Staff Twelve"
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
        "question_text": "U12 synthetic — mark each statement true or false.",
        "scenario": "",
        "option_a": "U12 statement A",
        "option_b": "U12 statement B",
        "option_c": "U12 statement C",
        "option_d": "U12 statement D",
        "option_e": "U12 statement E",
        "correct_answer": "A=TRUE,B=FALSE,C=TRUE,D=FALSE,E=TRUE",
        "explanation": "U12 synthetic rationale.",
        "blueprint_category": "Nursing Process",
        "blueprint_competency": "C1",
        "subject": "Fundamentals of Nursing",
        "topic": "Growth and Development",
        "cognitive_level": "recall",
        "difficulty": "",
        "scenario_based": "false",
        "source_name": "UNIT-12 synthetic fixture",
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
        "question_text": "U12 synthetic — pick the best answer.",
        "scenario": "",
        "option_a": "U12 Alpha",
        "option_b": "U12 Beta",
        "option_c": "U12 Gamma",
        "option_d": "U12 Delta",
        "option_e": "",
        "correct_answer": "B",
        "explanation": "U12 Beta is the synthetic key.",
        "blueprint_category": "Communication",
        "blueprint_competency": "C32",
        "subject": "Psychiatric and Mental Health Nursing",
        "topic": "",
        "cognitive_level": "understanding",
        "difficulty": "medium",
        "scenario_based": "false",
        "source_name": "UNIT-12 synthetic fixture",
        "source_page": "2",
        "source_reference": code,
        "status": "draft",
    }
    row.update(overrides)
    return row


def _attempt_item(user, question, version, selected_answer=None):
    attempt = Attempt.objects.create(
        user=user,
        mode=AttemptMode.PRACTICE,
        state=AttemptState.IN_PROGRESS,
    )
    return AttemptItem.objects.create(
        attempt=attempt,
        position=1,
        question=question,
        question_version=version,
        selected_answer=selected_answer,
    )


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"],
)
class ValidImportTests(TestCase):
    def setUp(self):
        self.editor = _staff_user("u12-editor@example.com", RoleCode.EDITOR)
        self.blueprint = ExamBlueprint.objects.get(code="BNMC_2018")

    def test_valid_tf_and_ba_import(self):
        buf = _xlsx_bytes([_tf_row("U12-TF-OK"), _ba_row("U12-BA-OK")])
        preview = QuestionImportService.preview(buf, blueprint=self.blueprint)
        self.assertEqual(preview.total, 2)
        self.assertEqual(preview.valid, 2)
        self.assertTrue(preview.importable)
        report = QuestionImportService.commit(
            _xlsx_bytes([_tf_row("U12-TF-OK"), _ba_row("U12-BA-OK")]),
            actor=self.editor,
            blueprint=self.blueprint,
        )
        self.assertEqual(report.created, 2)
        tf = Question.objects.get(question_code="U12-TF-OK")
        ba = Question.objects.get(question_code="U12-BA-OK")
        self.assertEqual(tf.question_type, QuestionType.TRUE_FALSE)
        self.assertEqual(tf.current_version.options.count(), 5)
        self.assertEqual(ba.question_type, QuestionType.BEST_ANSWER)
        self.assertEqual(ba.current_version.options.count(), 4)
        self.assertEqual(tf.content_subject, "Fundamentals of Nursing")
        self.assertEqual(tf.content_topic, "Growth and Development")
        self.assertFalse(tf.needs_review)
        self.assertEqual(tf.editorial_state, EditorialState.DRAFT)

    def test_alias_columns_map_to_unit11_contract(self):
        from apps.assessment.services.import_questions import OPTIONAL_COLUMNS

        header = list(REQUIRED_COLUMNS) + [
            c for c in OPTIONAL_COLUMNS if c not in REQUIRED_COLUMNS
        ]
        row = _tf_row(
            "U12-TF-ALIAS",
            option_a="",
            option_b="",
            option_c="",
            option_d="",
            option_e="",
            correct_answer="",
            subject="",
            topic="",
        )
        row.update(
            {
                "statement_a": "Alias A",
                "statement_b": "Alias B",
                "statement_c": "Alias C",
                "statement_d": "Alias D",
                "statement_e": "Alias E",
                "truth_a": "TRUE",
                "truth_b": "FALSE",
                "truth_c": "TRUE",
                "truth_d": "FALSE",
                "truth_e": "TRUE",
                "content_subject": "Anatomy and Physiology",
                "content_topic": "Human Heart",
                "source_type": "official_exam",
            }
        )
        buf = _xlsx_bytes([row], header=header)
        report = QuestionImportService.commit(
            buf, actor=self.editor, blueprint=self.blueprint
        )
        self.assertEqual(report.created, 1)
        q = Question.objects.get(question_code="U12-TF-ALIAS")
        labels = {
            o.key: o.translations.get(locale=LocaleCode.EN).label
            for o in q.current_version.options.all()
        }
        self.assertEqual(labels["a"], "Alias A")
        self.assertEqual(q.content_subject, "Anatomy and Physiology")
        self.assertEqual(q.source_type, QuestionSourceType.OFFICIAL_EXAM)

    def test_ba_correct_option_alias(self):
        from apps.assessment.services.import_questions import OPTIONAL_COLUMNS

        header = list(REQUIRED_COLUMNS) + list(OPTIONAL_COLUMNS)
        row = _ba_row("U12-BA-ALIAS", correct_answer="")
        row["correct_option"] = "C"
        buf = _xlsx_bytes([row], header=header)
        QuestionImportService.commit(buf, actor=self.editor, blueprint=self.blueprint)
        q = Question.objects.get(question_code="U12-BA-ALIAS")
        self.assertEqual(q.current_version.correct_answer_spec.get("key"), "c")


class StructuralValidationTests(TestCase):
    def setUp(self):
        self.blueprint = ExamBlueprint.objects.get(code="BNMC_2018")

    def test_missing_tf_statement(self):
        buf = _xlsx_bytes([_tf_row("U12-TF-MISS", option_c="")])
        preview = QuestionImportService.preview(buf, blueprint=self.blueprint)
        self.assertEqual(preview.invalid, 1)
        self.assertFalse(preview.importable)

    def test_invalid_tf_truth(self):
        buf = _xlsx_bytes([_tf_row("U12-TF-TRUTH", correct_answer="A=MAYBE,B=FALSE,C=TRUE,D=FALSE,E=TRUE")])
        preview = QuestionImportService.preview(buf, blueprint=self.blueprint)
        self.assertEqual(preview.invalid, 1)

    def test_missing_ba_option(self):
        buf = _xlsx_bytes([_ba_row("U12-BA-MISS", option_d="")])
        preview = QuestionImportService.preview(buf, blueprint=self.blueprint)
        self.assertEqual(preview.invalid, 1)

    def test_multiple_or_zero_ba_correct(self):
        zero = QuestionImportService.preview(
            _xlsx_bytes([_ba_row("U12-BA-ZERO", correct_answer="")]),
            blueprint=self.blueprint,
        )
        multi = QuestionImportService.preview(
            _xlsx_bytes([_ba_row("U12-BA-MULTI", correct_answer="A,B")]),
            blueprint=self.blueprint,
        )
        self.assertEqual(zero.invalid, 1)
        self.assertEqual(multi.invalid, 1)

    def test_option_e_rejected_for_ba(self):
        buf = _xlsx_bytes([_ba_row("U12-BA-E", option_e="Extra")])
        preview = QuestionImportService.preview(buf, blueprint=self.blueprint)
        self.assertEqual(preview.invalid, 1)


class DuplicateAndIdempotencyTests(TestCase):
    def setUp(self):
        self.editor = _staff_user("u12-dup@example.com", RoleCode.EDITOR)
        self.blueprint = ExamBlueprint.objects.get(code="BNMC_2018")

    def test_in_file_duplicate_code_is_validation_error(self):
        buf = _xlsx_bytes([_ba_row("U12-DUP"), _tf_row("U12-DUP")])
        preview = QuestionImportService.preview(buf, blueprint=self.blueprint)
        self.assertTrue(preview.has_invalid)

    def test_idempotent_reimport_skips_existing(self):
        first = _xlsx_bytes([_ba_row("U12-IDEM")])
        QuestionImportService.commit(first, actor=self.editor, blueprint=self.blueprint)
        second = _xlsx_bytes([_ba_row("U12-IDEM")])
        report = QuestionImportService.commit(
            second, actor=self.editor, blueprint=self.blueprint
        )
        self.assertEqual(report.created, 0)
        self.assertEqual(report.skipped_duplicate, 1)
        self.assertEqual(Question.objects.filter(question_code="U12-IDEM").count(), 1)


class BlueprintValidationTests(TestCase):
    def setUp(self):
        self.editor = _staff_user("u12-bp@example.com", RoleCode.EDITOR)
        self.blueprint = ExamBlueprint.objects.get(code="BNMC_2018")

    def test_invalid_blueprint_category(self):
        buf = _xlsx_bytes([_ba_row("U12-BAD-CAT", blueprint_category="Not A Category")])
        preview = QuestionImportService.preview(buf, blueprint=self.blueprint)
        self.assertEqual(preview.invalid, 1)

    def test_invalid_blueprint_competency(self):
        buf = _xlsx_bytes([_ba_row("U12-BAD-COMP", blueprint_competency="C999")])
        preview = QuestionImportService.preview(buf, blueprint=self.blueprint)
        self.assertEqual(preview.invalid, 1)

    def test_invalid_cognitive_level(self):
        buf = _xlsx_bytes([_ba_row("U12-BAD-COG", cognitive_level="analysis")])
        preview = QuestionImportService.preview(buf, blueprint=self.blueprint)
        self.assertEqual(preview.invalid, 1)

    def test_uncertain_mapping_imports_as_draft_needs_review(self):
        buf = _xlsx_bytes(
            [
                _ba_row(
                    "U12-UNCERTAIN",
                    blueprint_category="",
                    blueprint_competency="",
                    cognitive_level="",
                    status="published",
                )
            ]
        )
        report = QuestionImportService.commit(
            buf, actor=self.editor, blueprint=self.blueprint
        )
        self.assertEqual(report.created, 1)
        q = Question.objects.get(question_code="U12-UNCERTAIN")
        self.assertEqual(q.editorial_state, EditorialState.DRAFT)
        self.assertTrue(q.needs_review)
        self.assertIsNone(q.blueprint_category_id)
        pool = BlueprintService.eligible_pool_qs()
        self.assertFalse(pool.filter(pk=q.pk).exists())


class TransactionalSafetyTests(TestCase):
    def setUp(self):
        self.editor = _staff_user("u12-tx@example.com", RoleCode.EDITOR)
        self.blueprint = ExamBlueprint.objects.get(code="BNMC_2018")

    def test_invalid_workbook_zero_writes(self):
        before_q = Question.objects.count()
        before_b = QuestionImportBatch.objects.count()
        buf = _xlsx_bytes(
            [_ba_row("U12-OK-SKIP"), _tf_row("U12-BAD", correct_answer="junk")]
        )
        with self.assertRaises(ImportCommitError):
            QuestionImportService.commit(
                buf, actor=self.editor, blueprint=self.blueprint
            )
        self.assertEqual(Question.objects.count(), before_q)
        self.assertEqual(QuestionImportBatch.objects.count(), before_b)
        self.assertFalse(Question.objects.filter(question_code="U12-OK-SKIP").exists())

    def test_malformed_workbook_rejected(self):
        buf = _xlsx_bytes([{"question_code": "X"}], header=["question_code"])
        with self.assertRaises(ImportStructureError):
            QuestionImportService.parse(buf)


class TaxonomyAndScenarioTests(TestCase):
    def setUp(self):
        self.editor = _staff_user("u12-tax@example.com", RoleCode.EDITOR)
        self.blueprint = ExamBlueprint.objects.get(code="BNMC_2018")

    def test_subject_and_topic_canonicalized(self):
        self.assertEqual(len(CONTENT_SUBJECTS), 15)
        self.assertIn("CSF", CROSS_CUTTING_TOPICS)
        buf = _xlsx_bytes(
            [
                _tf_row(
                    "U12-SCEN-TF",
                    scenario="A simulated adult is admitted after a fall.",
                    scenario_based="true",
                    subject="fundamentals of nursing",
                    topic="csf",
                ),
                _ba_row(
                    "U12-SCEN-BA",
                    scenario="Simulated labour ward handover.",
                    scenario_based="true",
                    subject="Midwifery and Obstetrical Nursing",
                ),
            ]
        )
        QuestionImportService.commit(buf, actor=self.editor, blueprint=self.blueprint)
        tf = Question.objects.get(question_code="U12-SCEN-TF")
        ba = Question.objects.get(question_code="U12-SCEN-BA")
        self.assertEqual(tf.content_subject, "Fundamentals of Nursing")
        self.assertEqual(tf.content_topic, "CSF")
        self.assertTrue(tf.scenario_based)
        self.assertTrue(ba.scenario_based)
        self.assertEqual(tf.current_version.clinical_scenario_body[:10], "A simulate")


class ReviewWorkflowTests(TestCase):
    def setUp(self):
        self.editor = _staff_user("u12-rev@example.com", RoleCode.EDITOR)
        self.blueprint = ExamBlueprint.objects.get(code="BNMC_2018")

    def test_review_workflow_and_publish_safety(self):
        QuestionImportService.commit(
            _xlsx_bytes([_tf_row("U12-REV")]),
            actor=self.editor,
            blueprint=self.blueprint,
        )
        q = Question.objects.get(question_code="U12-REV")
        QuestionStaffService.workflow(
            actor=self.editor, question_id=q.id, action="submit_review"
        )
        q.refresh_from_db()
        self.assertEqual(q.editorial_state, EditorialState.REVIEW)
        QuestionStaffService.workflow(
            actor=self.editor, question_id=q.id, action="approve"
        )
        q.refresh_from_db()
        self.assertEqual(q.editorial_state, EditorialState.APPROVED)
        QuestionStaffService.workflow(
            actor=self.editor, question_id=q.id, action="publish"
        )
        q.refresh_from_db()
        self.assertEqual(q.editorial_state, EditorialState.PUBLISHED)

    def test_publish_blocked_when_needs_review(self):
        from apps.staff.services.questions import QuestionStaffError

        QuestionImportService.commit(
            _xlsx_bytes(
                [_ba_row("U12-BLOCK", blueprint_category="", cognitive_level="")]
            ),
            actor=self.editor,
            blueprint=self.blueprint,
        )
        q = Question.objects.get(question_code="U12-BLOCK")
        q.editorial_state = EditorialState.APPROVED
        q.save(update_fields=["editorial_state"])
        with self.assertRaises(QuestionStaffError):
            QuestionStaffService.workflow(
                actor=self.editor, question_id=q.id, action="publish"
            )
        q.refresh_from_db()
        self.assertEqual(q.editorial_state, EditorialState.APPROVED)

    def test_classification_and_review_state_edit(self):
        QuestionImportService.commit(
            _xlsx_bytes(
                [_ba_row("U12-CLASS", blueprint_category="", cognitive_level="")]
            ),
            actor=self.editor,
            blueprint=self.blueprint,
        )
        q = Question.objects.get(question_code="U12-CLASS")
        cat = self.blueprint.categories.get(code="FUNDAMENTALS")
        QuestionStaffService.update_classification(
            actor=self.editor,
            question=q,
            content_subject="Pharmacology for Nurses",
            content_topic="Nutrition and Vitamins",
            cognitive_level=CognitiveLevel.APPLICATION,
            blueprint_category_id=cat.id,
            needs_review=False,
        )
        q.refresh_from_db()
        self.assertEqual(q.content_subject, "Pharmacology for Nurses")
        self.assertEqual(q.cognitive_level, CognitiveLevel.APPLICATION)
        self.assertFalse(q.needs_review)
        QuestionStaffService.update_review_state(
            actor=self.editor, question=q, needs_review=True
        )
        q.refresh_from_db()
        self.assertTrue(q.needs_review)


class EligibilityAndBlueprintShortfallTests(TestCase):
    def setUp(self):
        self.editor = _staff_user("u12-elig@example.com", RoleCode.EDITOR)
        self.blueprint = ExamBlueprint.objects.get(code="BNMC_2018")

    def test_published_only_eligibility(self):
        QuestionImportService.commit(
            _xlsx_bytes([_tf_row("U12-DRAFT-ELIG"), _ba_row("U12-PUB-ELIG", status="published")]),
            actor=self.editor,
            blueprint=self.blueprint,
        )
        draft = Question.objects.get(question_code="U12-DRAFT-ELIG")
        published = Question.objects.get(question_code="U12-PUB-ELIG")
        self.assertEqual(draft.editorial_state, EditorialState.DRAFT)
        self.assertEqual(published.editorial_state, EditorialState.PUBLISHED)
        pool_ids = set(BlueprintService.eligible_pool_qs().values_list("id", flat=True))
        self.assertNotIn(draft.id, pool_ids)
        self.assertIn(published.id, pool_ids)

    def test_blueprint_shortfall_no_silent_substitution(self):
        plan = BlueprintService.plan(self.blueprint)
        self.assertEqual(plan.status, STATUS_INSUFFICIENT)
        self.assertTrue(plan.shortages)
        self.assertEqual(plan.selected_question_ids, [])
        generated = BlueprintService.generate(self.blueprint)
        self.assertEqual(generated.status, STATUS_INSUFFICIENT)
        self.assertEqual(generated.selected_question_ids, [])
        self.assertNotEqual(generated.status, STATUS_COMPLIANT)


class ScoringAndTimerTests(TestCase):
    def setUp(self):
        self.user, _ = AccountService.register(
            email="u12-score@example.com", password=STRONG_PASSWORD, full_name="Score12"
        )
        self.editor = _staff_user("u12-score-ed@example.com", RoleCode.EDITOR)
        self.blueprint = ExamBlueprint.objects.get(code="BNMC_2018")
        QuestionImportService.commit(
            _xlsx_bytes(
                [
                    _tf_row("U12-SCORE-TF", status="published"),
                    _ba_row("U12-SCORE-BA", status="published"),
                ]
            ),
            actor=self.editor,
            blueprint=self.blueprint,
        )
        self.tf = Question.objects.get(question_code="U12-SCORE-TF")
        self.ba = Question.objects.get(question_code="U12-SCORE-BA")

    def test_tf_partial_scoring(self):
        selected = {"truths": {"a": True, "b": True, "c": True, "e": True}}
        item = _attempt_item(self.user, self.tf, self.tf.current_version, selected)
        is_correct, points = score_item_detail(item)
        self.assertFalse(is_correct)
        self.assertAlmostEqual(points, 3 * TRUE_FALSE_STATEMENT_MARK)

    def test_unanswered_tf_is_zero(self):
        item = _attempt_item(self.user, self.tf, self.tf.current_version, None)
        is_correct, points = score_item_detail(item)
        self.assertIsNone(is_correct)
        self.assertEqual(points, 0.0)

    def test_no_negative_marking(self):
        QuestionImportService.commit(
            _xlsx_bytes(
                [
                    _tf_row(
                        "U12-NEG-TF",
                        status="published",
                        correct_answer="A=TRUE,B=TRUE,C=TRUE,D=TRUE,E=TRUE",
                    )
                ]
            ),
            actor=self.editor,
            blueprint=self.blueprint,
        )
        q = Question.objects.get(question_code="U12-NEG-TF")
        selected = {"truths": {k: False for k in ("a", "b", "c", "d", "e")}}
        item = _attempt_item(self.user, q, q.current_version, selected)
        is_correct, points = score_item_detail(item)
        self.assertFalse(is_correct)
        self.assertEqual(points, 0.0)

    def test_ba_scoring(self):
        right = _attempt_item(self.user, self.ba, self.ba.current_version, {"key": "b"})
        wrong = _attempt_item(self.user, self.ba, self.ba.current_version, {"key": "a"})
        none = _attempt_item(self.user, self.ba, self.ba.current_version, None)
        self.assertEqual(score_item_detail(right), (True, 1.0))
        self.assertEqual(score_item_detail(wrong), (False, 0.0))
        self.assertEqual(score_item_detail(none), (None, 0.0))

    def test_timer_30_45_60(self):
        self.assertEqual(ALLOWED_SECONDS_PER_QUESTION, (30, 45, 60))
        for sec in ALLOWED_SECONDS_PER_QUESTION:
            self.assertEqual(
                compute_time_limit_seconds(question_count=10, seconds_per_question=sec),
                10 * sec,
            )


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"],
)
class SecurityAndProvenanceTests(TestCase):
    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)
        self.student, _ = AccountService.register(
            email="u12-stu@example.com", password=STRONG_PASSWORD, full_name="Stu12"
        )
        self.other, _ = AccountService.register(
            email="u12-other@example.com", password=STRONG_PASSWORD, full_name="Oth12"
        )
        self.admin = _staff_user("u12-admin@example.com", RoleCode.ADMIN)
        self.editor = _staff_user("u12-sec-ed@example.com", RoleCode.EDITOR)
        self.blueprint = ExamBlueprint.objects.get(code="BNMC_2018")
        QuestionImportService.commit(
            _xlsx_bytes([_tf_row("U12-SEC-TF", status="published")]),
            actor=self.editor,
            blueprint=self.blueprint,
        )
        self.question = Question.objects.get(question_code="U12-SEC-TF")

    def _login(self, email):
        url = reverse("accounts:login")
        self.client.get(url)
        return self.client.post(
            url,
            {
                "email": email,
                "password": STRONG_PASSWORD,
                "next": "",
                "csrfmiddlewaretoken": self.client.cookies["csrftoken"].value,
            },
        )

    def test_provenance_admin_only(self):
        view = QuestionStaffService.admin_source_view(self.editor, self.question)
        self.assertEqual(view["source_name"], "UNIT-12 synthetic fixture")
        self.assertIsNone(
            QuestionStaffService.provenance_for(self.editor, self.question)
        )
        admin_view = QuestionStaffService.provenance_for(self.admin, self.question)
        self.assertIsNotNone(admin_view)
        self.assertEqual(admin_view["source_page"], "1")
        self._login(self.admin.email)
        resp = self.client.get(
            reverse("staff:question_detail", kwargs={"question_id": self.question.id})
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "UNIT-12 synthetic fixture")
        self.assertContains(resp, "Answer key (staff only)")

    def test_student_cannot_see_source_or_answer_key_before_submission(self):
        item = _attempt_item(
            self.student, self.question, self.question.current_version, None
        )
        payload = PracticePresentationService.session(
            self.student, item.attempt, item.position
        )
        self.assertFalse(payload["reveal_answers"])
        self.assertEqual(payload["explanation"], "")
        self.assertNotIn("source_name", payload)
        self.assertNotIn("source_page", payload)
        self.assertNotIn("source_reference", payload)
        self.assertNotIn("source_type", payload)
        for statement in payload["statements"]:
            self.assertIsNone(statement["correct"])
            self.assertFalse(statement["show_correctness"])
        blob = str(payload)
        self.assertNotIn("UNIT-12 synthetic fixture", blob)
        self.assertNotIn("A=TRUE", blob)

    def test_student_idor_staff_question_and_foreign_attempt(self):
        self._login(self.student.email)
        staff_detail = self.client.get(
            reverse("staff:question_detail", kwargs={"question_id": self.question.id})
        )
        self.assertEqual(staff_detail.status_code, 403)
        item = _attempt_item(
            self.other, self.question, self.question.current_version, None
        )
        foreign = self.client.get(
            reverse(
                "assessment:session",
                kwargs={"attempt_id": item.attempt.id, "position": 1},
            )
        )
        self.assertIn(foreign.status_code, {403, 404})

    def test_import_history_and_template_are_staff_only(self):
        self._login(self.student.email)
        self.assertEqual(
            self.client.get(reverse("staff:questions_import_history")).status_code, 403
        )
        self.assertEqual(
            self.client.get(reverse("staff:questions_import_template")).status_code, 403
        )
        self.client.logout()
        self._login(self.admin.email)
        hist = self.client.get(reverse("staff:questions_import_history"))
        self.assertEqual(hist.status_code, 200)
        tmpl = self.client.get(reverse("staff:questions_import_template"))
        self.assertEqual(tmpl.status_code, 200)
        self.assertIn(
            "spreadsheetml",
            tmpl["Content-Type"],
        )
        payload = build_example_workbook()
        self.assertGreater(len(payload), 100)
        self.assertNotIn(b"March 2025", payload)
        self.assertEqual(
            self.client.get(
                reverse("staff:questions_import_template_author")
            ).status_code,
            200,
        )
        self.client.logout()
        self._login(self.student.email)
        self.assertEqual(
            self.client.get(
                reverse("staff:questions_import_template_author")
            ).status_code,
            403,
        )


class PracticeExamVerificationTests(TestCase):
    def setUp(self):
        self.user, _ = AccountService.register(
            email="u12-prac@example.com", password=STRONG_PASSWORD, full_name="Prac12"
        )
        self.editor = _staff_user("u12-prac-ed@example.com", RoleCode.EDITOR)
        self.blueprint = ExamBlueprint.objects.get(code="BNMC_2018")

    def test_imported_published_tf_ba_enter_practice_shape(self):
        QuestionImportService.commit(
            _xlsx_bytes(
                [
                    _tf_row("U12-PRAC-TF", status="published", scenario_based="true", scenario="U12 practice scenario"),
                    _ba_row("U12-PRAC-BA", status="published"),
                ]
            ),
            actor=self.editor,
            blueprint=self.blueprint,
        )
        tf = Question.objects.get(question_code="U12-PRAC-TF")
        ba = Question.objects.get(question_code="U12-PRAC-BA")
        tf_item = _attempt_item(self.user, tf, tf.current_version, None)
        ba_item = _attempt_item(self.user, ba, ba.current_version, None)
        tf_session = PracticePresentationService.session(
            self.user, tf_item.attempt, 1
        )
        ba_session = PracticePresentationService.session(
            self.user, ba_item.attempt, 1
        )
        self.assertTrue(tf_session["is_true_false"])
        self.assertEqual(len(tf_session["statements"]), 5)
        self.assertEqual(len(ba_session["options"]), 4)
        self.assertEqual(tf.question_type, QuestionType.TRUE_FALSE)
        self.assertEqual(ba.question_type, QuestionType.BEST_ANSWER)

    def test_exam_pool_skips_unpublished_imported_rows(self):
        QuestionImportService.commit(
            _xlsx_bytes([_ba_row("U12-EXAM-DRAFT"), _ba_row("U12-EXAM-PUB", status="published")]),
            actor=self.editor,
            blueprint=self.blueprint,
        )
        draft = Question.objects.get(question_code="U12-EXAM-DRAFT")
        published = Question.objects.get(question_code="U12-EXAM-PUB")
        exam = ExamDefinition.objects.create(
            code="U12-EXAM",
            title_key="unit12.synthetic.exam",
            mode=AttemptMode.TIMED_EXAM,
            editorial_state=EditorialState.PUBLISHED,
        )
        ExamDefinitionItem.objects.create(
            exam_definition=exam, question=draft, sort_order=1
        )
        ExamDefinitionItem.objects.create(
            exam_definition=exam, question=published, sort_order=2
        )
        selected = ExamPoolService.select_questions(exam)
        self.assertEqual([q.question_code for q in selected], ["U12-EXAM-PUB"])

    def test_list_filters_subject_topic_scenario_needs_review(self):
        QuestionImportService.commit(
            _xlsx_bytes(
                [
                    _tf_row("U12-FILT-TF", scenario_based="true", scenario="s"),
                    _ba_row("U12-FILT-BA"),
                ]
            ),
            actor=self.editor,
            blueprint=self.blueprint,
        )
        page = QuestionStaffService.list_questions(
            self.editor,
            content_subject="Fundamentals of Nursing",
            scenario_based=True,
        )
        codes = {q.question_code for q in page}
        self.assertIn("U12-FILT-TF", codes)
        self.assertNotIn("U12-FILT-BA", codes)
        search = QuestionStaffService.list_questions(self.editor, q="U12-FILT-BA")
        self.assertTrue(any(q.question_code == "U12-FILT-BA" for q in search))


class TranscribedSourceFixtureTests(TestCase):
    def test_transcribed_rows_are_unique_and_previewable(self):
        from apps.assessment.data.bnmc_march_2025 import (
            BEST_ANSWER_ROWS,
            REAL_ROWS,
            TRUE_FALSE_ROWS,
        )

        codes = [r["question_code"] for r in REAL_ROWS]
        self.assertEqual(len(codes), len(set(codes)))
        self.assertEqual(len(TRUE_FALSE_ROWS), 22)
        self.assertEqual(len(BEST_ANSWER_ROWS), 29)
        self.assertEqual(len(REAL_ROWS), 51)
        editor = _staff_user("u12-real@example.com", RoleCode.EDITOR)
        blueprint = ExamBlueprint.objects.get(code="BNMC_2018")
        from openpyxl import Workbook

        header = list(REQUIRED_COLUMNS)
        wb = Workbook()
        ws = wb.active
        ws.append(header)
        for row in REAL_ROWS:
            ws.append([row.get(col, "") for col in header])
        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        preview = QuestionImportService.preview(buf, blueprint=blueprint)
        self.assertFalse(preview.has_invalid, preview.errors[:5])
        self.assertEqual(preview.valid, 51)
        self.assertEqual(preview.needs_review, 51)
        self.assertIsNotNone(editor)


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"],
)
class QuestionBankWorkflowTests(TestCase):
    """Bulk workflow 2.0 — does not weaken UNIT-11/12 importer or scoring tests."""

    def setUp(self):
        self.editor = _staff_user("u12-wf-ed@example.com", RoleCode.EDITOR)
        self.author = _staff_user("u12-wf-au@example.com", RoleCode.AUTHOR)
        self.blueprint = ExamBlueprint.objects.get(code="BNMC_2018")
        self.client = Client()

    def _commit(self, *rows):
        return QuestionImportService.commit(
            _xlsx_bytes(list(rows)),
            actor=self.editor,
            blueprint=self.blueprint,
        )

    def test_bulk_submit_approve_publish_and_partial_failure(self):
        self._commit(
            _tf_row("U12-WF-OK1"),
            _tf_row("U12-WF-OK2"),
            _ba_row("U12-WF-PUB", status="published"),
        )
        ok1 = Question.objects.get(question_code="U12-WF-OK1")
        ok2 = Question.objects.get(question_code="U12-WF-OK2")
        published = Question.objects.get(question_code="U12-WF-PUB")
        result = QuestionStaffService.bulk_submit_review(
            actor=self.editor,
            question_ids=[ok1.id, ok2.id, published.id],
        )
        self.assertEqual(result.selected, 3)
        self.assertEqual(result.succeeded, 2)
        self.assertEqual(result.failed, 1)
        ok1.refresh_from_db()
        ok2.refresh_from_db()
        published.refresh_from_db()
        self.assertEqual(ok1.editorial_state, EditorialState.REVIEW)
        self.assertEqual(ok2.editorial_state, EditorialState.REVIEW)
        self.assertEqual(published.editorial_state, EditorialState.PUBLISHED)

        approved = QuestionStaffService.bulk_approve(
            actor=self.editor, question_ids=[ok1.id, ok2.id]
        )
        self.assertEqual(approved.succeeded, 2)
        ok1.refresh_from_db()
        self.assertEqual(ok1.editorial_state, EditorialState.APPROVED)

        published_result = QuestionStaffService.bulk_publish(
            actor=self.editor, question_ids=[ok1.id, ok2.id]
        )
        self.assertEqual(published_result.succeeded, 2)
        ok1.refresh_from_db()
        self.assertEqual(ok1.editorial_state, EditorialState.PUBLISHED)

    def test_bulk_submit_rejects_invalid_structure(self):
        self._commit(_ba_row("U12-WF-BAD"))
        q = Question.objects.get(question_code="U12-WF-BAD")
        q.current_version.options.all().delete()
        result = QuestionStaffService.bulk_submit_review(
            actor=self.editor, question_ids=[q.id]
        )
        self.assertEqual(result.succeeded, 0)
        self.assertEqual(result.failed, 1)
        self.assertIn("Validation failed", result.failures[0].reason)
        q.refresh_from_db()
        self.assertEqual(q.editorial_state, EditorialState.DRAFT)

    def test_author_cannot_bulk_approve(self):
        self._commit(_tf_row("U12-WF-AUTH"))
        q = Question.objects.get(question_code="U12-WF-AUTH")
        QuestionStaffService.workflow(
            actor=self.editor, question_id=q.id, action="submit_review"
        )
        result = QuestionStaffService.bulk_approve(
            actor=self.author, question_ids=[q.id]
        )
        self.assertEqual(result.succeeded, 0)
        self.assertEqual(result.failed, 1)
        q.refresh_from_db()
        self.assertEqual(q.editorial_state, EditorialState.REVIEW)

    def test_bulk_classify_validates_category_competency(self):
        self._commit(_ba_row("U12-WF-CL"))
        q = Question.objects.get(question_code="U12-WF-CL")
        cat = self.blueprint.categories.get(code="FUNDAMENTALS")
        other = self.blueprint.categories.get(code="COMMUNICATION")
        competency = other.competencies.first()
        with self.assertRaises(QuestionStaffError):
            QuestionStaffService.bulk_classify(
                actor=self.editor,
                question_ids=[q.id],
                blueprint_category_id=cat.id,
                blueprint_competency_id=competency.id,
            )
        cat_fund = self.blueprint.categories.get(code="NURSING_PROCESS")
        result = QuestionStaffService.bulk_classify(
            actor=self.editor,
            question_ids=[q.id],
            content_subject="Fundamentals of Nursing",
            cognitive_level=CognitiveLevel.RECALL,
            blueprint_category_id=cat_fund.id,
        )
        self.assertEqual(result.succeeded, 1)
        q.refresh_from_db()
        self.assertEqual(q.content_subject, "Fundamentals of Nursing")
        self.assertEqual(q.blueprint_category_id, cat_fund.id)
        self.assertIsNone(q.blueprint_competency_id)

    def test_march_2025_prefix_blocked_from_bulk_classify_and_publish(self):
        self._commit(
            _tf_row(
                "BNMC-2025-03-TF-099",
                question_text="SYNTHETIC protection fixture — not a real exam item.",
            )
        )
        q = Question.objects.get(question_code="BNMC-2025-03-TF-099")
        classify = QuestionStaffService.bulk_classify(
            actor=self.editor,
            question_ids=[q.id],
            content_subject="Fundamentals of Nursing",
        )
        self.assertEqual(classify.succeeded, 0)
        self.assertIn("March 2025", classify.failures[0].reason)
        q.editorial_state = EditorialState.APPROVED
        q.save(update_fields=["editorial_state"])
        published = QuestionStaffService.bulk_publish(
            actor=self.editor, question_ids=[q.id]
        )
        self.assertEqual(published.succeeded, 0)
        q.refresh_from_db()
        self.assertEqual(q.editorial_state, EditorialState.APPROVED)

    def test_duplicate_warning_and_dismiss(self):
        from apps.assessment.services.duplicates import QuestionDuplicateService

        self._commit(
            _ba_row("U12-WF-DUP1", question_text="Identical synthetic stem for duplicate."),
            _ba_row("U12-WF-DUP2", question_text="Identical synthetic stem for duplicate."),
        )
        a = Question.objects.get(question_code="U12-WF-DUP1")
        b = Question.objects.get(question_code="U12-WF-DUP2")
        hits = QuestionDuplicateService.find_for(a)
        self.assertTrue(any(h.other_code == "U12-WF-DUP2" for h in hits))
        QuestionStaffService.dismiss_duplicate(
            actor=self.editor, question=a, other_id=b.id
        )
        hits_after = QuestionDuplicateService.find_for(a)
        self.assertFalse(any(h.other_code == "U12-WF-DUP2" for h in hits_after))
        self.assertEqual(Question.objects.filter(question_code__startswith="U12-WF-DUP").count(), 2)

    def test_blueprint_suggestion_exact_subject_only(self):
        from apps.assessment.services.blueprint_suggest import BlueprintSuggestionService

        self._commit(_tf_row("U12-WF-SUG", subject="Fundamentals of Nursing"))
        q = Question.objects.get(question_code="U12-WF-SUG")
        suggestion = BlueprintSuggestionService.suggest(q)
        self.assertTrue(suggestion.confident)
        self.assertEqual(suggestion.category_name, "Fundamentals of Nursing")
        self._commit(_ba_row("U12-WF-NOSUG", subject="Pharmacology for Nurses"))
        other = Question.objects.get(question_code="U12-WF-NOSUG")
        none = BlueprintSuggestionService.suggest(other)
        self.assertFalse(none.confident)
        self.assertEqual(none.reason, "No confident suggestion")

    def test_author_template_remains_import_compatible(self):
        from apps.assessment.services.import_template import (
            AUTHOR_TEMPLATE_FILENAME,
            build_author_workbook,
            build_example_workbook,
        )

        original = build_example_workbook()
        author = build_author_workbook()
        self.assertGreater(len(original), 100)
        self.assertGreater(len(author), 100)
        self.assertEqual(
            AUTHOR_TEMPLATE_FILENAME,
            "nursilo-question-import-template-author.xlsx",
        )
        preview = QuestionImportService.preview(
            io.BytesIO(author), blueprint=self.blueprint
        )
        self.assertFalse(preview.has_invalid, preview.errors[:5])
        self.assertGreaterEqual(preview.valid, 2)

    def test_list_http_bulk_select_and_queue_counts(self):
        self._commit(_tf_row("U12-WF-HTTP"))
        q = Question.objects.get(question_code="U12-WF-HTTP")
        self.client.force_login(self.editor)
        listing = self.client.get(reverse("staff:questions"))
        self.assertEqual(listing.status_code, 200)
        self.assertContains(listing, "Select all visible")
        self.assertContains(listing, "Submit for review")
        self.assertContains(listing, "Draft")
        post = self.client.post(
            reverse("staff:questions"),
            {"intent": "bulk_submit", "question_ids": [str(q.id)]},
        )
        self.assertEqual(post.status_code, 302)
        q.refresh_from_db()
        self.assertEqual(q.editorial_state, EditorialState.REVIEW)
        student, _ = AccountService.register(
            email="u12-wf-stu@example.com",
            password=STRONG_PASSWORD,
            full_name="WF Student",
        )
        self.client.force_login(student)
        denied = self.client.get(reverse("staff:questions"))
        self.assertEqual(denied.status_code, 403)
        self.assertNotContains(denied, q.question_code, status_code=403)

