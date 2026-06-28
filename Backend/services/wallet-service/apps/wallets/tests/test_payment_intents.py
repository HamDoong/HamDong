
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from apps.wallets.domain.models import PaymentIntent, TopUp, WalletTransaction
from apps.wallets.infrastructure.repositories import WalletRepository
from apps.wallets.tests.helpers import api_client, auth_user, create_user_projection, get_or_create_wallet


class PaymentIntentApiTests(TestCase):
    def setUp(self):
        self.user = create_user_projection(art_name="owner_artist")
        self.other = create_user_projection(email="other@example.com", art_name="other_artist")
        get_or_create_wallet(self.user.identity_user_id)
        get_or_create_wallet(self.other.identity_user_id)

    def _create(self, user, **payload):
        data = {
            "purpose": "WALLET_TOP_UP",
            "amount_minor": 1000000,
            "currency": "IRR",
            "provider": "FAKE",
            "idempotency_key": "intent-1",
        }
        data.update(payload)
        return api_client(auth_user(user.identity_user_id, user.email)).post(
            "/api/v1/payments/intents/",
            data,
            format="json",
        )

    def test_create_payment_intent_success(self):
        response = self._create(self.user)
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["purpose"], "WALLET_TOP_UP")
        self.assertEqual(data["status"], "REDIRECT_REQUIRED")
        self.assertTrue(data["payment_url"].startswith("https://fake-gateway/pay/"))
        self.assertEqual(PaymentIntent.objects.count(), 1)
        self.assertEqual(TopUp.objects.count(), 1)

    def test_duplicate_idempotency_returns_same_intent(self):
        first = self._create(self.user, idempotency_key="same-key")
        second = self._create(self.user, idempotency_key="same-key")
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 201)
        self.assertEqual(first.json()["payment_intent_id"], second.json()["payment_intent_id"])
        self.assertEqual(PaymentIntent.objects.count(), 1)
        self.assertEqual(TopUp.objects.count(), 1)

    def test_positive_amount_required(self):
        response = self._create(self.user, amount_minor=0)
        self.assertEqual(response.status_code, 400)

    def test_negative_amount_rejected(self):
        response = self._create(self.user, amount_minor=-1)
        self.assertEqual(response.status_code, 400)

    def test_invalid_provider_rejected(self):
        response = self._create(self.user, provider="OTHER")
        self.assertEqual(response.status_code, 400)

    def test_invalid_currency_rejected(self):
        response = self._create(self.user, currency="USD")
        self.assertEqual(response.status_code, 400)

    def test_wallet_not_credited_before_verify(self):
        response = self._create(self.user, amount_minor=700000)
        self.assertEqual(response.status_code, 201)
        wallet = WalletRepository.get_for_user(self.user.identity_user_id, "IRR")
        WalletRepository.refresh_balances(wallet)
        self.assertEqual(wallet.available_balance_minor, 0)
        self.assertEqual(WalletTransaction.objects.count(), 0)

    def test_user_can_only_view_own_payment_intent(self):
        response = self._create(self.user)
        intent_id = response.json()["payment_intent_id"]
        ok = api_client(auth_user(self.user.identity_user_id, self.user.email)).get(
            f"/api/v1/payments/intents/{intent_id}/"
        )
        self.assertEqual(ok.status_code, 200)
        forbidden = api_client(auth_user(self.other.identity_user_id, self.other.email)).get(
            f"/api/v1/payments/intents/{intent_id}/"
        )
        self.assertEqual(forbidden.status_code, 404)

    def test_create_requires_authentication(self):
        response = api_client().post(
            "/api/v1/payments/intents/",
            {
                "purpose": "WALLET_TOP_UP",
                "amount_minor": 1000000,
                "currency": "IRR",
                "provider": "FAKE",
                "idempotency_key": "intent-1",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 401)

    def test_detail_returns_expired_status_after_expiration(self):
        response = self._create(self.user, idempotency_key="expiring")
        intent = PaymentIntent.objects.get(id=response.json()["payment_intent_id"])
        intent.expires_at = timezone.now() - timedelta(minutes=1)
        intent.save(update_fields=["expires_at", "updated_at"])
        detail = api_client(auth_user(self.user.identity_user_id, self.user.email)).get(
            f"/api/v1/payments/intents/{intent.id}/"
        )
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.json()["status"], "EXPIRED")
