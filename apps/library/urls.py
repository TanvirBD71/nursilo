"""Library domain URL routes (UNIT-7)."""
from django.urls import path

from apps.library import views

app_name = "library"

urlpatterns = [
    path("", views.catalog, name="catalog"),
    path("bookmarks/", views.bookmarks, name="bookmarks"),
    path("downloads/", views.downloads, name="downloads"),
    path("books/<uuid:book_id>/", views.detail, name="detail"),
    path("books/<uuid:book_id>/read/", views.reader, name="reader"),
    path("books/<uuid:book_id>/bookmark/", views.bookmark_toggle, name="bookmark_toggle"),
    path("books/<uuid:book_id>/cover/", views.cover, name="cover"),
    path("assets/<uuid:asset_id>/stream/", views.asset_stream, name="asset_stream"),
    path("assets/<uuid:asset_id>/download/", views.asset_download, name="asset_download"),
]
