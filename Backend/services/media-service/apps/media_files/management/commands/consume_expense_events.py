import json

from django.core.management.base import BaseCommand

from apps.media_files.infrastructure.rabbitmq_consumer import MediaEventConsumer


class Command(BaseCommand):
    help = "Consume expense events for media-service projections"

    def add_arguments(self, parser):
        parser.add_argument("--payload", type=str, default=None)

    def handle(self, *args, **options):
        consumer = MediaEventConsumer()
        payload = options.get("payload")
        if payload:
            try:
                consumer.process_expense_payload(json.loads(payload))
                self.stdout.write(self.style.SUCCESS("Processed expense payload."))
            except Exception as exc:  # noqa: BLE001
                self.stderr.write(str(exc))
            return
        consumer.start_expense_consumer()
