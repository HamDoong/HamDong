"""RabbitMQ event publisher for identity-service with transactional outbox."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict

import pika
from django.conf import settings

from apps.identity.infrastructure.event_envelope import build_event_envelope
from apps.identity.infrastructure.repositories import OutboxRepository

logger = logging.getLogger(__name__)


class RabbitMqPublisher:
    def __init__(self):
        self.exchange = getattr(settings, "IDENTITY_RABBITMQ_EXCHANGE", "hamdong.identity")

    def queue(self, event_type: str, data: dict[str, Any], routing_key: str, *, source_service: str = "identity-service") -> bool:
        envelope = data if {"event_id","event_type","event_version","occurred_at","source_service","correlation_id","causation_id","routing_key","data"} <= set(data.keys()) else build_event_envelope(
            event_type,
            data,
            source_service=source_service,
            routing_key=routing_key,
        )
        OutboxRepository.create(
            event_type=envelope["event_type"],
            routing_key=routing_key,
            payload=envelope,
            exchange=self.exchange,
            source_service=source_service,
        )
        return True

    def publish(self, event_data: Dict[str, Any], routing_key: str) -> bool:
        event_type = event_data.get("event_type") or "Unknown"
        payload = event_data.get("data") if "data" in event_data else event_data
        return self.queue(event_type, payload if "data" not in event_data else event_data, routing_key)

    def publish_message(self, payload: dict[str, Any], routing_key: str | None = None, exchange: str | None = None) -> bool:
        credentials = pika.PlainCredentials(settings.RABBITMQ_DEFAULT_USER, settings.RABBITMQ_DEFAULT_PASS)
        params = pika.ConnectionParameters(host=settings.RABBITMQ_HOST, port=settings.RABBITMQ_PORT, credentials=credentials, connection_attempts=3, retry_delay=2)
        connection = None
        try:
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
            logger.exception("Failed to publish identity outbox message")
            return False
        finally:
            if connection and not connection.is_closed:
                connection.close()
