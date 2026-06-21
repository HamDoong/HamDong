from django.core.management.base import BaseCommand
from apps.groups.infrastructure.consumers import IdentityUserConsumer


class Command(BaseCommand):
    help = "Consume identity user events and project users into group DB."

    def handle(self, *args, **options):
        consumer = IdentityUserConsumer()
        consumer.start()
