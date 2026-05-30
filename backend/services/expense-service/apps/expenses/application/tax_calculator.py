from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List


def compute_percentage_amount(base_amount_minor: int, percentage: Decimal) -> int:
    if percentage is None:
        return 0
    p = Decimal(percentage)
    if p < 0:
        raise ValueError("Negative percentage not allowed")
    amt = (Decimal(base_amount_minor) * p / Decimal("100"))
    # round half up to nearest minor unit
    return int(amt.quantize(Decimal('1'), rounding=ROUND_HALF_UP))


def distribute_proportional(total_amount: int, participants_map: Dict[str, int]) -> Dict[str, int]:
    """Distribute `total_amount` proportionally according to participants_map (user_id -> base_share_minor).

    Deterministic remainder distribution by sorting user_id string.
    """
    if total_amount <= 0:
        return {uid: 0 for uid in participants_map}

    total_base = sum(int(v) for v in participants_map.values())
    if total_base <= 0:
        return {uid: 0 for uid in participants_map}

    floor_shares = {}
    allocated = 0
    for uid, base in participants_map.items():
        share = (int(base) * int(total_amount)) // int(total_base)
        floor_shares[uid] = int(share)
        allocated += int(share)

    remainder = int(total_amount) - allocated
    if remainder > 0:
        # deterministic order by user_id string
        ordered = sorted((str(uid) for uid in participants_map.keys()))
        for i in range(remainder):
            uid = ordered[i % len(ordered)]
            floor_shares[uid] += 1

    # final sanity
    assert sum(floor_shares.values()) == int(total_amount)
    return floor_shares
from decimal import Decimal
from typing import Dict


def compute_percentage_amount(base: int, percentage: Decimal) -> int:
    # returns floored integer minor units
    if percentage is None:
        return 0
    amt = (Decimal(base) * (percentage / Decimal(100))).quantize(Decimal("1."), rounding="ROUND_FLOOR")
    return int(amt)


def distribute_proportional(total_amount: int, base_shares: Dict[str, int]) -> Dict[str, int]:
    total_base = sum(base_shares.values())
    if total_base == 0:
        # nothing to distribute
        return {k: 0 for k in base_shares}

    shares = {}
    accumulated = 0
    # compute floor share
    for k, v in base_shares.items():
        share = (total_amount * v) // total_base
        shares[k] = share
        accumulated += share

    remainder = total_amount - accumulated
    if remainder > 0:
        # deterministic distribution by sorted keys
        keys = sorted(base_shares.keys(), key=lambda x: str(x))
        i = 0
        while remainder > 0:
            shares[keys[i % len(keys)]] += 1
            remainder -= 1
            i += 1

    return shares
