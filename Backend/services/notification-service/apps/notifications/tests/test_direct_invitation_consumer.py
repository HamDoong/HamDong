from __future__ import annotations

from uuid import uuid4

from django.test import TestCase, override_settings

from apps.notifications.domain.models import (
    InboxMessage,
    NotificationJob,
    NotificationJobStatusChoices,
    NotificationMessage,
    NotificationMessageTypeChoices,
)
from apps.notifications.infrastructure.direct_invitation_consumer import GroupDirectInvitationConsumer
from apps.notifications.infrastructure.event_envelope import build_event_envelope


@override_settings(EMAIL_PROVIDER="fake")
class GroupDirectInvitationConsumerTests(TestCase):
    def setUp(self):
        self.consumer = GroupDirectInvitationConsumer()

    def _payload(self, *, event_id=None):
        return build_event_envelope(
            event_type="GroupDirectInvitationCreated",
            source_service="group-service",
            routing_key="group.direct_invitation.created",
            event_id=str(event_id or uuid4()),
            data={
                "invitation_id": str(uuid4()),
                "group_id": str(uuid4()),
                "group_title": "سفر شمال",
                "recipient_user_id": str(uuid4()),
                "recipient_email": "invitee@example.com",
                "recipient_art_name": "invitee_artist",
                "invited_by_user_id": str(uuid4()),
                "expires_at": "2026-06-30T09:00:00Z",
            },
        )

    def test_created_event_creates_in_app_notification_and_email_job(self):
        payload = self._payload()
        self.consumer._handle(payload)

        self.assertEqual(NotificationJob.objects.count(), 1)
        self.assertEqual(NotificationMessage.objects.filter(message_type=NotificationMessageTypeChoices.INVITE).count(), 2)
        self.assertTrue(NotificationMessage.objects.filter(channel="IN_APP").exists())
        self.assertTrue(NotificationMessage.objects.filter(channel="EMAIL").exists())

        job = NotificationJob.objects.get()
        self.assertEqual(job.status, NotificationJobStatusChoices.SENT)
        self.assertEqual(InboxMessage.objects.count(), 1)

    def test_duplicate_event_is_idempotent(self):
        payload = self._payload(event_id=uuid4())
        self.consumer._handle(payload)
        self.consumer._handle(payload)

        self.assertEqual(NotificationJob.objects.count(), 1)
        self.assertEqual(NotificationMessage.objects.count(), 2)
        self.assertEqual(InboxMessage.objects.count(), 1)

    def test_notification_payload_does_not_expose_secrets_or_sms(self):
        payload = self._payload()
        self.consumer._handle(payload)

        messages = list(NotificationMessage.objects.order_by("created_at"))
        serialized = "".join(f"{message.title}{message.body}{message.metadata}" for message in messages)
        self.assertNotIn("token", serialized.lower())
        self.assertNotIn("otp", serialized.lower())
        self.assertFalse(NotificationMessage.objects.filter(channel="PUSH").exists())
