from __future__ import annotations

import json
import logging
import threading
import time
from datetime import datetime, timezone

import pika
from django.conf import settings

from apps.dashboard.domain.models import DashboardActivityTypeChoices
from apps.dashboard.infrastructure.event_envelope import validate_event_envelope
from apps.dashboard.infrastructure.repositories import (
    ActivityRepository,
    GroupMemberProjectionRepository,
    GroupProjectionRepository,
    InboxRepository,
    UserProjectionRepository,
)

logger = logging.getLogger(__name__)


class DashboardEventConsumer:
    def __init__(self):
        self.exchange_identity = getattr(settings, "IDENTITY_RABBITMQ_EXCHANGE", "hamdong.identity")
        self.exchange_group = getattr(settings, "GROUP_RABBITMQ_EXCHANGE", "hamdong.group")
        self.exchange_expense = getattr(settings, "EXPENSE_RABBITMQ_EXCHANGE", "hamdong.expense")
        self.exchange_media = getattr(settings, "MEDIA_RABBITMQ_EXCHANGE", "hamdong.media")
        self.exchange_settlement = getattr(settings, "SETTLEMENT_RABBITMQ_EXCHANGE", "hamdong.settlement")
        self.queue_identity = getattr(settings, "DASHBOARD_IDENTITY_QUEUE", "dashboard.identity.user_events")
        self.queue_group = getattr(settings, "DASHBOARD_GROUP_QUEUE", "dashboard.group.events")
        self.queue_expense = getattr(settings, "DASHBOARD_EXPENSE_QUEUE", "dashboard.expense.events")
        self.queue_media = getattr(settings, "DASHBOARD_MEDIA_QUEUE", "dashboard.media.events")
        self.queue_settlement = getattr(settings, "DASHBOARD_SETTLEMENT_QUEUE", "dashboard.settlement.events")
        self.retry_delay_seconds = 2

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
        channel.exchange_declare(exchange=exchange, exchange_type="topic", durable=True)
        channel.queue_declare(queue=queue, durable=True)
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
        handler(payload)
        InboxRepository.mark_processed(event_id, payload["event_type"], payload["source_service"], payload["routing_key"], payload)

    def _callback_factory(self, handler):
        def _callback(ch, method, properties, body):
            payload = None
            try:
                payload = self._parse(body)
                self._process(payload, handler)
            except Exception as exc:
                logger.exception("Failed to process dashboard event")
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
        return _callback

    def _occurred_at(self, payload):
        return datetime.fromisoformat(str(payload["occurred_at"]).replace("Z", "+00:00"))

    def _create_activity(self, payload, *, event_type, group_id, actor_user_id=None, source_object_id=None, summary=None):
        ActivityRepository.create_if_missing(
            event_id=payload["event_id"],
            event_type=event_type,
            source_service=payload["source_service"],
            routing_key=payload["routing_key"],
            group_id=group_id,
            actor_user_id=actor_user_id,
            source_object_id=source_object_id,
            summary=summary or {},
            occurred_at=self._occurred_at(payload),
        )

    def _handle_identity(self, payload):
        data = payload.get("data") or {}
        if payload["event_type"] in ("UserCreated", "UserUpdated"):
            UserProjectionRepository.upsert_from_event(**data)

    def _handle_group(self, payload):
        data = payload.get("data") or {}
        event_type = payload["event_type"]
        if event_type == "GroupCreated":
            GroupProjectionRepository.upsert_from_event(**data)
            self._create_activity(
                payload,
                event_type=DashboardActivityTypeChoices.GROUP_CREATED,
                group_id=data.get("group_id"),
                actor_user_id=data.get("created_by_user_id"),
                source_object_id=data.get("group_id"),
                summary={"group_id": data.get("group_id"), "title": data.get("title")},
            )
        elif event_type == "GroupUpdated":
            GroupProjectionRepository.upsert_from_event(**data)
        elif event_type == "GroupArchived":
            GroupProjectionRepository.upsert_from_event(**{**data, "status": "ARCHIVED"})
        elif event_type == "GroupMemberJoined":
            GroupMemberProjectionRepository.upsert_joined(**data)
            self._create_activity(
                payload,
                event_type=DashboardActivityTypeChoices.GROUP_MEMBER_JOINED,
                group_id=data.get("group_id"),
                actor_user_id=data.get("user_id"),
                source_object_id=data.get("user_id"),
                summary={"user_id": data.get("user_id"), "art_name": data.get("art_name")},
            )
        elif event_type == "GroupInviteCreated":
            self._create_activity(
                payload,
                event_type=DashboardActivityTypeChoices.GROUP_INVITATION_CREATED,
                group_id=data.get("group_id"),
                actor_user_id=data.get("created_by_user_id"),
                source_object_id=data.get("invite_id"),
                summary={"invite_id": data.get("invite_id")},
            )
        elif event_type == "GroupMemberRemoved":
            GroupMemberProjectionRepository.mark_removed(**data)
        elif event_type == "GroupMemberLeft":
            GroupMemberProjectionRepository.mark_left(**data)
        elif event_type == "GroupInviteAccepted":
            self._create_activity(
                payload,
                event_type=DashboardActivityTypeChoices.GROUP_MEMBER_JOINED,
                group_id=data.get("group_id"),
                actor_user_id=data.get("user_id"),
                source_object_id=data.get("invite_id"),
                summary={"invite_id": data.get("invite_id"), "user_id": data.get("user_id")},
            )

    def _handle_expense(self, payload):
        data = payload.get("data") or {}
        event_type = payload["event_type"]
        mapping = {
            "ExpenseCreated": DashboardActivityTypeChoices.EXPENSE_CREATED,
            "ExpenseUpdated": DashboardActivityTypeChoices.EXPENSE_UPDATED,
            "ExpenseDeleted": DashboardActivityTypeChoices.EXPENSE_DELETED,
        }
        if event_type not in mapping:
            return
        actor_user_id = data.get("created_by_user_id") or data.get("deleted_by_user_id")
        self._create_activity(
            payload,
            event_type=mapping[event_type],
            group_id=data.get("group_id"),
            actor_user_id=actor_user_id,
            source_object_id=data.get("expense_id"),
            summary={
                "expense_id": data.get("expense_id"),
                "payer_user_id": data.get("payer_user_id"),
                "amount_minor": int(data.get("total_amount_minor") or 0),
                "currency": data.get("currency"),
                "status": data.get("status"),
            },
        )

    def _handle_media(self, payload):
        data = payload.get("data") or {}
        if payload["event_type"] != "MediaUploaded":
            return
        self._create_activity(
            payload,
            event_type=DashboardActivityTypeChoices.RECEIPT_UPLOADED,
            group_id=data.get("group_id"),
            actor_user_id=data.get("uploaded_by_user_id"),
            source_object_id=data.get("media_file_id"),
            summary={
                "media_file_id": data.get("media_file_id"),
                "expense_id": data.get("related_expense_id"),
                "file_type": data.get("file_type"),
                "content_type": data.get("content_type"),
                "size_bytes": int(data.get("size_bytes") or 0),
            },
        )

    def _handle_settlement(self, payload):
        data = payload.get("data") or {}
        event_type = payload["event_type"]
        mapping = {
            "SettlementPlanItemReported": DashboardActivityTypeChoices.SETTLEMENT_REPORTED,
            "SettlementPlanItemConfirmed": DashboardActivityTypeChoices.SETTLEMENT_CONFIRMED,
            "SettlementPlanItemRejected": DashboardActivityTypeChoices.SETTLEMENT_REJECTED,
            "SettlementPlanActivated": DashboardActivityTypeChoices.SETTLEMENT_PLAN_ACTIVATED,
        }
        if event_type not in mapping:
            return
        actor_user_id = (
            data.get("activated_by_user_id")
            or data.get("receiver_user_id")
            or data.get("payer_user_id")
        )
        self._create_activity(
            payload,
            event_type=mapping[event_type],
            group_id=data.get("group_id"),
            actor_user_id=actor_user_id,
            source_object_id=data.get("item_id") or data.get("plan_id"),
            summary={
                "plan_id": data.get("plan_id"),
                "item_id": data.get("item_id"),
                "amount_minor": int(data.get("amount_minor") or 0),
                "currency": data.get("currency"),
                "payer_user_id": data.get("payer_user_id"),
                "receiver_user_id": data.get("receiver_user_id"),
            },
        )

    def process_identity_payload(self, payload: dict):
        return self._process(payload, self._handle_identity)

    def process_group_payload(self, payload: dict):
        return self._process(payload, self._handle_group)

    def process_expense_payload(self, payload: dict):
        return self._process(payload, self._handle_expense)

    def process_media_payload(self, payload: dict):
        return self._process(payload, self._handle_media)

    def process_settlement_payload(self, payload: dict):
        return self._process(payload, self._handle_settlement)

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
                logger.exception("Dashboard consumer unavailable; retrying")
                time.sleep(self.retry_delay_seconds)
            finally:
                if connection and not connection.is_closed:
                    connection.close()

    def start_consumers(self):
        workers = [
            ("identity", self.start_identity_consumer),
            ("group", self.start_group_consumer),
            ("expense", self.start_expense_consumer),
            ("media", self.start_media_consumer),
            ("settlement", self.start_settlement_consumer),
        ]
        threads = []
        for name, target in workers:
            thread = threading.Thread(target=target, name=f"dashboard-{name}-consumer", daemon=False)
            thread.start()
            threads.append(thread)
            logger.info("Started dashboard %s consumer thread", name)
        for thread in threads:
            thread.join()

    def start_identity_consumer(self):
        self._start_queue(
            self.exchange_identity,
            self.queue_identity,
            ["identity.user.created", "identity.user.updated"],
            self._callback_factory(self._handle_identity),
        )

    def start_group_consumer(self):
        self._start_queue(
            self.exchange_group,
            self.queue_group,
            [
                "group.created",
                "group.updated",
                "group.archived",
                "group.invite.created",
                "group.invite.accepted",
                "group.member.joined",
                "group.member.removed",
                "group.member.left",
            ],
            self._callback_factory(self._handle_group),
        )

    def start_expense_consumer(self):
        self._start_queue(
            self.exchange_expense,
            self.queue_expense,
            ["expense.created", "expense.updated", "expense.deleted"],
            self._callback_factory(self._handle_expense),
        )

    def start_media_consumer(self):
        self._start_queue(
            self.exchange_media,
            self.queue_media,
            ["media.uploaded"],
            self._callback_factory(self._handle_media),
        )

    def start_settlement_consumer(self):
        self._start_queue(
            self.exchange_settlement,
            self.queue_settlement,
            [
                "settlement.plan.activated",
                "settlement.plan_item.reported",
                "settlement.plan_item.confirmed",
                "settlement.plan_item.rejected",
            ],
            self._callback_factory(self._handle_settlement),
        )
