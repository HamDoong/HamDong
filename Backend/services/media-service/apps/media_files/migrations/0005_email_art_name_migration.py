from __future__ import annotations

import uuid

from django.db import migrations, models


def _placeholder(seed_value):
    seed = str(seed_value or uuid.uuid4()).replace("-", "")[:12]
    return f"legacy-{seed}@users.hamdong.local"


def forwards(apps, schema_editor):
    UserProjection = apps.get_model("media_files", "UserProjection")
    GroupMemberProjection = apps.get_model("media_files", "GroupMemberProjection")

    for model, seed_attr in (
        (UserProjection, "identity_user_id"),
        (GroupMemberProjection, "user_id"),
    ):
        for row in model.objects.all():
            if row.email and "@" not in row.email:
                row.email = _placeholder(getattr(row, seed_attr, row.id))
                row.save(update_fields=["email"])


class Migration(migrations.Migration):

    dependencies = [
        ("media_files", "0004_rename_media_inbox_event_type_idx_media_inbox_event_t_3a44fd_idx_and_more"),
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
            model_name="groupmemberprojection",
            old_name="phone_number",
            new_name="email",
        ),
        migrations.RenameField(
            model_name="groupmemberprojection",
            old_name="display_name_snapshot",
            new_name="art_name_snapshot",
        ),
        migrations.AlterField(
            model_name="userprojection",
            name="email",
            field=models.CharField(max_length=254),
        ),
        migrations.AlterField(
            model_name="groupmemberprojection",
            name="email",
            field=models.CharField(max_length=254),
        ),
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
