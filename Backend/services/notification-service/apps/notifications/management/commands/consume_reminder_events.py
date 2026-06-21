from django.core.management.base import BaseCommand

from apps.notifications.infrastructure.reminder_consumer import SettlementReminderConsumer


class Command(BaseCommand):
    help = "Consume settlement reminder events from RabbitMQ."

    def handle(self, *args, **options):
        SettlementReminderConsumer().start()
