"""Tax and service-fee calculations for integer minor units."""

from decimal import Decimal, ROUND_HALF_UP
from typing import Mapping


VALID_ADJUSTMENT_TYPES = {"NONE", "PERCENTAGE", "FIXED"}


def _to_decimal(value: object | None) -> Decimal:
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


def calculate_adjustment_amount_minor(
    adjustment_type: str,
    base_amount_minor: int,
    percentage: Decimal | str | None = None,
    fixed_amount_minor: int | None = None,
) -> int:
    """Calculate a tax or service-fee amount in minor units."""
    if adjustment_type not in VALID_ADJUSTMENT_TYPES:
        raise ValueError("INVALID_ADJUSTMENT_TYPE")

    normalized_base_amount_minor = int(base_amount_minor)
    if normalized_base_amount_minor < 0:
        raise ValueError("base_amount_minor must be non-negative")

    if adjustment_type == "NONE":
        return 0

    if adjustment_type == "PERCENTAGE":
        percent = _to_decimal(percentage)
        if percent < 0:
            raise ValueError("percentage must be non-negative")

        calculated_amount_minor = (Decimal(normalized_base_amount_minor) * percent) / Decimal("100")
        return int(calculated_amount_minor.quantize(Decimal("1"), rounding=ROUND_HALF_UP))

    if fixed_amount_minor is None:
        raise ValueError("fixed amount required")

    normalized_fixed_amount_minor = int(fixed_amount_minor)
    if normalized_fixed_amount_minor < 0:
        raise ValueError("fixed amount must be non-negative")

    return normalized_fixed_amount_minor


def compute_percentage_amount(base_amount_minor: int, percentage: Decimal | str | None) -> int:
    """Backward-compatible percentage helper used by tests and callers."""
    return calculate_adjustment_amount_minor("PERCENTAGE", base_amount_minor, percentage=percentage)


def calculate_tax_amount_minor(
    tax_type: str,
    base_amount_minor: int,
    tax_percentage: Decimal | str | None = None,
    tax_amount_minor: int | None = None,
) -> int:
    """Calculate tax in minor units."""
    return calculate_adjustment_amount_minor(
        tax_type,
        base_amount_minor,
        percentage=tax_percentage,
        fixed_amount_minor=tax_amount_minor,
    )


def calculate_service_fee_amount_minor(
    service_fee_type: str,
    base_amount_minor: int,
    service_fee_percentage: Decimal | str | None = None,
    service_fee_amount_minor: int | None = None,
) -> int:
    """Calculate service fee in minor units."""
    return calculate_adjustment_amount_minor(
        service_fee_type,
        base_amount_minor,
        percentage=service_fee_percentage,
        fixed_amount_minor=service_fee_amount_minor,
    )


def distribute_proportional(total_amount_minor: int, base_shares: Mapping[str, int]) -> dict[str, int]:
    """Distribute an amount proportionally by base shares with deterministic rounding."""
    normalized_total_amount_minor = int(total_amount_minor)
    if normalized_total_amount_minor < 0:
        raise ValueError("total_amount_minor must be non-negative")

    shares = {str(user_id): int(base_share) for user_id, base_share in base_shares.items()}
    if any(base_share < 0 for base_share in shares.values()):
        raise ValueError("base_share_minor must be non-negative")

    if not shares:
        if normalized_total_amount_minor == 0:
            return {}
        raise ValueError("base_shares required")

    if normalized_total_amount_minor == 0:
        return {user_id: 0 for user_id in shares}

    total_base = sum(shares.values())
    if total_base <= 0:
        raise ValueError("total base_share_minor must be positive")

    result: dict[str, int] = {}
    allocated = 0

    for user_id, base_share in shares.items():
        share = (base_share * normalized_total_amount_minor) // total_base
        result[user_id] = share
        allocated += share

    remainder = normalized_total_amount_minor - allocated
    for user_id in sorted(result)[:remainder]:
        result[user_id] += 1

    if sum(result.values()) != normalized_total_amount_minor:
        raise AssertionError("proportional distribution produced an invalid total")

    return result
