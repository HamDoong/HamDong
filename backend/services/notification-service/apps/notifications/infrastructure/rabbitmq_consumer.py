"""RabbitMQ consumer for identity OTP events."""

import json
import logging
import time
from typing import Callable

import pika
from django.conf import settings

from apps.notifications.application.use_cases import ProcessOtpSmsUseCase
from apps.notifications.domain.rules import PhoneNumberRule

logger = logging.getLogger(__name__)


class RabbitMqConsumer:
    def __init__(self):
        self.exchange = settings.IDENTITY_RABBITMQ_EXCHANGE
        self.queue = settings.IDENTITY_OTP_QUEUE
        self.dlx = settings.IDENTITY_OTP_DLX
        self.dlq = settings.IDENTITY_OTP_DLQ
        self.connection = None
        self.channel = None
        self.use_case = ProcessOtpSmsUseCase()
        self.max_retries = settings.SMS_OTP_MAX_RETRIES
        self.retry_delays = [int(x) for x in settings.SMS_OTP_RETRY_DELAYS_SECONDS.split(",") if x.strip()]

    def _connect(self):
        credentials = pika.PlainCredentials(
            settings.RABBITMQ_DEFAULT_USER, settings.RABBITMQ_DEFAULT_PASS
        )
        params = pika.ConnectionParameters(
            host=settings.RABBITMQ_HOST,
            port=settings.RABBITMQ_PORT,
            credentials=credentials,
            connection_attempts=3,
            retry_delay=2,
        )
        self.connection = pika.BlockingConnection(params)
        self.channel = self.connection.channel()

    def _declare_topology(self):
        # main exchange
        self.channel.exchange_declare(exchange=self.exchange, exchange_type="topic", durable=True)

        # declare DLX and DLQ
        self.channel.exchange_declare(exchange=self.dlx, exchange_type="fanout", durable=True)
        self.channel.queue_declare(queue=self.dlq, durable=True)
        self.channel.queue_bind(queue=self.dlq, exchange=self.dlx)

        # declare main queue with DLX set
        arguments = {"x-dead-letter-exchange": self.dlx}
        self.channel.queue_declare(queue=self.queue, durable=True, arguments=arguments)
        self.channel.queue_bind(queue=self.queue, exchange=self.exchange, routing_key="identity.otp.requested")

    def _safe_parse(self, body: bytes) -> dict | None:
        try:
            return json.loads(body)
        except Exception:
            logger.exception("Failed to parse message body as JSON")
            return None

    def _validate_event(self, payload: dict) -> bool:
        if not isinstance(payload, dict):
            return False
        if payload.get("event_type") != "SendOtpSmsRequested":
            return False
        data = payload.get("data") or {}
        phone = data.get("phone_number")
        code = data.get("code")
        expires_in = data.get("expires_in")
        if not phone or not code or not expires_in:
            return False
        if not PhoneNumberRule.is_valid(phone):
            return False
        return True

    def _process_message(self, payload: dict) -> bool:
        # Use the application use case which handles creating NotificationMessage and retries
        try:
            result = self.use_case.execute(payload)
            # If use_case.execute raises or returns a failed NotificationMessage, treat accordingly
            return True
        except Exception:
            logger.exception("Error while processing OTP command")
            return False

    def _consume_callback(self, ch, method, properties, body):
        # Parse
        payload = self._safe_parse(body)
        delivery_tag = method.delivery_tag

        if not payload:
            # invalid JSON, ack to remove
            ch.basic_ack(delivery_tag=delivery_tag)
            return

        # Validate
        if not self._validate_event(payload):
            logger.warning("Invalid or unsupported event received; acking and skipping")
            ch.basic_ack(delivery_tag=delivery_tag)
            return

        # Mask for logs
        phone = payload.get("data", {}).get("phone_number")
        logger.info("Consuming OTP request for %s", PhoneNumberRule.mask(phone))

        # Retry loop (in-process)
        success = False
        for attempt in range(self.max_retries + 1):
            if attempt > 0:
                delay = self.retry_delays[min(attempt - 1, len(self.retry_delays) - 1)]
                logger.info("Retrying (%d/%d) after %ds", attempt, self.max_retries, delay)
                time.sleep(delay)

            try:
                ok = self._process_message(payload)
                if ok:
                    success = True
                    ch.basic_ack(delivery_tag=delivery_tag)
                    break
            except Exception:
                logger.exception("Unhandled error processing message")

        if not success:
            # Exhausted retries: publish to DLX for manual inspection and ack original
            try:
                logger.error("Exhausted retries for message; routing to DLQ for %s", PhoneNumberRule.mask(phone))
                # Publish to DLX exchange with original body
                self.channel.basic_publish(exchange=self.dlx, routing_key="", body=json.dumps(payload))
            except Exception:
                logger.exception("Failed to route message to DLQ")
            finally:
                ch.basic_ack(delivery_tag=delivery_tag)

    def start_consuming(self):
        self._connect()
        self._declare_topology()
        self.channel.basic_qos(prefetch_count=1)
        self.channel.basic_consume(queue=self.queue, on_message_callback=self._consume_callback)
        logger.info("Starting RabbitMQ consumer for queue=%s", self.queue)
        try:
            self.channel.start_consuming()
        except KeyboardInterrupt:
            logger.info("Consumer interrupted")
        finally:
            if self.connection and not self.connection.is_closed:
                self.connection.close()
