from django.core.management.base import BaseCommand

from apps.expenses.infrastructure.rabbitmq_consumer import IdentityConsumer


class Command(BaseCommand):
    help = "Consume identity events for expense projections."

    def handle(self, *args, **options):
        IdentityConsumer().start()
