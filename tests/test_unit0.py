"""UNIT-0 foundation tests — no domain features."""
import json
import os
import subprocess
import sys
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase, Client
from django.urls import resolve

from config.settings.production_guards import (
    validate_csrf_trusted_origins,
    validate_production_hosts,
    validate_production_secret,
)


class SettingsLoadTests(SimpleTestCase):
    databases = []

    def test_development_settings_load(self):
        from django.conf import settings

        self.assertTrue(hasattr(settings, "SECRET_KEY"))
        self.assertIn("apps.accounts", settings.INSTALLED_APPS)
        self.assertIn("apps.platform", settings.INSTALLED_APPS)
        self.assertEqual(settings.DATABASES["default"]["ENGINE"], "django.db.backends.postgresql")
        self.assertEqual(settings.AUTH_USER_MODEL, "accounts.UserAccount")

    def test_production_secret_validators_fail_closed(self):
        with self.assertRaises(ImproperlyConfigured) as ctx:
            validate_production_secret("insecure-unit0-dev-only-change-me")
        message = str(ctx.exception).lower()
        self.assertIn("secret_key", message)
        self.assertNotIn("insecure-unit0", message)

        with self.assertRaises(ImproperlyConfigured):
            validate_production_secret("")
        with self.assertRaises(ImproperlyConfigured):
            validate_production_secret("change-me-to-a-long-random-value")
        with self.assertRaises(ImproperlyConfigured):
            validate_production_hosts([])
        with self.assertRaises(ImproperlyConfigured):
            validate_csrf_trusted_origins(["app.example.test"])

    def test_production_settings_load_with_strong_secret_subprocess(self):
        strong = "prod-" + ("A1b2C3d4E5f6G7h8I9j0" * 3)
        script = (
            "import os\n"
            f"os.environ['SECRET_KEY'] = {strong!r}\n"
            "os.environ['ALLOWED_HOSTS'] = 'app.example.test'\n"
            "os.environ['CSRF_TRUSTED_ORIGINS'] = 'https://app.example.test'\n"
            "os.environ['STATIC_ROOT'] = ''\n"
            "os.environ['MEDIA_ROOT'] = ''\n"
            "import config.settings.production as prod\n"
            "assert prod.DEBUG is False\n"
            "assert prod.DATABASES['default']['ENGINE'] == 'django.db.backends.postgresql'\n"
            f"assert prod.SECRET_KEY == {strong!r}\n"
            "assert prod.ALLOWED_HOSTS == ['app.example.test']\n"
            "assert prod.CSRF_TRUSTED_ORIGINS == ['https://app.example.test']\n"
            "assert prod.SECURE_SSL_REDIRECT is False\n"
            "assert prod.SECURE_HSTS_SECONDS == 0\n"
            "assert 'LOGGING' in dir(prod)\n"
            "from pathlib import Path\n"
            "assert Path(prod.STATIC_ROOT).resolve() != (Path(prod.BASE_DIR) / 'static').resolve()\n"
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


class HealthEndpointTests(SimpleTestCase):
    databases = []

    def test_health_url_resolves(self):
        match = resolve("/health/")
        self.assertEqual(match.url_name, "health")

    def test_health_returns_200(self):
        client = Client()
        response = client.get("/health/")
        self.assertEqual(response.status_code, 200)

    def test_health_does_not_leak_secrets(self):
        client = Client()
        response = client.get("/health/")
        body = response.content.decode("utf-8").lower()
        data = json.loads(response.content)
        self.assertEqual(data.get("status"), "ok")
        forbidden = [
            "secret",
            "password",
            "traceback",
            "exception",
            "c:\\",
            "g:\\",
            "/home/",
            "db_password",
            "allowed_hosts",
        ]
        for token in forbidden:
            self.assertNotIn(token, body)
