
from django.test import TestCase
from unittest.mock import patch

from apps.wallets.application.wallet_service import WalletService
from apps.wallets.domain.models import Wallet, WalletTransaction, Withdrawal, WithdrawalStatusChoices
from apps.wallets.infrastructure.repositories import WalletRepository
from apps.wallets.tests.helpers import api_client, auth_user, create_user_projection, seed_available_balance


VALID_CARD = {
    "id": "11111111-1111-1111-1111-111111111111",
    "masked_card_number": "6037******1234",
    "card_number_last4": "1234",
    "holder_name": "User",
    "bank_name": "Bank",
    "is_default": True,
    "is_active": True,
    "type": "BANK_CARD",
    "card_number": "6037999912341234",
}


class WalletWithdrawalApiTests(TestCase):
    def setUp(self):
        self.user = create_user_projection(art_name="withdraw_artist")
        self.other = create_user_projection(email="other@example.com", art_name="other_artist")
        seed_available_balance(self.user.identity_user_id, 1000000)
        self.client_auth = api_client(auth_user(self.user.identity_user_id, self.user.email))

    @patch("apps.wallets.application.wallet_service.IdentityBankCardClient.resolve_payment_context_cards", return_value=[VALID_CARD])
    def test_sufficient_balance_creates_withdrawal(self, _mock_cards):
        response = self.client_auth.post(
            "/api/v1/wallets/me/withdrawals/",
            {
                "amount_minor": 500000,
                "currency": "IRR",
                "payment_method_id": VALID_CARD["id"],
                "idempotency_key": "wd-1",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "PENDING")
        wallet = Wallet.objects.get(user_id=self.user.identity_user_id, currency="IRR")
        WalletRepository.refresh_balances(wallet)
        self.assertEqual(wallet.available_balance_minor, 500000)
        self.assertEqual(wallet.reserved_balance_minor, 500000)

    @patch("apps.wallets.application.wallet_service.IdentityBankCardClient.resolve_payment_context_cards", return_value=[VALID_CARD])
    def test_duplicate_idempotency_key_does_not_create_second_withdrawal(self, _mock_cards):
        first = self.client_auth.post("/api/v1/wallets/me/withdrawals/", {"amount_minor": 100000, "currency": "IRR", "payment_method_id": VALID_CARD["id"], "idempotency_key": "wd-dup"}, format="json")
        second = self.client_auth.post("/api/v1/wallets/me/withdrawals/", {"amount_minor": 100000, "currency": "IRR", "payment_method_id": VALID_CARD["id"], "idempotency_key": "wd-dup"}, format="json")
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(Withdrawal.objects.count(), 1)

    @patch("apps.wallets.application.wallet_service.IdentityBankCardClient.resolve_payment_context_cards", return_value=[VALID_CARD])
    def test_insufficient_balance_rejected(self, _mock_cards):
        response = self.client_auth.post("/api/v1/wallets/me/withdrawals/", {"amount_minor": 5000000, "currency": "IRR", "payment_method_id": VALID_CARD["id"], "idempotency_key": "wd-big"}, format="json")
        self.assertEqual(response.status_code, 409)

    @patch("apps.wallets.application.wallet_service.IdentityBankCardClient.resolve_payment_context_cards", return_value=[])
    def test_other_user_payment_method_rejected(self, _mock_cards):
        response = self.client_auth.post("/api/v1/wallets/me/withdrawals/", {"amount_minor": 100000, "currency": "IRR", "payment_method_id": VALID_CARD["id"], "idempotency_key": "wd-card"}, format="json")
        self.assertEqual(response.status_code, 400)

    @patch("apps.wallets.application.wallet_service.IdentityBankCardClient.resolve_payment_context_cards", return_value=[{**VALID_CARD, "is_active": False}])
    def test_deleted_or_inactive_card_rejected(self, _mock_cards):
        response = self.client_auth.post("/api/v1/wallets/me/withdrawals/", {"amount_minor": 100000, "currency": "IRR", "payment_method_id": VALID_CARD["id"], "idempotency_key": "wd-inactive"}, format="json")
        self.assertEqual(response.status_code, 400)

    @patch("apps.wallets.application.wallet_service.IdentityBankCardClient.resolve_payment_context_cards", return_value=[VALID_CARD])
    def test_cancel_pending_succeeds(self, _mock_cards):
        create = self.client_auth.post("/api/v1/wallets/me/withdrawals/", {"amount_minor": 200000, "currency": "IRR", "payment_method_id": VALID_CARD["id"], "idempotency_key": "wd-cancel"}, format="json")
        withdrawal_id = create.json()["id"]
        cancel = self.client_auth.post(f"/api/v1/wallets/me/withdrawals/{withdrawal_id}/cancel/")
        self.assertEqual(cancel.status_code, 200)
        self.assertEqual(cancel.json()["status"], "CANCELLED")
        wallet = Wallet.objects.get(user_id=self.user.identity_user_id, currency="IRR")
        WalletRepository.refresh_balances(wallet)
        self.assertEqual(wallet.available_balance_minor, 1000000)
        self.assertEqual(wallet.reserved_balance_minor, 0)

    @patch("apps.wallets.application.wallet_service.IdentityBankCardClient.resolve_payment_context_cards", return_value=[VALID_CARD])
    def test_cancel_processing_rejected(self, _mock_cards):
        create = self.client_auth.post("/api/v1/wallets/me/withdrawals/", {"amount_minor": 200000, "currency": "IRR", "payment_method_id": VALID_CARD["id"], "idempotency_key": "wd-processing"}, format="json")
        withdrawal = Withdrawal.objects.get(id=create.json()["id"])
        withdrawal.status = WithdrawalStatusChoices.PROCESSING
        withdrawal.save(update_fields=["status", "updated_at"])
        cancel = self.client_auth.post(f"/api/v1/wallets/me/withdrawals/{withdrawal.id}/cancel/")
        self.assertEqual(cancel.status_code, 409)

    @patch("apps.wallets.application.wallet_service.IdentityBankCardClient.resolve_payment_context_cards", return_value=[VALID_CARD])
    def test_user_cannot_see_another_user_withdrawal(self, _mock_cards):
        own = self.client_auth.post("/api/v1/wallets/me/withdrawals/", {"amount_minor": 100000, "currency": "IRR", "payment_method_id": VALID_CARD["id"], "idempotency_key": "wd-own"}, format="json")
        other_client = api_client(auth_user(self.other.identity_user_id, self.other.email))
        response = other_client.get(f"/api/v1/wallets/me/withdrawals/{own.json()['id']}/")
        self.assertEqual(response.status_code, 404)

    @patch("apps.wallets.application.wallet_service.IdentityBankCardClient.resolve_payment_context_cards", return_value=[VALID_CARD])
    def test_swagger_documents_withdrawals(self, _mock_cards):
        response = self.client.get("/api/schema/")
        self.assertEqual(response.status_code, 200)
        schema = response.content.decode("utf-8")
        self.assertIn("/api/v1/wallets/me/withdrawals/", schema)
        self.assertIn("/api/v1/wallets/me/withdrawals/{withdrawal_id}/cancel/", schema)


class WalletWithdrawalServiceTests(TestCase):
    @patch("apps.wallets.application.wallet_service.IdentityBankCardClient.resolve_payment_context_cards", return_value=[VALID_CARD])
    def test_failure_releases_reserved(self, _mock_cards):
        user = create_user_projection()
        seed_available_balance(user.identity_user_id, 600000)
        service = WalletService()
        created = service.create_withdrawal(
            user.identity_user_id,
            amount_minor=300000,
            currency="IRR",
            payment_method_id=VALID_CARD["id"],
            idempotency_key="wd-fail",
        )
        failed = service.fail_withdrawal(created["id"], "provider failed")
        self.assertEqual(failed["status"], "FAILED")
        wallet = Wallet.objects.get(user_id=user.identity_user_id, currency="IRR")
        WalletRepository.refresh_balances(wallet)
        self.assertEqual(wallet.available_balance_minor, 600000)
        self.assertEqual(wallet.reserved_balance_minor, 0)
