from apps.expenses.application.split_calculator import equal_split, custom_split


def test_equal_split_even():
    p = ["a","b","c"]
    res = equal_split(p, 900)
    assert sum(res.values()) == 900
    assert set(res.keys()) == set(p)


def test_equal_split_remainder():
    p = ["a","b","c"]
    res = equal_split(p, 1000)
    assert sum(res.values()) == 1000
    # base share floor is 333 each -> remainder 1 -> one gets +1
    assert sorted(res.values(), reverse=True)[0] in (334,)


def test_custom_split_valid():
    parts = [{"user_id":"a","base_share_minor":400}, {"user_id":"b","base_share_minor":600}]
    res = custom_split(parts, 1000)
    assert res["a"] == 400
    assert res["b"] == 600


def test_custom_split_invalid():
    parts = [{"user_id":"a","base_share_minor":300}, {"user_id":"b","base_share_minor":600}]
    try:
        custom_split(parts, 1000)
        assert False
    except ValueError:
        assert True
