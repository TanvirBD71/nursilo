"""CMS pages/blog + contact triage staff services."""
from __future__ import annotations

from django.db import transaction
from django.db.models import Q
from django.utils.text import slugify

from apps.audit.services import AuditService
from apps.cms.models import BlogPost, BlogPostTranslation, CmsPage, CmsPageTranslation, ContactMessage
from apps.cms.services import EditorialWorkflowService
from apps.common.choices import ContactMessageStatus, EditorialState, LocaleCode
from apps.rbac.services import AccessControlService
from apps.staff.services.pagination import paginate_queryset


class CmsStaffError(Exception):
    def __init__(self, message: str, *, code: str = "cms_error"):
        super().__init__(message)
        self.code = code


class CmsStaffService:
    @classmethod
    def list_pages(cls, actor, *, q: str = "", page=1):
        AccessControlService.require_permission(actor, "cms.manage")
        qs = CmsPage.objects.all().order_by("-updated_at")
        if q:
            qs = qs.filter(Q(code__icontains=q) | Q(translations__title__icontains=q)).distinct()
        return paginate_queryset(qs.prefetch_related("translations"), page=page)

    @classmethod
    def list_posts(cls, actor, *, q: str = "", page=1):
        AccessControlService.require_permission(actor, "cms.manage")
        qs = BlogPost.objects.all().order_by("-updated_at")
        if q:
            qs = qs.filter(Q(code__icontains=q) | Q(translations__title__icontains=q)).distinct()
        return paginate_queryset(qs.prefetch_related("translations"), page=page)

    @classmethod
    def get_page(cls, actor, page_id) -> CmsPage:
        AccessControlService.require_permission(actor, "cms.manage")
        try:
            return CmsPage.objects.prefetch_related("translations").get(pk=page_id)
        except CmsPage.DoesNotExist as exc:
            raise CmsStaffError("Not found.", code="not_found") from exc

    @classmethod
    def get_post(cls, actor, post_id) -> BlogPost:
        AccessControlService.require_permission(actor, "cms.manage")
        try:
            return BlogPost.objects.prefetch_related("translations").get(pk=post_id)
        except BlogPost.DoesNotExist as exc:
            raise CmsStaffError("Not found.", code="not_found") from exc

    @classmethod
    @transaction.atomic
    def create_page(
        cls,
        *,
        actor,
        code: str,
        title: str,
        body: str = "",
        locale: str = LocaleCode.EN,
        meta_title: str = "",
        meta_description: str = "",
    ) -> CmsPage:
        AccessControlService.require_permission(actor, "cms.manage")
        code = (code or "").strip().lower()
        if not code:
            raise CmsStaffError("Code required.", code="validation")
        page = CmsPage.objects.create(
            code=code,
            editorial_state=EditorialState.DRAFT,
            created_by=actor,
            updated_by=actor,
        )
        CmsPageTranslation.objects.create(
            page=page,
            locale=locale,
            title=(title or "").strip() or code,
            body=body or "",
            slug=slugify(title or code) or code,
            meta_title=meta_title or "",
            meta_description=meta_description or "",
        )
        AuditService.record(
            action="cms_page_created",
            actor_user=actor,
            target_type="cms_page",
            target_id=str(page.id),
            metadata={"code": code},
        )
        return page

    @classmethod
    @transaction.atomic
    def create_post(
        cls,
        *,
        actor,
        code: str,
        title: str,
        body: str = "",
        locale: str = LocaleCode.EN,
        meta_title: str = "",
        meta_description: str = "",
    ) -> BlogPost:
        AccessControlService.require_permission(actor, "cms.manage")
        code = (code or "").strip().lower()
        if not code:
            raise CmsStaffError("Code required.", code="validation")
        post = BlogPost.objects.create(
            code=code,
            editorial_state=EditorialState.DRAFT,
            created_by=actor,
            updated_by=actor,
        )
        BlogPostTranslation.objects.create(
            post=post,
            locale=locale,
            title=(title or "").strip() or code,
            body=body or "",
            slug=slugify(title or code) or code,
            meta_title=meta_title or "",
            meta_description=meta_description or "",
        )
        AuditService.record(
            action="blog_post_created",
            actor_user=actor,
            target_type="blog_post",
            target_id=str(post.id),
            metadata={"code": code},
        )
        return post

    @classmethod
    def workflow_page(cls, *, actor, page_id, action: str, notes: str = ""):
        page = cls.get_page(actor, page_id)
        return EditorialWorkflowService.transition(
            obj=page,
            action=action,
            actor=actor,
            domain="content",
            target_type="cms_page",
            notes=notes,
        )

    @classmethod
    def workflow_post(cls, *, actor, post_id, action: str, notes: str = ""):
        post = cls.get_post(actor, post_id)
        return EditorialWorkflowService.transition(
            obj=post,
            action=action,
            actor=actor,
            domain="content",
            target_type="blog_post",
            notes=notes,
        )

    @classmethod
    def list_contacts(cls, actor, *, status: str = "", page=1):
        AccessControlService.require_permission(actor, "cms.contact_triage")
        qs = ContactMessage.objects.all().order_by("-created_at")
        if status:
            qs = qs.filter(status=status)
        return paginate_queryset(qs, page=page)

    @classmethod
    @transaction.atomic
    def update_contact(cls, *, actor, message_id, status: str):
        AccessControlService.require_permission(actor, "cms.contact_triage")
        if status not in {c.value for c in ContactMessageStatus}:
            raise CmsStaffError("Invalid status.", code="validation")
        try:
            msg = ContactMessage.objects.select_for_update().get(pk=message_id)
        except ContactMessage.DoesNotExist as exc:
            raise CmsStaffError("Not found.", code="not_found") from exc
        msg.status = status
        msg.save(update_fields=["status"])
        AuditService.record(
            action="contact_message_updated",
            actor_user=actor,
            target_type="contact_message",
            target_id=str(msg.id),
            metadata={"status": status},
        )
        return msg
