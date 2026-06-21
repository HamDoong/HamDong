from django.core.management.base import BaseCommand

from apps.expenses.infrastructure.rabbitmq_consumer import GroupConsumer


class Command(BaseCommand):
    help = "Consume group events for expense projections."

    def handle(self, *args, **options):
        GroupConsumer().start()
