"""Staff console forms — validation only; services own authorization."""
from django import forms

from apps.common.choices import (
    AttemptMode,
    BookFormat,
    CognitiveLevel,
    ContactMessageStatus,
    DifficultyLevel,
    LocaleCode,
    QuestionErrorReportStatus,
    QuestionSourceType,
    QuestionType,
    RoleCode,
)


class UserCreateForm(forms.Form):
    email = forms.EmailField()
    full_name = forms.CharField(max_length=255, required=False)
    password = forms.CharField(widget=forms.PasswordInput, min_length=8)
    role_code = forms.ChoiceField(choices=[])

    def __init__(self, *args, role_choices=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["role_code"].choices = role_choices or [
            (RoleCode.STUDENT, "Student")
        ]


class UserEditForm(forms.Form):
    full_name = forms.CharField(max_length=255, required=False)
    is_active = forms.BooleanField(required=False)
    roles = forms.MultipleChoiceField(required=False, widget=forms.CheckboxSelectMultiple)

    def __init__(self, *args, role_choices=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["roles"].choices = role_choices or []


class LearningNodeForm(forms.Form):
    title_en = forms.CharField(max_length=255)
    title_bn = forms.CharField(max_length=255, required=False)
    summary = forms.CharField(widget=forms.Textarea, required=False)
    sort_order = forms.IntegerField(min_value=0, initial=0, required=False)
    parent_id = forms.UUIDField(required=False)
    is_premium = forms.BooleanField(required=False)


class QuestionCreateForm(forms.Form):
    stem = forms.CharField(widget=forms.Textarea)
    explanation = forms.CharField(widget=forms.Textarea, required=False)
    question_type = forms.ChoiceField(choices=QuestionType.choices, initial=QuestionType.MCQ)
    difficulty = forms.ChoiceField(
        choices=[("", "Unclassified")] + list(DifficultyLevel.choices),
        required=False,
        initial=DifficultyLevel.MEDIUM,
    )
    locale = forms.ChoiceField(choices=LocaleCode.choices, initial=LocaleCode.EN)
    topic_id = forms.UUIDField(required=False)
    option_a = forms.CharField(max_length=500)
    option_b = forms.CharField(max_length=500)
    option_c = forms.CharField(max_length=500, required=False)
    option_d = forms.CharField(max_length=500, required=False)
    correct_key = forms.ChoiceField(
        choices=[("A", "A"), ("B", "B"), ("C", "C"), ("D", "D")],
        initial="A",
    )
    # UNIT-11 metadata (all optional; classification gaps flag review).
    question_code = forms.CharField(max_length=64, required=False)
    cognitive_level = forms.ChoiceField(
        choices=[("", "Unclassified")] + list(CognitiveLevel.choices),
        required=False,
    )
    blueprint_category_id = forms.UUIDField(required=False)
    blueprint_competency_id = forms.UUIDField(required=False)
    subject = forms.CharField(max_length=255, required=False)
    topic = forms.CharField(max_length=255, required=False)
    scenario = forms.CharField(widget=forms.Textarea, required=False)
    scenario_based = forms.BooleanField(required=False)
    # Provenance (ADMIN-ONLY — never surfaced to students).
    source_type = forms.ChoiceField(
        choices=QuestionSourceType.choices,
        required=False,
        initial=QuestionSourceType.STAFF_CREATED,
    )
    source_name = forms.CharField(max_length=255, required=False)
    source_page = forms.CharField(max_length=64, required=False)
    source_reference = forms.CharField(max_length=255, required=False)


class QuestionImportForm(forms.Form):
    """Upload an .xlsx question workbook for preview/import (bulk foundation)."""

    file = forms.FileField(label="Question workbook (.xlsx)", required=False)
    confirm = forms.BooleanField(required=False)


class QuestionClassificationForm(forms.Form):
    """Staff classification / taxonomy edit (does not change scored wording)."""

    content_subject = forms.CharField(max_length=255, required=False)
    content_topic = forms.CharField(max_length=255, required=False)
    cognitive_level = forms.ChoiceField(
        choices=[("", "Unclassified")] + list(CognitiveLevel.choices),
        required=False,
    )
    difficulty = forms.ChoiceField(
        choices=[("", "Unclassified")] + list(DifficultyLevel.choices),
        required=False,
    )
    blueprint_category_id = forms.UUIDField(required=False)
    blueprint_competency_id = forms.UUIDField(required=False)
    scenario_based = forms.BooleanField(required=False)
    needs_review = forms.BooleanField(required=False)


class QuestionReviewForm(forms.Form):
    needs_review = forms.BooleanField(required=False)


class ExamForm(forms.Form):
    code = forms.SlugField(max_length=64, required=False)
    title_key = forms.CharField(max_length=128)
    mode = forms.ChoiceField(choices=AttemptMode.choices, initial=AttemptMode.MOCK)
    time_limit_seconds = forms.IntegerField(min_value=1, required=False)
    is_premium = forms.BooleanField(required=False)
    track_code = forms.CharField(max_length=64, required=False)
    question_id = forms.UUIDField(required=False)


class BookForm(forms.Form):
    title_en = forms.CharField(max_length=255)
    title_bn = forms.CharField(max_length=255, required=False)
    blurb = forms.CharField(widget=forms.Textarea, required=False)
    author_name = forms.CharField(max_length=255, required=False)
    category = forms.CharField(max_length=128, required=False)
    is_premium = forms.BooleanField(required=False)
    cover_storage_key = forms.CharField(max_length=512, required=False)
    asset_format = forms.ChoiceField(choices=BookFormat.choices, required=False)
    asset_storage_key = forms.CharField(max_length=512, required=False)


class CmsForm(forms.Form):
    code = forms.SlugField(max_length=64)
    title = forms.CharField(max_length=255)
    body = forms.CharField(widget=forms.Textarea, required=False)
    meta_title = forms.CharField(max_length=255, required=False)
    meta_description = forms.CharField(widget=forms.Textarea, required=False)


class AnnouncementForm(forms.Form):
    code = forms.SlugField(max_length=64)
    title = forms.CharField(max_length=255)
    body = forms.CharField(widget=forms.Textarea)


class WorkflowForm(forms.Form):
    action = forms.ChoiceField(
        choices=[
            ("submit_review", "Submit for review"),
            ("approve", "Approve"),
            ("reject", "Reject / return"),
            ("publish", "Publish"),
            ("archive", "Archive"),
            ("restore", "Restore"),
        ]
    )
    notes = forms.CharField(required=False, widget=forms.Textarea)


class ContactStatusForm(forms.Form):
    status = forms.ChoiceField(choices=ContactMessageStatus.choices)


class ErrorReportForm(forms.Form):
    status = forms.ChoiceField(
        choices=[
            (QuestionErrorReportStatus.TRIAGED, "Triaged"),
            (QuestionErrorReportStatus.RESOLVED, "Resolved"),
            (QuestionErrorReportStatus.DISMISSED, "Dismissed"),
        ]
    )
    notes = forms.CharField(required=False, widget=forms.Textarea)


class ManualGrantForm(forms.Form):
    user_id = forms.UUIDField()
    notes = forms.CharField(required=False, widget=forms.Textarea)


class SearchFilterForm(forms.Form):
    q = forms.CharField(required=False)
    state = forms.CharField(required=False)
