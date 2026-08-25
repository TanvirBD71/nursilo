"""Library staff management — storage keys are metadata, not authorization."""
from __future__ import annotations

from django.db import transaction
from django.db.models import Q

from apps.audit.services import AuditService
from apps.cms.services import EditorialWorkflowService
from apps.common.choices import BookFormat, EditorialState, LocaleCode
from apps.library.models import Book, BookAsset, BookTranslation
from apps.rbac.services import AccessControlService
from apps.staff.services.pagination import paginate_queryset


class LibraryStaffError(Exception):
    def __init__(self, message: str, *, code: str = "library_error"):
        super().__init__(message)
        self.code = code


class LibraryStaffService:
    @classmethod
    def list_books(cls, actor, *, q: str = "", state: str = "", page=1):
        cls._require_manage(actor)
        qs = Book.objects.all().order_by("-updated_at")
        if state:
            qs = qs.filter(editorial_state=state)
        if q:
            qs = qs.filter(
                Q(translations__title__icontains=q)
                | Q(author_name__icontains=q)
                | Q(id__icontains=q)
            ).distinct()
        return paginate_queryset(qs.prefetch_related("translations", "assets"), page=page)

    @classmethod
    def get_book(cls, actor, book_id) -> Book:
        cls._require_manage(actor)
        try:
            return Book.objects.prefetch_related("translations", "assets").get(pk=book_id)
        except Book.DoesNotExist as exc:
            raise LibraryStaffError("Not found.", code="not_found") from exc

    @classmethod
    @transaction.atomic
    def create_book(
        cls,
        *,
        actor,
        title_en: str,
        title_bn: str = "",
        blurb: str = "",
        author_name: str = "",
        category: str = "",
        is_premium: bool = False,
        cover_storage_key: str = "",
    ) -> Book:
        cls._require_manage(actor)
        book = Book.objects.create(
            author_name=(author_name or "").strip(),
            category=(category or "").strip(),
            is_premium=bool(is_premium),
            cover_storage_key=(cover_storage_key or "").strip(),
            editorial_state=EditorialState.DRAFT,
            created_by=actor,
            updated_by=actor,
        )
        BookTranslation.objects.create(
            book=book,
            locale=LocaleCode.EN,
            title=(title_en or "").strip() or "Untitled",
            blurb=blurb or "",
        )
        if title_bn:
            BookTranslation.objects.create(
                book=book,
                locale=LocaleCode.BN,
                title=title_bn.strip(),
                blurb=blurb or "",
            )
        AuditService.record(
            action="book_created",
            actor_user=actor,
            target_type="book",
            target_id=str(book.id),
            metadata={"title": title_en, "is_premium": book.is_premium},
        )
        return book

    @classmethod
    @transaction.atomic
    def update_book(
        cls,
        *,
        actor,
        book: Book,
        title_en: str,
        title_bn: str = "",
        blurb: str = "",
        author_name: str = "",
        category: str = "",
        is_premium: bool = False,
        cover_storage_key: str = "",
    ) -> Book:
        cls._require_manage(actor)
        book.author_name = (author_name or "").strip()
        book.category = (category or "").strip()
        book.is_premium = bool(is_premium)
        book.cover_storage_key = (cover_storage_key or "").strip()
        book.updated_by = actor
        book.version_number = int(book.version_number or 1) + 1
        book.save(
            update_fields=[
                "author_name",
                "category",
                "is_premium",
                "cover_storage_key",
                "updated_by",
                "version_number",
                "updated_at",
            ]
        )
        BookTranslation.objects.update_or_create(
            book=book,
            locale=LocaleCode.EN,
            defaults={"title": (title_en or "").strip() or "Untitled", "blurb": blurb or ""},
        )
        if title_bn:
            BookTranslation.objects.update_or_create(
                book=book,
                locale=LocaleCode.BN,
                defaults={"title": title_bn.strip(), "blurb": blurb or ""},
            )
        AuditService.record(
            action="book_edited",
            actor_user=actor,
            target_type="book",
            target_id=str(book.id),
            metadata={"title": title_en},
        )
        return book

    @classmethod
    @transaction.atomic
    def add_asset(
        cls,
        *,
        actor,
        book: Book,
        format: str,
        storage_key: str,
        sort_order: int = 0,
    ) -> BookAsset:
        cls._require_manage(actor)
        if format not in {c.value for c in BookFormat}:
            raise LibraryStaffError("Invalid format.", code="validation")
        storage_key = (storage_key or "").strip()
        if not storage_key:
            raise LibraryStaffError("Storage key required.", code="validation")
        # Storage key is a content reference only — never an auth token.
        asset = BookAsset.objects.create(
            book=book,
            format=format,
            storage_key=storage_key,
            sort_order=int(sort_order or 0),
        )
        AuditService.record(
            action="book_asset_added",
            actor_user=actor,
            target_type="book",
            target_id=str(book.id),
            metadata={"format": format},
        )
        return asset

    @classmethod
    def workflow(cls, *, actor, book_id, action: str, notes: str = ""):
        book = cls.get_book(actor, book_id)
        return EditorialWorkflowService.transition(
            obj=book,
            action=action,
            actor=actor,
            domain="content",
            target_type="book",
            notes=notes,
        )

    @classmethod
    def title_for(cls, book: Book) -> str:
        tr = book.translations.filter(locale=LocaleCode.EN).first() or book.translations.first()
        return getattr(tr, "title", None) or str(book.pk)

    @classmethod
    def _require_manage(cls, actor):
        if AccessControlService.has_permission(actor, "library.manage"):
            return
        if AccessControlService.has_permission(actor, "content.create_draft"):
            return
        raise PermissionError("Permission denied.")
