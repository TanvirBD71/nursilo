"""
Development-only demo content seed/cleanup for nursilo_dev.

Identifiable demo markers only — never used as a production data loader.
Passwords come from NURSILO_DEMO_PASSWORD (never logged or printed).
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.accounts.models import AcademicProfile, UserAccount
from apps.accounts.services import AccountService
from apps.assessment.models import (
    Attempt,
    AttemptItem,
    ExamDefinition,
    ExamDefinitionItem,
    Question,
    QuestionOption,
    QuestionOptionTranslation,
    QuestionTag,
    QuestionTopic,
    QuestionVersion,
    QuestionVersionTranslation,
    Tag,
)
from apps.billing.models import PaymentTransaction, Subscription
from apps.common.choices import (
    AttemptMode,
    BookFormat,
    DifficultyLevel,
    EditorialState,
    LocaleCode,
    QuestionType,
    RoleCode,
    SubscriptionState,
)
from apps.engagement.models import Bookmark, PersonalNote, StudyGoal, StudyStreak
from apps.entitlements.models import EntitlementGrant
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
from apps.learning.services import LearningProgressService
from apps.library.models import Book, BookAsset, BookTranslation
from apps.notifications.models import Notification
from apps.rbac.models import Role, RoleAssignment
from apps.rbac.services import AccessControlService


DEMO_TAG_CODE = "nursilo_demo"
DEMO_EXAM_CODE = "nursilo_demo_timed_exam"
DEMO_COURSE_TITLE = "Nursilo Demo Course"
DEMO_SUBJECT_TITLE = "Nursilo Demo Subject"
DEMO_UNIT_TITLE = "Nursilo Demo Unit"
DEMO_CHAPTER_TITLE = "Nursilo Demo Chapter"
DEMO_TOPIC_TITLE = "Nursilo Demo Topic"
DEMO_LESSON_TITLES = (
    "Nursilo Demo Lesson 1",
    "Nursilo Demo Lesson 2",
    "Nursilo Demo Lesson 3",
)
DEMO_FREE_MATERIAL_TITLE = "Nursilo Demo Free Notes"
DEMO_PREMIUM_MATERIAL_TITLE = "Nursilo Demo Premium Notes"
DEMO_FREE_BOOK_TITLE = "Nursilo Demo Free Book"
DEMO_PREMIUM_BOOK_TITLE = "Nursilo Demo Premium Book"
DEMO_MEDIA_PREFIX = "library/nursilo_demo"
DEMO_QUESTION_STEM_PREFIX = "[Nursilo Demo]"
DEMO_EXAM_TITLE_KEY = "Nursilo Demo Timed Exam"

DEMO_STUDENT_EMAIL = "student.demo@nursilo.example"
DEMO_PREMIUM_EMAIL = "premium.demo@nursilo.example"
DEMO_STAFF_EMAIL = "staff.demo@nursilo.example"
DEMO_EMAILS = (DEMO_STUDENT_EMAIL, DEMO_PREMIUM_EMAIL, DEMO_STAFF_EMAIL)

SAFE_DB_NAMES = frozenset({"nursilo_dev", "test_nursilo_dev"})
DEMO_PASSWORD_ENV = "NURSILO_DEMO_PASSWORD"
# Local-only fallback — never printed, never included in reports.
_LOCAL_ONLY_DEMO_PASSWORD = "Nursilo-Demo-Pass1!"

PRACTICE_QUESTION_COUNT = 12
EXAM_POOL_SIZE = 8


class DemoSeedError(Exception):
    """Raised when seed/cleanup refuses or cannot proceed safely."""


@dataclass
class SeedReport:
    created: list[str] = field(default_factory=list)
    updated: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)

    def note_created(self, label: str) -> None:
        self.created.append(label)

    def note_updated(self, label: str) -> None:
        self.updated.append(label)

    def note_skipped(self, label: str) -> None:
        self.skipped.append(label)

    def as_lines(self) -> list[str]:
        lines = []
        if self.created:
            lines.append("Created: " + ", ".join(self.created))
        if self.updated:
            lines.append("Updated: " + ", ".join(self.updated))
        if self.skipped:
            lines.append("Already present: " + ", ".join(self.skipped))
        return lines or ["No changes."]


def assert_safe_demo_environment() -> None:
    """Refuse outside DEBUG + nursilo_dev (or Django test_nursilo_dev)."""
    if not settings.DEBUG:
        raise DemoSeedError("Demo seed/cleanup refused: DEBUG must be True.")
    module = (getattr(settings, "SETTINGS_MODULE", "") or "").lower()
    if "production" in module:
        raise DemoSeedError("Demo seed/cleanup refused: production settings module.")
    db_name = settings.DATABASES["default"]["NAME"]
    if db_name not in SAFE_DB_NAMES:
        raise DemoSeedError(
            f"Demo seed/cleanup refused: database must be nursilo_dev "
            f"(got {db_name!r})."
        )


def resolve_demo_password() -> str:
    """Password from env, else local-only fallback. Never log the value."""
    raw = (os.environ.get(DEMO_PASSWORD_ENV) or "").strip()
    if raw:
        return raw
    return _LOCAL_ONLY_DEMO_PASSWORD


def _publish(node, **kwargs):
    node.editorial_state = EditorialState.PUBLISHED
    node.is_archived = False
    for key, value in kwargs.items():
        setattr(node, key, value)
    node.save()
    return node


def _write_media(rel_key: str, content: str | bytes) -> str:
    path = Path(settings.MEDIA_ROOT) / rel_key
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, bytes):
        path.write_bytes(content)
    else:
        path.write_text(content, encoding="utf-8")
    return rel_key


def _get_course_by_title(title: str) -> Course | None:
    tr = (
        CourseTranslation.objects.filter(locale=LocaleCode.EN, title=title)
        .select_related("course")
        .first()
    )
    return tr.course if tr else None


def _ensure_course(report: SeedReport) -> Course:
    course = _get_course_by_title(DEMO_COURSE_TITLE)
    if course:
        _publish(course, sort_order=1)
        report.note_skipped("course")
        return course
    course = _publish(Course.objects.create(sort_order=1))
    CourseTranslation.objects.create(
        course=course,
        locale=LocaleCode.EN,
        title=DEMO_COURSE_TITLE,
        summary="Fictional demo course for Nursilo development acceptance.",
    )
    report.note_created("course")
    return course


def _ensure_subject(course: Course, report: SeedReport) -> Subject:
    tr = (
        SubjectTranslation.objects.filter(
            locale=LocaleCode.EN, title=DEMO_SUBJECT_TITLE, subject__course=course
        )
        .select_related("subject")
        .first()
    )
    if tr:
        _publish(tr.subject, sort_order=1)
        report.note_skipped("subject")
        return tr.subject
    subject = _publish(Subject.objects.create(course=course, sort_order=1))
    SubjectTranslation.objects.create(
        subject=subject,
        locale=LocaleCode.EN,
        title=DEMO_SUBJECT_TITLE,
        summary="Demo subject covering foundational nursing concepts (fictional).",
    )
    report.note_created("subject")
    return subject


def _ensure_unit(subject: Subject, report: SeedReport) -> Unit:
    tr = (
        UnitTranslation.objects.filter(
            locale=LocaleCode.EN, title=DEMO_UNIT_TITLE, unit__subject=subject
        )
        .select_related("unit")
        .first()
    )
    if tr:
        _publish(tr.unit, sort_order=1)
        report.note_skipped("unit")
        return tr.unit
    unit = _publish(Unit.objects.create(subject=subject, sort_order=1))
    UnitTranslation.objects.create(
        unit=unit,
        locale=LocaleCode.EN,
        title=DEMO_UNIT_TITLE,
        summary="Demo unit for catalog navigation and progress.",
    )
    report.note_created("unit")
    return unit


def _ensure_chapter(unit: Unit, report: SeedReport) -> Chapter:
    tr = (
        ChapterTranslation.objects.filter(
            locale=LocaleCode.EN, title=DEMO_CHAPTER_TITLE, chapter__unit=unit
        )
        .select_related("chapter")
        .first()
    )
    if tr:
        _publish(tr.chapter, sort_order=1)
        report.note_skipped("chapter")
        return tr.chapter
    chapter = _publish(Chapter.objects.create(unit=unit, sort_order=1))
    ChapterTranslation.objects.create(
        chapter=chapter,
        locale=LocaleCode.EN,
        title=DEMO_CHAPTER_TITLE,
        summary="Demo chapter with practice-scoped topics.",
    )
    report.note_created("chapter")
    return chapter


def _ensure_topic(chapter: Chapter, report: SeedReport) -> Topic:
    tr = (
        TopicTranslation.objects.filter(
            locale=LocaleCode.EN, title=DEMO_TOPIC_TITLE, topic__chapter=chapter
        )
        .select_related("topic")
        .first()
    )
    if tr:
        _publish(tr.topic, sort_order=1)
        report.note_skipped("topic")
        return tr.topic
    topic = _publish(Topic.objects.create(chapter=chapter, sort_order=1))
    TopicTranslation.objects.create(
        topic=topic,
        locale=LocaleCode.EN,
        title=DEMO_TOPIC_TITLE,
        summary="Demo topic for lessons and question pool scoping.",
    )
    report.note_created("topic")
    return topic


def _ensure_lessons(topic: Topic, report: SeedReport) -> list[Lesson]:
    lessons: list[Lesson] = []
    for idx, title in enumerate(DEMO_LESSON_TITLES, start=1):
        tr = (
            LessonTranslation.objects.filter(
                locale=LocaleCode.EN, title=title, lesson__topic=topic
            )
            .select_related("lesson")
            .first()
        )
        if tr:
            _publish(tr.lesson, sort_order=idx)
            lessons.append(tr.lesson)
            report.note_skipped(f"lesson:{idx}")
            continue
        lesson = _publish(Lesson.objects.create(topic=topic, sort_order=idx))
        LessonTranslation.objects.create(
            lesson=lesson,
            locale=LocaleCode.EN,
            title=title,
            body=(
                f"<p>Fictional demo lesson body for <strong>{title}</strong>. "
                "This content is for development acceptance only and is not "
                "clinical advice.</p>"
            ),
        )
        lessons.append(lesson)
        report.note_created(f"lesson:{idx}")
    return lessons


def _ensure_materials(lesson: Lesson, report: SeedReport) -> None:
    free_tr = (
        LearningMaterialTranslation.objects.filter(
            locale=LocaleCode.EN, title=DEMO_FREE_MATERIAL_TITLE
        )
        .select_related("learning_material")
        .first()
    )
    if free_tr:
        free_mat = _publish(free_tr.learning_material, sort_order=1, is_premium=False)
        report.note_skipped("free_material")
    else:
        free_mat = _publish(
            LearningMaterial.objects.create(sort_order=1, is_premium=False)
        )
        LearningMaterialTranslation.objects.create(
            learning_material=free_mat,
            locale=LocaleCode.EN,
            title=DEMO_FREE_MATERIAL_TITLE,
            body="<p>Fictional free study notes for Nursilo demo learners.</p>",
        )
        report.note_created("free_material")
    LessonLearningMaterial.objects.get_or_create(
        lesson=lesson, learning_material=free_mat, defaults={"sort_order": 0}
    )

    prem_tr = (
        LearningMaterialTranslation.objects.filter(
            locale=LocaleCode.EN, title=DEMO_PREMIUM_MATERIAL_TITLE
        )
        .select_related("learning_material")
        .first()
    )
    if prem_tr:
        prem_mat = _publish(prem_tr.learning_material, sort_order=2, is_premium=True)
        report.note_skipped("premium_material")
    else:
        prem_mat = _publish(
            LearningMaterial.objects.create(sort_order=2, is_premium=True)
        )
        LearningMaterialTranslation.objects.create(
            learning_material=prem_mat,
            locale=LocaleCode.EN,
            title=DEMO_PREMIUM_MATERIAL_TITLE,
            body="<p>Fictional premium notes unlocked via existing entitlement.</p>",
        )
        report.note_created("premium_material")
    LessonLearningMaterial.objects.get_or_create(
        lesson=lesson, learning_material=prem_mat, defaults={"sort_order": 1}
    )


def _ensure_tag(report: SeedReport) -> Tag:
    tag, created = Tag.objects.get_or_create(
        code=DEMO_TAG_CODE, defaults={"name": "Nursilo Demo"}
    )
    if created:
        report.note_created("tag")
    else:
        report.note_skipped("tag")
    return tag


def _demo_questions_qs():
    return Question.objects.filter(tags__code=DEMO_TAG_CODE).distinct()


def _publish_question(topic: Topic, tag: Tag, *, index: int) -> Question:
    stem = (
        f"{DEMO_QUESTION_STEM_PREFIX} Practice question {index}: "
        "which action is safest?"
    )
    question = Question.objects.create(
        question_type=QuestionType.MCQ,
        difficulty=DifficultyLevel.EASY if index % 2 else DifficultyLevel.MEDIUM,
        editorial_state=EditorialState.PUBLISHED,
        is_archived=False,
        primary_locale=LocaleCode.EN,
    )
    version = QuestionVersion.objects.create(
        question=question,
        version_no=1,
        correct_answer_spec={"key": "A"},
        clinical_scenario_body="",
    )
    question.current_version = version
    question.save(update_fields=["current_version", "updated_at"])
    QuestionVersionTranslation.objects.create(
        version=version,
        locale=LocaleCode.EN,
        stem=stem,
        explanation="Fictional demo explanation — evidence supports option A.",
    )
    labels = {
        "A": "Prioritize airway and call for help (correct — demo)",
        "B": "Delay assessment until paperwork is done",
        "C": "Ignore vital-sign changes",
        "D": "Leave the bedside without handover",
    }
    for i, (key, label) in enumerate(labels.items()):
        opt = QuestionOption.objects.create(
            question_version=version,
            key=key,
            is_correct=(key == "A"),
            sort_order=i,
        )
        QuestionOptionTranslation.objects.create(
            option=opt, locale=LocaleCode.EN, label=label
        )
    QuestionTopic.objects.create(question=question, topic=topic)
    QuestionTag.objects.create(question=question, tag=tag)
    return question


def _ensure_questions(topic: Topic, tag: Tag, report: SeedReport) -> list[Question]:
    existing = list(_demo_questions_qs().order_by("created_at"))
    if len(existing) >= PRACTICE_QUESTION_COUNT:
        for q in existing:
            if q.editorial_state != EditorialState.PUBLISHED or q.is_archived:
                q.editorial_state = EditorialState.PUBLISHED
                q.is_archived = False
                q.save(update_fields=["editorial_state", "is_archived", "updated_at"])
        report.note_skipped(f"questions:{len(existing)}")
        return existing[:PRACTICE_QUESTION_COUNT]
    needed = PRACTICE_QUESTION_COUNT - len(existing)
    created = []
    start = len(existing) + 1
    for i in range(needed):
        created.append(_publish_question(topic, tag, index=start + i))
    report.note_created(f"questions:+{needed}")
    return existing + created


def _ensure_exam(questions: list[Question], report: SeedReport) -> ExamDefinition:
    exam = ExamDefinition.objects.filter(code=DEMO_EXAM_CODE).first()
    pool = questions[:EXAM_POOL_SIZE]
    if exam:
        exam.title_key = DEMO_EXAM_TITLE_KEY
        exam.mode = AttemptMode.TIMED_EXAM
        exam.time_limit_seconds = 900
        exam.is_premium = False
        exam.track_code = None
        exam.editorial_state = EditorialState.PUBLISHED
        exam.is_archived = False
        exam.rules = {}
        exam.save()
        existing_ids = set(
            ExamDefinitionItem.objects.filter(exam_definition=exam).values_list(
                "question_id", flat=True
            )
        )
        for i, q in enumerate(pool):
            if q.id not in existing_ids:
                ExamDefinitionItem.objects.create(
                    exam_definition=exam, question=q, sort_order=i
                )
        report.note_updated("exam")
        return exam
    exam = ExamDefinition.objects.create(
        code=DEMO_EXAM_CODE,
        title_key=DEMO_EXAM_TITLE_KEY,
        mode=AttemptMode.TIMED_EXAM,
        time_limit_seconds=900,
        is_premium=False,
        track_code=None,
        editorial_state=EditorialState.PUBLISHED,
        is_archived=False,
        rules={},
    )
    for i, q in enumerate(pool):
        ExamDefinitionItem.objects.create(
            exam_definition=exam, question=q, sort_order=i
        )
    report.note_created("exam")
    return exam


def _ensure_book_asset(book: Book, fmt: str, storage_key: str, sort_order: int) -> None:
    asset = BookAsset.objects.filter(book=book, format=fmt).first()
    if asset:
        if asset.storage_key != storage_key:
            asset.storage_key = storage_key
            asset.sort_order = sort_order
            asset.save(update_fields=["storage_key", "sort_order"])
        return
    BookAsset.objects.create(
        book=book, format=fmt, storage_key=storage_key, sort_order=sort_order
    )


def _ensure_books(report: SeedReport) -> tuple[Book, Book]:
    cover_key = _write_media(
        f"{DEMO_MEDIA_PREFIX}/cover.png",
        b"\x89PNG\r\n\x1a\nNursiloDemoCover",
    )
    free_html = _write_media(
        f"{DEMO_MEDIA_PREFIX}/free.html",
        "<article><h1>Nursilo Demo Free Book</h1>"
        "<p>Fictional free reader content for development acceptance.</p></article>",
    )
    free_pdf = _write_media(
        f"{DEMO_MEDIA_PREFIX}/free.pdf",
        b"%PDF-1.4 Nursilo demo free asset",
    )
    premium_html = _write_media(
        f"{DEMO_MEDIA_PREFIX}/premium.html",
        "<article><h1>Nursilo Demo Premium Book</h1>"
        "<p>Fictional premium reader content — entitlement gated.</p></article>",
    )

    free_tr = (
        BookTranslation.objects.filter(
            locale=LocaleCode.EN, title=DEMO_FREE_BOOK_TITLE
        )
        .select_related("book")
        .first()
    )
    if free_tr:
        free_book = _publish(
            free_tr.book,
            category="Anatomy",
            author_name="Nursilo Demo Author",
            edition="1st",
            publisher="Nursilo Demo Press",
            cover_storage_key=cover_key,
            is_premium=False,
        )
        report.note_skipped("free_book")
    else:
        free_book = _publish(
            Book.objects.create(
                category="Anatomy",
                author_name="Nursilo Demo Author",
                edition="1st",
                publisher="Nursilo Demo Press",
                cover_storage_key=cover_key,
                is_premium=False,
            )
        )
        BookTranslation.objects.create(
            book=free_book,
            locale=LocaleCode.EN,
            title=DEMO_FREE_BOOK_TITLE,
            blurb="Fictional free nursing primer for demo catalog and reader flows.",
        )
        report.note_created("free_book")
    _ensure_book_asset(free_book, BookFormat.HTML, free_html, 0)
    _ensure_book_asset(free_book, BookFormat.PDF, free_pdf, 1)

    prem_tr = (
        BookTranslation.objects.filter(
            locale=LocaleCode.EN, title=DEMO_PREMIUM_BOOK_TITLE
        )
        .select_related("book")
        .first()
    )
    if prem_tr:
        premium_book = _publish(
            prem_tr.book,
            category="Pharmacology",
            author_name="Nursilo Demo Premium Author",
            edition="1st",
            publisher="Nursilo Demo Press",
            is_premium=True,
        )
        report.note_skipped("premium_book")
    else:
        premium_book = _publish(
            Book.objects.create(
                category="Pharmacology",
                author_name="Nursilo Demo Premium Author",
                edition="1st",
                publisher="Nursilo Demo Press",
                is_premium=True,
            )
        )
        BookTranslation.objects.create(
            book=premium_book,
            locale=LocaleCode.EN,
            title=DEMO_PREMIUM_BOOK_TITLE,
            blurb="Fictional premium title — locked for free students via entitlement.",
        )
        report.note_created("premium_book")
    _ensure_book_asset(premium_book, BookFormat.HTML, premium_html, 0)
    return free_book, premium_book


def _ensure_student(
    email: str, full_name: str, password: str, report: SeedReport
) -> UserAccount:
    user = UserAccount.objects.filter(email=email).first()
    if user:
        AccountService.mark_email_verified(user)
        if not AccessControlService.has_role(user, RoleCode.STUDENT):
            AccessControlService.assign_role(
                user=user, role_code=RoleCode.STUDENT, assigned_by=None
            )
        AcademicProfile.objects.get_or_create(user=user)
        report.note_skipped(f"user:{email}")
        return user
    user, _token = AccountService.register(
        email=email, password=password, full_name=full_name
    )
    AccountService.mark_email_verified(user)
    report.note_created(f"user:{email}")
    return user


def _ensure_staff(email: str, password: str, report: SeedReport) -> UserAccount:
    user = UserAccount.objects.filter(email=email).first()
    if user:
        AccountService.mark_email_verified(user)
        role = Role.objects.get(code=RoleCode.ADMIN)
        RoleAssignment.objects.get_or_create(user=user, role=role)
        AcademicProfile.objects.get_or_create(user=user)
        report.note_skipped(f"user:{email}")
        return user
    user = UserAccount.objects.create_user(
        email=email,
        password=password,
        full_name="Nursilo Demo Staff",
        is_active=True,
    )
    AcademicProfile.objects.get_or_create(user=user)
    AccountService.mark_email_verified(user)
    role = Role.objects.get(code=RoleCode.ADMIN)
    RoleAssignment.objects.get_or_create(user=user, role=role)
    report.note_created(f"user:{email}")
    return user


def _ensure_subscriptions(
    free_user: UserAccount, premium_user: UserAccount, report: SeedReport
) -> None:
    Subscription.objects.update_or_create(
        user=free_user,
        defaults={"state": SubscriptionState.FREE},
    )
    now = timezone.now()
    Subscription.objects.update_or_create(
        user=premium_user,
        defaults={
            "state": SubscriptionState.PREMIUM_ACTIVE,
            "premium_started_at": now,
            "premium_expires_at": now + timedelta(days=365),
        },
    )
    report.note_updated("subscriptions")


def _ensure_dashboard_extras(
    *,
    free_user: UserAccount,
    premium_user: UserAccount,
    lessons: list[Lesson],
    free_book: Book,
    report: SeedReport,
) -> None:
    if lessons:
        LearningProgressService.complete_lesson(user=free_user, lesson=lessons[0])
        if len(lessons) > 1:
            LearningProgressService.record_lesson_visit(
                user=free_user, lesson=lessons[1]
            )
            LearningProgressService.record_lesson_visit(
                user=premium_user, lesson=lessons[1]
            )
        report.note_updated("progress")

    Bookmark.objects.get_or_create(
        user=free_user, target_type="book", target_id=free_book.id
    )
    Bookmark.objects.get_or_create(
        user=premium_user, target_type="book", target_id=free_book.id
    )
    Notification.objects.get_or_create(
        user=free_user,
        kind="system",
        title="Nursilo Demo Welcome",
        defaults={
            "body": "Fictional demo notification for dashboard acceptance.",
            "is_read": False,
        },
    )
    Notification.objects.get_or_create(
        user=premium_user,
        kind="system",
        title="Nursilo Demo Premium Notice",
        defaults={
            "body": "Your demo Premium subscription is active for development.",
            "is_read": False,
        },
    )
    StudyGoal.objects.get_or_create(
        user=free_user,
        title="Nursilo Demo Study Goal",
        defaults={
            "target_count": 5,
            "progress_count": 1,
            "is_active": True,
        },
    )
    StudyStreak.objects.update_or_create(
        user=free_user,
        defaults={
            "current_streak_days": 2,
            "longest_streak_days": 2,
            "last_activity_date": timezone.localdate(),
        },
    )
    report.note_updated("dashboard_extras")


@transaction.atomic
def seed_demo_data(*, password: str | None = None) -> SeedReport:
    assert_safe_demo_environment()
    password = password or resolve_demo_password()
    report = SeedReport()

    # Avoid printing verification tokens to console during seed.
    from django.test.utils import override_settings

    with override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"
    ):
        return _seed_demo_data_inner(password=password, report=report)


def _seed_demo_data_inner(*, password: str, report: SeedReport) -> SeedReport:
    course = _ensure_course(report)
    subject = _ensure_subject(course, report)
    unit = _ensure_unit(subject, report)
    chapter = _ensure_chapter(unit, report)
    topic = _ensure_topic(chapter, report)
    lessons = _ensure_lessons(topic, report)
    if lessons:
        _ensure_materials(lessons[0], report)

    tag = _ensure_tag(report)
    questions = _ensure_questions(topic, tag, report)
    _ensure_exam(questions, report)
    free_book, _premium_book = _ensure_books(report)

    free_user = _ensure_student(
        DEMO_STUDENT_EMAIL, "Nursilo Demo Student", password, report
    )
    premium_user = _ensure_student(
        DEMO_PREMIUM_EMAIL, "Nursilo Demo Premium Student", password, report
    )
    _ensure_staff(DEMO_STAFF_EMAIL, password, report)
    _ensure_subscriptions(free_user, premium_user, report)
    _ensure_dashboard_extras(
        free_user=free_user,
        premium_user=premium_user,
        lessons=lessons,
        free_book=free_book,
        report=report,
    )
    return report


def _demo_book_ids():
    return list(
        BookTranslation.objects.filter(
            locale=LocaleCode.EN,
            title__in=[DEMO_FREE_BOOK_TITLE, DEMO_PREMIUM_BOOK_TITLE],
        ).values_list("book_id", flat=True)
    )


def _demo_lesson_ids():
    return list(
        LessonTranslation.objects.filter(
            locale=LocaleCode.EN, title__in=DEMO_LESSON_TITLES
        ).values_list("lesson_id", flat=True)
    )


def _demo_material_ids():
    return list(
        LearningMaterialTranslation.objects.filter(
            locale=LocaleCode.EN,
            title__in=[DEMO_FREE_MATERIAL_TITLE, DEMO_PREMIUM_MATERIAL_TITLE],
        ).values_list("learning_material_id", flat=True)
    )


@transaction.atomic
def cleanup_demo_data() -> SeedReport:
    """Remove only identifiable Nursilo Demo records. Never deletes non-demo data."""
    assert_safe_demo_environment()
    report = SeedReport()

    demo_users = list(UserAccount.objects.filter(email__in=DEMO_EMAILS))
    demo_user_ids = [u.id for u in demo_users]
    question_ids = list(_demo_questions_qs().values_list("id", flat=True))
    exam = ExamDefinition.objects.filter(code=DEMO_EXAM_CODE).first()
    book_ids = _demo_book_ids()
    lesson_ids = _demo_lesson_ids()
    material_ids = _demo_material_ids()
    course = _get_course_by_title(DEMO_COURSE_TITLE)

    attempt_filter = Q()
    if demo_user_ids:
        attempt_filter |= Q(user_id__in=demo_user_ids)
    if exam:
        attempt_filter |= Q(exam_definition=exam)
    if question_ids:
        attempt_filter |= Q(items__question_id__in=question_ids)
    if attempt_filter:
        attempt_ids = list(
            Attempt.objects.filter(attempt_filter)
            .distinct()
            .values_list("id", flat=True)
        )
        if attempt_ids:
            AttemptItem.objects.filter(attempt_id__in=attempt_ids).delete()
            Attempt.objects.filter(id__in=attempt_ids).delete()
            report.note_updated(f"attempts:-{len(attempt_ids)}")

    if demo_user_ids:
        Notification.objects.filter(user_id__in=demo_user_ids).delete()
        Bookmark.objects.filter(user_id__in=demo_user_ids).delete()
        PersonalNote.objects.filter(user_id__in=demo_user_ids).delete()
        StudyGoal.objects.filter(user_id__in=demo_user_ids).delete()
        StudyStreak.objects.filter(user_id__in=demo_user_ids).delete()
        LearnerProgress.objects.filter(user_id__in=demo_user_ids).delete()
        ContinueLearningCursor.objects.filter(user_id__in=demo_user_ids).delete()
        EntitlementGrant.objects.filter(user_id__in=demo_user_ids).delete()
        PaymentTransaction.objects.filter(user_id__in=demo_user_ids).delete()
        Subscription.objects.filter(user_id__in=demo_user_ids).delete()
        RoleAssignment.objects.filter(user_id__in=demo_user_ids).delete()
        AcademicProfile.objects.filter(user_id__in=demo_user_ids).delete()

    if exam:
        ExamDefinitionItem.objects.filter(exam_definition=exam).delete()
        exam.delete()
        report.note_updated("exam:removed")

    if lesson_ids:
        LearnerProgress.objects.filter(lesson_id__in=lesson_ids).delete()
        ContinueLearningCursor.objects.filter(lesson_id__in=lesson_ids).delete()

    if question_ids:
        QuestionTag.objects.filter(question_id__in=question_ids).delete()
        QuestionTopic.objects.filter(question_id__in=question_ids).delete()
        Question.objects.filter(id__in=question_ids).update(current_version=None)
        QuestionVersion.objects.filter(question_id__in=question_ids).delete()
        Question.objects.filter(id__in=question_ids).delete()
        report.note_updated(f"questions:-{len(question_ids)}")

    Tag.objects.filter(code=DEMO_TAG_CODE).delete()

    if book_ids:
        Bookmark.objects.filter(target_type="book", target_id__in=book_ids).delete()
        BookAsset.objects.filter(book_id__in=book_ids).delete()
        BookTranslation.objects.filter(book_id__in=book_ids).delete()
        Book.objects.filter(id__in=book_ids).delete()
        report.note_updated(f"books:-{len(book_ids)}")

    media_root = Path(settings.MEDIA_ROOT) / DEMO_MEDIA_PREFIX
    if media_root.exists():
        for path in media_root.glob("*"):
            if path.is_file():
                path.unlink(missing_ok=True)
        try:
            media_root.rmdir()
        except OSError:
            pass

    if material_ids:
        LessonLearningMaterial.objects.filter(
            learning_material_id__in=material_ids
        ).delete()
        LearningMaterialTranslation.objects.filter(
            learning_material_id__in=material_ids
        ).delete()
        LearningMaterial.objects.filter(id__in=material_ids).delete()

    if lesson_ids:
        LessonLearningMaterial.objects.filter(lesson_id__in=lesson_ids).delete()
        LessonTranslation.objects.filter(lesson_id__in=lesson_ids).delete()
        Lesson.objects.filter(id__in=lesson_ids).delete()

    if course:
        subjects = Subject.objects.filter(course=course)
        units = Unit.objects.filter(subject__in=subjects)
        chapters = Chapter.objects.filter(unit__in=units)
        topics = Topic.objects.filter(chapter__in=chapters)
        TopicTranslation.objects.filter(topic__in=topics).delete()
        topics.delete()
        ChapterTranslation.objects.filter(chapter__in=chapters).delete()
        chapters.delete()
        UnitTranslation.objects.filter(unit__in=units).delete()
        units.delete()
        SubjectTranslation.objects.filter(subject__in=subjects).delete()
        subjects.delete()
        CourseTranslation.objects.filter(course=course).delete()
        course.delete()
        report.note_updated("learning:removed")

    if demo_users:
        count = len(demo_users)
        UserAccount.objects.filter(id__in=demo_user_ids).delete()
        report.note_updated(f"users:-{count}")

    return report
