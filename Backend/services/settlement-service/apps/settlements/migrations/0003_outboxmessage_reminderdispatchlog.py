# Generated manually for Phase 9

import uuid

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("settlements", "0002_settlementplan_settlementplaneventlog_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="OutboxMessage",
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
                (
                    "event_id",
                    models.UUIDField(db_index=True, default=uuid.uuid4, unique=True),
                ),
                (
                    "source_service",
                    models.CharField(default="settlement-service", max_length=128),
                ),
                ("aggregate_type", models.CharField(max_length=64)),
                ("aggregate_id", models.UUIDField(blank=True, db_index=True, null=True)),
                ("event_type", models.CharField(max_length=128)),
                ("routing_key", models.CharField(max_length=128)),
                (
                    "exchange",
                    models.CharField(default="hamdong.settlement", max_length=128),
                ),
                (
                    "correlation_id",
                    models.UUIDField(blank=True, db_index=True, null=True),
                ),
                (
                    "causation_id",
                    models.UUIDField(blank=True, db_index=True, null=True),
                ),
                ("payload", models.JSONField(default=dict)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("PENDING", "Pending"),
                            ("RETRY_PENDING", "Retry pending"),
                            ("SENT", "Sent"),
                            ("FAILED", "Failed"),
                        ],
                        default="PENDING",
                        max_length=20,
                    ),
                ),
                ("retry_count", models.PositiveIntegerField(default=0)),
                (
                    "available_at",
                    models.DateTimeField(
                        db_index=True, default=django.utils.timezone.now
                    ),
                ),
                ("published_at", models.DateTimeField(blank=True, null=True)),
                ("last_error", models.TextField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "settlement_outbox_messages",
                "indexes": [
                    models.Index(
                        fields=["status", "available_at"],
                        name="settlement_o_status_a7a0f7_idx",
                    ),
                    models.Index(
                        fields=["routing_key"],
                        name="settlement_o_routing_ef5c23_idx",
                    ),
                    models.Index(
                        fields=["aggregate_type", "aggregate_id"],
                        name="settlement_o_aggregate_7e9c7d_idx",
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name="ReminderDispatchLog",
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
                (
                    "reminder_type",
                    models.CharField(
                        choices=[
                            ("PAYMENT_REMINDER", "Payment reminder"),
                            (
                                "SETTLEMENT_CONFIRMATION_REMINDER",
                                "Settlement confirmation reminder",
                            ),
                            (
                                "SETTLEMENT_PLAN_ITEM_REMINDER",
                                "Settlement plan item reminder",
                            ),
                        ],
                        max_length=48,
                    ),
                ),
                ("group_id", models.UUIDField(db_index=True)),
                (
                    "settlement_plan_id",
                    models.UUIDField(blank=True, db_index=True, null=True),
                ),
                (
                    "settlement_plan_item_id",
                    models.UUIDField(blank=True, db_index=True, null=True),
                ),
                (
                    "manual_settlement_id",
                    models.UUIDField(blank=True, db_index=True, null=True),
                ),
                ("recipient_user_id", models.UUIDField(db_index=True)),
                ("recipient_phone_number", models.CharField(max_length=32)),
                (
                    "source_event_id",
                    models.UUIDField(blank=True, db_index=True, null=True),
                ),
                ("sent_count", models.PositiveIntegerField(default=0)),
                ("last_sent_at", models.DateTimeField(blank=True, null=True)),
                ("next_allowed_at", models.DateTimeField(blank=True, null=True)),
                ("metadata", models.JSONField(default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "settlement_reminder_dispatch_logs",
                "indexes": [
                    models.Index(
                        fields=["reminder_type", "group_id"],
                        name="settlement_r_reminder_2d3d54_idx",
                    ),
                    models.Index(
                        fields=["recipient_user_id"],
                        name="settlement_r_recipie_d98f60_idx",
                    ),
                    models.Index(
                        fields=["next_allowed_at"],
                        name="settlement_r_next_al_ee1ce1_idx",
                    ),
                ],
                "constraints": [
                    models.UniqueConstraint(
                        fields=(
                            "reminder_type",
                            "group_id",
                            "settlement_plan_id",
                            "settlement_plan_item_id",
                            "manual_settlement_id",
                            "recipient_user_id",
                        ),
                        name="settlement_reminder_unique_target",
                    )
                ],
            },
        ),
    ]
