"""Learner profile value objects and validation (registration + profile edit)."""
from __future__ import annotations

import re
from urllib.parse import urlparse

from django.core.exceptions import ValidationError
from django.db import models


class BloodGroup(models.TextChoices):
    A_POS = "A+", "A+"
    A_NEG = "A-", "A-"
    B_POS = "B+", "B+"
    B_NEG = "B-", "B-"
    AB_POS = "AB+", "AB+"
    AB_NEG = "AB-", "AB-"
    O_POS = "O+", "O+"
    O_NEG = "O-", "O-"


# Inclusive start year; bump ACADEMIC_SESSION_END_YEAR to offer newer sessions.
ACADEMIC_SESSION_START_YEAR = 2015
ACADEMIC_SESSION_END_YEAR = 2029


def academic_session_choices() -> list[tuple[str, str]]:
    """Controlled academic sessions (YYYY-YYYY). Future years are one-constant away."""
    pairs = []
    for year in range(ACADEMIC_SESSION_START_YEAR, ACADEMIC_SESSION_END_YEAR):
        label = f"{year}-{year + 1}"
        pairs.append((label, label))
    return pairs


ACADEMIC_SESSION_VALUES = {value for value, _label in academic_session_choices()}

_BD_LOCAL = re.compile(r"^01[3-9]\d{8}$")
_BD_COUNTRY = re.compile(r"^(?:\+?880)1[3-9]\d{8}$")
_E164 = re.compile(r"^\+[1-9]\d{7,14}$")
_ALLOWED_URL_SCHEMES = {"http", "https"}


def normalize_mobile_number(value: str) -> str:
    """
    Bangladesh-friendly mobile normalization.

    Accepts 01XXXXXXXXX, 8801XXXXXXXXX, +8801XXXXXXXXX, and legitimate
    international E.164 numbers. Does not invent a country code.
    """
    raw = (value or "").strip()
    if not raw:
        raise ValidationError("Enter a mobile number.", code="required")

    compact = re.sub(r"[\s\-().]", "", raw)
    if compact.startswith("00"):
        compact = "+" + compact[2:]

    digits_only = compact[1:] if compact.startswith("+") else compact
    if not digits_only.isdigit():
        raise ValidationError("Enter a valid mobile number.", code="invalid")

    if _BD_LOCAL.match(compact):
        return "+880" + compact[1:]
    if compact.startswith("880") and _BD_COUNTRY.match(compact):
        return "+" + compact
    if compact.startswith("+880") and _BD_COUNTRY.match(compact):
        return compact
    if _E164.match(compact):
        return compact

    raise ValidationError(
        "Enter a valid mobile number (Bangladesh 01XXXXXXXXX or international +country code).",
        code="invalid",
    )


def validate_academic_session(value: str) -> str:
    session = (value or "").strip()
    if not session:
        raise ValidationError("Select an academic session.", code="required")
    if session not in ACADEMIC_SESSION_VALUES:
        raise ValidationError("Select a valid academic session.", code="invalid")
    return session


def validate_blood_group(value: str) -> str:
    group = (value or "").strip()
    if not group:
        raise ValidationError("Select a blood group.", code="required")
    if group not in BloodGroup.values:
        raise ValidationError("Select a valid blood group.", code="invalid")
    return group


def validate_optional_profile_url(value: str, *, field_label: str = "URL") -> str:
    raw = (value or "").strip()
    if not raw:
        return ""
    parsed = urlparse(raw)
    if parsed.scheme.lower() not in _ALLOWED_URL_SCHEMES or not parsed.netloc:
        raise ValidationError(
            f"Enter a valid {field_label} starting with https:// or http://.",
            code="invalid",
        )
    return raw
