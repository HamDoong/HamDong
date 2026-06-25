"""RabbitMQ consumer for group direct invitation events."""

from __future__ import annotations

import json
import logging
import time

import pika
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.notifications.application.sms_service import EmailService
from apps.notifications.domain.models import (
    NotificationChannelChoices,
    NotificationJobStatusChoices,
    NotificationMessageTypeChoices,
    NotificationPriorityChoices,
)
from apps.notifications.domain.rules import EmailRule
from apps.notifications.infrastructure.event_envelope import validate_event_envelope
from apps.notifications.infrastructure.repositories import InboxRepository, NotificationRepository

logger = logging.getLogger(__name__)

SUPPORTED_EVENT_TYPES = {"GroupDirectInvitationCreated"}


class GroupDirectInvitationConsumer:
    def __init__(self):
        self.exchange = getattr(settings, "GROUP_RABBITMQ_EXCHANGE", "hamdong.group")
        self.queue = getattr(settings, "NOTIFICATION_GROUP_DIRECT_INVITE_QUEUE", "notification.group.direct_invites")
        self.dlq = f"{self.queue}{getattr(settings, 'EVENT_DLQ_SUFFIX', '.dlq')}"
        self.retry_delay_seconds = 2
        self.email_service = EmailService()

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
        self.channel.queue_bind(queue=self.queue, exchange=self.exchange, routing_key="group.direct_invitation.created")

    def _parse(self, body):
        if isinstance(body, (bytes, bytearray)):
            body = body.decode("utf-8")
        return json.loads(body)

    def _build_subject(self, data: dict) -> str:
        return f"Invitation to join {data.get('group_title') or 'a group'}"

    def _build_body(self, data: dict) -> str:
        inviter = data.get("invited_by_art_name") or "A group admin"
        group_title = data.get("group_title") or "a group"
        expires_at = data.get("expires_at") or ""
        return f"{inviter} invited you to join {group_title}. Expires at: {expires_at}"

    def _handle(self, payload: dict):
        valid, error = validate_event_envelope(payload)
        if not valid:
            raise ValueError(error)
        if payload.get("event_type") not in SUPPORTED_EVENT_TYPES:
            return
        event_id = payload["event_id"]
        if InboxRepository.was_processed(event_id):
            InboxRepository.mark_skipped(event_id, payload["event_type"], payload["source_service"], payload["routing_key"], payload)
            return
        if NotificationRepository.get_notification_job(event_id):
            InboxRepository.mark_skipped(event_id, payload["event_type"], payload["source_service"], payload["routing_key"], payload)
            return

        data = payload.get("data") or {}
        recipient_user_id = data.get("recipient_user_id")
        recipient_email = EmailRule.normalize(data.get("recipient_email"))
        subject = self._build_subject(data)
        body = self._build_body(data)
        metadata = {
            "invitation_id": data.get("invitation_id"),
            "group_id": data.get("group_id"),
            "group_title": data.get("group_title"),
            "invited_by_user_id": data.get("invited_by_user_id"),
            "expires_at": data.get("expires_at"),
            "event_id": event_id,
        }

        with transaction.atomic():
            in_app = NotificationRepository.create_notification_message(
                recipient_user_id=recipient_user_id,
                recipient_email=recipient_email,
                channel=NotificationChannelChoices.IN_APP,
                message_type=NotificationMessageTypeChoices.INVITE,
                title=subject,
                body=body,
                metadata=metadata,
                recipient=str(recipient_user_id),
                recipient_masked=str(recipient_user_id),
                priority=NotificationPriorityChoices.HIGH,
                status="SENT",
            )
            job = NotificationRepository.create_notification_job(
                event_id=event_id,
                source_service=payload.get("source_service") or "group-service",
                source_event_type=payload["event_type"],
                reminder_type="GROUP_DIRECT_INVITATION",
                notification_type="INVITE",
                recipient_user_id=recipient_user_id,
                recipient_email=recipient_email,
                channel=NotificationChannelChoices.EMAIL,
                recipient=recipient_email or str(recipient_user_id or ""),
                recipient_masked=EmailRule.mask(recipient_email) if recipient_email else str(recipient_user_id or "***"),
                template_code="GROUP_DIRECT_INVITATION",
                rendered_message=body,
                payload=payload,
                status=NotificationJobStatusChoices.PENDING,
                notification_message=in_app,
                scheduled_at=timezone.now(),
                last_attempt_at=timezone.now(),
            )

        if recipient_email:
            email_message = self.email_service.send_email(
                recipient_email,
                subject,
                body,
                recipient_user_id=recipient_user_id,
                metadata=metadata,
                template_code="GROUP_DIRECT_INVITATION",
                message_type=NotificationMessageTypeChoices.INVITE,
            )
            NotificationRepository.update_notification_job(
                job,
                status=NotificationJobStatusChoices.SENT if email_message.status == "SENT" else NotificationJobStatusChoices.FAILED,
                notification_message=email_message,
                sent_at=timezone.now() if email_message.status == "SENT" else None,
                last_error=getattr(email_message, "last_error", None),
                error_message=getattr(email_message, "error_message", None),
            )
        else:
            NotificationRepository.update_notification_job(
                job,
                status=NotificationJobStatusChoices.SKIPPED,
                last_error="Missing recipient email.",
                error_message="Missing recipient email.",
            )

        InboxRepository.mark_processed(event_id, payload["event_type"], payload["source_service"], payload["routing_key"], payload)

    def _callback(self, ch, method, properties, body):
        payload = None
        try:
            payload = self._parse(body)
            self._handle(payload)
        except Exception as exc:
            logger.exception("Failed to process direct invitation event")
            if isinstance(payload, dict) and payload.get("event_id"):
                InboxRepository.mark_failed(
                    payload["event_id"],
                    payload.get("event_type", "UNKNOWN"),
                    payload.get("source_service", "group-service"),
                    payload.get("routing_key", ""),
                    payload,
                    str(exc),
                )
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
                logger.exception("Notification direct invite consumer unavailable; retrying")
                time.sleep(self.retry_delay_seconds)
            finally:
                if getattr(self, "connection", None) and not self.connection.is_closed:
                    self.connection.close()
