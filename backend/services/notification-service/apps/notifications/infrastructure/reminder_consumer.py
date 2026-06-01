import json
import logging
import time

import pika
from django.conf import settings
from django.utils import timezone

from apps.notifications.application.sms_service import SmsService
from apps.notifications.application.template_service import TemplateService
from apps.notifications.domain.models import (
    NotificationJobStatusChoices,
    NotificationStatusChoices,
)
from apps.notifications.domain.rules import PhoneNumberRule
from apps.notifications.infrastructure.repositories import NotificationRepository

logger = logging.getLogger(__name__)

SUPPORTED_REMINDER_EVENTS = {
    "PaymentReminderRequested",
    "SettlementConfirmationReminderRequested",
    "SettlementPlanItemReminderRequested",
}


class SettlementReminderConsumer:
    def __init__(self):
        self.exchange = settings.SETTLEMENT_RABBITMQ_EXCHANGE
        self.queue = settings.SETTLEMENT_REMINDER_QUEUE
        self.dlx = settings.SETTLEMENT_REMINDER_DLX
        self.dlq = settings.SETTLEMENT_REMINDER_DLQ
        self.connection = None
        self.channel = None
        self.sms_service = SmsService()
        self.template_service = TemplateService()
        self.repository = NotificationRepository()
        self.retry_delay_seconds = 2

    def _connect(self):
        credentials = pika.PlainCredentials(
            settings.RABBITMQ_DEFAULT_USER,
            settings.RABBITMQ_DEFAULT_PASS,
        )
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
        self.channel.exchange_declare(
            exchange=self.exchange,
            exchange_type="topic",
            durable=True,
        )
        self.channel.exchange_declare(exchange=self.dlx, exchange_type="direct", durable=True)
        self.channel.queue_declare(queue=self.dlq, durable=True)
        self.channel.queue_bind(
            queue=self.dlq,
            exchange=self.dlx,
            routing_key=self.dlq,
        )
        self.channel.queue_declare(
            queue=self.queue,
            durable=True,
            arguments={
                "x-dead-letter-exchange": self.dlx,
                "x-dead-letter-routing-key": self.dlq,
            },
        )
        self.channel.queue_bind(
            queue=self.queue,
            exchange=self.exchange,
            routing_key="settlement.reminder.requested",
        )

    def _parse(self, body: bytes) -> dict | None:
        try:
            return json.loads(body)
        except Exception:
            logger.exception("Failed to parse reminder payload")
            return None

    def _render_message(self, payload: dict) -> tuple[str, str]:
        data = payload.get("data") or {}
        template_context = data.get("template_context") or {}
        template_context.setdefault("group_title", "Settlement group")
        template_context.setdefault("message", data.get("message") or "یادآوری تسویه")
        template_context.setdefault("recipient_phone_number", data.get("phone_number", ""))
        template_context.setdefault("template_code", data.get("template_code") or settings.SMS_TEMPLATE_SETTLEMENT_REMINDER)
        return self.template_service.render_reminder_message(template_context)

    def _handle_message(self, channel, method, properties, body):
        payload = self._parse(body)
        if not payload:
            channel.basic_ack(delivery_tag=method.delivery_tag)
            return

        event_id = payload.get("event_id")
        event_type = payload.get("event_type")
        if event_type not in SUPPORTED_REMINDER_EVENTS:
            logger.warning("Unsupported reminder event received: %s", event_type)
            channel.basic_ack(delivery_tag=method.delivery_tag)
            return

        data = payload.get("data") or {}
        phone_number = PhoneNumberRule.normalize(data.get("recipient_phone_number") or data.get("phone_number"))
        if not phone_number:
            channel.basic_reject(delivery_tag=method.delivery_tag, requeue=False)
            return

        if event_id and self.repository.get_notification_job(event_id):
            channel.basic_ack(delivery_tag=method.delivery_tag)
            return

        template_code, rendered_message = self._render_message(payload)
        notification_job = self.repository.create_notification_job(
            event_id=event_id,
            source_service=payload.get("source_service") or "settlement-service",
            source_event_type=event_type,
            reminder_type=event_type,
            channel="SMS",
            recipient=phone_number,
            recipient_masked=PhoneNumberRule.mask(phone_number),
            template_code=template_code,
            rendered_message=rendered_message,
            payload=payload,
            status=NotificationJobStatusChoices.PROCESSING,
            last_attempt_at=timezone.now(),
        )

        try:
            notification_message = self.sms_service.send_sms(phone_number, rendered_message)
            if notification_message.status == NotificationStatusChoices.FAILED:
                self.repository.update_notification_job(
                    notification_job,
                    status=NotificationJobStatusChoices.FAILED,
                    error_code=notification_message.error_code,
                    error_message=notification_message.error_message,
                    retry_count=notification_message.retry_count,
                    last_attempt_at=notification_message.last_attempt_at,
                )
                channel.basic_reject(delivery_tag=method.delivery_tag, requeue=False)
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
            )
            channel.basic_ack(delivery_tag=method.delivery_tag)
        except Exception as exc:
            logger.exception("Failed to process reminder event: %s", exc)
            self.repository.update_notification_job(
                notification_job,
                status=NotificationJobStatusChoices.FAILED,
                error_code="REMINDER_CONSUMER_FAILED",
                error_message=str(exc),
                last_attempt_at=timezone.now(),
            )
            channel.basic_reject(delivery_tag=method.delivery_tag, requeue=False)

    def start(self):
        while True:
            try:
                self._connect()
                self._declare_topology()
                self.channel.basic_qos(prefetch_count=1)
                self.channel.basic_consume(
                    queue=self.queue,
                    on_message_callback=self._handle_message,
                    auto_ack=False,
                )
                logger.info("Consuming settlement reminder messages from queue=%s", self.queue)
                try:
                    self.channel.start_consuming()
                finally:
                    if self.connection and not self.connection.is_closed:
                        self.connection.close()
                break
            except Exception:
                logger.exception("Settlement reminder consumer unavailable; retrying")
                time.sleep(self.retry_delay_seconds)
