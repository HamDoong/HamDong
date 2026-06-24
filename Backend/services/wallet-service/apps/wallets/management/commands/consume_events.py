from django.core.management.base import BaseCommand
from apps.wallets.infrastructure.rabbitmq_consumer import WalletEventConsumer


class Command(BaseCommand):
    help = "Run all wallet consumers"

    def handle(self, *args, **options):
        WalletEventConsumer().start_consumers()
