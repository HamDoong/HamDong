import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_gateway_nested_routes_come_before_groups_route():
    content = (ROOT / "api-gateway" / "nginx.conf").read_text()
    groups_index = content.index("location /api/v1/groups/")
    for needle in [
        "location ~ ^/api/v1/groups/[^/]+/expenses(/|$)",
        "location ~ ^/api/v1/groups/[^/]+/media(/|$)",
        "location ~ ^/api/v1/groups/[^/]+/(balances|debts|settlements|settlement-plan)(/|$)",
    ]:
        assert content.index(needle) < groups_index


def test_expense_api_tests_use_amount_minor_contract():
    content = (ROOT / "api-tests" / "expense.http").read_text()
    assert "base_amount_minor" in content
    assert "payer_user_id" in content
    assert "participant_user_ids" in content
    for legacy_key in ('"amount"', '"paid_by"', '"paidBy"'):
        assert legacy_key not in content


def test_hamdong_http_contains_demo_flow_sections():
    content = (ROOT / "api-tests" / "hamdong.http").read_text()
    for needle in [
        "Ali creates a group",
        "Ali creates an invite",
        "Sara accepts invite",
        "Reza accepts invite",
        "Sara creates an equal split expense",
        "Ali gets group balances",
        "Ali generates smart settlement plan",
        "Ali reports his plan item as paid",
        "Sara confirms the plan item",
    ]:
        assert needle in content
