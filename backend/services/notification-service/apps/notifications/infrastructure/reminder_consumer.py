from __future__ import annotations

import json
import logging
import time

import pika
from django.conf import settings
from django.utils import timezone

from apps.notifications.application.sms_service import SmsService
from apps.notifications.application.template_service import TemplateService
from apps.notifications.domain.models import NotificationJobStatusChoices, NotificationStatusChoices
from apps.notifications.domain.rules import PhoneNumberRule
from apps.notifications.infrastructure.event_envelope import validate_event_envelope
from apps.notifications.infrastructure.repositories import InboxRepository, NotificationRepository

logger = logging.getLogger(__name__)

SUPPORTED_REMINDER_EVENTS = {
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
        self.sms_service = SmsService()
        self.template_service = TemplateService()
        self.repository = NotificationRepository()
        self.retry_delay_seconds = 2

    def _connect(self):
        credentials = pika.PlainCredentials(settings.RABBITMQ_DEFAULT_USER, settings.RABBITMQ_DEFAULT_PASS)
        params = pika.ConnectionParameters(host=settings.RABBITMQ_HOST, port=settings.RABBITMQ_PORT, credentials=credentials, heartbeat=60, blocked_connection_timeout=30)
        self.connection = pika.BlockingConnection(params)
        self.channel = self.connection.channel()

    def _declare_topology(self):
        self.channel.exchange_declare(exchange=self.exchange, exchange_type="topic", durable=True)
        self.channel.queue_declare(queue=self.dlq, durable=True)
        self.channel.queue_declare(queue=self.queue, durable=True, arguments={"x-dead-letter-exchange": "", "x-dead-letter-routing-key": self.dlq})
        self.channel.queue_bind(queue=self.queue, exchange=self.exchange, routing_key="settlement.payment_reminder.requested")
        self.channel.queue_bind(queue=self.queue, exchange=self.exchange, routing_key="settlement.confirmation_reminder.requested")
        self.channel.queue_bind(queue=self.queue, exchange=self.exchange, routing_key="settlement.plan_item_reminder.requested")

    def _parse(self, body: bytes) -> dict | None:
        try:
            return json.loads(body)
        except Exception:
            logger.exception("Failed to parse reminder payload")
            return None

    def _render_message(self, payload: dict) -> tuple[str, str]:
        data = payload.get("data") or {}
        event_type = payload["event_type"]
        if event_type == "PaymentReminderRequested":
            context = {
                "group_title": (data.get("message_context") or {}).get("group_title", "Settlement group"),
                "message": f"شما در گروه {(data.get('message_context') or {}).get('group_title', 'هم‌دنگ')} مبلغ {data.get('amount_minor')} {data.get('currency', 'IRR')} بدهکار هستید. لطفاً در زمان مناسب تسویه را انجام دهید.",
            }
        elif event_type == "SettlementConfirmationReminderRequested":
            context = {
                "group_title": "هم‌دنگ",
                "message": f"{data.get('payer_display_name', 'کاربر')} اعلام کرده مبلغ {data.get('amount_minor')} {data.get('currency', 'IRR')} را پرداخت کرده است. لطفاً دریافت مبلغ را تأیید یا رد کنید.",
            }
        else:
            context = {
                "group_title": (data.get("message_context") or {}).get("group_title", "هم‌دنگ"),
                "message": f"برای تسویه گروه {(data.get('message_context') or {}).get('group_title', 'هم‌دنگ')} لطفاً مبلغ {data.get('amount_minor')} {data.get('currency', 'IRR')} را به {data.get('receiver_display_name', 'گیرنده')} پرداخت کنید.",
            }
        return self.template_service.render_reminder_message(context)

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
        phone_number = PhoneNumberRule.normalize(data.get("target_phone_number") or data.get("receiver_phone_number") or data.get("payer_phone_number") or data.get("recipient_phone_number"))
        if not phone_number:
            InboxRepository.mark_failed(event_id, event_type, payload["source_service"], payload["routing_key"], payload, "Missing phone number.")
            channel.basic_ack(delivery_tag=method.delivery_tag)
            return
        if self.repository.get_notification_job(event_id):
            InboxRepository.mark_skipped(event_id, event_type, payload["source_service"], payload["routing_key"], payload)
            channel.basic_ack(delivery_tag=method.delivery_tag)
            return
        template_code, rendered_message = self._render_message(payload)
        notification_job = self.repository.create_notification_job(
            event_id=event_id,
            source_service=payload.get("source_service") or "settlement-service",
            source_event_type=event_type,
            reminder_type=SUPPORTED_REMINDER_EVENTS[event_type],
            notification_type=SUPPORTED_REMINDER_EVENTS[event_type],
            channel="SMS",
            recipient_user_id=data.get("target_user_id") or data.get("receiver_user_id") or data.get("payer_user_id"),
            recipient=phone_number,
            recipient_phone_number=phone_number,
            recipient_masked=PhoneNumberRule.mask(phone_number),
            template_code=template_code,
            rendered_message=rendered_message,
            payload=payload,
            status=NotificationJobStatusChoices.SENDING,
            scheduled_at=timezone.now(),
            last_attempt_at=timezone.now(),
        )
        try:
            notification_message = self.sms_service.send_sms(phone_number, rendered_message)
            if notification_message.status == NotificationStatusChoices.FAILED:
                self.repository.update_notification_job(
                    notification_job,
                    status=NotificationJobStatusChoices.FAILED,
                    last_error=notification_message.error_message,
                    error_code=notification_message.error_code,
                    error_message=notification_message.error_message,
                    retry_count=notification_message.retry_count,
                    last_attempt_at=notification_message.last_attempt_at,
                )
                InboxRepository.mark_failed(event_id, event_type, payload["source_service"], payload["routing_key"], payload, notification_message.error_message or "Provider failure.")
                channel.basic_ack(delivery_tag=method.delivery_tag)
                return
            self.repository.update_notification_job(
                notification_job,
                status=NotificationJobStatusChoices.SENT,
                notification_message=notification_message,
                retry_count=notification_message.retry_count,
                sent_at=notification_message.sent_at,
                last_attempt_at=notification_message.last_attempt_at,
                error_code=None,
                error_message=None,
                last_error=None,
            )
            InboxRepository.mark_processed(event_id, event_type, payload["source_service"], payload["routing_key"], payload)
            channel.basic_ack(delivery_tag=method.delivery_tag)
        except Exception as exc:
            logger.exception("Failed to process reminder event: %s", exc)
            self.repository.update_notification_job(
                notification_job,
                status=NotificationJobStatusChoices.FAILED,
                error_code="REMINDER_CONSUMER_FAILED",
                error_message=str(exc),
                last_error=str(exc),
                last_attempt_at=timezone.now(),
            )
            InboxRepository.mark_failed(event_id, event_type, payload["source_service"], payload["routing_key"], payload, str(exc))
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
