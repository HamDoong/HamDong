import json

from django.core.management.base import BaseCommand

from apps.media_files.infrastructure.rabbitmq_consumer import MediaEventConsumer


class Command(BaseCommand):
    help = "Consume group events for media-service projections"

    def add_arguments(self, parser):
        parser.add_argument("--payload", type=str, default=None)

    def handle(self, *args, **options):
        consumer = MediaEventConsumer()
        payload = options.get("payload")
        if payload:
            try:
                consumer.process_group_payload(json.loads(payload))
                self.stdout.write(self.style.SUCCESS("Processed group payload."))
            except Exception as exc:
                self.stderr.write(str(exc))
            return
        consumer.start_group_consumer()
