from __future__ import annotations

import re

from django.db import migrations, models


_PERSIAN_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")


def _normalize_whitespace(value):
    return re.sub(r"\s+", " ", value or "").strip()


def _normalize_display_name(value):
    normalized = _normalize_whitespace(value)
    return normalized or None


def _normalize_phone_number(value):
    if not value:
        return None
    normalized = str(value).translate(_PERSIAN_DIGITS).strip()
    normalized = re.sub(r"[\s\-()]+", "", normalized)
    if not normalized:
        return None
    if normalized.startswith("0098"):
        normalized = "+" + normalized[2:]
    elif normalized.startswith("98"):
        normalized = "+" + normalized
    elif normalized.startswith("09"):
        normalized = "+98" + normalized[1:]
    if re.fullmatch(r"\+989\d{9}", normalized):
        return normalized
    return None


def rename_legacy_phone_constraints(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conname = 'users_phone_number_key'
            ) THEN
                ALTER TABLE users
                RENAME CONSTRAINT users_phone_number_key
                TO users_legacy_phone_number_key;
            END IF;

            IF EXISTS (
                SELECT 1
                FROM pg_class
                WHERE relname = 'users_phone_number_b4cde146_like'
            ) THEN
                ALTER INDEX users_phone_number_b4cde146_like
                RENAME TO users_legacy_phone_number_like;
            END IF;
        END $$;
        """
    )


def restore_legacy_phone_constraints(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conname = 'users_legacy_phone_number_key'
            ) THEN
                ALTER TABLE users
                RENAME CONSTRAINT users_legacy_phone_number_key
                TO users_phone_number_key;
            END IF;

            IF EXISTS (
                SELECT 1
                FROM pg_class
                WHERE relname = 'users_legacy_phone_number_like'
            ) THEN
                ALTER INDEX users_legacy_phone_number_like
                RENAME TO users_phone_number_b4cde146_like;
            END IF;
        END $$;
        """
    )


def forwards(apps, schema_editor):
    User = apps.get_model("identity", "User")
    for user in User.objects.all().order_by("created_at", "id"):
        update_fields = []
        if not getattr(user, "display_name", None):
            display_name = _normalize_display_name(getattr(user, "legacy_display_name", None))
            if display_name is not None:
                user.display_name = display_name
                update_fields.append("display_name")
        if not getattr(user, "phone_number", None):
            phone_number = _normalize_phone_number(getattr(user, "legacy_phone_number", None))
            if phone_number is not None:
                user.phone_number = phone_number
                update_fields.append("phone_number")
        if update_fields:
            user.save(update_fields=update_fields)


def backwards(apps, schema_editor):
    User = apps.get_model("identity", "User")
    for user in User.objects.all().order_by("created_at", "id"):
        update_fields = []
        if not getattr(user, "legacy_display_name", None) and getattr(user, "display_name", None):
            user.legacy_display_name = user.display_name
            update_fields.append("legacy_display_name")
        if not getattr(user, "legacy_phone_number", None) and getattr(user, "phone_number", None):
            user.legacy_phone_number = user.phone_number
            update_fields.append("legacy_phone_number")
        if update_fields:
            user.save(update_fields=update_fields)


class Migration(migrations.Migration):

    dependencies = [
        ("identity", "0007_alter_user_legacy_phone_number"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="bio",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="user",
            name="city",
            field=models.CharField(blank=True, max_length=150, null=True),
        ),
        migrations.AddField(
            model_name="user",
            name="date_of_birth",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="user",
            name="display_name",
            field=models.CharField(blank=True, max_length=150, null=True),
        ),
        migrations.RunPython(rename_legacy_phone_constraints, restore_legacy_phone_constraints),
        migrations.AddField(
            model_name="user",
            name="phone_number",
            field=models.CharField(blank=True, max_length=16, null=True, unique=True),
        ),
        migrations.RunPython(forwards, backwards),
    ]
