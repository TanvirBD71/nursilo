"""Remove identifiable Nursilo Demo content from nursilo_dev (development only)."""
from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from apps.platform.demo_seed import DemoSeedError, cleanup_demo_data


class Command(BaseCommand):
    help = (
        "Development-only cleanup of Nursilo Demo records. Does not delete "
        "non-demo content. Refuses outside DEBUG + nursilo_dev."
    )

    def handle(self, *args, **options):
        try:
            report = cleanup_demo_data()
        except DemoSeedError as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(self.style.SUCCESS("Nursilo demo cleanup completed."))
        for line in report.as_lines():
            self.stdout.write(f"  {line}")
