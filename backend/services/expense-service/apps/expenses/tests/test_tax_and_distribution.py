from decimal import Decimal
from apps.expenses.application.tax_calculator import compute_percentage_amount, distribute_proportional


def test_percentage_amount_rounding():
    assert compute_percentage_amount(1000, Decimal('2.5')) == 25
    assert compute_percentage_amount(101, Decimal('10')) == 10


def test_distribute_proportional_simple():
    participants = {"a": 50, "b": 50}
    total = 101
    shares = distribute_proportional(total, participants)
    assert sum(shares.values()) == total
    assert set(shares.keys()) == set(participants.keys())


def test_distribute_proportional_zero_total():
    participants = {"a": 0, "b": 0}
    shares = distribute_proportional(100, participants)
    assert shares == {"a": 0, "b": 0}
