"""Use case orchestration for notification-service."""

from __future__ import annotations

from dataclasses import dataclass

from django.utils import timezone

from apps.notifications.application.sms_service import EmailService
from apps.notifications.domain.events import DomainEvent
from apps.notifications.domain.models import (
    NotificationMessageTypeChoices,
    NotificationPriorityChoices,
    NotificationStatusChoices,
)
from apps.notifications.infrastructure.repositories import NotificationRepository, OutboxRepository


@dataclass
class NotificationQuery:
    is_read: bool | None = None
    priority: str | None = None
    notification_type: str | None = None
    limit: int | None = None
    cursor: str | None = None
    page_size: int | None = None


class SendTestEmailUseCase:
    def __init__(self):
        self.email_service = EmailService()

    def execute(self, email: str, message: str):
        return self.email_service.send_test_email(email=email, message=message)


class ProcessOtpEmailUseCase:
    def __init__(self):
        self.email_service = EmailService()

    def execute(self, payload: dict):
        return self.email_service.handle_otp_command(payload)


class ListNotificationMessagesUseCase:
    def __init__(self):
        self.repository = NotificationRepository()

    def execute(self, limit: int = 20):
        return self.repository.list_recent_messages(limit=limit)


class CreateNotificationUseCase:
    def __init__(self):
        self.repository = NotificationRepository

    def execute(self, actor, *, recipient_user_id, channel, notification_type, title, body, metadata, priority=None):
        notification = self.repository.create_notification_message(
            recipient_user_id=recipient_user_id,
            recipient_email=None,
            channel=channel,
            message_type=notification_type,
            title=title or "",
            body=body,
            metadata=metadata or {},
            priority=priority,
            recipient=str(recipient_user_id),
            recipient_masked=str(recipient_user_id),
            status=NotificationStatusChoices.PENDING,
            created_by_user_id=getattr(actor, "sub", getattr(actor, "id", None)),
        )
        payload = DomainEvent(
            "NotificationCreated",
            {
                "notification_id": str(notification.id),
                "recipient_user_id": str(notification.recipient_user_id),
            },
        ).to_dict()
        OutboxRepository.create(
            event_type="NotificationCreated",
            routing_key="notification.created",
            payload=payload,
            exchange="events",
        )
        return notification


class ListInboxNotificationsUseCase:
    def execute(self, user, query: NotificationQuery):
        user_id = getattr(user, "sub", user.id)
        filters = {
            "is_read": query.is_read,
            "priority": query.priority,
            "notification_type": query.notification_type,
        }
        return NotificationRepository.list_for_user(
            user_id,
            filters=filters,
            limit=query.limit,
            cursor=query.cursor,
            page_size=query.page_size,
        )


class CountUnreadNotificationsUseCase:
    def execute(self, user):
        user_id = getattr(user, "sub", user.id)
        return NotificationRepository.unread_counts_for_user(user_id)


class GetNotificationDetailUseCase:
    def execute(self, user, notification_id):
        notification = NotificationRepository.get_notification_message(notification_id)
        if not notification:
            return None
        user_id = str(getattr(user, "sub", user.id))
        if str(notification.recipient_user_id) != user_id and getattr(user, "role", "USER") not in ("ADMIN", "SYSTEM"):
            return None
        return notification


class MarkNotificationReadUseCase:
    def execute(self, user, notification_id):
        user_id = getattr(user, "sub", user.id)
        return NotificationRepository.mark_read_for_user(notification_id, user_id)


class MarkAllNotificationsReadUseCase:
    def execute(self, user):
        user_id = getattr(user, "sub", user.id)
        return NotificationRepository.mark_all_read_for_user(user_id)


class UpdateNotificationUseCase:
    def execute(self, user, notification, *, title=None, body=None, metadata=None, priority=None):
        if notification.status not in (NotificationStatusChoices.DRAFT, NotificationStatusChoices.PENDING):
            raise ValueError("NOTIFICATION_NOT_EDITABLE")
        user_id = str(getattr(user, "sub", user.id))
        if str(notification.created_by_user_id) != user_id and getattr(user, "role", "USER") not in ("ADMIN", "SYSTEM"):
            raise PermissionError("NOTIFICATION_EDIT_FORBIDDEN")
        if notification.message_type != NotificationMessageTypeChoices.CUSTOM:
            raise ValueError("NOTIFICATION_NOT_EDITABLE")

        if title is not None:
            notification.title = title
        if body is not None:
            notification.body = body
        if metadata is not None:
            notification.metadata = metadata
        if priority is not None:
            notification.priority = NotificationPriorityChoices(priority)
        notification.updated_at = timezone.now()
        notification.save()

        payload = DomainEvent("NotificationUpdated", {"notification_id": str(notification.id)}).to_dict()
        OutboxRepository.create(
            event_type="NotificationUpdated",
            routing_key="notification.updated",
            payload=payload,
            exchange="events",
        )
        return notification


class DeleteNotificationUseCase:
    def execute(self, user, notification):
        user_id = str(getattr(user, "sub", user.id))
        if str(notification.recipient_user_id) != user_id and getattr(user, "role", "USER") not in ("ADMIN", "SYSTEM"):
            raise PermissionError("NOTIFICATION_DELETE_FORBIDDEN")
        notification.is_deleted = True
        notification.deleted_at = timezone.now()
        notification.deleted_by_user_id = user_id
        notification.save(update_fields=["is_deleted", "deleted_at", "deleted_by_user_id", "updated_at"])

        payload = DomainEvent("NotificationDeleted", {"notification_id": str(notification.id)}).to_dict()
        OutboxRepository.create(
            event_type="NotificationDeleted",
            routing_key="notification.deleted",
            payload=payload,
            exchange="events",
        )
        return notification
