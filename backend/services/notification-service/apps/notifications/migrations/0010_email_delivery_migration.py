from __future__ import annotations

from django.db import migrations, models


def forwards(apps, schema_editor):
    NotificationMessage = apps.get_model("notifications", "NotificationMessage")
    NotificationJob = apps.get_model("notifications", "NotificationJob")

    for message in NotificationMessage.objects.all():
        recipient = getattr(message, "recipient_email", None) or getattr(message, "recipient", None)
        if recipient and "@" not in recipient:
            recipient = f"legacy-{str(message.id).replace('-', '')[:12]}@users.hamdong.local"
        message.recipient_email = recipient
        message.recipient = recipient or message.recipient
        message.recipient_masked = recipient or message.recipient_masked
        message.channel = "EMAIL"
        message.save(update_fields=["recipient_email", "recipient", "recipient_masked", "channel"])

    for job in NotificationJob.objects.all():
        recipient = getattr(job, "recipient_email", None) or getattr(job, "recipient", None)
        if recipient and "@" not in recipient:
            recipient = f"legacy-{str(job.id).replace('-', '')[:12]}@users.hamdong.local"
        job.recipient_email = recipient
        job.recipient = recipient or job.recipient
        job.recipient_masked = recipient or job.recipient_masked
        job.channel = "EMAIL"
        job.save(update_fields=["recipient_email", "recipient", "recipient_masked", "channel"])


class Migration(migrations.Migration):

    dependencies = [
        ("notifications", "0009_alter_notificationmessage_provider_and_more"),
    ]

    operations = [
        migrations.RenameField(
            model_name="notificationmessage",
            old_name="recipient_phone_number",
            new_name="recipient_email",
        ),
        migrations.RenameField(
            model_name="notificationjob",
            old_name="recipient_phone_number",
            new_name="recipient_email",
        ),
        migrations.AlterField(
            model_name="notificationmessage",
            name="recipient_email",
            field=models.CharField(blank=True, max_length=254, null=True),
        ),
        migrations.AlterField(
            model_name="notificationjob",
            name="recipient_email",
            field=models.CharField(blank=True, max_length=254, null=True),
        ),
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
