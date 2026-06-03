import pytest

from apps.expenses.application.split_calculator import INVALID_SPLIT_AMOUNT, custom_split, equal_split


def test_equal_split_even():
    result = equal_split(["a", "b", "c"], 900)
    assert result == {"a": 300, "b": 300, "c": 300}


def test_equal_split_remainder():
    result = equal_split(["b", "a", "c"], 1000)
    assert sum(result.values()) == 1000
    assert result["a"] == 334
    assert result["b"] == 333
    assert result["c"] == 333


def test_custom_split_valid():
    result = custom_split(
        [
            {"user_id": "a", "base_share_minor": 400},
            {"user_id": "b", "base_share_minor": 600},
        ],
        1000,
    )
    assert result == {"a": 400, "b": 600}


def test_custom_split_sum_mismatch_should_fail():
    with pytest.raises(ValueError, match=INVALID_SPLIT_AMOUNT):
        custom_split(
            [
                {"user_id": "a", "base_share_minor": 300},
                {"user_id": "b", "base_share_minor": 600},
            ],
            1000,
        )
