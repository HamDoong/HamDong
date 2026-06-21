# Generated migration for User and RefreshToken models

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="User",
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
                ("phone_number", models.CharField(max_length=20, unique=True)),
                (
                    "display_name",
                    models.CharField(blank=True, max_length=255, null=True),
                ),
                ("first_name", models.CharField(blank=True, max_length=150, null=True)),
                ("last_name", models.CharField(blank=True, max_length=150, null=True)),
                ("avatar_url", models.URLField(blank=True, null=True)),
                ("is_phone_verified", models.BooleanField(default=False)),
                ("is_active", models.BooleanField(default=True)),
                ("is_staff", models.BooleanField(default=False)),
                (
                    "role",
                    models.CharField(
                        choices=[("USER", "User"), ("ADMIN", "Admin")],
                        default="USER",
                        max_length=10,
                    ),
                ),
                ("last_login_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("version", models.IntegerField(default=1)),
            ],
            options={
                "db_table": "users",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="RefreshToken",
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
                ("token_hash", models.CharField(max_length=255, unique=True)),
                ("jti", models.UUIDField(default=uuid.uuid4, unique=True)),
                ("expires_at", models.DateTimeField()),
                ("revoked_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user_agent", models.TextField(blank=True, null=True)),
                ("ip_address", models.GenericIPAddressField(blank=True, null=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=models.deletion.CASCADE,
                        related_name="refresh_tokens",
                        to="identity.user",
                    ),
                ),
            ],
            options={
                "db_table": "refresh_tokens",
                "ordering": ["-created_at"],
            },
        ),
    ]
