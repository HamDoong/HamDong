import uuid

from django.db import models
from django.utils import timezone


class NotificationChannelChoices(models.TextChoices):
    EMAIL = "EMAIL", "Email"
    PUSH = "PUSH", "Push"
    IN_APP = "IN_APP", "In app"


class NotificationMessageTypeChoices(models.TextChoices):
    OTP = "OTP", "OTP"
    REMINDER = "REMINDER", "Reminder"
    INVITE = "INVITE", "Invite"
    SETTLEMENT = "SETTLEMENT", "Settlement"
    CUSTOM = "CUSTOM", "Custom"


class NotificationStatusChoices(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    PENDING = "PENDING", "Pending"
    SENDING = "SENDING", "Sending"
    SENT = "SENT", "Sent"
    FAILED = "FAILED", "Failed"
    RETRY_PENDING = "RETRY_PENDING", "Retry pending"
    SKIPPED = "SKIPPED", "Skipped"


class EmailProviderChoices(models.TextChoices):
    FAKE = "fake", "Fake"
    SMTP = "smtp", "SMTP"


# Compatibility alias for older imports/tests.
SmsProviderChoices = EmailProviderChoices


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
    recipient_user_id = models.UUIDField(null=True, blank=True)
    recipient_email = models.CharField(max_length=254, null=True, blank=True)
    channel = models.CharField(max_length=16, choices=NotificationChannelChoices.choices, default=NotificationChannelChoices.EMAIL)
    message_type = models.CharField(max_length=32, choices=NotificationMessageTypeChoices.choices)
    title = models.CharField(max_length=255, blank=True, default="")
    body = models.TextField(blank=True, default="")
    metadata = models.JSONField(default=dict, blank=True)
    recipient = models.CharField(max_length=254)
    recipient_masked = models.CharField(max_length=254)
    template_code = models.CharField(max_length=64, null=True, blank=True)
    status = models.CharField(max_length=32, choices=NotificationStatusChoices.choices, default=NotificationStatusChoices.PENDING)
    provider = models.CharField(max_length=32, choices=EmailProviderChoices.choices, default=EmailProviderChoices.FAKE)
    provider_message_id = models.CharField(max_length=128, null=True, blank=True)
    error_code = models.CharField(max_length=64, null=True, blank=True)
    error_message = models.TextField(null=True, blank=True)
    last_error = models.TextField(null=True, blank=True)
    retry_count = models.PositiveIntegerField(default=0)
    scheduled_at = models.DateTimeField(default=timezone.now)
    last_attempt_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_by_user_id = models.UUIDField(null=True, blank=True)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by_user_id = models.UUIDField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "notification_messages"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.channel}:{self.message_type}:{self.recipient_masked}"

    @property
    def message(self) -> str:
        return self.body


class NotificationJobStatusChoices(models.TextChoices):
    PENDING = "PENDING", "Pending"
    SENDING = "SENDING", "Sending"
    SENT = "SENT", "Sent"
    FAILED = "FAILED", "Failed"
    SKIPPED = "SKIPPED", "Skipped"


class NotificationJob(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_id = models.UUIDField(unique=True, db_index=True)
    source_service = models.CharField(max_length=128)
    source_event_type = models.CharField(max_length=128)
    reminder_type = models.CharField(max_length=48)
    notification_type = models.CharField(max_length=48, default="OTP")
    recipient_user_id = models.UUIDField(null=True, blank=True)
    recipient_email = models.CharField(max_length=254, null=True, blank=True)
    channel = models.CharField(max_length=16, choices=NotificationChannelChoices.choices, default=NotificationChannelChoices.EMAIL)
    recipient = models.CharField(max_length=254)
    recipient_masked = models.CharField(max_length=254)
    template_code = models.CharField(max_length=64, null=True, blank=True)
    rendered_message = models.TextField()
    payload = models.JSONField(default=dict)
    status = models.CharField(max_length=32, choices=NotificationJobStatusChoices.choices, default=NotificationJobStatusChoices.PENDING)
    notification_message = models.ForeignKey(NotificationMessage, on_delete=models.SET_NULL, null=True, blank=True, related_name="jobs")
    retry_count = models.PositiveIntegerField(default=0)
    scheduled_at = models.DateTimeField(default=timezone.now)
    last_attempt_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    error_code = models.CharField(max_length=64, null=True, blank=True)
    error_message = models.TextField(null=True, blank=True)
    last_error = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "notification_jobs"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["event_id"]), models.Index(fields=["status"]), models.Index(fields=["recipient"])]

    def __str__(self) -> str:
        return f"{self.source_event_type}:{self.recipient_masked}"


class ProviderDeliveryLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    notification_message = models.ForeignKey(NotificationMessage, on_delete=models.CASCADE, related_name="delivery_logs")
    provider = models.CharField(max_length=32, choices=EmailProviderChoices.choices, default=EmailProviderChoices.FAKE)
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


class OutboxMessageStatusChoices(models.TextChoices):
    PENDING = "PENDING", "Pending"
    PUBLISHED = "PUBLISHED", "Published"
    FAILED = "FAILED", "Failed"


class OutboxMessage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_id = models.UUIDField(unique=True, db_index=True)
    event_type = models.CharField(max_length=128)
    event_version = models.PositiveIntegerField(default=1)
    source_service = models.CharField(max_length=128)
    exchange = models.CharField(max_length=128)
    routing_key = models.CharField(max_length=128)
    payload = models.JSONField(default=dict)
    status = models.CharField(max_length=20, choices=OutboxMessageStatusChoices.choices, default=OutboxMessageStatusChoices.PENDING)
    retry_count = models.PositiveIntegerField(default=0)
    last_error = models.TextField(null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    available_at = models.DateTimeField(default=timezone.now, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "notifications_outbox_messages"
        indexes = [models.Index(fields=["status", "available_at"]), models.Index(fields=["routing_key"])]


class InboxMessageStatusChoices(models.TextChoices):
    PROCESSED = "PROCESSED", "Processed"
    FAILED = "FAILED", "Failed"
    SKIPPED = "SKIPPED", "Skipped"


class InboxMessage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_id = models.UUIDField(unique=True, db_index=True)
    event_type = models.CharField(max_length=128)
    source_service = models.CharField(max_length=128)
    routing_key = models.CharField(max_length=128)
    payload = models.JSONField(default=dict)
    status = models.CharField(max_length=20, choices=InboxMessageStatusChoices.choices, default=InboxMessageStatusChoices.PROCESSED)
    processed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "notifications_inbox_messages"
        indexes = [models.Index(fields=["event_type"]), models.Index(fields=["routing_key"])]
