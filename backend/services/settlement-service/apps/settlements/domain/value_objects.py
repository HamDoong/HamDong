from dataclasses import dataclass


@dataclass(frozen=True)
class BalanceRow:
    user_id: str
    display_name: str | None
    phone_number: str | None
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