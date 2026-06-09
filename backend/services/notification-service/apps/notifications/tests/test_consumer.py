"""Tests for the RabbitMQ consumer callback."""

import json
from types import SimpleNamespace
from datetime import datetime, timezone
from unittest.mock import Mock
from uuid import uuid4
from django.test import TestCase, override_settings

from apps.notifications.domain.models import (
    InboxMessage,
    InboxMessageStatusChoices,
    NotificationMessage,
    NotificationStatusChoices,
)

from apps.notifications.infrastructure.consumers import IdentityOtpConsumer
from apps.notifications.infrastructure.event_envelope import build_event_envelope

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

        event_id = str(uuid4())
        payload = build_event_envelope(
            event_type="SendOtpSmsRequested",
            source_service="identity-service",
            routing_key="identity.otp.requested",
            event_id=event_id,
                data={
                "phone_number": "09123456789",
                "code": "123456",
                "purpose": "login",
                "expires_in": 120,
            },
        )

        consumer._consume_callback(channel, method, None, json.dumps(payload).encode())

        self.assertEqual(channel.acked, [1])
        self.assertEqual(channel.rejected, [])
        self.assertEqual(NotificationMessage.objects.count(), 1)
        self.assertEqual(
            NotificationMessage.objects.first().status,
            NotificationStatusChoices.SENT,
        )
        self.assertEqual(InboxMessage.objects.count(), 1)
        self.assertEqual(InboxMessage.objects.first().status, InboxMessageStatusChoices.PROCESSED)
    

    def test_consumer_rejects_failed_message(self):
        consumer = IdentityOtpConsumer()
        consumer.use_case = Mock()
        consumer.use_case.execute.side_effect = RuntimeError("provider failed")
        consumer.max_retries = 0

        channel = DummyChannel()
        method = SimpleNamespace(delivery_tag=2)

        event_id = str(uuid4())
        payload = build_event_envelope(
            event_type="SendOtpSmsRequested",
            source_service="identity-service",
            routing_key="identity.otp.requested",
            event_id=event_id,
            occurred_at="2026-05-30T14:00:00+00:00",
            data={
                "phone_number": "09123456789",
                "code": "123456",
                "purpose": "login",
                "expires_in": 120,
            },
        )

        consumer._consume_callback(channel, method, None, json.dumps(payload).encode())

        self.assertEqual(channel.acked, [2])
        self.assertEqual(channel.rejected, [])
        self.assertEqual(InboxMessage.objects.count(), 1)
        self.assertEqual(InboxMessage.objects.first().status, InboxMessageStatusChoices.FAILED)