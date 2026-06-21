from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from apps.settlements.application.settlement_plan_service import SettlementPlanService
from apps.settlements.domain.models import (
    GroupBalanceSnapshot,
    SettlementPlanItemStatusChoices,
    SettlementPlanStatusChoices,
)
from apps.settlements.tests.plan_test_helpers import (
    api_client,
    auth_user,
    create_group,
    create_member,
)


class CancelSettlementPlanTests(TestCase):
    def setUp(self):
        self.owner = auth_user()
        self.group = create_group(owner_user_id=self.owner.sub)
        create_member(self.group.group_id, user_id=self.owner.sub, role="OWNER")
        self.debtor_one = create_member(self.group.group_id)
        self.debtor_two = create_member(self.group.group_id)
        self.creditor = create_member(self.group.group_id)
        self.client = api_client(self.owner)
        self.service = SettlementPlanService()

    def seed_balances(self):
        GroupBalanceSnapshot.objects.create(
            group_id=self.group.group_id,
            user_id=self.debtor_one.user_id,
            currency="IRR",
            total_paid_minor=0,
            total_share_minor=70000,
            total_settled_paid_minor=0,
            total_settled_received_minor=0,
            net_balance_minor=-70000,
        )
        GroupBalanceSnapshot.objects.create(
            group_id=self.group.group_id,
            user_id=self.debtor_two.user_id,
            currency="IRR",
            total_paid_minor=0,
            total_share_minor=30000,
            total_settled_paid_minor=0,
            total_settled_received_minor=0,
            net_balance_minor=-30000,
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

    def test_cancel_plan_cancels_pending_items_and_keeps_confirmed_items(self):
        self.seed_balances()
        with patch(
            "apps.settlements.infrastructure.rabbitmq_publisher.RabbitMQPublisher.publish",
            return_value=True,
        ):
            plan, items = self.service.generate_plan(
                self.group.group_id, self.owner.sub
            )
            self.service.activate_plan(plan.id, self.owner.sub)

        payer_client = api_client(auth_user(self.debtor_one.user_id))
        receiver_client = api_client(auth_user(self.creditor.user_id))
        with patch(
            "apps.settlements.infrastructure.rabbitmq_publisher.RabbitMQPublisher.publish",
            return_value=True,
        ):
            payer_client.post(
                reverse(
                    "report_settlement_plan_item_paid", kwargs={"item_id": items[0].id}
                ),
                data={},
                content_type="application/json",
            )
            receiver_client.post(
                reverse("confirm_settlement_plan_item", kwargs={"item_id": items[0].id})
            )
            response = self.client.post(
                reverse("cancel_settlement_plan", kwargs={"plan_id": plan.id})
            )

        self.assertEqual(response.status_code, 200)
        plan.refresh_from_db()
        self.assertEqual(plan.status, SettlementPlanStatusChoices.CANCELLED)

        items_by_id = {item.id: item for item in items}
        items_by_id[items[0].id].refresh_from_db()
        items_by_id[items[1].id].refresh_from_db()
        self.assertEqual(
            items_by_id[items[0].id].status,
            SettlementPlanItemStatusChoices.CONFIRMED,
        )
        self.assertEqual(
            items_by_id[items[1].id].status,
            SettlementPlanItemStatusChoices.CANCELLED,
        )

    def test_completed_plan_cannot_be_cancelled_again(self):
        self.seed_balances()
        with patch(
            "apps.settlements.infrastructure.rabbitmq_publisher.RabbitMQPublisher.publish",
            return_value=True,
        ):
            plan, items = self.service.generate_plan(
                self.group.group_id, self.owner.sub
            )
            self.service.activate_plan(plan.id, self.owner.sub)

        payer_one_client = api_client(auth_user(self.debtor_one.user_id))
        payer_two_client = api_client(auth_user(self.debtor_two.user_id))
        receiver_client = api_client(auth_user(self.creditor.user_id))
        with patch(
            "apps.settlements.infrastructure.rabbitmq_publisher.RabbitMQPublisher.publish",
            return_value=True,
        ):
            payer_one_client.post(
                reverse(
                    "report_settlement_plan_item_paid", kwargs={"item_id": items[0].id}
                ),
                data={},
                content_type="application/json",
            )
            receiver_client.post(
                reverse("confirm_settlement_plan_item", kwargs={"item_id": items[0].id})
            )
            payer_two_client.post(
                reverse(
                    "report_settlement_plan_item_paid", kwargs={"item_id": items[1].id}
                ),
                data={},
                content_type="application/json",
            )
            receiver_client.post(
                reverse("confirm_settlement_plan_item", kwargs={"item_id": items[1].id})
            )

        response = self.client.post(
            reverse("cancel_settlement_plan", kwargs={"plan_id": plan.id})
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "INVALID_PLAN_ITEM_ACTION")
