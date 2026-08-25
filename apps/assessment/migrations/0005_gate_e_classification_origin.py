from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("assessment", "0004_questionimportbatch"),
    ]

    operations = [
        migrations.AddField(
            model_name="question",
            name="classification_origin",
            field=models.CharField(
                blank=True,
                db_index=True,
                default="",
                help_text=(
                    "suggested = blueprint assistance accepted (not authority); "
                    "approved = staff confirmed. Blank = import/legacy/unspecified."
                ),
                max_length=16,
            ),
        ),
    ]
