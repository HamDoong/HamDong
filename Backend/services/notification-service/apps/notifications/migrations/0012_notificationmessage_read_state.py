# Legacy duplicate migration placeholder kept to avoid filename churn.
# The actual read-state migration lives in 0013_notificationmessage_read_state.py.

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("notifications", "0014_alter_notificationmessage_options"),
    ]

    operations = []
