from collections import defaultdict

from django.utils import timezone

from apps.settlements.domain.models import CurrencyChoices, DebtLedgerEntryTypeChoices
from apps.settlements.domain.rules import (
    balance_status,
    ensure_active_member,
    ensure_group_active,
    mask_email,
)
from apps.settlements.infrastructure.repositories import (
    DebtLedgerRepository,
    GroupBalanceSnapshotRepository,
    GroupMemberProjectionRepository,
    GroupProjectionRepository,
)


class BalanceService:
    def recalculate_group(self, group_id, currency=CurrencyChoices.IRR):
        group = GroupProjectionRepository.get(group_id)
        if not group:
            return []
        active_members = list(
            GroupMemberProjectionRepository.list_active_members(group_id)
        )
        active_user_ids = {member.user_id for member in active_members}
        for entry in DebtLedgerRepository.all_by_group(group_id):
            active_user_ids.add(entry.debtor_user_id)
            active_user_ids.add(entry.creditor_user_id)

        totals = defaultdict(
            lambda: {
                "total_paid_minor": 0,
                "total_share_minor": 0,
                "total_settled_paid_minor": 0,
                "total_settled_received_minor": 0,
                "net_balance_minor": 0,
            }
        )

        for entry in DebtLedgerRepository.active_by_group(group_id).filter(
            currency=currency
        ):
            debtor = totals[entry.debtor_user_id]
            creditor = totals[entry.creditor_user_id]
            if entry.entry_type == DebtLedgerEntryTypeChoices.MANUAL_SETTLEMENT:
                debtor["total_settled_received_minor"] += entry.amount_minor
                creditor["total_settled_paid_minor"] += entry.amount_minor
            else:
                debtor["total_share_minor"] += entry.amount_minor
                creditor["total_paid_minor"] += entry.amount_minor

        snapshots = []
        for user_id in active_user_ids:
            values = totals[user_id]
            net_balance = (
                values["total_paid_minor"]
                + values["total_settled_paid_minor"]
                - values["total_share_minor"]
                - values["total_settled_received_minor"]
            )
            values["net_balance_minor"] = net_balance
            snapshot = GroupBalanceSnapshotRepository.upsert_snapshot(
                group_id, user_id, currency, values
            )
            snapshots.append(snapshot)

        GroupBalanceSnapshotRepository.delete_missing(
            group_id, active_user_ids, currency=currency
        )
        return snapshots

    def my_balance(self, group_id, user_id, currency=CurrencyChoices.IRR):
        snapshot = GroupBalanceSnapshotRepository.get(
            group_id, user_id, currency=currency
        )
        if snapshot:
            return snapshot
        snapshots = self.recalculate_group(group_id, currency=currency)
        for item in snapshots:
            if str(item.user_id) == str(user_id):
                return item
        return GroupBalanceSnapshotRepository.get(group_id, user_id, currency=currency)

    def format_snapshot(self, snapshot, member=None):
        email = member.email if member else ""
        art_name = member.art_name_snapshot if member else None
        if member is None:
            art_name = None
        return {
            "user_id": str(snapshot.user_id),
            "art_name": art_name,
            "email": mask_email(email),
            "net_balance_minor": snapshot.net_balance_minor,
            "status": balance_status(snapshot.net_balance_minor),
        }

    def render_group_balances(
        self, group_id, requester_user_id=None, currency=CurrencyChoices.IRR
    ):
        ensure_group_active(GroupProjectionRepository.get(group_id))
        if requester_user_id is not None:
            ensure_active_member(
                GroupMemberProjectionRepository.get_active_member(
                    group_id, requester_user_id
                )
            )
        self.recalculate_group(group_id, currency=currency)
        members = {
            member.user_id: member
            for member in GroupMemberProjectionRepository.list_active_members(group_id)
        }
        results = []
        for snapshot in GroupBalanceSnapshotRepository.list_by_group(
            group_id, currency=currency
        ):
            member = members.get(snapshot.user_id)
            if member:
                results.append(self.format_snapshot(snapshot, member))
        results.sort(key=lambda item: item["net_balance_minor"], reverse=True)
        return {
            "group_id": str(group_id),
            "currency": currency,
            "balances": results,
            "calculated_at": timezone.now().isoformat(),
        }

    def render_my_balance(self, group_id, user_id, currency=CurrencyChoices.IRR):
        ensure_group_active(GroupProjectionRepository.get(group_id))
        ensure_active_member(
            GroupMemberProjectionRepository.get_active_member(group_id, user_id)
        )
        snapshot = self.my_balance(group_id, user_id, currency=currency)
        if not snapshot:
            return None
        return {
            "group_id": str(group_id),
            "user_id": str(user_id),
            "currency": currency,
            "net_balance_minor": snapshot.net_balance_minor,
            "status": balance_status(snapshot.net_balance_minor),
        }

    def render_group_debts(
        self, group_id, requester_user_id=None, currency=CurrencyChoices.IRR
    ):
        ensure_group_active(GroupProjectionRepository.get(group_id))
        if requester_user_id is not None:
            ensure_active_member(
                GroupMemberProjectionRepository.get_active_member(
                    group_id, requester_user_id
                )
            )
        debts = DebtLedgerRepository.active_by_group(group_id).filter(currency=currency)
        return {
            "group_id": str(group_id),
            "currency": currency,
            "debts": [
                {
                    "id": str(entry.id),
                    "source_expense_id": (
                        str(entry.source_expense_id)
                        if entry.source_expense_id
                        else None
                    ),
                    "debtor_user_id": str(entry.debtor_user_id),
                    "creditor_user_id": str(entry.creditor_user_id),
                    "amount_minor": entry.amount_minor,
                    "status": entry.status,
                    "entry_type": entry.entry_type,
                }
                for entry in debts
            ],
        }
