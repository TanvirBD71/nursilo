import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("assessment", "0003_seed_bnmc_blueprint"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="QuestionImportBatch",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("filename", models.CharField(blank=True, default="", max_length=255)),
                (
                    "status",
                    models.CharField(
                        db_index=True, default="committed", max_length=32
                    ),
                ),
                ("total_rows", models.PositiveIntegerField(default=0)),
                ("created_count", models.PositiveIntegerField(default=0)),
                ("skipped_duplicate", models.PositiveIntegerField(default=0)),
                ("invalid_count", models.PositiveIntegerField(default=0)),
                ("needs_review_count", models.PositiveIntegerField(default=0)),
                ("type_counts", models.JSONField(blank=True, default=dict)),
                ("blueprint_counts", models.JSONField(blank=True, default=dict)),
                ("cognitive_counts", models.JSONField(blank=True, default=dict)),
                ("created_codes", models.JSONField(blank=True, default=list)),
                ("skipped_codes", models.JSONField(blank=True, default=list)),
                ("errors", models.JSONField(blank=True, default=list)),
                ("warnings", models.JSONField(blank=True, default=list)),
                ("report", models.JSONField(blank=True, default=dict)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="question_import_batches",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "question_import_batches",
            },
        ),
        migrations.AddIndex(
            model_name="questionimportbatch",
            index=models.Index(
                fields=["-created_at"], name="question_im_created_8ce856_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="questionimportbatch",
            index=models.Index(
                fields=["status", "-created_at"],
                name="question_im_status_89a71e_idx",
            ),
        ),
    ]
