from django.db import migrations, models
import uuid


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="DashboardActivity",
            fields=[
                ("id", models.UUIDField(primary_key=True, serialize=False, editable=False)),
                ("event_type", models.CharField(max_length=64, choices=[
                    ("GROUP_CREATED", "Group Created"),
                    ("GROUP_MEMBER_JOINED", "Group Member Joined"),
                    ("GROUP_INVITATION_CREATED", "Group Invitation Created"),
                    ("EXPENSE_CREATED", "Expense Created"),
                    ("EXPENSE_UPDATED", "Expense Updated"),
                    ("EXPENSE_DELETED", "Expense Deleted"),
                    ("RECEIPT_UPLOADED", "Receipt Uploaded"),
                    ("SETTLEMENT_REPORTED", "Settlement Reported"),
                    ("SETTLEMENT_CONFIRMED", "Settlement Confirmed"),
                    ("SETTLEMENT_REJECTED", "Settlement Rejected"),
                    ("SETTLEMENT_PLAN_ACTIVATED", "Settlement Plan Activated"),
                    ("WALLET_PAYMENT_COMPLETED", "Wallet Payment Completed"),
                ])),
                ("source_service", models.CharField(max_length=64)),
                ("routing_key", models.CharField(max_length=128)),
                ("group_id", models.UUIDField(db_index=True)),
                ("actor_user_id", models.UUIDField(null=True, blank=True, db_index=True)),
                ("source_object_id", models.UUIDField(null=True, blank=True, db_index=True)),
                ("summary", models.JSONField(default=dict, blank=True)),
                ("occurred_at", models.DateTimeField(db_index=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "indexes": [
                    models.Index(fields=["group_id", "occurred_at"], name="dashboard_d_group_i_7083f5_idx"),
                    models.Index(fields=["event_type", "occurred_at"], name="dashboard_d_event_t_4cd1fc_idx"),
                ],
            },
        ),
        migrations.CreateModel(
            name="GroupProjection",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ("group_id", models.UUIDField(unique=True)),
                ("title", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True, default="")),
                ("group_type", models.CharField(max_length=32, default="GENERAL")),
                ("status", models.CharField(max_length=32, choices=[("ACTIVE", "Active"), ("ARCHIVED", "Archived"), ("DELETED", "Deleted")], default="ACTIVE")),
                ("created_by_user_id", models.UUIDField(null=True, blank=True)),
                ("member_count", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name="InboxMessage",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ("event_id", models.UUIDField(unique=True)),
                ("event_type", models.CharField(max_length=128)),
                ("source_service", models.CharField(max_length=64)),
                ("routing_key", models.CharField(max_length=128)),
                ("payload", models.JSONField(default=dict, blank=True)),
                ("status", models.CharField(max_length=16, choices=[("PROCESSED", "Processed"), ("SKIPPED", "Skipped"), ("FAILED", "Failed")], default="PROCESSED")),
                ("error_message", models.TextField(blank=True, default="")),
                ("processed_at", models.DateTimeField(null=True, blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name="UserProjection",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ("identity_user_id", models.UUIDField(unique=True)),
                ("email", models.EmailField(max_length=254, blank=True)),
                ("art_name", models.CharField(max_length=255, null=True, blank=True)),
                ("first_name", models.CharField(max_length=100, null=True, blank=True)),
                ("last_name", models.CharField(max_length=100, null=True, blank=True)),
                ("role", models.CharField(max_length=32, default="USER")),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name="GroupMemberProjection",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ("group_id", models.UUIDField(db_index=True)),
                ("user_id", models.UUIDField(db_index=True)),
                ("email", models.EmailField(max_length=254, blank=True)),
                ("art_name_snapshot", models.CharField(max_length=255, null=True, blank=True)),
                ("role", models.CharField(max_length=32, choices=[("OWNER", "Owner"), ("ADMIN", "Admin"), ("MEMBER", "Member")], default="MEMBER")),
                ("status", models.CharField(max_length=32, choices=[("ACTIVE", "Active"), ("LEFT", "Left"), ("REMOVED", "Removed")], default="ACTIVE")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "constraints": [
                    models.UniqueConstraint(fields=["group_id", "user_id"], name="dashboard_unique_group_member"),
                ],
                "indexes": [
                    models.Index(fields=["user_id", "status"], name="dashboard_g_user_id_dfa5b7_idx"),
                    models.Index(fields=["group_id", "status"], name="dashboard_g_group_i_b1ddd3_idx"),
                ],
            },
        ),
    ]
