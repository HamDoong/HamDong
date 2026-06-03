from decimal import Decimal

from apps.expenses.application.tax_calculator import (
    calculate_service_fee_amount,
    calculate_tax_amount,
    distribute_service_fee_amount,
    distribute_tax_amount,
)


def test_percentage_tax_calculation():
    assert calculate_tax_amount(
        tax_type="PERCENTAGE",
        base_amount_minor=1000,
        tax_percentage=Decimal("10"),
    ) == 100


def test_fixed_tax_calculation():
    assert calculate_tax_amount(
        tax_type="FIXED",
        base_amount_minor=1000,
        tax_amount_minor=125,
    ) == 125


def test_percentage_service_fee_calculation():
    assert calculate_service_fee_amount(
        service_fee_type="PERCENTAGE",
        base_amount_minor=1000,
        service_fee_percentage=Decimal("2.5"),
    ) == 25


def test_fixed_service_fee_calculation():
    assert calculate_service_fee_amount(
        service_fee_type="FIXED",
        base_amount_minor=1000,
        service_fee_amount_minor=75,
    ) == 75


def test_tax_distributed_proportionally_by_base_share():
    shares = distribute_tax_amount(
        tax_amount_minor=100,
        base_shares={"user-1": 750, "user-2": 250},
    )
    assert shares == {"user-1": 75, "user-2": 25}
    assert sum(shares.values()) == 100


def test_service_fee_distributed_proportionally_by_base_share():
    shares = distribute_service_fee_amount(
        service_fee_amount_minor=101,
        base_shares={"user-1": 500, "user-2": 500},
    )
    assert sum(shares.values()) == 101
    assert shares == {"user-1": 51, "user-2": 50}
