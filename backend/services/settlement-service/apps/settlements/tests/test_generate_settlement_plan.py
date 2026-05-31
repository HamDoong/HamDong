from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from apps.settlements.application.settlement_plan_service import SettlementPlanService
from apps.settlements.domain.models import (
    GroupBalanceSnapshot,
    SettlementPlan,
    SettlementPlanItem,
)
from apps.settlements.tests.plan_test_helpers import (
    api_client,
    auth_user,
    create_group,
    create_member,
    create_user_projection,
)


class GenerateSettlementPlanTests(TestCase):
    def setUp(self):
        self.owner = auth_user()
        self.group = create_group(owner_user_id=self.owner.sub)
        create_member(
            self.group.group_id,
            user_id=self.owner.sub,
            role="OWNER",
            display_name_snapshot="Owner",
        )
        self.creditor = create_member(
            self.group.group_id, display_name_snapshot="Creditor"
        )
        self.debtor = create_member(self.group.group_id, display_name_snapshot="Debtor")
        create_user_projection(self.owner.sub, display_name="Owner")
        create_user_projection(self.creditor.user_id, display_name="Creditor")
        create_user_projection(self.debtor.user_id, display_name="Debtor")
        self.client = api_client(self.owner)

    def seed_balances(self, balances):
        for user_id, net_balance_minor in balances:
            GroupBalanceSnapshot.objects.create(
                group_id=self.group.group_id,
                user_id=user_id,
                currency="IRR",
                total_paid_minor=max(net_balance_minor, 0),
                total_share_minor=max(-net_balance_minor, 0),
                total_settled_paid_minor=0,
                total_settled_received_minor=0,
                net_balance_minor=net_balance_minor,
            )

    def test_generate_plan_with_one_debtor_and_one_creditor(self):
        self.seed_balances(
            [(self.debtor.user_id, -100000), (self.creditor.user_id, 100000)]
        )
        with patch(
            "apps.settlements.infrastructure.rabbitmq_publisher.RabbitMQPublisher.publish",
            return_value=True,
        ):
            response = self.client.post(
                reverse(
                    "generate_settlement_plan", kwargs={"group_id": self.group.group_id}
                ),
                data={},
                content_type="application/json",
            )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["transaction_count"], 1)
        self.assertEqual(response.json()["total_debt_minor"], 100000)
        self.assertEqual(response.json()["items"][0]["amount_minor"], 100000)
        self.assertEqual(SettlementPlan.objects.count(), 1)
        self.assertEqual(SettlementPlanItem.objects.count(), 1)

    def test_generate_plan_with_multiple_debtors_one_creditor(self):
        a = create_member(self.group.group_id, display_name_snapshot="A")
        b = create_member(self.group.group_id, display_name_snapshot="B")
        c = create_member(self.group.group_id, display_name_snapshot="C")
        self.seed_balances(
            [(a.user_id, -70000), (b.user_id, -50000), (c.user_id, 120000)]
        )
        with patch(
            "apps.settlements.infrastructure.rabbitmq_publisher.RabbitMQPublisher.publish",
            return_value=True,
        ):
            response = self.client.post(
                reverse(
                    "generate_settlement_plan", kwargs={"group_id": self.group.group_id}
                ),
                data={},
                content_type="application/json",
            )
        self.assertEqual(
            [
                (item["payer_user_id"], item["receiver_user_id"], item["amount_minor"])
                for item in response.json()["items"]
            ],
            [
                (str(a.user_id), str(c.user_id), 70000),
                (str(b.user_id), str(c.user_id), 50000),
            ],
        )

    def test_generate_empty_plan_when_all_balances_zero(self):
        self.seed_balances([(self.debtor.user_id, 0), (self.creditor.user_id, 0)])
        with patch(
            "apps.settlements.infrastructure.rabbitmq_publisher.RabbitMQPublisher.publish",
            return_value=True,
        ):
            response = self.client.post(
                reverse(
                    "generate_settlement_plan", kwargs={"group_id": self.group.group_id}
                ),
                data={},
                content_type="application/json",
            )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["items"], [])
        self.assertEqual(response.json()["transaction_count"], 0)

    def test_only_owner_or_admin_can_generate_plan(self):
        self.seed_balances(
            [(self.debtor.user_id, -100000), (self.creditor.user_id, 100000)]
        )
        member_client = api_client(auth_user(self.debtor.user_id))
        response = member_client.post(
            reverse(
                "generate_settlement_plan", kwargs={"group_id": self.group.group_id}
            ),
            data={},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

    def test_active_member_can_view_latest_plan_and_non_member_cannot(self):
        self.seed_balances(
            [(self.debtor.user_id, -100000), (self.creditor.user_id, 100000)]
        )
        with patch(
            "apps.settlements.infrastructure.rabbitmq_publisher.RabbitMQPublisher.publish",
            return_value=True,
        ):
            SettlementPlanService().generate_plan(self.group.group_id, self.owner.sub)
        self.client = api_client(auth_user(self.debtor.user_id))
        response = self.client.get(
            reverse("latest_settlement_plan", kwargs={"group_id": self.group.group_id})
        )
        self.assertEqual(response.status_code, 200)
        non_member_client = api_client(auth_user())
        response = non_member_client.get(
            reverse("latest_settlement_plan", kwargs={"group_id": self.group.group_id})
        )
        self.assertEqual(response.status_code, 403)

    def test_latest_plan_prefers_active_then_draft(self):
        self.seed_balances(
            [(self.debtor.user_id, -100000), (self.creditor.user_id, 100000)]
        )
        with patch(
            "apps.settlements.infrastructure.rabbitmq_publisher.RabbitMQPublisher.publish",
            return_value=True,
        ):
            plan, items = SettlementPlanService().generate_plan(
                self.group.group_id, self.owner.sub
            )
        response = self.client.get(
            reverse("latest_settlement_plan", kwargs={"group_id": self.group.group_id})
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["id"], str(plan.id))
        self.assertEqual(response.json()["items"][0]["id"], str(items[0].id))

    def test_generated_plan_total_equals_total_positive_balance(self):
        self.seed_balances(
            [
                (self.debtor.user_id, -100000),
                (self.creditor.user_id, 40000),
                (create_member(self.group.group_id).user_id, 60000),
            ]
        )
        with patch(
            "apps.settlements.infrastructure.rabbitmq_publisher.RabbitMQPublisher.publish",
            return_value=True,
        ):
            response = self.client.post(
                reverse(
                    "generate_settlement_plan", kwargs={"group_id": self.group.group_id}
                ),
                data={},
                content_type="application/json",
            )
        self.assertEqual(
            response.json()["total_debt_minor"],
            sum(item["amount_minor"] for item in response.json()["items"]),
        )

    def test_generated_plan_never_uses_zero_amount_or_self_transfer(self):
        self.seed_balances(
            [(self.debtor.user_id, -100000), (self.creditor.user_id, 100000)]
        )
        with patch(
            "apps.settlements.infrastructure.rabbitmq_publisher.RabbitMQPublisher.publish",
            return_value=True,
        ):
            response = self.client.post(
                reverse(
                    "generate_settlement_plan", kwargs={"group_id": self.group.group_id}
                ),
                data={},
                content_type="application/json",
            )
        item = response.json()["items"][0]
        self.assertGreater(item["amount_minor"], 0)
        self.assertNotEqual(item["payer_user_id"], item["receiver_user_id"])

    def test_generated_plan_output_is_deterministic(self):
        balances = [(self.debtor.user_id, -60000), (self.creditor.user_id, 60000)]
        self.seed_balances(balances)
        with patch(
            "apps.settlements.infrastructure.rabbitmq_publisher.RabbitMQPublisher.publish",
            return_value=True,
        ):
            first = self.client.post(
                reverse(
                    "generate_settlement_plan", kwargs={"group_id": self.group.group_id}
                ),
                data={},
                content_type="application/json",
            ).json()
            SettlementPlan.objects.all().delete()
            SettlementPlanItem.objects.all().delete()
            second = self.client.post(
                reverse(
                    "generate_settlement_plan", kwargs={"group_id": self.group.group_id}
                ),
                data={},
                content_type="application/json",
            ).json()
        self.assertEqual(
            [
                {
                    "payer_user_id": item["payer_user_id"],
                    "receiver_user_id": item["receiver_user_id"],
                    "amount_minor": item["amount_minor"],
                    "status": item["status"],
                    "order_index": item["order_index"],
                }
                for item in first["items"]
            ],
            [
                {
                    "payer_user_id": item["payer_user_id"],
                    "receiver_user_id": item["receiver_user_id"],
                    "amount_minor": item["amount_minor"],
                    "status": item["status"],
                    "order_index": item["order_index"],
                }
                for item in second["items"]
            ],
        )
