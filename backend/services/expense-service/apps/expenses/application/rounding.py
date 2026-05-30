from typing import List
import uuid


def split_integer_minor(amount: int, participant_ids: List[str], deterministic_order: str = "sorted") -> List[int]:
    """Split an integer `amount` (minor units) across N participants deterministically.

    - `participant_ids`: list of ids to deterministically order remainder distribution.
    - `deterministic_order`: 'sorted' (default) or 'input'.

    Returns a list of integers (shares) in the same order as `participant_ids` when
    `deterministic_order='input'`, otherwise in the same order as `participant_ids` but
    remainder assigned according to sorted ordering.
    Sum of shares equals amount.
    """
    if amount < 0:
        raise ValueError("amount must be non-negative")
    n = len(participant_ids)
    if n == 0:
        raise ValueError("must have at least one participant")

    base = amount // n
    shares = [base] * n
    remainder = amount - base * n

    if remainder == 0:
        return shares

    # Determine deterministic index order for distributing remainder
    if deterministic_order == "input":
        order = list(range(n))
    else:
        # sort by stringified participant id to be deterministic
        sorted_pairs = sorted(((str(pid), idx) for idx, pid in enumerate(participant_ids)))
        order = [idx for (_pid, idx) in sorted_pairs]

    # distribute one unit to first `remainder` participants in the deterministic order
    for i in range(remainder):
        shares[order[i % n]] += 1

    # final sanity check
    assert sum(shares) == amount
    return shares
def distribute_remainder(participant_ids, base_share, base_amount):
    """Distribute remainder deterministically by sorted participant_ids."""
    n = len(participant_ids)
    shares = {pid: base_share for pid in participant_ids}
    remainder = base_amount - base_share * n
    # deterministic order: sort by string representation
    ordered = sorted(participant_ids, key=lambda x: str(x))
    idx = 0
    while remainder > 0:
        pid = ordered[idx % n]
        shares[pid] += 1
        remainder -= 1
        idx += 1
    return shares
