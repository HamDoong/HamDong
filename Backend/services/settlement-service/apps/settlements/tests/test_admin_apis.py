
from __future__ import annotations

from datetime import timedelta
from types import SimpleNamespace
from uuid import uuid4

from django.test import TestCase, override_settings
from django.utils import timezone

from apps.settlements.domain.models import InboxMessage, ManualSettlement, OutboxMessage, SettlementPlanItem
from apps.settlements.tests.plan_test_helpers import api_client


def auth_user(role="USER"):
    user_id = uuid4()
    return SimpleNamespace(sub=user_id, id=str(user_id), role=role, is_authenticated=True, email=f"{user_id}@example.com")


@override_settings(EXPOSE_API_DOCS=True)
class AdminSettlementApiTests(TestCase):
    def setUp(self):
        self.client = api_client()
        self.admin = auth_user(role="ADMIN")
        self.user = auth_user(role="USER")
        self.group_id = uuid4()
        self.payer_id = uuid4()
        self.payee_id = uuid4()
        self.plan_item = SettlementPlanItem.objects.create(
            settlement_plan_id=uuid4(),
            group_id=self.group_id,
            payer_user_id=self.payer_id,
            receiver_user_id=self.payee_id,
            amount_minor=500000,
            currency="IRR",
            status="PENDING",
            order_index=1,
        )
        self.manual = ManualSettlement.objects.create(
            group_id=self.group_id,
            payer_user_id=self.payer_id,
            receiver_user_id=self.payee_id,
            amount_minor=200000,
            currency="IRR",
            status="PENDING_CONFIRMATION",
            created_by_user_id=self.payer_id,
        )
        self.outbox = OutboxMessage.objects.create(
            aggregate_type="Reminder",
            aggregate_id=uuid4(),
            event_type="PasswordResetCompleted",
            routing_key="settlement.test",
            payload={"password": "hidden", "safe": True},
            status="PENDING",
        )
        self.failed = InboxMessage.objects.create(
            event_id=uuid4(),
            event_type="SomethingFailed",
            source_service="wallet-service",
            routing_key="wallet.failed",
            payload={"reset_token": "secret", "safe": True},
            status="FAILED",
            error_message="boom",
        )
        now = timezone.now()
        SettlementPlanItem.objects.filter(id=self.plan_item.id).update(created_at=now - timedelta(days=2), updated_at=now - timedelta(days=2))
        ManualSettlement.objects.filter(id=self.manual.id).update(created_at=now - timedelta(days=1), updated_at=now - timedelta(days=1))
        self.plan_item.refresh_from_db()
        self.manual.refresh_from_db()

    def test_missing_token_returns_401(self):
        response = self.client.get("/api/v1/admin/settlements/")
        self.assertEqual(response.status_code, 401)

    def test_normal_user_gets_403(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/v1/admin/settlements/")
        self.assertEqual(response.status_code, 403)

    def test_admin_can_list_settlements_and_filter(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(f"/api/v1/admin/settlements/?group_id={self.group_id}&payer_user_id={self.payer_id}")
        self.assertEqual(response.status_code, 200)
        ids = {row["id"] for row in response.json()["results"]}
        self.assertIn(str(self.plan_item.id), ids)
        self.assertIn(str(self.manual.id), ids)

    def test_admin_can_list_outbox_and_failed_events_with_masking(self):
        self.client.force_authenticate(user=self.admin)
        outbox_response = self.client.get("/api/v1/admin/outbox/")
        self.assertEqual(outbox_response.status_code, 200)
        self.assertEqual(outbox_response.json()["results"][0]["payload"]["password"], "***")

        failed_response = self.client.get("/api/v1/admin/failed-events/")
        self.assertEqual(failed_response.status_code, 200)
        self.assertEqual(failed_response.json()["results"][0]["payload"]["reset_token"], "***")

    def test_schema_contains_admin_paths(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.get("/api/schema/?format=json")
        self.assertEqual(response.status_code, 200)
        paths = response.json()["paths"]
        self.assertIn("/api/v1/admin/settlements/", paths)
        self.assertIn("/api/v1/admin/outbox/", paths)
        self.assertIn("/api/v1/admin/failed-events/", paths)
