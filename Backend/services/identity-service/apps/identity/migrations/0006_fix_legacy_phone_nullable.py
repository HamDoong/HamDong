from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("identity", "0005_email_auth_migration"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                ALTER TABLE users
                ALTER COLUMN legacy_phone_number DROP NOT NULL;
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]