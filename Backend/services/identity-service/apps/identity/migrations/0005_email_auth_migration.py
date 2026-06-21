from __future__ import annotations

import re
import uuid

from django.db import migrations, models


def _normalize_art_name(value: str | None, fallback_seed: str) -> str:
    if value:
        cleaned = value.strip()
        cleaned = re.sub(r"\s+", "-", cleaned)
        cleaned = re.sub(r"[^\w\-\u0600-\u06FF]", "-", cleaned, flags=re.UNICODE)
        cleaned = re.sub(r"-{2,}", "-", cleaned).strip("-_")
        if cleaned and 3 <= len(cleaned) <= 32:
            return cleaned
    return f"user-{fallback_seed[:8]}"[:32]


def forwards(apps, schema_editor):
    User = apps.get_model("identity", "User")
    existing_art_names = set(
        User.objects.exclude(art_name__isnull=True).exclude(art_name="").values_list("art_name", flat=True)
    )

    for user in User.objects.all().order_by("created_at", "id"):
        seed = str(user.id).replace("-", "")
        email = getattr(user, "email", None)
        if not email:
            user.email = f"legacy-{seed[:12]}@users.hamdong.local"

        art_name = getattr(user, "art_name", None)
        if not art_name:
            base_source = getattr(user, "legacy_display_name", None) or user.email.split("@", 1)[0]
            candidate = _normalize_art_name(base_source, seed)
            if candidate in existing_art_names:
                suffix = seed[:6]
                candidate = f"{candidate[: max(3, 32 - len(suffix) - 1)].rstrip('-')}-{suffix}"
            existing_art_names.add(candidate)
            user.art_name = candidate

        update_fields = ["email", "art_name"]
        if hasattr(user, "is_email_verified") and getattr(user, "is_email_verified", None) is None:
            user.is_email_verified = False
            update_fields.append("is_email_verified")
        user.save(update_fields=update_fields)


class Migration(migrations.Migration):

    dependencies = [
        ("identity", "0004_user_art_name_password_fields"),
    ]

    operations = [
        migrations.RenameField(
            model_name="user",
            old_name="phone_number",
            new_name="legacy_phone_number",
        ),
        migrations.RenameField(
            model_name="user",
            old_name="display_name",
            new_name="legacy_display_name",
        ),
        migrations.RenameField(
            model_name="user",
            old_name="is_phone_verified",
            new_name="is_email_verified",
        ),
        migrations.AddField(
            model_name="user",
            name="email",
            field=models.EmailField(blank=True, max_length=254, null=True),
        ),
        migrations.RunPython(forwards, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="user",
            name="email",
            field=models.EmailField(max_length=254, unique=True),
        ),
        migrations.AlterField(
            model_name="user",
            name="art_name",
            field=models.CharField(max_length=32, unique=True),
        ),
    ]
