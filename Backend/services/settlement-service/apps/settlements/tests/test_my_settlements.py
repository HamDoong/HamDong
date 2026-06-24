from datetime import timedelta
from uuid import uuid4

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.settlements.application.settlement_service import SettlementService
from apps.settlements.domain.models import (
    ManualSettlement,
    ManualSettlementStatusChoices,
    SettlementPlan,
    SettlementPlanItem,
    SettlementPlanItemStatusChoices,
    SettlementPlanStatusChoices,
)
from apps.settlements.domain.rules import InvalidSettlementCursorError
from apps.settlements.tests.plan_test_helpers import (
    api_client,
    auth_user,
    create_group,
    create_member,
    create_user_projection,
)


class MySettlementsAPITests(TestCase):
    def setUp(self):
        self.client = api_client()
        self.me = auth_user()
        self.friend_user_id = uuid4()
        self.third_user_id = uuid4()
        self.outsider_user_id = uuid4()
        self.unrelated_user_id = uuid4()

        create_user_projection(
            identity_user_id=self.me.sub,
            art_name="me_artist",
            email="me@example.com",
        )
        create_user_projection(
            identity_user_id=self.friend_user_id,
            art_name="friend_artist",
            email="friend@example.com",
        )
        create_user_projection(
            identity_user_id=self.third_user_id,
            art_name="third_artist",
            email="third@example.com",
        )
        create_user_projection(
            identity_user_id=self.outsider_user_id,
            art_name="outsider_artist",
            email="outsider@example.com",
        )

        self.group = create_group(title="سفر شمال", owner_user_id=self.me.sub)
        create_member(
            self.group.group_id,
            user_id=self.me.sub,
            role="OWNER",
            art_name_snapshot="me_artist",
            email="me@example.com",
        )
        create_member(
            self.group.group_id,
            user_id=self.friend_user_id,
            art_name_snapshot="friend_artist",
            email="friend@example.com",
        )
        create_member(
            self.group.group_id,
            user_id=self.third_user_id,
            art_name_snapshot="third_artist",
            email="third@example.com",
        )

        self.non_member_group = create_group(
            title="Hidden Group",
            owner_user_id=self.outsider_user_id,
        )
        create_member(
            self.non_member_group.group_id,
            user_id=self.outsider_user_id,
            role="OWNER",
            art_name_snapshot="outsider_artist",
            email="outsider@example.com",
        )

        self.plan = SettlementPlan.objects.create(
            group_id=self.group.group_id,
            currency="IRR",
            status=SettlementPlanStatusChoices.ACTIVE,
            generated_by_user_id=self.me.sub,
            activated_by_user_id=self.me.sub,
            activated_at=timezone.now(),
            source_balance_calculated_at=timezone.now(),
            total_debt_minor=900000,
            transaction_count=3,
            version=1,
        )

        self.pay_item_pending = SettlementPlanItem.objects.create(
            settlement_plan_id=self.plan.id,
            group_id=self.group.group_id,
            payer_user_id=self.me.sub,
            receiver_user_id=self.friend_user_id,
            amount_minor=500000,
            currency="IRR",
            status=SettlementPlanItemStatusChoices.PENDING,
            order_index=1,
        )
        self._set_timestamps(self.pay_item_pending, minutes_ago=90)

        self.reported_item = SettlementPlanItem.objects.create(
            settlement_plan_id=self.plan.id,
            group_id=self.group.group_id,
            payer_user_id=self.friend_user_id,
            receiver_user_id=self.me.sub,
            amount_minor=220000,
            currency="IRR",
            status=SettlementPlanItemStatusChoices.REPORTED,
            order_index=2,
        )
        self._set_timestamps(self.reported_item, minutes_ago=80)

        self.unrelated_same_group_item = SettlementPlanItem.objects.create(
            settlement_plan_id=self.plan.id,
            group_id=self.group.group_id,
            payer_user_id=self.friend_user_id,
            receiver_user_id=self.unrelated_user_id,
            amount_minor=123000,
            currency="IRR",
            status=SettlementPlanItemStatusChoices.PENDING,
            order_index=3,
        )
        self._set_timestamps(self.unrelated_same_group_item, minutes_ago=70)

        self.linked_manual_settlement = ManualSettlement.objects.create(
            group_id=self.group.group_id,
            payer_user_id=self.friend_user_id,
            receiver_user_id=self.me.sub,
            amount_minor=220000,
            currency="IRR",
            status=ManualSettlementStatusChoices.PENDING_CONFIRMATION,
            created_by_user_id=self.friend_user_id,
        )
        self._set_timestamps(self.linked_manual_settlement, minutes_ago=80)
        SettlementPlanItem.objects.filter(id=self.reported_item.id).update(
            manual_settlement_id=self.linked_manual_settlement.id
        )
        self.reported_item.refresh_from_db()

        self.receive_manual = ManualSettlement.objects.create(
            group_id=self.group.group_id,
            payer_user_id=self.friend_user_id,
            receiver_user_id=self.me.sub,
            amount_minor=100000,
            currency="IRR",
            status=ManualSettlementStatusChoices.PENDING_CONFIRMATION,
            created_by_user_id=self.friend_user_id,
        )
        self._set_timestamps(self.receive_manual, minutes_ago=60)

        self.pay_manual = ManualSettlement.objects.create(
            group_id=self.group.group_id,
            payer_user_id=self.me.sub,
            receiver_user_id=self.friend_user_id,
            amount_minor=90000,
            currency="IRR",
            status=ManualSettlementStatusChoices.PENDING_CONFIRMATION,
            created_by_user_id=self.me.sub,
        )
        self._set_timestamps(self.pay_manual, minutes_ago=50)

        self.hidden_non_member_settlement = ManualSettlement.objects.create(
            group_id=self.non_member_group.group_id,
            payer_user_id=self.me.sub,
            receiver_user_id=self.outsider_user_id,
            amount_minor=330000,
            currency="IRR",
            status=ManualSettlementStatusChoices.PENDING_CONFIRMATION,
            created_by_user_id=self.me.sub,
        )
        self._set_timestamps(self.hidden_non_member_settlement, minutes_ago=40)

    def _set_timestamps(self, instance, *, minutes_ago):
        timestamp = timezone.now() - timedelta(minutes=minutes_ago)
        type(instance).objects.filter(id=instance.id).update(
            created_at=timestamp,
            updated_at=timestamp,
        )
        instance.refresh_from_db()

    def test_requires_authentication(self):
        response = self.client.get(reverse("my_settlements"))
        self.assertEqual(response.status_code, 401)

    def test_lists_only_authenticated_user_related_settlements(self):
        client = api_client(self.me)
        response = client.get(reverse("my_settlements"))
        self.assertEqual(response.status_code, 200)
        payload = response.json()

        returned_ids = {item["id"] for item in payload["results"]}
        self.assertIn(str(self.pay_item_pending.id), returned_ids)
        self.assertIn(str(self.reported_item.id), returned_ids)
        self.assertIn(str(self.receive_manual.id), returned_ids)
        self.assertIn(str(self.pay_manual.id), returned_ids)
        self.assertNotIn(str(self.linked_manual_settlement.id), returned_ids)
        self.assertNotIn(str(self.unrelated_same_group_item.id), returned_ids)
        self.assertNotIn(str(self.hidden_non_member_settlement.id), returned_ids)

        by_id = {item["id"]: item for item in payload["results"]}
        pay_item = by_id[str(self.pay_item_pending.id)]
        self.assertEqual(pay_item["source_type"], "SETTLEMENT_PLAN_ITEM")
        self.assertEqual(pay_item["group"]["title"], "سفر شمال")
        self.assertEqual(pay_item["counterparty"]["art_name"], "friend_artist")
        self.assertEqual(pay_item["direction"], "PAY")
        self.assertEqual(pay_item["action_required"], "PAY")
        self.assertEqual(pay_item["allowed_actions"], ["REPORT_PAID"])

        receive_item = by_id[str(self.reported_item.id)]
        self.assertEqual(receive_item["direction"], "RECEIVE")
        self.assertEqual(receive_item["status"], SettlementPlanItemStatusChoices.REPORTED)
        self.assertEqual(receive_item["action_required"], "CONFIRM")
        self.assertEqual(receive_item["allowed_actions"], ["CONFIRM", "REJECT"])

        receive_manual = by_id[str(self.receive_manual.id)]
        self.assertEqual(receive_manual["source_type"], "MANUAL_SETTLEMENT")
        self.assertEqual(receive_manual["direction"], "RECEIVE")
        self.assertEqual(
            receive_manual["status"],
            ManualSettlementStatusChoices.PENDING_CONFIRMATION,
        )
        self.assertEqual(receive_manual["action_required"], "CONFIRM")

        pay_manual = by_id[str(self.pay_manual.id)]
        self.assertEqual(pay_manual["direction"], "PAY")
        self.assertIsNone(pay_manual["action_required"])
        self.assertEqual(pay_manual["allowed_actions"], ["CANCEL"])

    def test_unrelated_group_member_cannot_see_other_members_settlements(self):
        client = api_client(auth_user(self.third_user_id))
        response = client.get(reverse("my_settlements"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["results"], [])

    def test_direction_filters_work_for_pay_and_receive(self):
        client = api_client(self.me)

        pay_response = client.get(reverse("my_settlements"), {"direction": "PAY"})
        self.assertEqual(pay_response.status_code, 200)
        pay_ids = {item["id"] for item in pay_response.json()["results"]}
        self.assertEqual(
            pay_ids,
            {str(self.pay_item_pending.id), str(self.pay_manual.id)},
        )

        receive_response = client.get(
            reverse("my_settlements"),
            {"direction": "RECEIVE"},
        )
        self.assertEqual(receive_response.status_code, 200)
        receive_ids = {item["id"] for item in receive_response.json()["results"]}
        self.assertEqual(
            receive_ids,
            {str(self.reported_item.id), str(self.receive_manual.id)},
        )

    def test_status_and_action_required_filters_work(self):
        client = api_client(self.me)

        pending_response = client.get(reverse("my_settlements"), {"status": "PENDING"})
        self.assertEqual(pending_response.status_code, 200)
        pending_ids = {item["id"] for item in pending_response.json()["results"]}
        self.assertEqual(pending_ids, {str(self.pay_item_pending.id)})

        pending_confirmation_response = client.get(
            reverse("my_settlements"),
            {"status": "PENDING_CONFIRMATION"},
        )
        self.assertEqual(pending_confirmation_response.status_code, 200)
        pending_confirmation_ids = {
            item["id"] for item in pending_confirmation_response.json()["results"]
        }
        self.assertEqual(
            pending_confirmation_ids,
            {str(self.receive_manual.id), str(self.pay_manual.id)},
        )

        action_required_response = client.get(
            reverse("my_settlements"),
            {"action_required": "true"},
        )
        self.assertEqual(action_required_response.status_code, 200)
        action_required_ids = {
            item["id"] for item in action_required_response.json()["results"]
        }
        self.assertEqual(
            action_required_ids,
            {
                str(self.pay_item_pending.id),
                str(self.reported_item.id),
                str(self.receive_manual.id),
            },
        )

    def test_group_filter_requires_active_membership(self):
        client = api_client(self.me)

        visible_group_response = client.get(
            reverse("my_settlements"),
            {"group_id": str(self.group.group_id)},
        )
        self.assertEqual(visible_group_response.status_code, 200)
        self.assertGreaterEqual(len(visible_group_response.json()["results"]), 1)

        hidden_group_response = client.get(
            reverse("my_settlements"),
            {"group_id": str(self.non_member_group.group_id)},
        )
        self.assertEqual(hidden_group_response.status_code, 200)
        self.assertEqual(hidden_group_response.json()["results"], [])

    def test_pagination_uses_cursor_contract(self):
        client = api_client(self.me)

        first_page = client.get(reverse("my_settlements"), {"page_size": 2})
        self.assertEqual(first_page.status_code, 200)
        first_payload = first_page.json()
        self.assertEqual(len(first_payload["results"]), 2)
        self.assertIsNotNone(first_payload["next_cursor"])

        second_page = client.get(
            reverse("my_settlements"),
            {"page_size": 2, "cursor": first_payload["next_cursor"]},
        )
        self.assertEqual(second_page.status_code, 200)
        second_payload = second_page.json()
        self.assertGreaterEqual(len(second_payload["results"]), 1)

        first_ids = {item["id"] for item in first_payload["results"]}
        second_ids = {item["id"] for item in second_payload["results"]}
        self.assertTrue(first_ids.isdisjoint(second_ids))

    def test_invalid_query_values_return_400(self):
        client = api_client(self.me)

        invalid_direction = client.get(
            reverse("my_settlements"),
            {"direction": "SIDEWAYS"},
        )
        self.assertEqual(invalid_direction.status_code, 400)

        invalid_cursor = client.get(
            reverse("my_settlements"),
            {"cursor": "not-a-valid-cursor"},
        )
        self.assertEqual(invalid_cursor.status_code, 400)
        self.assertEqual(invalid_cursor.json()["error"]["code"], "INVALID_CURSOR")

    def test_schema_includes_settlements_me_endpoint(self):
        client = api_client(self.me)
        response = client.get(reverse("schema"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("/api/v1/settlements/me/", response.content.decode("utf-8"))


class SettlementServiceListMySettlementsTests(TestCase):
    def test_invalid_cursor_raises_domain_error(self):
        service = SettlementService()
        with self.assertRaises(InvalidSettlementCursorError):
            service.list_my_settlements(uuid4(), filters={"cursor": "bad"})
