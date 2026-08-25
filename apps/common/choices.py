"""Cross-cutting value-object enums aligned to docs/05–06 and docs/09."""
from django.db import models


class LocaleCode(models.TextChoices):
    BN = "bn", "Bangla"
    EN = "en", "English"


class EditorialState(models.TextChoices):
    DRAFT = "draft", "Draft"
    REVIEW = "review", "Review"
    APPROVED = "approved", "Approved"
    PUBLISHED = "published", "Published"
    ARCHIVED = "archived", "Archived"


class DifficultyLevel(models.TextChoices):
    EASY = "easy", "Easy"
    MEDIUM = "medium", "Medium"
    HARD = "hard", "Hard"
    EXPERT = "expert", "Expert"


class QuestionType(models.TextChoices):
    MCQ = "mcq", "MCQ"
    TRUE_FALSE = "true_false", "True/False"
    BEST_ANSWER = "best_answer", "Best Answer"
    CLINICAL_SCENARIO = "clinical_scenario", "Clinical Scenario"
    IMAGE_BASED = "image_based", "Image-Based"


class CognitiveLevel(models.TextChoices):
    """Bloom-derived levels from the BNMC blueprint (Recall/Understanding/Application)."""

    RECALL = "recall", "Recall"
    UNDERSTANDING = "understanding", "Understanding"
    APPLICATION = "application", "Application"


class ClassificationOrigin(models.TextChoices):
    """Suggested ≠ approved. Blank on the row means import/legacy/unspecified."""

    SUGGESTED = "suggested", "Suggested"
    APPROVED = "approved", "Approved"


class QuestionSourceType(models.TextChoices):
    """Provenance category for a question (ADMIN-ONLY — never exposed to students)."""

    OFFICIAL_EXAM = "official_exam", "Official Exam"
    BLUEPRINT = "blueprint", "Blueprint"
    TEXTBOOK = "textbook", "Textbook"
    STAFF_CREATED = "staff_created", "Staff Created"
    IMPORTED = "imported", "Imported"
    OTHER = "other", "Other"


class AttemptMode(models.TextChoices):
    PRACTICE = "practice", "Practice"
    CHAPTER_EXAM = "chapter_exam", "Chapter Exam"
    SUBJECT_EXAM = "subject_exam", "Subject Exam"
    TIMED_EXAM = "timed_exam", "Timed Exam"
    MOCK = "mock", "Mock"
    CUSTOM = "custom", "Custom"


class AttemptState(models.TextChoices):
    NOT_STARTED = "not_started", "Not Started"
    IN_PROGRESS = "in_progress", "In Progress"
    SUBMITTED = "submitted", "Submitted"
    COMPLETED = "completed", "Completed"


class SubscriptionState(models.TextChoices):
    FREE = "free", "Free"
    PENDING_PAYMENT = "pending_payment", "Pending Payment"
    PREMIUM_ACTIVE = "premium_active", "Premium Active"
    EXPIRED = "expired", "Expired"
    REVOKED = "revoked", "Revoked"


class PaymentGateway(models.TextChoices):
    BKASH = "bkash", "bKash"
    NAGAD = "nagad", "Nagad"
    SSLCOMMERZ = "sslcommerz", "SSLCommerz"


class PaymentStatus(models.TextChoices):
    INITIATED = "initiated", "Initiated"
    CONFIRMED = "confirmed", "Confirmed"
    FAILED = "failed", "Failed"


class BookFormat(models.TextChoices):
    PDF = "pdf", "PDF"
    EPUB = "epub", "EPUB"
    HTML = "html", "HTML"
    IMAGE = "image", "Image"


class RoleCode(models.TextChoices):
    SUPER_ADMIN = "super_admin", "Super Admin"
    ADMIN = "admin", "Admin"
    EDITOR = "editor", "Editor"
    REVIEWER = "reviewer", "Reviewer"
    AUTHOR = "author", "Author"
    STUDENT = "student", "Student"


class ContactMessageStatus(models.TextChoices):
    NEW = "new", "New"
    IN_PROGRESS = "in_progress", "In Progress"
    RESOLVED = "resolved", "Resolved"
    CLOSED = "closed", "Closed"


class QuestionErrorReportStatus(models.TextChoices):
    OPEN = "open", "Open"
    TRIAGED = "triaged", "Triaged"
    RESOLVED = "resolved", "Resolved"
    DISMISSED = "dismissed", "Dismissed"


class SearchEntityType(models.TextChoices):
    COURSE = "course", "Course"
    BOOK = "book", "Book"
    LESSON = "lesson", "Lesson"
    QUESTION = "question", "Question"
    AUTHOR = "author", "Author"
