import json
from django.core.management.base import BaseCommand, CommandError

from ...infrastructure.rabbitmq_consumer import ExpenseEventConsumer


class Command(BaseCommand):
    help = "Consume group events for expense-service (supports --payload for testing)"

    def add_arguments(self, parser):
        parser.add_argument("--payload", help="JSON payload of an event to process (single)")

    def handle(self, *args, **options):
        payload = options.get("payload")
        consumer = ExpenseEventConsumer()
        if payload:
            try:
                ok = consumer.process_message(payload)
                if not ok:
                    raise CommandError("Failed to process payload")
                self.stdout.write(self.style.SUCCESS("Processed payload"))
            except Exception as exc:
                raise CommandError(f"Error processing payload: {exc}")
            return

        # Placeholder: run-loop to connect to RabbitMQ would go here.
        self.stdout.write("No payload provided; consumer loop not implemented in this management command.")
from django.core.management.base import BaseCommand
from apps.expenses.infrastructure.rabbitmq_consumer import GroupConsumer


class Command(BaseCommand):
    help = "Consume group events for expense projections"

    def handle(self, *args, **options):
        consumer = GroupConsumer()
        consumer.start()
