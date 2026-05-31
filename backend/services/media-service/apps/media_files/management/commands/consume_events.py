from threading import Thread

from django.core.management.base import BaseCommand

from apps.media_files.infrastructure.rabbitmq_consumer import MediaEventConsumer


class Command(BaseCommand):
    help = "Consume identity and group events for media-service projections"

    def handle(self, *args, **options):
        consumer = MediaEventConsumer()
        identity_thread = Thread(target=consumer.start_identity_consumer, daemon=True)
        group_thread = Thread(target=consumer.start_group_consumer, daemon=True)
        identity_thread.start()
        group_thread.start()
        identity_thread.join()
        group_thread.join()
