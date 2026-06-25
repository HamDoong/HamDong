from django.db import migrations


def forwards(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute(
        """
        ALTER TABLE users
        ALTER COLUMN legacy_phone_number DROP NOT NULL;
        """
    )


class Migration(migrations.Migration):

    dependencies = [
        ("identity", "0005_email_auth_migration"),
    ]

    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
