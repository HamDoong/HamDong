from typing import List, Dict
from .rounding import split_integer_minor


def equal_split(participant_ids: List[str], base_amount_minor: int, order: str = "sorted") -> Dict[str, int]:
    """Split `base_amount_minor` equally across participant_ids.

    Returns dict mapping user_id (str) -> base_share_minor (int).
    """
    if not participant_ids:
        raise ValueError("no participants")
    if base_amount_minor < 0:
        raise ValueError("base_amount_minor must be non-negative")

    shares = split_integer_minor(base_amount_minor, participant_ids, deterministic_order=("input" if order == "input" else "sorted"))
    return {str(uid): int(share) for uid, share in zip(participant_ids, shares)}


def custom_split(participants: List[Dict], base_amount_minor: int) -> Dict[str, int]:
    """participants: list of dicts with user_id and base_share_minor

    Validates that the sum of participant shares equals base_amount_minor.
    Returns dict mapping user_id -> base_share_minor.
    """
    if not participants:
        raise ValueError("participants required")
    total = 0
    result = {}
    for p in participants:
        user_id = str(p.get("user_id"))
        if user_id is None:
            raise ValueError("participant must include user_id")
        share = int(p.get("base_share_minor", 0))
        if share < 0:
            raise ValueError("participant share cannot be negative")
        total += share
        result[user_id] = share

    if total != int(base_amount_minor):
        raise ValueError("INVALID_SPLIT_AMOUNT")

    return result
