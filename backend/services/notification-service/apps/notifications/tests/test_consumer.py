"""Tests for the RabbitMQ consumer callback."""

import json
from types import SimpleNamespace
from datetime import datetime, timezone
from unittest.mock import Mock

from django.test import TestCase, override_settings

from apps.notifications.domain.models import (
    NotificationMessage,
    NotificationStatusChoices,
)
from apps.notifications.infrastructure.consumers import IdentityOtpConsumer


class DummyChannel:
    def __init__(self):
        self.acked = []
        self.rejected = []

    def basic_ack(self, delivery_tag):
        self.acked.append(delivery_tag)

    def basic_reject(self, delivery_tag, requeue=False):
        self.rejected.append((delivery_tag, requeue))


class ConsumerTests(TestCase):
    @override_settings(SMS_PROVIDER="fake")
    def test_consumer_processes_otp_message(self):
        consumer = IdentityOtpConsumer()
        channel = DummyChannel()
        method = SimpleNamespace(delivery_tag=1)
        payload = {
            "event_id": "event-10",
            "event_type": "SendOtpSmsRequested",
            "occurred_at": datetime.now(timezone.utc).isoformat(),
            "version": 1,
            "data": {
                "phone_number": "09123456789",
                "code": "123456",
                "purpose": "login",
                "expires_in": 120,
            },
        }

        consumer._handle_message(channel, method, None, json.dumps(payload).encode())

        self.assertEqual(channel.acked, [1])
        self.assertEqual(channel.rejected, [])
        self.assertEqual(NotificationMessage.objects.count(), 1)
        self.assertEqual(
            NotificationMessage.objects.first().status,
            NotificationStatusChoices.SENT,
        )

    def test_consumer_rejects_failed_message(self):
        consumer = IdentityOtpConsumer()
        consumer.sms_service = Mock()
        consumer.sms_service.handle_otp_command.return_value = SimpleNamespace(
            status=NotificationStatusChoices.FAILED
        )

        channel = DummyChannel()
        method = SimpleNamespace(delivery_tag=2)
        payload = {
            "event_id": "event-11",
            "event_type": "SendOtpSmsRequested",
            "occurred_at": "2026-05-30T14:00:00+00:00",
            "version": 1,
            "data": {
                "phone_number": "09123456789",
                "code": "123456",
                "purpose": "login",
                "expires_in": 120,
            },
        }

        consumer._handle_message(channel, method, None, json.dumps(payload).encode())

        self.assertEqual(channel.acked, [])
        self.assertEqual(channel.rejected, [(2, False)])
