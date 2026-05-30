"""Initial migration for groups app creating domain tables."""
from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="UserProjection",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)),
                ("identity_user_id", models.UUIDField(unique=True)),
                ("phone_number", models.CharField(max_length=32)),
                ("display_name", models.CharField(max_length=255, null=True, blank=True)),
                ("first_name", models.CharField(max_length=255, null=True, blank=True)),
                ("last_name", models.CharField(max_length=255, null=True, blank=True)),
                ("role", models.CharField(max_length=32, default="USER")),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "groups_user_projections"},
        ),

        migrations.CreateModel(
            name="Group",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)),
                ("title", models.CharField(max_length=255)),
                ("description", models.TextField(null=True, blank=True)),
                ("group_type", models.CharField(max_length=32)),
                ("status", models.CharField(max_length=32, default="ACTIVE")),
                ("created_by_user_id", models.UUIDField()),
                ("created_by_phone_number", models.CharField(max_length=32)),
                ("member_count", models.PositiveIntegerField(default=0)),
                ("version", models.PositiveIntegerField(default=1)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("deleted_at", models.DateTimeField(null=True, blank=True)),
            ],
            options={"db_table": "groups"},
        ),

        migrations.CreateModel(
            name="GroupMember",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)),
                ("user_id", models.UUIDField()),
                ("phone_number", models.CharField(max_length=32)),
                ("display_name_snapshot", models.CharField(max_length=255, null=True, blank=True)),
                ("role", models.CharField(max_length=16)),
                ("status", models.CharField(max_length=16, default="ACTIVE")),
                ("joined_at", models.DateTimeField(auto_now_add=True)),
                ("left_at", models.DateTimeField(null=True, blank=True)),
                """Initial migration for groups app creating domain tables."""
                from django.db import migrations, models
                import uuid


                class Migration(migrations.Migration):

                    initial = True

                    dependencies = []

                    operations = [
                        migrations.CreateModel(
                            name="UserProjection",
                            fields=[
                                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)),
                                ("identity_user_id", models.UUIDField(unique=True)),
                                ("phone_number", models.CharField(max_length=32)),
                                ("display_name", models.CharField(max_length=255, null=True, blank=True)),
                                ("first_name", models.CharField(max_length=255, null=True, blank=True)),
                                ("last_name", models.CharField(max_length=255, null=True, blank=True)),
                                ("role", models.CharField(max_length=32, default="USER")),
                                ("is_active", models.BooleanField(default=True)),
                                ("created_at", models.DateTimeField(auto_now_add=True)),
                                ("updated_at", models.DateTimeField(auto_now=True)),
                            ],
                            options={"db_table": "groups_user_projections"},
                        ),

                        migrations.CreateModel(
                            name="Group",
                            fields=[
                                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)),
                                ("title", models.CharField(max_length=255)),
                                ("description", models.TextField(null=True, blank=True)),
                                ("group_type", models.CharField(max_length=32)),
                                ("status", models.CharField(max_length=32, default="ACTIVE")),
                                ("created_by_user_id", models.UUIDField()),
                                ("created_by_phone_number", models.CharField(max_length=32)),
                                ("member_count", models.PositiveIntegerField(default=0)),
                                ("version", models.PositiveIntegerField(default=1)),
                                ("created_at", models.DateTimeField(auto_now_add=True)),
                                ("updated_at", models.DateTimeField(auto_now=True)),
                                ("deleted_at", models.DateTimeField(null=True, blank=True)),
                            ],
                            options={"db_table": "groups"},
                        ),

                        migrations.CreateModel(
                            name="GroupMember",
                            fields=[
                                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)),
                                ("user_id", models.UUIDField()),
                                ("phone_number", models.CharField(max_length=32)),
                                ("display_name_snapshot", models.CharField(max_length=255, null=True, blank=True)),
                                ("role", models.CharField(max_length=16)),
                                ("status", models.CharField(max_length=16, default="ACTIVE")),
                                ("joined_at", models.DateTimeField(auto_now_add=True)),
                                ("left_at", models.DateTimeField(null=True, blank=True)),
                                ("removed_at", models.DateTimeField(null=True, blank=True)),
                                ("created_at", models.DateTimeField(auto_now_add=True)),
                                ("updated_at", models.DateTimeField(auto_now=True)),
                                ("group", models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="members", to="apps.groups.Group")),
                            ],
                            options={"db_table": "group_members"},
                        ),

                        migrations.CreateModel(
                            name="GroupInvite",
                            fields=[
                                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)),
                                ("created_by_user_id", models.UUIDField()),
                                ("token_hash", models.CharField(max_length=128)),
                                ("invite_code", models.CharField(max_length=64, null=True, blank=True)),
                                ("status", models.CharField(max_length=16, default="ACTIVE")),
                                ("max_uses", models.PositiveIntegerField(null=True, blank=True)),
                                ("used_count", models.PositiveIntegerField(default=0)),
                                ("expires_at", models.DateTimeField(null=True, blank=True)),
                                ("revoked_at", models.DateTimeField(null=True, blank=True)),
                                ("created_at", models.DateTimeField(auto_now_add=True)),
                                ("updated_at", models.DateTimeField(auto_now=True)),
                                ("group", models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="invites", to="apps.groups.Group")),
                            ],
                            options={"db_table": "group_invites"},
                        ),
                    ]
