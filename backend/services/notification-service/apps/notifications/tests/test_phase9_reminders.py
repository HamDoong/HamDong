import json
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from django.test import TestCase, override_settings

from apps.notifications.domain.models import (
    InboxMessage,
    NotificationChannelChoices,
    NotificationJob,
    NotificationJobStatusChoices,
    NotificationMessage,
    NotificationStatusChoices,
    OutboxMessage,
)
from apps.notifications.infrastructure.event_envelope import build_event_envelope
from apps.notifications.infrastructure.reminder_consumer import SettlementReminderConsumer


class DummyChannel:
    def __init__(self):
        self.acked = []
        self.rejected = []

    def basic_ack(self, delivery_tag):
        self.acked.append(delivery_tag)

    def basic_reject(self, delivery_tag, requeue=False):
        self.rejected.append((delivery_tag, requeue))


@override_settings(
    EMAIL_PROVIDER="fake",
    EMAIL_OTP_MAX_RETRIES=0,
    EMAIL_OTP_RETRY_DELAYS_SECONDS="0",
)
class SettlementReminderConsumerTests(TestCase):
    def setUp(self):
        self.consumer = SettlementReminderConsumer()
        self.channel = DummyChannel()

    def build_payload(self, *, event_id=None, send_in_app=True, send_email=True):
        return build_event_envelope(
            event_type="DebtReminderRequested",
            source_service="settlement-service",
            routing_key="settlement.debt_reminder.requested",
            event_id=event_id or str(uuid4()),
            data={
                "reminder_id": str(uuid4()),
                "source": "AUTOMATIC",
                "sequence_number": 1,
                "group_id": str(uuid4()),
                "group_title": "Trip to Shiraz",
                "settlement_plan_id": str(uuid4()),
                "settlement_plan_item_id": str(uuid4()),
                "recipient_user_id": str(uuid4()),
                "recipient_email": "artist@example.com",
                "creditor_user_id": str(uuid4()),
                "creditor_name": "Owner",
                "amount_minor": 250000,
                "currency": "IRR",
                "send_in_app": send_in_app,
                "send_email": send_email,
                "requested_by_user_id": str(uuid4()),
            },
        )

    def test_consumer_creates_in_app_email_job_and_delivery_update(self):
        payload = self.build_payload()
        method = SimpleNamespace(delivery_tag=1)

        self.consumer._handle_message(
            self.channel,
            method,
            None,
            json.dumps(payload).encode(),
        )

        self.assertEqual(self.channel.acked, [1])
        self.assertEqual(NotificationJob.objects.count(), 1)
        self.assertEqual(NotificationMessage.objects.count(), 2)
        self.assertEqual(
            NotificationMessage.objects.filter(channel=NotificationChannelChoices.IN_APP).count(),
            1,
        )
        self.assertEqual(
            NotificationMessage.objects.filter(channel=NotificationChannelChoices.EMAIL).count(),
            1,
        )
        self.assertEqual(NotificationJob.objects.first().status, NotificationJobStatusChoices.SENT)
        self.assertEqual(OutboxMessage.objects.count(), 1)
        self.assertEqual(OutboxMessage.objects.first().event_type, "DebtReminderDeliveryUpdated")
        self.assertEqual(InboxMessage.objects.count(), 1)

    def test_duplicate_event_does_not_create_duplicate_delivery(self):
        payload = self.build_payload(event_id="11111111-1111-1111-1111-111111111111")
        method = SimpleNamespace(delivery_tag=2)

        self.consumer._handle_message(self.channel, method, None, json.dumps(payload).encode())
        self.consumer._handle_message(self.channel, method, None, json.dumps(payload).encode())

        self.assertEqual(NotificationJob.objects.count(), 1)
        self.assertEqual(NotificationMessage.objects.count(), 2)
        self.assertEqual(OutboxMessage.objects.count(), 1)
        self.assertEqual(InboxMessage.objects.count(), 1)

    def test_in_app_only_event_skips_email_delivery(self):
        payload = self.build_payload(send_in_app=True, send_email=False)
        method = SimpleNamespace(delivery_tag=3)

        self.consumer._handle_message(self.channel, method, None, json.dumps(payload).encode())

        self.assertEqual(NotificationJob.objects.count(), 1)
        self.assertEqual(NotificationMessage.objects.count(), 1)
        message = NotificationMessage.objects.get()
        self.assertEqual(message.channel, NotificationChannelChoices.IN_APP)
        self.assertEqual(message.status, NotificationStatusChoices.SENT)

    def test_partial_failure_keeps_in_app_success_and_records_safe_error(self):
        payload = self.build_payload(send_in_app=True, send_email=True)
        method = SimpleNamespace(delivery_tag=4)

        with patch.object(
            self.consumer.email_service,
            "send_email",
            side_effect=RuntimeError("provider failed 123456"),
        ):
            self.consumer._handle_message(self.channel, method, None, json.dumps(payload).encode())

        job = NotificationJob.objects.get()
        self.assertEqual(job.status, NotificationJobStatusChoices.PARTIALLY_SENT)
        self.assertEqual(NotificationMessage.objects.count(), 1)
        self.assertEqual(
            NotificationMessage.objects.first().channel,
            NotificationChannelChoices.IN_APP,
        )
        self.assertNotIn("123456", job.last_error or "")
        delivery_event = OutboxMessage.objects.get()
        self.assertEqual(
            delivery_event.payload["data"]["channel_statuses"][NotificationChannelChoices.IN_APP],
            "SENT",
        )
        self.assertEqual(
            delivery_event.payload["data"]["channel_statuses"][NotificationChannelChoices.EMAIL],
            "FAILED",
        )
