"""RabbitMQ consumers for notification-service."""

import json
import logging

import pika
from django.conf import settings

from apps.notifications.application.sms_service import SmsService

logger = logging.getLogger(__name__)


class IdentityOtpConsumer:
    def __init__(self):
        self.sms_service = SmsService()
        self.connection = None
        self.channel = None

    def _connect(self) -> bool:
        try:
            credentials = pika.PlainCredentials(
                settings.RABBITMQ_DEFAULT_USER,
                settings.RABBITMQ_DEFAULT_PASS,
            )
            self.connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host=settings.RABBITMQ_HOST,
                    port=settings.RABBITMQ_PORT,
                    credentials=credentials,
                    heartbeat=60,
                    blocked_connection_timeout=30,
                )
            )
            self.channel = self.connection.channel()
            return True
        except Exception as exc:
            logger.error("Failed to connect to RabbitMQ: %s", exc)
            return False

    def _declare_topology(self) -> None:
        self.channel.exchange_declare(
            exchange=settings.IDENTITY_RABBITMQ_EXCHANGE,
            exchange_type="topic",
            durable=True,
        )
        self.channel.exchange_declare(
            exchange=settings.IDENTITY_OTP_DLX,
            exchange_type="direct",
            durable=True,
        )
        self.channel.queue_declare(
            queue=settings.IDENTITY_OTP_DLQ,
            durable=True,
        )
        self.channel.queue_bind(
            queue=settings.IDENTITY_OTP_DLQ,
            exchange=settings.IDENTITY_OTP_DLX,
            routing_key=settings.IDENTITY_OTP_DLQ,
        )
        self.channel.queue_declare(
            queue=settings.IDENTITY_OTP_QUEUE,
            durable=True,
            arguments={
                "x-dead-letter-exchange": settings.IDENTITY_OTP_DLX,
                "x-dead-letter-routing-key": settings.IDENTITY_OTP_DLQ,
            },
        )
        self.channel.queue_bind(
            queue=settings.IDENTITY_OTP_QUEUE,
            exchange=settings.IDENTITY_RABBITMQ_EXCHANGE,
            routing_key="identity.otp.requested",
        )

    def start(self) -> None:
        if not self._connect():
            raise RuntimeError("RabbitMQ is unavailable")

        self._declare_topology()
        self.channel.basic_qos(prefetch_count=1)
        self.channel.basic_consume(
            queue=settings.IDENTITY_OTP_QUEUE,
            on_message_callback=self._handle_message,
            auto_ack=False,
        )
        logger.info(
            "Consuming OTP messages from queue=%s",
            settings.IDENTITY_OTP_QUEUE,
        )
        self.channel.start_consuming()

    def _handle_message(self, channel, method, properties, body):
        try:
            payload = json.loads(body.decode("utf-8"))
            notification_message = self.sms_service.handle_otp_command(payload)

            if notification_message.status == "FAILED":
                channel.basic_reject(delivery_tag=method.delivery_tag, requeue=False)
                return

            channel.basic_ack(delivery_tag=method.delivery_tag)
        except Exception as exc:
            logger.exception("Failed to process OTP message: %s", exc)
            channel.basic_reject(delivery_tag=method.delivery_tag, requeue=False)
