import json
import logging

import pika
from django.conf import settings

logger = logging.getLogger(__name__)


class RabbitMQPublisher:
    def __init__(self):
        self.exchange = getattr(settings, "EXPENSE_RABBITMQ_EXCHANGE", "hamdong.expense")
        self._connection = None
        self._channel = None

    def _connect(self):
        if self._channel is not None and getattr(self._channel, "is_open", False):
            return

        try:
            credentials = pika.PlainCredentials(
                getattr(settings, "RABBITMQ_DEFAULT_USER", "guest"),
                getattr(settings, "RABBITMQ_DEFAULT_PASS", "guest"),
            )
            params = pika.ConnectionParameters(
                host=getattr(settings, "RABBITMQ_HOST", "rabbitmq"),
                port=getattr(settings, "RABBITMQ_PORT", 5672),
                credentials=credentials,
            )
            self._connection = pika.BlockingConnection(params)
            self._channel = self._connection.channel()
            self._channel.exchange_declare(
                exchange=self.exchange,
                exchange_type="topic",
                durable=True,
            )
        except Exception:
            logger.exception("Failed to connect to RabbitMQ")
            self._connection = None
            self._channel = None

    def publish(self, event: dict) -> bool:
        routing_key = event.get("routing_key")
        if not routing_key:
            logger.error("Event missing routing_key: %s", event.get("event_type"))
            return False

        self._connect()
        if self._channel is None:
            logger.error("No channel available to publish %s", event.get("event_type"))
            return False

        try:
            self._channel.basic_publish(
                exchange=self.exchange,
                routing_key=routing_key,
                body=json.dumps(event, default=str),
                properties=pika.BasicProperties(
                    content_type="application/json",
                    delivery_mode=2,
                ),
            )
            return True
        except Exception:
            logger.exception("Failed to publish %s", event.get("event_type"))
            return False

    def close(self):
        try:
            if self._channel is not None and getattr(self._channel, "is_open", False):
                self._channel.close()
            if self._connection is not None and getattr(self._connection, "is_open", False):
                self._connection.close()
        except Exception:
            logger.exception("Failed to close RabbitMQ connection")
        finally:
            self._channel = None
            self._connection = None
