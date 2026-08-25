"""
Load the transcribed March 2025 BNMC items through the UNIT-11/12 Excel importer.

Does not parse PDFs at runtime. Re-runs are idempotent on question_code.
Refuses outside DEBUG. Never invents answer keys or blueprint mappings.
"""
from __future__ import annotations

import io

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.assessment.data.bnmc_march_2025 import REAL_ROWS, SKIPPED, SOURCE_NAME
from apps.assessment.models import ExamBlueprint, Question
from apps.assessment.services.import_questions import (
    OPTIONAL_COLUMNS,
    REQUIRED_COLUMNS,
    QuestionImportService,
)
from apps.common.choices import RoleCode
from apps.rbac.models import RoleAssignment


class Command(BaseCommand):
    help = "Import transcribed BNMC March 2025 questions via the Excel pipeline."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview only; do not write questions.",
        )

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("Refusing to import real exam items outside DEBUG.")
        from openpyxl import Workbook

        header = list(REQUIRED_COLUMNS) + [
            c for c in OPTIONAL_COLUMNS if c not in REQUIRED_COLUMNS
        ]
        wb = Workbook()
        ws = wb.active
        ws.append(header)
        for row in REAL_ROWS:
            ws.append([row.get(col, "") for col in header])
        buf = io.BytesIO()
        wb.save(buf)
        payload = buf.getvalue()

        blueprint = ExamBlueprint.objects.filter(code="BNMC_2018").first()
        preview = QuestionImportService.preview(io.BytesIO(payload), blueprint=blueprint)
        self.stdout.write(
            f"Preview: total={preview.total} valid={preview.valid} "
            f"duplicate={preview.duplicate} invalid={preview.invalid} "
            f"needs_review={preview.needs_review}"
        )
        if preview.errors:
            for err in preview.errors[:20]:
                self.stdout.write(self.style.ERROR(err))
            raise CommandError("Workbook invalid — no questions imported.")
        if options["dry_run"]:
            self.stdout.write("Dry run: no writes.")
            self.stdout.write("Skipped source items: " + "; ".join(SKIPPED))
            return
        actor = (
            RoleAssignment.objects.filter(
                role__code__in=[RoleCode.ADMIN, RoleCode.SUPER_ADMIN, RoleCode.EDITOR]
            )
            .select_related("user")
            .first()
        )
        if actor is None or actor.user is None:
            raise CommandError("No staff actor available to own the import.")
        report = QuestionImportService.commit(
            io.BytesIO(payload),
            actor=actor.user,
            blueprint=blueprint,
            filename="bnmc-march-2025-transcribed.xlsx",
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Imported {report.created}; skipped {report.skipped_duplicate} "
                f"duplicate(s); needs_review={report.needs_review}."
            )
        )
        self.stdout.write(f"Source: {SOURCE_NAME}")
        self.stdout.write("Skipped source items: " + "; ".join(SKIPPED))
        self.stdout.write(
            f"Bank now has {Question.objects.filter(question_code__startswith='BNMC-2025-03-').count()} "
            "BNMC-2025-03 codes."
        )
