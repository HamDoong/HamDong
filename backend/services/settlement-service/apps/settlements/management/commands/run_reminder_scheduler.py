from django.core.management.base import BaseCommand

from apps.settlements.infrastructure.reminder_scheduler import SettlementReminderScheduler


class Command(BaseCommand):
    help = "Queue reminder events for pending settlement work."

    def handle(self, *args, **options):
        queued = SettlementReminderScheduler().run()
        self.stdout.write(self.style.SUCCESS(f"Queued {len(queued)} reminder messages."))
