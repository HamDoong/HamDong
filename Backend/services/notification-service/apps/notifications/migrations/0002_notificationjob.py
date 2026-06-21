# Generated manually for Phase 9

import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("notifications", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="NotificationJob",
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
                ("event_id", models.UUIDField(db_index=True, unique=True)),
                ("source_service", models.CharField(max_length=128)),
                ("source_event_type", models.CharField(max_length=128)),
                ("reminder_type", models.CharField(max_length=48)),
                (
                    "channel",
                    models.CharField(
                        choices=[("SMS", "SMS"), ("EMAIL", "Email"), ("PUSH", "Push")],
                        default="SMS",
                        max_length=16,
                    ),
                ),
                ("recipient", models.CharField(max_length=32)),
                ("recipient_masked", models.CharField(max_length=32)),
                (
                    "template_code",
                    models.CharField(blank=True, max_length=64, null=True),
                ),
                ("rendered_message", models.TextField()),
                ("payload", models.JSONField(default=dict)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("PENDING", "Pending"),
                            ("PROCESSING", "Processing"),
                            ("SENT", "Sent"),
                            ("FAILED", "Failed"),
                            ("RETRY_PENDING", "Retry pending"),
                            ("SKIPPED", "Skipped"),
                        ],
                        default="PENDING",
                        max_length=32,
                    ),
                ),
                (
                    "notification_message",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="jobs",
                        to="notifications.notificationmessage",
                    ),
                ),
                ("retry_count", models.PositiveIntegerField(default=0)),
                ("last_attempt_at", models.DateTimeField(blank=True, null=True)),
                ("sent_at", models.DateTimeField(blank=True, null=True)),
                ("error_code", models.CharField(blank=True, max_length=64, null=True)),
                ("error_message", models.TextField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "notification_jobs",
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(fields=["event_id"], name="notification_event_2a7a73_idx"),
                    models.Index(fields=["status"], name="notification_status_7ac2f5_idx"),
                    models.Index(fields=["recipient"], name="notification_recipient_0f1c4b_idx"),
                ],
            },
        ),
    ]
