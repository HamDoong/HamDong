
from __future__ import annotations

from datetime import timedelta
from types import SimpleNamespace
from uuid import uuid4

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.notifications.domain.models import NotificationMessage


def auth_user(role="USER"):
    user_id = uuid4()
    return SimpleNamespace(sub=str(user_id), id=str(user_id), role=role, email=f"{user_id}@example.com", is_authenticated=True)


class AdminNotificationApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = auth_user(role="ADMIN")
        self.user = auth_user(role="USER")
        self.notification = NotificationMessage.objects.create(
            recipient_user_id=uuid4(),
            recipient_email="notify@example.com",
            recipient="notify@example.com",
            recipient_masked="no***@example.com",
            channel="EMAIL",
            message_type="OTP",
            title="OTP title",
            body="OTP 123456",
            metadata={"smtp_password": "secret"},
            status="PENDING",
        )
        NotificationMessage.objects.filter(id=self.notification.id).update(created_at=timezone.now() - timedelta(days=1), updated_at=timezone.now() - timedelta(days=1))
        self.notification.refresh_from_db()

    def test_missing_token_returns_401(self):
        response = self.client.get("/api/v1/admin/notifications/")
        self.assertEqual(response.status_code, 401)

    def test_normal_user_gets_403(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/v1/admin/notifications/")
        self.assertEqual(response.status_code, 403)

    def test_admin_can_list_notifications_without_sensitive_body_fields(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.get("/api/v1/admin/notifications/?channel=EMAIL&type=OTP")
        self.assertEqual(response.status_code, 200)
        payload = response.json()["results"][0]
        self.assertEqual(payload["id"], str(self.notification.id))
        self.assertNotIn("body", payload)
        self.assertNotIn("metadata", payload)

    def test_schema_contains_admin_paths(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.get("/api/schema/?format=json")
        self.assertEqual(response.status_code, 200)
        self.assertIn("/api/v1/admin/notifications/", response.json()["paths"])
