from decimal import Decimal, ROUND_HALF_UP
from typing import Mapping

from .rounding import distribute_integer_minor_by_weights


def _to_decimal(value: Decimal | str | int | None) -> Decimal:
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


def calculate_amount_minor(
    *,
    amount_type: str,
    base_amount_minor: int,
    percentage: Decimal | str | int | None = None,
    amount_minor: int | None = None,
) -> int:
    normalized_amount_type = str(amount_type or "NONE")

    if normalized_amount_type == "NONE":
        return 0

    if normalized_amount_type == "PERCENTAGE":
        normalized_percentage = _to_decimal(percentage)
        if normalized_percentage < 0:
            raise ValueError("percentage cannot be negative")
        raw_amount = (Decimal(int(base_amount_minor)) * normalized_percentage) / Decimal("100")
        return int(raw_amount.quantize(Decimal("1"), rounding=ROUND_HALF_UP))

    if normalized_amount_type == "FIXED":
        if amount_minor is None:
            raise ValueError("amount_minor is required for FIXED amounts")
        fixed_amount = int(amount_minor)
        if fixed_amount < 0:
            raise ValueError("amount_minor cannot be negative")
        return fixed_amount

    raise ValueError("invalid amount_type")


def calculate_tax_amount(
    *,
    tax_type: str,
    base_amount_minor: int,
    tax_percentage: Decimal | str | int | None = None,
    tax_amount_minor: int | None = None,
) -> int:
    return calculate_amount_minor(
        amount_type=tax_type,
        base_amount_minor=base_amount_minor,
        percentage=tax_percentage,
        amount_minor=tax_amount_minor,
    )


def calculate_service_fee_amount(
    *,
    service_fee_type: str,
    base_amount_minor: int,
    service_fee_percentage: Decimal | str | int | None = None,
    service_fee_amount_minor: int | None = None,
) -> int:
    return calculate_amount_minor(
        amount_type=service_fee_type,
        base_amount_minor=base_amount_minor,
        percentage=service_fee_percentage,
        amount_minor=service_fee_amount_minor,
    )


def distribute_proportional(
    total_amount_minor: int,
    base_shares: Mapping[object, int],
    deterministic_order: str = "sorted",
) -> dict[str, int]:
    normalized_base_shares = {str(user_id): int(value) for user_id, value in base_shares.items()}
    if total_amount_minor < 0:
        raise ValueError("total_amount_minor cannot be negative")
    if not normalized_base_shares:
        raise ValueError("base_shares must not be empty")

    if total_amount_minor == 0:
        return {user_id: 0 for user_id in normalized_base_shares}

    if sum(normalized_base_shares.values()) <= 0:
        raise ValueError("base_shares must have a positive total")

    return distribute_integer_minor_by_weights(
        total_amount_minor=int(total_amount_minor),
        weights=normalized_base_shares,
        deterministic_order=deterministic_order,
    )


def distribute_tax_amount(
    *,
    tax_amount_minor: int,
    base_shares: Mapping[object, int],
    deterministic_order: str = "sorted",
) -> dict[str, int]:
    return distribute_proportional(
        total_amount_minor=tax_amount_minor,
        base_shares=base_shares,
        deterministic_order=deterministic_order,
    )


def distribute_service_fee_amount(
    *,
    service_fee_amount_minor: int,
    base_shares: Mapping[object, int],
    deterministic_order: str = "sorted",
) -> dict[str, int]:
    return distribute_proportional(
        total_amount_minor=service_fee_amount_minor,
        base_shares=base_shares,
        deterministic_order=deterministic_order,
    )
