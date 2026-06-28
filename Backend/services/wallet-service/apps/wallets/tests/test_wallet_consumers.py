
from django.test import TestCase

from apps.wallets.domain.models import (
    InboxMessage,
    SettlementItemProjection,
    SettlementItemStatusChoices,
    SettlementPlanStatusChoices,
    UserProjection,
)
from apps.wallets.infrastructure.rabbitmq_consumer import WalletEventConsumer
from apps.wallets.tests.helpers import identity_event, settlement_event


class WalletConsumerTests(TestCase):
    def setUp(self):
        self.consumer = WalletEventConsumer()

    def test_identity_consumer_is_idempotent(self):
        payload = identity_event(
            event_id="11111111-1111-1111-1111-111111111111",
            data={
                "user_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                "email": "user@example.com",
                "art_name": "artist",
                "role": "USER",
                "is_active": True,
            },
        )
        self.consumer.process_identity_payload(payload)
        self.consumer.process_identity_payload(payload)
        self.assertEqual(UserProjection.objects.count(), 1)
        self.assertEqual(InboxMessage.objects.count(), 1)

    def test_settlement_projection_lifecycle(self):
        plan_id = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
        item_id = "cccccccc-cccc-cccc-cccc-cccccccccccc"
        generated = settlement_event(
            "SettlementPlanGenerated",
            data={
                "plan_id": plan_id,
                "group_id": "dddddddd-dddd-dddd-dddd-dddddddddddd",
                "currency": "IRR",
                "status": "DRAFT",
                "items": [
                    {
                        "item_id": item_id,
                        "payer_user_id": "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee",
                        "receiver_user_id": "ffffffff-ffff-ffff-ffff-ffffffffffff",
                        "amount_minor": 500000,
                        "currency": "IRR",
                        "status": "PENDING",
                        "created_at": "2026-06-20T12:00:00Z",
                    }
                ],
            },
        )
        self.consumer.process_settlement_payload(generated)
        projection = SettlementItemProjection.objects.get(item_id=item_id)
        self.assertEqual(projection.plan_status, SettlementPlanStatusChoices.DRAFT)
        activated = settlement_event("SettlementPlanActivated", data={"plan_id": plan_id})
        self.consumer.process_settlement_payload(activated)
        projection.refresh_from_db()
        self.assertEqual(projection.plan_status, SettlementPlanStatusChoices.ACTIVE)
        reported = settlement_event("SettlementPlanItemReported", data={"item_id": item_id})
        self.consumer.process_settlement_payload(reported)
        projection.refresh_from_db()
        self.assertEqual(projection.item_status, SettlementItemStatusChoices.REPORTED)
        confirmed = settlement_event("SettlementPlanItemConfirmed", data={"item_id": item_id})
        self.consumer.process_settlement_payload(confirmed)
        projection.refresh_from_db()
        self.assertEqual(projection.item_status, SettlementItemStatusChoices.CONFIRMED)

    def test_duplicate_settlement_event_does_not_duplicate_projection(self):
        item_id = "cccccccc-cccc-cccc-cccc-cccccccccccc"
        payload = settlement_event(
            "SettlementPlanGenerated",
            event_id="99999999-9999-9999-9999-999999999999",
            data={
                "plan_id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
                "group_id": "dddddddd-dddd-dddd-dddd-dddddddddddd",
                "currency": "IRR",
                "status": "DRAFT",
                "items": [
                    {
                        "item_id": item_id,
                        "payer_user_id": "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee",
                        "receiver_user_id": "ffffffff-ffff-ffff-ffff-ffffffffffff",
                        "amount_minor": 500000,
                        "currency": "IRR",
                        "status": "PENDING",
                        "created_at": "2026-06-20T12:00:00Z",
                    }
                ],
            },
        )
        self.consumer.process_settlement_payload(payload)
        self.consumer.process_settlement_payload(payload)
        self.assertEqual(SettlementItemProjection.objects.filter(item_id=item_id).count(), 1)
