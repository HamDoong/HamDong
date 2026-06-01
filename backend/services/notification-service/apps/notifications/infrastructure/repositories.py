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
