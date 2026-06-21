"""Base-share split calculation for expenses."""

from collections.abc import Iterable, Mapping
from typing import Any

from apps.expenses.application.rounding import split_integer_minor


INVALID_SPLIT_AMOUNT = "INVALID_SPLIT_AMOUNT"


def equal_split(participant_user_ids: Iterable[Any], base_amount_minor: int) -> dict[str, int]:
    """Return base shares for an EQUAL split."""
    user_ids = [str(user_id) for user_id in participant_user_ids or []]
    if not user_ids:
        raise ValueError("participant_user_ids required")

    if len(set(user_ids)) != len(user_ids):
        raise ValueError("DUPLICATE_PARTICIPANT")

    normalized_base_amount_minor = int(base_amount_minor)
    if normalized_base_amount_minor < 0:
        raise ValueError("base_amount_minor must be non-negative")

    shares = split_integer_minor(normalized_base_amount_minor, user_ids, deterministic_order="sorted")
    result = dict(zip(user_ids, shares, strict=True))

    if sum(result.values()) != normalized_base_amount_minor:
        raise AssertionError("equal split produced an invalid total")

    return result


def custom_split(participants: Iterable[Mapping[str, Any]], base_amount_minor: int) -> dict[str, int]:
    """Return base shares for a CUSTOM_AMOUNT split."""
    rows = list(participants or [])
    if not rows:
        raise ValueError("participants required")

    normalized_base_amount_minor = int(base_amount_minor)
    if normalized_base_amount_minor < 0:
        raise ValueError("base_amount_minor must be non-negative")

    result: dict[str, int] = {}
    total = 0

    for row in rows:
        if "user_id" not in row or "base_share_minor" not in row:
            raise ValueError("participants require user_id and base_share_minor")

        user_id = str(row["user_id"])
        if user_id in result:
            raise ValueError("DUPLICATE_PARTICIPANT")

        share = int(row["base_share_minor"])
        if share < 0:
            raise ValueError("base_share_minor must be non-negative")

        result[user_id] = share
        total += share

    if total != normalized_base_amount_minor:
        raise ValueError(INVALID_SPLIT_AMOUNT)

    return result
