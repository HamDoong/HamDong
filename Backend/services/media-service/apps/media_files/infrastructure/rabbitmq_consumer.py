from __future__ import annotations

import json
import logging
import time

import pika
from django.conf import settings

from apps.media_files.infrastructure.event_envelope import validate_event_envelope
from apps.media_files.infrastructure.repositories import (
    GroupMemberProjectionRepository,
    GroupProjectionRepository,
    InboxRepository,
    UserProjectionRepository,
)

logger = logging.getLogger(__name__)


class MediaEventConsumer:
    def __init__(self):
        self.identity_exchange = getattr(settings, "IDENTITY_RABBITMQ_EXCHANGE", "hamdong.identity")
        self.group_exchange = getattr(settings, "GROUP_RABBITMQ_EXCHANGE", "hamdong.group")
        self.identity_queue = getattr(settings, "MEDIA_IDENTITY_QUEUE", "media.identity.user_events")
        self.group_queue = getattr(settings, "MEDIA_GROUP_QUEUE", "media.group.events")
        self.retry_delay_seconds = 2

    def _connect(self):
        credentials = pika.PlainCredentials(settings.RABBITMQ_DEFAULT_USER, settings.RABBITMQ_DEFAULT_PASS)
        params = pika.ConnectionParameters(host=settings.RABBITMQ_HOST, port=settings.RABBITMQ_PORT, credentials=credentials)
        connection = pika.BlockingConnection(params)
        return connection, connection.channel()

    def process_identity_payload(self, payload: dict):
        valid, error = validate_event_envelope(payload)
        if not valid:
            raise ValueError(error)
        if InboxRepository.was_processed(payload["event_id"]):
            InboxRepository.mark_skipped(payload["event_id"], payload["event_type"], payload["source_service"], payload["routing_key"], payload)
            return
        event_type = payload["event_type"]
        data = payload["data"] or {}
        if event_type in ("UserCreated", "UserUpdated"):
            UserProjectionRepository.upsert_from_event(**data)
        InboxRepository.mark_processed(payload["event_id"], event_type, payload["source_service"], payload["routing_key"], payload)

    def process_group_payload(self, payload: dict):
        valid, error = validate_event_envelope(payload)
        if not valid:
            raise ValueError(error)
        if InboxRepository.was_processed(payload["event_id"]):
            InboxRepository.mark_skipped(payload["event_id"], payload["event_type"], payload["source_service"], payload["routing_key"], payload)
            return
        event_type = payload["event_type"]
        data = payload["data"] or {}
        if event_type == "GroupCreated":
            GroupProjectionRepository.upsert_from_event(**data)
        elif event_type == "GroupUpdated":
            GroupProjectionRepository.upsert_from_event(**data)
        elif event_type == "GroupArchived":
            GroupProjectionRepository.upsert_from_event(**{**data, "status": "ARCHIVED"})
        elif event_type == "GroupMemberJoined":
            GroupMemberProjectionRepository.upsert_joined(**data)
        elif event_type == "GroupMemberRemoved":
            GroupMemberProjectionRepository.mark_removed(**data)
        elif event_type == "GroupMemberLeft":
            GroupMemberProjectionRepository.mark_left(**data)
        InboxRepository.mark_processed(payload["event_id"], event_type, payload["source_service"], payload["routing_key"], payload)

    def _callback_identity(self, ch, method, properties, body):
        payload = None
        try:
            payload = json.loads(body.decode("utf-8") if isinstance(body,(bytes,bytearray)) else body)
            self.process_identity_payload(payload)
        except Exception as exc:
            logger.exception("Failed to process identity event")
            if isinstance(payload, dict) and payload.get("event_id"):
                InboxRepository.mark_failed(payload["event_id"], payload.get("event_type","UNKNOWN"), payload.get("source_service",""), payload.get("routing_key",""), payload, str(exc))
        finally:
            ch.basic_ack(delivery_tag=method.delivery_tag)

    def _callback_group(self, ch, method, properties, body):
        payload = None
        try:
            payload = json.loads(body.decode("utf-8") if isinstance(body,(bytes,bytearray)) else body)
            self.process_group_payload(payload)
        except Exception as exc:
            logger.exception("Failed to process group event")
            if isinstance(payload, dict) and payload.get("event_id"):
                InboxRepository.mark_failed(payload["event_id"], payload.get("event_type","UNKNOWN"), payload.get("source_service",""), payload.get("routing_key",""), payload, str(exc))
        finally:
            ch.basic_ack(delivery_tag=method.delivery_tag)

    def _declare(self, channel, exchange, queue, keys):
        dlq = f"{queue}{getattr(settings, 'EVENT_DLQ_SUFFIX', '.dlq')}"
        channel.exchange_declare(exchange=exchange, exchange_type="topic", durable=True)
        channel.queue_declare(queue=dlq, durable=True)
        channel.queue_declare(queue=queue, durable=True, arguments={"x-dead-letter-exchange": "", "x-dead-letter-routing-key": dlq})
        for key in keys:
            channel.queue_bind(queue=queue, exchange=exchange, routing_key=key)

    def start_identity_consumer(self):
        while True:
            connection = None
            try:
                connection, channel = self._connect()
                self._declare(channel, self.identity_exchange, self.identity_queue, ["identity.user.created", "identity.user.updated"])
                channel.basic_qos(prefetch_count=1)
                channel.basic_consume(queue=self.identity_queue, on_message_callback=self._callback_identity)
                channel.start_consuming()
            except KeyboardInterrupt:
                break
            except Exception:
                logger.exception("Media identity consumer unavailable; retrying")
                time.sleep(self.retry_delay_seconds)
            finally:
                if connection and not connection.is_closed:
                    connection.close()

    def start_group_consumer(self):
        while True:
            connection = None
            try:
                connection, channel = self._connect()
                self._declare(channel, self.group_exchange, self.group_queue, ["group.created", "group.updated", "group.archived", "group.member.joined", "group.member.removed", "group.member.left"])
                channel.basic_qos(prefetch_count=1)
                channel.basic_consume(queue=self.group_queue, on_message_callback=self._callback_group)
                channel.start_consuming()
            except KeyboardInterrupt:
                break
            except Exception:
                logger.exception("Media group consumer unavailable; retrying")
                time.sleep(self.retry_delay_seconds)
            finally:
                if connection and not connection.is_closed:
                    connection.close()
