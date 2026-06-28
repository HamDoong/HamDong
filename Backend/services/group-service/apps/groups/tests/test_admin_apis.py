
from __future__ import annotations

from datetime import timedelta
from types import SimpleNamespace
from uuid import uuid4

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.groups.domain.models import Group


def auth_user(user_id=None, role="USER", email="user@example.com"):
    user_id = str(user_id or uuid4())
    return SimpleNamespace(id=user_id, sub=user_id, email=email, role=role, is_authenticated=True)


class AdminGroupApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = auth_user(role="ADMIN", email="admin@example.com")
        self.user = auth_user(role="USER", email="user@example.com")
        self.group1 = Group.objects.create(
            title="سفر شمال",
            group_type="TRIP",
            status="ACTIVE",
            created_by_user_id=uuid4(),
            created_by_email="owner1@example.com",
            member_count=5,
        )
        self.group2 = Group.objects.create(
            title="Hidden",
            group_type="GENERAL",
            status="ARCHIVED",
            created_by_user_id=uuid4(),
            created_by_email="owner2@example.com",
            member_count=2,
        )
        Group.objects.filter(id=self.group1.id).update(created_at=timezone.now() - timedelta(days=2), updated_at=timezone.now() - timedelta(days=2))
        Group.objects.filter(id=self.group2.id).update(created_at=timezone.now() - timedelta(days=1), updated_at=timezone.now() - timedelta(days=1))
        self.group1.refresh_from_db()
        self.group2.refresh_from_db()

    def test_missing_token_returns_401(self):
        response = self.client.get("/api/v1/admin/groups/")
        self.assertEqual(response.status_code, 401)

    def test_normal_user_gets_403(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/v1/admin/groups/")
        self.assertEqual(response.status_code, 403)

    def test_admin_can_list_groups_and_filter(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(f"/api/v1/admin/groups/?status=ACTIVE&owner_user_id={self.group1.created_by_user_id}")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload["results"]), 1)
        self.assertEqual(payload["results"][0]["id"], str(self.group1.id))
        self.assertNotIn("invite_code", str(payload))

    def test_pagination_and_schema(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.get("/api/v1/admin/groups/?page_size=1")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["next_cursor"])

        schema = self.client.get("/api/schema/?format=json")
        self.assertEqual(schema.status_code, 200)
        self.assertIn("/api/v1/admin/groups/", schema.json()["paths"])
