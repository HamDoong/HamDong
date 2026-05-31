from django.core.management.base import BaseCommand

from apps.settlements.infrastructure.rabbitmq_consumer import SettlementEventConsumer


class Command(BaseCommand):
    help = "Consume group events for settlement-service projections"

    def handle(self, *args, **options):
        SettlementEventConsumer().start_group_consumer()