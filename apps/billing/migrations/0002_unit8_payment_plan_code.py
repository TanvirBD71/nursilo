from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("billing", "0001_unit1_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="paymenttransaction",
            name="plan_code",
            field=models.CharField(db_index=True, default="", max_length=64),
        ),
    ]
