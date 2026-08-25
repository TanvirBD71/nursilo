"""Seed identifiable Nursilo Demo content into nursilo_dev (development only)."""
from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from apps.platform.demo_seed import (
    DEMO_EMAILS,
    DEMO_PASSWORD_ENV,
    DemoSeedError,
    seed_demo_data,
)


class Command(BaseCommand):
    help = (
        "Idempotent development seed for Nursilo Demo learning/practice/exam/"
        "library content and demo accounts. Refuses outside DEBUG + nursilo_dev."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--show-accounts",
            action="store_true",
            help="Print demo account emails only (never passwords).",
        )

    def handle(self, *args, **options):
        try:
            report = seed_demo_data()
        except DemoSeedError as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(self.style.SUCCESS("Nursilo demo seed completed."))
        for line in report.as_lines():
            self.stdout.write(f"  {line}")
        if options.get("show_accounts"):
            self.stdout.write("Demo accounts (emails only):")
            for email in DEMO_EMAILS:
                self.stdout.write(f"  - {email}")
            self.stdout.write(
                f"Password: set via {DEMO_PASSWORD_ENV} or local-only fallback "
                "(value not printed)."
            )
