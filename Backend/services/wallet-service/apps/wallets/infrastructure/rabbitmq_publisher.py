
from __future__ import annotations

import json
import logging

import pika
from django.conf import settings

from apps.wallets.infrastructure.event_envelope import build_event_envelope
from apps.wallets.infrastructure.repositories import OutboxRepository

logger = logging.getLogger(__name__)


class RabbitMQPublisher:
    def __init__(self, exchange=None):
        self.exchange = exchange or getattr(settings, "WALLET_RABBITMQ_EXCHANGE", "hamdong.wallet")

    def publish(self, event_type: str, data: dict, routing_key: str) -> bool:
        payload = data if {"event_id","event_type","event_version","occurred_at","source_service","correlation_id","causation_id","routing_key","data"} <= set(data.keys()) else build_event_envelope(
            event_type,
            data,
            source_service="wallet-service",
            routing_key=routing_key,
        )
        OutboxRepository.create(
            aggregate_type=event_type,
            aggregate_id=None,
            event_id=payload["event_id"],
            event_type=payload["event_type"],
            event_version=payload["event_version"],
            routing_key=payload["routing_key"],
            exchange=self.exchange,
            correlation_id=payload.get("correlation_id"),
            causation_id=payload.get("causation_id"),
            payload=payload,
            source_service="wallet-service",
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
            logger.exception("Failed to publish wallet outbox message")
            return False
        finally:
            if connection and not connection.is_closed:
                connection.close()
