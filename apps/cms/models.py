"""CMS foundation — pages, blog, contact (docs/05 §13, docs/06 §8.14)."""
from django.conf import settings
from django.db import models

from apps.common.choices import ContactMessageStatus
from apps.common.models import (
    ActorTrackedModel,
    ArchivableModel,
    EditorialModel,
    LocaleField,
    OptimisticConcurrencyModel,
    TimeStampedModel,
    UUIDPrimaryKeyModel,
)


class CmsPage(
    UUIDPrimaryKeyModel,
    TimeStampedModel,
    ActorTrackedModel,
    OptimisticConcurrencyModel,
    ArchivableModel,
    EditorialModel,
):
    code = models.CharField(max_length=64, unique=True)

    class Meta:
        db_table = "cms_pages"
        indexes = [
            models.Index(fields=["editorial_state", "is_archived"]),
        ]


class CmsPageTranslation(UUIDPrimaryKeyModel):
    page = models.ForeignKey(CmsPage, on_delete=models.CASCADE, related_name="translations")
    locale = LocaleField()
    title = models.CharField(max_length=255)
    body = models.TextField(blank=True, default="")
    slug = models.SlugField(max_length=255)
    meta_title = models.CharField(max_length=255, blank=True, default="")
    meta_description = models.TextField(blank=True, default="")

    class Meta:
        db_table = "cms_page_translations"
        constraints = [
            models.UniqueConstraint(fields=["page", "locale"], name="uq_cms_page_translations_locale"),
            models.UniqueConstraint(fields=["locale", "slug"], name="uq_cms_page_translations_slug"),
        ]


class BlogPost(
    UUIDPrimaryKeyModel,
    TimeStampedModel,
    ActorTrackedModel,
    OptimisticConcurrencyModel,
    ArchivableModel,
    EditorialModel,
):
    code = models.CharField(max_length=64, unique=True)

    class Meta:
        db_table = "blog_posts"
        indexes = [
            models.Index(fields=["editorial_state", "is_archived"]),
        ]


class BlogPostTranslation(UUIDPrimaryKeyModel):
    post = models.ForeignKey(BlogPost, on_delete=models.CASCADE, related_name="translations")
    locale = LocaleField()
    title = models.CharField(max_length=255)
    body = models.TextField(blank=True, default="")
    slug = models.SlugField(max_length=255)
    meta_title = models.CharField(max_length=255, blank=True, default="")
    meta_description = models.TextField(blank=True, default="")

    class Meta:
        db_table = "blog_post_translations"
        constraints = [
            models.UniqueConstraint(fields=["post", "locale"], name="uq_blog_post_translations_locale"),
            models.UniqueConstraint(fields=["locale", "slug"], name="uq_blog_post_translations_slug"),
        ]


class ContactMessage(UUIDPrimaryKeyModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="contact_messages",
    )
    email = models.EmailField()
    subject = models.CharField(max_length=255)
    body = models.TextField()
    status = models.CharField(
        max_length=32,
        choices=ContactMessageStatus.choices,
        default=ContactMessageStatus.NEW,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "contact_messages"
        indexes = [
            models.Index(fields=["status", "-created_at"]),
        ]
