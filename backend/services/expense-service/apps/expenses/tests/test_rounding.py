from apps.expenses.application.rounding import split_integer_minor


def test_clean_division():
    assert split_integer_minor(120, ["u1", "u2", "u3"]) == [40, 40, 40]


def test_division_with_remainder():
    shares = split_integer_minor(101, ["b", "a", "c"])
    assert shares == [34, 34, 33]
    assert sum(shares) == 101


def test_zero_remainder():
    shares = split_integer_minor(12, ["u1", "u2", "u3", "u4"])
    assert shares == [3, 3, 3, 3]


def test_deterministic_repeatability():
    participants = ["user-3", "user-1", "user-2"]
    first = split_integer_minor(10, participants)
    second = split_integer_minor(10, participants)
    assert first == second
