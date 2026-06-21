import uuid

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("media_files", "0002_rename_media_groupm_group_id_0c2d9e_idx_media_group_group_i_f78165_idx_and_more"),
    ]

    operations = [
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
            options={"db_table": "media_outbox_messages"},
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
            options={"db_table": "media_inbox_messages"},
        ),
        migrations.AddIndex(model_name="outboxmessage", index=models.Index(fields=["status", "available_at"], name="media_outbox_status_available_idx")),
        migrations.AddIndex(model_name="outboxmessage", index=models.Index(fields=["routing_key"], name="media_outbox_routing_idx")),
        migrations.AddIndex(model_name="inboxmessage", index=models.Index(fields=["event_type"], name="media_inbox_event_type_idx")),
        migrations.AddIndex(model_name="inboxmessage", index=models.Index(fields=["routing_key"], name="media_inbox_routing_idx")),
    ]
