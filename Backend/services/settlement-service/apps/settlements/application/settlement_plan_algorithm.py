from apps.settlements.domain.value_objects import (
    SettlementBalanceRow,
    SettlementPlanInstruction,
)


def generate_settlement_plan(balances):
    normalized = []
    for balance in balances:
        if isinstance(balance, SettlementBalanceRow):
            user_id = str(balance.user_id)
            net_balance_minor = int(balance.net_balance_minor)
        else:
            user_id = str(balance["user_id"])
            net_balance_minor = int(balance["net_balance_minor"])
        if net_balance_minor != 0:
            normalized.append((user_id, net_balance_minor))

    debtors = sorted(
        [(user_id, balance) for user_id, balance in normalized if balance < 0],
        key=lambda item: (item[1], item[0]),
    )
    creditors = sorted(
        [(user_id, balance) for user_id, balance in normalized if balance > 0],
        key=lambda item: (-item[1], item[0]),
    )

    plan_items = []
    debtor_index = 0
    creditor_index = 0
    order_index = 1

    while debtor_index < len(debtors) and creditor_index < len(creditors):
        debtor_user_id, debtor_balance = debtors[debtor_index]
        creditor_user_id, creditor_balance = creditors[creditor_index]
        amount_minor = min(abs(int(debtor_balance)), int(creditor_balance))
        if amount_minor > 0 and debtor_user_id != creditor_user_id:
            plan_items.append(
                SettlementPlanInstruction(
                    payer_user_id=debtor_user_id,
                    receiver_user_id=creditor_user_id,
                    amount_minor=amount_minor,
                    order_index=order_index,
                )
            )
            order_index += 1

        debtor_balance += amount_minor
        creditor_balance -= amount_minor
        debtors[debtor_index] = (debtor_user_id, debtor_balance)
        creditors[creditor_index] = (creditor_user_id, creditor_balance)

        if debtor_balance == 0:
            debtor_index += 1
        if creditor_balance == 0:
            creditor_index += 1

    return plan_items
