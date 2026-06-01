"""Publisher for expense events."""

import json
import logging
from datetime import datetime
import uuid

import pika
from django.conf import settings

logger = logging.getLogger(__name__)


def envelope(event_type: str, data: dict, version: str = "1.0") -> dict:
    return {
        "event_id": str(uuid.uuid4()),
        "event_type": event_type,
        "event_version": version,
        "occurred_at": datetime.utcnow().isoformat() + "Z",
        "version": version,
        "source_service": getattr(settings, "SERVICE_NAME", "expense-service"),
        "routing_key": None,
        "correlation_id": None,
        "causation_id": None,
        "data": data,
    }


class RabbitMQPublisher:
    def __init__(self):
        self.exchange = getattr(settings, "EXPENSE_RABBITMQ_EXCHANGE", "hamdong.expense")
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
        env = envelope(event_type, data)
        env["routing_key"] = routing_key
        body = json.dumps(env)
        try:
            if not self._channel:
                self._connect()
            if not self._channel:
                logger.error("No channel available to publish %s", event_type)
                return False
            self._channel.basic_publish(
                exchange=self.exchange,
                routing_key=routing_key,
                body=body,
                properties=pika.BasicProperties(content_type="application/json", delivery_mode=pika.spec.PERSISTENT_DELIVERY_MODE),
            )
            logger.info("Published event %s", event_type)
            return True
        except Exception:
            logger.exception("Failed to publish event %s", event_type)
            # Do not propagate publishing failures to callers; return False
            return False
