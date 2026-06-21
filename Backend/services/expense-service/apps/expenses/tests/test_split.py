import pytest

from apps.expenses.application.split_calculator import custom_split, equal_split


def test_equal_split_clean_division():
    result = equal_split(["a", "b", "c"], 900000)
    assert result == {"a": 300000, "b": 300000, "c": 300000}
    assert sum(result.values()) == 900000


def test_equal_split_rounding_remainder():
    result = equal_split(["b", "a", "c"], 100000)
    assert result == {"b": 33333, "a": 33334, "c": 33333}
    assert sum(result.values()) == 100000


def test_equal_requires_participants():
    with pytest.raises(ValueError):
        equal_split([], 100000)


def test_custom_split_valid():
    result = custom_split(
        [
            {"user_id": "a", "base_share_minor": 400000},
            {"user_id": "b", "base_share_minor": 300000},
            {"user_id": "c", "base_share_minor": 300000},
        ],
        1000000,
    )
    assert result == {"a": 400000, "b": 300000, "c": 300000}


def test_custom_split_sum_mismatch_should_fail():
    with pytest.raises(ValueError, match="INVALID_SPLIT_AMOUNT"):
        custom_split(
            [
                {"user_id": "a", "base_share_minor": 400000},
                {"user_id": "b", "base_share_minor": 300000},
            ],
            1000000,
        )


def test_custom_split_rejects_negative_share():
    with pytest.raises(ValueError):
        custom_split([{"user_id": "a", "base_share_minor": -1}], 1000000)
