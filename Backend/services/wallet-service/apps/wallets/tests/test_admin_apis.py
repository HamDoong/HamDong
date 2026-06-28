
from __future__ import annotations

from datetime import timedelta

from django.test import TestCase, override_settings
from django.utils import timezone

from apps.wallets.domain.models import PaymentIntent, WalletTransaction
from apps.wallets.tests.helpers import api_client, auth_user, create_user_projection, get_or_create_wallet


@override_settings(EXPOSE_API_DOCS=True)
class AdminWalletApiTests(TestCase):
    def setUp(self):
        self.admin = auth_user(role="ADMIN", email="admin@example.com")
        self.user = auth_user(role="USER", email="user@example.com")
        self.owner = create_user_projection(art_name="wallet_owner", email="wallet@example.com")
        self.wallet = get_or_create_wallet(self.owner.identity_user_id)
        self.tx = WalletTransaction.objects.create(
            wallet=self.wallet,
            type="TOP_UP",
            status="COMPLETED",
            direction="IN",
            amount_minor=1000000,
            currency="IRR",
            idempotency_key="admin-tx",
            reference_type="PAYMENT_INTENT",
            completed_at=timezone.now(),
        )
        self.payment = PaymentIntent.objects.create(
            wallet=self.wallet,
            purpose="WALLET_TOP_UP",
            amount_minor=1000000,
            currency="IRR",
            provider="FAKE",
            idempotency_key="admin-pay",
            status="SUCCEEDED",
            payment_url="https://example.com/pay",
            expires_at=timezone.now() + timedelta(hours=1),
            provider_reference="provider-ref",
            metadata={"provider_secret": "do-not-show"},
        )
        now = timezone.now()
        WalletTransaction.objects.filter(id=self.tx.id).update(created_at=now - timedelta(days=1), updated_at=now - timedelta(days=1))
        self.tx.refresh_from_db()

    def test_missing_token_returns_401(self):
        response = api_client().get("/api/v1/admin/wallet-transactions/")
        self.assertEqual(response.status_code, 401)

    def test_normal_user_gets_403(self):
        response = api_client(self.user).get("/api/v1/admin/wallet-transactions/")
        self.assertEqual(response.status_code, 403)

    def test_admin_can_list_transactions_and_payments(self):
        response = api_client(self.admin).get(f"/api/v1/admin/wallet-transactions/?user_id={self.owner.identity_user_id}&status=COMPLETED")
        self.assertEqual(response.status_code, 200)
        payload = response.json()["results"][0]
        self.assertEqual(payload["id"], str(self.tx.id))
        self.assertEqual(payload["user_id"], str(self.owner.identity_user_id))
        self.assertNotIn("provider_secret", str(payload))

        pay_response = api_client(self.admin).get(f"/api/v1/admin/payments/?user_id={self.owner.identity_user_id}&provider=FAKE&purpose=WALLET_TOP_UP")
        self.assertEqual(pay_response.status_code, 200)
        pay_payload = pay_response.json()["results"][0]
        self.assertEqual(pay_payload["id"], str(self.payment.id))
        self.assertNotIn("payment_url", pay_payload)
        self.assertNotIn("provider_reference", pay_payload)

    def test_schema_contains_admin_paths(self):
        response = api_client(self.admin).get("/api/schema/?format=json")
        self.assertEqual(response.status_code, 200)
        paths = response.json()["paths"]
        self.assertIn("/api/v1/admin/wallet-transactions/", paths)
        self.assertIn("/api/v1/admin/payments/", paths)
