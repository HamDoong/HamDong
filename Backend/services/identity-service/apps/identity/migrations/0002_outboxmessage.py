import uuid

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("identity", "0001_initial"),
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
            options={"db_table": "identity_outbox_messages"},
        ),
        migrations.AddIndex(
            model_name="outboxmessage",
            index=models.Index(fields=["status", "available_at"], name="identity_outbox_status_available_idx"),
        ),
        migrations.AddIndex(
            model_name="outboxmessage",
            index=models.Index(fields=["routing_key"], name="identity_outbox_routing_idx"),
        ),
    ]
