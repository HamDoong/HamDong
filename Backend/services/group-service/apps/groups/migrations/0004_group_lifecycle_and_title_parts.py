from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("groups", "0003_rename_groups_inbox_event_type_idx_groups_inbo_event_t_b211cc_idx_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="group",
            name="deleted_by_user_id",
            field=models.UUIDField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="group",
            name="restored_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="group",
            name="title_parts",
            field=models.JSONField(blank=True, default=list),
        ),
    ]
