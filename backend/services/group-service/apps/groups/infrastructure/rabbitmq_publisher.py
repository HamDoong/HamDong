"""RabbitMQ publisher for group-service events."""

import json
import logging
import pika
from django.conf import settings
from apps.groups.domain.events import make_event

logger = logging.getLogger(__name__)


class RabbitMQPublisher:
    def __init__(self):
        self.exchange = getattr(settings, "GROUP_RABBITMQ_EXCHANGE", "hamdong.group")
        self._connection = None
        self._channel = None

    def _connect(self):
        try:
            credentials = pika.PlainCredentials(settings.RABBITMQ_DEFAULT_USER, settings.RABBITMQ_DEFAULT_PASS)
            params = pika.ConnectionParameters(host=settings.RABBITMQ_HOST, port=settings.RABBITMQ_PORT, credentials=credentials)
            self._connection = pika.BlockingConnection(params)
            self._channel = self._connection.channel()
            self._channel.exchange_declare(exchange=self.exchange, exchange_type="topic", durable=True)
        except Exception:
            logger.exception("Failed to connect to RabbitMQ")
            self._connection = None
            self._channel = None

    def publish(self, event_type: str, data: dict, routing_key: str) -> bool:
        envelope = make_event(event_type, data)
        body = json.dumps(envelope)
        try:
            if not self._channel:
                self._connect()
            if not self._channel:
                logger.error("No channel available for publishing event %s", event_type)
                return False

            self._channel.basic_publish(
                exchange=self.exchange,
                routing_key=routing_key,
                body=body,
                properties=pika.BasicProperties(content_type="application/json", delivery_mode=pika.spec.PERSISTENT_DELIVERY_MODE),
            )
            logger.info("Published event %s to %s", event_type, routing_key)
            return True
        except Exception:
            logger.exception("Failed to publish event %s", event_type)
            return False
