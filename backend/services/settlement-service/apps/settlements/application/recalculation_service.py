from apps.settlements.application.balance_service import BalanceService


class RecalculationService:
    def __init__(self, balance_service=None):
        self.balance_service = balance_service or BalanceService()

    def rebuild_group_balances(self, group_id, currency="IRR"):
        return self.balance_service.recalculate_group(group_id, currency=currency)