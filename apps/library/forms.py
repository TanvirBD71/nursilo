"""Library forms — presentation only; services own rules."""
from django import forms


class LibraryCatalogFilterForm(forms.Form):
    q = forms.CharField(required=False, max_length=200, label="Search")
    category = forms.CharField(required=False, max_length=128, label="Category")
    access = forms.ChoiceField(
        required=False,
        choices=(
            ("all", "All"),
            ("free", "Free"),
            ("premium", "Premium"),
        ),
        initial="all",
        label="Access",
    )
    page = forms.IntegerField(required=False, min_value=1, initial=1)


class LibraryBookmarkForm(forms.Form):
    """CSRF-bound bookmark toggle; action decided server-side."""

    next = forms.CharField(required=False, max_length=512)
