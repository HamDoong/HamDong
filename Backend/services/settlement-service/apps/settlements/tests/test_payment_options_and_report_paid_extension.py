from unittest.mock import patch
from uuid import uuid4

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.settlements.application.settlement_plan_service import SettlementPlanService
from apps.settlements.domain.models import (
    BankCardProjection,
    GroupBalanceSnapshot,
    ManualSettlement,
    SettlementPlanItemStatusChoices,
)
from apps.settlements.tests.plan_test_helpers import (
    api_client,
    auth_user,
    create_group,
    create_member,
    create_user_projection,
)


class FakeBankCardClient:
    def resolve_payment_context_cards(self, owner_user_id, card_ids=None):
        return [
            {
                "id": str(card_id),
                "type": "BANK_CARD",
                "card_number": "6037991234567890",
                "masked_card_number": "6037 **** **** 7890",
                "card_number_last4": "7890",
                "bank_name": "Melli",
                "holder_name": "Receiver Holder",
                "is_default": True,
            }
            for card_id in (card_ids or [])
        ]


class SettlementPaymentOptionsAndReportPaidTests(TestCase):
    def setUp(self):
        self.owner = auth_user()
        self.group = create_group(owner_user_id=self.owner.sub)
        create_member(self.group.group_id, user_id=self.owner.sub, role="OWNER", art_name_snapshot="owner_artist")
        self.payer = create_member(self.group.group_id, art_name_snapshot="payer_artist")
        self.receiver = create_member(self.group.group_id, art_name_snapshot="receiver_artist")
        create_user_projection(identity_user_id=self.payer.user_id, art_name="payer_artist", email="payer@example.com")
        create_user_projection(identity_user_id=self.receiver.user_id, art_name="receiver_artist", email="receiver@example.com")
        self.card_id = uuid4()
        BankCardProjection.objects.create(
            card_id=self.card_id,
            user_id=self.receiver.user_id,
            holder_name="Receiver Holder",
            bank_name="Melli",
            card_number_last4="7890",
            masked_card_number="6037 **** **** 7890",
            is_default=True,
            is_active=True,
        )
        self.publisher = patch(
            "apps.settlements.infrastructure.rabbitmq_publisher.RabbitMQPublisher.publish",
            return_value=True,
        )
        self.publisher.start()
        self.addCleanup(self.publisher.stop)
        self.client_patch = patch(
            "apps.settlements.application.settlement_plan_service.IdentityBankCardClient",
            lambda: FakeBankCardClient(),
        )
        self.client_patch.start()
        self.addCleanup(self.client_patch.stop)
        self.service = SettlementPlanService()
        self.seed_and_activate_plan()

    def seed_and_activate_plan(self):
        GroupBalanceSnapshot.objects.create(
            group_id=self.group.group_id,
            user_id=self.payer.user_id,
            currency="IRR",
            total_paid_minor=0,
            total_share_minor=50000,
            total_settled_paid_minor=0,
            total_settled_received_minor=0,
            net_balance_minor=-50000,
        )
        GroupBalanceSnapshot.objects.create(
            group_id=self.group.group_id,
            user_id=self.receiver.user_id,
            currency="IRR",
            total_paid_minor=50000,
            total_share_minor=0,
            total_settled_paid_minor=0,
            total_settled_received_minor=0,
            net_balance_minor=50000,
        )
        self.plan, items = self.service.generate_plan(self.group.group_id, self.owner.sub)
        self.service.activate_plan(self.plan.id, self.owner.sub)
        self.item = items[0]

    def test_payer_can_view_payee_payment_options(self):
        payer_client = api_client(auth_user(self.payer.user_id))
        response = payer_client.get(
            reverse(
                "settlement_plan_item_payment_options",
                kwargs={"item_id": self.item.id},
            )
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["payer"]["art_name"], "payer_artist")
        self.assertEqual(payload["payee"]["art_name"], "receiver_artist")
        self.assertEqual(payload["payment_options"][0]["card_number"], "6037991234567890")
        self.assertEqual(payload["payment_options"][0]["masked_card_number"], "6037 **** **** 7890")

    def test_non_payer_cannot_view_payment_options(self):
        receiver_client = api_client(auth_user(self.receiver.user_id))
        response = receiver_client.get(
            reverse(
                "settlement_plan_item_payment_options",
                kwargs={"item_id": self.item.id},
            )
        )
        self.assertEqual(response.status_code, 403)

    def test_report_paid_saves_safe_bank_card_snapshot(self):
        payer_client = api_client(auth_user(self.payer.user_id))
        paid_at = timezone.now().isoformat()
        response = payer_client.post(
            reverse(
                "report_settlement_plan_item_paid",
                kwargs={"item_id": self.item.id},
            ),
            data={
                "payment_method": "BANK_TRANSFER",
                "paid_to_bank_card_id": str(self.card_id),
                "amount_minor": 50000,
                "paid_at": paid_at,
                "note": "card to card",
                "tracking_code": "123456",
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.item.refresh_from_db()
        self.assertEqual(self.item.status, SettlementPlanItemStatusChoices.REPORTED)
        settlement = ManualSettlement.objects.get(id=response.json()["manual_settlement_id"])
        self.assertEqual(str(settlement.paid_to_bank_card_id), str(self.card_id))
        self.assertEqual(settlement.paid_to_bank_card_masked_number, "6037 **** **** 7890")
        self.assertEqual(settlement.paid_to_bank_card_last4, "7890")
        self.assertEqual(response.json()["paid_to_bank_card"]["masked_card_number"], "6037 **** **** 7890")
        self.assertNotIn("card_number", response.json()["paid_to_bank_card"])

    def test_confirmed_item_is_not_payable(self):
        payer_client = api_client(auth_user(self.payer.user_id))
        payer_client.post(
            reverse(
                "report_settlement_plan_item_paid",
                kwargs={"item_id": self.item.id},
            ),
            data={"amount_minor": 50000},
            content_type="application/json",
        )
        receiver_client = api_client(auth_user(self.receiver.user_id))
        receiver_client.post(
            reverse(
                "confirm_settlement_plan_item",
                kwargs={"item_id": self.item.id},
            ),
            data={},
            content_type="application/json",
        )
        response = payer_client.get(
            reverse(
                "settlement_plan_item_payment_options",
                kwargs={"item_id": self.item.id},
            )
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["error"]["code"], "SETTLEMENT_NOT_PAYABLE")
