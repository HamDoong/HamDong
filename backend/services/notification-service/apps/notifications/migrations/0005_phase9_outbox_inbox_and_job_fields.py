import uuid

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("notifications", "0004_rename_notification_event_i_064516_idx_notificatio_event_i_064516_idx_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="notificationmessage",
            name="recipient_user_id",
            field=models.UUIDField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name="notificationmessage",
            name="recipient_phone_number",
            field=models.CharField(max_length=32, null=True, blank=True),
        ),
        migrations.AddField(
            model_name="notificationmessage",
            name="last_error",
            field=models.TextField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name="notificationmessage",
            name="scheduled_at",
            field=models.DateTimeField(default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="notificationjob",
            name="notification_type",
            field=models.CharField(max_length=48, default="OTP"),
        ),
        migrations.AddField(
            model_name="notificationjob",
            name="recipient_user_id",
            field=models.UUIDField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name="notificationjob",
            name="recipient_phone_number",
            field=models.CharField(max_length=32, null=True, blank=True),
        ),
        migrations.AddField(
            model_name="notificationjob",
            name="scheduled_at",
            field=models.DateTimeField(default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="notificationjob",
            name="last_error",
            field=models.TextField(null=True, blank=True),
        ),
        migrations.CreateModel(
            name="OutboxMessage",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ("event_id", models.UUIDField(unique=True, db_index=True)),
                ("event_type", models.CharField(max_length=128)),
                ("event_version", models.PositiveIntegerField(default=1)),
                ("source_service", models.CharField(max_length=128)),
                ("exchange", models.CharField(max_length=128)),
                ("routing_key", models.CharField(max_length=128)),
                ("payload", models.JSONField(default=dict)),
                ("status", models.CharField(max_length=20, choices=[("PENDING", "Pending"), ("PUBLISHED", "Published"), ("FAILED", "Failed")], default="PENDING")),
                ("retry_count", models.PositiveIntegerField(default=0)),
                ("last_error", models.TextField(null=True, blank=True)),
                ("published_at", models.DateTimeField(null=True, blank=True)),
                ("available_at", models.DateTimeField(default=django.utils.timezone.now, db_index=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "notifications_outbox_messages"},
        ),
        migrations.CreateModel(
            name="InboxMessage",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ("event_id", models.UUIDField(unique=True, db_index=True)),
                ("event_type", models.CharField(max_length=128)),
                ("source_service", models.CharField(max_length=128)),
                ("routing_key", models.CharField(max_length=128)),
                ("payload", models.JSONField(default=dict)),
                ("status", models.CharField(max_length=20, choices=[("PROCESSED", "Processed"), ("FAILED", "Failed"), ("SKIPPED", "Skipped")], default="PROCESSED")),
                ("processed_at", models.DateTimeField(null=True, blank=True)),
                ("error_message", models.TextField(null=True, blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "notifications_inbox_messages"},
        ),
        migrations.AddIndex(model_name="outboxmessage", index=models.Index(fields=["status", "available_at"], name="notifications_outbox_status_available_idx")),
        migrations.AddIndex(model_name="outboxmessage", index=models.Index(fields=["routing_key"], name="notifications_outbox_routing_idx")),
        migrations.AddIndex(model_name="inboxmessage", index=models.Index(fields=["event_type"], name="notifications_inbox_event_type_idx")),
        migrations.AddIndex(model_name="inboxmessage", index=models.Index(fields=["routing_key"], name="notifications_inbox_routing_idx")),
    ]
