"""RabbitMQ event publisher."""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, Any

import pika
from django.conf import settings

logger = logging.getLogger(__name__)


class RabbitMqPublisher:
    """Publishes identity events to RabbitMQ."""

    def __init__(self):
        self.exchange = settings.IDENTITY_RABBITMQ_EXCHANGE
        self.connection = None
        self.channel = None

    def _connect(self) -> bool:
        """Establish connection to RabbitMQ."""
        try:
            credentials = pika.PlainCredentials(
                settings.RABBITMQ_DEFAULT_USER,
                settings.RABBITMQ_DEFAULT_PASS,
            )
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host=settings.RABBITMQ_HOST,
                    port=settings.RABBITMQ_PORT,
                    credentials=credentials,
                    connection_attempts=3,
                    retry_delay=2,
                )
            )
            self.channel = connection.channel()
            self.connection = connection
            return True
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            return False

    def _ensure_exchange(self) -> bool:
        """Ensure exchange exists."""
        try:
            if not self.channel:
                return False
            self.channel.exchange_declare(
                exchange=self.exchange,
                exchange_type="topic",
                durable=True,
            )
            return True
        except Exception as e:
            logger.error(f"Failed to declare exchange: {e}")
            return False

    def publish(self, event_data: Dict[str, Any], routing_key: str) -> bool:
        """
        Publish event to RabbitMQ.

        Args:
            event_data: Event data as dictionary
            routing_key: RabbitMQ routing key

        Returns:
            True if published successfully, False otherwise
        """
        try:
            if not self.channel or self.connection.is_closed:
                if not self._connect():
                    logger.warning("Skipping event publish - RabbitMQ unavailable")
                    return False

            if not self._ensure_exchange():
                logger.warning("Skipping event publish - exchange not available")
                return False

            message = json.dumps(self._build_envelope(event_data, routing_key))
            self.channel.basic_publish(
                exchange=self.exchange,
                routing_key=routing_key,
                body=message,
                properties=pika.BasicProperties(
                    content_type="application/json",
                    delivery_mode=pika.spec.PERSISTENT_DELIVERY_MODE,
                ),
            )

            logger.info(
                f"Published event to RabbitMQ: {event_data.get('event_type', 'Unknown')} "
                f"(routing_key: {routing_key})"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to publish event to RabbitMQ: {e}")
            return False

    def _build_envelope(self, event_data: Dict[str, Any], routing_key: str) -> Dict[str, Any]:
        envelope = dict(event_data)
        envelope.setdefault("event_id", str(uuid.uuid4()))
        envelope.setdefault("event_version", envelope.get("version", 1))
        envelope.setdefault("version", envelope["event_version"])
        envelope.setdefault("occurred_at", datetime.now(timezone.utc).isoformat())
        envelope.setdefault("source_service", getattr(settings, "SERVICE_NAME", "identity-service"))
        envelope["routing_key"] = routing_key
        envelope.setdefault("correlation_id", None)
        envelope.setdefault("causation_id", None)
        if "data" not in envelope:
            envelope["data"] = {}
        return envelope

    def close(self):
        """Close connection."""
        try:
            if self.connection and not self.connection.is_closed:
                self.connection.close()
        except Exception as e:
            logger.error(f"Error closing RabbitMQ connection: {e}")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
