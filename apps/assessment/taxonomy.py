"""
Content taxonomy for the question bank (UNIT-12).

Deliberately separate from the BNMC exam blueprint. Subjects and cross-cutting
topics are a classification aid for staff review — they never replace, fill, or
invent blueprint competencies.
"""
from __future__ import annotations

CONTENT_SUBJECTS: tuple[str, ...] = (
    "Fundamentals of Nursing",
    "Anatomy and Physiology",
    "Medical-Surgical Nursing",
    "Community Health Nursing",
    "Nutrition and Dietetics",
    "Midwifery and Obstetrical Nursing",
    "Reproductive Health",
    "Newborn and Pediatric Nursing",
    "Traumatology and Orthopedic Nursing",
    "Psychiatric and Mental Health Nursing",
    "Gerontological Nursing",
    "Pharmacology for Nurses",
    "Microbiology",
    "Nursing Administration and Management",
    "Research in Nursing and Evidence-Based Nursing",
)

CROSS_CUTTING_TOPICS: tuple[str, ...] = (
    "Endocrine System and Hormones",
    "Nutrition and Vitamins",
    "Blood and Circulatory System",
    "Primary, Secondary and Tertiary Prevention",
    "CSF",
    "HIV/AIDS",
    "Burns",
    "Growth and Development",
    "Cancer and Tumors",
    "Cell and Plasma Membrane",
    "Human Heart",
    "Liver",
    "Epidemiology and Disease",
    "Arterial Pulse Points",
    "Important Health Days",
    "Meaning of Disease and Infection",
)

_SUBJECT_INDEX = {name.casefold(): name for name in CONTENT_SUBJECTS}
_TOPIC_INDEX = {name.casefold(): name for name in CROSS_CUTTING_TOPICS}


def canonicalize_subject(raw: str) -> tuple[str, bool]:
    """
    Return (value, known).

    Known names are canonicalized. Unknown supplied values are preserved exactly
    (source wording) and reported as not-in-taxonomy so callers can flag review.
    Empty input is unknown.
    """
    text = (raw or "").strip()
    if not text:
        return "", False
    known = _SUBJECT_INDEX.get(text.casefold())
    if known:
        return known, True
    return text, False


def canonicalize_topic(raw: str) -> tuple[str, bool]:
    text = (raw or "").strip()
    if not text:
        return "", False
    known = _TOPIC_INDEX.get(text.casefold())
    if known:
        return known, True
    return text, False


def subject_choices():
    return [("", "Unclassified")] + [(name, name) for name in CONTENT_SUBJECTS]


def topic_choices():
    return [("", "Unclassified")] + [(name, name) for name in CROSS_CUTTING_TOPICS]
