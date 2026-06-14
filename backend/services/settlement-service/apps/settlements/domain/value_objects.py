from dataclasses import dataclass


@dataclass(frozen=True)
class BalanceRow:
    user_id: str
    art_name: str | None
    email: str | None
    net_balance_minor: int
    status: str


@dataclass(frozen=True)
class SettlementRow:
    id: str
    group_id: str
    payer_user_id: str
    receiver_user_id: str
    amount_minor: int
    currency: str
    status: str


@dataclass(frozen=True)
class SettlementBalanceRow:
    user_id: str
    net_balance_minor: int


@dataclass(frozen=True)
class SettlementPlanInstruction:
    payer_user_id: str
    receiver_user_id: str
    amount_minor: int
    order_index: int
