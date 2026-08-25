"""Assessment services package — import concrete modules directly when needed."""

from apps.assessment.services.access import ExamAccessService, PracticeAccessService
from apps.assessment.services.exam import ExamService
from apps.assessment.services.exam_presentation import ExamPresentationService
from apps.assessment.services.exam_pool import ExamPoolService
from apps.assessment.services.scoring import build_score_summary, score_attempt_items

# PracticeService / pool / presentation import learning helpers lazily where needed.
from apps.assessment.services.practice import PracticeService
from apps.assessment.services.presentation import PracticePresentationService
from apps.assessment.services.pool import PracticePoolService

__all__ = [
    "PracticeAccessService",
    "ExamAccessService",
    "PracticeService",
    "ExamService",
    "PracticePresentationService",
    "ExamPresentationService",
    "PracticePoolService",
    "ExamPoolService",
    "build_score_summary",
    "score_attempt_items",
]
