"""UNIT-10 production hardening — email-verified checkout, settings, media safety."""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
import uuid
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from django.db import connection
from django.test import Client, RequestFactory, SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.accounts.policy import REAUTH_AT_SESSION_KEY
from apps.accounts.services import AccountService
from apps.billing.exceptions import EmailVerificationRequired
from apps.billing.models import PaymentTransaction, Subscription
from apps.billing.services import BillingService
from apps.billing.services.providers.fake import FakePaymentProvider
from apps.common.choices import PaymentStatus, SubscriptionState
from apps.entitlements.services import EntitlementService
from config import urls as root_urls
from config.settings.production_guards import (
    validate_csrf_trusted_origins,
    validate_production_hosts,
    validate_production_secret,
)


STRONG_PASSWORD = "Str0ng-Pass!Unit10"


def setUpModule():
    try:
        connection.ensure_connection()
    except Exception as exc:  # pragma: no cover
        raise unittest.SkipTest(f"PostgreSQL unavailable for UNIT-10: {exc}") from exc


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"],
    NURSILO_PAYMENT_PROVIDER="fake",
    NURSILO_PLAN_ANNUAL_PREMIUM_AMOUNT="199",
    NURSILO_PLAN_ANNUAL_PREMIUM_DURATION_DAYS=365,
)
class Unit10EmailVerifiedCheckoutTests(TestCase):
    def setUp(self):
        FakePaymentProvider.reset()
        self.factory = RequestFactory()
        suffix = uuid.uuid4().hex[:8]
        self.unverified, _ = AccountService.register(
            email=f"uv10-{suffix}@example.com", password=STRONG_PASSWORD
        )
        self.verified, _ = AccountService.register(
            email=f"ok10-{suffix}@example.com", password=STRONG_PASSWORD
        )
        AccountService.mark_email_verified(self.verified)
        self.client = Client()
        self.client.post(
            reverse("accounts:login"),
            {
                "email": f"ok10-{suffix}@example.com",
                "password": STRONG_PASSWORD,
                "next": "",
            },
        )

    def _request(self, user):
        req = self.factory.get("/billing/checkout/")
        req.user = user
        req.META["HTTP_HOST"] = "testserver"
        return req

    def _fresh_reauth(self, client):
        session = client.session
        session[REAUTH_AT_SESSION_KEY] = timezone.now().isoformat()
        session.save()

    def test_verified_user_can_start_checkout(self):
        payment, url = BillingService.start_checkout(
            user=self.verified,
            plan_code="annual_premium",
            request=self._request(self.verified),
        )
        self.assertEqual(payment.status, PaymentStatus.INITIATED)
        self.assertEqual(payment.amount, Decimal("199"))
        self.assertTrue(url.startswith("https://fake-gateway.test/"))
        self.assertFalse(EntitlementService.is_premium(self.verified))

    def test_unverified_user_blocked_from_start_checkout(self):
        before = PaymentTransaction.objects.filter(user=self.unverified).count()
        with self.assertRaises(EmailVerificationRequired):
            BillingService.start_checkout(
                user=self.unverified,
                plan_code="annual_premium",
                request=self._request(self.unverified),
            )
        self.assertEqual(
            PaymentTransaction.objects.filter(user=self.unverified).count(), before
        )
        self.assertFalse(EntitlementService.is_premium(self.unverified))
        sub = Subscription.objects.filter(user=self.unverified).first()
        if sub is not None:
            self.assertNotEqual(sub.state, SubscriptionState.PREMIUM_ACTIVE)

    def test_unverified_checkout_view_redirects_to_verify_path(self):
        client = Client()
        client.post(
            reverse("accounts:login"),
            {
                "email": self.unverified.email,
                "password": STRONG_PASSWORD,
                "next": "",
            },
        )
        self._fresh_reauth(client)
        resp = client.get(reverse("billing:checkout"))
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, reverse("accounts:resend_verification"))
        self.assertEqual(
            PaymentTransaction.objects.filter(user=self.unverified).count(), 0
        )
        self.assertFalse(EntitlementService.is_premium(self.unverified))

    def test_unverified_cannot_fabricate_premium_via_checkout(self):
        with self.assertRaises(EmailVerificationRequired):
            BillingService.start_checkout(
                user=self.unverified,
                plan_code="annual_premium",
                request=self._request(self.unverified),
            )
        self.assertFalse(EntitlementService.is_premium(self.unverified))
        self.assertFalse(
            PaymentTransaction.objects.filter(
                user=self.unverified, status=PaymentStatus.CONFIRMED
            ).exists()
        )


class Unit10ProductionSettingsHardeningTests(SimpleTestCase):
    databases = []

    def test_empty_allowed_hosts_refused(self):
        with self.assertRaises(ImproperlyConfigured) as ctx:
            validate_production_hosts([])
        self.assertIn("ALLOWED_HOSTS", str(ctx.exception))

    def test_malformed_csrf_origin_refused(self):
        with self.assertRaises(ImproperlyConfigured) as ctx:
            validate_csrf_trusted_origins(["app.example.test"])
        self.assertIn("CSRF_TRUSTED_ORIGINS", str(ctx.exception))

    def test_weak_secret_refused_without_leaking_value(self):
        weak = "insecure-unit0-dev-only-change-me"
        with self.assertRaises(ImproperlyConfigured) as ctx:
            validate_production_secret(weak)
        self.assertNotIn(weak, str(ctx.exception))

    def test_static_root_not_source_static(self):
        self.assertTrue(hasattr(settings, "STATIC_ROOT"))
        self.assertNotEqual(
            Path(settings.STATIC_ROOT).resolve(),
            (Path(settings.BASE_DIR) / "static").resolve(),
        )

    def test_production_module_imports_under_strong_env(self):
        strong = "prod-" + ("Z9y8X7w6V5u4T3s2R1q0" * 3)
        script = (
            "import os\n"
            f"os.environ['SECRET_KEY'] = {strong!r}\n"
            "os.environ['ALLOWED_HOSTS'] = 'app.example.test'\n"
            "os.environ['CSRF_TRUSTED_ORIGINS'] = 'https://app.example.test'\n"
            "import config.settings.production as prod\n"
            "assert prod.DEBUG is False\n"
            "assert hasattr(prod, 'LOGGING')\n"
            "print('OK')\n"
        )
        env = os.environ.copy()
        env["SECRET_KEY"] = strong
        env["ALLOWED_HOSTS"] = "app.example.test"
        env["CSRF_TRUSTED_ORIGINS"] = "https://app.example.test"
        result = subprocess.run(
            [sys.executable, "-c", script],
            cwd=str(Path(__file__).resolve().parent.parent),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("OK", result.stdout)


class Unit10MediaAndStaticSafetyTests(SimpleTestCase):
    databases = []

    def test_no_public_media_catchall_in_urlpatterns(self):
        source = Path(root_urls.__file__).read_text(encoding="utf-8")
        self.assertNotIn("document_root=settings.MEDIA_ROOT", source)
        self.assertNotIn("static(settings.MEDIA_URL", source)

    def test_collectstatic_writes_outside_source_static(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "collected"
            with override_settings(
                STATIC_ROOT=str(dest),
                STATICFILES_DIRS=[settings.BASE_DIR / "static"],
            ):
                call_command("collectstatic", "--noinput", verbosity=0)
            self.assertTrue(dest.exists())
            self.assertNotEqual(
                dest.resolve(),
                (Path(settings.BASE_DIR) / "static").resolve(),
            )
            source_static = Path(settings.BASE_DIR) / "static"
            self.assertTrue(source_static.exists())


class Unit10ErrorHandlerWiringTests(SimpleTestCase):
    databases = []

    def test_handler400_wired(self):
        self.assertEqual(root_urls.handler400, "config.errors.bad_request")
        self.assertEqual(root_urls.handler403, "config.errors.permission_denied")
        self.assertEqual(root_urls.handler404, "config.errors.page_not_found")
        self.assertEqual(root_urls.handler500, "config.errors.server_error")
