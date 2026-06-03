"""Deterministic integer rounding helpers for money in minor units."""

from collections.abc import Sequence
from typing import Any


def split_integer_minor(
    amount_minor: int,
    participant_ids: Sequence[Any],
    deterministic_order: str = "sorted",
) -> list[int]:
    """Split an integer amount without losing or creating minor units."""
    normalized_amount_minor = int(amount_minor)
    if normalized_amount_minor < 0:
        raise ValueError("amount_minor must be non-negative")

    ids = list(participant_ids)
    if not ids:
        raise ValueError("participant_user_ids required")

    base_share = normalized_amount_minor // len(ids)
    remainder = normalized_amount_minor % len(ids)
    shares = [base_share for _ in ids]

    if deterministic_order == "input":
        order = list(range(len(ids)))
    elif deterministic_order == "sorted":
        order = [idx for _, idx in sorted((str(user_id), idx) for idx, user_id in enumerate(ids))]
    else:
        raise ValueError("deterministic_order must be 'input' or 'sorted'")

    for idx in order[:remainder]:
        shares[idx] += 1

    if sum(shares) != normalized_amount_minor:
        raise AssertionError("split produced an invalid total")

    return shares
