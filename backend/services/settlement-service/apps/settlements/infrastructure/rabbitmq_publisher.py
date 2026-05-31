import json
import logging

import pika
from django.conf import settings

logger = logging.getLogger(__name__)


def envelope(event_type: str, data: dict, version: int = 1) -> dict:
    from datetime import datetime, timezone
    import uuid

    return {
        "event_id": str(uuid.uuid4()),
        "event_type": event_type,
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "version": version,
        "data": data,
    }


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
                body=json.dumps(envelope(event_type, data)),
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
