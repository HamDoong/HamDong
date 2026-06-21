"""Initial migration for groups app creating domain tables."""

import uuid

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="UserProjection",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ("identity_user_id", models.UUIDField(unique=True)),
                ("phone_number", models.CharField(max_length=32)),
                ("display_name", models.CharField(blank=True, max_length=255, null=True)),
                ("first_name", models.CharField(blank=True, max_length=255, null=True)),
                ("last_name", models.CharField(blank=True, max_length=255, null=True)),
                ("role", models.CharField(default="USER", max_length=32)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "groups_user_projections"},
        ),
        migrations.CreateModel(
            name="Group",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ("title", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True, null=True)),
                ("group_type", models.CharField(max_length=32)),
                ("status", models.CharField(default="ACTIVE", max_length=32)),
                ("created_by_user_id", models.UUIDField()),
                ("created_by_phone_number", models.CharField(max_length=32)),
                ("member_count", models.PositiveIntegerField(default=0)),
                ("version", models.PositiveIntegerField(default=1)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
            ],
            options={"db_table": "groups"},
        ),
        migrations.CreateModel(
            name="GroupMember",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ("user_id", models.UUIDField()),
                ("phone_number", models.CharField(max_length=32)),
                ("display_name_snapshot", models.CharField(blank=True, max_length=255, null=True)),
                ("role", models.CharField(max_length=16)),
                ("status", models.CharField(default="ACTIVE", max_length=16)),
                ("joined_at", models.DateTimeField(auto_now_add=True)),
                ("left_at", models.DateTimeField(blank=True, null=True)),
                ("removed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "group",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="members",
                        to="groups.group",
                    ),
                ),
            ],
            options={"db_table": "group_members"},
        ),
        migrations.CreateModel(
            name="GroupInvite",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ("created_by_user_id", models.UUIDField()),
                ("token_hash", models.CharField(max_length=128)),
                ("invite_code", models.CharField(blank=True, max_length=64, null=True)),
                ("status", models.CharField(default="ACTIVE", max_length=16)),
                ("max_uses", models.PositiveIntegerField(blank=True, null=True)),
                ("used_count", models.PositiveIntegerField(default=0)),
                ("expires_at", models.DateTimeField(blank=True, null=True)),
                ("revoked_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "group",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="invites",
                        to="groups.group",
                    ),
                ),
            ],
            options={"db_table": "group_invites"},
        ),
    ]
