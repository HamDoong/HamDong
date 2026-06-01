from django.core.management.base import BaseCommand

from apps.settlements.infrastructure.outbox_dispatcher import OutboxDispatcher


class Command(BaseCommand):
    help = "Dispatch pending settlement-service outbox messages."

    def handle(self, *args, **options):
        dispatched = OutboxDispatcher().dispatch()
        self.stdout.write(self.style.SUCCESS(f"Dispatched {dispatched} outbox messages."))
