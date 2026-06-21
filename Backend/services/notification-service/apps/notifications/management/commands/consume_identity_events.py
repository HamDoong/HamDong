"""Django management command to run the identity OTP RabbitMQ consumer."""

from django.core.management.base import BaseCommand

from apps.notifications.infrastructure.consumers import IdentityOtpConsumer


class Command(BaseCommand):
    help = "Consume OTP SMS commands from RabbitMQ."

    def handle(self, *args, **options):
        consumer = IdentityOtpConsumer()
        consumer.start()
