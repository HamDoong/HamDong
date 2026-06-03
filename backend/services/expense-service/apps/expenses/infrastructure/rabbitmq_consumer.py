from __future__ import annotations

import json
import logging
import time
import uuid
from typing import Any, Dict

import pika
from django.conf import settings
from django.db import models
from django.utils.dateparse import parse_datetime

from apps.expenses.domain.models import GroupMemberProjection, GroupProjection, UserProjection
from apps.expenses.infrastructure.event_envelope import validate_event_envelope
from apps.expenses.infrastructure.repositories import InboxRepository

logger = logging.getLogger(__name__)


class ExpenseEventConsumer:
    def process_identity_event(self, event_type: str, payload: Dict[str, Any]) -> bool:
        uid = uuid.UUID(str(payload.get("user_id")))
        defaults = {
            "phone_number": payload.get("phone_number", ""),
            "display_name": payload.get("display_name"),
            "first_name": payload.get("first_name"),
            "last_name": payload.get("last_name"),
            "role": payload.get("role", "USER"),
            "is_active": payload.get("is_active", True),
        }
        UserProjection.objects.update_or_create(identity_user_id=uid, defaults=defaults)
        return True

    def process_group_event(self, event_type: str, payload: Dict[str, Any]) -> bool:
        if event_type == "GroupCreated":
            gid = uuid.UUID(str(payload.get("group_id")))
            defaults = {
                "title": payload.get("title", ""),
                "group_type": payload.get("group_type", "GENERAL"),
                "status": payload.get("status", "ACTIVE"),
                "created_by_user_id": uuid.UUID(str(payload.get("created_by_user_id") or payload.get("created_by"))) if (payload.get("created_by_user_id") or payload.get("created_by")) else None,
                "member_count": int(payload.get("member_count", 0)),
            }
            GroupProjection.objects.update_or_create(group_id=gid, defaults=defaults)
            return True
        if event_type == "GroupUpdated":
            gid = uuid.UUID(str(payload.get("group_id")))
            defaults = {
                "title": payload.get("title", ""),
                "group_type": payload.get("group_type", "GENERAL"),
                "status": payload.get("status", "ACTIVE"),
                "member_count": int(payload.get("member_count", 0)),
            }
            GroupProjection.objects.update_or_create(group_id=gid, defaults=defaults)
            return True
        if event_type == "GroupArchived":
            gid = uuid.UUID(str(payload.get("group_id")))
            GroupProjection.objects.filter(group_id=gid).update(status="ARCHIVED")
            return True
        if event_type in ("GroupMemberJoined", "GroupMemberRemoved", "GroupMemberLeft"):
            gid = uuid.UUID(str(payload.get("group_id")))
            uid_value = payload.get("user_id") or payload.get("member_user_id")
            if not uid_value:
                return True
            uid = uuid.UUID(str(uid_value))
            phone = payload.get("phone_number", "")
            display = payload.get("display_name_snapshot") or payload.get("display_name")
            if event_type == "GroupMemberJoined":
                defaults = {
                    "phone_number": phone,
                    "display_name_snapshot": display,
                    "role": payload.get("role", "MEMBER"),
                    "status": "ACTIVE",
                    "joined_at": parse_datetime(payload.get("joined_at")) if payload.get("joined_at") else None,
                }
                GroupMemberProjection.objects.update_or_create(group_id=gid, user_id=uid, defaults=defaults)
                GroupProjection.objects.filter(group_id=gid).update(member_count=GroupMemberProjection.objects.filter(group_id=gid, status="ACTIVE").count())
                return True
            status = "REMOVED" if event_type == "GroupMemberRemoved" else "LEFT"
            GroupMemberProjection.objects.update_or_create(
                group_id=gid,
                user_id=uid,
                defaults={"phone_number": phone, "display_name_snapshot": display, "role": payload.get("role", "MEMBER"), "status": status},
            )
            GroupProjection.objects.filter(group_id=gid).update(member_count=GroupMemberProjection.objects.filter(group_id=gid, status="ACTIVE").count())
            return True
        return True

    def process_envelope(self, payload: dict) -> bool:
        valid, error = validate_event_envelope(payload)
        if not valid:
            raise ValueError(error)
        event_id = payload["event_id"]
        if InboxRepository.was_processed(event_id):
            InboxRepository.mark_skipped(event_id, payload["event_type"], payload["source_service"], payload["routing_key"], payload)
            return True
        event_type = payload["event_type"]
        data = payload["data"] or {}
        if event_type.startswith("User"):
            self.process_identity_event(event_type, data)
        else:
            self.process_group_event(event_type, data)
        InboxRepository.mark_processed(event_id, event_type, payload["source_service"], payload["routing_key"], payload)
        return True

    def process_message(self, raw_message: str) -> bool:
        payload = json.loads(raw_message) if isinstance(raw_message, str) else raw_message
        return self.process_envelope(payload)


class _BaseConsumer:
    routing_keys: list[str] = []
    exchange_setting: str = ""
    queue_setting: str = ""

    def __init__(self):
        self.exchange = getattr(settings, self.exchange_setting)
        self.queue = getattr(settings, self.queue_setting)
        self.dlq = f"{self.queue}{getattr(settings, 'EVENT_DLQ_SUFFIX', '.dlq')}"
        self.retry_delay_seconds = 2
        self.processor = ExpenseEventConsumer()

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
        for key in self.routing_keys:
            self.channel.queue_bind(queue=self.queue, exchange=self.exchange, routing_key=key)

    def _callback(self, ch, method, properties, body):
        try:
            payload = json.loads(body.decode("utf-8") if isinstance(body, (bytes, bytearray)) else body)
            self.processor.process_envelope(payload)
        except Exception as exc:
            logger.exception("Failed to process %s event", self.queue)
            if isinstance(payload, dict) and payload.get("event_id"):
                InboxRepository.mark_failed(payload["event_id"], payload.get("event_type","UNKNOWN"), payload.get("source_service",""), payload.get("routing_key",""), payload, str(exc))
        finally:
            ch.basic_ack(delivery_tag=method.delivery_tag)

    def start(self):
        while True:
            try:
                self._connect()
                self._declare()
                self.channel.basic_qos(prefetch_count=1)
                self.channel.basic_consume(queue=self.queue, on_message_callback=self._callback)
                self.channel.start_consuming()
            except KeyboardInterrupt:
                break
            except Exception:
                logger.exception("Expense consumer unavailable; retrying")
                time.sleep(self.retry_delay_seconds)
            finally:
                if getattr(self, "connection", None) and not self.connection.is_closed:
                    self.connection.close()


class IdentityConsumer(_BaseConsumer):
    exchange_setting = "IDENTITY_RABBITMQ_EXCHANGE"
    queue_setting = "EXPENSE_IDENTITY_QUEUE"
    routing_keys = ["identity.user.created", "identity.user.updated"]


class GroupConsumer(_BaseConsumer):
    exchange_setting = "GROUP_RABBITMQ_EXCHANGE"
    queue_setting = "EXPENSE_GROUP_QUEUE"
    routing_keys = ["group.created", "group.updated", "group.archived", "group.member.joined", "group.member.removed", "group.member.left"]
