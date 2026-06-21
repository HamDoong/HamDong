from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone
from django.urls import reverse

from apps.settlements.application.settlement_plan_service import SettlementPlanService
from apps.settlements.domain.models import (
    GroupBalanceSnapshot,
    SettlementPlanItem,
    SettlementPlanStatusChoices,
)
from apps.settlements.tests.plan_test_helpers import (
    api_client,
    auth_user,
    create_group,
    create_member,
)


class ActivateSettlementPlanTests(TestCase):
    def setUp(self):
        self.owner = auth_user()
        self.group = create_group(owner_user_id=self.owner.sub)
        create_member(self.group.group_id, user_id=self.owner.sub, role="OWNER")
        self.debtor = create_member(self.group.group_id)
        self.creditor = create_member(self.group.group_id)
        self.client = api_client(self.owner)
        self.service = SettlementPlanService()

    def seed_balances(self, debt=-100000, credit=100000):
        GroupBalanceSnapshot.objects.create(
            group_id=self.group.group_id,
            user_id=self.debtor.user_id,
            currency="IRR",
            total_paid_minor=0,
            total_share_minor=debt * -1,
            total_settled_paid_minor=0,
            total_settled_received_minor=0,
            net_balance_minor=debt,
        )
        GroupBalanceSnapshot.objects.create(
            group_id=self.group.group_id,
            user_id=self.creditor.user_id,
            currency="IRR",
            total_paid_minor=credit,
            total_share_minor=0,
            total_settled_paid_minor=0,
            total_settled_received_minor=0,
            net_balance_minor=credit,
        )

    def test_only_owner_or_admin_can_activate_or_cancel_plan(self):
        self.seed_balances()
        with patch(
            "apps.settlements.infrastructure.rabbitmq_publisher.RabbitMQPublisher.publish",
            return_value=True,
        ):
            plan, _ = self.service.generate_plan(self.group.group_id, self.owner.sub)
        member_client = api_client(auth_user(self.debtor.user_id))
        response = member_client.post(
            reverse("activate_settlement_plan", kwargs={"plan_id": plan.id})
        )
        self.assertEqual(response.status_code, 403)
        response = member_client.post(
            reverse("cancel_settlement_plan", kwargs={"plan_id": plan.id})
        )
        self.assertEqual(response.status_code, 403)

    def test_activate_plan_success(self):
        self.seed_balances()
        with patch(
            "apps.settlements.infrastructure.rabbitmq_publisher.RabbitMQPublisher.publish",
            return_value=True,
        ):
            plan, _ = self.service.generate_plan(self.group.group_id, self.owner.sub)
            response = self.client.post(
                reverse("activate_settlement_plan", kwargs={"plan_id": plan.id})
            )
        self.assertEqual(response.status_code, 200)
        plan.refresh_from_db()
        self.assertEqual(plan.status, SettlementPlanStatusChoices.ACTIVE)
        self.assertIsNotNone(plan.activated_by_user_id)

    def test_cannot_activate_expired_plan(self):
        self.seed_balances()
        with patch(
            "apps.settlements.infrastructure.rabbitmq_publisher.RabbitMQPublisher.publish",
            return_value=True,
        ):
            plan, _ = self.service.generate_plan(self.group.group_id, self.owner.sub)
        GroupBalanceSnapshot.objects.filter(
            group_id=self.group.group_id, user_id=self.debtor.user_id
        ).update(calculated_at=timezone.now() + timedelta(days=1))
        response = self.client.post(
            reverse("activate_settlement_plan", kwargs={"plan_id": plan.id})
        )
        self.assertEqual(response.status_code, 409)
        plan.refresh_from_db()
        self.assertEqual(plan.status, SettlementPlanStatusChoices.EXPIRED)

    def test_cannot_have_two_active_plans_for_same_group(self):
        self.seed_balances()
        with patch(
            "apps.settlements.infrastructure.rabbitmq_publisher.RabbitMQPublisher.publish",
            return_value=True,
        ):
            first_plan, _ = self.service.generate_plan(
                self.group.group_id, self.owner.sub
            )
            self.service.activate_plan(first_plan.id, self.owner.sub)
            second_plan, _ = self.service.generate_plan(
                self.group.group_id, self.owner.sub
            )
            response = self.client.post(
                reverse("activate_settlement_plan", kwargs={"plan_id": second_plan.id})
            )
        self.assertEqual(response.status_code, 409)

    def test_cancel_plan_marks_cancelled(self):
        self.seed_balances()
        with patch(
            "apps.settlements.infrastructure.rabbitmq_publisher.RabbitMQPublisher.publish",
            return_value=True,
        ):
            plan, _ = self.service.generate_plan(self.group.group_id, self.owner.sub)
            response = self.client.post(
                reverse("cancel_settlement_plan", kwargs={"plan_id": plan.id})
            )
        self.assertEqual(response.status_code, 200)
        plan.refresh_from_db()
        self.assertEqual(plan.status, SettlementPlanStatusChoices.CANCELLED)

    def test_cancel_active_plan_cancels_pending_items(self):
        self.seed_balances()
        with patch(
            "apps.settlements.infrastructure.rabbitmq_publisher.RabbitMQPublisher.publish",
            return_value=True,
        ):
            plan, items = self.service.generate_plan(
                self.group.group_id, self.owner.sub
            )
            self.service.activate_plan(plan.id, self.owner.sub)
            self.service.cancel_plan(plan.id, self.owner.sub)
        plan.refresh_from_db()
        self.assertEqual(plan.status, SettlementPlanStatusChoices.CANCELLED)
        refreshed_items = [SettlementPlanItem.objects.get(id=item.id) for item in items]
        self.assertTrue(all(item.status == "CANCELLED" for item in refreshed_items))
