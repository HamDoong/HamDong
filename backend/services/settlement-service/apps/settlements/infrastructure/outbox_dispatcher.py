import json
import logging

import pika
from django.conf import settings

from apps.settlements.infrastructure.repositories import OutboxRepository

logger = logging.getLogger(__name__)


class OutboxDispatcher:
    def __init__(self):
        self.batch_size = settings.EVENT_OUTBOX_BATCH_SIZE
        self.max_retry_count = settings.EVENT_MAX_RETRY_COUNT
        self.retry_delay_seconds = settings.EVENT_RETRY_DELAY_SECONDS

    def _connect(self):
        credentials = pika.PlainCredentials(
            settings.RABBITMQ_DEFAULT_USER,
            settings.RABBITMQ_DEFAULT_PASS,
        )
        params = pika.ConnectionParameters(
            host=settings.RABBITMQ_HOST,
            port=settings.RABBITMQ_PORT,
            credentials=credentials,
            heartbeat=60,
            blocked_connection_timeout=30,
        )
        connection = pika.BlockingConnection(params)
        return connection, connection.channel()

    def _publish(self, channel, message):
        channel.exchange_declare(exchange=message.exchange, exchange_type="topic", durable=True)
        channel.basic_publish(
            exchange=message.exchange,
            routing_key=message.routing_key,
            body=json.dumps(message.payload),
            properties=pika.BasicProperties(content_type="application/json", delivery_mode=2),
        )

    def dispatch(self):
        connection = None
        dispatched = 0
        try:
            connection, channel = self._connect()
            for message in OutboxRepository.pending(limit=self.batch_size):
                try:
                    self._publish(channel, message)
                    OutboxRepository.mark_sent(message)
                    dispatched += 1
                except Exception as exc:
                    logger.exception("Failed to dispatch outbox message %s", message.event_id)
                    if message.retry_count + 1 >= self.max_retry_count:
                        message.status = "FAILED"
                        message.last_error = str(exc)
                        message.retry_count += 1
                        message.save(update_fields=["status", "last_error", "retry_count", "updated_at"])
                    else:
                        OutboxRepository.mark_retry(
                            message,
                            str(exc),
                            retry_delay_seconds=self.retry_delay_seconds,
                        )
            return dispatched
        finally:
            if connection and not connection.is_closed:
                connection.close()
