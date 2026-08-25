"""Practice interaction forms — server validation baseline (docs/19)."""
from django import forms

from apps.assessment.services.pool import (
    ALLOWED_DIFFICULTIES,
    DEFAULT_QUESTION_COUNT,
    MAX_QUESTION_COUNT,
    MIN_QUESTION_COUNT,
)
from apps.common.choices import DifficultyLevel


SCOPE_CHOICES = (
    ("topic", "Topic"),
    ("chapter", "Chapter"),
    ("unit", "Unit"),
    ("subject", "Subject"),
    ("course", "Course"),
    ("random", "Random"),
)


class PracticeSetupForm(forms.Form):
    scope_type = forms.ChoiceField(
        choices=SCOPE_CHOICES,
        label="Practice scope",
    )
    scope_id = forms.UUIDField(
        required=False,
        label="Scope item",
        help_text="Required unless scope is Random.",
    )
    difficulty = forms.ChoiceField(
        choices=[("", "Any difficulty")]
        + [(d.value, d.label) for d in DifficultyLevel if d.value in ALLOWED_DIFFICULTIES],
        required=False,
        label="Difficulty",
    )
    count = forms.IntegerField(
        min_value=MIN_QUESTION_COUNT,
        max_value=MAX_QUESTION_COUNT,
        initial=DEFAULT_QUESTION_COUNT,
        label="Number of questions",
    )


class PracticeAnswerForm(forms.Form):
    """Option key for the current attempt item; empty clears the answer."""

    option_key = forms.CharField(required=False, max_length=16, label="Answer")


class PracticeSubmitForm(forms.Form):
    confirm = forms.BooleanField(required=False, initial=True)


class ExamStartForm(forms.Form):
    """Confirm starting or resuming a formal exam (docs/19)."""

    confirm = forms.BooleanField(required=False, initial=True)


class ExamAnswerForm(forms.Form):
    option_key = forms.CharField(required=False, max_length=16, label="Answer")


class ExamSubmitForm(forms.Form):
    confirm = forms.BooleanField(required=False, initial=True)
