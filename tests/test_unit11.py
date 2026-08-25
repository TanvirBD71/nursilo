"""
UNIT-11 — Real Question Bank + Exam Blueprint Foundation tests.

Covers the new question types (TRUE/FALSE + BEST_ANSWER), partial True/False
scoring, server-authoritative answer normalization, the data-driven BNMC
blueprint seed, blueprint-driven generation compliance/shortage reporting, the
timer configuration helper, and the Excel import FOUNDATION
(parse/validate/preview/commit + idempotency + transactional safety), plus the
staff RBAC + admin-only provenance surface.

These tests do NOT weaken UNIT-5/6: they only add coverage for new behavior and
assert the existing ScoreSummary contract (``score`` / ``percent_correct``) is
preserved alongside the new partial-aware ``points`` / ``percent`` keys.
"""
from __future__ import annotations

import io
import unittest

from django.db import connection
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.accounts.services import AccountService
from apps.accounts.models import UserAccount
from apps.assessment.models import (
    Attempt,
    AttemptItem,
    BlueprintCategory,
    BlueprintCompetency,
    ExamBlueprint,
    Question,
    QuestionOption,
    QuestionOptionTranslation,
    QuestionVersion,
    QuestionVersionTranslation,
)
from apps.assessment.services.answers import normalize_answer
from apps.assessment.services.blueprint import (
    STATUS_COMPLIANT,
    STATUS_INSUFFICIENT,
    BlueprintService,
)
from apps.assessment.services.import_questions import (
    ImportCommitError,
    ImportStructureError,
    QuestionImportService,
    REQUIRED_COLUMNS,
)
from apps.assessment.services.scoring import (
    TRUE_FALSE_STATEMENT_MARK,
    build_score_summary,
    score_item_detail,
)
from apps.assessment.services.timer import (
    ALLOWED_SECONDS_PER_QUESTION,
    compute_time_limit_seconds,
)
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

STRONG_PASSWORD = "Str0ng-Pass!Unit11"


def setUpModule():
    try:
        connection.ensure_connection()
    except Exception as exc:  # pragma: no cover
        raise unittest.SkipTest(f"PostgreSQL unavailable for UNIT-11: {exc}") from exc


def _assign(user, *role_codes):
    for code in role_codes:
        role = Role.objects.get(code=code)
        RoleAssignment.objects.get_or_create(user=user, role=role)


def _staff_user(email, *role_codes):
    user = UserAccount.objects.create_user(
        email=email, password=STRONG_PASSWORD, full_name="Staff Eleven"
    )
    _assign(user, *role_codes)
    return user


def _make_true_false(
    *,
    truths=None,
    statements=None,
    editorial_state=EditorialState.PUBLISHED,
    blueprint_category=None,
    cognitive_level=None,
    question_code=None,
):
    """Test-only TRUE/FALSE factory (5 statements a–e)."""
    truths = truths or {"a": True, "b": False, "c": True, "d": False, "e": True}
    statements = statements or {k: f"Statement {k}" for k in ("a", "b", "c", "d", "e")}
    question = Question.objects.create(
        question_type=QuestionType.TRUE_FALSE,
        editorial_state=editorial_state,
        primary_locale=LocaleCode.EN,
        blueprint_category=blueprint_category,
        cognitive_level=cognitive_level,
        question_code=question_code,
    )
    version = QuestionVersion.objects.create(
        question=question,
        version_no=1,
        correct_answer_spec={"type": "true_false", "truths": truths},
    )
    QuestionVersionTranslation.objects.create(
        version=version, locale=LocaleCode.EN, stem="Mark each statement."
    )
    for order, key in enumerate(("a", "b", "c", "d", "e")):
        opt = QuestionOption.objects.create(
            question_version=version,
            key=key,
            is_correct=bool(truths.get(key)),
            sort_order=order,
        )
        QuestionOptionTranslation.objects.create(
            option=opt, locale=LocaleCode.EN, label=statements[key]
        )
    question.current_version = version
    question.save(update_fields=["current_version", "updated_at"])
    return question, version


def _make_best_answer(
    *,
    correct_key="a",
    editorial_state=EditorialState.PUBLISHED,
    blueprint_category=None,
    cognitive_level=None,
    question_code=None,
):
    """Test-only BEST_ANSWER factory (4 options a–d, one correct)."""
    question = Question.objects.create(
        question_type=QuestionType.BEST_ANSWER,
        editorial_state=editorial_state,
        primary_locale=LocaleCode.EN,
        blueprint_category=blueprint_category,
        cognitive_level=cognitive_level,
        question_code=question_code,
    )
    version = QuestionVersion.objects.create(
        question=question,
        version_no=1,
        correct_answer_spec={"key": correct_key},
    )
    QuestionVersionTranslation.objects.create(
        version=version, locale=LocaleCode.EN, stem="Pick the best answer."
    )
    for order, key in enumerate(("a", "b", "c", "d")):
        opt = QuestionOption.objects.create(
            question_version=version,
            key=key,
            is_correct=(key == correct_key),
            sort_order=order,
        )
        QuestionOptionTranslation.objects.create(
            option=opt, locale=LocaleCode.EN, label=f"Option {key}"
        )
    question.current_version = version
    question.save(update_fields=["current_version", "updated_at"])
    return question, version


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


def _xlsx_bytes(rows, *, header=None):
    """Build an in-memory .xlsx workbook from dict rows keyed by column name."""
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
        "question_text": "Mark each statement true or false.",
        "scenario": "",
        "option_a": "Statement A",
        "option_b": "Statement B",
        "option_c": "Statement C",
        "option_d": "Statement D",
        "option_e": "Statement E",
        "correct_answer": "A=TRUE,B=FALSE,C=TRUE,D=FALSE,E=TRUE",
        "explanation": "Because.",
        "blueprint_category": "Nursing Process",
        "blueprint_competency": "",
        "subject": "Fundamentals",
        "topic": "Assessment",
        "cognitive_level": "recall",
        "difficulty": "",
        "scenario_based": "false",
        "source_name": "March 2025 Exam",
        "source_page": "3",
        "source_reference": "Q1",
        "status": "draft",
    }
    row.update(overrides)
    return row


def _ba_row(code, **overrides):
    row = {
        "question_code": code,
        "question_type": "BEST_ANSWER",
        "question_text": "Pick the best answer.",
        "scenario": "",
        "option_a": "Alpha",
        "option_b": "Beta",
        "option_c": "Gamma",
        "option_d": "Delta",
        "option_e": "",
        "correct_answer": "B",
        "explanation": "Beta is correct.",
        "blueprint_category": "Communication",
        "blueprint_competency": "",
        "subject": "Comms",
        "topic": "Therapeutic",
        "cognitive_level": "understanding",
        "difficulty": "medium",
        "scenario_based": "false",
        "source_name": "",
        "source_page": "",
        "source_reference": "",
        "status": "published",
    }
    row.update(overrides)
    return row


class BlueprintSeedTests(TestCase):
    def test_bnmc_blueprint_seeded_exactly(self):
        bp = ExamBlueprint.objects.get(code="BNMC_2018")
        self.assertTrue(bp.is_active)
        self.assertEqual(bp.total_questions, 100)
        self.assertEqual(bp.version_label, "November 2018")

        cats = {c.code: c for c in bp.categories.all()}
        self.assertEqual(sum(c.question_count for c in cats.values()), 100)
        self.assertEqual(cats["NURSING_PROCESS"].question_count, 15)
        self.assertEqual(cats["FUNDAMENTALS"].question_count, 30)
        self.assertEqual(cats["GENERAL_NURSING_CARE"].question_count, 33)
        self.assertEqual(cats["COMMUNICATION"].question_count, 10)
        self.assertEqual(cats["PROFESSIONALISM_LEADERSHIP"].question_count, 12)

        self.assertEqual(
            BlueprintCompetency.objects.filter(category__blueprint=bp).count(), 40
        )
        # Category competency counts match the source tables.
        self.assertEqual(cats["NURSING_PROCESS"].competencies.count(), 6)
        self.assertEqual(cats["FUNDAMENTALS"].competencies.count(), 12)
        self.assertEqual(cats["GENERAL_NURSING_CARE"].competencies.count(), 13)
        self.assertEqual(cats["COMMUNICATION"].competencies.count(), 4)
        self.assertEqual(cats["PROFESSIONALISM_LEADERSHIP"].competencies.count(), 5)

        cog = {a.cognitive_level: a.percent for a in bp.cognitive_allocations.all()}
        self.assertEqual(cog[CognitiveLevel.RECALL], 50)
        self.assertEqual(cog[CognitiveLevel.UNDERSTANDING], 25)
        self.assertEqual(cog[CognitiveLevel.APPLICATION], 25)

    def test_per_category_competency_counts_sum_to_allocation(self):
        bp = ExamBlueprint.objects.get(code="BNMC_2018")
        for cat in bp.categories.all():
            total = sum(c.question_count for c in cat.competencies.all())
            self.assertEqual(
                total, cat.question_count, f"{cat.code} competency counts mismatch"
            )


class ScoringTests(TestCase):
    def setUp(self):
        self.user, _ = AccountService.register(
            email="score11@example.com", password=STRONG_PASSWORD, full_name="Score"
        )

    def test_true_false_partial_scoring(self):
        truths = {"a": True, "b": False, "c": True, "d": False, "e": True}
        _q, version = _make_true_false(truths=truths)
        # 3 correct (a,c,e), 1 wrong (b), 1 unanswered (d)
        selected = {"truths": {"a": True, "b": True, "c": True, "e": True}}
        item = _attempt_item(self.user, _q, version, selected)
        is_correct, points = score_item_detail(item)
        self.assertFalse(is_correct)
        self.assertAlmostEqual(points, 3 * TRUE_FALSE_STATEMENT_MARK)

    def test_true_false_all_correct(self):
        truths = {"a": True, "b": False, "c": True, "d": False, "e": True}
        _q, version = _make_true_false(truths=truths)
        item = _attempt_item(self.user, _q, version, {"truths": dict(truths)})
        is_correct, points = score_item_detail(item)
        self.assertTrue(is_correct)
        self.assertAlmostEqual(points, 1.0)

    def test_true_false_unanswered_is_none_zero(self):
        _q, version = _make_true_false()
        item = _attempt_item(self.user, _q, version, None)
        is_correct, points = score_item_detail(item)
        self.assertIsNone(is_correct)
        self.assertEqual(points, 0.0)

    def test_true_false_no_negative_marking(self):
        truths = {"a": True, "b": True, "c": True, "d": True, "e": True}
        _q, version = _make_true_false(truths=truths)
        # all wrong
        selected = {"truths": {k: False for k in truths}}
        item = _attempt_item(self.user, _q, version, selected)
        is_correct, points = score_item_detail(item)
        self.assertFalse(is_correct)
        self.assertEqual(points, 0.0)

    def test_best_answer_scoring(self):
        _q, version = _make_best_answer(correct_key="b")
        correct_item = _attempt_item(self.user, _q, version, {"key": "b"})
        self.assertEqual(score_item_detail(correct_item), (True, 1.0))

        _q2, v2 = _make_best_answer(correct_key="b")
        wrong_item = _attempt_item(self.user, _q2, v2, {"key": "a"})
        self.assertEqual(score_item_detail(wrong_item), (False, 0.0))

        _q3, v3 = _make_best_answer(correct_key="b")
        unanswered = _attempt_item(self.user, _q3, v3, None)
        self.assertEqual(score_item_detail(unanswered), (None, 0.0))

    def test_score_summary_preserves_contract_and_adds_points(self):
        # Build items with known outcomes without persisting scores.
        class Fake:
            def __init__(self, is_correct, score):
                self.is_correct = is_correct
                self.score = score

        items = [
            Fake(True, 1.0),
            Fake(False, 0.4),  # TF partial
            Fake(None, 0.0),  # unanswered
        ]
        summary = build_score_summary(items)
        self.assertEqual(summary["total"], 3)
        self.assertEqual(summary["correct"], 1)
        self.assertEqual(summary["score"], 1)  # UNIT-5/6 contract: full-correct count
        self.assertEqual(summary["max_points"], 3)
        self.assertAlmostEqual(summary["points"], 1.4)
        self.assertIn("percent_correct", summary)
        self.assertIn("percent", summary)


class AnswerNormalizationTests(TestCase):
    def setUp(self):
        self.user, _ = AccountService.register(
            email="ans11@example.com", password=STRONG_PASSWORD, full_name="Ans"
        )

    def test_true_false_normalization(self):
        _q, version = _make_true_false()
        item = _attempt_item(self.user, _q, version, None)
        res = normalize_answer(item, truths={"a": "true", "b": "false"})
        self.assertTrue(res.ok)
        self.assertEqual(res.code, "saved")
        self.assertEqual(res.selected_answer, {"truths": {"a": True, "b": False}})

    def test_true_false_invalid_statement_key(self):
        _q, version = _make_true_false()
        item = _attempt_item(self.user, _q, version, None)
        res = normalize_answer(item, truths={"z": "true"})
        self.assertFalse(res.ok)
        self.assertEqual(res.code, "invalid_answer")

    def test_true_false_clear(self):
        _q, version = _make_true_false()
        item = _attempt_item(self.user, _q, version, None)
        res = normalize_answer(item, truths={})
        self.assertTrue(res.ok)
        self.assertTrue(res.clear)

    def test_best_answer_normalization(self):
        _q, version = _make_best_answer(correct_key="c")
        item = _attempt_item(self.user, _q, version, None)
        res = normalize_answer(item, option_key="a")
        self.assertTrue(res.ok)
        self.assertEqual(res.selected_answer, {"key": "a"})

    def test_best_answer_invalid_key(self):
        _q, version = _make_best_answer(correct_key="c")
        item = _attempt_item(self.user, _q, version, None)
        res = normalize_answer(item, option_key="z")
        self.assertFalse(res.ok)
        self.assertEqual(res.code, "invalid_answer")


class TimerConfigTests(TestCase):
    def test_total_time_is_count_times_seconds(self):
        self.assertEqual(
            compute_time_limit_seconds(question_count=100, seconds_per_question=60),
            6000,
        )
        for sec in ALLOWED_SECONDS_PER_QUESTION:
            self.assertEqual(
                compute_time_limit_seconds(question_count=10, seconds_per_question=sec),
                10 * sec,
            )

    def test_rejects_bad_pacing_and_counts(self):
        with self.assertRaises(ValueError):
            compute_time_limit_seconds(question_count=10, seconds_per_question=25)
        with self.assertRaises(ValueError):
            compute_time_limit_seconds(question_count=0, seconds_per_question=60)


class BlueprintGenerationTests(TestCase):
    def setUp(self):
        self.user, _ = AccountService.register(
            email="bp11@example.com", password=STRONG_PASSWORD, full_name="BP"
        )
        # Small custom blueprint for deterministic compliance testing.
        self.bp = ExamBlueprint.objects.create(
            code="TEST_BP",
            name="Test Blueprint",
            total_questions=4,
            is_active=False,
        )
        self.cat = BlueprintCategory.objects.create(
            blueprint=self.bp, code="TEST", name="Test Cat", percent=100,
            question_count=4, sort_order=1,
        )
        from apps.assessment.models import BlueprintCognitiveAllocation

        BlueprintCognitiveAllocation.objects.create(
            blueprint=self.bp, cognitive_level=CognitiveLevel.RECALL, percent=50,
            sort_order=1,
        )
        BlueprintCognitiveAllocation.objects.create(
            blueprint=self.bp, cognitive_level=CognitiveLevel.UNDERSTANDING,
            percent=50, sort_order=2,
        )

    def test_insufficient_pool_reports_shortage_and_no_selection(self):
        _make_best_answer(
            blueprint_category=self.cat, cognitive_level=CognitiveLevel.RECALL
        )
        plan = BlueprintService.generate(self.bp)
        self.assertEqual(plan.status, STATUS_INSUFFICIENT)
        self.assertFalse(plan.compliant)
        self.assertTrue(plan.shortages)
        self.assertEqual(plan.selected_question_ids, [])

    def test_compliant_pool_selects_exact_count(self):
        for _ in range(2):
            _make_best_answer(
                blueprint_category=self.cat, cognitive_level=CognitiveLevel.RECALL
            )
            _make_best_answer(
                blueprint_category=self.cat,
                cognitive_level=CognitiveLevel.UNDERSTANDING,
            )
        plan = BlueprintService.generate(self.bp)
        self.assertEqual(plan.status, STATUS_COMPLIANT)
        self.assertTrue(plan.compliant)
        self.assertEqual(len(plan.selected_question_ids), 4)

    def test_draft_questions_not_eligible(self):
        for _ in range(4):
            _make_best_answer(
                blueprint_category=self.cat,
                cognitive_level=CognitiveLevel.RECALL,
                editorial_state=EditorialState.DRAFT,
            )
        plan = BlueprintService.plan(self.bp)
        self.assertEqual(plan.status, STATUS_INSUFFICIENT)


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"],
)
class ExcelImportTests(TestCase):
    def setUp(self):
        self.editor = _staff_user("imp-editor@example.com", RoleCode.EDITOR)
        self.blueprint = ExamBlueprint.objects.get(code="BNMC_2018")

    def test_parse_rejects_missing_columns(self):
        buf = _xlsx_bytes([{"question_code": "X1"}], header=["question_code"])
        with self.assertRaises(ImportStructureError):
            QuestionImportService.parse(buf)

    def test_preview_valid_mixed_types(self):
        buf = _xlsx_bytes([_tf_row("TF-1"), _ba_row("BA-1")])
        preview = QuestionImportService.preview(buf, blueprint=self.blueprint)
        self.assertEqual(preview.total, 2)
        self.assertEqual(preview.valid, 2)
        self.assertEqual(preview.invalid, 0)
        self.assertTrue(preview.importable)

    def test_true_false_requires_five_truths(self):
        buf = _xlsx_bytes([_tf_row("TF-BAD", correct_answer="A=TRUE,B=FALSE")])
        preview = QuestionImportService.preview(buf, blueprint=self.blueprint)
        self.assertEqual(preview.invalid, 1)
        self.assertFalse(preview.importable)

    def test_best_answer_rejects_option_e(self):
        buf = _xlsx_bytes([_ba_row("BA-E", option_e="Extra")])
        preview = QuestionImportService.preview(buf, blueprint=self.blueprint)
        self.assertEqual(preview.invalid, 1)

    def test_unknown_blueprint_category_invalid(self):
        buf = _xlsx_bytes([_ba_row("BA-CAT", blueprint_category="Nonexistent")])
        preview = QuestionImportService.preview(buf, blueprint=self.blueprint)
        self.assertEqual(preview.invalid, 1)

    def test_in_file_duplicate_code_invalid(self):
        buf = _xlsx_bytes([_ba_row("DUP"), _tf_row("DUP")])
        preview = QuestionImportService.preview(buf, blueprint=self.blueprint)
        self.assertTrue(preview.has_invalid)

    def test_commit_is_transactional_on_invalid(self):
        before = Question.objects.count()
        buf = _xlsx_bytes([_ba_row("OK-1"), _tf_row("BAD", correct_answer="junk")])
        with self.assertRaises(ImportCommitError):
            QuestionImportService.commit(buf, actor=self.editor, blueprint=self.blueprint)
        self.assertEqual(Question.objects.count(), before)

    def test_commit_creates_questions_with_provenance(self):
        buf = _xlsx_bytes([_tf_row("TF-C"), _ba_row("BA-C")])
        report = QuestionImportService.commit(
            buf, actor=self.editor, blueprint=self.blueprint
        )
        self.assertEqual(report.created, 2)
        tf = Question.objects.get(question_code="TF-C")
        self.assertEqual(tf.question_type, QuestionType.TRUE_FALSE)
        self.assertEqual(tf.source_type, QuestionSourceType.IMPORTED)
        self.assertEqual(tf.source_name, "March 2025 Exam")
        self.assertEqual(tf.current_version.correct_answer_spec.get("type"), "true_false")
        self.assertEqual(tf.current_version.options.count(), 5)
        ba = Question.objects.get(question_code="BA-C")
        self.assertEqual(ba.editorial_state, EditorialState.PUBLISHED)
        self.assertEqual(ba.current_version.options.count(), 4)

    def test_idempotent_skip_existing_code(self):
        buf = _xlsx_bytes([_ba_row("BA-IDEM")])
        QuestionImportService.commit(buf, actor=self.editor, blueprint=self.blueprint)
        buf2 = _xlsx_bytes([_ba_row("BA-IDEM")])
        report = QuestionImportService.commit(
            buf2, actor=self.editor, blueprint=self.blueprint
        )
        self.assertEqual(report.created, 0)
        self.assertEqual(report.skipped_duplicate, 1)
        self.assertEqual(Question.objects.filter(question_code="BA-IDEM").count(), 1)


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"],
)
class StaffQuestionBankTests(TestCase):
    def setUp(self):
        self.editor = _staff_user("sqb-editor@example.com", RoleCode.EDITOR)
        self.author = _staff_user("sqb-author@example.com", RoleCode.AUTHOR)
        self.blueprint = ExamBlueprint.objects.get(code="BNMC_2018")

    def test_author_cannot_import(self):
        from apps.staff.services import QuestionStaffService

        buf = _xlsx_bytes([_ba_row("A-DENY")])
        with self.assertRaises(PermissionError):
            QuestionStaffService.import_commit(self.author, buf)

    def test_validation_problems_flags_missing_classification(self):
        from apps.staff.services import QuestionStaffService

        q, _v = _make_best_answer(editorial_state=EditorialState.DRAFT)
        problems = QuestionStaffService.validation_problems(q)
        self.assertTrue(any("blueprint" in p.lower() for p in problems))
        self.assertTrue(any("cognitive" in p.lower() for p in problems))

    def test_admin_source_view_returns_provenance(self):
        from apps.staff.services import QuestionStaffService

        q, _v = _make_best_answer(question_code="SRC-1")
        q.source_name = "March 2025 Exam"
        q.source_page = "5"
        q.source_type = QuestionSourceType.OFFICIAL_EXAM
        q.save(update_fields=["source_name", "source_page", "source_type"])
        view = QuestionStaffService.admin_source_view(self.editor, q)
        self.assertEqual(view["source_name"], "March 2025 Exam")
        self.assertEqual(view["source_page"], "5")
        self.assertEqual(view["question_code"], "SRC-1")

    def test_list_filters_by_type_and_needs_review(self):
        from apps.staff.services import QuestionStaffService

        cat = self.blueprint.categories.get(code="NURSING_PROCESS")
        _make_true_false(
            blueprint_category=cat, cognitive_level=CognitiveLevel.RECALL,
            editorial_state=EditorialState.DRAFT,
        )
        _make_best_answer(editorial_state=EditorialState.DRAFT)  # no classification
        tf_page = QuestionStaffService.list_questions(
            self.editor, question_type=QuestionType.TRUE_FALSE
        )
        for q in tf_page:
            self.assertEqual(q.question_type, QuestionType.TRUE_FALSE)


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"],
)
class StudentSecurityTests(TestCase):
    """Students never receive source/provenance or the answer key pre-submission."""

    def setUp(self):
        self.user, _ = AccountService.register(
            email="sec11@example.com", password=STRONG_PASSWORD, full_name="Sec"
        )

    def test_true_false_session_never_reveals_answer_key(self):
        from apps.assessment.services.presentation import PracticePresentationService

        _q, version = _make_true_false()
        item = _attempt_item(self.user, _q, version, None)
        statements = PracticePresentationService.true_false_statements(
            item, LocaleCode.EN, reveal=False
        )
        self.assertEqual(len(statements), 5)
        for s in statements:
            self.assertIsNone(s["correct"])
            self.assertFalse(s["show_correctness"])
