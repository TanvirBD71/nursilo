"""Authentication forms — validation only; business rules live in services (docs/19)."""
from __future__ import annotations

from django import forms
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from apps.accounts.profile import (
    BloodGroup,
    academic_session_choices,
    normalize_mobile_number,
    validate_academic_session,
    validate_blood_group,
    validate_optional_profile_url,
)


class LearnerProfileFieldsMixin:
    """Shared registration/profile fields — one validation path, no duplicate logic."""

    def _add_learner_profile_fields(self, *, required: bool) -> None:
        self.fields["mobile_number"] = forms.CharField(
            label="Mobile number",
            max_length=32,
            required=required,
            widget=forms.TextInput(
                attrs={
                    "autocomplete": "tel",
                    "inputmode": "tel",
                    "placeholder": "01XXXXXXXXX",
                }
            ),
        )
        self.fields["academic_session"] = forms.ChoiceField(
            label="Academic session",
            choices=[("", "Select session")] + academic_session_choices(),
            required=required,
        )
        self.fields["blood_group"] = forms.ChoiceField(
            label="Blood group",
            choices=[("", "Select blood group")] + list(BloodGroup.choices),
            required=required,
        )
        self.fields["address"] = forms.CharField(
            label="Address",
            required=False,
            widget=forms.Textarea(
                attrs={"rows": 3, "autocomplete": "street-address"}
            ),
        )
        self.fields["social_profile_url"] = forms.CharField(
            label="Social media profile link",
            required=False,
            widget=forms.URLInput(
                attrs={"placeholder": "https://", "autocomplete": "url"}
            ),
        )
        self.fields["linkedin_url"] = forms.CharField(
            label="LinkedIn profile link",
            required=False,
            widget=forms.URLInput(
                attrs={
                    "placeholder": "https://www.linkedin.com/in/…",
                    "autocomplete": "url",
                }
            ),
        )

    def clean_mobile_number(self):
        value = (self.cleaned_data.get("mobile_number") or "").strip()
        if not value:
            if self.fields["mobile_number"].required:
                raise ValidationError("Enter a mobile number.")
            return ""
        return normalize_mobile_number(value)

    def clean_academic_session(self):
        value = (self.cleaned_data.get("academic_session") or "").strip()
        if not value:
            if self.fields["academic_session"].required:
                raise ValidationError("Select an academic session.")
            return ""
        return validate_academic_session(value)

    def clean_blood_group(self):
        value = (self.cleaned_data.get("blood_group") or "").strip()
        if not value:
            if self.fields["blood_group"].required:
                raise ValidationError("Select a blood group.")
            return ""
        return validate_blood_group(value)

    def clean_address(self):
        return (self.cleaned_data.get("address") or "").strip()

    def clean_social_profile_url(self):
        return validate_optional_profile_url(
            self.cleaned_data.get("social_profile_url") or "",
            field_label="social media profile link",
        )

    def clean_linkedin_url(self):
        return validate_optional_profile_url(
            self.cleaned_data.get("linkedin_url") or "",
            field_label="LinkedIn profile link",
        )


class RegisterForm(LearnerProfileFieldsMixin, forms.Form):
    email = forms.EmailField(
        label="Email",
        max_length=254,
        widget=forms.EmailInput(attrs={"autocomplete": "email"}),
    )
    full_name = forms.CharField(
        label="Full name",
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={"autocomplete": "name"}),
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        strip=False,
    )
    password_confirm = forms.CharField(
        label="Confirm password",
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        strip=False,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._add_learner_profile_fields(required=True)
        # Keep account fields first, then personal / academic / contact.
        self.order_fields(
            [
                "full_name",
                "email",
                "password",
                "password_confirm",
                "mobile_number",
                "blood_group",
                "academic_session",
                "address",
                "social_profile_url",
                "linkedin_url",
            ]
        )

    def clean_email(self):
        return (self.cleaned_data["email"] or "").strip().lower()

    def clean_full_name(self):
        return (self.cleaned_data.get("full_name") or "").strip()

    def clean(self):
        cleaned = super().clean()
        password = cleaned.get("password")
        confirm = cleaned.get("password_confirm")
        if password and confirm and password != confirm:
            self.add_error("password_confirm", "Passwords do not match.")
        if password:
            try:
                validate_password(password)
            except ValidationError as exc:
                self.add_error("password", exc)
        return cleaned


class LoginForm(forms.Form):
    email = forms.EmailField(
        label="Email",
        max_length=254,
        widget=forms.EmailInput(attrs={"autocomplete": "username"}),
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
        strip=False,
    )
    remember_me = forms.BooleanField(
        label="Remember me on this browser",
        required=False,
        widget=forms.CheckboxInput(attrs={"autocomplete": "off"}),
    )
    next = forms.CharField(required=False, widget=forms.HiddenInput)

    def clean_email(self):
        return (self.cleaned_data["email"] or "").strip().lower()


class PasswordChangeForm(forms.Form):
    current_password = forms.CharField(
        label="Current password", widget=forms.PasswordInput, strip=False
    )
    new_password = forms.CharField(
        label="New password", widget=forms.PasswordInput, strip=False
    )
    new_password_confirm = forms.CharField(
        label="Confirm new password", widget=forms.PasswordInput, strip=False
    )

    def clean(self):
        cleaned = super().clean()
        new_password = cleaned.get("new_password")
        confirm = cleaned.get("new_password_confirm")
        if new_password and confirm and new_password != confirm:
            self.add_error("new_password_confirm", "Passwords do not match.")
        if new_password:
            try:
                validate_password(new_password)
            except ValidationError as exc:
                self.add_error("new_password", exc)
        return cleaned


class PasswordResetRequestForm(forms.Form):
    email = forms.EmailField(label="Email", max_length=254)

    def clean_email(self):
        return (self.cleaned_data["email"] or "").strip().lower()


class PasswordResetConfirmForm(forms.Form):
    token = forms.CharField(label="Reset token", max_length=128)
    new_password = forms.CharField(
        label="New password", widget=forms.PasswordInput, strip=False
    )
    new_password_confirm = forms.CharField(
        label="Confirm new password", widget=forms.PasswordInput, strip=False
    )

    def clean(self):
        cleaned = super().clean()
        new_password = cleaned.get("new_password")
        confirm = cleaned.get("new_password_confirm")
        if new_password and confirm and new_password != confirm:
            self.add_error("new_password_confirm", "Passwords do not match.")
        if new_password:
            try:
                validate_password(new_password)
            except ValidationError as exc:
                self.add_error("new_password", exc)
        return cleaned


class EmailVerificationForm(forms.Form):
    token = forms.CharField(label="Verification token", max_length=128)


class ResendVerificationForm(forms.Form):
    email = forms.EmailField(label="Email", max_length=254)

    def clean_email(self):
        return (self.cleaned_data["email"] or "").strip().lower()


class ReauthForm(forms.Form):
    password = forms.CharField(label="Password", widget=forms.PasswordInput, strip=False)
    next = forms.CharField(required=False, widget=forms.HiddenInput)


class LogoutAllForm(forms.Form):
    password = forms.CharField(label="Password", widget=forms.PasswordInput, strip=False)


class LogoutOthersForm(forms.Form):
    password = forms.CharField(label="Password", widget=forms.PasswordInput, strip=False)
