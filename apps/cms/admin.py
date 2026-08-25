from django.contrib import admin

from apps.cms.models import BlogPost, CmsPage, ContactMessage


@admin.register(CmsPage)
class CmsPageAdmin(admin.ModelAdmin):
    list_display = ("code", "editorial_state", "is_archived", "updated_at")
    list_filter = ("editorial_state", "is_archived")


@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ("code", "editorial_state", "is_archived", "updated_at")
    list_filter = ("editorial_state", "is_archived")


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ("email", "subject", "status", "created_at")
    list_filter = ("status",)
    raw_id_fields = ("user",)
