from django.core.management.base import BaseCommand

from apps.notifications.infrastructure.direct_invitation_consumer import GroupDirectInvitationConsumer


class Command(BaseCommand):
    help = "Consume group direct invitation events from RabbitMQ."

    def handle(self, *args, **options):
        GroupDirectInvitationConsumer().start()
