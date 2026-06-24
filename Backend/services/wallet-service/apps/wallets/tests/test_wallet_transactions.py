
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from apps.wallets.domain.models import (
    CurrencyChoices,
    LedgerEntry,
    LedgerEntryTypeChoices,
    WalletTransaction,
    WalletTransactionDirectionChoices,
    WalletTransactionStatusChoices,
    WalletTransactionTypeChoices,
)
from apps.wallets.infrastructure.repositories import WalletRepository
from apps.wallets.tests.helpers import api_client, auth_user, create_user_projection, get_or_create_wallet


class WalletTransactionApiTests(TestCase):
    def setUp(self):
        self.user = create_user_projection(art_name="tx_artist")
        self.other = create_user_projection(email="other@example.com", art_name="other_artist")
        self.wallet = get_or_create_wallet(self.user.identity_user_id)
        self.other_wallet = get_or_create_wallet(self.other.identity_user_id)
        now = timezone.now()
        self.tx1 = WalletTransaction.objects.create(
            wallet=self.wallet,
            type=WalletTransactionTypeChoices.SETTLEMENT_PAYMENT,
            status=WalletTransactionStatusChoices.COMPLETED,
            direction=WalletTransactionDirectionChoices.OUT,
            amount_minor=100000,
            currency=CurrencyChoices.IRR,
            description="A",
            reference_type="SETTLEMENT_PLAN_ITEM",
            reference_id="00000000-0000-0000-0000-000000000001",
            idempotency_key="tx1",
            completed_at=now - timedelta(days=2),
        )
        self.tx2 = WalletTransaction.objects.create(
            wallet=self.wallet,
            type=WalletTransactionTypeChoices.WITHDRAWAL,
            status=WalletTransactionStatusChoices.PENDING,
            direction=WalletTransactionDirectionChoices.OUT,
            amount_minor=200000,
            currency=CurrencyChoices.IRR,
            description="B",
            reference_type="WITHDRAWAL",
            reference_id="00000000-0000-0000-0000-000000000002",
            idempotency_key="tx2",
        )
        self.tx3 = WalletTransaction.objects.create(
            wallet=self.wallet,
            type=WalletTransactionTypeChoices.SETTLEMENT_RECEIVED,
            status=WalletTransactionStatusChoices.COMPLETED,
            direction=WalletTransactionDirectionChoices.IN,
            amount_minor=300000,
            currency=CurrencyChoices.IRR,
            description="C",
            reference_type="SETTLEMENT_PLAN_ITEM",
            reference_id="00000000-0000-0000-0000-000000000003",
            idempotency_key="tx3",
            completed_at=now,
        )
        WalletTransaction.objects.filter(id=self.tx1.id).update(created_at=now - timedelta(days=2), updated_at=now - timedelta(days=2))
        WalletTransaction.objects.filter(id=self.tx2.id).update(created_at=now - timedelta(days=1), updated_at=now - timedelta(days=1))
        WalletTransaction.objects.filter(id=self.tx3.id).update(created_at=now, updated_at=now)
        self.tx1.refresh_from_db()
        self.tx2.refresh_from_db()
        self.tx3.refresh_from_db()
        WalletRepository.refresh_balances(self.wallet)
        self.other_tx = WalletTransaction.objects.create(
            wallet=self.other_wallet,
            type=WalletTransactionTypeChoices.TOP_UP,
            status=WalletTransactionStatusChoices.COMPLETED,
            direction=WalletTransactionDirectionChoices.IN,
            amount_minor=500000,
            currency=CurrencyChoices.IRR,
            description="other",
            idempotency_key="other-tx",
            completed_at=now,
        )

    def test_user_sees_only_own_transactions(self):
        response = api_client(auth_user(self.user.identity_user_id, self.user.email)).get("/api/v1/wallets/me/transactions/")
        self.assertEqual(response.status_code, 200)
        ids = {entry["id"] for entry in response.json()["results"]}
        self.assertEqual(ids, {str(self.tx1.id), str(self.tx2.id), str(self.tx3.id)})
        self.assertNotIn(str(self.other_tx.id), ids)

    def test_other_user_transaction_blocked(self):
        response = api_client(auth_user(self.user.identity_user_id, self.user.email)).get(f"/api/v1/wallets/me/transactions/{self.other_tx.id}/")
        self.assertEqual(response.status_code, 404)

    def test_type_filter_works(self):
        response = api_client(auth_user(self.user.identity_user_id, self.user.email)).get("/api/v1/wallets/me/transactions/?type=WITHDRAWAL")
        self.assertEqual(response.status_code, 200)
        results = response.json()["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], str(self.tx2.id))

    def test_status_filter_works(self):
        response = api_client(auth_user(self.user.identity_user_id, self.user.email)).get("/api/v1/wallets/me/transactions/?status=COMPLETED")
        self.assertEqual(response.status_code, 200)
        ids = {entry["id"] for entry in response.json()["results"]}
        self.assertEqual(ids, {str(self.tx1.id), str(self.tx3.id)})

    def test_date_filter_works(self):
        from_value = (timezone.now() - timedelta(hours=12)).isoformat()
        response = api_client(auth_user(self.user.identity_user_id, self.user.email)).get(f"/api/v1/wallets/me/transactions/?from={from_value}")
        self.assertEqual(response.status_code, 200)
        results = response.json()["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], str(self.tx3.id))

    def test_pagination_works(self):
        client = api_client(auth_user(self.user.identity_user_id, self.user.email))
        first = client.get("/api/v1/wallets/me/transactions/?page_size=2")
        self.assertEqual(first.status_code, 200)
        data = first.json()
        self.assertEqual(len(data["results"]), 2)
        self.assertTrue(data["next_cursor"])
        second = client.get(f"/api/v1/wallets/me/transactions/?page_size=2&cursor={data['next_cursor']}")
        self.assertEqual(second.status_code, 200)
        ids = {entry["id"] for entry in data["results"] + second.json()["results"]}
        self.assertEqual(ids, {str(self.tx1.id), str(self.tx2.id), str(self.tx3.id)})

    def test_response_has_no_card_number_or_secret(self):
        response = api_client(auth_user(self.user.identity_user_id, self.user.email)).get(f"/api/v1/wallets/me/transactions/{self.tx1.id}/")
        self.assertEqual(response.status_code, 200)
        serialized = response.content.decode("utf-8")
        self.assertNotIn("card_number", serialized)
        self.assertNotIn("secret", serialized)

    def test_swagger_documents_transaction_endpoints(self):
        response = self.client.get("/api/schema/")
        self.assertEqual(response.status_code, 200)
        schema = response.content.decode("utf-8")
        self.assertIn("/api/v1/wallets/me/transactions/", schema)
        self.assertIn("/api/v1/wallets/me/transactions/{transaction_id}/", schema)
