"""RabbitMQ consumer for identity OTP events."""

from __future__ import annotations

import json
import logging
import time

import pika
from django.conf import settings

from apps.notifications.application.use_cases import ProcessOtpSmsUseCase
from apps.notifications.domain.rules import PhoneNumberRule
from apps.notifications.infrastructure.event_envelope import validate_event_envelope
from apps.notifications.infrastructure.repositories import InboxRepository

logger = logging.getLogger(__name__)


class RabbitMqConsumer:
    def __init__(self):
        self.exchange = settings.IDENTITY_RABBITMQ_EXCHANGE
        self.queue = settings.IDENTITY_OTP_QUEUE
        self.dlq = settings.IDENTITY_OTP_DLQ
        self.connection = None
        self.channel = None
        self.use_case = ProcessOtpSmsUseCase()
        self.max_retries = settings.SMS_OTP_MAX_RETRIES
        self.retry_delays = [int(x) for x in settings.SMS_OTP_RETRY_DELAYS_SECONDS.split(",") if x.strip()]

    def _connect(self):
        credentials = pika.PlainCredentials(settings.RABBITMQ_DEFAULT_USER, settings.RABBITMQ_DEFAULT_PASS)
        params = pika.ConnectionParameters(host=settings.RABBITMQ_HOST, port=settings.RABBITMQ_PORT, credentials=credentials, connection_attempts=3, retry_delay=2)
        self.connection = pika.BlockingConnection(params)
        self.channel = self.connection.channel()

    def _declare_topology(self):
        self.channel.exchange_declare(exchange=self.exchange, exchange_type="topic", durable=True)
        self.channel.queue_declare(queue=self.dlq, durable=True)
        self.channel.queue_declare(queue=self.queue, durable=True, arguments={"x-dead-letter-exchange": "", "x-dead-letter-routing-key": self.dlq})
        self.channel.queue_bind(queue=self.queue, exchange=self.exchange, routing_key="identity.otp.requested")

    def _safe_parse(self, body: bytes) -> dict | None:
        try:
            return json.loads(body)
        except Exception:
            logger.exception("Failed to parse message body as JSON")
            return None

    def _validate_event(self, payload: dict) -> bool:
        valid, _ = validate_event_envelope(payload)
        if not valid or payload.get("event_type") != "SendOtpSmsRequested":
            return False
        data = payload.get("data") or {}
        phone = data.get("phone_number")
        code = data.get("code")
        expires_in = data.get("expires_in")
        return bool(phone and code and expires_in and PhoneNumberRule.is_valid(phone))

    def _consume_callback(self, ch, method, properties, body):
        payload = self._safe_parse(body)
        delivery_tag = method.delivery_tag
        if not payload:
            ch.basic_ack(delivery_tag=delivery_tag)
            return
        if not self._validate_event(payload):
            logger.warning("Invalid or unsupported event received; acking and skipping")
            ch.basic_ack(delivery_tag=delivery_tag)
            return
        event_id = payload["event_id"]
        if InboxRepository.was_processed(event_id):
            InboxRepository.mark_skipped(event_id, payload["event_type"], payload["source_service"], payload["routing_key"], payload)
            ch.basic_ack(delivery_tag=delivery_tag)
            return
        phone = payload.get("data", {}).get("phone_number")
        logger.info("Consuming OTP request for %s", PhoneNumberRule.mask(phone))
        success = False
        for attempt in range(self.max_retries + 1):
            if attempt > 0:
                delay = self.retry_delays[min(attempt - 1, len(self.retry_delays) - 1)]
                time.sleep(delay)
            try:
                self.use_case.execute(payload)
                InboxRepository.mark_processed(event_id, payload["event_type"], payload["source_service"], payload["routing_key"], payload)
                success = True
                ch.basic_ack(delivery_tag=delivery_tag)
                break
            except Exception as exc:
                logger.exception("Error while processing OTP command")
                InboxRepository.mark_failed(event_id, payload["event_type"], payload["source_service"], payload["routing_key"], payload, str(exc))
        if not success:
            ch.basic_ack(delivery_tag=delivery_tag)

    def start_consuming(self):
        while True:
            try:
                self._connect()
                self._declare_topology()
                self.channel.basic_qos(prefetch_count=1)
                self.channel.basic_consume(queue=self.queue, on_message_callback=self._consume_callback)
                self.channel.start_consuming()
            except KeyboardInterrupt:
                break
            except Exception:
                logger.exception("Notification OTP consumer unavailable; retrying")
                time.sleep(2)
            finally:
                if self.connection and not self.connection.is_closed:
                    self.connection.close()
