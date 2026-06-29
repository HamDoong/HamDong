"""Tests for bank card holder-name fallback and owner payload."""

from __future__ import annotations

from unittest.mock import patch

from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

from apps.identity.application.token_service import TokenService
from apps.identity.domain.models import User, UserBankCard


@override_settings(
    DEBUG=True,
    JWT_PRIVATE_KEY_PATH="keys/private.pem",
    JWT_PUBLIC_KEY_PATH="keys/public.pem",
)
class BankCardImprovementsTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.token_service = TokenService()
        self.user = User.objects.create(
            email="cards-improvements@example.com",
            art_name="amir_art",
            first_name="Amir",
            last_name="Hosseini",
            avatar_url=None,
            is_email_verified=True,
        )
        access_token, _, _ = self.token_service.generate_tokens(self.user)
        self.auth_headers = {"HTTP_AUTHORIZATION": f"Bearer {access_token}"}
        self.cards_url = "/api/v1/users/me/bank-cards/"
        self.bulk_url = "/api/v1/users/me/bank-cards/bulk/"
        self.publisher = patch(
            "apps.identity.infrastructure.rabbitmq_publisher.RabbitMqPublisher.publish",
            return_value=True,
        )
        self.publisher.start()
        self.addCleanup(self.publisher.stop)

    def test_create_without_holder_name_falls_back_to_full_name(self):
        response = self.client.post(
            self.cards_url,
            {
                "card_number": "6037991234567890",
                "bank_name": "Melli",
                "is_default": True,
            },
            format="json",
            **self.auth_headers,
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.json()["holder_name"], "Amir Hosseini")

    def test_create_without_holder_name_falls_back_to_first_name_only(self):
        self.user.last_name = None
        self.user.save(update_fields=["last_name", "updated_at"])

        response = self.client.post(
            self.cards_url,
            {
                "card_number": "6037991234567890",
                "bank_name": "Melli",
            },
            format="json",
            **self.auth_headers,
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.json()["holder_name"], "Amir")

    def test_create_without_holder_name_falls_back_to_last_name_only(self):
        self.user.first_name = None
        self.user.save(update_fields=["first_name", "updated_at"])

        response = self.client.post(
            self.cards_url,
            {
                "card_number": "6037991234567890",
                "bank_name": "Melli",
            },
            format="json",
            **self.auth_headers,
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.json()["holder_name"], "Hosseini")

    def test_create_without_holder_name_and_without_user_name_returns_validation_error(self):
        self.user.first_name = None
        self.user.last_name = None
        self.user.save(update_fields=["first_name", "last_name", "updated_at"])

        response = self.client.post(
            self.cards_url,
            {
                "card_number": "6037991234567890",
                "bank_name": "Melli",
            },
            format="json",
            **self.auth_headers,
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["error"]["code"], "INVALID_HOLDER_NAME")
        self.assertEqual(UserBankCard.objects.filter(user=self.user).count(), 0)

    def test_explicit_holder_name_is_not_overridden_and_is_trimmed(self):
        response = self.client.post(
            self.cards_url,
            {
                "card_number": "6037991234567890",
                "holder_name": "  Ali Rezaei  ",
                "bank_name": "Melli",
            },
            format="json",
            **self.auth_headers,
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.json()["holder_name"], "Ali Rezaei")

    def test_blank_holder_name_falls_back_to_user_name(self):
        response = self.client.post(
            self.cards_url,
            {
                "card_number": "6037991234567890",
                "holder_name": "   ",
                "bank_name": "Melli",
            },
            format="json",
            **self.auth_headers,
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.json()["holder_name"], "Amir Hosseini")

    def test_bulk_save_without_holder_name_uses_fallback(self):
        response = self.client.put(
            self.bulk_url,
            {
                "cards": [
                    {
                        "client_id": "tmp-1",
                        "card_number": "6037991234567890",
                        "bank_name": "Melli",
                        "is_default": True,
                    }
                ],
                "deleted_card_ids": [],
            },
            format="json",
            **self.auth_headers,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["items"][0]["holder_name"], "Amir Hosseini")

    def test_bulk_save_without_holder_name_and_without_user_name_is_atomic(self):
        self.user.first_name = None
        self.user.last_name = None
        self.user.save(update_fields=["first_name", "last_name", "updated_at"])

        response = self.client.put(
            self.bulk_url,
            {
                "cards": [
                    {
                        "client_id": "tmp-1",
                        "card_number": "6037991234567890",
                        "bank_name": "Melli",
                        "is_default": True,
                    }
                ],
                "deleted_card_ids": [],
            },
            format="json",
            **self.auth_headers,
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["error"]["code"], "VALIDATION_ERROR")
        self.assertIn("cards[0].holder_name", response.json()["error"]["details"])
        self.assertEqual(UserBankCard.objects.filter(user=self.user).count(), 0)

    def test_get_bank_cards_includes_owner_payload_and_no_sensitive_owner_fields(self):
        self.client.post(
            self.cards_url,
            {
                "card_number": "6037991234567890",
                "bank_name": "Melli",
                "is_default": True,
            },
            format="json",
            **self.auth_headers,
        )

        response = self.client.get(self.cards_url, **self.auth_headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = response.json()
        self.assertEqual(
            payload["owner"],
            {
                "user_id": str(self.user.id),
                "first_name": "Amir",
                "last_name": "Hosseini",
                "art_name": "amir_art",
                "avatar_url": None,
            },
        )
        self.assertEqual(payload["items"][0]["holder_name"], "Amir Hosseini")
        for forbidden_field in (
            "email",
            "phone_number",
            "date_of_birth",
            "city",
            "bio",
            "role",
            "roles",
            "password_hash",
            "is_staff",
        ):
            self.assertNotIn(forbidden_field, payload["owner"])

    def test_get_bank_cards_without_cards_still_returns_owner(self):
        response = self.client.get(self.cards_url, **self.auth_headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["items"], [])
        self.assertEqual(response.json()["owner"]["user_id"], str(self.user.id))

    def test_schema_marks_holder_name_optional_and_lists_owner(self):
        response = self.client.get("/api/schema/?format=json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = response.json()

        bank_cards_path = payload["paths"]["/api/v1/users/me/bank-cards/"]["get"]
        self.assertIn("responses", bank_cards_path)

        list_schema_ref = bank_cards_path["responses"]["200"]["content"]["application/json"]["schema"]["$ref"]
        list_schema_name = list_schema_ref.rsplit("/", 1)[-1]
        list_schema = payload["components"]["schemas"][list_schema_name]
        self.assertIn("owner", list_schema["properties"])
        self.assertIn("items", list_schema["properties"])

        create_schema = payload["components"]["schemas"]["CreateUserBankCard"]
        self.assertNotIn("holder_name", create_schema.get("required", []))

        bulk_item_ref = payload["components"]["schemas"]["BulkUserBankCardSave"]["properties"]["cards"]["items"]["$ref"]
        bulk_item_name = bulk_item_ref.rsplit("/", 1)[-1]
        bulk_item_schema = payload["components"]["schemas"][bulk_item_name]
        self.assertNotIn("holder_name", bulk_item_schema.get("required", []))
