"""RabbitMQ publisher for group-service events backed by OutboxMessage."""

from __future__ import annotations

import json
import logging

import pika
from django.conf import settings

from apps.groups.domain.events import make_event
from apps.groups.infrastructure.repositories import OutboxRepository

logger = logging.getLogger(__name__)


class RabbitMQPublisher:
    def __init__(self):
        self.exchange = getattr(settings, "GROUP_RABBITMQ_EXCHANGE", "hamdong.group")

    def publish(self, event_type: str, data: dict, routing_key: str) -> bool:
        envelope = data if {"event_id","event_type","event_version","occurred_at","source_service","correlation_id","causation_id","routing_key","data"} <= set(data.keys()) else make_event(event_type, data, routing_key=routing_key)
        OutboxRepository.create(
            event_type=envelope["event_type"],
            routing_key=routing_key,
            payload=envelope,
            exchange=self.exchange,
            source_service="group-service",
        )
        return True

    def publish_message(self, payload: dict, routing_key: str | None = None, exchange: str | None = None) -> bool:
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
                body=json.dumps(payload),
                properties=pika.BasicProperties(content_type="application/json", delivery_mode=pika.spec.PERSISTENT_DELIVERY_MODE),
            )
            return True
        except Exception:
            logger.exception("Failed to publish group outbox message")
            return False
        finally:
            if connection and not connection.is_closed:
                connection.close()
