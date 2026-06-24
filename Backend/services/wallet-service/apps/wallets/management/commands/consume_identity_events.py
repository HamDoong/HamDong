from django.core.management.base import BaseCommand
from apps.wallets.infrastructure.rabbitmq_consumer import WalletEventConsumer


class Command(BaseCommand):
    help = "Consume identity events for wallet projections"

    def handle(self, *args, **options):
        WalletEventConsumer().start_identity_consumer()
