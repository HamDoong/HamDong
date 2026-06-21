from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("identity", "0006_fix_legacy_phone_nullable"),
    ]

    operations = [
        migrations.AlterField(
            model_name="user",
            name="legacy_phone_number",
            field=models.CharField(
                blank=True,
                max_length=20,
                null=True,
                unique=True,
            ),
        ),
    ]
