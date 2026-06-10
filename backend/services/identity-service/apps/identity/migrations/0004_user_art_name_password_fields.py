from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("identity", "0003_rename_identity_outbox_status_available_idx_identity_ou_status_ad1dbd_idx_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="art_name",
            field=models.CharField(blank=True, max_length=32, null=True, unique=True),
        ),
        migrations.AddField(
            model_name="user",
            name="password_changed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="user",
            name="password_hash",
            field=models.CharField(blank=True, max_length=128, null=True),
        ),
    ]
