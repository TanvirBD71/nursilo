"""Public landing presentation assembly — display data only (docs/15 Family A)."""
from __future__ import annotations

from dataclasses import dataclass

from apps.billing.plans import PlanCatalog, PlanDefinition
from apps.common.choices import LocaleCode
from apps.learning.models import Subject
from apps.learning.services import LearningCatalogService

_MOTIF_RULES = (
    ("pharmacolog", "capsule"),
    ("midwifer", "heart"),
    ("pediatric", "heart"),
    ("paediatric", "heart"),
    ("psychiatr", "brain"),
    ("mental health", "brain"),
    ("nutrition", "clipboard"),
    ("diet", "clipboard"),
    ("fundament", "book"),
    ("anatomy", "lungs"),
    ("physiology", "lungs"),
    ("a&p", "lungs"),
    ("a and p", "lungs"),
    ("med-surg", "stethoscope"),
    ("med surg", "stethoscope"),
    ("medical-surgical", "stethoscope"),
    ("surgical", "stethoscope"),
    ("community", "clipboard"),
    ("public health", "clipboard"),
)

_MOTIF_FALLBACKS = (
    "book",
    "stethoscope",
    "brain",
    "heart",
    "clipboard",
    "microscope",
)


def motif_for_title(title: str) -> str:
    """Map a catalog title to a decorative icon name. Presentation only."""
    text = (title or "").casefold()
    for needle, motif in _MOTIF_RULES:
        if needle in text:
            return motif
    if not title:
        return "book"
    return _MOTIF_FALLBACKS[sum(ord(ch) for ch in title) % len(_MOTIF_FALLBACKS)]


@dataclass(frozen=True)
class CatalogCard:
    title: str
    summary: str
    parent_title: str = ""
    motif: str = "book"


@dataclass(frozen=True)
class LandingPresentation:
    courses: tuple[CatalogCard, ...]
    subjects: tuple[CatalogCard, ...]
    premium_plan: PlanDefinition


class LandingPresentationService:
    """Assemble public marketing teasers from published catalog + plan catalog."""

    @classmethod
    def build(cls, *, locale: str = LocaleCode.EN) -> LandingPresentation:
        courses: list[CatalogCard] = []
        subjects: list[CatalogCard] = []
        for course in LearningCatalogService.list_courses():
            course_title = LearningCatalogService.title_for(course, locale)
            courses.append(
                CatalogCard(
                    title=course_title,
                    summary=LearningCatalogService.summary_for(course, locale),
                    motif=motif_for_title(course_title),
                )
            )
            for subject in LearningCatalogService.published_children(
                course, Subject, "course"
            ):
                subject_title = LearningCatalogService.title_for(subject, locale)
                subjects.append(
                    CatalogCard(
                        title=subject_title,
                        summary=LearningCatalogService.summary_for(subject, locale),
                        parent_title=course_title,
                        motif=motif_for_title(subject_title),
                    )
                )
        return LandingPresentation(
            courses=tuple(courses),
            subjects=tuple(subjects),
            premium_plan=PlanCatalog.default_plan(),
        )
