from apps.expenses.application.rounding import split_integer_minor


def test_clean_division():
    shares = split_integer_minor(900000, ["u1", "u2", "u3"])
    assert shares == [300000, 300000, 300000]
    assert sum(shares) == 900000


def test_division_with_remainder():
    shares = split_integer_minor(100000, ["b", "a", "c"])
    assert shares == [33333, 33334, 33333]
    assert sum(shares) == 100000


def test_zero_remainder():
    shares = split_integer_minor(6, ["u1", "u2", "u3"])
    assert shares == [2, 2, 2]
    assert sum(shares) == 6


def test_deterministic_repeatability():
    participants = ["b", "a", "c"]
    assert split_integer_minor(100000, participants) == split_integer_minor(100000, participants)


def test_no_negative_shares():
    assert all(share >= 0 for share in split_integer_minor(2, ["u1", "u2", "u3"]))
