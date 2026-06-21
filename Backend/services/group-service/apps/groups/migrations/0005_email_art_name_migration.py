from __future__ import annotations

import uuid

from django.db import migrations, models


def _placeholder(seed_value):
    seed = str(seed_value or uuid.uuid4()).replace("-", "")[:12]
    return f"legacy-{seed}@users.hamdong.local"


def forwards(apps, schema_editor):
    UserProjection = apps.get_model("groups", "UserProjection")
    Group = apps.get_model("groups", "Group")
    GroupMember = apps.get_model("groups", "GroupMember")

    for row in UserProjection.objects.all():
        if row.email and "@" not in row.email:
            row.email = _placeholder(getattr(row, "identity_user_id", row.id))
            row.save(update_fields=["email"])
    for row in Group.objects.all():
        if row.created_by_email and "@" not in row.created_by_email:
            row.created_by_email = _placeholder(getattr(row, "created_by_user_id", row.id))
            row.save(update_fields=["created_by_email"])
    for row in GroupMember.objects.all():
        if row.email and "@" not in row.email:
            row.email = _placeholder(getattr(row, "user_id", row.id))
            row.save(update_fields=["email"])


class Migration(migrations.Migration):

    dependencies = [
        ("groups", "0004_group_lifecycle_and_title_parts"),
    ]

    operations = [
        migrations.RenameField(
            model_name="userprojection",
            old_name="phone_number",
            new_name="email",
        ),
        migrations.RenameField(
            model_name="userprojection",
            old_name="display_name",
            new_name="art_name",
        ),
        migrations.RenameField(
            model_name="group",
            old_name="created_by_phone_number",
            new_name="created_by_email",
        ),
        migrations.RenameField(
            model_name="groupmember",
            old_name="phone_number",
            new_name="email",
        ),
        migrations.RenameField(
            model_name="groupmember",
            old_name="display_name_snapshot",
            new_name="art_name_snapshot",
        ),
        migrations.AlterField(
            model_name="userprojection",
            name="email",
            field=models.CharField(max_length=254),
        ),
        migrations.AlterField(
            model_name="group",
            name="created_by_email",
            field=models.CharField(max_length=254),
        ),
        migrations.AlterField(
            model_name="groupmember",
            name="email",
            field=models.CharField(max_length=254),
        ),
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
