"""Django management command to run the RabbitMQ consumer."""

from django.core.management.base import BaseCommand
from apps.notifications.infrastructure.rabbitmq_consumer import RabbitMqConsumer


class Command(BaseCommand):
    help = "Consume identity events from RabbitMQ and process OTP requests."

    def handle(self, *args, **options):
        consumer = RabbitMqConsumer()
        consumer.start_consuming()
"""Consume identity events from RabbitMQ."""

from django.core.management.base import BaseCommand

from apps.notifications.infrastructure.consumers import IdentityOtpConsumer


class Command(BaseCommand):
    help = "Consume OTP SMS commands from RabbitMQ."

    def handle(self, *args, **options):
        consumer = IdentityOtpConsumer()
        consumer.start()
