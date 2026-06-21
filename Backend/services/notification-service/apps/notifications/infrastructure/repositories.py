"""Database repositories for notification-service."""

from __future__ import annotations

import base64
import json
import uuid
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone

from apps.notifications.domain.models import (
    InboxMessage,
    InboxMessageStatusChoices,
    NotificationJob,
    NotificationJobStatusChoices,
    NotificationMessage,
    NotificationPriorityChoices,
    OutboxMessage,
    OutboxMessageStatusChoices,
    ProviderDeliveryLog,
    SmsTemplate,
)
from apps.notifications.domain.rules import NotificationPriorityRule


class NotificationRepository:
    MAX_LIMIT = 100

    @staticmethod
    def create_notification_message(**kwargs) -> NotificationMessage:
        metadata = kwargs.get("metadata") or {}
        priority = kwargs.pop("priority", None) or metadata.get("priority")
        kwargs["metadata"] = metadata
        kwargs["priority"] = NotificationPriorityRule.normalize(priority, message_type=kwargs.get("message_type"))
        kwargs.setdefault("is_read", False)
        kwargs.setdefault("read_at", None)
        return NotificationMessage.objects.create(**kwargs)

    @staticmethod
    def update_notification_message(notification_message: NotificationMessage, **kwargs) -> NotificationMessage:
        if "priority" in kwargs:
            kwargs["priority"] = NotificationPriorityRule.normalize(
                kwargs.get("priority"),
                message_type=kwargs.get("message_type", notification_message.message_type),
            )
        for key, value in kwargs.items():
            setattr(notification_message, key, value)
        notification_message.save()
        return notification_message

    @staticmethod
    def get_notification_message(notification_id):
        return NotificationMessage.objects.filter(id=notification_id, is_deleted=False).first()

    @staticmethod
    def get_for_user(notification_id, user_id, *, for_update: bool = False):
        qs = NotificationMessage.objects.filter(
            id=notification_id,
            recipient_user_id=user_id,
            is_deleted=False,
        )
        if for_update:
            qs = qs.select_for_update()
        return qs.first()

    @staticmethod
    def list_recent_messages(limit: int = 20):
        safe_limit = min(max(int(limit), 1), NotificationRepository.MAX_LIMIT)
        return NotificationMessage.objects.filter(is_deleted=False).order_by("-created_at", "-id")[:safe_limit]

    @staticmethod
    def _base_user_queryset(user_id):
        return NotificationMessage.objects.filter(
            recipient_user_id=user_id,
            is_deleted=False,
        )

    @staticmethod
    def encode_cursor(notification: NotificationMessage) -> str:
        payload = {
            "created_at": notification.created_at.isoformat(),
            "id": str(notification.id),
        }
        raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        return base64.urlsafe_b64encode(raw).decode("ascii")

    @staticmethod
    def decode_cursor(cursor: str | None) -> dict | None:
        if not cursor:
            return None
        try:
            raw = base64.urlsafe_b64decode(cursor.encode("ascii")).decode("utf-8")
            data = json.loads(raw)
            return {
                "created_at": data["created_at"],
                "id": uuid.UUID(data["id"]),
            }
        except Exception as exc:
            raise ValueError("INVALID_CURSOR") from exc

    @staticmethod
    def list_for_user(
        user_id,
        *,
        filters: dict | None = None,
        limit: int | None = None,
        cursor: str | None = None,
        page_size: int | None = None,
    ) -> tuple[list[NotificationMessage], str | None]:
        qs = NotificationRepository._base_user_queryset(user_id).order_by("-created_at", "-id")

        if filters:
            if filters.get("is_read") is not None:
                qs = qs.filter(is_read=filters["is_read"])
            if filters.get("priority"):
                qs = qs.filter(priority=filters["priority"])
            if filters.get("notification_type"):
                qs = qs.filter(message_type=filters["notification_type"])

        if cursor:
            cursor_data = NotificationRepository.decode_cursor(cursor)
            qs = qs.filter(
                Q(created_at__lt=cursor_data["created_at"])
                | Q(created_at=cursor_data["created_at"], id__lt=cursor_data["id"])
            )

        fetch_limit = page_size if page_size is not None else limit
        safe_limit = min(max(int(fetch_limit or 20), 1), NotificationRepository.MAX_LIMIT)
        rows = list(qs[: safe_limit + 1])
        has_more = len(rows) > safe_limit
        items = rows[:safe_limit]
        next_cursor = NotificationRepository.encode_cursor(items[-1]) if has_more and items else None
        return items, next_cursor

    @staticmethod
    def unread_counts_for_user(user_id) -> dict[str, int]:
        counts = NotificationRepository._base_user_queryset(user_id).aggregate(
            unread_count=Count("id", filter=Q(is_read=False)),
            important_unread_count=Count(
                "id",
                filter=Q(is_read=False, priority__in=[NotificationPriorityChoices.HIGH, NotificationPriorityChoices.URGENT]),
            ),
        )
        return {
            "unread_count": int(counts.get("unread_count") or 0),
            "important_unread_count": int(counts.get("important_unread_count") or 0),
        }

    @staticmethod
    @transaction.atomic
    def mark_read_for_user(notification_id, user_id):
        notification = NotificationRepository.get_for_user(notification_id, user_id, for_update=True)
        if not notification:
            return None
        if not notification.is_read:
            read_at = timezone.now()
            notification.is_read = True
            notification.read_at = read_at
            notification.save(update_fields=["is_read", "read_at", "updated_at"])
        return notification

    @staticmethod
    @transaction.atomic
    def mark_all_read_for_user(user_id) -> tuple[int, timezone.datetime]:
        read_at = timezone.now()
        updated_count = NotificationRepository._base_user_queryset(user_id).filter(is_read=False).update(
            is_read=True,
            read_at=read_at,
            updated_at=read_at,
        )
        return int(updated_count), read_at

    @staticmethod
    def create_delivery_log(**kwargs) -> ProviderDeliveryLog:
        return ProviderDeliveryLog.objects.create(**kwargs)

    @staticmethod
    def ensure_template(code: str, title: str, body: str) -> SmsTemplate:
        template, _ = SmsTemplate.objects.get_or_create(
            code=code,
            defaults={"title": title, "body": body, "is_active": True},
        )
        if not template.is_active:
            template.is_active = True
            template.save(update_fields=["is_active", "updated_at"])
        return template

    @staticmethod
    def create_notification_job(**kwargs) -> NotificationJob:
        return NotificationJob.objects.create(**kwargs)

    @staticmethod
    def update_notification_job(notification_job: NotificationJob, **kwargs) -> NotificationJob:
        for key, value in kwargs.items():
            setattr(notification_job, key, value)
        notification_job.save()
        return notification_job

    @staticmethod
    def get_notification_job(event_id):
        return NotificationJob.objects.filter(event_id=event_id).first()

    @staticmethod
    def mark_notification_job_sent(notification_job: NotificationJob, **kwargs):
        return NotificationRepository.update_notification_job(
            notification_job,
            status=NotificationJobStatusChoices.SENT,
            **kwargs,
        )


class OutboxRepository:
    @staticmethod
    def create(*, event_type, routing_key, payload, exchange, source_service="notification-service"):
        return OutboxMessage.objects.create(
            event_id=payload["event_id"],
            event_type=event_type,
            event_version=int(payload.get("event_version", 1)),
            source_service=source_service,
            exchange=exchange,
            routing_key=routing_key,
            payload=payload,
        )

    @staticmethod
    def pending(limit: int = 50, max_retry_count: int = 5):
        return OutboxMessage.objects.filter(
            status__in=[OutboxMessageStatusChoices.PENDING, OutboxMessageStatusChoices.FAILED],
            retry_count__lt=max_retry_count,
            available_at__lte=timezone.now(),
        ).order_by("created_at")[:limit]

    @staticmethod
    def mark_published(message):
        message.status = OutboxMessageStatusChoices.PUBLISHED
        message.published_at = timezone.now()
        message.last_error = None
        message.save(update_fields=["status", "published_at", "last_error", "updated_at"])

    @staticmethod
    def mark_failed(message, error: str):
        message.retry_count += 1
        message.last_error = error
        max_retry_count = int(getattr(settings, "EVENT_MAX_RETRY_COUNT", 5))
        retry_delays = [int(value.strip()) for value in str(getattr(settings, "EVENT_RETRY_DELAY_SECONDS", "10,30,60")).split(",") if value.strip()]
        if hasattr(message, "available_at") and message.retry_count <= len(retry_delays):
            message.available_at = timezone.now() + timedelta(seconds=retry_delays[message.retry_count - 1])
        if message.retry_count >= max_retry_count:
            message.status = OutboxMessageStatusChoices.FAILED
        else:
            message.status = OutboxMessageStatusChoices.PENDING
        update_fields = ["retry_count", "last_error", "status", "updated_at"]
        if hasattr(message, "available_at"):
            update_fields.append("available_at")
        message.save(update_fields=update_fields)


class InboxRepository:
    @staticmethod
    def was_processed(event_id):
        return InboxMessage.objects.filter(event_id=event_id, status=InboxMessageStatusChoices.PROCESSED).exists()

    @staticmethod
    def mark_processed(event_id, event_type, source_service, routing_key, payload):
        obj, _ = InboxMessage.objects.update_or_create(
            event_id=event_id,
            defaults={
                "event_type": event_type,
                "source_service": source_service,
                "routing_key": routing_key,
                "payload": payload,
                "status": InboxMessageStatusChoices.PROCESSED,
                "processed_at": timezone.now(),
                "error_message": None,
            },
        )
        return obj

    @staticmethod
    def mark_failed(event_id, event_type, source_service, routing_key, payload, error_message):
        obj, _ = InboxMessage.objects.update_or_create(
            event_id=event_id,
            defaults={
                "event_type": event_type,
                "source_service": source_service,
                "routing_key": routing_key,
                "payload": payload,
                "status": InboxMessageStatusChoices.FAILED,
                "processed_at": timezone.now(),
                "error_message": error_message,
            },
        )
        return obj

    @staticmethod
    def mark_skipped(event_id, event_type, source_service, routing_key, payload):
        obj, _ = InboxMessage.objects.update_or_create(
            event_id=event_id,
            defaults={
                "event_type": event_type,
                "source_service": source_service,
                "routing_key": routing_key,
                "payload": payload,
                "status": InboxMessageStatusChoices.SKIPPED,
                "processed_at": timezone.now(),
                "error_message": None,
            },
        )
        return obj
