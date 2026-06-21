# Generated manually for automatic debt reminders.
import uuid

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("settlements", "0007_email_art_name_migration"),
    ]

    operations = [
        migrations.AddField(
            model_name="settlementplan",
            name="activated_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.CreateModel(
            name="GroupReminderSettings",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ("group_id", models.UUIDField(db_index=True, unique=True)),
                ("is_enabled", models.BooleanField(default=True)),
                ("first_reminder_after_hours", models.PositiveIntegerField(default=24)),
                ("repeat_interval_hours", models.PositiveIntegerField(default=48)),
                ("maximum_reminders", models.PositiveIntegerField(default=3)),
                ("send_in_app", models.BooleanField(default=True)),
                ("send_email", models.BooleanField(default=True)),
                ("created_by_user_id", models.UUIDField(blank=True, null=True)),
                ("updated_by_user_id", models.UUIDField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "settlement_group_reminder_settings",
            },
        ),
        migrations.CreateModel(
            name="DebtReminderRequest",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ("group_id", models.UUIDField(db_index=True)),
                ("settlement_plan_id", models.UUIDField(db_index=True)),
                ("settlement_plan_item_id", models.UUIDField(db_index=True)),
                ("recipient_user_id", models.UUIDField(db_index=True)),
                ("creditor_user_id", models.UUIDField(db_index=True)),
                ("requested_by_user_id", models.UUIDField(blank=True, null=True)),
                ("sequence_number", models.PositiveIntegerField(default=1)),
                ("source", models.CharField(max_length=32, choices=[
                    ("AUTOMATIC", "Automatic"),
                    ("MANUAL_GROUP_RUN", "Manual group run"),
                    ("MANUAL_ITEM", "Manual item"),
                ])),
                ("channels", models.JSONField(default=list)),
                ("channel_statuses", models.JSONField(default=dict, blank=True)),
                ("status", models.CharField(max_length=32, default="PENDING", choices=[
                    ("PENDING", "Pending"),
                    ("QUEUED", "Queued"),
                    ("PARTIALLY_SENT", "Partially sent"),
                    ("SENT", "Sent"),
                    ("FAILED", "Failed"),
                    ("CANCELED", "Canceled"),
                    ("SKIPPED", "Skipped"),
                ])),
                ("currency", models.CharField(max_length=3, default="IRR", choices=[("IRR", "Iranian Rial")])),
                ("amount_minor", models.BigIntegerField(default=0)),
                ("source_timestamp", models.DateTimeField(blank=True, null=True)),
                ("scheduled_at", models.DateTimeField(db_index=True)),
                ("requested_at", models.DateTimeField()),
                ("sent_at", models.DateTimeField(blank=True, null=True)),
                ("delivery_updated_at", models.DateTimeField(blank=True, null=True)),
                ("last_error", models.TextField(blank=True, null=True)),
                ("dedupe_key", models.CharField(blank=True, db_index=True, max_length=128, null=True)),
                ("created_by_user_id", models.UUIDField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "settlement_debt_reminder_requests",
            },
        ),
        migrations.AddIndex(
            model_name="groupremindersettings",
            index=models.Index(fields=["group_id"], name="settlement__group_i_e722d2_idx"),
        ),
        migrations.AddIndex(
            model_name="debtreminderrequest",
            index=models.Index(fields=["group_id", "-created_at"], name="settlement__group_i_5af738_idx"),
        ),
        migrations.AddIndex(
            model_name="debtreminderrequest",
            index=models.Index(fields=["settlement_plan_item_id", "source", "sequence_number"], name="settlement__settlem_a2f212_idx"),
        ),
        migrations.AddIndex(
            model_name="debtreminderrequest",
            index=models.Index(fields=["recipient_user_id", "-created_at"], name="settlement__recipi_507541_idx"),
        ),
        migrations.AddIndex(
            model_name="debtreminderrequest",
            index=models.Index(fields=["status", "-scheduled_at"], name="settlement__status_f92644_idx"),
        ),
        migrations.AddIndex(
            model_name="debtreminderrequest",
            index=models.Index(fields=["source", "-created_at"], name="settlement__source_77dbab_idx"),
        ),
        migrations.AddConstraint(
            model_name="debtreminderrequest",
            constraint=models.UniqueConstraint(
                fields=("settlement_plan_item_id", "source", "sequence_number"),
                name="settlement_debt_reminder_unique_sequence",
            ),
        ),
    ]
