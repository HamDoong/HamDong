from __future__ import annotations

import re
from pathlib import Path
import unittest


BACKEND_DIR = Path(__file__).resolve().parents[1]


class FixPack4ContractChecks(unittest.TestCase):
    def test_gateway_nested_routes_precede_generic_groups_route(self) -> None:
        nginx = (BACKEND_DIR / "api-gateway" / "nginx.conf").read_text(encoding="utf-8")
        nested_patterns = [
            r"location ~ \^/api/v1/groups/\[^/\]\+/expenses\(/\|\$\)",
            r"location ~ \^/api/v1/groups/\[^/\]\+/media\(/\|\$\)",
            r"location ~ \^/api/v1/groups/\[^/\]\+/(balances\|debts\|settlements\|settlement-plan)\(/\|\$\)",
        ]
        group_index = nginx.index("location /api/v1/groups/")
        for snippet in [
            "location ~ ^/api/v1/groups/[^/]+/expenses(/|$)",
            "location ~ ^/api/v1/groups/[^/]+/media(/|$)",
            "location ~ ^/api/v1/groups/[^/]+/(balances|debts|settlements|settlement-plan)(/|$)",
        ]:
            self.assertIn(snippet, nginx)
            self.assertLess(nginx.index(snippet), group_index)

    def test_api_tests_do_not_use_deprecated_expense_fields(self) -> None:
        api_tests_dir = BACKEND_DIR / "api-tests"
        combined = "\n".join(
            path.read_text(encoding="utf-8")
            for path in api_tests_dir.glob("*.http")
        )
        self.assertNotIn("paid_by", combined)
        self.assertNotIn("paidBy", combined)
        self.assertNotRegex(combined, r'\n\s*"amount"\s*:')

    def test_hamdong_demo_contains_required_sections(self) -> None:
        hamdong = (BACKEND_DIR / "api-tests" / "hamdong.http").read_text(encoding="utf-8")
        required_markers = [
            "@aliPhone = 09120000001",
            "@saraPhone = 09120000002",
            "@rezaPhone = 09120000003",
            "### 7. Ali creates group",
            "### 8. Ali creates invite",
            "### 9. Sara accepts invite",
            "### 10. Reza accepts invite",
            "### 13. Sara creates equal split expense",
            '"base_amount_minor": 900000',
            '"payer_user_id": "{{saraUserId}}"',
            "Wait a few seconds for RabbitMQ consumers to process events before running this request.",
            "### 16. Ali generates settlement plan",
            "### 18. Ali reports his plan item as paid",
            "### 19. Sara confirms the plan item",
            "### 20. Ali gets final balances",
        ]
        for marker in required_markers:
            self.assertIn(marker, hamdong)


if __name__ == "__main__":
    unittest.main()
