import uuid
from types import SimpleNamespace
from unittest.mock import ANY, Mock, patch

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.settlements.application.debt_service import DebtService
from apps.settlements.application.settlement_service import SettlementService
from apps.settlements.domain.models import (
    DebtLedgerEntry,
    DebtLedgerEntryTypeChoices,
    DebtLedgerStatusChoices,
    GroupMemberProjection,
    GroupMemberStatusChoices,
    GroupProjection,
    GroupStatusChoices,
    ManualSettlementStatusChoices,
    UserProjection,
)
from apps.settlements.domain.rules import (
    InvalidSettlementAmountError,
    InvalidSettlementParticipantError,
    InvalidSettlementStatusError,
    NotGroupMemberError,
    SettlementPermissionDeniedError,
)
from apps.settlements.infrastructure.rabbitmq_consumer import SettlementEventConsumer
from apps.settlements.infrastructure.repositories import (
    ExpenseParticipantProjectionRepository,
    ExpenseProjectionRepository,
    ManualSettlementRepository,
)


def create_group(group_id=None, owner_user_id=None, title="Group A"):
    group_id = group_id or uuid.uuid4()
    owner_user_id = owner_user_id or uuid.uuid4()
    return GroupProjection.objects.create(
        group_id=group_id,
        title=title,
        group_type="GENERAL",
        status=GroupStatusChoices.ACTIVE,
        created_by_user_id=owner_user_id,
        member_count=0,
    )


def create_member(
    group_id,
    user_id=None,
    status=GroupMemberStatusChoices.ACTIVE,
    email="+989121234567",
    role="MEMBER",
):
    user_id = user_id or uuid.uuid4()
    return GroupMemberProjection.objects.create(
        group_id=group_id,
        user_id=user_id,
        email=email,
        art_name_snapshot="Member",
        role=role,
        status=status,
    )


class DebtServiceTests(TestCase):
    def setUp(self):
        self.publisher = Mock()
        self.balance_service = Mock()
        self.balance_service.render_group_balances.return_value = {"balances": []}
        self.debt_service = DebtService(
            publisher=self.publisher, balance_service=self.balance_service
        )
        self.group = create_group()
        self.payer = create_member(self.group.group_id)
        self.member_a = create_member(self.group.group_id)
        self.member_b = create_member(self.group.group_id)

    def _expense_payload(
        self, expense_id=None, participants=None, version=1, total_amount_minor=3000
    ):
        expense_id = expense_id or uuid.uuid4()
        participants = participants or [
            {
                "user_id": str(self.payer.user_id),
                "total_share_minor": 1000,
                "base_share_minor": 1000,
                "tax_share_minor": 0,
                "service_fee_share_minor": 0,
            },
            {
                "user_id": str(self.member_a.user_id),
                "total_share_minor": 1000,
                "base_share_minor": 1000,
                "tax_share_minor": 0,
                "service_fee_share_minor": 0,
            },
            {
                "user_id": str(self.member_b.user_id),
                "total_share_minor": 1000,
                "base_share_minor": 1000,
                "tax_share_minor": 0,
                "service_fee_share_minor": 0,
            },
        ]
        return {
            "expense_id": str(expense_id),
            "group_id": str(self.group.group_id),
            "created_by_user_id": str(self.payer.user_id),
            "payer_user_id": str(self.payer.user_id),
            "currency": "IRR",
            "base_amount_minor": total_amount_minor,
            "tax_amount_minor": 0,
            "service_fee_amount_minor": 0,
            "total_amount_minor": total_amount_minor,
            "expense_version": version,
            "participants": participants,
        }

    def test_expense_created_creates_projection_and_participants_and_debt_entries(self):
        payload = self._expense_payload()
        expense, entries = self.debt_service.handle_expense_created(payload)

        self.assertIsNotNone(ExpenseProjectionRepository.get(payload["expense_id"]))
        self.assertEqual(
            ExpenseParticipantProjectionRepository.list_for_expense(
                payload["expense_id"]
            ).count(),
            3,
        )
        self.assertEqual(len(entries), 2)
        self.assertFalse(
            any(
                entry.debtor_user_id == self.payer.user_id
                and entry.creditor_user_id == self.payer.user_id
                for entry in entries
            )
        )
        self.balance_service.recalculate_group.assert_called_once_with(
            expense.group_id, currency="IRR"
        )
        published_types = [
            call.args[0] for call in self.publisher.publish.call_args_list
        ]
        self.assertIn("DebtLedgerUpdated", published_types)
        self.assertIn("BalanceRecalculated", published_types)

    def test_expense_updated_reverses_previous_entries_and_creates_new_entries(self):
        payload = self._expense_payload()
        expense, _ = self.debt_service.handle_expense_created(payload)

        updated_payload = self._expense_payload(
            expense_id=payload["expense_id"],
            version=2,
            participants=[
                {
                    "user_id": str(self.payer.user_id),
                    "total_share_minor": 1500,
                    "base_share_minor": 1500,
                    "tax_share_minor": 0,
                    "service_fee_share_minor": 0,
                },
                {
                    "user_id": str(self.member_a.user_id),
                    "total_share_minor": 1500,
                    "base_share_minor": 1500,
                    "tax_share_minor": 0,
                    "service_fee_share_minor": 0,
                },
            ],
            total_amount_minor=3000,
        )
        self.balance_service.reset_mock()
        self.publisher.reset_mock()
        self.debt_service.handle_expense_updated(updated_payload)

        reversed_count = DebtLedgerEntry.objects.filter(
            source_expense_id=expense.expense_id,
            status=DebtLedgerStatusChoices.REVERSED,
        ).count()
        active_count = DebtLedgerEntry.objects.filter(
            source_expense_id=expense.expense_id, status=DebtLedgerStatusChoices.ACTIVE
        ).count()
        self.assertGreaterEqual(reversed_count, 2)
        self.assertEqual(active_count, 1)
        self.balance_service.recalculate_group.assert_called_once_with(
            expense.group_id, currency="IRR"
        )
        published_types = [
            call.args[0] for call in self.publisher.publish.call_args_list
        ]
        self.assertIn("DebtLedgerUpdated", published_types)
        self.assertIn("BalanceRecalculated", published_types)

    def test_expense_deleted_reverses_active_entries_and_recalculates(self):
        payload = self._expense_payload()
        expense, _ = self.debt_service.handle_expense_created(payload)

        self.balance_service.reset_mock()
        self.publisher.reset_mock()
        self.debt_service.handle_expense_deleted(
            {"expense_id": str(expense.expense_id)}
        )

        self.assertEqual(
            DebtLedgerEntry.objects.filter(
                source_expense_id=expense.expense_id,
                status=DebtLedgerStatusChoices.ACTIVE,
            ).count(),
            0,
        )
        self.assertGreaterEqual(
            DebtLedgerEntry.objects.filter(
                source_expense_id=expense.expense_id,
                status=DebtLedgerStatusChoices.REVERSED,
            ).count(),
            1,
        )
        self.balance_service.recalculate_group.assert_called_once_with(
            expense.group_id, currency="IRR"
        )
        published_types = [
            call.args[0] for call in self.publisher.publish.call_args_list
        ]
        self.assertIn("DebtLedgerUpdated", published_types)
        self.assertIn("BalanceRecalculated", published_types)


class SettlementApiTests(TestCase):
    def setUp(self):
        self.user = SimpleNamespace(sub=uuid.uuid4(), is_authenticated=True)
        self.client = APIClient()
        self.group = create_group(owner_user_id=self.user.sub)
        create_member(self.group.group_id, user_id=self.user.sub)
        self.other = create_member(self.group.group_id)
        DebtLedgerEntry.objects.create(
            group_id=self.group.group_id,
            source_expense_id=uuid.uuid4(),
            source_expense_version=1,
            debtor_user_id=self.user.sub,
            creditor_user_id=self.other.user_id,
            amount_minor=1000,
            currency="IRR",
            entry_type=DebtLedgerEntryTypeChoices.EXPENSE_SHARE,
            status=DebtLedgerStatusChoices.ACTIVE,
        )
        DebtLedgerEntry.objects.create(
            group_id=self.group.group_id,
            source_expense_id=uuid.uuid4(),
            source_expense_version=1,
            debtor_user_id=self.other.user_id,
            creditor_user_id=self.user.sub,
            amount_minor=500,
            currency="IRR",
            entry_type=DebtLedgerEntryTypeChoices.EXPENSE_SHARE,
            status=DebtLedgerStatusChoices.REVERSED,
        )

    def test_group_balances_endpoint_returns_payload(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(
            reverse("group_balances", kwargs={"group_id": self.group.group_id})
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("balances", response.json())

    def test_group_balances_denies_non_member(self):
        non_member = SimpleNamespace(sub=uuid.uuid4(), is_authenticated=True)
        self.client.force_authenticate(user=non_member)
        response = self.client.get(
            reverse("group_balances", kwargs={"group_id": self.group.group_id})
        )
        self.assertEqual(response.status_code, 403)

    def test_group_balances_denies_left_member(self):
        left_user_id = uuid.uuid4()
        create_member(
            self.group.group_id,
            user_id=left_user_id,
            status=GroupMemberStatusChoices.LEFT,
        )
        self.client.force_authenticate(
            user=SimpleNamespace(sub=left_user_id, is_authenticated=True)
        )
        response = self.client.get(
            reverse("group_balances", kwargs={"group_id": self.group.group_id})
        )
        self.assertEqual(response.status_code, 403)

    def test_my_balance_endpoint_returns_current_user_balance(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(
            reverse("my_balance", kwargs={"group_id": self.group.group_id})
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["user_id"], str(self.user.sub))

    def test_group_debts_endpoint_returns_only_active_debts(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(
            reverse("group_debts", kwargs={"group_id": self.group.group_id})
        )
        self.assertEqual(response.status_code, 200)
        debts = response.json()["debts"]
        self.assertEqual(len(debts), 1)
        self.assertEqual(debts[0]["status"], "ACTIVE")

    def test_create_manual_settlement_returns_201(self):
        self.client.force_authenticate(user=self.user)
        with patch(
            "apps.settlements.application.settlement_service.RabbitMQPublisher.publish",
            return_value=True,
        ):
            response = self.client.post(
                reverse("group_settlements", kwargs={"group_id": self.group.group_id}),
                data={
                    "receiver_user_id": str(self.other.user_id),
                    "amount_minor": 1200,
                    "currency": "IRR",
                    "description": "Dinner",
                },
                content_type="application/json",
            )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["status"], "PENDING_CONFIRMATION")


class SettlementWorkflowServiceTests(TestCase):
    def setUp(self):
        self.publisher = Mock()
        self.balance_service = Mock()
        self.balance_service.render_group_balances.return_value = {"balances": []}
        self.debt_service = DebtService(
            publisher=self.publisher, balance_service=self.balance_service
        )
        self.service = SettlementService(
            publisher=self.publisher,
            debt_service=self.debt_service,
            balance_service=self.balance_service,
        )
        self.group = create_group()
        self.payer = create_member(self.group.group_id)
        self.receiver = create_member(self.group.group_id)

    def test_create_settlement_success_and_event_published(self):
        settlement = self.service.create_manual_settlement(
            self.group.group_id,
            self.payer.user_id,
            {
                "receiver_user_id": str(self.receiver.user_id),
                "amount_minor": 1000,
                "currency": "IRR",
                "description": "Taxi",
            },
        )
        self.assertEqual(
            settlement.status, ManualSettlementStatusChoices.PENDING_CONFIRMATION
        )
        self.assertEqual(settlement.created_by_user_id, self.payer.user_id)
        self.publisher.publish.assert_any_call(
            "SettlementCreated", ANY, "settlement.created"
        )

    def test_create_settlement_same_payer_receiver_fails(self):
        with self.assertRaises(InvalidSettlementParticipantError):
            self.service.create_manual_settlement(
                self.group.group_id,
                self.payer.user_id,
                {
                    "receiver_user_id": str(self.payer.user_id),
                    "amount_minor": 1000,
                    "currency": "IRR",
                },
            )

    def test_create_settlement_non_member_receiver_fails(self):
        with self.assertRaises(NotGroupMemberError):
            self.service.create_manual_settlement(
                self.group.group_id,
                self.payer.user_id,
                {
                    "receiver_user_id": str(uuid.uuid4()),
                    "amount_minor": 1000,
                    "currency": "IRR",
                },
            )

    def test_create_settlement_invalid_amount_fails(self):
        with self.assertRaises(InvalidSettlementAmountError):
            self.service.create_manual_settlement(
                self.group.group_id,
                self.payer.user_id,
                {
                    "receiver_user_id": str(self.receiver.user_id),
                    "amount_minor": 0,
                    "currency": "IRR",
                },
            )

    def test_confirm_settlement_by_receiver_and_publishes_events(self):
        settlement = ManualSettlementRepository.create_pending(
            group_id=self.group.group_id,
            payer_user_id=self.payer.user_id,
            receiver_user_id=self.receiver.user_id,
            amount_minor=500,
            currency="IRR",
            created_by_user_id=self.payer.user_id,
        )
        self.service.confirm_settlement(settlement.id, self.receiver.user_id)
        settlement.refresh_from_db()
        self.assertEqual(settlement.status, ManualSettlementStatusChoices.CONFIRMED)
        self.assertIsNotNone(settlement.confirmed_at)
        self.assertEqual(
            DebtLedgerEntry.objects.filter(
                group_id=self.group.group_id,
                entry_type=DebtLedgerEntryTypeChoices.MANUAL_SETTLEMENT,
                status=DebtLedgerStatusChoices.ACTIVE,
            ).count(),
            1,
        )
        published_types = [
            call.args[0] for call in self.publisher.publish.call_args_list
        ]
        self.assertIn("SettlementConfirmed", published_types)
        self.assertIn("BalanceRecalculated", published_types)
        self.assertIn("DebtLedgerUpdated", published_types)

    def test_confirm_settlement_by_non_receiver_fails(self):
        settlement = ManualSettlementRepository.create_pending(
            group_id=self.group.group_id,
            payer_user_id=self.payer.user_id,
            receiver_user_id=self.receiver.user_id,
            amount_minor=500,
            currency="IRR",
            created_by_user_id=self.payer.user_id,
        )
        with self.assertRaises(SettlementPermissionDeniedError):
            self.service.confirm_settlement(settlement.id, self.payer.user_id)

    def test_reject_settlement_by_receiver_and_event_published(self):
        settlement = ManualSettlementRepository.create_pending(
            group_id=self.group.group_id,
            payer_user_id=self.payer.user_id,
            receiver_user_id=self.receiver.user_id,
            amount_minor=500,
            currency="IRR",
            created_by_user_id=self.payer.user_id,
        )
        self.service.reject_settlement(settlement.id, self.receiver.user_id)
        settlement.refresh_from_db()
        self.assertEqual(settlement.status, ManualSettlementStatusChoices.REJECTED)
        published_types = [
            call.args[0] for call in self.publisher.publish.call_args_list
        ]
        self.assertIn("SettlementRejected", published_types)

    def test_reject_settlement_by_non_receiver_fails(self):
        settlement = ManualSettlementRepository.create_pending(
            group_id=self.group.group_id,
            payer_user_id=self.payer.user_id,
            receiver_user_id=self.receiver.user_id,
            amount_minor=500,
            currency="IRR",
            created_by_user_id=self.payer.user_id,
        )
        with self.assertRaises(SettlementPermissionDeniedError):
            self.service.reject_settlement(settlement.id, self.payer.user_id)

    def test_cancel_settlement_by_payer_before_confirmation(self):
        settlement = ManualSettlementRepository.create_pending(
            group_id=self.group.group_id,
            payer_user_id=self.payer.user_id,
            receiver_user_id=self.receiver.user_id,
            amount_minor=500,
            currency="IRR",
            created_by_user_id=self.payer.user_id,
        )
        self.service.cancel_settlement(settlement.id, self.payer.user_id)
        settlement.refresh_from_db()
        self.assertEqual(settlement.status, ManualSettlementStatusChoices.CANCELLED)
        published_types = [
            call.args[0] for call in self.publisher.publish.call_args_list
        ]
        self.assertIn("SettlementCancelled", published_types)

    def test_cancel_settlement_by_non_payer_fails(self):
        settlement = ManualSettlementRepository.create_pending(
            group_id=self.group.group_id,
            payer_user_id=self.payer.user_id,
            receiver_user_id=self.receiver.user_id,
            amount_minor=500,
            currency="IRR",
            created_by_user_id=self.payer.user_id,
        )
        with self.assertRaises(SettlementPermissionDeniedError):
            self.service.cancel_settlement(settlement.id, self.receiver.user_id)

    def test_cannot_cancel_confirmed_settlement(self):
        settlement = ManualSettlementRepository.create_pending(
            group_id=self.group.group_id,
            payer_user_id=self.payer.user_id,
            receiver_user_id=self.receiver.user_id,
            amount_minor=500,
            currency="IRR",
            created_by_user_id=self.payer.user_id,
        )
        self.service.confirm_settlement(settlement.id, self.receiver.user_id)
        with self.assertRaises(InvalidSettlementStatusError):
            self.service.cancel_settlement(settlement.id, self.payer.user_id)


class SettlementConsumerTests(TestCase):
    def setUp(self):
        self.consumer = SettlementEventConsumer()

    def test_duplicate_event_id_is_ignored(self):
        payload = {
            "event_id": str(uuid.uuid4()),
            "event_type": "ExpenseCreated",
            "data": {"expense_id": str(uuid.uuid4())},
        }
        with patch(
            "apps.settlements.infrastructure.rabbitmq_consumer.ProcessedEventRepository.was_processed",
            return_value=True,
        ), patch.object(self.consumer.expense_events, "handle") as handle_mock:
            result = self.consumer.process_expense_payload(payload)
        self.assertFalse(result)
        handle_mock.assert_not_called()

    def test_processed_event_prevents_double_debt_creation(self):
        event_id = str(uuid.uuid4())
        payload = {
            "event_id": event_id,
            "event_type": "ExpenseCreated",
            "data": {"expense_id": str(uuid.uuid4())},
        }
        with patch.object(
            self.consumer.expense_events, "handle", return_value=None
        ) as handle_mock:
            first = self.consumer.process_expense_payload(payload)
            second = self.consumer.process_expense_payload(payload)
        self.assertTrue(first)
        self.assertFalse(second)
        self.assertEqual(handle_mock.call_count, 1)

    def test_identity_payload_is_idempotent(self):
        payload = {
            "event_id": str(uuid.uuid4()),
            "event_type": "UserCreated",
            "data": {
                "identity_user_id": str(uuid.uuid4()),
                "email": "+15550001",
                "art_name": "Test User",
                "first_name": "Test",
                "last_name": "User",
                "role": "USER",
                "is_active": True,
            },
        }
        with patch(
            "apps.settlements.infrastructure.rabbitmq_consumer.ProcessedEventRepository.was_processed",
            return_value=False,
        ), patch(
            "apps.settlements.infrastructure.rabbitmq_consumer.UserProjectionRepository.upsert_from_event",
            return_value=SimpleNamespace(),
        ), patch(
            "apps.settlements.infrastructure.rabbitmq_consumer.ProcessedEventRepository.mark_processed"
        ) as mark_processed:
            result = self.consumer.process_identity_payload(payload)
        self.assertTrue(result)
        mark_processed.assert_called_once()

    def test_user_created_and_updated_projection(self):
        user_id = uuid.uuid4()
        created = {
            "event_id": str(uuid.uuid4()),
            "event_type": "UserCreated",
            "data": {
                "identity_user_id": str(user_id),
                "email": "+989121111111",
                "art_name": "User A",
                "first_name": "User",
                "last_name": "A",
                "role": "USER",
                "is_active": True,
            },
        }
        updated = {
            "event_id": str(uuid.uuid4()),
            "event_type": "UserUpdated",
            "data": {
                "identity_user_id": str(user_id),
                "email": "+989121111111",
                "art_name": "User Updated",
                "first_name": "User",
                "last_name": "Updated",
                "role": "ADMIN",
                "is_active": True,
            },
        }
        self.consumer.process_identity_payload(created)
        self.consumer.process_identity_payload(updated)
        user = UserProjection.objects.get(identity_user_id=user_id)
        self.assertEqual(user.art_name, "User Updated")
        self.assertEqual(user.role, "ADMIN")

    def test_group_created_and_member_joined_and_removed_updates_projection(self):
        group_id = uuid.uuid4()
        member_user_id = uuid.uuid4()
        self.consumer.process_group_payload(
            {
                "event_id": str(uuid.uuid4()),
                "event_type": "GroupCreated",
                "data": {
                    "group_id": str(group_id),
                    "title": "Trip",
                    "group_type": "TRIP",
                    "status": "ACTIVE",
                    "created_by_user_id": str(member_user_id),
                    "member_count": 1,
                },
            }
        )
        self.consumer.process_group_payload(
            {
                "event_id": str(uuid.uuid4()),
                "event_type": "GroupMemberJoined",
                "data": {
                    "group_id": str(group_id),
                    "user_id": str(member_user_id),
                    "email": "+989121222222",
                    "art_name": "Member 1",
                    "role": "MEMBER",
                },
            }
        )
        self.consumer.process_group_payload(
            {
                "event_id": str(uuid.uuid4()),
                "event_type": "GroupMemberRemoved",
                "data": {
                    "group_id": str(group_id),
                    "user_id": str(member_user_id),
                },
            }
        )
        group = GroupProjection.objects.get(group_id=group_id)
        member = GroupMemberProjection.objects.get(
            group_id=group_id, user_id=member_user_id
        )
        self.assertEqual(group.title, "Trip")
        self.assertEqual(member.status, GroupMemberStatusChoices.REMOVED)

    def test_invalid_payload_does_not_crash_expense_callback(self):
        class FakeChannel:
            def __init__(self):
                self.acked = False

            def basic_ack(self, delivery_tag):
                self.acked = True

        channel = FakeChannel()
        method = SimpleNamespace(delivery_tag="d1")
        self.consumer._callback_expense(channel, method, None, b"not-json")
        self.assertTrue(channel.acked)
