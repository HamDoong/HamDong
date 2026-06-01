import json
import logging

import pika
from django.conf import settings

from apps.settlements.infrastructure.event_envelope import build_event_envelope

logger = logging.getLogger(__name__)


def envelope(event_type: str, data: dict, version: int = 1) -> dict:
    return build_event_envelope(
        event_type,
        data,
        version=version,
        source_service="settlement-service",
    )


class RabbitMQPublisher:
    def __init__(self, exchange=None):
        self.exchange = exchange or getattr(
            settings, "SETTLEMENT_RABBITMQ_EXCHANGE", "hamdong.settlement"
        )

    def publish(self, event_type: str, data: dict, routing_key: str) -> bool:
        credentials = pika.PlainCredentials(
            settings.RABBITMQ_DEFAULT_USER, settings.RABBITMQ_DEFAULT_PASS
        )
        params = pika.ConnectionParameters(
            host=settings.RABBITMQ_HOST,
            port=settings.RABBITMQ_PORT,
            credentials=credentials,
        )
        connection = None
        try:
            connection = pika.BlockingConnection(params)
            channel = connection.channel()
            channel.exchange_declare(
                exchange=self.exchange, exchange_type="topic", durable=True
            )
            channel.basic_publish(
                exchange=self.exchange,
                routing_key=routing_key,
                body=json.dumps(
                    build_event_envelope(
                        event_type,
                        data,
                        version=1,
                        source_service="settlement-service",
                        routing_key=routing_key,
                    )
                ),
                properties=pika.BasicProperties(
                    content_type="application/json", delivery_mode=2
                ),
            )
            return True
        except Exception:
            logger.exception("Failed to publish %s to %s", event_type, self.exchange)
            return False
        finally:
            if connection and not connection.is_closed:
                try:
                    connection.close()
                except Exception:
                    pass
