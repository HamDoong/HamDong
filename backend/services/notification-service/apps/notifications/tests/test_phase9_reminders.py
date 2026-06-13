import json
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

from django.test import TestCase, override_settings

from apps.notifications.domain.models import NotificationJob, NotificationMessage, NotificationStatusChoices
from apps.notifications.infrastructure.reminder_consumer import SettlementReminderConsumer
from apps.notifications.infrastructure.event_envelope import build_event_envelope

class DummyChannel:
    def __init__(self):
        self.acked = []
        self.rejected = []

    def basic_ack(self, delivery_tag):
        self.acked.append(delivery_tag)

    def basic_reject(self, delivery_tag, requeue=False):
        self.rejected.append((delivery_tag, requeue))


class SettlementReminderConsumerTests(TestCase):
    @override_settings(SMS_PROVIDER="fake")
    def test_consumer_creates_notification_job_and_sends_sms(self):
        consumer = SettlementReminderConsumer()
        channel = DummyChannel()
        method = SimpleNamespace(delivery_tag=1)

        payload = build_event_envelope(
            event_type="PaymentReminderRequested",
            source_service="settlement-service",
            routing_key="settlement.payment_reminder.requested",
            event_id="11111111-1111-1111-1111-111111111111",
            data={
                "message_context": {
                    "group_title": "Trip to Shiraz",
                },
                "amount_minor": 250000,
                "currency": "IRR",
                "recipient_phone_number": "09123456789",
                "template_code": "SETTLEMENT_REMINDER",
            },
        )

        consumer._handle_message(channel, method, None, json.dumps(payload).encode())

        self.assertEqual(channel.acked, [1])
        self.assertEqual(channel.rejected, [])
        self.assertEqual(NotificationJob.objects.count(), 1)
        self.assertEqual(NotificationMessage.objects.count(), 1)
        self.assertEqual(
            NotificationMessage.objects.first().status,
            NotificationStatusChoices.SENT,
        )

    @override_settings(SMS_PROVIDER="fake")
    def test_consumer_rejects_unsupported_event(self):
        consumer = SettlementReminderConsumer()
        channel = DummyChannel()
        method = SimpleNamespace(delivery_tag=2)
    
        payload = build_event_envelope(
            event_type="UnsupportedReminder",
            source_service="settlement-service",
            routing_key="settlement.unsupported",
            event_id="11111111-1111-1111-1111-111111111112",
            data={
                "recipient_phone_number": "09123456789",
            },
        )
    
        consumer._handle_message(channel, method, None, json.dumps(payload).encode())
    
        self.assertEqual(channel.acked, [2])
        self.assertEqual(channel.rejected, [])
        self.assertEqual(NotificationJob.objects.count(), 0)
