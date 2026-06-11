"""RabbitMQ publisher for expense-service event envelopes."""

from __future__ import annotations

import json
import logging
from typing import Any

import pika
from django.conf import settings

from apps.expenses.domain.events import event_envelope
from apps.expenses.infrastructure.repositories import OutboxRepository

logger = logging.getLogger(__name__)


class RabbitMQPublisher:
    def __init__(self) -> None:
        self.exchange = getattr(settings, "EXPENSE_RABBITMQ_EXCHANGE", "hamdong.expense")

    def queue_event(self, event: dict[str, Any]) -> bool:
        OutboxRepository.create(
            event_type=event["event_type"],
            routing_key=event["routing_key"],
            payload=event,
            exchange=self.exchange,
            source_service="expense-service",
        )
        return True

    def publish_event(self, event: dict[str, Any]) -> bool:
        return self.queue_event(event)

    def publish(self, event_type: str, data: dict[str, Any], routing_key: str | None = None) -> bool:
        if {"event_id","event_type","event_version","occurred_at","source_service","correlation_id","causation_id","routing_key","data"} <= set(data.keys()):
            event = data
        else:
            event = event_envelope(event_type, data)
            if routing_key:
                event["routing_key"] = routing_key
        return self.queue_event(event)

    def publish_message(self, payload: dict[str, Any], routing_key: str | None = None, exchange: str | None = None) -> bool:
        connection = None
        try:
            credentials = pika.PlainCredentials(settings.RABBITMQ_DEFAULT_USER, settings.RABBITMQ_DEFAULT_PASS)
            params = pika.ConnectionParameters(host=settings.RABBITMQ_HOST, port=settings.RABBITMQ_PORT, credentials=credentials)
            connection = pika.BlockingConnection(params)
            channel = connection.channel()
            channel.exchange_declare(exchange=exchange or self.exchange, exchange_type="topic", durable=True)
            channel.basic_publish(
                exchange=exchange or self.exchange,
                routing_key=routing_key or payload["routing_key"],
                body=json.dumps(payload, default=str),
                properties=pika.BasicProperties(content_type="application/json", delivery_mode=pika.spec.PERSISTENT_DELIVERY_MODE),
            )
            return True
        except Exception:
            logger.exception("Failed to publish expense outbox message")
            return False
        finally:
            if connection and not connection.is_closed:
                connection.close()
