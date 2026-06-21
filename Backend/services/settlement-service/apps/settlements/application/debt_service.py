from django.db import transaction

from apps.settlements.application.balance_service import BalanceService
from apps.settlements.domain.models import ExpenseStatusChoices
from apps.settlements.infrastructure.rabbitmq_publisher import RabbitMQPublisher
from apps.settlements.infrastructure.repositories import (
    DebtLedgerRepository,
    ExpenseParticipantProjectionRepository,
    ExpenseProjectionRepository,
)


class DebtService:
    def __init__(self, publisher=None, balance_service=None):
        self.publisher = publisher or RabbitMQPublisher()
        self.balance_service = balance_service or BalanceService()

    def _publish_updates(
        self,
        group_id,
        currency,
        source_expense_id=None,
        source_settlement_id=None,
        entry_ids=None,
        status="ACTIVE",
    ):
        balances = self.balance_service.render_group_balances(
            group_id, currency=currency
        )["balances"]
        self.publisher.publish(
            "DebtLedgerUpdated",
            {
                "group_id": str(group_id),
                "currency": currency,
                "source_expense_id": (
                    str(source_expense_id) if source_expense_id else None
                ),
                "source_settlement_id": (
                    str(source_settlement_id) if source_settlement_id else None
                ),
                "entry_ids": [str(entry_id) for entry_id in (entry_ids or [])],
                "status": status,
            },
            "settlement.debt_ledger_updated",
        )
        self.publisher.publish(
            "BalanceRecalculated",
            {"group_id": str(group_id), "currency": currency, "balances": balances},
            "settlement.balance_recalculated",
        )

    @transaction.atomic
    def handle_expense_created(self, payload):
        expense = ExpenseProjectionRepository.upsert_from_event(**payload)
        if not expense:
            return None
        participants = payload.get("participants", [])
        ExpenseParticipantProjectionRepository.replace_for_expense(
            expense, participants
        )
        entries = DebtLedgerRepository.create_expense_entries(expense, participants)
        self.balance_service.recalculate_group(
            expense.group_id, currency=expense.currency
        )
        self._publish_updates(
            expense.group_id,
            expense.currency,
            source_expense_id=expense.expense_id,
            entry_ids=[entry.id for entry in entries],
        )
        return expense, entries

    @transaction.atomic
    def handle_expense_updated(self, payload):
        expense = ExpenseProjectionRepository.upsert_from_event(**payload)
        if not expense:
            return None
        reversed_entries = DebtLedgerRepository.reverse_active_for_expense(
            expense.expense_id
        )
        participants = payload.get("participants", [])
        if not participants:
            participants = [
                {
                    "user_id": row.user_id,
                    "base_share_minor": row.base_share_minor,
                    "tax_share_minor": row.tax_share_minor,
                    "service_fee_share_minor": row.service_fee_share_minor,
                    "total_share_minor": row.total_share_minor,
                }
                for row in ExpenseParticipantProjectionRepository.list_for_expense(
                    expense.expense_id
                )
            ]
        ExpenseParticipantProjectionRepository.replace_for_expense(
            expense, participants
        )
        new_entries = DebtLedgerRepository.create_expense_entries(expense, participants)
        expense.status = ExpenseStatusChoices.UPDATED
        expense.save(update_fields=["status", "expense_version", "updated_at"])
        self.balance_service.recalculate_group(
            expense.group_id, currency=expense.currency
        )
        self._publish_updates(
            expense.group_id,
            expense.currency,
            source_expense_id=expense.expense_id,
            entry_ids=[entry.id for entry in new_entries + reversed_entries],
            status="UPDATED",
        )
        return expense, new_entries

    @transaction.atomic
    def handle_expense_deleted(self, payload):
        expense = ExpenseProjectionRepository.get(payload.get("expense_id"))
        if not expense:
            return None
        reversed_entries = DebtLedgerRepository.reverse_active_for_expense(
            expense.expense_id
        )
        ExpenseProjectionRepository.mark_deleted(expense.expense_id)
        self.balance_service.recalculate_group(
            expense.group_id, currency=expense.currency
        )
        self._publish_updates(
            expense.group_id,
            expense.currency,
            source_expense_id=expense.expense_id,
            entry_ids=[entry.id for entry in reversed_entries],
            status="REVERSED",
        )
        return expense

    @transaction.atomic
    def handle_expense_participants_changed(self, payload):
        return self.handle_expense_updated(payload)

    @transaction.atomic
    def create_manual_settlement_ledger(self, settlement):
        entry = DebtLedgerRepository.create_manual_settlement_entry(settlement)
        self.balance_service.recalculate_group(
            settlement.group_id, currency=settlement.currency
        )
        self._publish_updates(
            settlement.group_id,
            settlement.currency,
            source_settlement_id=settlement.id,
            entry_ids=[entry.id],
        )
        return entry
