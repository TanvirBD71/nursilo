"""Thin staff console views — services own authZ and mutations (docs/03, docs/24)."""
from __future__ import annotations

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods, require_POST

from apps.cms.services import EditorialWorkflowError, EditorialWorkflowService
from apps.common.choices import ClassificationOrigin, EditorialState, QuestionSourceType
from apps.rbac.services import AccessControlService
from apps.staff.access import (
    any_permission_required,
    permission_required,
    staff_console_required,
)
from apps.staff.forms import (
    AnnouncementForm,
    BookForm,
    CmsForm,
    ContactStatusForm,
    ErrorReportForm,
    ExamForm,
    LearningNodeForm,
    ManualGrantForm,
    QuestionClassificationForm,
    QuestionCreateForm,
    QuestionImportForm,
    QuestionReviewForm,
    UserCreateForm,
    UserEditForm,
    WorkflowForm,
)
from apps.staff.services import (
    AnnouncementStaffService,
    AuditStaffService,
    BillingStaffService,
    BlueprintStaffService,
    CmsStaffService,
    ExamStaffService,
    LearningStaffService,
    LibraryStaffService,
    QuestionStaffService,
    StaffDashboardService,
    StaffNavigationService,
    UserStaffService,
)
from apps.staff.services.blueprint import BlueprintStaffError
from apps.staff.services.announcements import AnnouncementStaffError
from apps.staff.services.billing import BillingStaffError
from apps.staff.services.cms_pages import CmsStaffError
from apps.staff.services.exams import ExamStaffError
from apps.staff.services.learning import LearningStaffError
from apps.staff.services.library import LibraryStaffError
from apps.staff.services.questions import QuestionStaffError
from apps.staff.services.users import UserStaffError


def _staff_context(request, *, active: str, extra=None) -> dict:
    context = {
        "nav_items": StaffNavigationService.items(request.user, active=active),
        "nav_active": active,
        "layout_family": "staff",
        "page_heading": active.replace("_", " ").title(),
    }
    if extra:
        context.update(extra)
    return context


def _handle_perm(exc, request):
    if isinstance(exc, PermissionError):
        raise PermissionDenied(str(exc)) from exc
    raise exc


def _question_list_filters(request):
    needs_review_param = request.GET.get("needs_review", "")
    needs_review = True if needs_review_param in {"1", "true", "on"} else None
    scenario_param = request.GET.get("scenario_based", "")
    scenario_based = True if scenario_param in {"1", "true", "on"} else None
    params = request.GET.copy()
    params.pop("page", None)
    return {
        "q": request.GET.get("q", ""),
        "state": request.GET.get("state", ""),
        "question_type": request.GET.get("question_type", ""),
        "cognitive": request.GET.get("cognitive", ""),
        "blueprint_category": request.GET.get("blueprint_category", ""),
        "blueprint_competency": request.GET.get("blueprint_competency", ""),
        "subject": request.GET.get("subject", ""),
        "topic": request.GET.get("topic", ""),
        "scenario_based": scenario_based,
        "needs_review": needs_review,
        "source_type": request.GET.get("source_type", ""),
        "source_name": request.GET.get("source_name", ""),
        "created_from": request.GET.get("created_from", ""),
        "created_to": request.GET.get("created_to", ""),
        "import_batch_id": request.GET.get("import_batch_id", ""),
        "difficulty": request.GET.get("difficulty", ""),
        "classification_origin": request.GET.get("classification_origin", ""),
        "needs_review_param": needs_review_param,
        "scenario_param": scenario_param,
        "querystring": params.urlencode(),
    }


def _flash_bulk_result(request, result):
    if result.failed == 0:
        messages.success(
            request,
            f"Bulk {result.action}: {result.succeeded} of {result.selected} succeeded.",
        )
    else:
        messages.warning(
            request,
            f"Bulk {result.action}: selected {result.selected}, "
            f"succeeded {result.succeeded}, failed {result.failed}.",
        )
    for failure in result.failures[:25]:
        label = failure.question_code or failure.question_id
        messages.error(request, f"{label}: {failure.reason}")
    if result.failed > 25:
        messages.error(request, f"{result.failed - 25} additional failure(s) omitted.")


@staff_console_required
@require_http_methods(["GET"])
def dashboard(request):
    data = StaffDashboardService.build(request.user)
    return render(
        request,
        "staff/dashboard.html",
        _staff_context(
            request,
            active="dashboard",
            extra={"dashboard": data, "page_heading": "Staff dashboard"},
        ),
    )


# ----- Users -----


@permission_required("users.view")
@require_http_methods(["GET"])
def users_list(request):
    page_obj, rows = UserStaffService.list_users(
        request.user, q=request.GET.get("q", ""), page=request.GET.get("page")
    )
    return render(
        request,
        "staff/users/list.html",
        _staff_context(
            request,
            active="users",
            extra={
                "page_heading": "Users",
                "page_obj": page_obj,
                "rows": rows,
                "q": request.GET.get("q", ""),
            },
        ),
    )


@permission_required("users.create")
@require_http_methods(["GET", "POST"])
def users_create(request):
    choices = UserStaffService.assignable_roles_for(request.user)
    form = UserCreateForm(request.POST or None, role_choices=choices)
    if request.method == "POST" and form.is_valid():
        try:
            user = UserStaffService.create_user(
                actor=request.user,
                email=form.cleaned_data["email"],
                password=form.cleaned_data["password"],
                full_name=form.cleaned_data.get("full_name") or "",
                role_code=form.cleaned_data["role_code"],
            )
            messages.success(request, f"Created user {user.email}.")
            return redirect("staff:user_detail", user_id=user.id)
        except UserStaffError as exc:
            messages.error(request, str(exc))
        except PermissionError as exc:
            _handle_perm(exc, request)
    return render(
        request,
        "staff/users/form.html",
        _staff_context(
            request,
            active="users",
            extra={"page_heading": "Create user", "form": form},
        ),
    )


@permission_required("users.view")
@require_http_methods(["GET", "POST"])
def user_detail(request, user_id):
    try:
        user = UserStaffService.get_user(request.user, user_id)
    except UserStaffError:
        raise PermissionDenied("User not found.") from None
    choices = UserStaffService.assignable_roles_for(request.user)
    initial = {
        "full_name": user.full_name,
        "is_active": user.is_active,
        "roles": list(AccessControlService.role_codes_for(user)),
    }
    form = UserEditForm(
        request.POST or None, initial=initial, role_choices=choices
    )
    if request.method == "POST" and form.is_valid():
        try:
            UserStaffService.update_user(
                actor=request.user,
                user=user,
                full_name=form.cleaned_data.get("full_name") or "",
                is_active=bool(form.cleaned_data.get("is_active")),
            )
            UserStaffService.set_roles(
                actor=request.user,
                user=user,
                role_codes=form.cleaned_data.get("roles") or [],
            )
            messages.success(request, "User updated.")
            return redirect("staff:user_detail", user_id=user.id)
        except UserStaffError as exc:
            messages.error(request, str(exc))
        except PermissionError as exc:
            _handle_perm(exc, request)
    return render(
        request,
        "staff/users/detail.html",
        _staff_context(
            request,
            active="users",
            extra={"page_heading": user.email, "target_user": user, "form": form},
        ),
    )


# ----- Learning -----


@any_permission_required(
    "content.create_draft", "content.view_unpublished", "content.edit", "content.publish"
)
@require_http_methods(["GET"])
def learning_list(request):
    try:
        page_obj = LearningStaffService.list_courses(
            request.user,
            q=request.GET.get("q", ""),
            state=request.GET.get("state", ""),
            page=request.GET.get("page"),
        )
    except PermissionError as exc:
        _handle_perm(exc, request)
    return render(
        request,
        "staff/learning/list.html",
        _staff_context(
            request,
            active="learning",
            extra={
                "page_heading": "Learning content",
                "page_obj": page_obj,
                "q": request.GET.get("q", ""),
                "state": request.GET.get("state", ""),
                "states": EditorialState.choices,
                "title_for": LearningStaffService.title_for,
            },
        ),
    )


@any_permission_required("content.create_draft", "content.edit")
@require_http_methods(["GET", "POST"])
def learning_create(request, kind="course"):
    initial = {}
    if request.GET.get("parent"):
        initial["parent_id"] = request.GET.get("parent")
    form = LearningNodeForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        try:
            obj = LearningStaffService.create_node(
                actor=request.user,
                kind=kind,
                title_en=form.cleaned_data["title_en"],
                title_bn=form.cleaned_data.get("title_bn") or "",
                summary=form.cleaned_data.get("summary") or "",
                parent_id=form.cleaned_data.get("parent_id") or initial.get("parent_id"),
                sort_order=form.cleaned_data.get("sort_order") or 0,
                is_premium=bool(form.cleaned_data.get("is_premium")),
            )
            messages.success(request, "Content created as Draft.")
            return redirect("staff:learning_detail", kind=kind, node_id=obj.id)
        except (LearningStaffError, PermissionError) as exc:
            if isinstance(exc, PermissionError):
                _handle_perm(exc, request)
            messages.error(request, str(exc))
    return render(
        request,
        "staff/learning/form.html",
        _staff_context(
            request,
            active="learning",
            extra={"page_heading": f"Create {kind}", "form": form, "kind": kind},
        ),
    )


@any_permission_required(
    "content.create_draft", "content.view_unpublished", "content.edit", "content.publish"
)
@require_http_methods(["GET", "POST"])
def learning_detail(request, kind, node_id):
    try:
        obj = LearningStaffService.get_node(request.user, kind, node_id)
    except LearningStaffError:
        raise PermissionDenied("Not found.") from None
    workflow_form = WorkflowForm(request.POST if request.POST.get("workflow") else None)
    edit_form = LearningNodeForm(
        request.POST if request.POST.get("edit") else None,
        initial={
            "title_en": LearningStaffService.title_for(obj),
            "sort_order": obj.sort_order,
            "is_premium": getattr(obj, "is_premium", False),
        },
    )
    if request.method == "POST" and request.POST.get("workflow") and workflow_form.is_valid():
        try:
            LearningStaffService.workflow(
                actor=request.user,
                kind=kind,
                node_id=node_id,
                action=workflow_form.cleaned_data["action"],
                notes=workflow_form.cleaned_data.get("notes") or "",
            )
            messages.success(request, "Workflow updated.")
            return redirect("staff:learning_detail", kind=kind, node_id=node_id)
        except (EditorialWorkflowError, PermissionError, LearningStaffError) as exc:
            if isinstance(exc, PermissionError):
                _handle_perm(exc, request)
            messages.error(request, str(exc))
    if request.method == "POST" and request.POST.get("edit") and edit_form.is_valid():
        try:
            LearningStaffService.update_node(
                actor=request.user,
                kind=kind,
                node_id=node_id,
                title_en=edit_form.cleaned_data["title_en"],
                title_bn=edit_form.cleaned_data.get("title_bn") or "",
                summary=edit_form.cleaned_data.get("summary") or "",
                sort_order=edit_form.cleaned_data.get("sort_order") or 0,
                is_premium=bool(edit_form.cleaned_data.get("is_premium")),
            )
            messages.success(request, "Saved.")
            return redirect("staff:learning_detail", kind=kind, node_id=node_id)
        except (LearningStaffError, PermissionError) as exc:
            if isinstance(exc, PermissionError):
                _handle_perm(exc, request)
            messages.error(request, str(exc))
    children = None
    child_kind = None
    try:
        child_kind, children = LearningStaffService.children(request.user, kind, node_id)
    except LearningStaffError:
        children = []
    actions = EditorialWorkflowService.allowed_actions(request.user, obj, domain="content")
    return render(
        request,
        "staff/learning/detail.html",
        _staff_context(
            request,
            active="learning",
            extra={
                "page_heading": LearningStaffService.title_for(obj),
                "obj": obj,
                "kind": kind,
                "workflow_form": WorkflowForm(),
                "edit_form": edit_form,
                "actions": actions,
                "children": children or [],
                "child_kind": child_kind,
                "title_for": LearningStaffService.title_for,
            },
        ),
    )


# ----- Questions -----


@any_permission_required(
    "questions.create", "questions.view_unpublished", "questions.edit", "questions.publish"
)
@require_http_methods(["GET", "POST"])
def questions_list(request):
    if request.method == "POST":
        return _questions_bulk(request)
    filters = _question_list_filters(request)
    try:
        page_obj = QuestionStaffService.list_questions(
            request.user,
            q=filters["q"],
            state=filters["state"],
            question_type=filters["question_type"],
            cognitive=filters["cognitive"],
            blueprint_category=filters["blueprint_category"],
            blueprint_competency=filters["blueprint_competency"],
            content_subject=filters["subject"],
            content_topic=filters["topic"],
            scenario_based=filters["scenario_based"],
            needs_review=filters["needs_review"],
            source_type=filters["source_type"],
            source_name=filters["source_name"],
            created_from=filters["created_from"],
            created_to=filters["created_to"],
            import_batch_id=filters["import_batch_id"],
            difficulty=filters["difficulty"],
            classification_origin=filters["classification_origin"],
            page=request.GET.get("page"),
        )
        counts = QuestionStaffService.queue_counts(request.user)
    except PermissionError as exc:
        _handle_perm(exc, request)
    from apps.assessment.models import BlueprintCategory, BlueprintCompetency, ExamBlueprint
    from apps.common.choices import (
        ClassificationOrigin,
        CognitiveLevel,
        DifficultyLevel,
        QuestionType,
    )

    active_bp = ExamBlueprint.objects.filter(is_active=True).first()
    categories = (
        list(BlueprintCategory.objects.filter(blueprint=active_bp).order_by("sort_order"))
        if active_bp
        else []
    )
    competencies = (
        list(
            BlueprintCompetency.objects.filter(category__blueprint=active_bp)
            .select_related("category")
            .order_by("sort_order")
        )
        if active_bp
        else []
    )
    batches = []
    if AccessControlService.has_permission(request.user, "questions.import"):
        batches = list(
            QuestionStaffService.list_import_batches(request.user, page=1)
        )
    return render(
        request,
        "staff/questions/list.html",
        _staff_context(
            request,
            active="questions",
            extra={
                "page_heading": "Question bank",
                "page_obj": page_obj,
                "visible_count": len(page_obj.object_list) if page_obj else 0,
                "stem_for": QuestionStaffService.stem_for,
                "q": filters["q"],
                "state": filters["state"],
                "question_type": filters["question_type"],
                "cognitive": filters["cognitive"],
                "blueprint_category": filters["blueprint_category"],
                "blueprint_competency": filters["blueprint_competency"],
                "subject": filters["subject"],
                "topic": filters["topic"],
                "scenario_based": filters["scenario_param"],
                "needs_review": filters["needs_review_param"],
                "source_type": filters["source_type"],
                "source_name": filters["source_name"],
                "created_from": filters["created_from"],
                "created_to": filters["created_to"],
                "import_batch_id": filters["import_batch_id"],
                "difficulty": filters["difficulty"],
                "classification_origin": filters["classification_origin"],
                "querystring": filters["querystring"],
                "states": EditorialState.choices,
                "question_types": QuestionType.choices,
                "cognitive_levels": CognitiveLevel.choices,
                "difficulty_levels": DifficultyLevel.choices,
                "classification_origins": ClassificationOrigin.choices,
                "source_types": QuestionSourceType.choices,
                "blueprint_categories": categories,
                "blueprint_competencies": competencies,
                "import_batches": batches,
                "counts": counts,
                "import_href": reverse("staff:questions_import"),
                "blueprint_href": reverse("staff:blueprints"),
                "can_create": AccessControlService.has_permission(
                    request.user, "questions.create"
                ),
                "can_import": AccessControlService.has_permission(
                    request.user, "questions.import"
                ),
                "can_bulk_submit": AccessControlService.has_permission(
                    request.user, "content.submit_review"
                ),
                "can_bulk_approve": AccessControlService.has_permission(
                    request.user, "questions.approve"
                ),
                "can_bulk_publish": AccessControlService.has_permission(
                    request.user, "questions.publish"
                ),
                "can_bulk_classify": AccessControlService.has_permission(
                    request.user, "questions.edit"
                ),
                "can_view_provenance": QuestionStaffService.can_view_provenance(
                    request.user
                ),
            },
        ),
    )


def _questions_return_url(request):
    url = reverse("staff:questions")
    qs = request.GET.urlencode()
    if qs:
        return f"{url}?{qs}"
    return url


def _questions_bulk(request):
    intent = (request.POST.get("intent") or "").strip()
    ids = request.POST.getlist("question_ids")
    if intent == "bulk_publish" and request.POST.get("confirm_publish") != "1":
        messages.error(
            request,
            "Publish requires confirmation. Tick “Confirm publish” then try again.",
        )
        return redirect(_questions_return_url(request))
    try:
        if intent == "bulk_submit":
            result = QuestionStaffService.bulk_submit_review(
                actor=request.user, question_ids=ids
            )
        elif intent == "bulk_approve":
            result = QuestionStaffService.bulk_approve(
                actor=request.user, question_ids=ids
            )
        elif intent == "bulk_publish":
            result = QuestionStaffService.bulk_publish(
                actor=request.user, question_ids=ids
            )
        elif intent == "bulk_classify":
            result = QuestionStaffService.bulk_classify(
                actor=request.user,
                question_ids=ids,
                content_subject=request.POST.get("content_subject") or "",
                content_topic=request.POST.get("content_topic") or "",
                cognitive_level=request.POST.get("cognitive_level") or None,
                blueprint_category_id=request.POST.get("blueprint_category_id") or None,
                blueprint_competency_id=request.POST.get("blueprint_competency_id")
                or None,
            )
        else:
            messages.error(request, "Unknown bulk action.")
            return redirect(_questions_return_url(request))
    except (QuestionStaffError, PermissionError) as exc:
        if isinstance(exc, PermissionError):
            _handle_perm(exc, request)
        messages.error(request, str(exc))
        return redirect(_questions_return_url(request))
    _flash_bulk_result(request, result)
    return redirect(_questions_return_url(request))


@permission_required("questions.create")
@require_http_methods(["GET", "POST"])
def questions_create(request):
    form = QuestionCreateForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        options = [
            {"key": "A", "label": form.cleaned_data["option_a"]},
            {"key": "B", "label": form.cleaned_data["option_b"]},
        ]
        if form.cleaned_data.get("option_c"):
            options.append({"key": "C", "label": form.cleaned_data["option_c"]})
        if form.cleaned_data.get("option_d"):
            options.append({"key": "D", "label": form.cleaned_data["option_d"]})
        try:
            q = QuestionStaffService.create_question(
                actor=request.user,
                stem=form.cleaned_data["stem"],
                explanation=form.cleaned_data.get("explanation") or "",
                question_type=form.cleaned_data["question_type"],
                difficulty=form.cleaned_data.get("difficulty") or None,
                locale=form.cleaned_data["locale"],
                options=options,
                correct_key=form.cleaned_data["correct_key"],
                topic_id=form.cleaned_data.get("topic_id"),
                question_code=form.cleaned_data.get("question_code") or None,
                cognitive_level=form.cleaned_data.get("cognitive_level") or None,
                blueprint_category_id=form.cleaned_data.get("blueprint_category_id"),
                blueprint_competency_id=form.cleaned_data.get("blueprint_competency_id"),
                content_subject=form.cleaned_data.get("subject") or "",
                content_topic=form.cleaned_data.get("topic") or "",
                scenario_based=bool(form.cleaned_data.get("scenario_based")),
                scenario_body=form.cleaned_data.get("scenario") or "",
                source_type=form.cleaned_data.get("source_type") or None,
                source_name=form.cleaned_data.get("source_name") or "",
                source_page=form.cleaned_data.get("source_page") or "",
                source_reference=form.cleaned_data.get("source_reference") or "",
            )
            messages.success(request, "Question created as Draft.")
            return redirect("staff:question_detail", question_id=q.id)
        except (QuestionStaffError, PermissionError) as exc:
            if isinstance(exc, PermissionError):
                _handle_perm(exc, request)
            messages.error(request, str(exc))
    return render(
        request,
        "staff/questions/form.html",
        _staff_context(
            request,
            active="questions",
            extra={
                "page_heading": "Create question",
                "form": form,
                "create_breadcrumbs": [
                    {"label": "Question bank", "href": reverse("staff:questions")},
                    {"label": "Create", "href": ""},
                ],
            },
        ),
    )


@any_permission_required(
    "questions.create", "questions.view_unpublished", "questions.edit", "questions.publish"
)
@require_http_methods(["GET", "POST"])
def question_detail(request, question_id):
    try:
        question = QuestionStaffService.get_question(request.user, question_id)
    except QuestionStaffError:
        raise PermissionDenied("Not found.") from None
    intent = request.POST.get("intent", "workflow") if request.method == "POST" else ""
    if request.method == "POST" and intent == "classification":
        form = QuestionClassificationForm(request.POST)
        if form.is_valid():
            try:
                QuestionStaffService.update_classification(
                    actor=request.user,
                    question=question,
                    content_subject=form.cleaned_data.get("content_subject") or "",
                    content_topic=form.cleaned_data.get("content_topic") or "",
                    cognitive_level=form.cleaned_data.get("cognitive_level") or None,
                    difficulty=form.cleaned_data.get("difficulty") or None,
                    blueprint_category_id=form.cleaned_data.get("blueprint_category_id"),
                    blueprint_competency_id=form.cleaned_data.get(
                        "blueprint_competency_id"
                    ),
                    scenario_based=bool(form.cleaned_data.get("scenario_based")),
                    needs_review=bool(form.cleaned_data.get("needs_review")),
                    classification_origin=ClassificationOrigin.APPROVED,
                )
                messages.success(request, "Classification updated.")
                return redirect("staff:question_detail", question_id=question_id)
            except (QuestionStaffError, PermissionError) as exc:
                if isinstance(exc, PermissionError):
                    _handle_perm(exc, request)
                messages.error(request, str(exc))
    elif request.method == "POST" and intent == "review":
        form = QuestionReviewForm(request.POST)
        if form.is_valid():
            try:
                QuestionStaffService.update_review_state(
                    actor=request.user,
                    question=question,
                    needs_review=bool(form.cleaned_data.get("needs_review")),
                )
                messages.success(request, "Review state updated.")
                return redirect("staff:question_detail", question_id=question_id)
            except (QuestionStaffError, PermissionError) as exc:
                if isinstance(exc, PermissionError):
                    _handle_perm(exc, request)
                messages.error(request, str(exc))
    elif request.method == "POST" and intent == "apply_suggestion":
        try:
            QuestionStaffService.apply_suggestion(
                actor=request.user,
                question=question,
                fields=request.POST.getlist("suggestion_fields"),
            )
            messages.success(
                request,
                "Suggestion applied. Review it — suggestion is not final authority.",
            )
            return redirect("staff:question_detail", question_id=question_id)
        except (QuestionStaffError, PermissionError) as exc:
            if isinstance(exc, PermissionError):
                _handle_perm(exc, request)
            messages.error(request, str(exc))
    elif request.method == "POST" and intent == "reject_suggestion":
        try:
            QuestionStaffService.dismiss_suggestion(
                actor=request.user, question=question
            )
            messages.success(
                request,
                "Suggestion rejected. It was not assigned. Classify manually if needed.",
            )
            return redirect("staff:question_detail", question_id=question_id)
        except (QuestionStaffError, PermissionError) as exc:
            if isinstance(exc, PermissionError):
                _handle_perm(exc, request)
            messages.error(request, str(exc))
    elif request.method == "POST" and intent == "dismiss_duplicate":
        try:
            QuestionStaffService.dismiss_duplicate(
                actor=request.user,
                question=question,
                other_id=request.POST.get("other_id"),
            )
            messages.success(request, "Possible duplicate dismissed (both kept).")
            return redirect("staff:question_detail", question_id=question_id)
        except (QuestionStaffError, PermissionError) as exc:
            if isinstance(exc, PermissionError):
                _handle_perm(exc, request)
            messages.error(request, str(exc))
    elif request.method == "POST":
        workflow_form = WorkflowForm(request.POST)
        if workflow_form.is_valid():
            try:
                QuestionStaffService.workflow(
                    actor=request.user,
                    question_id=question_id,
                    action=workflow_form.cleaned_data["action"],
                    notes=workflow_form.cleaned_data.get("notes") or "",
                )
                messages.success(request, "Workflow updated.")
                return redirect("staff:question_detail", question_id=question_id)
            except (EditorialWorkflowError, PermissionError, QuestionStaffError) as exc:
                if isinstance(exc, PermissionError):
                    _handle_perm(exc, request)
                messages.error(request, str(exc))
    question = QuestionStaffService.get_question(request.user, question_id)
    actions = EditorialWorkflowService.allowed_actions(
        request.user, question, domain="questions"
    )
    from apps.assessment.models import BlueprintCategory, BlueprintCompetency, ExamBlueprint
    from apps.assessment.services.blueprint_suggest import BlueprintSuggestionService
    from apps.assessment.services.duplicates import QuestionDuplicateService

    active_bp = ExamBlueprint.objects.filter(is_active=True).first()
    categories = (
        list(BlueprintCategory.objects.filter(blueprint=active_bp).order_by("sort_order"))
        if active_bp
        else []
    )
    competencies = (
        list(
            BlueprintCompetency.objects.filter(category__blueprint=active_bp)
            .select_related("category")
            .order_by("sort_order")
        )
        if active_bp
        else []
    )
    classification_form = QuestionClassificationForm(
        initial={
            "content_subject": question.content_subject,
            "content_topic": question.content_topic,
            "cognitive_level": question.cognitive_level or "",
            "difficulty": question.difficulty or "",
            "blueprint_category_id": question.blueprint_category_id,
            "blueprint_competency_id": question.blueprint_competency_id,
            "scenario_based": question.scenario_based,
            "needs_review": question.needs_review,
        }
    )
    return render(
        request,
        "staff/questions/detail.html",
        _staff_context(
            request,
            active="questions",
            extra={
                "page_heading": "Question",
                "question": question,
                "stem": QuestionStaffService.stem_for(question),
                "actions": actions,
                "workflow_form": WorkflowForm(),
                "classification_form": classification_form,
                "review_form": QuestionReviewForm(
                    initial={"needs_review": question.needs_review}
                ),
                "validation_problems": QuestionStaffService.validation_problems(question),
                "source_view": QuestionStaffService.provenance_for(
                    request.user, question
                ),
                "answer_key": QuestionStaffService.staff_answer_key(
                    request.user, question
                ),
                "blueprint_categories": categories,
                "blueprint_competencies": competencies,
                "suggestion": BlueprintSuggestionService.suggest(question),
                "duplicate_hits": QuestionDuplicateService.find_for(question),
                "question_breadcrumbs": [
                    {"label": "Question bank", "href": reverse("staff:questions")},
                    {
                        "label": question.question_code or "Question",
                        "href": "",
                    },
                ],
            },
        ),
    )


# ----- Question Excel import -----


@permission_required("questions.import")
@require_http_methods(["GET", "POST"])
def questions_import(request):
    form = QuestionImportForm(request.POST or None, request.FILES or None)
    preview = None
    report = None
    stash_key = QuestionStaffService.IMPORT_STASH_SESSION_KEY
    if request.method == "POST" and form.is_valid():
        upload = form.cleaned_data.get("file")
        confirm = bool(form.cleaned_data.get("confirm"))
        from apps.assessment.services.import_questions import (
            ImportCommitError,
            ImportStructureError,
        )

        try:
            source, filename = QuestionStaffService.resolve_import_source(
                request.user,
                upload=upload,
                stash=request.session.get(stash_key),
            )
            if source is None:
                messages.error(
                    request,
                    "Choose a workbook to preview, or re-select it to confirm import.",
                )
            elif confirm:
                report = QuestionStaffService.import_commit(
                    request.user, source, filename=filename
                )
                QuestionStaffService.clear_import_stash(
                    request.session.pop(stash_key, None)
                )
                messages.success(
                    request,
                    f"Imported {report.created} question(s); "
                    f"skipped {report.skipped_duplicate} duplicate(s); "
                    f"needs review {report.needs_review}.",
                )
                if report.batch_id:
                    return redirect(
                        "staff:questions_import_batch", batch_id=report.batch_id
                    )
                return redirect("staff:questions")
            else:
                QuestionStaffService.clear_import_stash(
                    request.session.pop(stash_key, None)
                )
                request.session[stash_key] = QuestionStaffService.stash_import_upload(
                    request.user, source
                )
                preview = QuestionStaffService.import_preview(
                    request.user, request.session[stash_key]["path"]
                )
                if preview.importable:
                    messages.info(
                        request,
                        f"{preview.valid} valid, {preview.duplicate} duplicate, "
                        f"{preview.invalid} invalid. Confirm to import — "
                        "you do not need to re-attach the file.",
                    )
                else:
                    QuestionStaffService.clear_import_stash(
                        request.session.pop(stash_key, None)
                    )
                    messages.error(
                        request,
                        f"Workbook has {preview.invalid} invalid row(s); fix before importing.",
                    )
        except ImportStructureError as exc:
            messages.error(request, f"Workbook rejected: {exc}")
        except ImportCommitError as exc:
            messages.error(request, str(exc))
        except PermissionError as exc:
            _handle_perm(exc, request)
    return render(
        request,
        "staff/questions/import.html",
        _staff_context(
            request,
            active="questions",
            extra={
                "page_heading": "Import questions",
                "form": form,
                "preview": preview,
                "report": report,
                "has_stash": bool(request.session.get(stash_key)),
                "template_href": reverse("staff:questions_import_template"),
                "history_href": reverse("staff:questions_import_history"),
                "import_breadcrumbs": [
                    {"label": "Question bank", "href": reverse("staff:questions")},
                    {"label": "Import", "href": ""},
                ],
            },
        ),
    )


@permission_required("questions.import")
@require_http_methods(["GET"])
def questions_import_template(request):
    try:
        filename, payload = QuestionStaffService.example_workbook(request.user)
    except PermissionError as exc:
        _handle_perm(exc, request)
    response = HttpResponse(
        payload,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@permission_required("questions.import")
@require_http_methods(["GET"])
def questions_import_template_author(request):
    try:
        filename, payload = QuestionStaffService.author_workbook(request.user)
    except PermissionError as exc:
        _handle_perm(exc, request)
    response = HttpResponse(
        payload,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@permission_required("questions.import")
@require_http_methods(["GET"])
def questions_import_history(request):
    try:
        page_obj = QuestionStaffService.list_import_batches(
            request.user, page=request.GET.get("page")
        )
    except PermissionError as exc:
        _handle_perm(exc, request)
    return render(
        request,
        "staff/questions/import_history.html",
        _staff_context(
            request,
            active="questions",
            extra={
                "page_heading": "Import history",
                "page_obj": page_obj,
            },
        ),
    )


@permission_required("questions.import")
@require_http_methods(["GET"])
def questions_import_batch(request, batch_id):
    try:
        batch = QuestionStaffService.get_import_batch(request.user, batch_id)
    except QuestionStaffError:
        raise PermissionDenied("Not found.") from None
    except PermissionError as exc:
        _handle_perm(exc, request)
    created_codes = list(batch.created_codes or [])
    skipped_codes = list(batch.skipped_codes or [])
    errors = list(batch.errors or [])
    warnings = list(batch.warnings or [])
    return render(
        request,
        "staff/questions/import_batch.html",
        _staff_context(
            request,
            active="questions",
            extra={
                "page_heading": "Import report",
                "batch": batch,
                "created_codes": created_codes[:50],
                "created_more": max(0, len(created_codes) - 50),
                "skipped_codes": skipped_codes[:50],
                "skipped_more": max(0, len(skipped_codes) - 50),
                "display_errors": errors[:100],
                "hidden_error_count": max(0, len(errors) - 100),
                "display_warnings": warnings[:100],
                "hidden_warning_count": max(0, len(warnings) - 100),
                "source_counts": (batch.report or {}).get("source_counts") or {},
                "review_href": reverse("staff:questions")
                + f"?import_batch_id={batch.id}",
            },
        ),
    )


# ----- Blueprint -----


@any_permission_required("questions.view_unpublished", "exams.view", "questions.import")
@require_http_methods(["GET"])
def blueprints_list(request):
    try:
        blueprints = BlueprintStaffService.list_blueprints(request.user)
    except PermissionError as exc:
        _handle_perm(exc, request)
    return render(
        request,
        "staff/blueprints/list.html",
        _staff_context(
            request,
            active="questions",
            extra={"page_heading": "Exam blueprints", "blueprints": blueprints},
        ),
    )


@any_permission_required("questions.view_unpublished", "exams.view", "questions.import")
@require_http_methods(["GET"])
def blueprint_detail(request, blueprint_id):
    try:
        blueprint = BlueprintStaffService.get_blueprint(request.user, blueprint_id)
    except BlueprintStaffError:
        raise PermissionDenied("Not found.") from None
    except PermissionError as exc:
        _handle_perm(exc, request)
    plan = BlueprintStaffService.generation_plan(request.user, blueprint)
    return render(
        request,
        "staff/blueprints/detail.html",
        _staff_context(
            request,
            active="questions",
            extra={
                "page_heading": blueprint.name,
                "blueprint": blueprint,
                "categories": list(
                    blueprint.categories.all().order_by("sort_order", "name")
                ),
                "cognitive_allocations": list(
                    blueprint.cognitive_allocations.all().order_by("sort_order")
                ),
                "plan": plan,
            },
        ),
    )


@any_permission_required(
    "questions.view_error_reports", "questions.view_own_error_reports"
)
@require_http_methods(["GET", "POST"])
def question_reports(request):
    if request.method == "POST":
        form = ErrorReportForm(request.POST)
        if form.is_valid():
            try:
                QuestionStaffService.resolve_error_report(
                    actor=request.user,
                    report_id=request.POST.get("report_id"),
                    status=form.cleaned_data["status"],
                    notes=form.cleaned_data.get("notes") or "",
                )
                messages.success(request, "Report updated.")
            except (QuestionStaffError, PermissionError) as exc:
                if isinstance(exc, PermissionError):
                    _handle_perm(exc, request)
                messages.error(request, str(exc))
        return redirect("staff:question_reports")
    page_obj = QuestionStaffService.list_error_reports(
        request.user, status=request.GET.get("status", ""), page=request.GET.get("page")
    )
    return render(
        request,
        "staff/questions/reports.html",
        _staff_context(
            request,
            active="questions",
            extra={
                "page_heading": "Question error reports",
                "page_obj": page_obj,
                "form": ErrorReportForm(),
            },
        ),
    )


# ----- Exams -----


@permission_required("exams.view")
@require_http_methods(["GET"])
def exams_list(request):
    page_obj = ExamStaffService.list_exams(
        request.user,
        q=request.GET.get("q", ""),
        state=request.GET.get("state", ""),
        page=request.GET.get("page"),
    )
    return render(
        request,
        "staff/exams/list.html",
        _staff_context(
            request,
            active="exams",
            extra={
                "page_heading": "Exams",
                "page_obj": page_obj,
                "q": request.GET.get("q", ""),
                "state": request.GET.get("state", ""),
                "states": EditorialState.choices,
            },
        ),
    )


@any_permission_required("exams.create", "exams.create_limited")
@require_http_methods(["GET", "POST"])
def exams_create(request):
    form = ExamForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            exam = ExamStaffService.create_exam(
                actor=request.user,
                code=form.cleaned_data.get("code") or form.cleaned_data["title_key"],
                title_key=form.cleaned_data["title_key"],
                mode=form.cleaned_data["mode"],
                time_limit_seconds=form.cleaned_data.get("time_limit_seconds"),
                is_premium=bool(form.cleaned_data.get("is_premium")),
                track_code=form.cleaned_data.get("track_code") or "",
            )
            messages.success(request, "Exam created as Draft.")
            return redirect("staff:exam_detail", exam_id=exam.id)
        except (ExamStaffError, PermissionError) as exc:
            if isinstance(exc, PermissionError):
                _handle_perm(exc, request)
            messages.error(request, str(exc))
    return render(
        request,
        "staff/exams/form.html",
        _staff_context(
            request, active="exams", extra={"page_heading": "Create exam", "form": form}
        ),
    )


@permission_required("exams.view")
@require_http_methods(["GET", "POST"])
def exam_detail(request, exam_id):
    try:
        exam = ExamStaffService.get_exam(request.user, exam_id)
    except ExamStaffError:
        raise PermissionDenied("Not found.") from None
    form = ExamForm(request.POST or None, initial={
        "title_key": exam.title_key,
        "time_limit_seconds": exam.time_limit_seconds,
        "is_premium": exam.is_premium,
        "track_code": exam.track_code or "",
        "mode": exam.mode,
    })
    workflow_form = WorkflowForm(request.POST if request.POST.get("workflow") else None)
    if request.method == "POST" and request.POST.get("add_question"):
        qid = request.POST.get("question_id")
        try:
            ExamStaffService.add_question(actor=request.user, exam=exam, question_id=qid)
            messages.success(request, "Question linked.")
            return redirect("staff:exam_detail", exam_id=exam.id)
        except (ExamStaffError, PermissionError) as exc:
            if isinstance(exc, PermissionError):
                _handle_perm(exc, request)
            messages.error(request, str(exc))
    if request.method == "POST" and request.POST.get("workflow") and workflow_form.is_valid():
        try:
            ExamStaffService.workflow(
                actor=request.user,
                exam_id=exam_id,
                action=workflow_form.cleaned_data["action"],
                notes=workflow_form.cleaned_data.get("notes") or "",
            )
            messages.success(request, "Workflow updated.")
            return redirect("staff:exam_detail", exam_id=exam_id)
        except (EditorialWorkflowError, PermissionError, ExamStaffError) as exc:
            if isinstance(exc, PermissionError):
                _handle_perm(exc, request)
            messages.error(request, str(exc))
    if request.method == "POST" and request.POST.get("edit") and form.is_valid():
        try:
            ExamStaffService.update_exam(
                actor=request.user,
                exam=exam,
                title_key=form.cleaned_data["title_key"],
                time_limit_seconds=form.cleaned_data.get("time_limit_seconds"),
                is_premium=bool(form.cleaned_data.get("is_premium")),
                track_code=form.cleaned_data.get("track_code") or "",
            )
            messages.success(request, "Saved.")
            return redirect("staff:exam_detail", exam_id=exam.id)
        except (ExamStaffError, PermissionError) as exc:
            if isinstance(exc, PermissionError):
                _handle_perm(exc, request)
            messages.error(request, str(exc))
    actions = EditorialWorkflowService.allowed_actions(request.user, exam, domain="content")
    return render(
        request,
        "staff/exams/detail.html",
        _staff_context(
            request,
            active="exams",
            extra={
                "page_heading": exam.code,
                "exam": exam,
                "form": form,
                "workflow_form": WorkflowForm(),
                "actions": actions,
            },
        ),
    )


# ----- Library -----


@any_permission_required("library.manage", "content.create_draft", "content.publish")
@require_http_methods(["GET"])
def library_list(request):
    try:
        page_obj = LibraryStaffService.list_books(
            request.user,
            q=request.GET.get("q", ""),
            state=request.GET.get("state", ""),
            page=request.GET.get("page"),
        )
    except PermissionError as exc:
        _handle_perm(exc, request)
    return render(
        request,
        "staff/library/list.html",
        _staff_context(
            request,
            active="library",
            extra={
                "page_heading": "Library",
                "page_obj": page_obj,
                "title_for": LibraryStaffService.title_for,
                "q": request.GET.get("q", ""),
                "state": request.GET.get("state", ""),
                "states": EditorialState.choices,
            },
        ),
    )


@any_permission_required("library.manage", "content.create_draft")
@require_http_methods(["GET", "POST"])
def library_create(request):
    form = BookForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            book = LibraryStaffService.create_book(
                actor=request.user,
                title_en=form.cleaned_data["title_en"],
                title_bn=form.cleaned_data.get("title_bn") or "",
                blurb=form.cleaned_data.get("blurb") or "",
                author_name=form.cleaned_data.get("author_name") or "",
                category=form.cleaned_data.get("category") or "",
                is_premium=bool(form.cleaned_data.get("is_premium")),
                cover_storage_key=form.cleaned_data.get("cover_storage_key") or "",
            )
            messages.success(request, "Book created as Draft.")
            return redirect("staff:library_detail", book_id=book.id)
        except (LibraryStaffError, PermissionError) as exc:
            if isinstance(exc, PermissionError):
                _handle_perm(exc, request)
            messages.error(request, str(exc))
    return render(
        request,
        "staff/library/form.html",
        _staff_context(
            request, active="library", extra={"page_heading": "Create book", "form": form}
        ),
    )


@any_permission_required("library.manage", "content.create_draft", "content.publish")
@require_http_methods(["GET", "POST"])
def library_detail(request, book_id):
    try:
        book = LibraryStaffService.get_book(request.user, book_id)
    except LibraryStaffError:
        raise PermissionDenied("Not found.") from None
    form = BookForm(
        request.POST or None,
        initial={
            "title_en": LibraryStaffService.title_for(book),
            "author_name": book.author_name,
            "category": book.category,
            "is_premium": book.is_premium,
            "cover_storage_key": book.cover_storage_key,
        },
    )
    workflow_form = WorkflowForm(request.POST if request.POST.get("workflow") else None)
    if request.method == "POST" and request.POST.get("add_asset"):
        try:
            LibraryStaffService.add_asset(
                actor=request.user,
                book=book,
                format=request.POST.get("asset_format") or "pdf",
                storage_key=request.POST.get("asset_storage_key") or "",
            )
            messages.success(request, "Asset added.")
            return redirect("staff:library_detail", book_id=book.id)
        except (LibraryStaffError, PermissionError) as exc:
            if isinstance(exc, PermissionError):
                _handle_perm(exc, request)
            messages.error(request, str(exc))
    if request.method == "POST" and request.POST.get("workflow") and workflow_form.is_valid():
        try:
            LibraryStaffService.workflow(
                actor=request.user,
                book_id=book_id,
                action=workflow_form.cleaned_data["action"],
                notes=workflow_form.cleaned_data.get("notes") or "",
            )
            messages.success(request, "Workflow updated.")
            return redirect("staff:library_detail", book_id=book_id)
        except (EditorialWorkflowError, PermissionError, LibraryStaffError) as exc:
            if isinstance(exc, PermissionError):
                _handle_perm(exc, request)
            messages.error(request, str(exc))
    if request.method == "POST" and request.POST.get("edit") and form.is_valid():
        try:
            LibraryStaffService.update_book(
                actor=request.user,
                book=book,
                title_en=form.cleaned_data["title_en"],
                title_bn=form.cleaned_data.get("title_bn") or "",
                blurb=form.cleaned_data.get("blurb") or "",
                author_name=form.cleaned_data.get("author_name") or "",
                category=form.cleaned_data.get("category") or "",
                is_premium=bool(form.cleaned_data.get("is_premium")),
                cover_storage_key=form.cleaned_data.get("cover_storage_key") or "",
            )
            messages.success(request, "Saved.")
            return redirect("staff:library_detail", book_id=book.id)
        except (LibraryStaffError, PermissionError) as exc:
            if isinstance(exc, PermissionError):
                _handle_perm(exc, request)
            messages.error(request, str(exc))
    actions = EditorialWorkflowService.allowed_actions(request.user, book, domain="content")
    return render(
        request,
        "staff/library/detail.html",
        _staff_context(
            request,
            active="library",
            extra={
                "page_heading": LibraryStaffService.title_for(book),
                "book": book,
                "form": form,
                "workflow_form": WorkflowForm(),
                "actions": actions,
            },
        ),
    )


# ----- CMS -----


@permission_required("cms.manage")
@require_http_methods(["GET"])
def cms_home(request):
    pages = CmsStaffService.list_pages(request.user, q=request.GET.get("q", ""), page=1)
    posts = CmsStaffService.list_posts(request.user, q=request.GET.get("q", ""), page=1)
    contacts = None
    if AccessControlService.has_permission(request.user, "cms.contact_triage"):
        contacts = CmsStaffService.list_contacts(request.user, page=1)
    return render(
        request,
        "staff/cms/home.html",
        _staff_context(
            request,
            active="cms",
            extra={
                "page_heading": "CMS",
                "pages": pages,
                "posts": posts,
                "contacts": contacts,
                "contact_form": ContactStatusForm(),
            },
        ),
    )


@permission_required("cms.manage")
@require_http_methods(["GET", "POST"])
def cms_page_create(request):
    form = CmsForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            page = CmsStaffService.create_page(
                actor=request.user,
                code=form.cleaned_data["code"],
                title=form.cleaned_data["title"],
                body=form.cleaned_data.get("body") or "",
                meta_title=form.cleaned_data.get("meta_title") or "",
                meta_description=form.cleaned_data.get("meta_description") or "",
            )
            messages.success(request, "Page created as Draft.")
            return redirect("staff:cms_page_detail", page_id=page.id)
        except (CmsStaffError, PermissionError) as exc:
            if isinstance(exc, PermissionError):
                _handle_perm(exc, request)
            messages.error(request, str(exc))
    return render(
        request,
        "staff/cms/form.html",
        _staff_context(
            request, active="cms", extra={"page_heading": "Create CMS page", "form": form}
        ),
    )


@permission_required("cms.manage")
@require_http_methods(["GET", "POST"])
def cms_page_detail(request, page_id):
    try:
        page = CmsStaffService.get_page(request.user, page_id)
    except CmsStaffError:
        raise PermissionDenied("Not found.") from None
    workflow_form = WorkflowForm(request.POST or None)
    if request.method == "POST" and workflow_form.is_valid():
        try:
            CmsStaffService.workflow_page(
                actor=request.user,
                page_id=page_id,
                action=workflow_form.cleaned_data["action"],
                notes=workflow_form.cleaned_data.get("notes") or "",
            )
            messages.success(request, "Workflow updated.")
            return redirect("staff:cms_page_detail", page_id=page_id)
        except (EditorialWorkflowError, PermissionError, CmsStaffError) as exc:
            if isinstance(exc, PermissionError):
                _handle_perm(exc, request)
            messages.error(request, str(exc))
    return render(
        request,
        "staff/cms/detail.html",
        _staff_context(
            request,
            active="cms",
            extra={
                "page_heading": page.code,
                "obj": page,
                "kind": "page",
                "actions": EditorialWorkflowService.allowed_actions(
                    request.user, page, domain="content"
                ),
                "workflow_form": WorkflowForm(),
            },
        ),
    )


@permission_required("cms.manage")
@require_http_methods(["GET", "POST"])
def cms_post_create(request):
    form = CmsForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            post = CmsStaffService.create_post(
                actor=request.user,
                code=form.cleaned_data["code"],
                title=form.cleaned_data["title"],
                body=form.cleaned_data.get("body") or "",
                meta_title=form.cleaned_data.get("meta_title") or "",
                meta_description=form.cleaned_data.get("meta_description") or "",
            )
            messages.success(request, "Post created as Draft.")
            return redirect("staff:cms_post_detail", post_id=post.id)
        except (CmsStaffError, PermissionError) as exc:
            if isinstance(exc, PermissionError):
                _handle_perm(exc, request)
            messages.error(request, str(exc))
    return render(
        request,
        "staff/cms/form.html",
        _staff_context(
            request, active="cms", extra={"page_heading": "Create blog post", "form": form}
        ),
    )


@permission_required("cms.manage")
@require_http_methods(["GET", "POST"])
def cms_post_detail(request, post_id):
    try:
        post = CmsStaffService.get_post(request.user, post_id)
    except CmsStaffError:
        raise PermissionDenied("Not found.") from None
    workflow_form = WorkflowForm(request.POST or None)
    if request.method == "POST" and workflow_form.is_valid():
        try:
            CmsStaffService.workflow_post(
                actor=request.user,
                post_id=post_id,
                action=workflow_form.cleaned_data["action"],
                notes=workflow_form.cleaned_data.get("notes") or "",
            )
            messages.success(request, "Workflow updated.")
            return redirect("staff:cms_post_detail", post_id=post_id)
        except (EditorialWorkflowError, PermissionError, CmsStaffError) as exc:
            if isinstance(exc, PermissionError):
                _handle_perm(exc, request)
            messages.error(request, str(exc))
    return render(
        request,
        "staff/cms/detail.html",
        _staff_context(
            request,
            active="cms",
            extra={
                "page_heading": post.code,
                "obj": post,
                "kind": "post",
                "actions": EditorialWorkflowService.allowed_actions(
                    request.user, post, domain="content"
                ),
                "workflow_form": WorkflowForm(),
            },
        ),
    )


@permission_required("cms.contact_triage")
@require_POST
def cms_contact_update(request, message_id):
    form = ContactStatusForm(request.POST)
    if form.is_valid():
        try:
            CmsStaffService.update_contact(
                actor=request.user,
                message_id=message_id,
                status=form.cleaned_data["status"],
            )
            messages.success(request, "Contact updated.")
        except (CmsStaffError, PermissionError) as exc:
            if isinstance(exc, PermissionError):
                _handle_perm(exc, request)
            messages.error(request, str(exc))
    return redirect("staff:cms")


# ----- Announcements -----


@any_permission_required("announcements.create", "announcements.publish")
@require_http_methods(["GET"])
def announcements_list(request):
    page_obj = AnnouncementStaffService.list_announcements(
        request.user, q=request.GET.get("q", ""), page=request.GET.get("page")
    )
    return render(
        request,
        "staff/announcements/list.html",
        _staff_context(
            request,
            active="announcements",
            extra={"page_heading": "Announcements", "page_obj": page_obj},
        ),
    )


@permission_required("announcements.create")
@require_http_methods(["GET", "POST"])
def announcements_create(request):
    form = AnnouncementForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            row = AnnouncementStaffService.create(
                actor=request.user,
                code=form.cleaned_data["code"],
                title=form.cleaned_data["title"],
                body=form.cleaned_data["body"],
            )
            messages.success(request, "Announcement created as Draft.")
            return redirect("staff:announcement_detail", announcement_id=row.id)
        except (AnnouncementStaffError, PermissionError) as exc:
            if isinstance(exc, PermissionError):
                _handle_perm(exc, request)
            messages.error(request, str(exc))
    return render(
        request,
        "staff/announcements/form.html",
        _staff_context(
            request,
            active="announcements",
            extra={"page_heading": "Create announcement", "form": form},
        ),
    )


@any_permission_required("announcements.create", "announcements.publish")
@require_http_methods(["GET", "POST"])
def announcement_detail(request, announcement_id):
    try:
        row = AnnouncementStaffService.get(request.user, announcement_id)
    except AnnouncementStaffError:
        raise PermissionDenied("Not found.") from None
    workflow_form = WorkflowForm(request.POST or None)
    if request.method == "POST" and workflow_form.is_valid():
        try:
            AnnouncementStaffService.workflow(
                actor=request.user,
                announcement_id=announcement_id,
                action=workflow_form.cleaned_data["action"],
                notes=workflow_form.cleaned_data.get("notes") or "",
            )
            messages.success(request, "Workflow updated.")
            return redirect("staff:announcement_detail", announcement_id=announcement_id)
        except (EditorialWorkflowError, PermissionError, AnnouncementStaffError) as exc:
            if isinstance(exc, PermissionError):
                _handle_perm(exc, request)
            messages.error(request, str(exc))
    return render(
        request,
        "staff/announcements/detail.html",
        _staff_context(
            request,
            active="announcements",
            extra={
                "page_heading": row.code,
                "obj": row,
                "actions": EditorialWorkflowService.allowed_actions(
                    request.user, row, domain="content"
                ),
                "workflow_form": WorkflowForm(),
            },
        ),
    )


# ----- Billing -----


@any_permission_required("billing.view_subscriptions", "billing.view_payments")
@require_http_methods(["GET", "POST"])
def billing_home(request):
    grant_form = ManualGrantForm(request.POST or None)
    if request.method == "POST" and request.POST.get("grant") and grant_form.is_valid():
        try:
            BillingStaffService.manual_grant_premium(
                actor=request.user,
                user_id=grant_form.cleaned_data["user_id"],
                notes=grant_form.cleaned_data.get("notes") or "",
            )
            messages.success(request, "Premium granted (audited).")
            return redirect("staff:billing")
        except (BillingStaffError, PermissionError) as exc:
            if isinstance(exc, PermissionError):
                _handle_perm(exc, request)
            messages.error(request, str(exc))
    if request.method == "POST" and request.POST.get("revoke") and grant_form.is_valid():
        try:
            BillingStaffService.manual_revoke_premium(
                actor=request.user,
                user_id=grant_form.cleaned_data["user_id"],
                notes=grant_form.cleaned_data.get("notes") or "",
            )
            messages.success(request, "Premium revoked (audited).")
            return redirect("staff:billing")
        except (BillingStaffError, PermissionError) as exc:
            if isinstance(exc, PermissionError):
                _handle_perm(exc, request)
            messages.error(request, str(exc))
    subs = None
    payments = None
    if AccessControlService.has_permission(request.user, "billing.view_subscriptions"):
        subs = BillingStaffService.list_subscriptions(
            request.user,
            q=request.GET.get("q", ""),
            state=request.GET.get("state", ""),
            page=request.GET.get("page"),
        )
    if AccessControlService.has_permission(request.user, "billing.view_payments"):
        payments = BillingStaffService.list_payments(
            request.user, q=request.GET.get("q", ""), page=1
        )
    return render(
        request,
        "staff/billing/home.html",
        _staff_context(
            request,
            active="billing",
            extra={
                "page_heading": "Billing & subscriptions",
                "subs": subs,
                "payments": payments,
                "grant_form": ManualGrantForm(),
                "can_grant": AccessControlService.has_permission(
                    request.user, "billing.manual_grant"
                ),
            },
        ),
    )


# ----- Audit -----


@permission_required("audit.view")
@require_http_methods(["GET"])
def audit_list(request):
    page_obj = AuditStaffService.list_events(
        request.user,
        q=request.GET.get("q", ""),
        action=request.GET.get("action", ""),
        page=request.GET.get("page"),
    )
    return render(
        request,
        "staff/audit/list.html",
        _staff_context(
            request,
            active="audit",
            extra={
                "page_heading": "Audit log",
                "page_obj": page_obj,
                "q": request.GET.get("q", ""),
            },
        ),
    )


# ----- Editorial queue -----


@any_permission_required(
    "content.approve", "content.publish", "content.submit_review", "questions.approve"
)
@require_http_methods(["GET"])
def editorial_queue(request):
    from apps.assessment.models import Question
    from apps.learning.models import Course
    from apps.library.models import Book

    courses = Course.objects.filter(editorial_state=EditorialState.REVIEW, is_archived=False)[
        :50
    ]
    questions = Question.objects.filter(
        editorial_state=EditorialState.REVIEW, is_archived=False
    )[:50]
    approved_courses = Course.objects.filter(
        editorial_state=EditorialState.APPROVED, is_archived=False
    )[:50]
    books = Book.objects.filter(editorial_state=EditorialState.REVIEW, is_archived=False)[
        :50
    ]
    return render(
        request,
        "staff/editorial/queue.html",
        _staff_context(
            request,
            active="editorial",
            extra={
                "page_heading": "Editorial queue",
                "courses_review": courses,
                "courses_approved": approved_courses,
                "questions_review": questions,
                "books_review": books,
                "title_for": LearningStaffService.title_for,
                "book_title": LibraryStaffService.title_for,
                "stem_for": QuestionStaffService.stem_for,
            },
        ),
    )


@staff_console_required
@require_http_methods(["GET"])
def preview_learning(request, kind, node_id):
    """Staff unpublished preview — never a Student capability (docs/03)."""
    if not (
        AccessControlService.has_permission(request.user, "content.preview_unpublished")
        or AccessControlService.has_permission(request.user, "content.preview_own")
        or AccessControlService.has_permission(request.user, "content.view_unpublished")
    ):
        raise PermissionDenied("Preview denied.")
    try:
        obj = LearningStaffService.get_node(request.user, kind, node_id)
    except LearningStaffError:
        raise PermissionDenied("Not found.") from None
    return render(
        request,
        "staff/learning/preview.html",
        _staff_context(
            request,
            active="learning",
            extra={
                "page_heading": f"Preview: {LearningStaffService.title_for(obj)}",
                "obj": obj,
                "kind": kind,
                "title": LearningStaffService.title_for(obj),
            },
        ),
    )
