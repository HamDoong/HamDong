from django.core.management.base import BaseCommand

from apps.identity.infrastructure.outbox_dispatcher import OutboxDispatcher


class Command(BaseCommand):
    help = "Dispatch pending outbox messages."

    def handle(self, *args, **options):
        count = OutboxDispatcher().dispatch()
        self.stdout.write(self.style.SUCCESS(f"Dispatched {count} outbox messages."))
