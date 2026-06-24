
from django.test import TestCase

from apps.wallets.application.wallet_service import WalletService
from apps.wallets.domain.models import (
    LedgerEntry,
    OutboxMessage,
    SettlementItemStatusChoices,
    SettlementPlanStatusChoices,
    Wallet,
    WalletTransaction,
)
from apps.wallets.infrastructure.repositories import WalletRepository
from apps.wallets.tests.helpers import (
    api_client,
    auth_user,
    create_settlement_item_projection,
    create_user_projection,
    get_or_create_wallet,
    seed_available_balance,
)


class WalletPayApiTests(TestCase):
    def setUp(self):
        self.payer = create_user_projection(art_name="payer_artist")
        self.payee = create_user_projection(email="payee@example.com", art_name="payee_artist")
        self.other = create_user_projection(email="other@example.com", art_name="other_artist")
        seed_available_balance(self.payer.identity_user_id, 900000)
        get_or_create_wallet(self.payee.identity_user_id)
        self.item = create_settlement_item_projection(
            payer_user_id=self.payer.identity_user_id,
            payee_user_id=self.payee.identity_user_id,
            amount_minor=500000,
        )

    def _pay(self, user, item_id=None, key="idem-1"):
        return api_client(auth_user(user.identity_user_id, user.email)).post(
            f"/api/v1/wallets/settlement-plan-items/{item_id or self.item.item_id}/pay/",
            {"idempotency_key": key},
            format="json",
        )

    def test_payer_can_pay(self):
        response = self._pay(self.payer)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["amount_minor"], 500000)
        self.assertEqual(data["currency"], "IRR")
        payer_wallet = Wallet.objects.get(user_id=self.payer.identity_user_id, currency="IRR")
        payee_wallet = Wallet.objects.get(user_id=self.payee.identity_user_id, currency="IRR")
        WalletRepository.refresh_balances(payer_wallet)
        WalletRepository.refresh_balances(payee_wallet)
        self.assertEqual(payer_wallet.available_balance_minor, 400000)
        self.assertEqual(payee_wallet.available_balance_minor, 500000)
        self.assertEqual(LedgerEntry.objects.count(), 3)
        self.assertEqual(OutboxMessage.objects.filter(event_type="WalletSettlementPaid").count(), 1)

    def test_other_user_cannot_pay(self):
        response = self._pay(self.other)
        self.assertEqual(response.status_code, 403)

    def test_payee_cannot_pay_instead_of_payer(self):
        response = self._pay(self.payee)
        self.assertEqual(response.status_code, 403)

    def test_missing_idempotency_key_rejected(self):
        response = api_client(auth_user(self.payer.identity_user_id, self.payer.email)).post(
            f"/api/v1/wallets/settlement-plan-items/{self.item.item_id}/pay/",
            {},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_item_not_found_rejected(self):
        response = self._pay(self.payer, item_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
        self.assertEqual(response.status_code, 404)

    def test_paid_item_rejected(self):
        self.item.item_status = SettlementItemStatusChoices.CONFIRMED
        self.item.save(update_fields=["item_status", "updated_at"])
        response = self._pay(self.payer)
        self.assertEqual(response.status_code, 409)

    def test_inactive_plan_rejected(self):
        self.item.plan_status = SettlementPlanStatusChoices.CANCELLED
        self.item.save(update_fields=["plan_status", "updated_at"])
        response = self._pay(self.payer)
        self.assertEqual(response.status_code, 409)

    def test_insufficient_balance_rejected(self):
        self.item.amount_minor = 999999999
        self.item.save(update_fields=["amount_minor", "updated_at"])
        response = self._pay(self.payer)
        self.assertEqual(response.status_code, 409)

    def test_same_idempotency_key_returns_same_result_and_no_duplicate_debit(self):
        first = self._pay(self.payer, key="same-key")
        second = self._pay(self.payer, key="same-key")
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.json()["transaction_id"], second.json()["transaction_id"])
        payer_wallet = Wallet.objects.get(user_id=self.payer.identity_user_id, currency="IRR")
        WalletRepository.refresh_balances(payer_wallet)
        self.assertEqual(payer_wallet.available_balance_minor, 400000)
        self.assertEqual(WalletTransaction.objects.filter(wallet=payer_wallet, reference_id=self.item.item_id).count(), 1)

    def test_swagger_documents_pay_endpoint(self):
        response = self.client.get("/api/schema/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("/api/v1/wallets/settlement-plan-items/{item_id}/pay/", response.content.decode("utf-8"))


class WalletPayServiceTests(TestCase):
    def setUp(self):
        self.payer = create_user_projection(art_name="payer_artist")
        self.payee = create_user_projection(email="payee@example.com", art_name="payee_artist")
        seed_available_balance(self.payer.identity_user_id, 700000)
        get_or_create_wallet(self.payee.identity_user_id)
        self.item = create_settlement_item_projection(
            payer_user_id=self.payer.identity_user_id,
            payee_user_id=self.payee.identity_user_id,
            amount_minor=500000,
        )
        self.service = WalletService()

    def test_repeated_requests_only_one_payment_is_recorded(self):
        first = self.service.pay_settlement_item(self.payer.identity_user_id, self.item.item_id, "concurrent-like")
        second = self.service.pay_settlement_item(self.payer.identity_user_id, self.item.item_id, "concurrent-like")
        self.assertEqual(first["transaction_id"], second["transaction_id"])
        payer_wallet = Wallet.objects.get(user_id=self.payer.identity_user_id, currency="IRR")
        WalletRepository.refresh_balances(payer_wallet)
        self.assertEqual(payer_wallet.available_balance_minor, 200000)

    def test_outbox_event_payload_matches_payment(self):
        result = self.service.pay_settlement_item(self.payer.identity_user_id, self.item.item_id, "event-check")
        outbox = OutboxMessage.objects.get(event_type="WalletSettlementPaid")
        self.assertEqual(outbox.payload["data"]["settlement_plan_item_id"], str(self.item.item_id))
        self.assertEqual(str(result["transaction_id"]), outbox.payload["data"]["wallet_transaction_id"])
