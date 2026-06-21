from __future__ import annotations

import json
import logging
import time

import pika
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.notifications.application.sms_service import EmailService
from apps.notifications.application.template_service import TemplateService
from apps.notifications.domain.models import (
    NotificationChannelChoices,
    NotificationJobStatusChoices,
    NotificationMessageTypeChoices,
    NotificationStatusChoices,
)
from apps.notifications.domain.rules import EmailRule, sanitize_message_text
from apps.notifications.infrastructure.event_envelope import (
    build_event_envelope,
    validate_event_envelope,
)
from apps.notifications.infrastructure.repositories import (
    InboxRepository,
    NotificationRepository,
    OutboxRepository,
)

logger = logging.getLogger(__name__)

SUPPORTED_REMINDER_EVENTS = {
    "DebtReminderRequested": "DEBT_REMINDER",
    "PaymentReminderRequested": "PAYMENT_REMINDER",
    "SettlementConfirmationReminderRequested": "SETTLEMENT_CONFIRMATION_REMINDER",
    "SettlementPlanItemReminderRequested": "PLAN_ITEM_REMINDER",
}


class SettlementReminderConsumer:
    def __init__(self):
        self.exchange = settings.SETTLEMENT_REMINDER_EXCHANGE
        self.queue = settings.NOTIFICATION_REMINDER_QUEUE
        self.dlq = f"{self.queue}{getattr(settings, 'EVENT_DLQ_SUFFIX', '.dlq')}"
        self.connection = None
        self.channel = None
        self.email_service = EmailService()
        self.template_service = TemplateService()
        self.repository = NotificationRepository()
        self.retry_delay_seconds = 2

    def _connect(self):
        credentials = pika.PlainCredentials(settings.RABBITMQ_DEFAULT_USER, settings.RABBITMQ_DEFAULT_PASS)
        params = pika.ConnectionParameters(
            host=settings.RABBITMQ_HOST,
            port=settings.RABBITMQ_PORT,
            credentials=credentials,
            heartbeat=60,
            blocked_connection_timeout=30,
        )
        self.connection = pika.BlockingConnection(params)
        self.channel = self.connection.channel()

    def _declare_topology(self):
        self.channel.exchange_declare(exchange=self.exchange, exchange_type="topic", durable=True)
        self.channel.queue_declare(queue=self.dlq, durable=True)
        self.channel.queue_declare(
            queue=self.queue,
            durable=True,
            arguments={"x-dead-letter-exchange": "", "x-dead-letter-routing-key": self.dlq},
        )
        self.channel.queue_bind(queue=self.queue, exchange=self.exchange, routing_key="settlement.debt_reminder.requested")
        # Legacy bindings retained for compatibility.
        self.channel.queue_bind(queue=self.queue, exchange=self.exchange, routing_key="settlement.payment_reminder.requested")
        self.channel.queue_bind(queue=self.queue, exchange=self.exchange, routing_key="settlement.confirmation_reminder.requested")
        self.channel.queue_bind(queue=self.queue, exchange=self.exchange, routing_key="settlement.plan_item_reminder.requested")

    def _parse(self, body: bytes) -> dict | None:
        try:
            return json.loads(body)
        except Exception:
            logger.exception("Failed to parse reminder payload")
            return None

    def _render_message(self, payload: dict) -> tuple[str, str, str]:
        data = payload.get("data") or {}
        event_type = payload["event_type"]
        reminder_type = SUPPORTED_REMINDER_EVENTS[event_type]
        if event_type == "DebtReminderRequested":
            context = {
                "group_title": data.get("group_title", "HamDong"),
                "amount": data.get("amount_minor"),
                "currency": data.get("currency", "IRR"),
                "creditor_name": data.get("creditor_name", "your group member"),
            }
        elif event_type == "PaymentReminderRequested":
            context = {
                "group_title": (data.get("message_context") or {}).get("group_title", "HamDong"),
                "amount": data.get("amount_minor"),
                "currency": data.get("currency", "IRR"),
            }
        elif event_type == "SettlementConfirmationReminderRequested":
            context = {
                "payer_name": data.get("payer_art_name", "User"),
                "amount": data.get("amount_minor"),
                "currency": data.get("currency", "IRR"),
            }
        else:
            context = {
                "group_title": (data.get("message_context") or {}).get("group_title", "HamDong"),
                "amount": data.get("amount_minor"),
                "currency": data.get("currency", "IRR"),
                "receiver_name": data.get("receiver_art_name", "Receiver"),
            }
        return self.template_service.render_reminder_message(reminder_type, context)

    def _safe_error(self, value) -> str | None:
        if not value:
            return None
        return sanitize_message_text(str(value))[:255]

    def _create_in_app_notification(self, data: dict, rendered_message: str, template_code: str, subject: str):
        recipient_user_id = data.get("recipient_user_id") or data.get("target_user_id") or data.get("receiver_user_id") or data.get("payer_user_id")
        if not recipient_user_id:
            return None
        metadata = {
            "reminder_id": data.get("reminder_id"),
            "settlement_plan_item_id": data.get("settlement_plan_item_id") or data.get("item_id"),
            "settlement_plan_id": data.get("settlement_plan_id") or data.get("plan_id"),
            "group_id": data.get("group_id"),
            "group_title": data.get("group_title") or (data.get("message_context") or {}).get("group_title"),
        }
        return self.repository.create_notification_message(
            recipient_user_id=recipient_user_id,
            channel=NotificationChannelChoices.IN_APP,
            message_type=NotificationMessageTypeChoices.REMINDER,
            title=subject,
            body=rendered_message,
            metadata=metadata,
            recipient=str(recipient_user_id),
            recipient_masked=str(recipient_user_id),
            template_code=template_code,
            status=NotificationStatusChoices.SENT,
        )

    def _publish_delivery_update(self, *, payload: dict, status: str, channel_statuses: dict, last_error: str | None):
        reminder_id = (payload.get("data") or {}).get("reminder_id")
        if not reminder_id:
            return None
        event_payload = {
            "reminder_id": reminder_id,
            "status": status,
            "channel_statuses": channel_statuses,
            "last_error": last_error,
            "delivery_updated_at": timezone.now().isoformat(),
        }
        envelope = build_event_envelope(
            "DebtReminderDeliveryUpdated",
            event_payload,
            source_service="notification-service",
            routing_key="notification.debt_reminder.delivery.updated",
        )
        return OutboxRepository.create(
            event_type="DebtReminderDeliveryUpdated",
            routing_key="notification.debt_reminder.delivery.updated",
            payload=envelope,
            exchange=getattr(settings, "NOTIFICATION_RABBITMQ_EXCHANGE", "hamdong.notification"),
        )

    def _determine_aggregate_status(self, channel_statuses: dict[str, str]) -> str:
        values = set(channel_statuses.values())
        if not values:
            return NotificationJobStatusChoices.SKIPPED
        if values <= {"SENT"}:
            return NotificationJobStatusChoices.SENT
        if "SENT" in values and "FAILED" in values:
            return NotificationJobStatusChoices.PARTIALLY_SENT
        if values <= {"FAILED"}:
            return NotificationJobStatusChoices.FAILED
        return NotificationJobStatusChoices.SENT if "SENT" in values else NotificationJobStatusChoices.SENDING

    def _handle_message(self, channel, method, properties, body):
        payload = self._parse(body)
        if not payload:
            channel.basic_ack(delivery_tag=method.delivery_tag)
            return
        valid, error = validate_event_envelope(payload)
        if not valid:
            logger.warning("Invalid reminder event: %s", error)
            channel.basic_ack(delivery_tag=method.delivery_tag)
            return
        event_id = payload["event_id"]
        event_type = payload["event_type"]
        if event_type not in SUPPORTED_REMINDER_EVENTS:
            channel.basic_ack(delivery_tag=method.delivery_tag)
            return
        if InboxRepository.was_processed(event_id):
            InboxRepository.mark_skipped(event_id, event_type, payload["source_service"], payload["routing_key"], payload)
            channel.basic_ack(delivery_tag=method.delivery_tag)
            return

        data = payload.get("data") or {}
        email = EmailRule.normalize(data.get("recipient_email") or data.get("target_email") or data.get("receiver_email") or data.get("payer_email"))
        send_in_app = bool(data.get("send_in_app", event_type == "DebtReminderRequested"))
        send_email = bool(data.get("send_email", bool(email)))
        if not send_in_app and not send_email:
            InboxRepository.mark_skipped(event_id, event_type, payload["source_service"], payload["routing_key"], payload)
            channel.basic_ack(delivery_tag=method.delivery_tag)
            return
        if self.repository.get_notification_job(event_id):
            InboxRepository.mark_skipped(event_id, event_type, payload["source_service"], payload["routing_key"], payload)
            channel.basic_ack(delivery_tag=method.delivery_tag)
            return

        template_code, subject, rendered_message = self._render_message(payload)
        recipient_user_id = data.get("recipient_user_id") or data.get("target_user_id") or data.get("receiver_user_id") or data.get("payer_user_id")
        metadata = {
            "reminder_id": data.get("reminder_id"),
            "group_id": data.get("group_id"),
            "group_title": data.get("group_title") or (data.get("message_context") or {}).get("group_title"),
            "settlement_plan_id": data.get("settlement_plan_id") or data.get("plan_id"),
            "settlement_plan_item_id": data.get("settlement_plan_item_id") or data.get("item_id"),
            "sequence_number": data.get("sequence_number"),
            "source": data.get("source"),
        }

        with transaction.atomic():
            notification_job = self.repository.create_notification_job(
                event_id=event_id,
                source_service=payload.get("source_service") or "settlement-service",
                source_event_type=event_type,
                reminder_type=SUPPORTED_REMINDER_EVENTS[event_type],
                notification_type=SUPPORTED_REMINDER_EVENTS[event_type],
                channel=NotificationChannelChoices.EMAIL if send_email else NotificationChannelChoices.IN_APP,
                recipient_user_id=recipient_user_id,
                recipient=email or str(recipient_user_id or ""),
                recipient_email=email,
                recipient_masked=EmailRule.mask(email) if email else str(recipient_user_id or "***"),
                template_code=template_code,
                rendered_message=rendered_message,
                payload=payload,
                status=NotificationJobStatusChoices.SENDING,
                scheduled_at=timezone.now(),
                last_attempt_at=timezone.now(),
            )

            channel_statuses: dict[str, str] = {}
            primary_message = None
            last_error = None

            if send_in_app:
                try:
                    primary_message = self._create_in_app_notification(data, rendered_message, template_code, subject)
                    channel_statuses[NotificationChannelChoices.IN_APP] = "SENT"
                except Exception as exc:
                    logger.exception("Failed to create in-app reminder notification")
                    channel_statuses[NotificationChannelChoices.IN_APP] = "FAILED"
                    last_error = self._safe_error(exc)

            if send_email:
                if not email:
                    channel_statuses[NotificationChannelChoices.EMAIL] = "FAILED"
                    last_error = self._safe_error("Missing recipient email.")
                else:
                    try:
                        email_message = self.email_service.send_email(
                            email,
                            subject,
                            rendered_message,
                            recipient_user_id=recipient_user_id,
                            metadata=metadata,
                            template_code=template_code,
                        )
                        primary_message = primary_message or email_message
                        if email_message.status == NotificationStatusChoices.SENT:
                            channel_statuses[NotificationChannelChoices.EMAIL] = "SENT"
                        else:
                            channel_statuses[NotificationChannelChoices.EMAIL] = "FAILED"
                            last_error = self._safe_error(email_message.last_error or email_message.error_message)
                    except Exception as exc:
                        logger.exception("Failed to deliver reminder email")
                        channel_statuses[NotificationChannelChoices.EMAIL] = "FAILED"
                        last_error = self._safe_error(exc)

            aggregate_status = self._determine_aggregate_status(channel_statuses)
            self.repository.update_notification_job(
                notification_job,
                status=aggregate_status,
                notification_message=primary_message,
                payload={**payload, "delivery": {"channel_statuses": channel_statuses}},
                sent_at=timezone.now() if aggregate_status in (NotificationJobStatusChoices.SENT, NotificationJobStatusChoices.PARTIALLY_SENT) else None,
                last_attempt_at=timezone.now(),
                error_code=None if aggregate_status != NotificationJobStatusChoices.FAILED else "DELIVERY_FAILED",
                error_message=last_error,
                last_error=last_error,
            )
            settlement_status = "SENT"
            if aggregate_status == NotificationJobStatusChoices.PARTIALLY_SENT:
                settlement_status = "PARTIALLY_SENT"
            elif aggregate_status == NotificationJobStatusChoices.FAILED:
                settlement_status = "FAILED"
            self._publish_delivery_update(
                payload=payload,
                status=settlement_status,
                channel_statuses=channel_statuses,
                last_error=last_error,
            )
            InboxRepository.mark_processed(event_id, event_type, payload["source_service"], payload["routing_key"], payload)
        channel.basic_ack(delivery_tag=method.delivery_tag)

    def start(self):
        while True:
            try:
                self._connect()
                self._declare_topology()
                self.channel.basic_qos(prefetch_count=1)
                self.channel.basic_consume(queue=self.queue, on_message_callback=self._handle_message, auto_ack=False)
                self.channel.start_consuming()
            except KeyboardInterrupt:
                break
            except Exception:
                logger.exception("Settlement reminder consumer unavailable; retrying")
                time.sleep(self.retry_delay_seconds)
            finally:
                if self.connection and not self.connection.is_closed:
                    self.connection.close()
