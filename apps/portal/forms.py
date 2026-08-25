"""Student profile forms — validation only; AccountService owns persistence (docs/19)."""
from __future__ import annotations

from django import forms

from apps.accounts.forms import LearnerProfileFieldsMixin
from apps.common.choices import LocaleCode


class ProfileEditForm(LearnerProfileFieldsMixin, forms.Form):
    full_name = forms.CharField(
        label="Full name",
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={"autocomplete": "name"}),
    )
    ui_locale = forms.ChoiceField(
        label="Interface language",
        choices=LocaleCode.choices,
    )

    def __init__(self, *args, include_learner_profile=True, **kwargs):
        super().__init__(*args, **kwargs)
        if include_learner_profile:
            self._add_learner_profile_fields(required=True)
            self.order_fields(
                [
                    "full_name",
                    "ui_locale",
                    "mobile_number",
                    "blood_group",
                    "academic_session",
                    "address",
                    "social_profile_url",
                    "linkedin_url",
                ]
            )

    def clean_full_name(self):
        return (self.cleaned_data.get("full_name") or "").strip()


class AcademicProfileForm(forms.Form):
    academic_program = forms.CharField(
        label="Academic program",
        required=False,
        widget=forms.Textarea(attrs={"rows": 2}),
    )
    institution = forms.CharField(
        label="Institution",
        required=False,
        widget=forms.Textarea(attrs={"rows": 2}),
    )
    current_semester_year = forms.CharField(
        label="Current semester / year",
        required=False,
        widget=forms.Textarea(attrs={"rows": 2}),
    )
    expected_graduation_year = forms.IntegerField(
        label="Expected graduation year",
        required=False,
        min_value=1990,
        max_value=2100,
    )
    current_study_goal = forms.CharField(
        label="Current study goal",
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
    )

    def clean_academic_program(self):
        return (self.cleaned_data.get("academic_program") or "").strip()

    def clean_institution(self):
        return (self.cleaned_data.get("institution") or "").strip()

    def clean_current_semester_year(self):
        return (self.cleaned_data.get("current_semester_year") or "").strip()

    def clean_current_study_goal(self):
        value = self.cleaned_data.get("current_study_goal")
        if value is None:
            return None
        value = value.strip()
        return value or None
