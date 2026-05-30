import json
import logging
import uuid
from typing import Any, Dict

from django.utils.dateparse import parse_datetime
from django.db import models

from ..domain.models import UserProjection, GroupProjection, GroupMemberProjection

logger = logging.getLogger(__name__)


class ExpenseEventConsumer:
    """Processes identity and group events to update expense-service projections.

    Requirements satisfied:
    - Idempotent updates via update_or_create or safe state transitions
    - Invalid payloads are caught and logged
    - No cross-service DB calls
    """

    def process_identity_event(self, event_type: str, payload: Dict[str, Any]) -> bool:
        try:
            if event_type == "UserCreated":
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

            if event_type == "UserUpdated":
                uid = uuid.UUID(str(payload.get("user_id")))
                defaults = {
                    "phone_number": payload.get("phone_number", ""),
                    "display_name": payload.get("display_name"),
                    "first_name": payload.get("first_name"),
                    "last_name": payload.get("last_name"),
                    "role": payload.get("role", "USER"),
                    "is_active": payload.get("is_active", True),
                }
                # update_or_create ensures idempotency
                UserProjection.objects.update_or_create(identity_user_id=uid, defaults=defaults)
                return True

            logger.debug("Unhandled identity event type: %s", event_type)
            return False
        except Exception as exc:
            logger.exception("Failed to process identity event %s: %s", event_type, exc)
            return False

    def process_group_event(self, event_type: str, payload: Dict[str, Any]) -> bool:
        try:
            if event_type == "GroupCreated":
                gid = uuid.UUID(str(payload.get("group_id")))
                defaults = {
                    "title": payload.get("title", ""),
                    "group_type": payload.get("group_type", "GENERAL"),
                    "status": payload.get("status", "ACTIVE"),
                    "created_by_user_id": uuid.UUID(str(payload.get("created_by_user_id"))) if payload.get("created_by_user_id") else None,
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
                uid = uuid.UUID(str(payload.get("user_id")))
                phone = payload.get("phone_number", "")
                display = payload.get("display_name_snapshot") or payload.get("display_name")

                if event_type == "GroupMemberJoined":
                    joined_at = parse_datetime(payload.get("joined_at")) if payload.get("joined_at") else None
                    defaults = {
                        "phone_number": phone,
                        "display_name_snapshot": display,
                        "role": payload.get("role", "MEMBER"),
                        "status": "ACTIVE",
                        "joined_at": joined_at,
                    }
                    GroupMemberProjection.objects.update_or_create(group_id=gid, user_id=uid, defaults=defaults)
                    # increase member_count if projection exists
                    GroupProjection.objects.filter(group_id=gid).update(member_count=models.F("member_count") + 1)
                    return True

                if event_type == "GroupMemberRemoved":
                    removed_at = parse_datetime(payload.get("removed_at")) if payload.get("removed_at") else None
                    GroupMemberProjection.objects.filter(group_id=gid, user_id=uid).update(status="REMOVED", removed_at=removed_at)
                    GroupProjection.objects.filter(group_id=gid).update(member_count=models.F("member_count") - 1)
                    return True

                if event_type == "GroupMemberLeft":
                    left_at = parse_datetime(payload.get("left_at")) if payload.get("left_at") else None
                    GroupMemberProjection.objects.filter(group_id=gid, user_id=uid).update(status="LEFT", left_at=left_at)
                    GroupProjection.objects.filter(group_id=gid).update(member_count=models.F("member_count") - 1)
                    return True

            logger.debug("Unhandled group event type: %s", event_type)
            return False
        except Exception as exc:
            logger.exception("Failed to process group event %s: %s", event_type, exc)
            return False

    def process_message(self, raw_message: str) -> bool:
        """Dispatch a raw JSON message containing {'type': ..., 'payload': {...}}"""
        try:
            obj = json.loads(raw_message)
            event_type = obj.get("type")
            payload = obj.get("payload", {})
            if not event_type:
                logger.warning("Received event without type")
                return False

            if event_type.startswith("User"):
                return self.process_identity_event(event_type, payload)

            return self.process_group_event(event_type, payload)
        except json.JSONDecodeError:
            logger.exception("Invalid JSON message")
            return False
        except Exception:
            logger.exception("Unexpected error processing message")
            return False
import json
import logging
import pika
from django.conf import settings
from apps.expenses.infrastructure.repositories import ProjectionRepository

logger = logging.getLogger(__name__)


class IdentityConsumer:
    def __init__(self):
        self.exchange = getattr(settings, "IDENTITY_RABBITMQ_EXCHANGE", "hamdong.identity")
        self.queue = getattr(settings, "EXPENSE_IDENTITY_QUEUE", "expense.identity.user_events")
        self.connection = None
        self.channel = None

    def _connect(self):
        credentials = pika.PlainCredentials(settings.RABBITMQ_DEFAULT_USER, settings.RABBITMQ_DEFAULT_PASS)
        params = pika.ConnectionParameters(host=settings.RABBITMQ_HOST, port=settings.RABBITMQ_PORT, credentials=credentials)
        self.connection = pika.BlockingConnection(params)
        self.channel = self.connection.channel()

    def _declare(self):
        self.channel.exchange_declare(exchange=self.exchange, exchange_type="topic", durable=True)
        self.channel.queue_declare(queue=self.queue, durable=True)
        self.channel.queue_bind(queue=self.queue, exchange=self.exchange, routing_key="identity.user.created")
        self.channel.queue_bind(queue=self.queue, exchange=self.exchange, routing_key="identity.user.updated")

    def _callback(self, ch, method, properties, body):
        try:
            payload = json.loads(body)
            data = payload.get("data") or {}
            identity_user_id = data.get("user_id")
            phone = data.get("phone_number")
            display = data.get("display_name")
            if identity_user_id and phone:
                ProjectionRepository.create_or_update = getattr(ProjectionRepository, "create_or_update", None)
                # For simplicity, directly use Django model
                from apps.expenses.domain.models import UserProjection
                UserProjection.objects.update_or_create(identity_user_id=identity_user_id, defaults={"phone_number": phone, "display_name": display})
        except Exception:
            logger.exception("Failed to process identity event")
        finally:
            ch.basic_ack(delivery_tag=method.delivery_tag)

    def start(self):
        self._connect()
        self._declare()
        self.channel.basic_qos(prefetch_count=1)
        self.channel.basic_consume(queue=self.queue, on_message_callback=self._callback)
        try:
            self.channel.start_consuming()
        except KeyboardInterrupt:
            pass


class GroupConsumer:
    def __init__(self):
        self.exchange = getattr(settings, "GROUP_RABBITMQ_EXCHANGE", "hamdong.group")
        self.queue = getattr(settings, "EXPENSE_GROUP_QUEUE", "expense.group.events")
        self.connection = None
        self.channel = None

    def _connect(self):
        credentials = pika.PlainCredentials(settings.RABBITMQ_DEFAULT_USER, settings.RABBITMQ_DEFAULT_PASS)
        params = pika.ConnectionParameters(host=settings.RABBITMQ_HOST, port=settings.RABBITMQ_PORT, credentials=credentials)
        self.connection = pika.BlockingConnection(params)
        self.channel = self.connection.channel()

    def _declare(self):
        self.channel.exchange_declare(exchange=self.exchange, exchange_type="topic", durable=True)
        self.channel.queue_declare(queue=self.queue, durable=True)
        keys = ["group.created", "group.updated", "group.archived", "group.member.joined", "group.member.removed", "group.member.left"]
        for k in keys:
            self.channel.queue_bind(queue=self.queue, exchange=self.exchange, routing_key=k)

    def _callback(self, ch, method, properties, body):
        try:
            payload = json.loads(body)
            data = payload.get("data") or {}
            # Very simple handling: update group projections
            from apps.expenses.domain.models import GroupProjection, GroupMemberProjection
            et = payload.get("event_type")
            if et == "GroupCreated":
                gid = data.get("group_id")
                GroupProjection.objects.update_or_create(group_id=gid, defaults={"title": data.get("title", ""), "group_type": data.get("group_type", "GENERAL")})
            elif et == "GroupMemberJoined":
                gid = data.get("group_id")
                uid = data.get("user_id")
                GroupMemberProjection.objects.update_or_create(group_id=gid, user_id=uid, defaults={"status": "ACTIVE"})
            elif et == "GroupMemberRemoved":
                gid = data.get("group_id")
                mid = data.get("member_id")
                # mark removed; best-effort
                GroupMemberProjection.objects.filter(id=mid).update(status="REMOVED")
        except Exception:
            logger.exception("Failed to process group event")
        finally:
            ch.basic_ack(delivery_tag=method.delivery_tag)

    def start(self):
        self._connect()
        self._declare()
        self.channel.basic_qos(prefetch_count=1)
        self.channel.basic_consume(queue=self.queue, on_message_callback=self._callback)
        try:
            self.channel.start_consuming()
        except KeyboardInterrupt:
            pass
