from __future__ import annotations

from unittest.mock import patch
from uuid import uuid4

from django.test import TestCase
from django.urls import reverse
from datetime import timedelta

from django.utils import timezone

from apps.dashboard.tests.helpers import api_client, auth_user


class FakeActionClient:
    def __init__(self, settlements=None, notifications=None, invitations=None):
        self._settlements = settlements or []
        self._notifications = notifications or []
        self._invitations = invitations or []

    def list_all_settlements(self, token, action_required=None):
        return list(self._settlements)

    def list_group_invitations(self, token):
        return list(self._invitations)

    def list_important_notifications(self, token):
        return list(self._notifications)

    def list_my_groups(self, token):
        return []

    def get_unread_counts(self, token):
        return {"unread_count": 0, "important_unread_count": len(self._notifications)}


class DashboardActionItemsTests(TestCase):
    def setUp(self):
        self.me = auth_user(sub=uuid4())
        self.client = api_client(self.me)

    def _url(self):
        return reverse("dashboard_action_items")


    def _invite(self, *, group_id=None, created_at=None, invite_id=None):
        return {
            "id": str(invite_id or uuid4()),
            "group": {"id": str(group_id or uuid4()), "title": "سفر شمال"},
            "invited_by": {"user_id": str(uuid4()), "art_name": "ali_artist"},
            "status": "PENDING",
            "expires_at": timezone.now().isoformat(),
            "created_at": created_at or timezone.now().isoformat(),
        }

    def _settlement(self, *, direction="PAY", status="PENDING", action_required="PAY", group_id=None, created_at=None):
        source_id = uuid4()
        return {
            "id": str(source_id),
            "source_type": "SETTLEMENT_PLAN_ITEM",
            "source_id": str(source_id),
            "group": {"id": str(group_id or uuid4()), "title": "سفر شمال"},
            "counterparty": {"user_id": str(uuid4()), "art_name": "reza_artist"},
            "direction": direction,
            "amount_minor": 500000,
            "currency": "IRR",
            "status": status,
            "action_required": action_required,
            "allowed_actions": ["REPORT_PAID"],
            "created_at": created_at or timezone.now().isoformat(),
            "updated_at": created_at or timezone.now().isoformat(),
        }

    @patch("apps.dashboard.application.dashboard_service.InternalAPIClient")
    def test_action_items_include_settlement_and_notification_actions(self, client_cls):
        earlier = (timezone.now() - timedelta(hours=1)).isoformat()
        latest = timezone.now().isoformat()
        group_id = uuid4()
        client_cls.return_value = FakeActionClient(
            settlements=[
                self._settlement(direction="PAY", status="PENDING", action_required="PAY", group_id=group_id, created_at=latest),
                self._settlement(direction="RECEIVE", status="REPORTED", action_required="CONFIRM", group_id=group_id, created_at=earlier),
                self._settlement(direction="PAY", status="REJECTED", action_required=None, group_id=group_id, created_at=earlier),
            ],
            invitations=[self._invite(group_id=group_id, created_at=latest)],
            notifications=[
                {
                    "id": str(uuid4()),
                    "title": "Important",
                    "body": "Please review",
                    "priority": "URGENT",
                    "created_at": earlier,
                }
            ],
        )

        response = self.client.get(self._url())
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data["results"]), 5)
        types = {item["type"] for item in data["results"]}
        self.assertIn("PAY_DEBT", types)
        self.assertIn("CONFIRM_RECEIVED_PAYMENT", types)
        self.assertIn("REVIEW_REJECTED_PAYMENT", types)
        self.assertIn("VIEW_IMPORTANT_NOTIFICATION", types)
        self.assertIn("RESPOND_TO_GROUP_INVITATION", types)

    @patch("apps.dashboard.application.dashboard_service.InternalAPIClient")
    def test_action_items_support_filters_and_pagination(self, client_cls):
        group_a = uuid4()
        group_b = uuid4()
        t1 = timezone.now().isoformat()
        t2 = (timezone.now() - timedelta(minutes=2)).isoformat()
        t3 = (timezone.now() - timedelta(minutes=3)).isoformat()
        client_cls.return_value = FakeActionClient(
            settlements=[
                self._settlement(direction="PAY", status="PENDING", action_required="PAY", group_id=group_a, created_at=t1),
                self._settlement(direction="RECEIVE", status="REPORTED", action_required="CONFIRM", group_id=group_a, created_at=t2),
                self._settlement(direction="PAY", status="REJECTED", action_required=None, group_id=group_b, created_at=t3),
            ],
        )

        response = self.client.get(self._url(), {"group_id": str(group_a), "page_size": 1})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data["results"]), 1)
        self.assertIsNotNone(data["next_cursor"])

        response_next = self.client.get(self._url(), {"group_id": str(group_a), "page_size": 1, "cursor": data["next_cursor"]})
        self.assertEqual(response_next.status_code, 200)
        self.assertEqual(len(response_next.json()["results"]), 1)

        response_filtered = self.client.get(self._url(), {"type": "CONFIRM_RECEIVED_PAYMENT"})
        self.assertEqual(response_filtered.status_code, 200)
        self.assertEqual(response_filtered.json()["results"][0]["type"], "CONFIRM_RECEIVED_PAYMENT")


    @patch("apps.dashboard.application.dashboard_service.InternalAPIClient")
    def test_direct_invitation_action_exposes_accept_and_reject(self, client_cls):
        group_id = uuid4()
        client_cls.return_value = FakeActionClient(invitations=[self._invite(group_id=group_id)])

        response = self.client.get(self._url(), {"type": "RESPOND_TO_GROUP_INVITATION"})
        self.assertEqual(response.status_code, 200)
        item = response.json()["results"][0]
        self.assertEqual(item["type"], "RESPOND_TO_GROUP_INVITATION")
        paths = {action["path"] for action in item["allowed_actions"]}
        self.assertEqual(paths, {
            f"/api/v1/group-invitations/{item['source']['id']}/accept/",
            f"/api/v1/group-invitations/{item['source']['id']}/reject/",
        })

    @patch("apps.dashboard.application.dashboard_service.InternalAPIClient")
    def test_invalid_query_returns_400(self, client_cls):
        client_cls.return_value = FakeActionClient()
        response = self.client.get(self._url(), {"page_size": 999})
        self.assertEqual(response.status_code, 400)

    def test_requires_authentication(self):
        self.client.logout()
        response = self.client.get(self._url())
        self.assertEqual(response.status_code, 401)


    @patch("apps.dashboard.application.dashboard_service.InternalAPIClient")
    def test_invalid_cursor_returns_400(self, client_cls):
        client_cls.return_value = FakeActionClient()
        response = self.client.get(self._url(), {"cursor": "bad-cursor"})
        self.assertEqual(response.status_code, 400)
