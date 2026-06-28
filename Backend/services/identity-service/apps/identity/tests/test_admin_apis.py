
from __future__ import annotations

from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.identity.application.token_service import TokenService
from apps.identity.domain.models import RefreshToken, User, UserBankCard


class AdminUserApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.token_service = TokenService()
        self.admin = User.objects.create(email="admin@example.com", art_name="admin_artist", role="ADMIN")
        self.normal = User.objects.create(email="user@example.com", art_name="user_artist", role="USER")
        self.user1 = User.objects.create(email="alpha@example.com", art_name="alpha_artist", role="USER", is_email_verified=True)
        self.user2 = User.objects.create(email="beta@example.com", art_name="beta_artist", role="USER", is_active=False)
        UserBankCard.objects.create(
            user=self.user1,
            holder_name="Alpha Artist",
            bank_name="Mask Bank",
            card_number_last4="1234",
            masked_card_number="****-****-****-1234",
            card_number_hash="hash1234",
            encrypted_card_number="secret",
            is_default=True,
        )
        RefreshToken.objects.create(
            user=self.user1,
            token_hash="secret-token-hash",
            jti="11111111-1111-1111-1111-111111111111",
            expires_at=timezone.now() + timedelta(days=7),
        )
        User.objects.filter(id=self.user1.id).update(created_at=timezone.now() - timedelta(days=2), updated_at=timezone.now() - timedelta(days=2))
        User.objects.filter(id=self.user2.id).update(created_at=timezone.now() - timedelta(days=1), updated_at=timezone.now() - timedelta(days=1))
        self.user1.refresh_from_db()
        self.user2.refresh_from_db()

    def auth(self, user):
        access, _, _ = self.token_service.generate_tokens(user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    def test_missing_token_returns_401(self):
        response = self.client.get("/api/v1/admin/users/")
        self.assertEqual(response.status_code, 401)

    def test_normal_user_gets_403(self):
        self.auth(self.normal)
        response = self.client.get("/api/v1/admin/users/")
        self.assertEqual(response.status_code, 403)

    def test_admin_can_list_and_filter_users(self):
        self.auth(self.admin)
        response = self.client.get("/api/v1/admin/users/?status=ACTIVE&email=alpha")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload["results"]), 1)
        self.assertEqual(payload["results"][0]["id"], str(self.user1.id))

    def test_admin_can_view_user_detail_without_sensitive_fields(self):
        self.auth(self.admin)
        response = self.client.get(f"/api/v1/admin/users/{self.user1.id}/")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["id"], str(self.user1.id))
        self.assertIn("bank_cards", payload)
        self.assertNotIn("password_hash", payload)
        self.assertNotIn("refresh_token", payload)
        self.assertNotIn("jti", payload)
        self.assertEqual(payload["bank_cards"][0]["masked_card_number"], "****-****-****-1234")

    def test_pagination_works(self):
        self.auth(self.admin)
        response = self.client.get("/api/v1/admin/users/?page_size=1")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload["results"]), 1)
        self.assertTrue(payload["next_cursor"])

    def test_schema_includes_admin_user_paths(self):
        self.auth(self.admin)
        response = self.client.get("/api/schema/?format=json")
        self.assertEqual(response.status_code, 200)
        paths = response.json()["paths"]
        self.assertIn("/api/v1/admin/users/", paths)
        self.assertIn("/api/v1/admin/users/{user_id}/", paths)
