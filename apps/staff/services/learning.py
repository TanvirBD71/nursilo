"""Learning hierarchy staff management (reuse UNIT-4 models)."""
from __future__ import annotations

from django.db import transaction
from django.db.models import Q

from apps.audit.services import AuditService
from apps.cms.services import EditorialWorkflowService
from apps.common.choices import EditorialState, LocaleCode
from apps.learning.models import (
    Chapter,
    ChapterTranslation,
    Course,
    CourseTranslation,
    LearningMaterial,
    LearningMaterialTranslation,
    Lesson,
    LessonLearningMaterial,
    LessonTranslation,
    Subject,
    SubjectTranslation,
    Topic,
    TopicTranslation,
    Unit,
    UnitTranslation,
)
from apps.rbac.services import AccessControlService
from apps.staff.services.pagination import paginate_queryset

NODE_MAP = {
    "course": (Course, CourseTranslation, "course", None),
    "subject": (Subject, SubjectTranslation, "subject", "course"),
    "unit": (Unit, UnitTranslation, "unit", "subject"),
    "chapter": (Chapter, ChapterTranslation, "chapter", "unit"),
    "topic": (Topic, TopicTranslation, "topic", "chapter"),
    "lesson": (Lesson, LessonTranslation, "lesson", "topic"),
    "material": (LearningMaterial, LearningMaterialTranslation, "learning_material", None),
}

CHILD_OF = {
    "course": ("subject", Subject, "course"),
    "subject": ("unit", Unit, "subject"),
    "unit": ("chapter", Chapter, "unit"),
    "chapter": ("topic", Topic, "chapter"),
    "topic": ("lesson", Lesson, "topic"),
}


class LearningStaffError(Exception):
    def __init__(self, message: str, *, code: str = "learning_error"):
        super().__init__(message)
        self.code = code


class LearningStaffService:
    @classmethod
    def list_courses(cls, actor, *, q: str = "", state: str = "", page=1):
        cls._require_view(actor)
        qs = Course.objects.all().order_by("sort_order", "created_at")
        qs = cls._scope_queryset(actor, qs)
        if state:
            qs = qs.filter(editorial_state=state)
        if q:
            qs = qs.filter(
                Q(translations__title__icontains=q) | Q(id__icontains=q)
            ).distinct()
        page_obj = paginate_queryset(qs.prefetch_related("translations"), page=page)
        return page_obj

    @classmethod
    def get_node(cls, actor, kind: str, node_id):
        cls._require_view(actor)
        model, _trans, _fk, _parent = cls._resolve(kind)
        try:
            obj = model.objects.get(pk=node_id)
        except model.DoesNotExist as exc:
            raise LearningStaffError("Not found.", code="not_found") from exc
        if not cls._can_view_obj(actor, obj):
            raise LearningStaffError("Not found.", code="not_found")
        return obj

    @classmethod
    @transaction.atomic
    def create_node(
        cls,
        *,
        actor,
        kind: str,
        title_en: str,
        title_bn: str = "",
        summary: str = "",
        parent_id=None,
        sort_order: int = 0,
        is_premium: bool = False,
    ):
        if not (
            AccessControlService.has_permission(actor, "content.create_draft")
            or AccessControlService.has_permission(actor, "content.edit")
        ):
            raise PermissionError("Permission denied.")
        model, trans_model, fk_name, parent_field = cls._resolve(kind)
        kwargs: dict = {
            "sort_order": int(sort_order or 0),
            "editorial_state": EditorialState.DRAFT,
            "created_by": actor,
            "updated_by": actor,
        }
        if parent_field:
            if not parent_id:
                raise LearningStaffError("Parent is required.", code="validation")
            parent_kind = {
                "subject": "course",
                "unit": "subject",
                "chapter": "unit",
                "topic": "chapter",
                "lesson": "topic",
            }[kind]
            parent = cls.get_node(actor, parent_kind, parent_id)
            kwargs[parent_field] = parent
        if kind == "material":
            kwargs["is_premium"] = bool(is_premium)
        obj = model.objects.create(**kwargs)
        cls._upsert_translation(
            trans_model,
            fk_name,
            obj,
            LocaleCode.EN,
            title_en,
            summary,
        )
        if title_bn:
            cls._upsert_translation(
                trans_model,
                fk_name,
                obj,
                LocaleCode.BN,
                title_bn,
                summary,
            )
        AuditService.record(
            action="content_created",
            actor_user=actor,
            target_type=kind,
            target_id=str(obj.pk),
            metadata={"title": title_en},
        )
        return obj

    @classmethod
    @transaction.atomic
    def update_node(
        cls,
        *,
        actor,
        kind: str,
        node_id,
        title_en: str,
        title_bn: str = "",
        summary: str = "",
        sort_order: int = 0,
        is_premium: bool | None = None,
    ):
        obj = cls.get_node(actor, kind, node_id)
        cls._require_edit(actor, obj)
        model, trans_model, fk_name, _parent = cls._resolve(kind)
        # Published edits by editors/admins allowed; authors only drafts they own.
        obj.sort_order = int(sort_order or 0)
        obj.updated_by = actor
        fields = ["sort_order", "updated_by", "updated_at"]
        if kind == "material" and is_premium is not None:
            obj.is_premium = bool(is_premium)
            fields.append("is_premium")
        if hasattr(obj, "version_number"):
            obj.version_number = int(obj.version_number or 1) + 1
            fields.append("version_number")
        obj.save(update_fields=fields)
        cls._upsert_translation(
            trans_model, fk_name, obj, LocaleCode.EN, title_en, summary
        )
        if title_bn:
            cls._upsert_translation(
                trans_model, fk_name, obj, LocaleCode.BN, title_bn, summary
            )
        AuditService.record(
            action="content_edited",
            actor_user=actor,
            target_type=kind,
            target_id=str(obj.pk),
            metadata={"title": title_en},
        )
        return obj

    @classmethod
    def children(cls, actor, kind: str, node_id):
        obj = cls.get_node(actor, kind, node_id)
        if kind not in CHILD_OF:
            return None, []
        child_kind, child_model, fk = CHILD_OF[kind]
        qs = child_model.objects.filter(**{fk: obj}).order_by("sort_order", "created_at")
        qs = cls._scope_queryset(actor, qs)
        return child_kind, list(qs.prefetch_related("translations"))

    @classmethod
    def workflow(cls, *, actor, kind: str, node_id, action: str, notes: str = ""):
        obj = cls.get_node(actor, kind, node_id)
        return EditorialWorkflowService.transition(
            obj=obj,
            action=action,
            actor=actor,
            domain="content",
            target_type=kind,
            notes=notes,
        )

    @classmethod
    def title_for(cls, obj, locale=LocaleCode.EN) -> str:
        trans = None
        if hasattr(obj, "translations"):
            trans = obj.translations.filter(locale=locale).first()
            if trans is None:
                trans = obj.translations.first()
        return getattr(trans, "title", None) or str(obj.pk)

    @classmethod
    def link_material(cls, *, actor, lesson_id, material_id, sort_order: int = 0):
        lesson = cls.get_node(actor, "lesson", lesson_id)
        material = cls.get_node(actor, "material", material_id)
        cls._require_edit(actor, lesson)
        link, _ = LessonLearningMaterial.objects.get_or_create(
            lesson=lesson,
            learning_material=material,
            defaults={"sort_order": int(sort_order or 0)},
        )
        return link

    @classmethod
    def _resolve(cls, kind: str):
        if kind not in NODE_MAP:
            raise LearningStaffError("Unknown content type.", code="validation")
        return NODE_MAP[kind]

    @classmethod
    def _require_view(cls, actor):
        if AccessControlService.has_permission(actor, "content.view_unpublished"):
            return
        if AccessControlService.has_permission(actor, "content.create_draft"):
            return
        if AccessControlService.has_permission(actor, "content.preview_own"):
            return
        raise PermissionError("Permission denied.")

    @classmethod
    def _require_edit(cls, actor, obj):
        if AccessControlService.has_permission(actor, "content.edit"):
            return
        if AccessControlService.has_permission(actor, "content.edit_own_draft"):
            if (
                getattr(obj, "created_by_id", None) == actor.id
                and obj.editorial_state == EditorialState.DRAFT
            ):
                return
        raise PermissionError("Permission denied.")

    @classmethod
    def _can_view_obj(cls, actor, obj) -> bool:
        if AccessControlService.has_permission(actor, "content.view_unpublished"):
            return True
        if AccessControlService.has_permission(actor, "content.preview_unpublished"):
            return True
        if getattr(obj, "created_by_id", None) == actor.id:
            return True
        if obj.editorial_state == EditorialState.PUBLISHED and not obj.is_archived:
            return True
        return False

    @classmethod
    def _scope_queryset(cls, actor, qs):
        if AccessControlService.has_permission(actor, "content.view_unpublished"):
            return qs
        if AccessControlService.has_permission(actor, "content.preview_unpublished"):
            return qs
        # Authors: own drafts + published
        return qs.filter(
            Q(created_by=actor)
            | Q(editorial_state=EditorialState.PUBLISHED, is_archived=False)
        )

    @staticmethod
    def _upsert_translation(trans_model, fk_name, obj, locale, title, summary):
        defaults = {"title": (title or "").strip() or "Untitled"}
        if "summary" in {f.name for f in trans_model._meta.fields}:
            defaults["summary"] = summary or ""
        if "body" in {f.name for f in trans_model._meta.fields}:
            defaults["body"] = summary or ""
        trans_model.objects.update_or_create(
            **{fk_name: obj, "locale": locale},
            defaults=defaults,
        )
