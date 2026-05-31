# Generated manually for Phase 6 media-service

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
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("identity_user_id", models.UUIDField(unique=True)),
                ("phone_number", models.CharField(max_length=32)),
                ("display_name", models.CharField(blank=True, max_length=255, null=True)),
                ("first_name", models.CharField(blank=True, max_length=150, null=True)),
                ("last_name", models.CharField(blank=True, max_length=150, null=True)),
                ("role", models.CharField(choices=[("USER", "User"), ("ADMIN", "Admin")], default="USER", max_length=10)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "media_user_projections"},
        ),
        migrations.CreateModel(
            name="GroupProjection",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("group_id", models.UUIDField(unique=True)),
                ("title", models.CharField(max_length=255)),
                ("group_type", models.CharField(choices=[("EVENT", "Event"), ("TRIP", "Trip"), ("GENERAL", "General")], default="GENERAL", max_length=20)),
                ("status", models.CharField(choices=[("ACTIVE", "Active"), ("ARCHIVED", "Archived"), ("DELETED", "Deleted")], default="ACTIVE", max_length=10)),
                ("created_by_user_id", models.UUIDField()),
                ("member_count", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "media_group_projections"},
        ),
        migrations.CreateModel(
            name="MediaFile",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("uploaded_by_user_id", models.UUIDField(db_index=True)),
                ("group_id", models.UUIDField(db_index=True)),
                ("related_expense_id", models.UUIDField(blank=True, null=True)),
                ("file_type", models.CharField(choices=[("RECEIPT", "Receipt"), ("AVATAR", "Avatar"), ("OTHER", "Other")], default="RECEIPT", max_length=10)),
                ("storage_provider", models.CharField(choices=[("LOCAL", "Local"), ("S3", "S3"), ("MINIO", "MinIO")], default="LOCAL", max_length=10)),
                ("bucket_name", models.CharField(blank=True, max_length=255, null=True)),
                ("object_key", models.CharField(max_length=512, unique=True)),
                ("original_filename", models.CharField(max_length=255)),
                ("stored_filename", models.CharField(max_length=255)),
                ("content_type", models.CharField(max_length=128)),
                ("file_extension", models.CharField(max_length=16)),
                ("size_bytes", models.PositiveBigIntegerField()),
                ("checksum_sha256", models.CharField(max_length=64)),
                ("status", models.CharField(choices=[("ACTIVE", "Active"), ("DELETED", "Deleted")], default="ACTIVE", max_length=10)),
                ("visibility", models.CharField(choices=[("GROUP_MEMBERS", "Group Members"), ("OWNER_ONLY", "Owner Only"), ("PRIVATE", "Private")], default="GROUP_MEMBERS", max_length=20)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("version", models.PositiveIntegerField(default=1)),
            ],
            options={"db_table": "media_files"},
        ),
        migrations.CreateModel(
            name="GroupMemberProjection",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("group_id", models.UUIDField(db_index=True)),
                ("user_id", models.UUIDField(db_index=True)),
                ("phone_number", models.CharField(max_length=32)),
                ("display_name_snapshot", models.CharField(blank=True, max_length=255, null=True)),
                ("role", models.CharField(choices=[("OWNER", "Owner"), ("ADMIN", "Admin"), ("MEMBER", "Member")], default="MEMBER", max_length=10)),
                ("status", models.CharField(choices=[("ACTIVE", "Active"), ("LEFT", "Left"), ("REMOVED", "Removed")], default="ACTIVE", max_length=10)),
                ("joined_at", models.DateTimeField(blank=True, null=True)),
                ("left_at", models.DateTimeField(blank=True, null=True)),
                ("removed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "media_group_member_projections", "unique_together": {("group_id", "user_id")}},
        ),
        migrations.CreateModel(
            name="MediaAccessLog",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("user_id", models.UUIDField(db_index=True)),
                ("action", models.CharField(choices=[("UPLOAD", "Upload"), ("VIEW", "View"), ("DOWNLOAD", "Download"), ("DELETE", "Delete")], max_length=10)),
                ("ip_address", models.GenericIPAddressField(blank=True, null=True)),
                ("user_agent", models.TextField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("media_file", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="access_logs", to="media_files.mediafile")),
            ],
            options={"db_table": "media_access_logs"},
        ),
        migrations.AddIndex(
            model_name="groupmemberprojection",
            index=models.Index(fields=["group_id"], name="media_groupm_group_id_0c2d9e_idx"),
        ),
        migrations.AddIndex(
            model_name="groupmemberprojection",
            index=models.Index(fields=["user_id"], name="media_groupm_user_id_8af01e_idx"),
        ),
    ]
