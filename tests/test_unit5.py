"""UNIT-5 Practice Engine & Practice Experience tests."""
from __future__ import annotations

import unittest
import uuid

from django.db import connection
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from apps.accounts.services import AccountService
from apps.assessment.models import (
    Attempt,
    AttemptItem,
    Question,
    QuestionOption,
    QuestionOptionTranslation,
    QuestionTopic,
    QuestionVersion,
    QuestionVersionTranslation,
)
from apps.assessment.services import PracticeService
from apps.assessment.services.exceptions import PracticeCapExceeded, PracticePoolEmpty
from apps.assessment.services.pool import PracticePoolService
from apps.assessment.services.practice import FREE_PRACTICE_CAP_SETTING_KEY
from apps.assessment.services.scoring import build_score_summary, score_item
from apps.billing.models import Subscription
from apps.common.choices import (
    AttemptMode,
    AttemptState,
    DifficultyLevel,
    EditorialState,
    LocaleCode,
    QuestionType,
    SubscriptionState,
)
from apps.platform.models import PlatformSetting
from apps.portal.services import NavigationService
from tests.test_unit4 import build_published_hierarchy


STRONG_PASSWORD = "Str0ng-Pass!Unit5"


def setUpModule():
    try:
        connection.ensure_connection()
    except Exception as exc:  # pragma: no cover
        raise unittest.SkipTest(f"PostgreSQL unavailable for UNIT-5: {exc}") from exc


def _publish_question(
    topic,
    *,
    key_correct="A",
    stem="What is the correct nursing action?",
    explanation="Because evidence supports it.",
    difficulty=DifficultyLevel.EASY,
    qtype=QuestionType.MCQ,
    editorial_state=EditorialState.PUBLISHED,
    locale=LocaleCode.EN,
    option_labels=None,
):
    """Test-only factory — never used for production seed content."""
    question = Question.objects.create(
        question_type=qtype,
        difficulty=difficulty,
        editorial_state=editorial_state,
        is_archived=False,
        primary_locale=locale,
    )
    version = QuestionVersion.objects.create(
        question=question,
        version_no=1,
        correct_answer_spec={"key": key_correct},
    )
    question.current_version = version
    question.save(update_fields=["current_version", "updated_at"])
    QuestionVersionTranslation.objects.create(
        version=version,
        locale=locale,
        stem=stem,
        explanation=explanation,
    )
    labels = option_labels or {"A": "Correct option", "B": "Wrong option", "C": "Also wrong"}
    for i, (key, label) in enumerate(labels.items()):
        opt = QuestionOption.objects.create(
            question_version=version,
            key=key,
            is_correct=(key == key_correct),
            sort_order=i,
        )
        QuestionOptionTranslation.objects.create(option=opt, locale=locale, label=label)
    QuestionTopic.objects.create(question=question, topic=topic)
    return question


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"],
)
class PracticeEngineTests(TestCase):
    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)
        self.user, _ = AccountService.register(
            email="practice5@example.com",
            password=STRONG_PASSWORD,
            full_name="Practice Five",
        )
        self.other, _ = AccountService.register(
            email="other5@example.com",
            password=STRONG_PASSWORD,
            full_name="Other Five",
        )
        self.tree = build_published_hierarchy(title_prefix="Unit5")
        self.topic = self.tree["topic"]
        self.questions = [
            _publish_question(self.topic, stem=f"Stem {i}", key_correct="A")
            for i in range(5)
        ]
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

    def _start(self, *, count=3, scope_type="topic", scope_id=None, difficulty=""):
        scope_id = scope_id or self.topic.id
        resp = self.client.post(
            reverse("assessment:setup"),
            {
                "scope_type": scope_type,
                "scope_id": str(scope_id) if scope_type != "random" else "",
                "difficulty": difficulty,
                "count": str(count),
                "csrfmiddlewaretoken": self._csrf(),
            },
        )
        return resp

    def test_navigation_practice_available(self):
        items = NavigationService.items(active="practice")
        by_key = {i.key: i for i in items}
        self.assertTrue(by_key["practice"].available)
        self.assertEqual(by_key["practice"].href, reverse("assessment:entry"))

    def test_anonymous_cannot_access_practice(self):
        c = Client()
        for name, kwargs in (
            ("assessment:entry", {}),
            ("assessment:setup", {}),
            ("assessment:history", {}),
        ):
            resp = c.get(reverse(name, kwargs=kwargs))
            self.assertEqual(resp.status_code, 302)
            self.assertIn("/accounts/login", resp.url)

    def test_setup_validation_errors(self):
        resp = self.client.post(
            reverse("assessment:setup"),
            {
                "scope_type": "topic",
                "scope_id": "",
                "difficulty": "",
                "count": "10",
                "csrfmiddlewaretoken": self._csrf(),
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Practice setup")

        resp = self.client.post(
            reverse("assessment:setup"),
            {
                "scope_type": "topic",
                "scope_id": str(self.topic.id),
                "difficulty": "not-a-level",
                "count": "10",
                "csrfmiddlewaretoken": self._csrf(),
            },
        )
        self.assertEqual(resp.status_code, 200)

        resp = self.client.post(
            reverse("assessment:setup"),
            {
                "scope_type": "topic",
                "scope_id": str(self.topic.id),
                "difficulty": "",
                "count": "999",
                "csrfmiddlewaretoken": self._csrf(),
            },
        )
        self.assertEqual(resp.status_code, 200)

    def test_unpublished_scope_denied(self):
        self.topic.editorial_state = EditorialState.DRAFT
        self.topic.save(update_fields=["editorial_state", "updated_at"])
        resp = self._start()
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Attempt.objects.filter(user=self.user).count(), 0)

    def test_start_topic_practice_server_selects_questions(self):
        resp = self._start(count=3)
        self.assertEqual(resp.status_code, 302)
        attempt = Attempt.objects.get(user=self.user)
        self.assertEqual(attempt.mode, AttemptMode.PRACTICE)
        self.assertEqual(attempt.state, AttemptState.IN_PROGRESS)
        self.assertEqual(attempt.scope_type, "topic")
        self.assertEqual(attempt.scope_id, self.topic.id)
        self.assertEqual(attempt.items.count(), 3)
        for item in attempt.items.all():
            self.assertIsNotNone(item.question_version_id)
            self.assertIsNone(item.is_correct)
            self.assertEqual(item.question.current_version_id, item.question_version_id)

    def test_client_question_ids_ignored(self):
        resp = self.client.post(
            reverse("assessment:setup"),
            {
                "scope_type": "topic",
                "scope_id": str(self.topic.id),
                "difficulty": "",
                "count": "2",
                "question_ids": [str(self.questions[0].id), str(uuid.uuid4())],
                "csrfmiddlewaretoken": self._csrf(),
            },
        )
        self.assertEqual(resp.status_code, 302)
        attempt = Attempt.objects.get(user=self.user)
        self.assertEqual(attempt.items.count(), 2)

    def test_empty_pool_denied(self):
        Question.objects.all().update(editorial_state=EditorialState.DRAFT)
        with self.assertRaises(PracticePoolEmpty):
            PracticeService.start_practice(
                self.user,
                scope_type="topic",
                scope_id=self.topic.id,
                count=2,
            )

    def test_session_does_not_leak_answer_key(self):
        resp = self._start(count=2)
        attempt = Attempt.objects.get(user=self.user)
        session = self.client.get(
            reverse(
                "assessment:session",
                kwargs={"attempt_id": attempt.id, "position": 1},
            )
        )
        self.assertEqual(session.status_code, 200)
        content = session.content.decode("utf-8")
        self.assertIn("Select an answer", content)
        # Option labels may be shown; correctness markers / explanations must not.
        self.assertNotIn("Because evidence supports it.", content)
        self.assertNotIn("is_correct", content)
        self.assertNotIn("correct_answer_spec", content)
        self.assertNotIn('data-correct="true"', content)
        self.assertNotIn("outcome-correct", content)
        self.assertNotContains(session, "Explanation")
        self.assertNotIn("is-correct", content)
        self.assertNotIn("(correct)", content)

    def test_answer_persist_and_navigation(self):
        self._start(count=3)
        attempt = Attempt.objects.get(user=self.user)
        item1 = attempt.items.get(position=1)
        valid_key = item1.question_version.options.filter(is_correct=True).first().key

        resp = self.client.post(
            reverse(
                "assessment:answer",
                kwargs={"attempt_id": attempt.id, "position": 1},
            ),
            {
                "option_key": valid_key,
                "nav": "next",
                "csrfmiddlewaretoken": self._csrf(),
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/session/2/", resp.url)
        item1.refresh_from_db()
        self.assertEqual(item1.selected_answer, {"key": valid_key})
        self.assertIsNone(item1.is_correct)  # no scoring during active

        # Invalid option rejected
        bad = self.client.post(
            reverse(
                "assessment:answer",
                kwargs={"attempt_id": attempt.id, "position": 2},
            ),
            {
                "option_key": "ZZ",
                "nav": "stay",
                "csrfmiddlewaretoken": self._csrf(),
            },
        )
        self.assertEqual(bad.status_code, 302)
        item2 = attempt.items.get(position=2)
        self.assertIsNone(item2.selected_answer)

        # Unauthorized position
        ghost = self.client.get(
            reverse(
                "assessment:session",
                kwargs={"attempt_id": attempt.id, "position": 99},
            )
        )
        self.assertEqual(ghost.status_code, 404)

    def test_cross_user_attempt_denied(self):
        self._start(count=2)
        attempt = Attempt.objects.get(user=self.user)
        self.client.logout()
        self._login(self.other.email)
        for name, kwargs in (
            (
                "assessment:session",
                {"attempt_id": attempt.id, "position": 1},
            ),
            ("assessment:result", {"attempt_id": attempt.id}),
            ("assessment:review", {"attempt_id": attempt.id}),
            ("assessment:submit", {"attempt_id": attempt.id}),
        ):
            resp = self.client.get(reverse(name, kwargs=kwargs))
            self.assertEqual(resp.status_code, 404, msg=name)

        resp = self.client.post(
            reverse(
                "assessment:answer",
                kwargs={"attempt_id": attempt.id, "position": 1},
            ),
            {
                "option_key": "A",
                "csrfmiddlewaretoken": self._csrf(),
            },
        )
        self.assertEqual(resp.status_code, 404)

    def test_submit_scores_server_side_and_duplicate_safe(self):
        self._start(count=3)
        attempt = Attempt.objects.get(user=self.user)
        items = list(attempt.items.order_by("position"))
        # Answer 1 correct, 2 incorrect, 3 blank
        correct1 = items[0].question_version.options.filter(is_correct=True).first().key
        wrong2 = items[1].question_version.options.filter(is_correct=False).first().key
        PracticeService.persist_answer(
            self.user, attempt.id, position=1, option_key=correct1
        )
        PracticeService.persist_answer(
            self.user, attempt.id, position=2, option_key=wrong2
        )

        confirm = self.client.get(reverse("assessment:submit", kwargs={"attempt_id": attempt.id}))
        self.assertEqual(confirm.status_code, 200)
        self.assertContains(confirm, "Confirm submit")

        submit = self.client.post(
            reverse("assessment:submit", kwargs={"attempt_id": attempt.id}),
            {"confirm": "true", "csrfmiddlewaretoken": self._csrf()},
        )
        self.assertEqual(submit.status_code, 302)
        attempt.refresh_from_db()
        self.assertEqual(attempt.state, AttemptState.COMPLETED)
        summary = attempt.score_summary
        self.assertEqual(summary["total"], 3)
        self.assertEqual(summary["correct"], 1)
        self.assertEqual(summary["incorrect"], 1)
        self.assertEqual(summary["unanswered"], 1)
        self.assertEqual(summary["score"], 1)
        self.assertEqual(summary["percent_correct"], 33.33)

        # Active session no longer available
        sess = self.client.get(
            reverse(
                "assessment:session",
                kwargs={"attempt_id": attempt.id, "position": 1},
            )
        )
        self.assertEqual(sess.status_code, 302)
        self.assertIn("/result/", sess.url)

        # Duplicate submit idempotent
        again = PracticeService.submit(self.user, attempt.id)
        self.assertTrue(again.already_submitted)
        self.assertEqual(again.score_summary["correct"], 1)

        result = self.client.get(
            reverse("assessment:result", kwargs={"attempt_id": attempt.id})
        )
        self.assertEqual(result.status_code, 200)
        self.assertContains(result, "Score summary")
        self.assertContains(result, "33.33")

    def test_review_reveals_answers_after_completion_only(self):
        self._start(count=1)
        attempt = Attempt.objects.get(user=self.user)
        item = attempt.items.get()
        key = item.question_version.options.filter(is_correct=True).first().key
        PracticeService.persist_answer(
            self.user, attempt.id, position=1, option_key=key
        )

        early = self.client.get(
            reverse("assessment:review", kwargs={"attempt_id": attempt.id})
        )
        self.assertEqual(early.status_code, 302)

        PracticeService.submit(self.user, attempt.id)
        review = self.client.get(
            reverse("assessment:review", kwargs={"attempt_id": attempt.id})
        )
        self.assertEqual(review.status_code, 200)
        self.assertContains(review, "Because evidence supports it.")
        self.assertContains(review, "Correct answer")
        self.assertContains(review, "Correct")

    def test_history_ownership_and_pagination_foundation(self):
        for _ in range(2):
            attempt = PracticeService.start_practice(
                self.user,
                scope_type="topic",
                scope_id=self.topic.id,
                count=1,
            )
            PracticeService.submit(self.user, attempt.id)

        # Other user's attempt must not appear
        other_attempt = PracticeService.start_practice(
            self.other,
            scope_type="topic",
            scope_id=self.topic.id,
            count=1,
        )
        PracticeService.submit(self.other, other_attempt.id)

        hist = self.client.get(reverse("assessment:history"))
        self.assertEqual(hist.status_code, 200)
        self.assertContains(hist, "Practice history")
        body = hist.content.decode("utf-8")
        self.assertIn(str(Attempt.objects.filter(user=self.user).first().id), body)
        self.assertNotIn(str(other_attempt.id), body)

    def test_free_cap_enforced_premium_uncapped(self):
        PlatformSetting.objects.update_or_create(
            pk=FREE_PRACTICE_CAP_SETTING_KEY,
            defaults={"value": {"limit": 2}},
        )
        PracticeService.start_practice(
            self.user, scope_type="topic", scope_id=self.topic.id, count=2
        )
        with self.assertRaises(PracticeCapExceeded):
            PracticeService.start_practice(
                self.user, scope_type="topic", scope_id=self.topic.id, count=1
            )

        Subscription.objects.update_or_create(
            user=self.user,
            defaults={"state": SubscriptionState.PREMIUM_ACTIVE},
        )
        premium_attempt = PracticeService.start_practice(
            self.user, scope_type="topic", scope_id=self.topic.id, count=2
        )
        self.assertEqual(premium_attempt.items.count(), 2)

    def test_chapter_and_random_scope(self):
        chapter = self.tree["chapter"]
        resp = self._start(count=2, scope_type="chapter", scope_id=chapter.id)
        self.assertEqual(resp.status_code, 302)
        attempt = Attempt.objects.filter(user=self.user, scope_type="chapter").latest(
            "created_at"
        )
        self.assertEqual(attempt.items.count(), 2)

        resp = self._start(count=2, scope_type="random")
        self.assertEqual(resp.status_code, 302)
        random_attempt = Attempt.objects.filter(
            user=self.user, scope_type="random"
        ).latest("created_at")
        self.assertEqual(random_attempt.items.count(), 2)

    def test_learning_hierarchy_practice_link(self):
        resp = self.client.get(
            reverse("learning:topic", kwargs={"topic_id": self.topic.id})
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Practice this topic")
        self.assertContains(resp, f"scope_id={self.topic.id}")

    def test_scoring_uses_frozen_version_not_live_head(self):
        question = self.questions[0]
        old_version = question.current_version
        # Create new version that changes correctness; freeze old on attempt.
        new_version = QuestionVersion.objects.create(
            question=question,
            version_no=2,
            correct_answer_spec={"key": "B"},
        )
        QuestionVersionTranslation.objects.create(
            version=new_version,
            locale=LocaleCode.EN,
            stem="Changed stem",
            explanation="New explanation",
        )
        for i, key in enumerate(["A", "B"]):
            QuestionOption.objects.create(
                question_version=new_version,
                key=key,
                is_correct=(key == "B"),
                sort_order=i,
            )
        question.current_version = new_version
        question.save(update_fields=["current_version", "updated_at"])

        attempt = Attempt.objects.create(
            user=self.user,
            mode=AttemptMode.PRACTICE,
            state=AttemptState.IN_PROGRESS,
            scope_type="topic",
            scope_id=self.topic.id,
        )
        item = AttemptItem.objects.create(
            attempt=attempt,
            position=1,
            question=question,
            question_version=old_version,
            selected_answer={"key": "A"},
        )
        # Prefetch options for scoring helper
        item = (
            AttemptItem.objects.select_related("question_version")
            .prefetch_related("question_version__options")
            .get(pk=item.pk)
        )
        self.assertTrue(score_item(item))
        PracticeService.submit(self.user, attempt.id)
        item.refresh_from_db()
        self.assertTrue(item.is_correct)

    def test_entry_resume_and_setup_get(self):
        entry = self.client.get(reverse("assessment:entry"))
        self.assertEqual(entry.status_code, 200)
        self.assertContains(entry, "Start practice setup")

        setup = self.client.get(
            reverse("assessment:setup")
            + f"?scope_type=topic&scope_id={self.topic.id}"
        )
        self.assertEqual(setup.status_code, 200)
        self.assertContains(setup, "Practice setup")

        self._start(count=1)
        entry2 = self.client.get(reverse("assessment:entry"))
        self.assertContains(entry2, "Resume")


class PracticeScoringUnitTests(TestCase):
    def setUp(self):
        self.tree = build_published_hierarchy(title_prefix="Score5")
        self.q = _publish_question(self.tree["topic"])

    def test_build_score_summary_counts(self):
        user, _ = AccountService.register(
            email="score5@example.com", password=STRONG_PASSWORD
        )
        attempt = Attempt.objects.create(
            user=user,
            mode=AttemptMode.PRACTICE,
            state=AttemptState.IN_PROGRESS,
        )
        v = self.q.current_version
        AttemptItem.objects.create(
            attempt=attempt,
            position=1,
            question=self.q,
            question_version=v,
            is_correct=True,
        )
        AttemptItem.objects.create(
            attempt=attempt,
            position=2,
            question=self.q,
            question_version=v,
            is_correct=False,
        )
        AttemptItem.objects.create(
            attempt=attempt,
            position=3,
            question=self.q,
            question_version=v,
            is_correct=None,
        )
        items = list(attempt.items.order_by("position"))
        summary = build_score_summary(items)
        self.assertEqual(summary["correct"], 1)
        self.assertEqual(summary["incorrect"], 1)
        self.assertEqual(summary["unanswered"], 1)
        self.assertEqual(summary["score"], 1)

    def test_pool_filters_difficulty(self):
        _publish_question(
            self.tree["topic"],
            difficulty=DifficultyLevel.HARD,
            stem="Hard stem",
        )
        user, _ = AccountService.register(
            email="pool5@example.com", password=STRONG_PASSWORD
        )
        scope = PracticePoolService.validate_setup(
            scope_type="topic",
            scope_id=self.tree["topic"].id,
            difficulty="hard",
            count=5,
            user=user,
        )
        qs = PracticePoolService.published_pool_qs(scope)
        self.assertTrue(qs.exists())
        self.assertTrue(all(q.difficulty == DifficultyLevel.HARD for q in qs))
