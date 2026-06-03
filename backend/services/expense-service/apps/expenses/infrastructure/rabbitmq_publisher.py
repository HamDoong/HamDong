"""RabbitMQ publisher for settlement-compatible expense events."""

from __future__ import annotations

import json
import logging
from typing import Any

import pika
from django.conf import settings

from apps.expenses.domain.events import event_envelope

logger = logging.getLogger(__name__)


class RabbitMQPublisher:
    """Publish expense-service event envelopes to RabbitMQ."""

    def __init__(self) -> None:
        self.exchange = getattr(settings, "EXPENSE_RABBITMQ_EXCHANGE", "hamdong.expense")
        self._connection = None
        self._channel = None

    def _connect(self) -> None:
        try:
            credentials = pika.PlainCredentials(
                settings.RABBITMQ_DEFAULT_USER,
                settings.RABBITMQ_DEFAULT_PASS,
            )
            params = pika.ConnectionParameters(
                host=settings.RABBITMQ_HOST,
                port=settings.RABBITMQ_PORT,
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

    def publish_event(self, event: dict[str, Any]) -> bool:
        """Publish a fully built event envelope."""
        routing_key = event["routing_key"]
        body = json.dumps(event, default=str)

        try:
            if not self._channel:
                self._connect()

            if not self._channel:
                logger.error("No RabbitMQ channel available for %s", event.get("event_type"))
                return False

            self._channel.basic_publish(
                exchange=self.exchange,
                routing_key=routing_key,
                body=body,
                properties=pika.BasicProperties(
                    content_type="application/json",
                    delivery_mode=pika.spec.PERSISTENT_DELIVERY_MODE,
                ),
            )
            return True
        except Exception:
            logger.exception("Failed to publish event %s", event.get("event_type"))
            return False

    def publish(self, event_type: str, data: dict[str, Any], routing_key: str | None = None) -> bool:
        """Backward-compatible publisher API."""
        event = event_envelope(event_type, data)
        if routing_key:
            event["routing_key"] = routing_key
        return self.publish_event(event)
