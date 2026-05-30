import uuid

from django.db import models


class NotificationChannelChoices(models.TextChoices):
    SMS = "SMS", "SMS"
    EMAIL = "EMAIL", "Email"
    PUSH = "PUSH", "Push"


class NotificationMessageTypeChoices(models.TextChoices):
    OTP = "OTP", "OTP"
    REMINDER = "REMINDER", "Reminder"
    INVITE = "INVITE", "Invite"
    SETTLEMENT = "SETTLEMENT", "Settlement"


class NotificationStatusChoices(models.TextChoices):
    PENDING = "PENDING", "Pending"
    SENDING = "SENDING", "Sending"
    SENT = "SENT", "Sent"
    FAILED = "FAILED", "Failed"
    RETRY_PENDING = "RETRY_PENDING", "Retry pending"
    SKIPPED = "SKIPPED", "Skipped"


class SmsProviderChoices(models.TextChoices):
    FAKE = "fake", "Fake"
    KAVENEGAR = "kavenegar", "Kavenegar"
    MELIPAYAMAK = "melipayamak", "Melipayamak"


class SmsTemplate(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=64, unique=True)
    title = models.CharField(max_length=255)
    body = models.TextField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "notification_sms_templates"

    def __str__(self) -> str:
        return self.code


class NotificationMessage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    channel = models.CharField(
        max_length=16, choices=NotificationChannelChoices.choices
    )
    message_type = models.CharField(
        max_length=32, choices=NotificationMessageTypeChoices.choices
    )
    recipient = models.CharField(max_length=32)
    recipient_masked = models.CharField(max_length=32)
    template_code = models.CharField(max_length=64, null=True, blank=True)
    status = models.CharField(
        max_length=32,
        choices=NotificationStatusChoices.choices,
        default=NotificationStatusChoices.PENDING,
    )
    provider = models.CharField(
        max_length=32,
        choices=SmsProviderChoices.choices,
        default=SmsProviderChoices.FAKE,
    )
    provider_message_id = models.CharField(max_length=128, null=True, blank=True)
    error_code = models.CharField(max_length=64, null=True, blank=True)
    error_message = models.TextField(null=True, blank=True)
    retry_count = models.PositiveIntegerField(default=0)
    last_attempt_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "notification_messages"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.channel}:{self.message_type}:{self.recipient_masked}"


class ProviderDeliveryLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    notification_message = models.ForeignKey(
        NotificationMessage,
        on_delete=models.CASCADE,
        related_name="delivery_logs",
    )
    provider = models.CharField(
        max_length=32,
        choices=SmsProviderChoices.choices,
        default=SmsProviderChoices.FAKE,
    )
    request_payload_masked = models.JSONField(default=dict)
    response_payload = models.JSONField(default=dict)
    http_status_code = models.IntegerField(null=True, blank=True)
    is_success = models.BooleanField(default=False)
    duration_ms = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "provider_delivery_logs"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.provider}:{self.is_success}"
