from django.test import TestCase

from apps.settlements.application.settlement_plan_algorithm import (
    generate_settlement_plan,
)


class SettlementPlanAlgorithmTests(TestCase):
    def test_one_debtor_one_creditor(self):
        plan = generate_settlement_plan(
            [
                {"user_id": "debtor", "net_balance_minor": -100000},
                {"user_id": "creditor", "net_balance_minor": 100000},
            ]
        )
        self.assertEqual(len(plan), 1)
        self.assertEqual(plan[0].payer_user_id, "debtor")
        self.assertEqual(plan[0].receiver_user_id, "creditor")
        self.assertEqual(plan[0].amount_minor, 100000)

    def test_multiple_debtors_one_creditor(self):
        plan = generate_settlement_plan(
            [
                {"user_id": "a", "net_balance_minor": -70000},
                {"user_id": "b", "net_balance_minor": -50000},
                {"user_id": "c", "net_balance_minor": 120000},
            ]
        )
        self.assertEqual(
            [
                (item.payer_user_id, item.receiver_user_id, item.amount_minor)
                for item in plan
            ],
            [("a", "c", 70000), ("b", "c", 50000)],
        )

    def test_one_debtor_multiple_creditors(self):
        plan = generate_settlement_plan(
            [
                {"user_id": "a", "net_balance_minor": -90000},
                {"user_id": "x", "net_balance_minor": 50000},
                {"user_id": "y", "net_balance_minor": 40000},
            ]
        )
        self.assertEqual(
            [
                (item.payer_user_id, item.receiver_user_id, item.amount_minor)
                for item in plan
            ],
            [("a", "x", 50000), ("a", "y", 40000)],
        )

    def test_multiple_debtors_multiple_creditors(self):
        plan = generate_settlement_plan(
            [
                {"user_id": "a", "net_balance_minor": -100000},
                {"user_id": "b", "net_balance_minor": -50000},
                {"user_id": "c", "net_balance_minor": 60000},
                {"user_id": "d", "net_balance_minor": 90000},
            ]
        )
        self.assertEqual(
            [
                (item.payer_user_id, item.receiver_user_id, item.amount_minor)
                for item in plan
            ],
            [("a", "d", 90000), ("a", "c", 10000), ("b", "c", 50000)],
        )

    def test_zero_balances_return_empty_plan(self):
        self.assertEqual(
            generate_settlement_plan([{"user_id": "a", "net_balance_minor": 0}]), []
        )

    def test_total_equals_total_positive_balance(self):
        plan = generate_settlement_plan(
            [
                {"user_id": "a", "net_balance_minor": -100000},
                {"user_id": "b", "net_balance_minor": 40000},
                {"user_id": "c", "net_balance_minor": 60000},
            ]
        )
        self.assertEqual(sum(item.amount_minor for item in plan), 100000)

    def test_no_zero_amount_and_no_self_transfer(self):
        plan = generate_settlement_plan(
            [
                {"user_id": "a", "net_balance_minor": -100000},
                {"user_id": "b", "net_balance_minor": 100000},
            ]
        )
        self.assertTrue(all(item.amount_minor > 0 for item in plan))
        self.assertTrue(
            all(item.payer_user_id != item.receiver_user_id for item in plan)
        )

    def test_deterministic_output(self):
        balances = [
            {"user_id": "z", "net_balance_minor": 40000},
            {"user_id": "a", "net_balance_minor": -60000},
            {"user_id": "b", "net_balance_minor": 20000},
            {"user_id": "c", "net_balance_minor": -20000},
        ]
        first = generate_settlement_plan(balances)
        second = generate_settlement_plan(list(reversed(balances)))
        self.assertEqual(first, second)
