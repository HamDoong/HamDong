
from django.test import TestCase
from unittest.mock import patch

from apps.wallets.domain.models import OutboxMessage, OutboxMessageStatusChoices
from apps.wallets.infrastructure.outbox_dispatcher import OutboxDispatcher
from apps.wallets.infrastructure.repositories import OutboxRepository


class WalletOutboxDispatcherTests(TestCase):
    def test_outbox_dispatcher_marks_message_published(self):
        message = OutboxRepository.create(
            event_type="WalletSettlementPaid",
            routing_key="wallet.settlement.paid",
            payload={
                "event_id": "11111111-1111-1111-1111-111111111111",
                "event_type": "WalletSettlementPaid",
                "event_version": 1,
                "occurred_at": "2026-06-20T12:00:00Z",
                "source_service": "wallet-service",
                "correlation_id": "22222222-2222-2222-2222-222222222222",
                "causation_id": "22222222-2222-2222-2222-222222222222",
                "routing_key": "wallet.settlement.paid",
                "data": {"settlement_plan_item_id": "33333333-3333-3333-3333-333333333333"},
            },
        )
        with patch("apps.wallets.infrastructure.outbox_dispatcher.RabbitMQPublisher.publish_message", return_value=True):
            dispatched = OutboxDispatcher().dispatch()
        self.assertEqual(dispatched, 1)
        message.refresh_from_db()
        self.assertEqual(message.status, OutboxMessageStatusChoices.PUBLISHED)
