
from __future__ import annotations

import json
import logging
import threading
import time

import pika
from django.conf import settings

from apps.wallets.domain.models import (
    SettlementItemStatusChoices,
    SettlementPlanStatusChoices,
)
from apps.wallets.infrastructure.event_envelope import validate_event_envelope
from apps.wallets.infrastructure.repositories import (
    InboxRepository,
    SettlementItemProjectionRepository,
    UserProjectionRepository,
)

logger = logging.getLogger(__name__)


class WalletEventConsumer:
    def __init__(self):
        self.exchange_identity = getattr(settings, "IDENTITY_RABBITMQ_EXCHANGE", "hamdong.identity")
        self.exchange_settlement = getattr(settings, "SETTLEMENT_RABBITMQ_EXCHANGE", "hamdong.settlement")
        self.queue_identity = getattr(settings, "WALLET_IDENTITY_QUEUE", "wallet.identity.user_events")
        self.queue_settlement = getattr(settings, "WALLET_SETTLEMENT_QUEUE", "wallet.settlement.events")

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
        handler(payload["event_type"], payload["data"] or {}, payload.get("occurred_at"))
        InboxRepository.mark_processed(event_id, payload["event_type"], payload["source_service"], payload["routing_key"], payload)

    def process_identity_payload(self, payload: dict):
        self._process(payload, self._handle_identity)

    def process_settlement_payload(self, payload: dict):
        self._process(payload, self._handle_settlement)

    def _handle_identity(self, event_type: str, data: dict, occurred_at=None):
        if event_type in {"UserCreated", "UserUpdated"}:
            UserProjectionRepository.upsert_from_event(**data)

    def _handle_settlement(self, event_type: str, data: dict, occurred_at=None):
        if event_type == "SettlementPlanGenerated":
            SettlementItemProjectionRepository.upsert_from_generated(
                plan_id=data.get("plan_id"),
                group_id=data.get("group_id"),
                currency=data.get("currency") or "IRR",
                plan_status=data.get("status") or SettlementPlanStatusChoices.DRAFT,
                items=data.get("items") or [],
                occurred_at=occurred_at,
            )
        elif event_type == "SettlementPlanActivated":
            SettlementItemProjectionRepository.update_plan_status(
                data.get("plan_id"), SettlementPlanStatusChoices.ACTIVE, occurred_at
            )
        elif event_type == "SettlementPlanCancelled":
            SettlementItemProjectionRepository.update_plan_status(
                data.get("plan_id"), SettlementPlanStatusChoices.CANCELLED, occurred_at
            )
        elif event_type == "SettlementPlanExpired":
            SettlementItemProjectionRepository.update_plan_status(
                data.get("plan_id"), SettlementPlanStatusChoices.EXPIRED, occurred_at
            )
        elif event_type == "SettlementPlanCompleted":
            SettlementItemProjectionRepository.update_plan_status(
                data.get("plan_id"), SettlementPlanStatusChoices.COMPLETED, occurred_at
            )
        elif event_type == "SettlementPlanItemReported":
            SettlementItemProjectionRepository.update_item_status(
                data.get("item_id"), SettlementItemStatusChoices.REPORTED, occurred_at
            )
        elif event_type == "SettlementPlanItemConfirmed":
            SettlementItemProjectionRepository.update_item_status(
                data.get("item_id"), SettlementItemStatusChoices.CONFIRMED, occurred_at
            )
        elif event_type == "SettlementPlanItemRejected":
            SettlementItemProjectionRepository.update_item_status(
                data.get("item_id"), SettlementItemStatusChoices.REJECTED, occurred_at
            )

    def _callback_identity(self, ch, method, properties, body):
        payload = None
        try:
            payload = self._parse(body)
            self.process_identity_payload(payload)
            ch.basic_ack(delivery_tag=method.delivery_tag)
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
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

    def _callback_settlement(self, ch, method, properties, body):
        payload = None
        try:
            payload = self._parse(body)
            self.process_settlement_payload(payload)
            ch.basic_ack(delivery_tag=method.delivery_tag)
        except Exception as exc:
            logger.exception("Failed to process settlement event")
            if isinstance(payload, dict) and payload.get("event_id"):
                InboxRepository.mark_failed(
                    payload["event_id"],
                    payload.get("event_type", "UNKNOWN"),
                    payload.get("source_service", ""),
                    payload.get("routing_key", ""),
                    payload,
                    str(exc),
                )
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

    def start_identity_consumer(self):
        connection, channel = self._connect()
        self._declare(channel, self.exchange_identity, self.queue_identity, ["identity.user.created", "identity.user.updated"])
        channel.basic_qos(prefetch_count=20)
        channel.basic_consume(queue=self.queue_identity, on_message_callback=self._callback_identity)
        try:
            channel.start_consuming()
        finally:
            if connection and not connection.is_closed:
                connection.close()

    def start_settlement_consumer(self):
        connection, channel = self._connect()
        self._declare(channel, self.exchange_settlement, self.queue_settlement, [
            "settlement.plan.generated",
            "settlement.plan.activated",
            "settlement.plan.cancelled",
            "settlement.plan.expired",
            "settlement.plan.completed",
            "settlement.plan_item.reported",
            "settlement.plan_item.confirmed",
            "settlement.plan_item.rejected",
        ])
        channel.basic_qos(prefetch_count=20)
        channel.basic_consume(queue=self.queue_settlement, on_message_callback=self._callback_settlement)
        try:
            channel.start_consuming()
        finally:
            if connection and not connection.is_closed:
                connection.close()

    def start_consumers(self):
        threads = [
            threading.Thread(target=self.start_identity_consumer, daemon=True),
            threading.Thread(target=self.start_settlement_consumer, daemon=True),
        ]
        for thread in threads:
            thread.start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Wallet consumers stopped")
