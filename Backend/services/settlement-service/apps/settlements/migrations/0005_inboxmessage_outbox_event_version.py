import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("settlements", "0004_rename_settlement_o_status_a7a0f7_idx_settlement__status_142d3a_idx_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="outboxmessage",
            name="event_version",
            field=models.PositiveIntegerField(default=1),
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
            options={"db_table": "settlement_inbox_messages"},
        ),
        migrations.AddIndex(model_name="inboxmessage", index=models.Index(fields=["event_type"], name="settlement_inbox_event_type_idx")),
        migrations.AddIndex(model_name="inboxmessage", index=models.Index(fields=["routing_key"], name="settlement_inbox_routing_idx")),
    ]
