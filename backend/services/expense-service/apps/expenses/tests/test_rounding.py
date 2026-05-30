from apps.expenses.application.rounding import split_integer_minor


def test_clean_division():
    amount = 100
    participants = ["u1", "u2", "u3", "u4"]
    shares = split_integer_minor(amount, participants)
    assert shares == [25, 25, 25, 25]
    assert sum(shares) == amount


def test_remainder_division_sorted():
    amount = 101
    participants = ["b", "a", "c"]
    # default deterministic order is 'sorted', so order will be a,b,c -> indices [1,0,2]
    shares = split_integer_minor(amount, participants)
    # base = 33, remainder = 2 -> add to 'a' and 'b' based on sorted order => a and b get +1
    # mapping back to input order [b,a,c] -> b:34, a:34, c:33
    assert sum(shares) == amount
    assert shares == [34, 34, 33]


def test_remainder_division_input_order():
    amount = 5
    participants = ["p1", "p2", "p3"]
    shares = split_integer_minor(amount, participants, deterministic_order="input")
    # base=1, remainder=2 -> give +1 to first two participants p1,p2
    assert shares == [2, 2, 1]
    assert sum(shares) == amount
