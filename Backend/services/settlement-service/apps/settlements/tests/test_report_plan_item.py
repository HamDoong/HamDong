from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from apps.settlements.application.settlement_plan_service import SettlementPlanService
from apps.settlements.domain.models import (
    ManualSettlement,
    ManualSettlementStatusChoices,
    SettlementPlanEventLog,
    SettlementPlanItemStatusChoices,
    SettlementPlanStatusChoices,
)
from apps.settlements.tests.plan_test_helpers import (
    api_client,
    auth_user,
    create_group,
    create_member,
)


class ReportPlanItemTests(TestCase):
    def setUp(self):
        self.owner = auth_user()
        self.group = create_group(owner_user_id=self.owner.sub)
        create_member(self.group.group_id, user_id=self.owner.sub, role="OWNER")
        self.payer = create_member(self.group.group_id, art_name_snapshot="Payer")
        self.receiver = create_member(
            self.group.group_id, art_name_snapshot="Receiver"
        )
        self.client = api_client(self.owner)
        self.service = SettlementPlanService()
        self.plan = None
        self.item = None

    def seed_and_activate_plan(self):
        from apps.settlements.domain.models import GroupBalanceSnapshot

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
        with patch(
            "apps.settlements.infrastructure.rabbitmq_publisher.RabbitMQPublisher.publish",
            return_value=True,
        ):
            self.plan, items = self.service.generate_plan(
                self.group.group_id, self.owner.sub
            )
            self.service.activate_plan(self.plan.id, self.owner.sub)
        self.item = items[0]

    def test_only_payer_can_report_plan_item_paid(self):
        self.seed_and_activate_plan()
        non_payer_client = api_client(auth_user(self.receiver.user_id))
        response = non_payer_client.post(
            reverse(
                "report_settlement_plan_item_paid", kwargs={"item_id": self.item.id}
            ),
            data={"description": "test"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

    def test_reported_item_cannot_be_reported_again_after_confirmation(self):
        self.seed_and_activate_plan()
        payer_client = api_client(auth_user(self.payer.user_id))
        receiver_client = api_client(auth_user(self.receiver.user_id))
        with patch(
            "apps.settlements.infrastructure.rabbitmq_publisher.RabbitMQPublisher.publish",
            return_value=True,
        ):
            payer_client.post(
                reverse(
                    "report_settlement_plan_item_paid", kwargs={"item_id": self.item.id}
                ),
                data={},
                content_type="application/json",
            )
            receiver_client.post(
                reverse(
                    "confirm_settlement_plan_item", kwargs={"item_id": self.item.id}
                )
            )

        response = payer_client.post(
            reverse(
                "report_settlement_plan_item_paid", kwargs={"item_id": self.item.id}
            ),
            data={"description": "again"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "INVALID_PLAN_ITEM_ACTION")

    def test_cancelled_item_cannot_be_reported(self):
        self.seed_and_activate_plan()
        payer_client = api_client(auth_user(self.payer.user_id))
        with patch(
            "apps.settlements.infrastructure.rabbitmq_publisher.RabbitMQPublisher.publish",
            return_value=True,
        ):
            self.service.cancel_plan(self.plan.id, self.owner.sub)

        response = payer_client.post(
            reverse(
                "report_settlement_plan_item_paid", kwargs={"item_id": self.item.id}
            ),
            data={"description": "after cancel"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "INVALID_PLAN_ITEM_ACTION")

    def test_report_plan_item_creates_manual_settlement_and_sets_reference(self):
        self.seed_and_activate_plan()
        payer_client = api_client(auth_user(self.payer.user_id))
        with patch(
            "apps.settlements.infrastructure.rabbitmq_publisher.RabbitMQPublisher.publish",
            return_value=True,
        ):
            response = payer_client.post(
                reverse(
                    "report_settlement_plan_item_paid", kwargs={"item_id": self.item.id}
                ),
                data={"description": "پرداخت کارت به کارت انجام شد"},
                content_type="application/json",
            )
        self.assertEqual(response.status_code, 200)
        self.item.refresh_from_db()
        self.assertEqual(self.item.status, SettlementPlanItemStatusChoices.REPORTED)
        self.assertIsNotNone(self.item.manual_settlement_id)
        settlement = ManualSettlement.objects.get(id=self.item.manual_settlement_id)
        self.assertEqual(
            settlement.status, ManualSettlementStatusChoices.PENDING_CONFIRMATION
        )
        self.assertEqual(settlement.payer_user_id, self.payer.user_id)
        self.assertEqual(settlement.receiver_user_id, self.receiver.user_id)

    def test_confirming_plan_item_completes_plan_when_all_items_confirmed(self):
        self.seed_and_activate_plan()
        payer_client = api_client(auth_user(self.payer.user_id))
        receiver_client = api_client(auth_user(self.receiver.user_id))
        with patch(
            "apps.settlements.infrastructure.rabbitmq_publisher.RabbitMQPublisher.publish",
            return_value=True,
        ):
            payer_client.post(
                reverse(
                    "report_settlement_plan_item_paid", kwargs={"item_id": self.item.id}
                ),
                data={},
                content_type="application/json",
            )
            response = receiver_client.post(
                reverse(
                    "confirm_settlement_plan_item", kwargs={"item_id": self.item.id}
                )
            )
        self.assertEqual(response.status_code, 200)
        self.item.refresh_from_db()
        self.plan.refresh_from_db()
        self.assertEqual(self.item.status, SettlementPlanItemStatusChoices.CONFIRMED)
        self.assertEqual(self.plan.status, SettlementPlanStatusChoices.COMPLETED)
        self.assertIsNotNone(self.plan.completed_at)

    def test_only_receiver_can_confirm_or_reject_plan_item(self):
        self.seed_and_activate_plan()
        payer_client = api_client(auth_user(self.payer.user_id))
        with patch(
            "apps.settlements.infrastructure.rabbitmq_publisher.RabbitMQPublisher.publish",
            return_value=True,
        ):
            payer_client.post(
                reverse(
                    "report_settlement_plan_item_paid", kwargs={"item_id": self.item.id}
                ),
                data={},
                content_type="application/json",
            )
        response = payer_client.post(
            reverse("confirm_settlement_plan_item", kwargs={"item_id": self.item.id})
        )
        self.assertEqual(response.status_code, 403)
        response = payer_client.post(
            reverse("reject_settlement_plan_item", kwargs={"item_id": self.item.id}),
            data={"reason": "reject"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

    def test_reject_plan_item_sets_rejected(self):
        self.seed_and_activate_plan()
        payer_client = api_client(auth_user(self.payer.user_id))
        receiver_client = api_client(auth_user(self.receiver.user_id))
        with patch(
            "apps.settlements.infrastructure.rabbitmq_publisher.RabbitMQPublisher.publish",
            return_value=True,
        ):
            payer_client.post(
                reverse(
                    "report_settlement_plan_item_paid", kwargs={"item_id": self.item.id}
                ),
                data={},
                content_type="application/json",
            )
            response = receiver_client.post(
                reverse(
                    "reject_settlement_plan_item", kwargs={"item_id": self.item.id}
                ),
                data={"reason": "مبلغ را دریافت نکردم"},
                content_type="application/json",
            )
        self.assertEqual(response.status_code, 200)
        self.item.refresh_from_db()
        self.assertEqual(self.item.status, SettlementPlanItemStatusChoices.REJECTED)
        self.assertTrue(
            SettlementPlanEventLog.objects.filter(event_type="ITEM_REJECTED").exists()
        )

    def test_plan_events_are_published(self):
        self.seed_and_activate_plan()
        payer_client = api_client(auth_user(self.payer.user_id))
        receiver_client = api_client(auth_user(self.receiver.user_id))
        with patch(
            "apps.settlements.infrastructure.rabbitmq_publisher.RabbitMQPublisher.publish",
            return_value=True,
        ) as publish_mock:
            payer_client.post(
                reverse(
                    "report_settlement_plan_item_paid", kwargs={"item_id": self.item.id}
                ),
                data={},
                content_type="application/json",
            )
            receiver_client.post(
                reverse(
                    "confirm_settlement_plan_item", kwargs={"item_id": self.item.id}
                )
            )
        routing_keys = [call.args[2] for call in publish_mock.call_args_list]
        self.assertIn("settlement.plan_item.reported", routing_keys)
        self.assertIn("settlement.plan_item.confirmed", routing_keys)
        self.assertIn("settlement.plan.completed", routing_keys)
