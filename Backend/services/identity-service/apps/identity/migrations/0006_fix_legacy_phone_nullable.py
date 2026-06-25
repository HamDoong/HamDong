
from django.db import migrations


def make_legacy_phone_nullable(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
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
        migrations.RunPython(make_legacy_phone_nullable, migrations.RunPython.noop),
    ]
