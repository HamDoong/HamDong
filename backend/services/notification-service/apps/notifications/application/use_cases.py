"""Use case orchestration for notification-service."""

from apps.notifications.application.sms_service import SmsService
from apps.notifications.infrastructure.repositories import NotificationRepository


class SendTestSmsUseCase:
    def __init__(self):
        self.sms_service = SmsService()

    def execute(self, phone_number: str, message: str):
        return self.sms_service.send_sms(phone_number=phone_number, message=message)


class ProcessOtpSmsUseCase:
    def __init__(self):
        self.sms_service = SmsService()

    def execute(self, payload: dict):
        return self.sms_service.handle_otp_command(payload)


class ListNotificationMessagesUseCase:
    def __init__(self):
        self.repository = NotificationRepository()

    def execute(self, limit: int = 20):
        return self.repository.list_recent_messages(limit=limit)


"""Use case orchestration for notification-service."""
