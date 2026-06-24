from __future__ import annotations

from datetime import timedelta
from uuid import uuid4

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.dashboard.domain.models import InboxMessage
from apps.dashboard.infrastructure.rabbitmq_consumer import DashboardEventConsumer
from apps.dashboard.tests.helpers import (
    api_client,
    auth_user,
    create_activity,
    create_group,
    create_member,
    create_user_projection,
)


def envelope(event_type, routing_key, data, *, event_id=None, occurred_at=None, source_service="test-service"):
    value = occurred_at or timezone.now().isoformat()
    return {
        "event_id": str(event_id or uuid4()),
        "event_type": event_type,
        "event_version": 1,
        "occurred_at": value,
        "source_service": source_service,
        "correlation_id": str(uuid4()),
        "causation_id": str(uuid4()),
        "routing_key": routing_key,
        "data": data,
    }


class DashboardActivityFeedTests(TestCase):
    def setUp(self):
        self.me = auth_user(sub=uuid4())
        self.friend_id = uuid4()
        self.other_user = auth_user(sub=uuid4())
        self.client = api_client(self.me)
        self.group = create_group(title="شام دوستانه", created_by_user_id=self.me.sub)
        self.other_group = create_group(title="Hidden Group", created_by_user_id=self.other_user.sub)
        create_user_projection(user_id=self.me.sub, art_name="ali_artist")
        create_user_projection(user_id=self.friend_id, art_name="reza_artist")
        create_member(self.group.group_id, user_id=self.me.sub, role="OWNER", art_name_snapshot="ali_artist")
        create_member(self.group.group_id, user_id=self.friend_id, art_name_snapshot="reza_artist")
        create_member(self.other_group.group_id, user_id=self.other_user.sub, role="OWNER", art_name_snapshot="outsider")

    def _url(self):
        return reverse("dashboard_activity_feed")

    def test_feed_only_returns_current_user_group_activity(self):
        now = timezone.now()
        create_activity(
            group_id=self.group.group_id,
            actor_user_id=self.me.sub,
            event_type="EXPENSE_CREATED",
            occurred_at=now,
            summary={"expense_id": str(uuid4()), "amount_minor": 800000, "currency": "IRR"},
        )
        create_activity(
            group_id=self.other_group.group_id,
            actor_user_id=self.other_user.sub,
            event_type="EXPENSE_CREATED",
            occurred_at=now - timedelta(minutes=1),
            summary={"expense_id": str(uuid4()), "amount_minor": 500000, "currency": "IRR"},
        )

        response = self.client.get(self._url())
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data["results"]), 1)
        self.assertEqual(data["results"][0]["group"]["id"], str(self.group.group_id))
        self.assertEqual(data["results"][0]["actor"]["art_name"], "ali_artist")

    def test_feed_filters_and_pagination(self):
        base = timezone.now()
        create_activity(group_id=self.group.group_id, actor_user_id=self.me.sub, event_type="EXPENSE_CREATED", occurred_at=base, summary={"expense_id": str(uuid4())})
        create_activity(group_id=self.group.group_id, actor_user_id=self.friend_id, event_type="SETTLEMENT_REPORTED", occurred_at=base - timedelta(minutes=1), summary={"item_id": str(uuid4())})
        create_activity(group_id=self.group.group_id, actor_user_id=self.friend_id, event_type="RECEIPT_UPLOADED", occurred_at=base - timedelta(minutes=2), summary={"media_file_id": str(uuid4())})

        response = self.client.get(self._url(), {"type": "SETTLEMENT_REPORTED", "page_size": 1})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["results"]), 1)

        response = self.client.get(self._url(), {"group_id": str(self.group.group_id), "from": str(base.date()), "to": str(base.date())})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["results"]), 3)

    def test_consumer_creates_activity_and_is_idempotent(self):
        consumer = DashboardEventConsumer()
        event_id = uuid4()
        payload = envelope(
            "ExpenseCreated",
            "expense.created",
            {
                "expense_id": str(uuid4()),
                "group_id": str(self.group.group_id),
                "created_by_user_id": str(self.me.sub),
                "payer_user_id": str(self.me.sub),
                "currency": "IRR",
                "total_amount_minor": 900000,
            },
            event_id=event_id,
            source_service="expense-service",
        )

        consumer.process_expense_payload(payload)
        consumer.process_expense_payload(payload)

        response = self.client.get(self._url())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["results"]), 1)
        self.assertEqual(InboxMessage.objects.count(), 1)
        self.assertEqual(InboxMessage.objects.first().status, "PROCESSED")

    def test_invalid_activity_query_returns_400(self):
        response = self.client.get(self._url(), {"page_size": 200})
        self.assertEqual(response.status_code, 400)

    def test_swagger_contains_activity_and_action_paths(self):
        response = self.client.get("/api/schema/")
        self.assertEqual(response.status_code, 200)
        payload = response.content.decode("utf-8")
        self.assertIn("/api/v1/dashboard/activity-feed/", payload)
        self.assertIn("/api/v1/dashboard/action-items/", payload)


class DashboardActivityAuthTests(TestCase):
    def test_requires_authentication(self):
        response = self.client.get(reverse("dashboard_activity_feed"))
        self.assertEqual(response.status_code, 401)
