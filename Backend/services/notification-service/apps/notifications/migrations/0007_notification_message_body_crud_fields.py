from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("notifications", "0006_rename_notifications_inbox_event_type_idx_notificatio_event_t_837d3d_idx_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="notificationmessage",
            name="title",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AddField(
            model_name="notificationmessage",
            name="body",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="notificationmessage",
            name="metadata",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="notificationmessage",
            name="created_by_user_id",
            field=models.UUIDField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="notificationmessage",
            name="is_deleted",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="notificationmessage",
            name="deleted_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="notificationmessage",
            name="deleted_by_user_id",
            field=models.UUIDField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="notificationmessage",
            name="recipient",
            field=models.CharField(max_length=128),
        ),
        migrations.AlterField(
            model_name="notificationmessage",
            name="recipient_masked",
            field=models.CharField(max_length=128),
        ),
    ]
