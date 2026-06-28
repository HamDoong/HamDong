
from datetime import timezone as dt_timezone
from unittest.mock import patch
from uuid import uuid4

from django.test import TestCase
from django.utils import timezone

from apps.settlements.domain.models import (
    InboxMessage,
    InboxMessageStatusChoices,
    SettlementPlanEventLog,
    SettlementPlanEventTypeChoices,
    SettlementPlanItem,
    SettlementPlanItemStatusChoices,
    SettlementPlanStatusChoices,
)
from apps.settlements.infrastructure.rabbitmq_consumer import SettlementEventConsumer
from apps.settlements.application.settlement_plan_service import SettlementPlanService
from apps.settlements.tests.plan_test_helpers import (
    auth_user,
    create_group,
    create_member,
    create_user_projection,
    seed_snapshot,
)


class SettlementWalletEventConsumerTests(TestCase):
    def setUp(self):
        self.owner = auth_user()
        self.group = create_group(owner_user_id=self.owner.sub)
        create_member(self.group.group_id, user_id=self.owner.sub, role="OWNER", art_name_snapshot="owner_artist")
        self.payer = create_member(self.group.group_id, art_name_snapshot="payer_artist")
        self.receiver = create_member(self.group.group_id, art_name_snapshot="receiver_artist")
        create_user_projection(identity_user_id=self.payer.user_id, art_name="payer_artist", email="payer@example.com")
        create_user_projection(identity_user_id=self.receiver.user_id, art_name="receiver_artist", email="receiver@example.com")
        seed_snapshot(self.group.group_id, self.payer.user_id, -50000)
        seed_snapshot(self.group.group_id, self.receiver.user_id, 50000)
        self.publish_patch = patch(
            "apps.settlements.infrastructure.rabbitmq_publisher.RabbitMQPublisher.publish",
            return_value=True,
        )
        self.publish_patch.start()
        self.addCleanup(self.publish_patch.stop)
        self.service = SettlementPlanService()
        self.plan, items = self.service.generate_plan(self.group.group_id, self.owner.sub)
        self.service.activate_plan(self.plan.id, self.owner.sub)
        self.item = items[0]
        self.consumer = SettlementEventConsumer()

    def _wallet_event(self, *, event_id=None, item_id=None, wallet_transaction_id=None):
        now = timezone.now().astimezone(dt_timezone.utc).isoformat().replace("+00:00", "Z")
        correlation_id = str(uuid4())
        return {
            "event_id": str(event_id or uuid4()),
            "event_type": "WalletSettlementPaid",
            "event_version": 1,
            "occurred_at": now,
            "source_service": "wallet-service",
            "correlation_id": correlation_id,
            "causation_id": correlation_id,
            "routing_key": "wallet.settlement.paid",
            "data": {
                "wallet_transaction_id": str(wallet_transaction_id or uuid4()),
                "settlement_plan_item_id": str(item_id or self.item.id),
                "payer_user_id": str(self.payer.user_id),
                "payee_user_id": str(self.receiver.user_id),
                "amount_minor": self.item.amount_minor,
                "currency": self.item.currency,
                "paid_at": now,
            },
        }

    def test_wallet_event_confirms_item_and_completes_plan(self):
        payload = self._wallet_event()
        self.consumer._process(payload, self.consumer._handle_wallet)

        self.item.refresh_from_db()
        self.plan.refresh_from_db()

        self.assertEqual(self.item.status, SettlementPlanItemStatusChoices.CONFIRMED)
        self.assertEqual(self.plan.status, SettlementPlanStatusChoices.COMPLETED)
        self.assertTrue(self.item.updated_at <= timezone.now())
        self.assertEqual(
            SettlementPlanEventLog.objects.filter(
                settlement_plan_id=self.plan.id,
                settlement_plan_item_id=self.item.id,
                event_type=SettlementPlanEventTypeChoices.ITEM_CONFIRMED,
            ).count(),
            1,
        )
        self.assertEqual(
            SettlementPlanEventLog.objects.filter(
                settlement_plan_id=self.plan.id,
                event_type=SettlementPlanEventTypeChoices.PLAN_COMPLETED,
            ).count(),
            1,
        )
        inbox = InboxMessage.objects.get(event_id=payload["event_id"])
        self.assertEqual(inbox.status, InboxMessageStatusChoices.PROCESSED)

    def test_duplicate_wallet_event_is_idempotent(self):
        payload = self._wallet_event(event_id="11111111-1111-1111-1111-111111111111")
        self.consumer._process(payload, self.consumer._handle_wallet)
        self.consumer._process(payload, self.consumer._handle_wallet)

        self.item.refresh_from_db()
        self.plan.refresh_from_db()

        self.assertEqual(self.item.status, SettlementPlanItemStatusChoices.CONFIRMED)
        self.assertEqual(self.plan.status, SettlementPlanStatusChoices.COMPLETED)
        self.assertEqual(
            SettlementPlanEventLog.objects.filter(
                settlement_plan_id=self.plan.id,
                settlement_plan_item_id=self.item.id,
                event_type=SettlementPlanEventTypeChoices.ITEM_CONFIRMED,
            ).count(),
            1,
        )
        self.assertEqual(InboxMessage.objects.filter(event_id=payload["event_id"]).count(), 1)
        inbox = InboxMessage.objects.get(event_id=payload["event_id"])
        self.assertEqual(inbox.status, InboxMessageStatusChoices.SKIPPED)

    def test_wallet_event_can_confirm_rejected_item(self):
        SettlementPlanItem.objects.filter(id=self.item.id).update(status=SettlementPlanItemStatusChoices.REJECTED)
        self.item.refresh_from_db()

        payload = self._wallet_event()
        self.consumer._process(payload, self.consumer._handle_wallet)

        self.item.refresh_from_db()
        self.plan.refresh_from_db()

        self.assertEqual(self.item.status, SettlementPlanItemStatusChoices.CONFIRMED)
        self.assertEqual(self.plan.status, SettlementPlanStatusChoices.COMPLETED)
