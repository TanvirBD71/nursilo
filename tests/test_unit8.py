"""UNIT-8 Billing, Subscription & Entitlement tests."""
from __future__ import annotations

import unittest
import uuid
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

from django.db import connection
from django.test import Client, RequestFactory, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.accounts.policy import REAUTH_AT_SESSION_KEY
from apps.accounts.services import AccountService
from apps.billing.exceptions import PaymentForbidden, PaymentNotConfigured
from apps.billing.models import PaymentTransaction, Subscription
from apps.billing.plans import PlanCatalog
from apps.billing.services import BillingService
from apps.billing.services.providers.fake import FakePaymentProvider
from apps.billing.services.providers.sslcommerz import SSLCommerzSandboxAdapter, _md5_hex
from apps.common.choices import (
    BookFormat,
    EditorialState,
    LocaleCode,
    PaymentStatus,
    SubscriptionState,
)
from apps.entitlements.models import EntitlementGrant
from apps.entitlements.services import EntitlementService
from apps.library.models import Book, BookAsset, BookTranslation
from apps.library.services import LibraryAccessService


STRONG_PASSWORD = "Str0ng-Pass!Unit8"


def setUpModule():
    try:
        connection.ensure_connection()
    except Exception as exc:  # pragma: no cover
        raise unittest.SkipTest(f"PostgreSQL unavailable for UNIT-8: {exc}") from exc


def _publish(book: Book, **kwargs) -> Book:
    book.editorial_state = EditorialState.PUBLISHED
    book.is_archived = False
    for key, value in kwargs.items():
        setattr(book, key, value)
    book.save()
    return book


def _write_media(rel_key: str, content: str | bytes) -> str:
    from django.conf import settings

    path = Path(settings.MEDIA_ROOT) / rel_key
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, bytes):
        path.write_bytes(content)
    else:
        path.write_text(content, encoding="utf-8")
    return rel_key


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"],
    NURSILO_PAYMENT_PROVIDER="fake",
    NURSILO_PLAN_ANNUAL_PREMIUM_AMOUNT="199",
    NURSILO_PLAN_ANNUAL_PREMIUM_DURATION_DAYS=365,
    SSLCOMMERZ_STORE_ID="",
    SSLCOMMERZ_STORE_PASSWD="",
)
class Unit8PlanCatalogTests(TestCase):
    def test_authoritative_annual_premium_plan(self):
        plan = PlanCatalog.default_plan()
        self.assertEqual(plan.code, "annual_premium")
        self.assertEqual(plan.name, "Annual Premium")
        self.assertEqual(plan.amount, Decimal("199"))
        self.assertEqual(plan.currency, "BDT")
        self.assertEqual(plan.duration_days, 365)
        self.assertEqual(len(PlanCatalog.all_active()), 1)

    def test_pricing_is_plan_data_driven_not_workflow_literal(self):
        with self.settings(NURSILO_PLAN_ANNUAL_PREMIUM_AMOUNT="250"):
            self.assertEqual(PlanCatalog.default_plan().amount, Decimal("250"))


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"],
    NURSILO_PAYMENT_PROVIDER="fake",
)
class Unit8EntitlementTests(TestCase):
    def setUp(self):
        FakePaymentProvider.reset()
        self.user, _ = AccountService.register(
            email="ent8@example.com", password=STRONG_PASSWORD
        )

    def test_free_default_not_premium(self):
        snap = EntitlementService.snapshot(self.user)
        self.assertEqual(snap.tier, "free")
        self.assertFalse(snap.is_premium)

    def test_pending_not_premium(self):
        Subscription.objects.create(
            user=self.user, state=SubscriptionState.PENDING_PAYMENT
        )
        snap = EntitlementService.snapshot(self.user)
        self.assertEqual(snap.tier, "pending")
        self.assertFalse(EntitlementService.is_premium(self.user))

    def test_active_premium_allowed(self):
        Subscription.objects.create(
            user=self.user,
            state=SubscriptionState.PREMIUM_ACTIVE,
            premium_expires_at=timezone.now() + timedelta(days=30),
        )
        self.assertTrue(EntitlementService.is_premium(self.user))
        self.assertEqual(EntitlementService.snapshot(self.user).tier, "active")

    def test_expired_by_time_flips_and_denies(self):
        Subscription.objects.create(
            user=self.user,
            state=SubscriptionState.PREMIUM_ACTIVE,
            premium_expires_at=timezone.now() - timedelta(hours=1),
        )
        self.assertFalse(EntitlementService.is_premium(self.user))
        sub = Subscription.objects.get(user=self.user)
        self.assertEqual(sub.state, SubscriptionState.EXPIRED)
        self.assertEqual(EntitlementService.snapshot(self.user).tier, "expired")

    def test_revoked_denies(self):
        Subscription.objects.create(user=self.user, state=SubscriptionState.REVOKED)
        self.assertFalse(EntitlementService.is_premium(self.user))


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"],
    NURSILO_PAYMENT_PROVIDER="fake",
    NURSILO_PLAN_ANNUAL_PREMIUM_AMOUNT="199",
    NURSILO_PLAN_ANNUAL_PREMIUM_DURATION_DAYS=365,
)
class Unit8CheckoutAndActivationTests(TestCase):
    def setUp(self):
        FakePaymentProvider.reset()
        self.factory = RequestFactory()
        self.user, _ = AccountService.register(
            email="pay8@example.com", password=STRONG_PASSWORD
        )
        AccountService.mark_email_verified(self.user)
        self.client = Client()
        self.client.post(
            reverse("accounts:login"),
            {"email": "pay8@example.com", "password": STRONG_PASSWORD, "next": ""},
        )

    def _request(self):
        req = self.factory.get("/billing/checkout/")
        req.user = self.user
        req.META["HTTP_HOST"] = "testserver"
        return req

    def _fresh_reauth(self):
        session = self.client.session
        session[REAUTH_AT_SESSION_KEY] = timezone.now().isoformat()
        session.save()

    def test_checkout_requires_auth(self):
        anon = Client()
        resp = anon.get(reverse("billing:checkout"))
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse("accounts:login"), resp.url)

    def test_checkout_requires_reauth(self):
        resp = self.client.get(reverse("billing:checkout"))
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse("accounts:reauth"), resp.url)

    def test_start_checkout_creates_pending_txn_and_gateway_url(self):
        payment, url = BillingService.start_checkout(
            user=self.user,
            plan_code="annual_premium",
            request=self._request(),
        )
        self.assertEqual(payment.status, PaymentStatus.INITIATED)
        self.assertEqual(payment.amount, Decimal("199.00"))
        self.assertEqual(payment.plan_code, "annual_premium")
        self.assertTrue(url.startswith("https://fake-gateway.test/"))
        sub = Subscription.objects.get(user=self.user)
        self.assertEqual(sub.state, SubscriptionState.PENDING_PAYMENT)
        self.assertFalse(EntitlementService.is_premium(self.user))

    def test_unconfigured_provider_blocks_checkout(self):
        FakePaymentProvider.configured = False
        with self.assertRaises(PaymentNotConfigured):
            BillingService.start_checkout(
                user=self.user,
                plan_code="annual_premium",
                request=self._request(),
            )

    def test_verify_activates_premium_and_sets_expiry(self):
        payment, _url = BillingService.start_checkout(
            user=self.user,
            plan_code="annual_premium",
            request=self._request(),
        )
        before = timezone.now()
        confirmed = BillingService.handle_provider_callback(
            {
                "tran_id": payment.gateway_ref,
                "val_id": "VAL-1",
                "amount": "199.00",
                "currency": "BDT",
                "status": "VALID",
                "value_a": str(self.user.id),
                "value_b": "annual_premium",
            },
            require_hash=False,
        )
        self.assertEqual(confirmed.status, PaymentStatus.CONFIRMED)
        self.assertTrue(EntitlementService.is_premium(self.user))
        sub = Subscription.objects.get(user=self.user)
        self.assertEqual(sub.state, SubscriptionState.PREMIUM_ACTIVE)
        self.assertIsNotNone(sub.premium_expires_at)
        self.assertGreaterEqual(
            sub.premium_expires_at, before + timedelta(days=364, hours=23)
        )
        self.assertTrue(
            EntitlementGrant.objects.filter(
                user=self.user, notes=f"payment:{payment.id}"
            ).exists()
        )

    def test_idempotent_confirmation_does_not_double_extend(self):
        payment, _ = BillingService.start_checkout(
            user=self.user,
            plan_code="annual_premium",
            request=self._request(),
        )
        payload = {
            "tran_id": payment.gateway_ref,
            "val_id": "VAL-IDEMP",
            "amount": "199.00",
            "currency": "BDT",
            "status": "VALID",
            "value_a": str(self.user.id),
            "value_b": "annual_premium",
        }
        first = BillingService.handle_provider_callback(payload, require_hash=False)
        expiry_1 = Subscription.objects.get(user=self.user).premium_expires_at
        second = BillingService.handle_provider_callback(payload, require_hash=False)
        expiry_2 = Subscription.objects.get(user=self.user).premium_expires_at
        self.assertEqual(first.id, second.id)
        self.assertEqual(expiry_1, expiry_2)
        self.assertEqual(
            EntitlementGrant.objects.filter(
                user=self.user, notes=f"payment:{payment.id}"
            ).count(),
            1,
        )
        self.assertEqual(
            PaymentTransaction.objects.filter(
                gateway_ref=payment.gateway_ref, status=PaymentStatus.CONFIRMED
            ).count(),
            1,
        )

    def test_renewal_extends_from_current_expiry_when_active(self):
        existing_expiry = timezone.now() + timedelta(days=10)
        Subscription.objects.create(
            user=self.user,
            state=SubscriptionState.PREMIUM_ACTIVE,
            premium_started_at=timezone.now() - timedelta(days=20),
            premium_expires_at=existing_expiry,
        )
        payment, _ = BillingService.start_checkout(
            user=self.user,
            plan_code="annual_premium",
            request=self._request(),
        )
        # Active premium must remain active during renewal checkout.
        self.assertEqual(
            Subscription.objects.get(user=self.user).state,
            SubscriptionState.PREMIUM_ACTIVE,
        )
        BillingService.handle_provider_callback(
            {
                "tran_id": payment.gateway_ref,
                "val_id": "VAL-REN",
                "amount": "199.00",
                "currency": "BDT",
                "value_a": str(self.user.id),
                "value_b": "annual_premium",
            },
            require_hash=False,
        )
        sub = Subscription.objects.get(user=self.user)
        expected = existing_expiry + timedelta(days=365)
        self.assertAlmostEqual(
            sub.premium_expires_at.timestamp(),
            expected.timestamp(),
            delta=2,
        )

    def test_renewal_from_expired_uses_server_now(self):
        Subscription.objects.create(
            user=self.user,
            state=SubscriptionState.EXPIRED,
            premium_expires_at=timezone.now() - timedelta(days=5),
        )
        payment, _ = BillingService.start_checkout(
            user=self.user,
            plan_code="annual_premium",
            request=self._request(),
        )
        before = timezone.now()
        BillingService.handle_provider_callback(
            {
                "tran_id": payment.gateway_ref,
                "val_id": "VAL-EXP",
                "amount": "199.00",
                "currency": "BDT",
                "value_a": str(self.user.id),
                "value_b": "annual_premium",
            },
            require_hash=False,
        )
        sub = Subscription.objects.get(user=self.user)
        self.assertGreaterEqual(sub.premium_expires_at, before + timedelta(days=364))

    def test_failed_payment_does_not_grant_premium(self):
        payment, _ = BillingService.start_checkout(
            user=self.user,
            plan_code="annual_premium",
            request=self._request(),
        )
        result = BillingService.handle_provider_callback(
            {
                "tran_id": payment.gateway_ref,
                "val_id": "VAL-FAIL",
                "amount": "199.00",
                "currency": "BDT",
                "status": "FAILED",
                "value_a": str(self.user.id),
                "value_b": "annual_premium",
            },
            require_hash=False,
            mark_failed_on_error=True,
        )
        self.assertEqual(result.status, PaymentStatus.FAILED)
        self.assertFalse(EntitlementService.is_premium(self.user))
        self.assertNotEqual(
            Subscription.objects.get(user=self.user).state,
            SubscriptionState.PREMIUM_ACTIVE,
        )

    def test_amount_mismatch_rejected(self):
        payment, _ = BillingService.start_checkout(
            user=self.user,
            plan_code="annual_premium",
            request=self._request(),
        )
        FakePaymentProvider.validate_mode = "amount_mismatch"
        from apps.billing.exceptions import PaymentVerificationFailed

        with self.assertRaises(PaymentVerificationFailed):
            BillingService.handle_provider_callback(
                {
                    "tran_id": payment.gateway_ref,
                    "val_id": "VAL-AMT",
                    "amount": "199.00",
                    "currency": "BDT",
                    "value_a": str(self.user.id),
                    "value_b": "annual_premium",
                },
                require_hash=False,
                mark_failed_on_error=True,
            )
        payment.refresh_from_db()
        # Amount mismatch raises inside transaction.atomic() after a tentative
        # fail write; the raise rolls that write back, so status stays initiated.
        # Payment is not confirmed and Premium is not granted.
        self.assertEqual(payment.status, PaymentStatus.INITIATED)
        self.assertFalse(EntitlementService.is_premium(self.user))

    def test_browser_return_without_val_id_stays_pending(self):
        payment, _ = BillingService.start_checkout(
            user=self.user,
            plan_code="annual_premium",
            request=self._request(),
        )
        result = BillingService.process_return({"tran_id": payment.gateway_ref})
        self.assertEqual(result.status, PaymentStatus.INITIATED)
        self.assertFalse(EntitlementService.is_premium(self.user))

    def test_checkout_post_redirects_to_gateway_after_reauth(self):
        self._fresh_reauth()
        token = self.client.cookies["csrftoken"].value
        resp = self.client.post(
            reverse("billing:checkout"),
            {"csrfmiddlewaretoken": token, "plan_code": "annual_premium"},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(resp.url.startswith("https://fake-gateway.test/"))

    def test_success_page_only_after_confirm(self):
        payment, _ = BillingService.start_checkout(
            user=self.user,
            plan_code="annual_premium",
            request=self._request(),
        )
        pending = self.client.get(
            reverse("billing:success", kwargs={"payment_id": payment.id})
        )
        self.assertEqual(pending.status_code, 302)
        self.assertEqual(
            pending.url, reverse("billing:pending", kwargs={"payment_id": payment.id})
        )
        BillingService.handle_provider_callback(
            {
                "tran_id": payment.gateway_ref,
                "val_id": "VAL-OK",
                "amount": "199.00",
                "currency": "BDT",
                "value_a": str(self.user.id),
                "value_b": "annual_premium",
            },
            require_hash=False,
        )
        ok = self.client.get(
            reverse("billing:success", kwargs={"payment_id": payment.id})
        )
        self.assertEqual(ok.status_code, 200)
        self.assertContains(ok, "Payment verified")

    def test_history_and_idor(self):
        payment, _ = BillingService.start_checkout(
            user=self.user,
            plan_code="annual_premium",
            request=self._request(),
        )
        hist = self.client.get(reverse("billing:history"))
        self.assertEqual(hist.status_code, 200)
        self.assertContains(hist, payment.gateway_ref)

        other, _ = AccountService.register(
            email="other8@example.com", password=STRONG_PASSWORD
        )
        with self.assertRaises(PaymentForbidden):
            BillingService.get_own_payment(other, payment.id)

        other_client = Client()
        other_client.post(
            reverse("accounts:login"),
            {"email": "other8@example.com", "password": STRONG_PASSWORD, "next": ""},
        )
        denied = other_client.get(
            reverse("billing:pending", kwargs={"payment_id": payment.id})
        )
        self.assertEqual(denied.status_code, 403)

    def test_pricing_page_honest_copy(self):
        resp = self.client.get(reverse("billing:pricing"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Annual Premium")
        self.assertContains(resp, "৳199")
        self.assertNotContains(resp, "Only today")
        self.assertNotContains(resp, "countdown")


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"],
    NURSILO_PAYMENT_PROVIDER="fake",
)
class Unit8LibraryEntitlementMatrixTests(TestCase):
    def setUp(self):
        FakePaymentProvider.reset()
        self.factory = RequestFactory()
        prefix = uuid.uuid4().hex[:8]
        self.free_user, _ = AccountService.register(
            email=f"free8-{prefix}@example.com", password=STRONG_PASSWORD
        )
        AccountService.mark_email_verified(self.free_user)
        html_key = _write_media(f"library/u8/{prefix}.html", "<p>premium body</p>")
        self.premium_book = _publish(
            Book.objects.create(
                category="Pharm",
                author_name="U8 Author",
                is_premium=True,
            )
        )
        BookTranslation.objects.create(
            book=self.premium_book,
            locale=LocaleCode.EN,
            title=f"U8 Premium {prefix}",
            blurb="blurb",
        )
        BookAsset.objects.create(
            book=self.premium_book,
            format=BookFormat.HTML,
            storage_key=html_key,
            sort_order=0,
        )

    def _request(self, user):
        req = self.factory.get("/billing/checkout/")
        req.user = user
        req.META["HTTP_HOST"] = "testserver"
        return req

    def test_matrix_free_pending_failed_active_expired(self):
        # FREE
        self.assertEqual(
            LibraryAccessService.access_state(self.free_user, self.premium_book),
            "locked",
        )
        self.assertFalse(
            LibraryAccessService.decide_read(self.free_user, self.premium_book).allowed
        )

        # PENDING
        Subscription.objects.create(
            user=self.free_user, state=SubscriptionState.PENDING_PAYMENT
        )
        self.assertFalse(EntitlementService.is_premium(self.free_user))
        self.assertFalse(
            LibraryAccessService.decide_read(self.free_user, self.premium_book).allowed
        )

        # FAILED payment path → free again
        Subscription.objects.filter(user=self.free_user).update(
            state=SubscriptionState.FREE
        )
        self.assertFalse(
            LibraryAccessService.decide_read(self.free_user, self.premium_book).allowed
        )

        # ACTIVE
        Subscription.objects.filter(user=self.free_user).update(
            state=SubscriptionState.PREMIUM_ACTIVE,
            premium_expires_at=timezone.now() + timedelta(days=30),
        )
        self.assertTrue(EntitlementService.is_premium(self.free_user))
        self.assertTrue(
            LibraryAccessService.decide_read(self.free_user, self.premium_book).allowed
        )
        self.assertEqual(
            LibraryAccessService.access_state(self.free_user, self.premium_book),
            "premium",
        )

        # EXPIRED
        Subscription.objects.filter(user=self.free_user).update(
            state=SubscriptionState.PREMIUM_ACTIVE,
            premium_expires_at=timezone.now() - timedelta(minutes=1),
        )
        self.assertFalse(EntitlementService.is_premium(self.free_user))
        self.assertFalse(
            LibraryAccessService.decide_read(self.free_user, self.premium_book).allowed
        )


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"],
)
class Unit8SSLCommerzAdapterUnitTests(TestCase):
    def test_hash_validation_matches_official_algorithm(self):
        store_pass = "qwerty"
        adapter = SSLCommerzSandboxAdapter(
            store_id="testbox", store_passwd=store_pass
        )
        payload = {
            "amount": "100",
            "bank_tran_id": "BANK1",
            "base_fair": "0.00",
            "card_brand": "VISA",
            "card_issuer": "Bank",
            "card_issuer_country": "Bangladesh",
            "card_issuer_country_code": "BD",
            "card_no": "425272XXXXXX3456",
            "card_type": "VISA",
            "currency": "BDT",
            "currency_amount": "100.00",
            "currency_rate": "1.0000",
            "currency_type": "BDT",
            "risk_level": "0",
            "risk_title": "Safe",
            "status": "VALID",
            "store_amount": "97",
            "store_id": "testbox",
            "tran_date": "2017-11-23 18:59:55",
            "tran_id": "5a16c68b23783",
            "val_id": "1711231900331kHP17lnrr9T8Gt",
            "value_a": "ref001_A",
            "value_b": "ref002_B",
            "value_c": "ref003_C",
            "value_d": "ref004_D",
        }
        keys = sorted(payload.keys())
        verify_key = ",".join(keys)
        parts = [f"{k}={payload[k]}" for k in keys]
        parts.append(f"store_passwd={_md5_hex(store_pass)}")
        payload["verify_key"] = verify_key
        payload["verify_sign"] = _md5_hex("&".join(parts))
        self.assertTrue(adapter.verify_callback_authenticity(payload))
        payload["verify_sign"] = "deadbeef"
        self.assertFalse(adapter.verify_callback_authenticity(payload))

    def test_adapter_not_configured_without_credentials(self):
        adapter = SSLCommerzSandboxAdapter(store_id="", store_passwd="")
        self.assertFalse(adapter.is_configured())


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"],
    NURSILO_PAYMENT_PROVIDER="fake",
)
class Unit8LivePgVerificationTests(TestCase):
    """Live PostgreSQL verification with transactional rollback (TestCase)."""

    def setUp(self):
        FakePaymentProvider.reset()
        self.factory = RequestFactory()
        self.user, _ = AccountService.register(
            email=f"live8-{uuid.uuid4().hex[:8]}@example.com",
            password=STRONG_PASSWORD,
        )
        AccountService.mark_email_verified(self.user)

    def test_payment_unique_gateway_ref_and_activation_row(self):
        req = self.factory.get("/")
        req.user = self.user
        req.META["HTTP_HOST"] = "testserver"
        payment, _ = BillingService.start_checkout(
            user=self.user, plan_code="annual_premium", request=req
        )
        BillingService.handle_provider_callback(
            {
                "tran_id": payment.gateway_ref,
                "val_id": "VAL-LIVE",
                "amount": "199.00",
                "currency": "BDT",
                "value_a": str(self.user.id),
                "value_b": "annual_premium",
            },
            require_hash=False,
        )
        self.assertEqual(
            PaymentTransaction.objects.filter(user=self.user).count(), 1
        )
        self.assertEqual(
            Subscription.objects.get(user=self.user).state,
            SubscriptionState.PREMIUM_ACTIVE,
        )
        # Duplicate gateway_ref must remain unique
        with self.assertRaises(Exception):
            PaymentTransaction.objects.create(
                user=self.user,
                subscription=Subscription.objects.get(user=self.user),
                gateway=payment.gateway,
                gateway_ref=payment.gateway_ref,
                plan_code=payment.plan_code,
                amount=payment.amount,
                currency=payment.currency,
            )
