from decimal import Decimal

import pytest

from apps.expenses.application.tax_calculator import (
    calculate_service_fee_amount_minor,
    calculate_tax_amount_minor,
    compute_percentage_amount,
    distribute_proportional,
)


def test_tax_none_returns_zero():
    assert calculate_tax_amount_minor("NONE", 1000000) == 0


def test_percentage_tax_calculation():
    assert calculate_tax_amount_minor("PERCENTAGE", 1200000, tax_percentage=Decimal("10.00")) == 120000


def test_fixed_tax_calculation():
    assert calculate_tax_amount_minor("FIXED", 1000000, tax_amount_minor=100000) == 100000


def test_percentage_service_fee_calculation():
    assert calculate_service_fee_amount_minor("PERCENTAGE", 1000000, service_fee_percentage="2.50") == 25000


def test_fixed_service_fee_calculation():
    assert calculate_service_fee_amount_minor("FIXED", 1000000, service_fee_amount_minor=50000) == 50000


def test_negative_fixed_amount_fails():
    with pytest.raises(ValueError):
        calculate_tax_amount_minor("FIXED", 1000000, tax_amount_minor=-1)


def test_negative_percentage_fails():
    with pytest.raises(ValueError):
        compute_percentage_amount(1000000, Decimal("-1"))


def test_tax_distributed_proportionally_by_base_share():
    shares = distribute_proportional(100000, {"a": 400000, "b": 300000, "c": 300000})
    assert shares == {"a": 40000, "b": 30000, "c": 30000}
    assert sum(shares.values()) == 100000


def test_service_fee_distributed_proportionally_with_remainder():
    shares = distribute_proportional(100001, {"b": 1, "a": 1, "c": 1})
    assert shares == {"b": 33334, "a": 33334, "c": 33333}
    assert sum(shares.values()) == 100001
