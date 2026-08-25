"""Root URL configuration for Nursilo."""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from apps.portal.views import home_entry
from config.health import health

urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", health, name="health"),
    path("accounts/", include("apps.accounts.urls")),
    path("portal/", include("apps.portal.urls")),
    path("staff/", include("apps.staff.urls")),
    path("learn/", include("apps.learning.urls")),
    path("practice/", include("apps.assessment.urls")),
    path("exams/", include("apps.assessment.exam_urls")),
    path("library/", include("apps.library.urls")),
    path("billing/", include("apps.billing.urls")),
    path("", home_entry, name="home"),
]

handler400 = "config.errors.bad_request"
handler403 = "config.errors.permission_denied"
handler404 = "config.errors.page_not_found"
handler500 = "config.errors.server_error"

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.BASE_DIR / "static")
# Intentionally no public MEDIA catch-all: protected books use mediated library views.
# Ops must not Alias MEDIA_ROOT publicly for premium/protected assets (cPanel mapping).
