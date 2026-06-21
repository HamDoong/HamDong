import os
import time

from django.core.management import BaseCommand, call_command


class Command(BaseCommand):
    help = "Continuously dispatch identity outbox messages."

    def handle(self, *args, **options):
        interval = int(os.getenv("EVENT_OUTBOX_POLL_INTERVAL_SECONDS", "5"))

        self.stdout.write(
            self.style.SUCCESS(
                f"Starting identity outbox dispatcher loop every {interval} seconds..."
            )
        )

        while True:
            call_command("dispatch_outbox")
            time.sleep(interval)