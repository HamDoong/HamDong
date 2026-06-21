from django.core.management.base import BaseCommand

from apps.settlements.infrastructure.rabbitmq_consumer import SettlementEventConsumer


class Command(BaseCommand):
    help = "Consume expense events for settlement-service projections"

    def handle(self, *args, **options):
        SettlementEventConsumer().start_expense_consumer()
