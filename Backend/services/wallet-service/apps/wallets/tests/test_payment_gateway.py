
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from apps.wallets.domain.models import (
    GatewayTransaction,
    OutboxMessage,
    PaymentCallbackLog,
    PaymentIntent,
    TopUp,
    WalletTransaction,
)
from apps.wallets.infrastructure.repositories import WalletRepository
from apps.wallets.tests.helpers import api_client, auth_user, create_user_projection, get_or_create_wallet


class PaymentGatewayApiTests(TestCase):
    def setUp(self):
        self.user = create_user_projection(art_name="wallet_owner")
        self.other = create_user_projection(email="other@example.com", art_name="other_owner")
        get_or_create_wallet(self.user.identity_user_id)
        get_or_create_wallet(self.other.identity_user_id)

    def _create_intent(self, user=None, **payload):
        user = user or self.user
        data = {
            "purpose": "WALLET_TOP_UP",
            "amount_minor": 900000,
            "currency": "IRR",
            "provider": "FAKE",
            "idempotency_key": "pay-1",
        }
        data.update(payload)
        response = api_client(auth_user(user.identity_user_id, user.email)).post(
            "/api/v1/payments/intents/",
            data,
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        return response.json()

    def _callback(self, *, method="post", provider="FAKE", **payload):
        client = api_client()
        url = f"/api/v1/payments/gateway/{provider}/callback/"
        if method.lower() == "get":
            return client.get(url, payload)
        return client.post(url, payload, format="json")

    def _verify(self, *, user=None, provider="FAKE", **payload):
        user = user or self.user
        return api_client(auth_user(user.identity_user_id, user.email)).post(
            f"/api/v1/payments/gateway/{provider}/verify/",
            payload,
            format="json",
        )

    def test_callback_alone_does_not_credit_wallet(self):
        intent = self._create_intent()
        response = self._callback(
            payment_intent_id=intent["payment_intent_id"],
            provider_reference="ref-1",
            amount_minor=900000,
            currency="IRR",
            result="success",
        )
        self.assertEqual(response.status_code, 200)
        wallet = WalletRepository.get_for_user(self.user.identity_user_id, "IRR")
        WalletRepository.refresh_balances(wallet)
        self.assertEqual(wallet.available_balance_minor, 0)
        self.assertEqual(PaymentCallbackLog.objects.count(), 1)
        self.assertEqual(WalletTransaction.objects.count(), 0)

    def test_successful_callback_and_verify_credits_wallet(self):
        intent = self._create_intent(idempotency_key="pay-success")
        self._callback(
            payment_intent_id=intent["payment_intent_id"],
            provider_reference="ref-success",
            amount_minor=900000,
            currency="IRR",
            result="success",
        )
        verify = self._verify(payment_intent_id=intent["payment_intent_id"])
        self.assertEqual(verify.status_code, 200)
        data = verify.json()
        self.assertEqual(data["status"], "SUCCEEDED")
        wallet = WalletRepository.get_for_user(self.user.identity_user_id, "IRR")
        WalletRepository.refresh_balances(wallet)
        self.assertEqual(wallet.available_balance_minor, 900000)
        self.assertEqual(WalletTransaction.objects.filter(type="TOP_UP", status="COMPLETED").count(), 1)
        self.assertEqual(TopUp.objects.filter(status="COMPLETED").count(), 1)
        self.assertEqual(OutboxMessage.objects.filter(event_type="WalletTopUpCompleted").count(), 1)

    def test_duplicate_callback_and_verify_do_not_credit_twice(self):
        intent = self._create_intent(idempotency_key="dup-verify")
        payload = {
            "payment_intent_id": intent["payment_intent_id"],
            "provider_reference": "ref-dup",
            "amount_minor": 900000,
            "currency": "IRR",
            "result": "success",
        }
        self._callback(**payload)
        self._callback(**payload)
        first = self._verify(payment_intent_id=intent["payment_intent_id"])
        second = self._verify(payment_intent_id=intent["payment_intent_id"])
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        wallet = WalletRepository.get_for_user(self.user.identity_user_id, "IRR")
        WalletRepository.refresh_balances(wallet)
        self.assertEqual(wallet.available_balance_minor, 900000)
        self.assertEqual(WalletTransaction.objects.filter(type="TOP_UP").count(), 1)
        self.assertEqual(PaymentCallbackLog.objects.count(), 2)

    def test_provider_amount_mismatch_marks_failed(self):
        intent = self._create_intent(idempotency_key="mismatch")
        self._callback(
            payment_intent_id=intent["payment_intent_id"],
            provider_reference="ref-mismatch",
            amount_minor=800000,
            currency="IRR",
            result="success",
        )
        verify = self._verify(payment_intent_id=intent["payment_intent_id"])
        self.assertEqual(verify.status_code, 200)
        self.assertEqual(verify.json()["status"], "FAILED")
        wallet = WalletRepository.get_for_user(self.user.identity_user_id, "IRR")
        WalletRepository.refresh_balances(wallet)
        self.assertEqual(wallet.available_balance_minor, 0)
        self.assertEqual(PaymentIntent.objects.get(id=intent["payment_intent_id"]).status, "FAILED")

    def test_provider_timeout_becomes_retryable(self):
        intent = self._create_intent(idempotency_key="timeout")
        self._callback(
            payment_intent_id=intent["payment_intent_id"],
            provider_reference="timeout-ref-1",
            amount_minor=900000,
            currency="IRR",
            result="timeout",
        )
        verify = self._verify(payment_intent_id=intent["payment_intent_id"])
        self.assertEqual(verify.status_code, 200)
        self.assertEqual(verify.json()["status"], "RETRYABLE")
        self.assertEqual(PaymentIntent.objects.get(id=intent["payment_intent_id"]).status, "RETRYABLE")
        self.assertEqual(WalletTransaction.objects.count(), 0)

    def test_expired_payment_intent_cannot_be_verified(self):
        intent = self._create_intent(idempotency_key="expired")
        payment_intent = PaymentIntent.objects.get(id=intent["payment_intent_id"])
        payment_intent.expires_at = timezone.now() - timedelta(minutes=1)
        payment_intent.save(update_fields=["expires_at", "updated_at"])
        verify = self._verify(payment_intent_id=intent["payment_intent_id"])
        self.assertEqual(verify.status_code, 409)
        self.assertEqual(PaymentIntent.objects.get(id=intent["payment_intent_id"]).status, "EXPIRED")

    def test_duplicate_provider_reference_rejected(self):
        first = self._create_intent(idempotency_key="first-intent")
        second = self._create_intent(idempotency_key="second-intent")
        self._callback(
            payment_intent_id=first["payment_intent_id"],
            provider_reference="shared-ref",
            amount_minor=900000,
            currency="IRR",
            result="success",
        )
        verify_first = self._verify(payment_intent_id=first["payment_intent_id"])
        self.assertEqual(verify_first.status_code, 200)
        conflict = self._callback(
            payment_intent_id=second["payment_intent_id"],
            provider_reference="shared-ref",
            amount_minor=900000,
            currency="IRR",
            result="success",
        )
        self.assertEqual(conflict.status_code, 409)

    def test_verify_requires_authentication(self):
        intent = self._create_intent(idempotency_key="need-auth")
        response = api_client().post(
            "/api/v1/payments/gateway/FAKE/verify/",
            {"payment_intent_id": intent["payment_intent_id"]},
            format="json",
        )
        self.assertEqual(response.status_code, 401)

    def test_other_user_cannot_verify_someone_else_intent(self):
        intent = self._create_intent(idempotency_key="owner-only")
        response = self._verify(user=self.other, payment_intent_id=intent["payment_intent_id"])
        self.assertEqual(response.status_code, 404)

    def test_swagger_includes_payment_paths(self):
        response = api_client().get("/api/schema/?format=json")
        self.assertEqual(response.status_code, 200)
        schema = response.json()
        self.assertIn("/api/v1/payments/intents/", schema["paths"])
        self.assertIn("/api/v1/payments/intents/{payment_intent_id}/", schema["paths"])
        self.assertIn("/api/v1/payments/gateway/{provider}/callback/", schema["paths"])
        self.assertIn("/api/v1/payments/gateway/{provider}/verify/", schema["paths"])

    def test_gateway_detail_does_not_expose_secret_fields(self):
        intent = self._create_intent(idempotency_key="no-secret")
        detail = api_client(auth_user(self.user.identity_user_id, self.user.email)).get(
            f"/api/v1/payments/intents/{intent['payment_intent_id']}/"
        )
        self.assertEqual(detail.status_code, 200)
        payload = detail.json()
        self.assertNotIn("provider_secret", payload)
        self.assertNotIn("secret_key", payload)
        self.assertNotIn("api_key", payload)
