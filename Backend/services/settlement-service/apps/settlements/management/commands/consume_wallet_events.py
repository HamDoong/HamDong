from django.core.management.base import BaseCommand

from apps.settlements.infrastructure.rabbitmq_consumer import SettlementEventConsumer


class Command(BaseCommand):
    help = "Consume wallet events for settlement-service"

    def handle(self, *args, **options):
        SettlementEventConsumer().start_wallet_consumer()
