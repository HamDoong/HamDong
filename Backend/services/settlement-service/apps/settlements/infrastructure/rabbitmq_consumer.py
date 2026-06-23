from __future__ import annotations

import json
import logging
import time
import threading

import pika
from django.conf import settings

from apps.settlements.application.reminder_service import ReminderService
from apps.settlements.application.use_cases import ExpenseEventUseCase
from apps.settlements.infrastructure.event_envelope import validate_event_envelope
from apps.settlements.infrastructure.repositories import (
    BankCardProjectionRepository,
    GroupMemberProjectionRepository,
    GroupProjectionRepository,
    InboxRepository,
    ProcessedEventRepository,
    UserProjectionRepository,
)

logger = logging.getLogger(__name__)


class SettlementEventConsumer:
    def __init__(self):
        self.exchange_identity = getattr(settings, "IDENTITY_RABBITMQ_EXCHANGE", "hamdong.identity")
        self.exchange_group = getattr(settings, "GROUP_RABBITMQ_EXCHANGE", "hamdong.group")
        self.exchange_expense = getattr(settings, "EXPENSE_RABBITMQ_EXCHANGE", "hamdong.expense")
        self.exchange_notification = getattr(settings, "NOTIFICATION_RABBITMQ_EXCHANGE", "hamdong.notification")
        self.queue_identity = getattr(settings, "SETTLEMENT_IDENTITY_QUEUE", "settlement.identity.user_events")
        self.queue_group = getattr(settings, "SETTLEMENT_GROUP_QUEUE", "settlement.group.events")
        self.queue_expense = getattr(settings, "SETTLEMENT_EXPENSE_QUEUE", "settlement.expense.events")
        self.queue_notification = getattr(settings, "SETTLEMENT_NOTIFICATION_QUEUE", "settlement.notification.events")
        self.retry_delay_seconds = 2
        self.expense_events = ExpenseEventUseCase()
        self.reminder_service = ReminderService()

    def _connect(self):
        credentials = pika.PlainCredentials(settings.RABBITMQ_DEFAULT_USER, settings.RABBITMQ_DEFAULT_PASS)
        params = pika.ConnectionParameters(host=settings.RABBITMQ_HOST, port=settings.RABBITMQ_PORT, credentials=credentials)
        connection = pika.BlockingConnection(params)
        return connection, connection.channel()

    def _parse(self, body):
        if isinstance(body, (bytes, bytearray)):
            body = body.decode("utf-8")
        return json.loads(body)

    def _declare(self, channel, exchange, queue, routing_keys):
        dlq = f"{queue}{getattr(settings, 'EVENT_DLQ_SUFFIX', '.dlq')}"
        channel.exchange_declare(exchange=exchange, exchange_type="topic", durable=True)
        channel.queue_declare(queue=dlq, durable=True)
        channel.queue_declare(queue=queue, durable=True, arguments={"x-dead-letter-exchange": "", "x-dead-letter-routing-key": dlq})
        for key in routing_keys:
            channel.queue_bind(queue=queue, exchange=exchange, routing_key=key)

    def _process(self, payload, handler):
        valid, error = validate_event_envelope(payload)
        if not valid:
            raise ValueError(error)
        event_id = payload["event_id"]
        if InboxRepository.was_processed(event_id):
            InboxRepository.mark_skipped(event_id, payload["event_type"], payload["source_service"], payload["routing_key"], payload)
            return
        handler(payload["event_type"], payload["data"] or {})
        InboxRepository.mark_processed(event_id, payload["event_type"], payload["source_service"], payload["routing_key"], payload)

    def _legacy_process(self, payload, handler):
        if not isinstance(payload, dict):
            raise ValueError("Invalid event payload.")
        event_id = payload.get("event_id")
        event_type = payload.get("event_type")
        if not event_id or not event_type:
            raise ValueError("Invalid event payload.")
        if ProcessedEventRepository.was_processed(event_id):
            return False
        handler(event_type, payload.get("data") or {})
        ProcessedEventRepository.mark_processed(
            event_id,
            event_type,
            payload.get("source_service") or "",
        )
        return True

    def process_identity_payload(self, payload: dict):
        return self._legacy_process(payload, self._handle_identity)

    def process_group_payload(self, payload: dict):
        return self._legacy_process(payload, self._handle_group)

    def process_expense_payload(self, payload: dict):
        return self._legacy_process(payload, self._handle_expense)

    def _callback_identity(self, ch, method, properties, body):
        payload = None
        try:
            payload = self._parse(body)
            self.process_identity_payload(payload)
        except Exception as exc:
            logger.exception("Failed to process identity event")
            if isinstance(payload, dict) and payload.get("event_id"):
                InboxRepository.mark_failed(
                    payload["event_id"],
                    payload.get("event_type", "UNKNOWN"),
                    payload.get("source_service", ""),
                    payload.get("routing_key", ""),
                    payload,
                    str(exc),
                )
        finally:
            ch.basic_ack(delivery_tag=method.delivery_tag)

    def _callback_group(self, ch, method, properties, body):
        payload = None
        try:
            payload = self._parse(body)
            self.process_group_payload(payload)
        except Exception as exc:
            logger.exception("Failed to process group event")
            if isinstance(payload, dict) and payload.get("event_id"):
                InboxRepository.mark_failed(
                    payload["event_id"],
                    payload.get("event_type", "UNKNOWN"),
                    payload.get("source_service", ""),
                    payload.get("routing_key", ""),
                    payload,
                    str(exc),
                )
        finally:
            ch.basic_ack(delivery_tag=method.delivery_tag)

    def _callback_expense(self, ch, method, properties, body):
        payload = None
        try:
            payload = self._parse(body)
            self.process_expense_payload(payload)
        except Exception as exc:
            logger.exception("Failed to process expense event")
            if isinstance(payload, dict) and payload.get("event_id"):
                InboxRepository.mark_failed(
                    payload["event_id"],
                    payload.get("event_type", "UNKNOWN"),
                    payload.get("source_service", ""),
                    payload.get("routing_key", ""),
                    payload,
                    str(exc),
                )
        finally:
            ch.basic_ack(delivery_tag=method.delivery_tag)

    def _handle_identity(self, event_type, data):
        if event_type in ("UserCreated", "UserUpdated"):
            UserProjectionRepository.upsert_from_event(**data)
        elif event_type in ("UserBankCardCreated", "UserBankCardUpdated", "UserBankCardDeactivated"):
            BankCardProjectionRepository.upsert_from_event(**data)

    def _handle_group(self, event_type, data):
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

    def _handle_expense(self, event_type, data):
        self.expense_events.handle(event_type, data)

    def _handle_notification(self, event_type, data):
        if event_type == "DebtReminderDeliveryUpdated":
            self.reminder_service.apply_delivery_update(data)

    def _callback_factory(self, handler):
        def _callback(ch, method, properties, body):
            payload = None
            try:
                payload = self._parse(body)
                self._process(payload, handler)
            except Exception as exc:
                logger.exception("Failed to process settlement event")
                if isinstance(payload, dict) and payload.get("event_id"):
                    InboxRepository.mark_failed(payload["event_id"], payload.get("event_type","UNKNOWN"), payload.get("source_service",""), payload.get("routing_key",""), payload, str(exc))
            finally:
                ch.basic_ack(delivery_tag=method.delivery_tag)
        return _callback

    def _start_queue(self, exchange, queue, routing_keys, callback):
        while True:
            connection = None
            try:
                connection, channel = self._connect()
                self._declare(channel, exchange, queue, routing_keys)
                channel.basic_qos(prefetch_count=1)
                channel.basic_consume(queue=queue, on_message_callback=callback)
                channel.start_consuming()
            except KeyboardInterrupt:
                break
            except Exception:
                logger.exception("Settlement consumer unavailable; retrying")
                time.sleep(self.retry_delay_seconds)
            finally:
                if connection and not connection.is_closed:
                    connection.close()

    def start_consumers(self):
        workers = [
            ("identity", self.start_identity_consumer),
            ("group", self.start_group_consumer),
            ("expense", self.start_expense_consumer),
            ("notification", self.start_notification_consumer),
        ]

        threads = []

        for name, target in workers:
            thread = threading.Thread(
                target=target,
                name=f"settlement-{name}-consumer",
                daemon=False,
            )
            thread.start()
            threads.append(thread)
            logger.info("Started settlement %s consumer thread", name)

        for thread in threads:
            thread.join()

    def start_identity_consumer(self):
        self._start_queue(self.exchange_identity, self.queue_identity, ["identity.user.created", "identity.user.updated", "identity.user_bank_card.created", "identity.user_bank_card.updated", "identity.user_bank_card.deactivated"], self._callback_factory(self._handle_identity))

    def start_group_consumer(self):
        self._start_queue(self.exchange_group, self.queue_group, ["group.created", "group.updated", "group.archived", "group.member.joined", "group.member.removed", "group.member.left"], self._callback_factory(self._handle_group))

    def start_expense_consumer(self):
        self._start_queue(self.exchange_expense, self.queue_expense, ["expense.created", "expense.updated", "expense.deleted", "expense.participants.changed"], self._callback_factory(self._handle_expense))

    def start_notification_consumer(self):
        self._start_queue(
            self.exchange_notification,
            self.queue_notification,
            ["notification.debt_reminder.delivery.updated"],
            self._callback_factory(self._handle_notification),
        )
