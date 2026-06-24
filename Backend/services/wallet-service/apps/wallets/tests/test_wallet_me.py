
from django.test import TestCase

from apps.wallets.domain.models import CurrencyChoices, InboxMessage, UserProjection, Wallet
from apps.wallets.infrastructure.rabbitmq_consumer import WalletEventConsumer
from apps.wallets.tests.helpers import api_client, auth_user, create_user_projection, identity_event, seed_available_balance


class WalletMeApiTests(TestCase):
    def test_no_token_returns_401(self):
        response = self.client.get("/api/v1/wallets/me/")
        self.assertEqual(response.status_code, 401)

    def test_user_sees_only_own_wallet(self):
        owner = create_user_projection(art_name="owner_artist")
        other = create_user_projection(email="other@example.com", art_name="other_artist")
        seed_available_balance(owner.identity_user_id, 1200000)
        seed_available_balance(other.identity_user_id, 800000)

        response = api_client(auth_user(owner.identity_user_id, owner.email)).get("/api/v1/wallets/me/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["currency"], CurrencyChoices.IRR)
        self.assertEqual(data["available_balance_minor"], 1200000)
        self.assertEqual(str(data["id"]), str(Wallet.objects.get(user_id=owner.identity_user_id, currency=CurrencyChoices.IRR).id))

    def test_new_wallet_starts_at_zero(self):
        user = create_user_projection()
        response = api_client(auth_user(user.identity_user_id, user.email)).get("/api/v1/wallets/me/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["available_balance_minor"], 0)
        self.assertEqual(data["reserved_balance_minor"], 0)
        self.assertEqual(data["total_inflow_minor"], 0)
        self.assertEqual(data["total_outflow_minor"], 0)

    def test_balance_equals_ledger(self):
        user = create_user_projection()
        wallet, _ = seed_available_balance(user.identity_user_id, 1500000)
        response = api_client(auth_user(user.identity_user_id, user.email)).get("/api/v1/wallets/me/")
        self.assertEqual(response.status_code, 200)
        wallet.refresh_from_db()
        self.assertEqual(response.json()["available_balance_minor"], wallet.available_balance_minor)
        self.assertEqual(wallet.available_balance_minor, 1500000)

    def test_duplicate_user_event_does_not_create_second_wallet(self):
        user_id = "f2b9f5a1-f493-4b7c-99d3-0a56465aa111"
        payload = identity_event(
            data={
                "user_id": user_id,
                "email": "user@example.com",
                "art_name": "artist",
                "role": "USER",
                "is_active": True,
            }
        )
        consumer = WalletEventConsumer()
        consumer.process_identity_payload(payload)
        consumer.process_identity_payload(payload)
        self.assertEqual(UserProjection.objects.filter(identity_user_id=user_id).count(), 1)
        self.assertEqual(InboxMessage.objects.filter(event_id=payload["event_id"]).count(), 1)

    def test_swagger_documents_endpoint(self):
        response = self.client.get("/api/schema/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("/api/v1/wallets/me/", response.content.decode("utf-8"))
