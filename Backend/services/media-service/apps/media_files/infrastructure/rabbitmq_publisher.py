from __future__ import annotations

import json
import logging

import pika
from django.conf import settings

from apps.media_files.domain.events import ROUTING_KEYS
from apps.media_files.infrastructure.event_envelope import build_event_envelope
from apps.media_files.infrastructure.repositories import OutboxRepository

logger = logging.getLogger(__name__)


class RabbitMQPublisher:
    def __init__(self, exchange=None):
        self.exchange = exchange or getattr(settings, "MEDIA_RABBITMQ_EXCHANGE", "hamdong.media")

    def publish(self, event_type: str, data: dict, routing_key: str) -> bool:
        envelope = data if {"event_id","event_type","event_version","occurred_at","source_service","correlation_id","causation_id","routing_key","data"} <= set(data.keys()) else build_event_envelope(
            event_type,
            data,
            source_service="media-service",
            routing_key=routing_key or ROUTING_KEYS[event_type],
        )
        OutboxRepository.create(
            event_type=envelope["event_type"],
            routing_key=envelope["routing_key"],
            payload=envelope,
            exchange=self.exchange,
            source_service="media-service",
        )
        return True

    def publish_message(self, payload: dict, routing_key: str | None = None, exchange: str | None = None) -> bool:
        credentials = pika.PlainCredentials(settings.RABBITMQ_DEFAULT_USER, settings.RABBITMQ_DEFAULT_PASS)
        params = pika.ConnectionParameters(host=settings.RABBITMQ_HOST, port=settings.RABBITMQ_PORT, credentials=credentials)
        connection = None
        try:
            connection = pika.BlockingConnection(params)
            channel = connection.channel()
            channel.exchange_declare(exchange=exchange or self.exchange, exchange_type="topic", durable=True)
            channel.basic_publish(
                exchange=exchange or self.exchange,
                routing_key=routing_key or payload["routing_key"],
                body=json.dumps(payload),
                properties=pika.BasicProperties(content_type="application/json", delivery_mode=2),
            )
            return True
        except Exception:
            logger.exception("Failed to publish media outbox message")
            return False
        finally:
            if connection and not connection.is_closed:
                connection.close()
