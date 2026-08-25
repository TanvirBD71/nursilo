"""Learning interaction forms — server-posted completion baseline (docs/19)."""
from django import forms


class LessonCompleteForm(forms.Form):
    """CSRF-backed completion post; lesson identity comes from the URL."""

    confirm = forms.BooleanField(required=False, initial=True)
