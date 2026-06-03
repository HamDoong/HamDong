from collections.abc import Mapping, Sequence


def _ordered_indices(
    participant_ids: Sequence[object],
    deterministic_order: str = "sorted",
) -> list[int]:
    if deterministic_order not in {"sorted", "input"}:
        raise ValueError("deterministic_order must be 'sorted' or 'input'")

    if deterministic_order == "input":
        return list(range(len(participant_ids)))

    ordered_pairs = sorted(
        ((str(participant_id), index) for index, participant_id in enumerate(participant_ids)),
        key=lambda item: item[0],
    )
    return [index for _, index in ordered_pairs]


def split_integer_minor(
    amount: int,
    participant_ids: Sequence[object],
    deterministic_order: str = "sorted",
) -> list[int]:
    if amount < 0:
        raise ValueError("amount must be non-negative")
    if not participant_ids:
        raise ValueError("must have at least one participant")

    participant_count = len(participant_ids)
    base_share = amount // participant_count
    remainder = amount % participant_count

    shares = [base_share] * participant_count
    for index in _ordered_indices(participant_ids, deterministic_order)[:remainder]:
        shares[index] += 1

    if sum(shares) != amount:
        raise ValueError("split result does not match amount")

    return shares


def distribute_integer_minor_by_weights(
    total_amount_minor: int,
    weights: Mapping[object, int],
    deterministic_order: str = "sorted",
) -> dict[str, int]:
    if total_amount_minor < 0:
        raise ValueError("total_amount_minor must be non-negative")
    if not weights:
        raise ValueError("weights must not be empty")

    normalized = [(str(key), int(value)) for key, value in weights.items()]
    if any(weight < 0 for _, weight in normalized):
        raise ValueError("weights must be non-negative")

    if total_amount_minor == 0:
        return {key: 0 for key, _ in normalized}

    total_weight = sum(weight for _, weight in normalized)
    if total_weight <= 0:
        raise ValueError("total weight must be positive")

    allocated: dict[str, int] = {}
    used = 0
    for key, weight in normalized:
        share = (total_amount_minor * weight) // total_weight
        allocated[key] = share
        used += share

    remainder = total_amount_minor - used
    ordered_keys = (
        [key for key, _ in normalized]
        if deterministic_order == "input"
        else sorted(key for key, _ in normalized)
    )
    for key in ordered_keys[:remainder]:
        allocated[key] += 1

    if sum(allocated.values()) != total_amount_minor:
        raise ValueError("distributed result does not match total_amount_minor")

    return allocated
