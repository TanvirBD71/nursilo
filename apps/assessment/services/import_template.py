"""
Staff Excel template for question import (UNIT-12).

Contains one synthetic TRUE/FALSE row and one synthetic BEST_ANSWER row that
demonstrate the UNIT-11 column contract. Never includes real exam questions.
"""
from __future__ import annotations

import io

from apps.assessment.services.import_questions import REQUIRED_COLUMNS, OPTIONAL_COLUMNS

TEMPLATE_FILENAME = "nursilo-question-import-template.xlsx"
AUTHOR_TEMPLATE_FILENAME = "nursilo-question-import-template-author.xlsx"

_EXAMPLE_TF = {
    "question_code": "EXAMPLE-TF-001",
    "question_type": "TRUE/FALSE",
    "question_text": "EXAMPLE ONLY — not a real exam item. Mark each statement True or False.",
    "scenario": "",
    "option_a": "Example statement A (synthetic).",
    "option_b": "Example statement B (synthetic).",
    "option_c": "Example statement C (synthetic).",
    "option_d": "Example statement D (synthetic).",
    "option_e": "Example statement E (synthetic).",
    "correct_answer": "A=TRUE,B=FALSE,C=TRUE,D=FALSE,E=TRUE",
    "explanation": "Example rationale for staff training — not a licensing key.",
    "blueprint_category": "Nursing Process",
    "blueprint_competency": "C1",
    "subject": "Fundamentals of Nursing",
    "topic": "Growth and Development",
    "cognitive_level": "recall",
    "difficulty": "easy",
    "scenario_based": "false",
    "source_name": "Nursilo example template",
    "source_page": "",
    "source_reference": "EXAMPLE-TF-001",
    "status": "draft",
    "source_type": "imported",
    "needs_review": "false",
}

_EXAMPLE_BA = {
    "question_code": "EXAMPLE-BA-001",
    "question_type": "BEST_ANSWER",
    "question_text": "EXAMPLE ONLY — not a real exam item. Choose the single best answer.",
    "scenario": "A staff-training scenario about a simulated adult inpatient.",
    "option_a": "Example option A (synthetic).",
    "option_b": "Example option B (synthetic).",
    "option_c": "Example option C (synthetic).",
    "option_d": "Example option D (synthetic).",
    "option_e": "",
    "correct_answer": "B",
    "explanation": "Example rationale for staff training — not a licensing key.",
    "blueprint_category": "Fundamentals of Nursing",
    "blueprint_competency": "C11",
    "subject": "Pharmacology for Nurses",
    "topic": "",
    "cognitive_level": "understanding",
    "difficulty": "medium",
    "scenario_based": "true",
    "source_name": "Nursilo example template",
    "source_page": "",
    "source_reference": "EXAMPLE-BA-001",
    "status": "draft",
    "source_type": "imported",
    "needs_review": "false",
}

TEMPLATE_COLUMNS = list(REQUIRED_COLUMNS) + [
    c for c in OPTIONAL_COLUMNS if c not in REQUIRED_COLUMNS
]


def build_example_workbook() -> bytes:
    """Return .xlsx bytes for the staff import template (synthetic rows only)."""
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = "questions"
    ws.append(TEMPLATE_COLUMNS)
    for row in (_EXAMPLE_TF, _EXAMPLE_BA):
        ws.append([row.get(col, "") for col in TEMPLATE_COLUMNS])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


_USER_ENTERED = {
    "question_code",
    "question_type",
    "question_text",
    "scenario",
    "option_a",
    "option_b",
    "option_c",
    "option_d",
    "option_e",
    "correct_answer",
    "explanation",
    "subject",
    "topic",
    "scenario_based",
    "source_name",
    "source_page",
    "source_reference",
    "statement_a",
    "statement_b",
    "statement_c",
    "statement_d",
    "statement_e",
    "truth_a",
    "truth_b",
    "truth_c",
    "truth_d",
    "truth_e",
    "correct_option",
    "content_subject",
    "content_topic",
}

_SYSTEM_MANAGED = {
    "status",
    "source_type",
    "needs_review",
}

_OPTIONAL_CLASSIFICATION = {
    "blueprint_category",
    "blueprint_competency",
    "cognitive_level",
    "difficulty",
}

_AUTHOR_TF = {
    **_EXAMPLE_TF,
    "status": "",
    "source_type": "",
    "needs_review": "",
    "blueprint_category": "",
    "blueprint_competency": "",
    "cognitive_level": "",
    "difficulty": "",
}

_AUTHOR_BA = {
    **_EXAMPLE_BA,
    "status": "",
    "source_type": "",
    "needs_review": "",
    "blueprint_category": "",
    "blueprint_competency": "",
    "cognitive_level": "",
    "difficulty": "",
}


def _column_role(name: str) -> str:
    if name in _SYSTEM_MANAGED:
        return "system-managed (leave blank unless you must override)"
    if name in _OPTIONAL_CLASSIFICATION:
        return "optional classification (can also be set in the staff UI)"
    if name in _USER_ENTERED:
        return "user-entered"
    return "optional alias"


def build_author_workbook() -> bytes:
    """
    Author-friendly workbook. The questions sheet still uses the original
    UNIT-11/12 column contract so existing importers accept it.
    """
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = "questions"
    ws.append(TEMPLATE_COLUMNS)
    for row in (_AUTHOR_TF, _AUTHOR_BA):
        ws.append([row.get(col, "") for col in TEMPLATE_COLUMNS])

    guide = wb.create_sheet("column_guide")
    guide.append(["column", "role", "notes"])
    notes = {
        "question_code": "Stable idempotency key. Required. Re-importing the same code skips.",
        "question_type": "TRUE/FALSE or BEST_ANSWER (aliases accepted).",
        "correct_answer": "TF: A=TRUE,B=FALSE,...  BA: a single letter, or use correct_option.",
        "option_e": "Required column; leave blank for BEST_ANSWER.",
        "status": "Defaults to draft when blank. Do not publish from the workbook.",
        "needs_review": "Server may flag review when mapping is uncertain.",
        "blueprint_category": "Optional. Uncertain mapping stays unclassified for admin review.",
        "statement_a": "Optional TF alias for option_a.",
        "truth_a": "Optional TF alias; combined into correct_answer.",
        "correct_option": "Optional BA alias for correct_answer.",
    }
    for col in TEMPLATE_COLUMNS:
        guide.append([col, _column_role(col), notes.get(col, "")])

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
