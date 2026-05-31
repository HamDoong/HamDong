"""Use case orchestration for settlement-service."""

from apps.settlements.application.balance_service import BalanceService
from apps.settlements.application.debt_service import DebtService
from apps.settlements.application.recalculation_service import RecalculationService
from apps.settlements.application.settlement_service import SettlementService
from apps.settlements.domain.models import CurrencyChoices
from apps.settlements.infrastructure.repositories import DebtLedgerRepository


class GetGroupBalancesUseCase:
    def __init__(self, balance_service=None):
        self.balance_service = balance_service or BalanceService()

    def execute(self, user, group_id):
        return self.balance_service.render_group_balances(group_id, requester_user_id=user.sub, currency=CurrencyChoices.IRR)


class GetMyBalanceUseCase:
    def __init__(self, balance_service=None):
        self.balance_service = balance_service or BalanceService()

    def execute(self, user, group_id):
        return self.balance_service.render_my_balance(group_id, user.sub, currency=CurrencyChoices.IRR)


class GetGroupDebtsUseCase:
    def __init__(self, balance_service=None):
        self.balance_service = balance_service or BalanceService()

    def execute(self, user, group_id):
        return self.balance_service.render_group_debts(group_id, requester_user_id=user.sub, currency=CurrencyChoices.IRR)


class CreateManualSettlementUseCase:
    def __init__(self, settlement_service=None):
        self.settlement_service = settlement_service or SettlementService()

    def execute(self, user, group_id, payload):
        return self.settlement_service.create_manual_settlement(group_id, user.sub, payload)


class ListGroupSettlementsUseCase:
    def __init__(self, settlement_service=None):
        self.settlement_service = settlement_service or SettlementService()

    def execute(self, user, group_id, filters=None):
        return self.settlement_service.list_group_settlements(group_id, user.sub, filters=filters)


class ConfirmSettlementUseCase:
    def __init__(self, settlement_service=None):
        self.settlement_service = settlement_service or SettlementService()

    def execute(self, user, settlement_id):
        return self.settlement_service.confirm_settlement(settlement_id, user.sub)


class RejectSettlementUseCase:
    def __init__(self, settlement_service=None):
        self.settlement_service = settlement_service or SettlementService()

    def execute(self, user, settlement_id, reason=None):
        return self.settlement_service.reject_settlement(settlement_id, user.sub, reason=reason)


class CancelSettlementUseCase:
    def __init__(self, settlement_service=None):
        self.settlement_service = settlement_service or SettlementService()

    def execute(self, user, settlement_id):
        return self.settlement_service.cancel_settlement(settlement_id, user.sub)


class RebuildGroupBalancesUseCase:
    def __init__(self, recalculation_service=None):
        self.recalculation_service = recalculation_service or RecalculationService()

    def execute(self, group_id):
        return self.recalculation_service.rebuild_group_balances(group_id, currency=CurrencyChoices.IRR)


class ExpenseEventUseCase:
    def __init__(self, debt_service=None):
        self.debt_service = debt_service or DebtService()

    def handle(self, event_type, payload):
        if event_type == "ExpenseCreated":
            return self.debt_service.handle_expense_created(payload)
        if event_type == "ExpenseUpdated":
            return self.debt_service.handle_expense_updated(payload)
        if event_type == "ExpenseDeleted":
            return self.debt_service.handle_expense_deleted(payload)
        if event_type == "ExpenseParticipantsChanged":
            return self.debt_service.handle_expense_participants_changed(payload)
        return None
