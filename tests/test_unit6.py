"""UNIT-6 Formal Examination Engine tests."""
from __future__ import annotations

import unittest
from datetime import timedelta

from django.db import connection
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.accounts.services import AccountService
from apps.assessment.models import (
    Attempt,
    ExamDefinition,
    ExamDefinitionItem,
)
from apps.assessment.services import ExamService
from apps.assessment.services.exceptions import ExamNotEntitled, ExamPoolEmpty
from apps.billing.models import Subscription
from apps.common.choices import (
    AttemptMode,
    AttemptState,
    EditorialState,
    SubscriptionState,
)
from apps.portal.services import NavigationService
from tests.test_unit4 import build_published_hierarchy
from tests.test_unit5 import STRONG_PASSWORD, _publish_question


def setUpModule():
    try:
        connection.ensure_connection()
    except Exception as exc:  # pragma: no cover
        raise unittest.SkipTest(f"PostgreSQL unavailable for UNIT-6: {exc}") from exc


def _publish_exam(
    *,
    code,
    title_key,
    mode=AttemptMode.TIMED_EXAM,
    time_limit_seconds=600,
    is_premium=False,
    track_code=None,
    questions=None,
    editorial_state=EditorialState.PUBLISHED,
):
    exam = ExamDefinition.objects.create(
        code=code,
        title_key=title_key,
        mode=mode,
        time_limit_seconds=time_limit_seconds,
        is_premium=is_premium,
        track_code=track_code,
        editorial_state=editorial_state,
        is_archived=False,
        rules={},
    )
    for i, q in enumerate(questions or []):
        ExamDefinitionItem.objects.create(
            exam_definition=exam, question=q, sort_order=i
        )
    return exam


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"],
)
class FormalExamEngineTests(TestCase):
    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)
        self.user, _ = AccountService.register(
            email="exam6@example.com",
            password=STRONG_PASSWORD,
            full_name="Exam Six",
        )
        self.other, _ = AccountService.register(
            email="other6@example.com",
            password=STRONG_PASSWORD,
            full_name="Other Six",
        )
        self.tree = build_published_hierarchy(title_prefix="Unit6")
        self.topic = self.tree["topic"]
        self.questions = [
            _publish_question(self.topic, stem=f"Exam stem {i}", key_correct="A")
            for i in range(4)
        ]
        self.exam = _publish_exam(
            code="unit6_timed",
            title_key="unit6_timed_exam",
            mode=AttemptMode.TIMED_EXAM,
            time_limit_seconds=3600,
            questions=self.questions[:3],
        )
        self.premium_exam = _publish_exam(
            code="unit6_premium_track",
            title_key="licensing_prep",
            mode=AttemptMode.MOCK,
            time_limit_seconds=1800,
            is_premium=True,
            track_code="licensing",
            questions=self.questions[:2],
        )
        self.draft_exam = _publish_exam(
            code="unit6_draft",
            title_key="hidden_draft",
            editorial_state=EditorialState.DRAFT,
            questions=self.questions[:1],
        )
        self._login(self.user.email)

    def _login(self, email):
        login_url = reverse("accounts:login")
        self.client.get(login_url)
        self.client.post(
            login_url,
            {
                "email": email,
                "password": STRONG_PASSWORD,
                "next": "",
                "csrfmiddlewaretoken": self.client.cookies["csrftoken"].value,
            },
        )

    def _csrf(self):
        return self.client.cookies["csrftoken"].value

    def _make_premium(self, user):
        Subscription.objects.update_or_create(
            user=user,
            defaults={
                "state": SubscriptionState.PREMIUM_ACTIVE,
                "premium_started_at": timezone.now(),
                "premium_expires_at": timezone.now() + timedelta(days=30),
            },
        )

    def _start(self, exam=None):
        exam = exam or self.exam
        return self.client.post(
            reverse("exams:start", kwargs={"exam_id": exam.id}),
            {"confirm": "true", "csrfmiddlewaretoken": self._csrf()},
        )

    def test_navigation_exams_available(self):
        items = NavigationService.items(active="exams")
        by_key = {i.key: i for i in items}
        self.assertTrue(by_key["exams"].available)
        self.assertEqual(by_key["exams"].href, reverse("exams:catalog"))

    def test_anonymous_redirected(self):
        c = Client()
        for name, kwargs in (
            ("exams:catalog", {}),
            ("exams:history", {}),
            ("exams:detail", {"exam_id": self.exam.id}),
        ):
            resp = c.get(reverse(name, kwargs=kwargs))
            self.assertEqual(resp.status_code, 302)
            self.assertIn("/accounts/login", resp.url)

    def test_catalog_hides_unpublished(self):
        resp = self.client.get(reverse("exams:catalog"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Unit6 Timed Exam")
        self.assertNotContains(resp, "Hidden Draft")
        self.assertNotContains(resp, str(self.draft_exam.id))

        ghost = self.client.get(
            reverse("exams:detail", kwargs={"exam_id": self.draft_exam.id})
        )
        self.assertEqual(ghost.status_code, 404)

    def test_detail_states_available_and_locked(self):
        avail = self.client.get(
            reverse("exams:detail", kwargs={"exam_id": self.exam.id})
        )
        self.assertEqual(avail.status_code, 200)
        self.assertContains(avail, "Available")
        self.assertContains(avail, "Start exam")

        locked = self.client.get(
            reverse("exams:detail", kwargs={"exam_id": self.premium_exam.id})
        )
        self.assertEqual(locked.status_code, 200)
        self.assertContains(locked, "Premium required")
        self.assertNotContains(locked, "Begin exam")

    def test_eligibility_blocks_premium_without_entitlement(self):
        with self.assertRaises(ExamNotEntitled):
            ExamService.start_or_resume(self.user, self.premium_exam.id)
        resp = self._start(self.premium_exam)
        self.assertEqual(resp.status_code, 302)
        self.assertIn(str(self.premium_exam.id), resp.url)
        self.assertEqual(Attempt.objects.filter(user=self.user).count(), 0)

    def test_premium_can_start_track_exam(self):
        self._make_premium(self.user)
        resp = self._start(self.premium_exam)
        self.assertEqual(resp.status_code, 302)
        attempt = Attempt.objects.get(user=self.user, exam_definition=self.premium_exam)
        self.assertEqual(attempt.mode, AttemptMode.MOCK)
        self.assertEqual(attempt.state, AttemptState.IN_PROGRESS)
        self.assertEqual(attempt.items.count(), 2)

    def test_start_freezes_question_versions_and_timing(self):
        resp = self._start()
        self.assertEqual(resp.status_code, 302)
        attempt = Attempt.objects.get(user=self.user, exam_definition=self.exam)
        self.assertEqual(attempt.items.count(), 3)
        self.assertIsNotNone(attempt.started_at)
        self.assertIsNotNone(attempt.expires_at)
        self.assertEqual(attempt.time_limit_seconds, 3600)
        for item in attempt.items.all():
            self.assertEqual(item.question_version_id, item.question.current_version_id)
            self.assertIsNone(item.is_correct)

        # Mutating live head does not change frozen attempt versions.
        q = attempt.items.first().question
        old_vid = attempt.items.first().question_version_id
        q.current_version = None
        q.save(update_fields=["current_version", "updated_at"])
        attempt.refresh_from_db()
        self.assertEqual(attempt.items.first().question_version_id, old_vid)

    def test_refresh_resumes_same_attempt(self):
        self._start()
        first = Attempt.objects.get(user=self.user, exam_definition=self.exam)
        self._start()
        self.assertEqual(
            Attempt.objects.filter(user=self.user, exam_definition=self.exam).count(),
            1,
        )
        second = Attempt.objects.get(user=self.user, exam_definition=self.exam)
        self.assertEqual(first.id, second.id)

    def test_session_does_not_leak_answer_key(self):
        self._start()
        attempt = Attempt.objects.get(user=self.user)
        session = self.client.get(
            reverse(
                "exams:session",
                kwargs={"attempt_id": attempt.id, "position": 1},
            )
        )
        self.assertEqual(session.status_code, 200)
        content = session.content.decode("utf-8")
        self.assertIn("Select an answer", content)
        self.assertIn("Time remaining", content)
        self.assertNotIn("Because evidence supports it.", content)
        self.assertNotIn("correct_answer_spec", content)
        self.assertNotIn("is_correct", content)
        self.assertNotIn('data-correct="true"', content)
        self.assertNotContains(session, "Explanation")
        self.assertNotIn("(correct)", content)

    def test_answer_persist_navigation_and_invalid(self):
        self._start()
        attempt = Attempt.objects.get(user=self.user)
        item1 = attempt.items.get(position=1)
        key = item1.question_version.options.filter(is_correct=True).first().key
        resp = self.client.post(
            reverse(
                "exams:answer",
                kwargs={"attempt_id": attempt.id, "position": 1},
            ),
            {
                "option_key": key,
                "nav": "next",
                "csrfmiddlewaretoken": self._csrf(),
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/session/2/", resp.url)
        item1.refresh_from_db()
        self.assertEqual(item1.selected_answer, {"key": key})
        self.assertIsNone(item1.is_correct)

        bad = self.client.post(
            reverse(
                "exams:answer",
                kwargs={"attempt_id": attempt.id, "position": 2},
            ),
            {
                "option_key": "ZZ",
                "nav": "stay",
                "csrfmiddlewaretoken": self._csrf(),
            },
        )
        self.assertEqual(bad.status_code, 302)
        self.assertIsNone(attempt.items.get(position=2).selected_answer)

        ghost = self.client.get(
            reverse(
                "exams:session",
                kwargs={"attempt_id": attempt.id, "position": 99},
            )
        )
        self.assertEqual(ghost.status_code, 404)

    def test_cross_user_attempt_denied(self):
        self._start()
        attempt = Attempt.objects.get(user=self.user)
        self.client.logout()
        self._login(self.other.email)
        for name, kwargs in (
            ("exams:session", {"attempt_id": attempt.id, "position": 1}),
            ("exams:result", {"attempt_id": attempt.id}),
            ("exams:review", {"attempt_id": attempt.id}),
            ("exams:submit", {"attempt_id": attempt.id}),
        ):
            resp = self.client.get(reverse(name, kwargs=kwargs))
            self.assertEqual(resp.status_code, 404, msg=name)

        resp = self.client.post(
            reverse(
                "exams:answer",
                kwargs={"attempt_id": attempt.id, "position": 1},
            ),
            {"option_key": "A", "csrfmiddlewaretoken": self._csrf()},
        )
        self.assertEqual(resp.status_code, 404)

    def test_submit_scores_and_duplicate_safe(self):
        self._start()
        attempt = Attempt.objects.get(user=self.user)
        items = list(attempt.items.order_by("position"))
        ExamService.persist_answer(
            self.user,
            attempt.id,
            position=1,
            option_key=items[0]
            .question_version.options.filter(is_correct=True)
            .first()
            .key,
        )
        ExamService.persist_answer(
            self.user,
            attempt.id,
            position=2,
            option_key=items[1]
            .question_version.options.filter(is_correct=False)
            .first()
            .key,
        )
        confirm = self.client.get(
            reverse("exams:submit", kwargs={"attempt_id": attempt.id})
        )
        self.assertEqual(confirm.status_code, 200)
        self.assertContains(confirm, "Confirm submit")

        submit = self.client.post(
            reverse("exams:submit", kwargs={"attempt_id": attempt.id}),
            {"confirm": "true", "csrfmiddlewaretoken": self._csrf()},
        )
        self.assertEqual(submit.status_code, 302)
        attempt.refresh_from_db()
        self.assertEqual(attempt.state, AttemptState.COMPLETED)
        self.assertEqual(attempt.score_summary["correct"], 1)
        self.assertEqual(attempt.score_summary["incorrect"], 1)
        self.assertEqual(attempt.score_summary["unanswered"], 1)

        again = ExamService.submit(self.user, attempt.id)
        self.assertTrue(again.already_submitted)
        self.assertEqual(again.score_summary["correct"], 1)

        sess = self.client.get(
            reverse(
                "exams:session",
                kwargs={"attempt_id": attempt.id, "position": 1},
            )
        )
        self.assertEqual(sess.status_code, 302)
        self.assertIn("/result/", sess.url)

    def test_auto_submit_on_timeout_and_reject_late_answers(self):
        self._start()
        attempt = Attempt.objects.get(user=self.user)
        Attempt.objects.filter(pk=attempt.pk).update(
            expires_at=timezone.now() - timedelta(seconds=5)
        )
        attempt.refresh_from_db()

        late = ExamService.persist_answer(
            self.user, attempt.id, position=1, option_key="A"
        )
        self.assertFalse(late.ok)
        self.assertEqual(late.code, "already_submitted")

        attempt.refresh_from_db()
        self.assertEqual(attempt.state, AttemptState.COMPLETED)
        self.assertIsNotNone(attempt.score_summary)
        self.assertIsNotNone(attempt.completed_at)

        # Session redirects to result after auto-submit.
        self._start()  # new attempt after completed
        attempt2 = (
            Attempt.objects.filter(user=self.user, exam_definition=self.exam)
            .order_by("-created_at")
            .first()
        )
        Attempt.objects.filter(pk=attempt2.pk).update(
            expires_at=timezone.now() - timedelta(seconds=1)
        )
        sess = self.client.get(
            reverse(
                "exams:session",
                kwargs={"attempt_id": attempt2.id, "position": 1},
            )
        )
        self.assertEqual(sess.status_code, 302)
        self.assertIn("/result/", sess.url)
        attempt2.refresh_from_db()
        self.assertEqual(attempt2.state, AttemptState.COMPLETED)

    def test_client_cannot_extend_timer(self):
        self._start()
        attempt = Attempt.objects.get(user=self.user)
        original = attempt.expires_at
        # Forged expires_at via POST fields must be ignored (no such form field).
        self.client.post(
            reverse(
                "exams:answer",
                kwargs={"attempt_id": attempt.id, "position": 1},
            ),
            {
                "option_key": "A",
                "expires_at": (timezone.now() + timedelta(days=10)).isoformat(),
                "remaining_seconds": "99999",
                "csrfmiddlewaretoken": self._csrf(),
            },
        )
        attempt.refresh_from_db()
        self.assertEqual(attempt.expires_at, original)

    def test_review_only_after_completion(self):
        self._start()
        attempt = Attempt.objects.get(user=self.user)
        early = self.client.get(
            reverse("exams:review", kwargs={"attempt_id": attempt.id})
        )
        self.assertEqual(early.status_code, 302)

        ExamService.submit(self.user, attempt.id)
        review = self.client.get(
            reverse("exams:review", kwargs={"attempt_id": attempt.id})
        )
        self.assertEqual(review.status_code, 200)
        self.assertContains(review, "Because evidence supports it.")
        self.assertContains(review, "Correct answer")

    def test_history_ownership_and_pagination(self):
        for _ in range(2):
            a = ExamService.start_or_resume(self.user, self.exam.id)
            ExamService.submit(self.user, a.id)

        other_a = ExamService.start_or_resume(self.other, self.exam.id)
        ExamService.submit(self.other, other_a.id)

        hist = self.client.get(reverse("exams:history"))
        self.assertEqual(hist.status_code, 200)
        self.assertContains(hist, "Unit6 Timed Exam")
        body = hist.content.decode("utf-8")
        self.assertEqual(body.count(str(other_a.id)), 0)

    def test_empty_pool_unavailable(self):
        empty = _publish_exam(
            code="unit6_empty",
            title_key="empty_exam",
            questions=[],
        )
        elig = ExamService.eligibility(self.user, empty)
        self.assertEqual(elig.state, "unavailable")
        with self.assertRaises(ExamPoolEmpty):
            ExamService.start_or_resume(self.user, empty.id)

    def test_practice_attempt_not_accessible_via_exam_routes(self):
        from apps.assessment.services import PracticeService

        practice = PracticeService.start_practice(
            self.user,
            scope_type="topic",
            scope_id=self.topic.id,
            count=1,
        )
        resp = self.client.get(
            reverse(
                "exams:session",
                kwargs={"attempt_id": practice.id, "position": 1},
            )
        )
        self.assertEqual(resp.status_code, 404)

    def test_score_manipulation_rejected(self):
        self._start()
        attempt = Attempt.objects.get(user=self.user)
        ExamService.submit(self.user, attempt.id)
        # Client cannot rewrite score via result GET/POST.
        forged = self.client.post(
            reverse("exams:result", kwargs={"attempt_id": attempt.id}),
            {
                "score": "100",
                "percent_correct": "100",
                "csrfmiddlewaretoken": self._csrf(),
            },
        )
        # Result is GET-only; POST should not mutate.
        self.assertIn(forged.status_code, {405, 302, 200})
        attempt.refresh_from_db()
        self.assertNotEqual(attempt.score_summary.get("percent_correct"), 100.0)
        # Ensure summary still reflects server scoring of unanswered items.
        self.assertEqual(attempt.score_summary["correct"], 0)

    def test_untimed_exam_has_no_auto_expiry(self):
        untimed = _publish_exam(
            code="unit6_untimed",
            title_key="untimed_chapter",
            mode=AttemptMode.CHAPTER_EXAM,
            time_limit_seconds=None,
            questions=self.questions[:2],
        )
        attempt = ExamService.start_or_resume(self.user, untimed.id)
        self.assertIsNone(attempt.expires_at)
        self.assertIsNone(attempt.time_limit_seconds)
        snap = ExamService.timer_for(attempt)
        self.assertFalse(snap.is_timed)
        self.assertFalse(snap.is_expired)
        # Still active after "fake" long wait without expires_at.
        attempt2 = ExamService.enforce_timeout(self.user, attempt)
        self.assertEqual(attempt2.state, AttemptState.IN_PROGRESS)
