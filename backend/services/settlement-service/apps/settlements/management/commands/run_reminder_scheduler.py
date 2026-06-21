from django.core.management.base import BaseCommand

from apps.settlements.infrastructure.reminder_scheduler import SettlementReminderScheduler


class Command(BaseCommand):
    help = "Queue automatic debt reminder events for eligible settlement plan items."

    def handle(self, *args, **options):
        result = SettlementReminderScheduler().run()
        self.stdout.write(
            self.style.SUCCESS(
                f"Automatic reminders eligible={result['eligible_count']} created={result['created_count']} skipped={result['skipped_count']}"
            )
        )
