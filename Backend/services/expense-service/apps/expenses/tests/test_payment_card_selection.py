from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

from apps.expenses.domain.models import (
    BankCardProjection,
    Expense,
    ExpensePaymentOption,
    GroupMemberProjection,
    GroupProjection,
    UserProjection,
)


class FakeBankCardClient:
    def __init__(self):
        self.calls = []

    def resolve_payment_context_cards(self, owner_user_id, card_ids=None):
        normalized_ids = [str(card_id) for card_id in (card_ids or [])]
        self.calls.append((str(owner_user_id), normalized_ids))
        return [
            {
                "id": card_id,
                "type": "BANK_CARD",
                "card_number": "6037991234567890" if card_id == normalized_ids[0] else "5022291234561111",
                "masked_card_number": "6037 **** **** 7890" if card_id == normalized_ids[0] else "5022 **** **** 1111",
                "card_number_last4": "7890" if card_id == normalized_ids[0] else "1111",
                "bank_name": "Melli" if card_id == normalized_ids[0] else "Pasargad",
                "holder_name": "Owner Holder",
                "is_default": card_id == normalized_ids[0],
            }
            for card_id in normalized_ids
        ]


def auth_user(user_id):
    return SimpleNamespace(sub=str(user_id), is_authenticated=True)


@override_settings(
    DEBUG=True,
    IDENTITY_PUBLIC_KEY_PATH="keys/public.pem",
    INTERNAL_SERVICE_TOKEN="internal-test-token",
)
class ExpensePaymentCardSelectionTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.group_id = uuid4()
        self.owner_id = uuid4()
        self.member_id = uuid4()
        self.outsider_id = uuid4()
        self.card_one = uuid4()
        self.card_two = uuid4()
        GroupProjection.objects.create(
            group_id=self.group_id,
            title="Trip group",
            group_type=GroupProjection.TYPE_TRIP,
            status=GroupProjection.STATUS_ACTIVE,
            created_by_user_id=self.owner_id,
            member_count=2,
        )
        UserProjection.objects.create(
            identity_user_id=self.owner_id,
            email="owner@example.com",
            art_name="owner_artist",
        )
        UserProjection.objects.create(
            identity_user_id=self.member_id,
            email="member@example.com",
            art_name="member_artist",
        )
        GroupMemberProjection.objects.bulk_create(
            [
                GroupMemberProjection(
                    group_id=self.group_id,
                    user_id=self.owner_id,
                    email="owner@example.com",
                    art_name_snapshot="owner_artist",
                    role=GroupMemberProjection.ROLE_OWNER,
                    status=GroupMemberProjection.STATUS_ACTIVE,
                ),
                GroupMemberProjection(
                    group_id=self.group_id,
                    user_id=self.member_id,
                    email="member@example.com",
                    art_name_snapshot="member_artist",
                    role=GroupMemberProjection.ROLE_MEMBER,
                    status=GroupMemberProjection.STATUS_ACTIVE,
                ),
            ]
        )
        BankCardProjection.objects.bulk_create(
            [
                BankCardProjection(
                    card_id=self.card_one,
                    user_id=self.owner_id,
                    holder_name="Owner Holder",
                    bank_name="Melli",
                    card_number_last4="7890",
                    masked_card_number="6037 **** **** 7890",
                    is_default=True,
                    is_active=True,
                ),
                BankCardProjection(
                    card_id=self.card_two,
                    user_id=self.owner_id,
                    holder_name="Owner Holder",
                    bank_name="Pasargad",
                    card_number_last4="1111",
                    masked_card_number="5022 **** **** 1111",
                    is_default=False,
                    is_active=True,
                ),
            ]
        )
        self.publisher = patch(
            "apps.expenses.infrastructure.rabbitmq_publisher.RabbitMQPublisher.publish",
            return_value=True,
        )
        self.publisher.start()
        self.addCleanup(self.publisher.stop)
        self.fake_client = FakeBankCardClient()
        self.bank_card_client_patch = patch(
            "apps.expenses.application.use_cases.IdentityBankCardClient",
            lambda: self.fake_client,
        )
        self.bank_card_client_patch.start()
        self.addCleanup(self.bank_card_client_patch.stop)

    def build_payload(self, **overrides):
        payload = {
            "title": "Dinner",
            "description": "Shared dinner",
            "payer_user_id": str(self.owner_id),
            "base_amount_minor": 1000,
            "currency": "IRR",
            "split_method": "EQUAL",
            "participant_user_ids": [str(self.owner_id), str(self.member_id)],
        }
        payload.update(overrides)
        return payload

    def test_create_expense_attaches_selected_cards_masked_only(self):
        self.client.force_authenticate(user=auth_user(self.owner_id))
        response = self.client.post(
            f"/api/v1/groups/{self.group_id}/expenses/",
            self.build_payload(
                payment_card_ids=[str(self.card_one), str(self.card_two), str(self.card_two)]
            ),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()
        self.assertEqual(data["created_by"]["art_name"], "owner_artist")
        self.assertEqual(len(data["payment_options"]), 2)
        self.assertEqual(data["payment_options"][0]["masked_card_number"], "6037 **** **** 7890")
        self.assertNotIn("card_number", data["payment_options"][0])
        expense = Expense.objects.get(id=data["id"])
        self.assertEqual(ExpensePaymentOption.objects.filter(expense=expense).count(), 2)

    def test_create_expense_uses_default_when_payment_card_ids_missing(self):
        self.client.force_authenticate(user=auth_user(self.owner_id))
        response = self.client.post(
            f"/api/v1/groups/{self.group_id}/expenses/",
            self.build_payload(),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(response.json()["payment_options"]), 1)
        self.assertEqual(response.json()["payment_options"][0]["id"], str(self.card_one))

    def test_create_expense_with_empty_payment_card_ids_attaches_none(self):
        self.client.force_authenticate(user=auth_user(self.owner_id))
        response = self.client.post(
            f"/api/v1/groups/{self.group_id}/expenses/",
            self.build_payload(payment_card_ids=[]),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.json()["payment_options"], [])

    def test_create_expense_rejects_other_users_card_without_creating_expense(self):
        outsider_card = uuid4()
        BankCardProjection.objects.create(
            card_id=outsider_card,
            user_id=self.outsider_id,
            holder_name="Other Holder",
            bank_name="Other",
            card_number_last4="0000",
            masked_card_number="6037 **** **** 0000",
            is_default=True,
            is_active=True,
        )
        self.client.force_authenticate(user=auth_user(self.owner_id))
        response = self.client.post(
            f"/api/v1/groups/{self.group_id}/expenses/",
            self.build_payload(payment_card_ids=[str(outsider_card)]),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["error"]["code"], "INVALID_PAYMENT_CARD")
        self.assertEqual(Expense.objects.count(), 0)

    def test_get_and_replace_expense_payment_options_require_membership_and_use_full_number(self):
        self.client.force_authenticate(user=auth_user(self.owner_id))
        create_response = self.client.post(
            f"/api/v1/groups/{self.group_id}/expenses/",
            self.build_payload(payment_card_ids=[str(self.card_one)]),
            format="json",
        )
        expense_id = create_response.json()["id"]

        participant_client = APIClient()
        participant_client.force_authenticate(user=auth_user(self.member_id))
        payment_options = participant_client.get(f"/api/v1/expenses/{expense_id}/payment-options/")
        self.assertEqual(payment_options.status_code, status.HTTP_200_OK)
        payload = payment_options.json()
        self.assertEqual(payload["payee"]["art_name"], "owner_artist")
        self.assertEqual(payload["payment_options"][0]["card_number"], "6037991234567890")

        outsider_client = APIClient()
        outsider_client.force_authenticate(user=auth_user(self.outsider_id))
        forbidden = outsider_client.get(f"/api/v1/expenses/{expense_id}/payment-options/")
        self.assertEqual(forbidden.status_code, status.HTTP_403_FORBIDDEN)

        updated = self.client.put(
            f"/api/v1/expenses/{expense_id}/payment-options/",
            {"payment_card_ids": [str(self.card_two), str(self.card_two)]},
            format="json",
        )
        self.assertEqual(updated.status_code, status.HTTP_200_OK)
        self.assertEqual(len(updated.json()["payment_options"]), 1)
        self.assertEqual(updated.json()["payment_options"][0]["id"], str(self.card_two))
        self.assertNotIn("card_number", updated.json()["payment_options"][0])
