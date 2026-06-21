import os
import time

from django.core.management import BaseCommand, call_command


class Command(BaseCommand):
    help = "Continuously run settlement reminder scheduler."

    def handle(self, *args, **options):
        interval = int(os.getenv("REMINDER_SCHEDULER_INTERVAL_SECONDS", "3600"))

        self.stdout.write(
            self.style.SUCCESS(
                f"Starting reminder scheduler loop every {interval} seconds..."
            )
        )

        while True:
            call_command("run_reminder_scheduler")
            time.sleep(interval)