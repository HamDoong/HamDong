import uuid
from datetime import datetime, timezone


class DomainEvent:
    def __init__(self, event_type: str, data: dict, version: int = 1):
        self.event_id = str(uuid.uuid4())
        self.event_type = event_type
        self.occurred_at = datetime.now(timezone.utc)
        self.version = version
        self.data = data

    def to_dict(self):
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "occurred_at": self.occurred_at.isoformat(),
            "version": self.version,
            "data": self.data,
        }


class SettlementCreated(DomainEvent):
    def __init__(
        self,
        settlement_id,
        group_id,
        payer_user_id,
        receiver_user_id,
        amount_minor,
        currency,
        status,
    ):
        super().__init__(
            "SettlementCreated",
            {
                "settlement_id": str(settlement_id),
                "group_id": str(group_id),
                "payer_user_id": str(payer_user_id),
                "receiver_user_id": str(receiver_user_id),
                "amount_minor": amount_minor,
                "currency": currency,
                "status": status,
            },
        )


class SettlementConfirmed(DomainEvent):
    def __init__(
        self,
        settlement_id,
        group_id,
        payer_user_id,
        receiver_user_id,
        amount_minor,
        currency,
        confirmed_by_user_id,
    ):
        super().__init__(
            "SettlementConfirmed",
            {
                "settlement_id": str(settlement_id),
                "group_id": str(group_id),
                "payer_user_id": str(payer_user_id),
                "receiver_user_id": str(receiver_user_id),
                "amount_minor": amount_minor,
                "currency": currency,
                "confirmed_by_user_id": str(confirmed_by_user_id),
            },
        )


class SettlementRejected(DomainEvent):
    def __init__(
        self,
        settlement_id,
        group_id,
        payer_user_id,
        receiver_user_id,
        amount_minor,
        currency,
        rejected_by_user_id,
        reason=None,
    ):
        data = {
            "settlement_id": str(settlement_id),
            "group_id": str(group_id),
            "payer_user_id": str(payer_user_id),
            "receiver_user_id": str(receiver_user_id),
            "amount_minor": amount_minor,
            "currency": currency,
            "rejected_by_user_id": str(rejected_by_user_id),
        }
        if reason:
            data["reason"] = reason
        super().__init__("SettlementRejected", data)


class SettlementCancelled(DomainEvent):
    def __init__(
        self,
        settlement_id,
        group_id,
        payer_user_id,
        receiver_user_id,
        amount_minor,
        currency,
        cancelled_by_user_id,
    ):
        super().__init__(
            "SettlementCancelled",
            {
                "settlement_id": str(settlement_id),
                "group_id": str(group_id),
                "payer_user_id": str(payer_user_id),
                "receiver_user_id": str(receiver_user_id),
                "amount_minor": amount_minor,
                "currency": currency,
                "cancelled_by_user_id": str(cancelled_by_user_id),
            },
        )


class BalanceRecalculated(DomainEvent):
    def __init__(self, group_id, currency, balances):
        super().__init__(
            "BalanceRecalculated",
            {
                "group_id": str(group_id),
                "currency": currency,
                "balances": balances,
            },
        )


class DebtLedgerUpdated(DomainEvent):
    def __init__(
        self,
        group_id,
        currency,
        source_expense_id=None,
        source_settlement_id=None,
        entry_ids=None,
        status="ACTIVE",
    ):
        data = {
            "group_id": str(group_id),
            "currency": currency,
            "status": status,
        }
        if source_expense_id is not None:
            data["source_expense_id"] = str(source_expense_id)
        if source_settlement_id is not None:
            data["source_settlement_id"] = str(source_settlement_id)
        if entry_ids is not None:
            data["entry_ids"] = [str(entry_id) for entry_id in entry_ids]
        super().__init__("DebtLedgerUpdated", data)


class SettlementPlanGenerated(DomainEvent):
    def __init__(
        self, plan_id, group_id, currency, transaction_count, total_debt_minor
    ):
        super().__init__(
            "SettlementPlanGenerated",
            {
                "plan_id": str(plan_id),
                "group_id": str(group_id),
                "currency": currency,
                "transaction_count": transaction_count,
                "total_debt_minor": total_debt_minor,
            },
        )


class SettlementPlanActivated(DomainEvent):
    def __init__(self, plan_id, group_id, activated_by_user_id):
        super().__init__(
            "SettlementPlanActivated",
            {
                "plan_id": str(plan_id),
                "group_id": str(group_id),
                "activated_by_user_id": str(activated_by_user_id),
            },
        )


class SettlementPlanCancelled(DomainEvent):
    def __init__(self, plan_id, group_id, cancelled_by_user_id):
        super().__init__(
            "SettlementPlanCancelled",
            {
                "plan_id": str(plan_id),
                "group_id": str(group_id),
                "cancelled_by_user_id": str(cancelled_by_user_id),
            },
        )


class SettlementPlanExpired(DomainEvent):
    def __init__(self, plan_id, group_id):
        super().__init__(
            "SettlementPlanExpired",
            {"plan_id": str(plan_id), "group_id": str(group_id)},
        )


class SettlementPlanItemReported(DomainEvent):
    def __init__(
        self,
        plan_id,
        item_id,
        group_id,
        payer_user_id,
        receiver_user_id,
        amount_minor,
        manual_settlement_id,
    ):
        super().__init__(
            "SettlementPlanItemReported",
            {
                "plan_id": str(plan_id),
                "item_id": str(item_id),
                "group_id": str(group_id),
                "payer_user_id": str(payer_user_id),
                "receiver_user_id": str(receiver_user_id),
                "amount_minor": amount_minor,
                "manual_settlement_id": str(manual_settlement_id),
            },
        )


class SettlementPlanItemConfirmed(DomainEvent):
    def __init__(
        self, plan_id, item_id, group_id, payer_user_id, receiver_user_id, amount_minor
    ):
        super().__init__(
            "SettlementPlanItemConfirmed",
            {
                "plan_id": str(plan_id),
                "item_id": str(item_id),
                "group_id": str(group_id),
                "payer_user_id": str(payer_user_id),
                "receiver_user_id": str(receiver_user_id),
                "amount_minor": amount_minor,
            },
        )


class SettlementPlanItemRejected(DomainEvent):
    def __init__(
        self, plan_id, item_id, group_id, payer_user_id, receiver_user_id, amount_minor
    ):
        super().__init__(
            "SettlementPlanItemRejected",
            {
                "plan_id": str(plan_id),
                "item_id": str(item_id),
                "group_id": str(group_id),
                "payer_user_id": str(payer_user_id),
                "receiver_user_id": str(receiver_user_id),
                "amount_minor": amount_minor,
            },
        )


class SettlementPlanCompleted(DomainEvent):
    def __init__(self, plan_id, group_id, completed_at):
        super().__init__(
            "SettlementPlanCompleted",
            {
                "plan_id": str(plan_id),
                "group_id": str(group_id),
                "completed_at": completed_at.isoformat(),
            },
        )
