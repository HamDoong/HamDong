import json
import logging
from threading import Thread

import pika
from django.conf import settings

from apps.settlements.application.use_cases import ExpenseEventUseCase
from apps.settlements.domain.rules import InvalidEventPayloadError
from apps.settlements.infrastructure.repositories import (
    GroupMemberProjectionRepository,
    GroupProjectionRepository,
    ProcessedEventRepository,
    UserProjectionRepository,
)

logger = logging.getLogger(__name__)


class SettlementEventConsumer:
    def __init__(self):
        self.exchange_identity = getattr(settings, "IDENTITY_RABBITMQ_EXCHANGE", "hamdong.identity")
        self.exchange_group = getattr(settings, "GROUP_RABBITMQ_EXCHANGE", "hamdong.group")
        self.exchange_expense = getattr(settings, "EXPENSE_RABBITMQ_EXCHANGE", "hamdong.expense")
        self.queue_identity = getattr(settings, "SETTLEMENT_IDENTITY_QUEUE", "settlement.identity.user_events")
        self.queue_group = getattr(settings, "SETTLEMENT_GROUP_QUEUE", "settlement.group.events")
        self.queue_expense = getattr(settings, "SETTLEMENT_EXPENSE_QUEUE", "settlement.expense.events")
        self.expense_events = ExpenseEventUseCase()

    def _connect(self):
        credentials = pika.PlainCredentials(settings.RABBITMQ_DEFAULT_USER, settings.RABBITMQ_DEFAULT_PASS)
        params = pika.ConnectionParameters(host=settings.RABBITMQ_HOST, port=settings.RABBITMQ_PORT, credentials=credentials)
        connection = pika.BlockingConnection(params)
        return connection, connection.channel()

    def _decode(self, body):
        if isinstance(body, (bytes, bytearray)):
            body = body.decode("utf-8")
        if isinstance(body, str):
            body = json.loads(body)
        if not isinstance(body, dict):
            raise InvalidEventPayloadError()
        event_type = body.get("event_type") or body.get("eventType") or body.get("type")
        data = body.get("data") if isinstance(body.get("data"), dict) else body
        event_id = body.get("event_id") or body.get("id")
        return event_id, event_type, data

    def _process(self, source_service, body, handler):
        event_id, event_type, data = self._decode(body)
        if not event_type:
            raise InvalidEventPayloadError()
        if event_id and ProcessedEventRepository.was_processed(event_id):
            return False
        handler(event_type, data)
        if event_id:
            ProcessedEventRepository.mark_processed(event_id, event_type, source_service)
        return True

    def process_identity_payload(self, payload):
        def handler(event_type, data):
            if event_type in ("UserCreated", "UserUpdated"):
                UserProjectionRepository.upsert_from_event(**data)

        return self._process("identity-service", payload, handler)

    def process_group_payload(self, payload):
        def handler(event_type, data):
            if event_type in ("GroupCreated", "GroupUpdated"):
                GroupProjectionRepository.upsert_from_event(**data)
            elif event_type == "GroupArchived":
                GroupProjectionRepository.upsert_from_event(**{**data, "status": "ARCHIVED"})
            elif event_type == "GroupMemberJoined":
                GroupMemberProjectionRepository.upsert_joined(**data)
            elif event_type == "GroupMemberRemoved":
                GroupMemberProjectionRepository.mark_removed(**data)
            elif event_type == "GroupMemberLeft":
                GroupMemberProjectionRepository.mark_left(**data)

        return self._process("group-service", payload, handler)

    def process_expense_payload(self, payload):
        return self._process("expense-service", payload, self.expense_events.handle)

    def _consume(self, queue_name, exchange_name, routing_keys, callback):
        connection, channel = self._connect()
        channel.exchange_declare(exchange=exchange_name, exchange_type="topic", durable=True)
        channel.queue_declare(queue=queue_name, durable=True)
        for routing_key in routing_keys:
            channel.queue_bind(queue=queue_name, exchange=exchange_name, routing_key=routing_key)
        channel.basic_qos(prefetch_count=10)
        channel.basic_consume(queue=queue_name, on_message_callback=callback, auto_ack=False)
        try:
            channel.start_consuming()
        finally:
            if connection and not connection.is_closed:
                connection.close()

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

    def _callback_expense(self, ch, method, properties, body):
        try:
            self.process_expense_payload(body)
        except Exception:
            logger.exception("Failed to process expense event")
        finally:
            ch.basic_ack(delivery_tag=method.delivery_tag)

    def start_identity_consumer(self):
        self._consume(self.queue_identity, self.exchange_identity, ["identity.user.created", "identity.user.updated"], self._callback_identity)

    def start_group_consumer(self):
        self._consume(
            self.queue_group,
            self.exchange_group,
            [
                "group.created",
                "group.updated",
                "group.archived",
                "group.member.joined",
                "group.member.removed",
                "group.member.left",
            ],
            self._callback_group,
        )

    def start_expense_consumer(self):
        self._consume(
            self.queue_expense,
            self.exchange_expense,
            ["expense.created", "expense.updated", "expense.deleted", "expense.participants.changed"],
            self._callback_expense,
        )

    def start_consumers(self):
        threads = [
            Thread(target=self.start_identity_consumer, daemon=True),
            Thread(target=self.start_group_consumer, daemon=True),
            Thread(target=self.start_expense_consumer, daemon=True),
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()