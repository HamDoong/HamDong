from django.core.management.base import BaseCommand

from apps.dashboard.infrastructure.rabbitmq_consumer import DashboardEventConsumer


class Command(BaseCommand):
    help = "Run dashboard event consumer"

    def handle(self, *args, **options):
        DashboardEventConsumer().start_settlement_consumer()
