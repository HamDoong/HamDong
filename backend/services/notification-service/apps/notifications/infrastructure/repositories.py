from datetime import timedelta
"""Database repositories for notification-service."""

from apps.notifications.domain.models import (
    NotificationMessage,
    NotificationJob,
    NotificationJobStatusChoices,
    ProviderDeliveryLog,
    SmsTemplate,
)


class NotificationRepository:
    @staticmethod
    def create_notification_message(**kwargs) -> NotificationMessage:
        return NotificationMessage.objects.create(**kwargs)

    @staticmethod
    def update_notification_message(
        notification_message: NotificationMessage, **kwargs
    ) -> NotificationMessage:
        for key, value in kwargs.items():
            setattr(notification_message, key, value)
        notification_message.save()
        return notification_message

    @staticmethod
    def create_delivery_log(**kwargs) -> ProviderDeliveryLog:
        return ProviderDeliveryLog.objects.create(**kwargs)

    @staticmethod
    def list_recent_messages(limit: int = 20):
        return NotificationMessage.objects.all()[:limit]

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


from django.conf import settings
from django.utils import timezone
from apps.notifications.domain.models import (
    InboxMessage,
    InboxMessageStatusChoices,
    NotificationJob,
    NotificationJobStatusChoices,
    OutboxMessage,
    OutboxMessageStatusChoices,
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

