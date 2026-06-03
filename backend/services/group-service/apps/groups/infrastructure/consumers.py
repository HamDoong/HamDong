"""RabbitMQ consumers for group-service."""

from __future__ import annotations

import json
import logging
import time

import pika
from django.conf import settings

from apps.groups.infrastructure.event_envelope import validate_event_envelope
from apps.groups.infrastructure.repositories import InboxRepository, UserProjectionRepository

logger = logging.getLogger(__name__)


class IdentityUserConsumer:
    def __init__(self):
        self.exchange = getattr(settings, "IDENTITY_RABBITMQ_EXCHANGE", "hamdong.identity")
        self.queue = getattr(settings, "GROUP_IDENTITY_QUEUE", "group.identity.user_events")
        self.dlq = f"{self.queue}{getattr(settings, 'EVENT_DLQ_SUFFIX', '.dlq')}"
        self.retry_delay_seconds = 2

    def _connect(self):
        credentials = pika.PlainCredentials(settings.RABBITMQ_DEFAULT_USER, settings.RABBITMQ_DEFAULT_PASS)
        params = pika.ConnectionParameters(host=settings.RABBITMQ_HOST, port=settings.RABBITMQ_PORT, credentials=credentials)
        self.connection = pika.BlockingConnection(params)
        self.channel = self.connection.channel()

    def _declare(self):
        self.channel.exchange_declare(exchange=self.exchange, exchange_type="topic", durable=True)
        self.channel.queue_declare(queue=self.dlq, durable=True)
        self.channel.queue_declare(
            queue=self.queue,
            durable=True,
            arguments={"x-dead-letter-exchange": "", "x-dead-letter-routing-key": self.dlq},
        )
        self.channel.queue_bind(queue=self.queue, exchange=self.exchange, routing_key="identity.user.created")
        self.channel.queue_bind(queue=self.queue, exchange=self.exchange, routing_key="identity.user.updated")

    def _safe_parse(self, body: bytes):
        try:
            if isinstance(body, (bytes, bytearray)):
                body = body.decode("utf-8")
            return json.loads(body)
        except Exception:
            logger.exception("Failed to parse message")
            return None

    def _handle_event(self, payload: dict):
        valid, error = validate_event_envelope(payload)
        if not valid:
            raise ValueError(error)
        event_id = payload["event_id"]
        if InboxRepository.was_processed(event_id):
            InboxRepository.mark_skipped(event_id, payload["event_type"], payload["source_service"], payload["routing_key"], payload)
            return
        event_type = payload["event_type"]
        data = payload["data"] or {}
        if event_type in ("UserCreated", "UserUpdated"):
            identity_user_id = data.get("user_id")
            phone = data.get("phone_number")
            if identity_user_id and phone:
                UserProjectionRepository.create_or_update(
                    identity_user_id=identity_user_id,
                    phone_number=phone,
                    display_name=data.get("display_name"),
                    first_name=data.get("first_name"),
                    last_name=data.get("last_name"),
                    role=data.get("role"),
                    is_active=data.get("is_active", True),
                )
        InboxRepository.mark_processed(event_id, event_type, payload["source_service"], payload["routing_key"], payload)

    def _callback(self, ch, method, properties, body):
        payload = self._safe_parse(body)
        if not payload:
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return
        try:
            self._handle_event(payload)
        except Exception as exc:
            logger.exception("Failed to process identity event")
            event_id = payload.get("event_id")
            if event_id:
                InboxRepository.mark_failed(event_id, payload.get("event_type", "UNKNOWN"), payload.get("source_service", "identity-service"), payload.get("routing_key", ""), payload, str(exc))
        finally:
            ch.basic_ack(delivery_tag=method.delivery_tag)

    def start(self):
        while True:
            try:
                self._connect()
                self._declare()
                self.channel.basic_qos(prefetch_count=1)
                self.channel.basic_consume(queue=self.queue, on_message_callback=self._callback)
                logger.info("Starting identity consumer for queue=%s", self.queue)
                self.channel.start_consuming()
            except KeyboardInterrupt:
                break
            except Exception:
                logger.exception("Group identity consumer unavailable; retrying")
                time.sleep(self.retry_delay_seconds)
            finally:
                if getattr(self, "connection", None) and not self.connection.is_closed:
                    self.connection.close()
