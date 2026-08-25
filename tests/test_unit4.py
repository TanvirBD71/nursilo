"""UNIT-4 Learning Domain & Learning Experience tests."""
from __future__ import annotations

import unittest
import uuid

from django.db import connection
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from apps.accounts.services import AccountService
from apps.billing.models import Subscription
from apps.common.choices import EditorialState, LocaleCode, SubscriptionState
from apps.learning.models import (
    Chapter,
    ChapterTranslation,
    ContinueLearningCursor,
    Course,
    CourseTranslation,
    LearnerProgress,
    LearningMaterial,
    LearningMaterialTranslation,
    Lesson,
    LessonLearningMaterial,
    LessonTranslation,
    Subject,
    SubjectTranslation,
    Topic,
    TopicTranslation,
    Unit,
    UnitTranslation,
)
from apps.learning.services import (
    LearningAccessService,
    LearningProgressService,
)
from apps.learning.services.progress import CompletionResult
from apps.portal.services import DashboardPresentationService, NavigationService


STRONG_PASSWORD = "Str0ng-Pass!Unit4"


def setUpModule():
    try:
        connection.ensure_connection()
    except Exception as exc:  # pragma: no cover
        raise unittest.SkipTest(f"PostgreSQL unavailable for UNIT-4: {exc}") from exc


def _publish(node, **kwargs):
    node.editorial_state = EditorialState.PUBLISHED
    node.is_archived = False
    for key, value in kwargs.items():
        setattr(node, key, value)
    node.save()
    return node


def build_published_hierarchy(*, locale=LocaleCode.EN, title_prefix="Unit4"):
    """Test-only factory — never used for production seed content."""
    course = _publish(Course.objects.create(sort_order=1))
    CourseTranslation.objects.create(
        course=course, locale=locale, title=f"{title_prefix} Course", summary="Course summary"
    )
    subject = _publish(Subject.objects.create(course=course, sort_order=1))
    SubjectTranslation.objects.create(
        subject=subject, locale=locale, title=f"{title_prefix} Subject", summary="Subject summary"
    )
    unit = _publish(Unit.objects.create(subject=subject, sort_order=1))
    UnitTranslation.objects.create(
        unit=unit, locale=locale, title=f"{title_prefix} Unit", summary="Unit summary"
    )
    chapter = _publish(Chapter.objects.create(unit=unit, sort_order=1))
    ChapterTranslation.objects.create(
        chapter=chapter, locale=locale, title=f"{title_prefix} Chapter", summary="Chapter summary"
    )
    topic = _publish(Topic.objects.create(chapter=chapter, sort_order=1))
    TopicTranslation.objects.create(
        topic=topic, locale=locale, title=f"{title_prefix} Topic", summary="Topic summary"
    )
    lesson_a = _publish(Lesson.objects.create(topic=topic, sort_order=1))
    LessonTranslation.objects.create(
        lesson=lesson_a,
        locale=locale,
        title=f"{title_prefix} Lesson A",
        body="Lesson A body text for reading.",
    )
    lesson_b = _publish(Lesson.objects.create(topic=topic, sort_order=2))
    LessonTranslation.objects.create(
        lesson=lesson_b,
        locale=locale,
        title=f"{title_prefix} Lesson B",
        body="Lesson B body text for reading.",
    )
    free_material = _publish(LearningMaterial.objects.create(sort_order=1, is_premium=False))
    LearningMaterialTranslation.objects.create(
        learning_material=free_material,
        locale=locale,
        title=f"{title_prefix} Free Notes",
        body="Free material body.",
    )
    premium_material = _publish(LearningMaterial.objects.create(sort_order=2, is_premium=True))
    LearningMaterialTranslation.objects.create(
        learning_material=premium_material,
        locale=locale,
        title=f"{title_prefix} Premium Notes",
        body="Premium secret body must not leak to free users.",
    )
    LessonLearningMaterial.objects.create(
        lesson=lesson_a, learning_material=free_material, sort_order=0
    )
    LessonLearningMaterial.objects.create(
        lesson=lesson_a, learning_material=premium_material, sort_order=1
    )
    return {
        "course": course,
        "subject": subject,
        "unit": unit,
        "chapter": chapter,
        "topic": topic,
        "lesson_a": lesson_a,
        "lesson_b": lesson_b,
        "free_material": free_material,
        "premium_material": premium_material,
    }


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"],
)
class LearningAccessAndCatalogTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user, _ = AccountService.register(
            email="learn4@example.com",
            password=STRONG_PASSWORD,
            full_name="Learner Four",
        )
        self.tree = build_published_hierarchy()
        self._login()

    def _login(self):
        self.client.post(
            reverse("accounts:login"),
            {"email": "learn4@example.com", "password": STRONG_PASSWORD, "next": ""},
        )

    def test_anonymous_cannot_access_learning(self):
        anon = Client()
        urls = [
            reverse("learning:catalog"),
            reverse("learning:course", kwargs={"course_id": self.tree["course"].id}),
            reverse("learning:lesson", kwargs={"lesson_id": self.tree["lesson_a"].id}),
        ]
        for url in urls:
            resp = anon.get(url)
            self.assertEqual(resp.status_code, 302, url)
            self.assertIn("/accounts/login/", resp["Location"])

    def test_catalog_lists_published_courses_only(self):
        draft = Course.objects.create(sort_order=99, editorial_state=EditorialState.DRAFT)
        CourseTranslation.objects.create(
            course=draft, locale=LocaleCode.EN, title="Hidden Draft Course"
        )
        resp = self.client.get(reverse("learning:catalog"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Unit4 Course")
        self.assertNotContains(resp, "Hidden Draft Course")
        self.assertContains(resp, 'id="main-content"')
        self.assertContains(resp, "Skip to main content")

    def test_empty_catalog_is_honest(self):
        Course.objects.all().update(editorial_state=EditorialState.ARCHIVED, is_archived=True)
        resp = self.client.get(reverse("learning:catalog"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "No courses available")

    def test_hierarchy_navigation_and_breadcrumbs(self):
        course = self.tree["course"]
        subject = self.tree["subject"]
        unit = self.tree["unit"]
        chapter = self.tree["chapter"]
        topic = self.tree["topic"]
        lesson = self.tree["lesson_a"]

        path = [
            ("learning:course", {"course_id": course.id}, "Unit4 Course", "Unit4 Subject"),
            ("learning:subject", {"subject_id": subject.id}, "Unit4 Subject", "Unit4 Unit"),
            ("learning:unit", {"unit_id": unit.id}, "Unit4 Unit", "Unit4 Chapter"),
            ("learning:chapter", {"chapter_id": chapter.id}, "Unit4 Chapter", "Unit4 Topic"),
            ("learning:topic", {"topic_id": topic.id}, "Unit4 Topic", "Unit4 Lesson A"),
            ("learning:lesson", {"lesson_id": lesson.id}, "Unit4 Lesson A", "Lesson A body"),
        ]
        for name, kwargs, heading, child_or_body in path:
            resp = self.client.get(reverse(name, kwargs=kwargs))
            self.assertEqual(resp.status_code, 200, name)
            self.assertContains(resp, heading)
            self.assertContains(resp, child_or_body)
            self.assertContains(resp, 'aria-label="Breadcrumb"')

    def test_unpublished_and_archived_nodes_are_404(self):
        draft_lesson = Lesson.objects.create(
            topic=self.tree["topic"],
            sort_order=9,
            editorial_state=EditorialState.DRAFT,
        )
        LessonTranslation.objects.create(
            lesson=draft_lesson, locale=LocaleCode.EN, title="Secret Draft Lesson", body="nope"
        )
        resp = self.client.get(
            reverse("learning:lesson", kwargs={"lesson_id": draft_lesson.id})
        )
        self.assertEqual(resp.status_code, 404)
        self.assertNotContains(resp, "Secret Draft Lesson", status_code=404)

        archived = self.tree["lesson_b"]
        archived.is_archived = True
        archived.editorial_state = EditorialState.ARCHIVED
        archived.save()
        resp = self.client.get(reverse("learning:lesson", kwargs={"lesson_id": archived.id}))
        self.assertEqual(resp.status_code, 404)

    def test_ancestor_unpublished_hides_child_lesson(self):
        subject = self.tree["subject"]
        subject.editorial_state = EditorialState.DRAFT
        subject.save(update_fields=["editorial_state"])
        resp = self.client.get(
            reverse("learning:lesson", kwargs={"lesson_id": self.tree["lesson_a"].id})
        )
        self.assertEqual(resp.status_code, 404)
        body = resp.content.decode("utf-8").lower()
        self.assertNotIn("lesson a body", body)

    def test_missing_ids_404(self):
        missing = uuid.uuid4()
        for name, kw in (
            ("learning:course", {"course_id": missing}),
            ("learning:subject", {"subject_id": missing}),
            ("learning:unit", {"unit_id": missing}),
            ("learning:chapter", {"chapter_id": missing}),
            ("learning:topic", {"topic_id": missing}),
            ("learning:lesson", {"lesson_id": missing}),
            ("learning:material", {"material_id": missing}),
        ):
            resp = self.client.get(reverse(name, kwargs=kw))
            self.assertEqual(resp.status_code, 404, name)


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"],
)
class LessonProgressAndMaterialsTests(TestCase):
    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)
        self.user, _ = AccountService.register(
            email="progress4@example.com",
            password=STRONG_PASSWORD,
            full_name="Progress Four",
        )
        self.tree = build_published_hierarchy(title_prefix="Prog")
        self._login()

    def _login(self):
        login_url = reverse("accounts:login")
        self.client.get(login_url)
        self.client.post(
            login_url,
            {
                "email": "progress4@example.com",
                "password": STRONG_PASSWORD,
                "next": "",
                "csrfmiddlewaretoken": self.client.cookies["csrftoken"].value,
            },
        )

    def _csrf_post(self, url, data=None):
        self.client.get(
            reverse("learning:lesson", kwargs={"lesson_id": self.tree["lesson_a"].id})
        )
        payload = dict(data or {})
        payload["csrfmiddlewaretoken"] = self.client.cookies["csrftoken"].value
        return self.client.post(url, payload)

    def test_lesson_page_shows_materials_and_completion_form(self):
        resp = self.client.get(
            reverse("learning:lesson", kwargs={"lesson_id": self.tree["lesson_a"].id})
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Prog Lesson A")
        self.assertContains(resp, "Prog Free Notes")
        self.assertContains(resp, "Mark lesson complete")
        self.assertContains(resp, "Premium required")
        self.assertNotContains(resp, "Premium secret body must not leak")

    def test_complete_lesson_success_and_idempotent(self):
        url = reverse(
            "learning:lesson_complete", kwargs={"lesson_id": self.tree["lesson_a"].id}
        )
        resp = self._csrf_post(url, {"confirm": "true"})
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(
            LearnerProgress.objects.filter(
                user=self.user, lesson=self.tree["lesson_a"], is_completed=True
            ).exists()
        )
        cursor = ContinueLearningCursor.objects.get(user=self.user)
        self.assertEqual(cursor.lesson_id, self.tree["lesson_a"].id)

        resp2 = self._csrf_post(url, {"confirm": "true"})
        self.assertEqual(resp2.status_code, 302)
        self.assertEqual(
            LearnerProgress.objects.filter(
                user=self.user, lesson=self.tree["lesson_a"]
            ).count(),
            1,
        )
        page = self.client.get(
            reverse("learning:lesson", kwargs={"lesson_id": self.tree["lesson_a"].id})
        )
        self.assertContains(page, "already complete")

    def test_complete_unpublished_lesson_not_found(self):
        draft = Lesson.objects.create(
            topic=self.tree["topic"],
            sort_order=8,
            editorial_state=EditorialState.DRAFT,
        )
        result = LearningProgressService.complete_lesson(user=self.user, lesson=draft)
        self.assertEqual(result, CompletionResult.NOT_FOUND)
        self.assertFalse(LearnerProgress.objects.filter(user=self.user, lesson=draft).exists())

    def test_visit_sets_continue_learning_cursor(self):
        self.client.get(
            reverse("learning:lesson", kwargs={"lesson_id": self.tree["lesson_b"].id})
        )
        cursor = ContinueLearningCursor.objects.get(user=self.user)
        self.assertEqual(cursor.lesson_id, self.tree["lesson_b"].id)

        dash = DashboardPresentationService.build(self.user)
        cont = next(s for s in dash["sections"] if s.key == "continue_learning")
        self.assertTrue(cont.available)
        self.assertFalse(cont.empty)
        self.assertEqual(cont.data["lesson_title"], "Prog Lesson B")
        self.assertTrue(dash["has_any_learning_data"])

        resp = self.client.get(reverse("portal:dashboard"))
        self.assertContains(resp, "Continue learning")
        self.assertContains(resp, "Prog Lesson B")

    def test_continue_learning_empty_when_no_cursor(self):
        state = LearningProgressService.continue_learning_for(self.user, locale="en")
        self.assertTrue(state.available)
        self.assertTrue(state.empty)
        self.assertIn("/learn/", state.href)

    def test_progress_percent_on_course_overview(self):
        LearningProgressService.complete_lesson(
            user=self.user, lesson=self.tree["lesson_a"]
        )
        resp = self.client.get(
            reverse("learning:course", kwargs={"course_id": self.tree["course"].id})
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "1 of 2 lessons complete")
        self.assertContains(resp, "50%")

    def test_premium_material_locked_for_free_user(self):
        material = self.tree["premium_material"]
        resp = self.client.get(
            reverse("learning:material", kwargs={"material_id": material.id})
            + f"?lesson={self.tree['lesson_a'].id}"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Premium required")
        self.assertNotContains(resp, "Premium secret body must not leak")

    def test_premium_material_available_for_premium_user(self):
        Subscription.objects.create(
            user=self.user, state=SubscriptionState.PREMIUM_ACTIVE
        )
        material = self.tree["premium_material"]
        resp = self.client.get(
            reverse("learning:material", kwargs={"material_id": material.id})
            + f"?lesson={self.tree['lesson_a'].id}"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Premium secret body must not leak")

    def test_draft_material_not_leaked(self):
        draft = LearningMaterial.objects.create(
            sort_order=9, editorial_state=EditorialState.DRAFT, is_premium=False
        )
        LearningMaterialTranslation.objects.create(
            learning_material=draft,
            locale=LocaleCode.EN,
            title="Draft Material Title",
            body="draft body",
        )
        LessonLearningMaterial.objects.create(
            lesson=self.tree["lesson_a"], learning_material=draft, sort_order=9
        )
        resp = self.client.get(
            reverse("learning:lesson", kwargs={"lesson_id": self.tree["lesson_a"].id})
        )
        self.assertNotContains(resp, "Draft Material Title")
        self.assertNotContains(resp, "draft body")
        detail = self.client.get(
            reverse("learning:material", kwargs={"material_id": draft.id})
        )
        self.assertEqual(detail.status_code, 404)

    def test_prev_next_lesson_links(self):
        resp = self.client.get(
            reverse("learning:lesson", kwargs={"lesson_id": self.tree["lesson_a"].id})
        )
        self.assertContains(resp, "Next: Prog Lesson B")
        resp_b = self.client.get(
            reverse("learning:lesson", kwargs={"lesson_id": self.tree["lesson_b"].id})
        )
        self.assertContains(resp_b, "Previous: Prog Lesson A")

    def test_access_service_fail_closed(self):
        decision = LearningAccessService.decide_lesson(None, self.tree["lesson_a"])
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, "forbidden")


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"],
)
class LearningPortalWiringAndSecurityTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user, _ = AccountService.register(
            email="wire4@example.com",
            password=STRONG_PASSWORD,
        )
        self.client.post(
            reverse("accounts:login"),
            {"email": "wire4@example.com", "password": STRONG_PASSWORD, "next": ""},
        )

    def test_learn_nav_points_to_catalog(self):
        items = NavigationService.items(active="learn")
        learn = next(i for i in items if i.key == "learn")
        self.assertTrue(learn.available)
        self.assertTrue(learn.current)
        self.assertEqual(learn.href, reverse("learning:catalog"))

    def test_completion_requires_post_and_auth(self):
        tree = build_published_hierarchy(title_prefix="Sec")
        url = reverse(
            "learning:lesson_complete", kwargs={"lesson_id": tree["lesson_a"].id}
        )
        get_resp = self.client.get(url)
        self.assertEqual(get_resp.status_code, 405)

        anon = Client()
        anon_resp = anon.post(url, {"confirm": "true"})
        self.assertEqual(anon_resp.status_code, 302)
        self.assertIn("/accounts/login/", anon_resp["Location"])

    def test_no_secret_leakage_on_learning_pages(self):
        tree = build_published_hierarchy(title_prefix="Leak")
        resp = self.client.get(reverse("learning:catalog"))
        body = resp.content.decode("utf-8").lower()
        for token in ("traceback", "secret_key", "db_password", "exception type"):
            self.assertNotIn(token, body)
        lesson = self.client.get(
            reverse("learning:lesson", kwargs={"lesson_id": tree["lesson_a"].id})
        )
        lesson_body = lesson.content.decode("utf-8").lower()
        self.assertNotIn("traceback", lesson_body)

    def test_empty_children_states(self):
        course = _publish(Course.objects.create(sort_order=5))
        CourseTranslation.objects.create(
            course=course, locale=LocaleCode.EN, title="Empty Course", summary=""
        )
        resp = self.client.get(
            reverse("learning:course", kwargs={"course_id": course.id})
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Nothing here yet")

    def test_progress_page_honest_empty_and_real_counts(self):
        empty = self.client.get(reverse("learning:progress"))
        self.assertEqual(empty.status_code, 200)
        self.assertContains(empty, "Learning progress")
        self.assertContains(empty, "No lesson in progress")

        tree = build_published_hierarchy(title_prefix="ProgPage")
        LearningProgressService.complete_lesson(
            user=self.user, lesson=tree["lesson_a"]
        )
        filled = self.client.get(reverse("learning:progress"))
        self.assertContains(filled, "ProgPage Course")
        self.assertContains(filled, "1 of 2 lessons complete")
        self.assertContains(filled, "Continue learning")
