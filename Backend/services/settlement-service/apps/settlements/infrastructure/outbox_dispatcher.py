from __future__ import annotations

import logging

from django.conf import settings

from apps.settlements.infrastructure.repositories import OutboxRepository
from apps.settlements.infrastructure.rabbitmq_publisher import RabbitMQPublisher

logger = logging.getLogger(__name__)


class OutboxDispatcher:
    def __init__(self):
        self.batch_size = int(getattr(settings, "EVENT_OUTBOX_BATCH_SIZE", 50))
        self.max_retry_count = int(getattr(settings, "EVENT_MAX_RETRY_COUNT", 5))
        self.publisher = RabbitMQPublisher()

    def dispatch(self) -> int:
        dispatched = 0
        for message in OutboxRepository.pending(limit=self.batch_size, max_retry_count=self.max_retry_count):
            try:
                ok = self.publisher.publish_message(message.payload, routing_key=message.routing_key, exchange=message.exchange)
                if ok:
                    OutboxRepository.mark_published(message)
                    dispatched += 1
                else:
                    OutboxRepository.mark_failed(message, "Publish returned False.")
            except Exception as exc:
                logger.exception("Failed to dispatch outbox message %s", message.event_id)
                OutboxRepository.mark_failed(message, str(exc))
        return dispatched
