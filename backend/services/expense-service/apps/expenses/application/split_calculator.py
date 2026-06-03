from collections.abc import Iterable
from typing import Any

from .rounding import split_integer_minor

INVALID_SPLIT_AMOUNT = "INVALID_SPLIT_AMOUNT"


def _normalize_user_id(value: Any) -> str:
    user_id = str(value)
    if not user_id or user_id == "None":
        raise ValueError("participant must include user_id")
    return user_id


def equal_split(
    participant_user_ids: Iterable[object],
    base_amount_minor: int,
    deterministic_order: str = "sorted",
) -> dict[str, int]:
    participant_ids = [_normalize_user_id(user_id) for user_id in participant_user_ids]
    if not participant_ids:
        raise ValueError("at least one participant is required")
    if len(set(participant_ids)) != len(participant_ids):
        raise ValueError("duplicate participant_user_ids are not allowed")
    if int(base_amount_minor) < 0:
        raise ValueError("base_amount_minor must be non-negative")

    shares = split_integer_minor(
        amount=int(base_amount_minor),
        participant_ids=participant_ids,
        deterministic_order=deterministic_order,
    )
    return {user_id: share for user_id, share in zip(participant_ids, shares)}


def custom_split(
    participants: Iterable[dict[str, Any]],
    base_amount_minor: int,
) -> dict[str, int]:
    participant_list = list(participants)
    if not participant_list:
        raise ValueError("participants are required")

    shares: dict[str, int] = {}
    running_total = 0

    for participant in participant_list:
        user_id = _normalize_user_id(participant.get("user_id"))
        if user_id in shares:
            raise ValueError("duplicate participants are not allowed")

        base_share_minor = int(participant.get("base_share_minor", 0))
        if base_share_minor < 0:
            raise ValueError("base_share_minor cannot be negative")

        shares[user_id] = base_share_minor
        running_total += base_share_minor

    if running_total != int(base_amount_minor):
        raise ValueError(INVALID_SPLIT_AMOUNT)

    return shares
