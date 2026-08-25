"""Staff list pagination helper."""
from __future__ import annotations

from django.core.paginator import Paginator


def paginate_queryset(qs, *, page: int | str | None = 1, per_page: int = 25):
    paginator = Paginator(qs, per_page)
    try:
        page_number = int(page or 1)
    except (TypeError, ValueError):
        page_number = 1
    return paginator.get_page(page_number)
