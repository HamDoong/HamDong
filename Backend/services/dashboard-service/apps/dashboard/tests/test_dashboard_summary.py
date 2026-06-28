from __future__ import annotations

from datetime import timedelta
from unittest.mock import patch
from uuid import uuid4

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.dashboard.tests.helpers import api_client, auth_user


class FakeSummaryClient:
    def __init__(self, settlements=None, groups=None, unread_counts=None, notifications=None):
        self._settlements = settlements or []
        self._groups = groups or []
        self._unread_counts = unread_counts or {"unread_count": 0, "important_unread_count": 0}
        self._notifications = notifications or []

    def list_all_settlements(self, token, action_required=None):
        if action_required is True:
            return [item for item in self._settlements if item.get("action_required") or (item.get("status") == "REJECTED" and item.get("direction") == "PAY")]
        return list(self._settlements)

    def list_my_groups(self, token):
        return list(self._groups)

    def get_unread_counts(self, token):
        return dict(self._unread_counts)

    def list_important_notifications(self, token):
        return list(self._notifications)


class DashboardSummaryTests(TestCase):
    def setUp(self):
        self.me = auth_user(sub=uuid4())
        self.client = api_client(self.me)

    def _summary_url(self):
        return reverse("dashboard_summary")

    def _settlement(self, *, direction, status, amount_minor, currency="IRR", action_required=None):
        item_id = uuid4()
        return {
            "id": str(item_id),
            "source_type": "SETTLEMENT_PLAN_ITEM",
            "source_id": str(item_id),
            "group": {"id": str(uuid4()), "title": "سفر شمال"},
            "counterparty": {"user_id": str(uuid4()), "art_name": "reza_artist"},
            "direction": direction,
            "amount_minor": amount_minor,
            "currency": currency,
            "status": status,
            "action_required": action_required,
            "allowed_actions": ["REPORT_PAID"],
            "created_at": timezone.now().isoformat(),
            "updated_at": timezone.now().isoformat(),
        }

    def test_requires_authentication(self):
        self.client.logout()
        response = self.client.get(self._summary_url())
        self.assertEqual(response.status_code, 401)

    @patch("apps.dashboard.application.dashboard_service.InternalAPIClient")
    def test_summary_aggregates_only_pending_settlements(self, client_cls):
        client_cls.return_value = FakeSummaryClient(
            settlements=[
                self._settlement(direction="RECEIVE", status="PENDING", amount_minor=500000, action_required="CONFIRM"),
                self._settlement(direction="PAY", status="PENDING", amount_minor=120000, action_required="PAY"),
                self._settlement(direction="PAY", status="CONFIRMED", amount_minor=90000),
                self._settlement(direction="RECEIVE", status="REPORTED", amount_minor=45000, currency="USD"),
            ],
            groups=[
                {"id": str(uuid4()), "status": "ACTIVE"},
                {"id": str(uuid4()), "status": "ARCHIVED"},
                {"id": str(uuid4()), "status": "ACTIVE"},
            ],
            unread_counts={"unread_count": 4, "important_unread_count": 1},
            notifications=[
                {
                    "id": str(uuid4()),
                    "title": "Important",
                    "body": "Check it",
                    "priority": "HIGH",
                    "created_at": timezone.now().isoformat(),
                }
            ],
        )

        response = self.client.get(self._summary_url())
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["active_groups_count"], 2)
        self.assertEqual(data["pending_settlements_count"], 3)
        self.assertEqual(data["important_unread_notifications_count"], 1)
        self.assertEqual(data["action_items_count"], 3)
        financials = {row["currency"]: row for row in data["financials"]}
        self.assertEqual(financials["IRR"]["total_receivable_minor"], 500000)
        self.assertEqual(financials["IRR"]["total_payable_minor"], 120000)
        self.assertEqual(financials["IRR"]["net_balance_minor"], 380000)
        self.assertEqual(financials["USD"]["total_receivable_minor"], 45000)

    @patch("apps.dashboard.application.dashboard_service.InternalAPIClient")
    def test_summary_supports_currency_filter_and_zero_defaults(self, client_cls):
        client_cls.return_value = FakeSummaryClient()
        response = self.client.get(self._summary_url(), {"currency": "IRR"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["financials"], [
            {
                "currency": "IRR",
                "total_receivable_minor": 0,
                "total_payable_minor": 0,
                "net_balance_minor": 0,
            }
        ])
        self.assertEqual(data["active_groups_count"], 0)
        self.assertEqual(data["pending_settlements_count"], 0)

    def test_swagger_contains_dashboard_summary_path(self):
        response = self.client.get("/api/schema/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("/api/v1/dashboard/summary/", response.content.decode("utf-8"))
