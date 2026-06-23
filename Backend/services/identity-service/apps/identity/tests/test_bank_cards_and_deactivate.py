"""Tests for bank card management and account deactivation."""

from __future__ import annotations

from unittest.mock import patch

from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

from apps.identity.application.token_service import TokenService
from apps.identity.domain.models import RefreshToken, User, UserBankCard


@override_settings(
    DEBUG=True,
    INTERNAL_SERVICE_TOKEN="internal-test-token",
    JWT_PRIVATE_KEY_PATH="keys/private.pem",
    JWT_PUBLIC_KEY_PATH="keys/public.pem",
)
class UserBankCardApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.token_service = TokenService()
        self.user = User.objects.create(
            email="cards@example.com",
            art_name="card-owner",
            is_email_verified=True,
        )
        self.user.set_password("Secret123!")
        self.user.save(update_fields=["password_hash", "updated_at"])
        access_token, refresh_token, _ = self.token_service.generate_tokens(self.user)
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.auth_headers = {"HTTP_AUTHORIZATION": f"Bearer {self.access_token}"}
        self.cards_url = "/api/v1/users/me/bank-cards/"
        self.bulk_url = "/api/v1/users/me/bank-cards/bulk/"
        self.deactivate_url = "/api/v1/users/me/deactivate/"
        self.internal_url = "/api/v1/internal/bank-cards/payment-context/"
        self.publisher = patch(
            "apps.identity.infrastructure.rabbitmq_publisher.RabbitMqPublisher.publish",
            return_value=True,
        )
        self.publisher.start()
        self.addCleanup(self.publisher.stop)

    def test_bank_card_crud_and_internal_payment_context(self):
        response = self.client.get(self.cards_url, **self.auth_headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), {"items": []})

        response = self.client.post(
            self.cards_url,
            {
                "card_number": "6037991234567890",
                "holder_name": "Amir Hosseini",
                "bank_name": "Melli",
                "is_default": True,
            },
            format="json",
            **self.auth_headers,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        created = response.json()
        self.assertEqual(created["masked_card_number"], "6037 **** **** 7890")
        self.assertEqual(created["card_number_last4"], "7890")
        self.assertTrue(created["is_default"])
        self.assertNotIn("card_number", created)
        self.assertNotIn("encrypted_card_number", created)
        self.assertNotIn("card_number_hash", created)

        duplicate = self.client.post(
            self.cards_url,
            {
                "card_number": "6037991234567890",
                "holder_name": "Amir Hosseini",
            },
            format="json",
            **self.auth_headers,
        )
        self.assertEqual(duplicate.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(duplicate.json()["error"]["code"], "CARD_ALREADY_EXISTS")

        detail_url = f"{self.cards_url}{created['id']}/"
        updated = self.client.patch(
            detail_url,
            {"holder_name": "Amir H.", "bank_name": "Mellat"},
            format="json",
            **self.auth_headers,
        )
        self.assertEqual(updated.status_code, status.HTTP_200_OK)
        self.assertEqual(updated.json()["holder_name"], "Amir H.")
        self.assertEqual(updated.json()["bank_name"], "Mellat")

        internal = self.client.post(
            self.internal_url,
            {"owner_user_id": str(self.user.id), "card_ids": [created["id"]]},
            format="json",
            HTTP_X_INTERNAL_SERVICE_TOKEN="internal-test-token",
        )
        self.assertEqual(internal.status_code, status.HTTP_200_OK)
        payload = internal.json()["items"][0]
        self.assertEqual(payload["card_number"], "6037991234567890")
        self.assertEqual(payload["masked_card_number"], "6037 **** **** 7890")

        unauthorized_internal = self.client.post(
            self.internal_url,
            {"owner_user_id": str(self.user.id)},
            format="json",
        )
        self.assertEqual(unauthorized_internal.status_code, status.HTTP_403_FORBIDDEN)

        deleted = self.client.delete(detail_url, **self.auth_headers)
        self.assertEqual(deleted.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(UserBankCard.objects.get(id=created["id"]).is_active)

    def test_bulk_save_is_atomic_and_replaces_metadata(self):
        first = self.client.post(
            self.cards_url,
            {
                "card_number": "6037991234567890",
                "holder_name": "First Holder",
                "bank_name": "Melli",
                "is_default": True,
            },
            format="json",
            **self.auth_headers,
        ).json()
        second = self.client.post(
            self.cards_url,
            {
                "card_number": "6104331234561234",
                "holder_name": "Second Holder",
                "bank_name": "Mellat",
                "is_default": False,
            },
            format="json",
            **self.auth_headers,
        ).json()

        invalid = self.client.put(
            self.bulk_url,
            {
                "cards": [
                    {
                        "id": first["id"],
                        "holder_name": "First Updated",
                        "is_default": True,
                    },
                    {
                        "client_id": "tmp-2",
                        "card_number": "123",
                        "holder_name": "Broken",
                    },
                ],
                "deleted_card_ids": [second["id"]],
            },
            format="json",
            **self.auth_headers,
        )
        self.assertEqual(invalid.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(UserBankCard.objects.filter(user=self.user, is_active=True).count(), 2)
        self.assertEqual(UserBankCard.objects.get(id=first["id"]).holder_name, "First Holder")
        self.assertTrue(UserBankCard.objects.get(id=second["id"]).is_active)

        valid = self.client.put(
            self.bulk_url,
            {
                "cards": [
                    {
                        "id": first["id"],
                        "holder_name": "First Updated",
                        "bank_name": "Parsian",
                        "is_default": False,
                    },
                    {
                        "client_id": "tmp-3",
                        "card_number": "5022291234561111",
                        "holder_name": "Third Holder",
                        "bank_name": "Pasargad",
                        "is_default": True,
                    },
                ],
                "deleted_card_ids": [second["id"]],
            },
            format="json",
            **self.auth_headers,
        )
        self.assertEqual(valid.status_code, status.HTTP_200_OK)
        body = valid.json()
        self.assertEqual(body["deleted_card_ids"], [second["id"]])
        self.assertEqual(len(body["items"]), 2)
        self.assertEqual(UserBankCard.objects.filter(user=self.user, is_active=True).count(), 2)
        self.assertFalse(UserBankCard.objects.get(id=second["id"]).is_active)
        first_card = UserBankCard.objects.get(id=first["id"])
        self.assertEqual(first_card.holder_name, "First Updated")
        self.assertFalse(first_card.is_default)
        self.assertTrue(UserBankCard.objects.exclude(id=first["id"]).get(is_active=True).is_default)

    def test_deactivate_account_revokes_refresh_and_blocks_access(self):
        response = self.client.post(
            self.deactivate_url,
            {"current_password": "Secret123!", "reason": "Done"},
            format="json",
            **self.auth_headers,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)
        self.assertIsNotNone(self.user.deleted_at)
        self.assertFalse(
            RefreshToken.objects.filter(user=self.user, revoked_at__isnull=True).exists()
        )

        refresh_response = self.client.post(
            "/api/v1/auth/token/refresh/",
            {"refresh_token": self.refresh_token},
            format="json",
        )
        self.assertEqual(refresh_response.status_code, status.HTTP_401_UNAUTHORIZED)

        me_response = self.client.get("/api/v1/users/me/", **self.auth_headers)
        self.assertEqual(me_response.status_code, status.HTTP_401_UNAUTHORIZED)

        password_login = self.client.post(
            "/api/v1/auth/password/login/",
            {"art_name": self.user.art_name, "password": "Secret123!"},
            format="json",
        )
        self.assertEqual(password_login.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(password_login.json()["error"]["code"], "INVALID_CREDENTIALS")

        repeated = self.client.post(
            self.deactivate_url,
            {"current_password": "Secret123!"},
            format="json",
            **self.auth_headers,
        )
        self.assertEqual(repeated.status_code, status.HTTP_401_UNAUTHORIZED)
