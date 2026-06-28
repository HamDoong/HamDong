
from django.test import TestCase

from apps.wallets.domain.models import (
    CurrencyChoices,
    SettlementItemStatusChoices,
    SettlementPlanStatusChoices,
    WalletTransaction,
    WalletTransactionDirectionChoices,
    WalletTransactionStatusChoices,
    WalletTransactionTypeChoices,
)
from apps.wallets.tests.helpers import (
    api_client,
    auth_user,
    create_settlement_item_projection,
    create_user_projection,
    get_or_create_wallet,
    seed_available_balance,
)


class WalletSummaryApiTests(TestCase):
    def setUp(self):
        self.user = create_user_projection(art_name="owner_artist")
        self.receiver = create_user_projection(email="receiver@example.com", art_name="receiver_artist")
        self.payer = create_user_projection(email="payer@example.com", art_name="payer_artist")
        seed_available_balance(self.user.identity_user_id, 1000000)
        create_settlement_item_projection(
            payer_user_id=self.user.identity_user_id,
            payee_user_id=self.receiver.identity_user_id,
            amount_minor=250000,
            item_status=SettlementItemStatusChoices.PENDING,
            plan_status=SettlementPlanStatusChoices.ACTIVE,
        )
        create_settlement_item_projection(
            payer_user_id=self.payer.identity_user_id,
            payee_user_id=self.user.identity_user_id,
            amount_minor=350000,
            item_status=SettlementItemStatusChoices.PENDING,
            plan_status=SettlementPlanStatusChoices.ACTIVE,
        )
        create_settlement_item_projection(
            payer_user_id=self.user.identity_user_id,
            payee_user_id=self.receiver.identity_user_id,
            amount_minor=100000,
            item_status=SettlementItemStatusChoices.CONFIRMED,
            plan_status=SettlementPlanStatusChoices.ACTIVE,
        )
        wallet = get_or_create_wallet(self.user.identity_user_id)
        WalletTransaction.objects.create(
            wallet=wallet,
            type=WalletTransactionTypeChoices.TOP_UP,
            status=WalletTransactionStatusChoices.COMPLETED,
            direction=WalletTransactionDirectionChoices.IN,
            amount_minor=1000000,
            currency=CurrencyChoices.IRR,
            description="Top up",
            idempotency_key="summary-top-up",
        )

    def test_summary_only_for_current_user(self):
        response = api_client(auth_user(self.user.identity_user_id, self.user.email)).get("/api/v1/wallets/me/summary/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["wallet"]["currency"], "IRR")
        self.assertEqual(len(data["pending_payables"]), 1)
        self.assertEqual(len(data["pending_receivables"]), 1)

    def test_confirmed_settlements_removed_from_pending(self):
        response = api_client(auth_user(self.user.identity_user_id, self.user.email)).get("/api/v1/wallets/me/summary/")
        statuses = {entry["status"] for entry in response.json()["pending_payables"]}
        self.assertNotIn("CONFIRMED", statuses)

    def test_recent_transactions_newest_first(self):
        response = api_client(auth_user(self.user.identity_user_id, self.user.email)).get("/api/v1/wallets/me/summary/")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["recent_transactions"])

    def test_swagger_documents_summary(self):
        response = self.client.get("/api/schema/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("/api/v1/wallets/me/summary/", response.content.decode("utf-8"))
