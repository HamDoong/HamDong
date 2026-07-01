from __future__ import annotations

from unittest.mock import Mock, patch
from uuid import uuid4

import httpx
from django.test import TestCase, override_settings

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


def mocked_response(*, status_code=200, body=None):
    response = Mock()
    response.status_code = status_code
    response.json.return_value = body or {}
    return response


@override_settings(
    ZARINPAL_MERCHANT_ID="00000000-0000-0000-0000-000000000000",
    ZARINPAL_SANDBOX=True,
    ZARINPAL_CALLBACK_BASE_URL="http://localhost:8080",
    ZARINPAL_HTTP_TIMEOUT_SECONDS=10,
)
class ZarinpalPaymentGatewayApiTests(TestCase):
    def setUp(self):
        self.user = create_user_projection(art_name="wallet_owner", email="owner@example.com")
        self.other = create_user_projection(email="other@example.com", art_name="other_owner")
        get_or_create_wallet(self.user.identity_user_id)
        get_or_create_wallet(self.other.identity_user_id)

    def _create_payload(self, **overrides):
        payload = {
            "purpose": "WALLET_TOP_UP",
            "amount_minor": 1000000,
            "currency": "IRR",
            "provider": "ZARINPAL",
            "idempotency_key": "zarinpal-create-1",
        }
        payload.update(overrides)
        return payload

    def _request_success_body(self, authority="S123456789012345678901234567890123456"):
        return {
            "data": {
                "code": 100,
                "message": "Success",
                "authority": authority,
            },
            "errors": [],
        }

    def _verify_success_body(self, code=100):
        return {
            "data": {
                "code": code,
                "message": "Verified",
                "ref_id": 99887766,
                "card_pan": "6037****1234",
                "card_hash": "hash-value",
                "fee": 0,
                "fee_type": "Merchant",
            },
            "errors": [],
        }

    def _create_intent(self, user=None, **overrides):
        user = user or self.user
        payload = self._create_payload(**overrides)
        authority = overrides.pop("request_authority", f"S{uuid4().hex.upper()}")
        with patch(
            "apps.wallets.infrastructure.payment_providers.httpx.post",
            return_value=mocked_response(body=self._request_success_body(authority)),
        ) as mocked_post:
            response = api_client(auth_user(user.identity_user_id, user.email)).post(
                "/api/v1/payments/intents/",
                payload,
                format="json",
            )
        return response, mocked_post

    def _callback(self, *, provider="ZARINPAL", method="get", **payload):
        client = api_client()
        url = f"/api/v1/payments/gateway/{provider}/callback/"
        if method.lower() == "post":
            return client.post(url, payload, format="json")
        return client.get(url, payload)

    def _verify(self, *, user=None, provider="ZARINPAL", **payload):
        user = user or self.user
        return api_client(auth_user(user.identity_user_id, user.email)).post(
            f"/api/v1/payments/gateway/{provider}/verify/",
            payload,
            format="json",
        )

    def test_create_payment_intent_with_zarinpal_returns_redirect_and_authority(self):
        response, mocked_post = self._create_intent()
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["provider"], "ZARINPAL")
        self.assertEqual(data["status"], "REDIRECT_REQUIRED")
        self.assertTrue(data["payment_url"].startswith("https://sandbox.zarinpal.com/pg/StartPay/"))
        self.assertTrue(data["provider_reference"].startswith("S"))
        self.assertEqual(TopUp.objects.count(), 1)
        gateway_tx = GatewayTransaction.objects.get(payment_intent_id=data["payment_intent_id"])
        self.assertEqual(gateway_tx.provider_reference, data["provider_reference"])
        self.assertEqual(gateway_tx.provider, "ZARINPAL")
        wallet = WalletRepository.get_for_user(self.user.identity_user_id, "IRR")
        WalletRepository.refresh_balances(wallet)
        self.assertEqual(wallet.available_balance_minor, 0)
        request_payload = mocked_post.call_args.kwargs["json"]
        self.assertEqual(request_payload["amount"], 1000000)
        self.assertEqual(request_payload["currency"], "IRR")
        self.assertIn("payment_intent_id=", request_payload["callback_url"])
        self.assertNotIn("merchant_id", data)

    def test_create_intent_idempotency_returns_same_intent_for_zarinpal(self):
        first, _ = self._create_intent(idempotency_key="same-zarinpal-key")
        second, mocked_post = self._create_intent(idempotency_key="same-zarinpal-key")
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 201)
        self.assertEqual(first.json()["payment_intent_id"], second.json()["payment_intent_id"])
        self.assertEqual(PaymentIntent.objects.count(), 1)
        self.assertEqual(TopUp.objects.count(), 1)
        mocked_post.assert_not_called()

    def test_existing_fake_provider_still_works(self):
        response = api_client(auth_user(self.user.identity_user_id, self.user.email)).post(
            "/api/v1/payments/intents/",
            {
                "purpose": "WALLET_TOP_UP",
                "amount_minor": 500000,
                "currency": "IRR",
                "provider": "FAKE",
                "idempotency_key": "fake-still-works",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["provider"], "FAKE")
        self.assertTrue(response.json()["payment_url"].startswith("https://fake-gateway/pay/"))

    def test_callback_with_authority_and_status_ok_is_logged_without_credit(self):
        response, _ = self._create_intent(idempotency_key="zarinpal-callback-ok")
        intent_id = response.json()["payment_intent_id"]
        callback = self._callback(
            payment_intent_id=intent_id,
            Authority="S123456789012345678901234567890123456",
            Status="OK",
        )
        self.assertEqual(callback.status_code, 200)
        intent = PaymentIntent.objects.get(id=intent_id)
        top_up = TopUp.objects.get(payment_intent=intent)
        wallet = WalletRepository.get_for_user(self.user.identity_user_id, "IRR")
        WalletRepository.refresh_balances(wallet)
        self.assertEqual(wallet.available_balance_minor, 0)
        self.assertEqual(intent.status, "CALLBACK_RECEIVED")
        self.assertEqual(top_up.status, "PROCESSING")
        self.assertEqual(PaymentCallbackLog.objects.count(), 1)
        log = PaymentCallbackLog.objects.get()
        self.assertEqual(log.provider_reference, "S123456789012345678901234567890123456")
        self.assertEqual(log.payload["Authority"], "S123456789012345678901234567890123456")
        self.assertEqual(log.payload["Status"], "OK")
        self.assertEqual(WalletTransaction.objects.count(), 0)

    def test_callback_with_status_nok_marks_failed(self):
        response, _ = self._create_intent(idempotency_key="zarinpal-callback-nok")
        intent_id = response.json()["payment_intent_id"]
        callback = self._callback(
            payment_intent_id=intent_id,
            Authority="S123456789012345678901234567890123456",
            Status="NOK",
        )
        self.assertEqual(callback.status_code, 200)
        intent = PaymentIntent.objects.get(id=intent_id)
        top_up = TopUp.objects.get(payment_intent=intent)
        self.assertEqual(intent.status, "FAILED")
        self.assertEqual(top_up.status, "FAILED")
        self.assertEqual(WalletTransaction.objects.count(), 0)

    def test_callback_without_payment_intent_id_is_logged_and_returns_200(self):
        callback = self._callback(Authority="S123456789012345678901234567890123456", Status="OK")
        self.assertEqual(callback.status_code, 200)
        self.assertEqual(PaymentCallbackLog.objects.count(), 1)
        self.assertIsNone(PaymentCallbackLog.objects.get().payment_intent)

    def test_callback_authority_is_never_treated_as_payment_intent_id(self):
        response, _ = self._create_intent(idempotency_key="zarinpal-authority-not-intent")
        callback = self._callback(Authority="S123456789012345678901234567890123456", Status="OK")
        self.assertEqual(callback.status_code, 200)
        intent = PaymentIntent.objects.get(id=response.json()["payment_intent_id"])
        intent.refresh_from_db()
        self.assertEqual(intent.status, "REDIRECT_REQUIRED")

    def test_callback_duplicate_provider_reference_returns_conflict(self):
        first, _ = self._create_intent(idempotency_key="zarinpal-first")
        second, _ = self._create_intent(idempotency_key="zarinpal-second")
        ok = self._callback(
            payment_intent_id=first.json()["payment_intent_id"],
            Authority="S111111111111111111111111111111111111",
            Status="OK",
        )
        self.assertEqual(ok.status_code, 200)
        conflict = self._callback(
            payment_intent_id=second.json()["payment_intent_id"],
            Authority="S111111111111111111111111111111111111",
            Status="OK",
        )
        self.assertEqual(conflict.status_code, 409)

    def test_verify_success_credits_wallet_once_and_emits_outbox(self):
        response, _ = self._create_intent(idempotency_key="zarinpal-verify-success")
        intent_id = response.json()["payment_intent_id"]
        self._callback(
            payment_intent_id=intent_id,
            Authority="S123456789012345678901234567890123456",
            Status="OK",
        )
        with patch(
            "apps.wallets.infrastructure.payment_providers.httpx.post",
            return_value=mocked_response(body=self._verify_success_body(100)),
        ) as mocked_post:
            verify = self._verify(payment_intent_id=intent_id)
        self.assertEqual(verify.status_code, 200)
        payload = verify.json()
        self.assertEqual(payload["status"], "SUCCEEDED")
        self.assertIsNotNone(payload["wallet_transaction_id"])
        wallet = WalletRepository.get_for_user(self.user.identity_user_id, "IRR")
        WalletRepository.refresh_balances(wallet)
        self.assertEqual(wallet.available_balance_minor, 1000000)
        self.assertEqual(WalletTransaction.objects.filter(type="TOP_UP", status="COMPLETED").count(), 1)
        self.assertEqual(TopUp.objects.filter(status="COMPLETED").count(), 1)
        self.assertEqual(OutboxMessage.objects.filter(event_type="WalletTopUpCompleted").count(), 1)
        self.assertEqual(
            mocked_post.call_args.kwargs["json"],
            {
                "merchant_id": "00000000-0000-0000-0000-000000000000",
                "amount": 1000000,
                "authority": "S123456789012345678901234567890123456",
            },
        )

    def test_verify_twice_does_not_credit_wallet_twice(self):
        response, _ = self._create_intent(idempotency_key="zarinpal-verify-dup")
        intent_id = response.json()["payment_intent_id"]
        self._callback(
            payment_intent_id=intent_id,
            Authority="S123456789012345678901234567890123456",
            Status="OK",
        )
        with patch(
            "apps.wallets.infrastructure.payment_providers.httpx.post",
            return_value=mocked_response(body=self._verify_success_body(100)),
        ):
            first = self._verify(payment_intent_id=intent_id)
        with patch(
            "apps.wallets.infrastructure.payment_providers.httpx.post",
            return_value=mocked_response(body=self._verify_success_body(101)),
        ):
            second = self._verify(payment_intent_id=intent_id)
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        wallet = WalletRepository.get_for_user(self.user.identity_user_id, "IRR")
        WalletRepository.refresh_balances(wallet)
        self.assertEqual(wallet.available_balance_minor, 1000000)
        self.assertEqual(WalletTransaction.objects.filter(type="TOP_UP").count(), 1)

    def test_verify_code_101_is_treated_as_idempotent_success(self):
        response, _ = self._create_intent(idempotency_key="zarinpal-verify-101")
        intent_id = response.json()["payment_intent_id"]
        self._callback(
            payment_intent_id=intent_id,
            Authority="S101010101010101010101010101010101010",
            Status="OK",
        )
        with patch(
            "apps.wallets.infrastructure.payment_providers.httpx.post",
            return_value=mocked_response(body=self._verify_success_body(101)),
        ):
            verify = self._verify(payment_intent_id=intent_id)
        self.assertEqual(verify.status_code, 200)
        self.assertEqual(verify.json()["status"], "SUCCEEDED")
        self.assertEqual(WalletTransaction.objects.filter(type="TOP_UP").count(), 1)

    def test_verify_failure_code_minus_54_marks_failed_without_credit(self):
        response, _ = self._create_intent(idempotency_key="zarinpal-verify-fail")
        intent_id = response.json()["payment_intent_id"]
        self._callback(
            payment_intent_id=intent_id,
            Authority="S999999999999999999999999999999999999",
            Status="OK",
        )
        with patch(
            "apps.wallets.infrastructure.payment_providers.httpx.post",
            return_value=mocked_response(
                body={"data": {"code": -54, "message": "Invalid authority"}, "errors": []}
            ),
        ):
            verify = self._verify(payment_intent_id=intent_id)
        self.assertEqual(verify.status_code, 200)
        self.assertEqual(verify.json()["status"], "FAILED")
        self.assertEqual(WalletTransaction.objects.count(), 0)
        self.assertEqual(TopUp.objects.get(payment_intent_id=intent_id).status, "FAILED")
        self.assertEqual(GatewayTransaction.objects.get(payment_intent_id=intent_id).status, "FAILED")

    def test_verify_retryable_timeout_does_not_credit_wallet(self):
        response, _ = self._create_intent(idempotency_key="zarinpal-verify-timeout")
        intent_id = response.json()["payment_intent_id"]
        self._callback(
            payment_intent_id=intent_id,
            Authority="Stimeout0000000000000000000000000000000",
            Status="OK",
        )
        with patch(
            "apps.wallets.infrastructure.payment_providers.httpx.post",
            side_effect=httpx.TimeoutException("timeout"),
        ):
            verify = self._verify(
                payment_intent_id=intent_id,
                provider_reference="Stimeout0000000000000000000000000000000",
            )
        self.assertEqual(verify.status_code, 200)
        self.assertEqual(verify.json()["status"], "RETRYABLE")
        self.assertEqual(WalletTransaction.objects.count(), 0)
        self.assertEqual(GatewayTransaction.objects.get(payment_intent_id=intent_id).verification_attempts, 1)

    def test_verify_retryable_http_5xx_does_not_credit_wallet(self):
        response, _ = self._create_intent(idempotency_key="zarinpal-verify-500")
        intent_id = response.json()["payment_intent_id"]
        self._callback(
            payment_intent_id=intent_id,
            Authority="S500000000000000000000000000000000000",
            Status="OK",
        )
        with patch(
            "apps.wallets.infrastructure.payment_providers.httpx.post",
            return_value=mocked_response(status_code=503, body={"data": {"code": None, "message": "down"}}),
        ):
            verify = self._verify(payment_intent_id=intent_id)
        self.assertEqual(verify.status_code, 200)
        self.assertEqual(verify.json()["status"], "RETRYABLE")
        self.assertEqual(WalletTransaction.objects.count(), 0)

    def test_verify_requires_authentication_for_zarinpal(self):
        response, _ = self._create_intent(idempotency_key="zarinpal-auth")
        verify = api_client().post(
            "/api/v1/payments/gateway/ZARINPAL/verify/",
            {"payment_intent_id": response.json()["payment_intent_id"]},
            format="json",
        )
        self.assertEqual(verify.status_code, 401)

    def test_other_user_cannot_verify_someone_elses_zarinpal_intent(self):
        response, _ = self._create_intent(idempotency_key="zarinpal-owner-only")
        verify = self._verify(user=self.other, payment_intent_id=response.json()["payment_intent_id"])
        self.assertEqual(verify.status_code, 404)

    def test_verify_uses_database_amount_not_user_supplied_amount(self):
        response, _ = self._create_intent(idempotency_key="zarinpal-db-amount")
        intent_id = response.json()["payment_intent_id"]
        self._callback(
            payment_intent_id=intent_id,
            Authority="S777777777777777777777777777777777777",
            Status="OK",
            amount_minor=1,
        )
        with patch(
            "apps.wallets.infrastructure.payment_providers.httpx.post",
            return_value=mocked_response(body=self._verify_success_body(100)),
        ) as mocked_post:
            verify = self._verify(
                payment_intent_id=intent_id,
                provider_reference="S777777777777777777777777777777777777",
            )
        self.assertEqual(verify.status_code, 200)
        self.assertEqual(mocked_post.call_args.kwargs["json"]["amount"], 1000000)

    def test_callback_nok_prevents_verify_from_succeeding(self):
        response, _ = self._create_intent(idempotency_key="zarinpal-nok-no-verify")
        intent_id = response.json()["payment_intent_id"]
        self._callback(
            payment_intent_id=intent_id,
            Authority="S555555555555555555555555555555555555",
            Status="NOK",
        )
        with patch(
            "apps.wallets.infrastructure.payment_providers.httpx.post",
            return_value=mocked_response(body=self._verify_success_body(100)),
        ):
            verify = self._verify(payment_intent_id=intent_id)
        self.assertEqual(verify.status_code, 200)
        self.assertEqual(verify.json()["status"], "FAILED")
        self.assertEqual(WalletTransaction.objects.count(), 0)

    def test_create_request_failure_marks_intent_failed(self):
        with patch(
            "apps.wallets.infrastructure.payment_providers.httpx.post",
            return_value=mocked_response(status_code=400, body={"data": {"code": -54, "message": "bad request"}}),
        ):
            response = api_client(auth_user(self.user.identity_user_id, self.user.email)).post(
                "/api/v1/payments/intents/",
                self._create_payload(idempotency_key="zarinpal-request-failed"),
                format="json",
            )
        self.assertEqual(response.status_code, 400)
        intent = PaymentIntent.objects.get(idempotency_key="zarinpal-request-failed")
        self.assertEqual(intent.status, "FAILED")
        self.assertEqual(TopUp.objects.get(payment_intent=intent).status, "FAILED")
        self.assertEqual(GatewayTransaction.objects.get(payment_intent=intent).status, "FAILED")

    def test_swagger_schema_lists_zarinpal_and_callback_parameters(self):
        response = api_client().get("/api/schema/?format=json")
        self.assertEqual(response.status_code, 200)
        schema = response.json()
        provider_schema = schema["components"]["schemas"]["PaymentIntentCreate"]["properties"]["provider"]
        if "$ref" in provider_schema:
            enum_name = provider_schema["$ref"].split("/")[-1]
            create_enum = schema["components"]["schemas"][enum_name]["enum"]
        else:
            create_enum = provider_schema["enum"]
        self.assertIn("ZARINPAL", create_enum)
        callback_parameters = schema["paths"]["/api/v1/payments/gateway/{provider}/callback/"]["get"]["parameters"]
        callback_names = {item["name"] for item in callback_parameters}
        self.assertIn("Authority", callback_names)
        self.assertIn("Status", callback_names)

    def test_settings_defaults_are_sandbox_safe(self):
        from django.conf import settings

        self.assertTrue(settings.ZARINPAL_SANDBOX)
        self.assertEqual(settings.ZARINPAL_CALLBACK_BASE_URL, "http://localhost:8080")
        self.assertEqual(settings.ZARINPAL_HTTP_TIMEOUT_SECONDS, 10)
