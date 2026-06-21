from unittest.mock import patch

from django.test import TestCase

from apps.settlements.application.settlement_plan_service import SettlementPlanService
from apps.settlements.domain.models import (
    GroupBalanceSnapshot,
    SettlementPlanEventLog,
    SettlementPlanItem,
    SettlementPlanItemStatusChoices,
    SettlementPlanStatusChoices,
)
from apps.settlements.tests.plan_test_helpers import (
    api_client,
    auth_user,
    create_group,
    create_member,
)


class CompleteSettlementPlanTests(TestCase):
    def setUp(self):
        self.owner = auth_user()
        self.group = create_group(owner_user_id=self.owner.sub)
        create_member(self.group.group_id, user_id=self.owner.sub, role="OWNER")
        self.payer_a = create_member(self.group.group_id)
        self.payer_b = create_member(self.group.group_id)
        self.creditor = create_member(self.group.group_id)
        self.service = SettlementPlanService()
        self.owner_client = api_client(self.owner)

    def seed_balances(self):
        GroupBalanceSnapshot.objects.create(
            group_id=self.group.group_id,
            user_id=self.payer_a.user_id,
            currency="IRR",
            total_paid_minor=0,
            total_share_minor=60000,
            total_settled_paid_minor=0,
            total_settled_received_minor=0,
            net_balance_minor=-60000,
        )
        GroupBalanceSnapshot.objects.create(
            group_id=self.group.group_id,
            user_id=self.payer_b.user_id,
            currency="IRR",
            total_paid_minor=0,
            total_share_minor=40000,
            total_settled_paid_minor=0,
            total_settled_received_minor=0,
            net_balance_minor=-40000,
        )
        GroupBalanceSnapshot.objects.create(
            group_id=self.group.group_id,
            user_id=self.creditor.user_id,
            currency="IRR",
            total_paid_minor=100000,
            total_share_minor=0,
            total_settled_paid_minor=0,
            total_settled_received_minor=0,
            net_balance_minor=100000,
        )

    def test_confirming_all_items_completes_plan_and_publishes_completed_event(self):
        self.seed_balances()
        with patch(
            "apps.settlements.infrastructure.rabbitmq_publisher.RabbitMQPublisher.publish",
            return_value=True,
        ) as publish_mock:
            plan, items = self.service.generate_plan(
                self.group.group_id, self.owner.sub
            )
            self.service.activate_plan(plan.id, self.owner.sub)
            payer_a_client = api_client(auth_user(self.payer_a.user_id))
            payer_b_client = api_client(auth_user(self.payer_b.user_id))
            receiver_client = api_client(auth_user(self.creditor.user_id))
            payer_a_client.post(
                f"/api/v1/settlement-plan-items/{items[0].id}/report-paid/",
                data={"description": "A"},
                content_type="application/json",
            )
            payer_b_client.post(
                f"/api/v1/settlement-plan-items/{items[1].id}/report-paid/",
                data={"description": "B"},
                content_type="application/json",
            )
            receiver_client.post(
                f"/api/v1/settlement-plan-items/{items[0].id}/confirm/"
            )
            response = receiver_client.post(
                f"/api/v1/settlement-plan-items/{items[1].id}/confirm/"
            )
        self.assertEqual(response.status_code, 200)
        plan.refresh_from_db()
        self.assertEqual(plan.status, SettlementPlanStatusChoices.COMPLETED)
        self.assertIsNotNone(plan.completed_at)
        self.assertTrue(
            SettlementPlanEventLog.objects.filter(
                event_type="PLAN_COMPLETED", settlement_plan_id=plan.id
            ).exists()
        )
        self.assertTrue(
            all(
                item.status == SettlementPlanItemStatusChoices.CONFIRMED
                for item in SettlementPlanItem.objects.filter(
                    settlement_plan_id=plan.id
                )
            )
        )
        routing_keys = [call.args[2] for call in publish_mock.call_args_list]
        self.assertIn("settlement.plan.completed", routing_keys)
