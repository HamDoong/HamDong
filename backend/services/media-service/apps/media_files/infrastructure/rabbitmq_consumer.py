import json
import logging

import pika
from django.conf import settings

from apps.media_files.infrastructure.repositories import GroupMemberProjectionRepository, GroupProjectionRepository, UserProjectionRepository

logger = logging.getLogger(__name__)


class MediaEventConsumer:
    def __init__(self):
        self.identity_exchange = getattr(settings, "IDENTITY_RABBITMQ_EXCHANGE", "hamdong.identity")
        self.group_exchange = getattr(settings, "GROUP_RABBITMQ_EXCHANGE", "hamdong.group")
        self.identity_queue = getattr(settings, "MEDIA_IDENTITY_QUEUE", "media.identity.user_events")
        self.group_queue = getattr(settings, "MEDIA_GROUP_QUEUE", "media.group.events")

    def _connect(self):
        credentials = pika.PlainCredentials(settings.RABBITMQ_DEFAULT_USER, settings.RABBITMQ_DEFAULT_PASS)
        params = pika.ConnectionParameters(host=settings.RABBITMQ_HOST, port=settings.RABBITMQ_PORT, credentials=credentials)
        connection = pika.BlockingConnection(params)
        return connection, connection.channel()

    def _as_payload(self, payload):
        if isinstance(payload, (bytes, bytearray)):
            payload = payload.decode("utf-8")
        if isinstance(payload, str):
            payload = json.loads(payload)
        if not isinstance(payload, dict):
            raise ValueError("Payload must be a JSON object")
        return payload

    def _event_type(self, payload: dict):
        return payload.get("event_type") or payload.get("eventType") or payload.get("type")

    def _event_data(self, payload: dict):
        data = payload.get("data")
        if isinstance(data, dict):
            return data
        if data is None:
            return {}
        raise ValueError("Event data must be an object")

    def process_identity_payload(self, payload: dict):
        payload = self._as_payload(payload)
        event_type = self._event_type(payload)
        data = self._event_data(payload)
        if event_type in ("UserCreated", "UserUpdated"):
            UserProjectionRepository.upsert_from_event(**data)

    def process_group_payload(self, payload: dict):
        payload = self._as_payload(payload)
        event_type = self._event_type(payload)
        data = self._event_data(payload)
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

    def _callback_identity(self, ch, method, properties, body):
        try:
            self.process_identity_payload(body)
        except Exception:
            logger.exception("Failed to process identity event")
        finally:
            ch.basic_ack(delivery_tag=method.delivery_tag)

    def _callback_group(self, ch, method, properties, body):
        try:
            self.process_group_payload(body)
        except Exception:
            logger.exception("Failed to process group event")
        finally:
            ch.basic_ack(delivery_tag=method.delivery_tag)

    def start_identity_consumer(self):
        connection, channel = self._connect()
        channel.exchange_declare(exchange=self.identity_exchange, exchange_type="topic", durable=True)
        channel.queue_declare(queue=self.identity_queue, durable=True)
        channel.queue_bind(queue=self.identity_queue, exchange=self.identity_exchange, routing_key="identity.user.created")
        channel.queue_bind(queue=self.identity_queue, exchange=self.identity_exchange, routing_key="identity.user.updated")
        channel.basic_qos(prefetch_count=1)
        channel.basic_consume(queue=self.identity_queue, on_message_callback=self._callback_identity)
        try:
            channel.start_consuming()
        finally:
            connection.close()

    def start_group_consumer(self):
        connection, channel = self._connect()
        channel.exchange_declare(exchange=self.group_exchange, exchange_type="topic", durable=True)
        channel.queue_declare(queue=self.group_queue, durable=True)
        for routing_key in ["group.created", "group.updated", "group.archived", "group.member.joined", "group.member.removed", "group.member.left"]:
            channel.queue_bind(queue=self.group_queue, exchange=self.group_exchange, routing_key=routing_key)
        channel.basic_qos(prefetch_count=1)
        channel.basic_consume(queue=self.group_queue, on_message_callback=self._callback_group)
        try:
            channel.start_consuming()
        finally:
            connection.close()
