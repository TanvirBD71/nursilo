"""March 2025 bank protection — no auto-classify or bulk publish of the imported 51."""
from __future__ import annotations

MARCH_2025_CODE_PREFIX = "BNMC-2025-03-"
MARCH_2025_BULK_REASON = (
    "March 2025 protected: not eligible for bulk classify/publish/workflow."
)


def is_march_2025_protected(question) -> bool:
    code = (getattr(question, "question_code", None) or "").strip()
    return code.startswith(MARCH_2025_CODE_PREFIX)
