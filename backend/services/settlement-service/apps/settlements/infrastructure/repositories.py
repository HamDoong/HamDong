import uuid

from django.utils import timezone

from apps.settlements.domain.models import (
    CurrencyChoices,
    DebtLedgerEntry,
    DebtLedgerEntryTypeChoices,
    DebtLedgerStatusChoices,
    ExpenseParticipantProjection,
    ExpenseProjection,
    ExpenseStatusChoices,
    GroupBalanceSnapshot,
    GroupMemberProjection,
    GroupProjection,
    GroupStatusChoices,
    ManualSettlement,
    ManualSettlementStatusChoices,
    ProcessedEvent,
    UserProjection,
)


def normalize_uuid(value):
    if value in (None, ""):
        return None
    if isinstance(value, uuid.UUID):
        return value
    return uuid.UUID(str(value))


class UserProjectionRepository:
    @staticmethod
    def upsert_from_event(**data):
        identity_user_id = normalize_uuid(
            data.get("user_id") or data.get("identity_user_id")
        )
        if not identity_user_id:
            return None
        defaults = {
            "phone_number": data.get("phone_number", ""),
            "display_name": data.get("display_name"),
            "first_name": data.get("first_name"),
            "last_name": data.get("last_name"),
            "role": data.get("role", "USER"),
            "is_active": data.get("is_active", True),
        }
        obj, _ = UserProjection.objects.update_or_create(
            identity_user_id=identity_user_id, defaults=defaults
        )
        return obj

    @staticmethod
    def get(identity_user_id):
        return UserProjection.objects.filter(
            identity_user_id=normalize_uuid(identity_user_id)
        ).first()


class GroupProjectionRepository:
    @staticmethod
    def upsert_from_event(**data):
        group_id = normalize_uuid(data.get("group_id"))
        if not group_id:
            return None
        current = GroupProjection.objects.filter(group_id=group_id).first()
        defaults = {
            "title": data.get("title")
            or (current.title if current else "Untitled group"),
            "group_type": data.get("group_type")
            or (current.group_type if current else "GENERAL"),
            "status": data.get("status")
            or (current.status if current else GroupStatusChoices.ACTIVE),
            "created_by_user_id": normalize_uuid(
                data.get("created_by_user_id")
                or data.get("created_by")
                or (current.created_by_user_id if current else group_id)
            ),
            "member_count": (
                data.get("member_count")
                if data.get("member_count") is not None
                else (current.member_count if current else 0)
            ),
        }
        obj, _ = GroupProjection.objects.update_or_create(
            group_id=group_id, defaults=defaults
        )
        return obj

    @staticmethod
    def get(group_id):
        return GroupProjection.objects.filter(group_id=normalize_uuid(group_id)).first()

    @staticmethod
    def refresh_member_count(group_id):
        group = GroupProjectionRepository.get(group_id)
        if not group:
            return None
        group.member_count = GroupMemberProjection.objects.filter(
            group_id=group.group_id, status="ACTIVE"
        ).count()
        group.save(update_fields=["member_count", "updated_at"])
        return group


class GroupMemberProjectionRepository:
    @staticmethod
    def _display_snapshot(user_id):
        user = UserProjectionRepository.get(user_id)
        if not user:
            return None, ""
        return user.display_name, user.phone_number

    @staticmethod
    def upsert_joined(**data):
        group_id = normalize_uuid(data.get("group_id"))
        user_id = normalize_uuid(data.get("user_id"))
        if not group_id or not user_id:
            return None
        display_name = data.get("display_name_snapshot") or data.get("display_name")
        phone_number = data.get("phone_number")
        if not phone_number:
            fallback_display, phone_number = (
                GroupMemberProjectionRepository._display_snapshot(user_id)
            )
            display_name = display_name or fallback_display
        defaults = {
            "phone_number": phone_number or "",
            "display_name_snapshot": display_name,
            "role": data.get("role", "MEMBER"),
            "status": "ACTIVE",
            "joined_at": data.get("joined_at") or timezone.now(),
            "left_at": None,
            "removed_at": None,
        }
        obj, _ = GroupMemberProjection.objects.update_or_create(
            group_id=group_id, user_id=user_id, defaults=defaults
        )
        GroupProjectionRepository.refresh_member_count(group_id)
        return obj

    @staticmethod
    def mark_left(**data):
        group_id = normalize_uuid(data.get("group_id"))
        user_id = normalize_uuid(data.get("user_id") or data.get("member_user_id"))
        if not group_id or not user_id:
            return None
        member = GroupMemberProjection.objects.filter(
            group_id=group_id, user_id=user_id
        ).first()
        if not member:
            member = GroupMemberProjection(
                group_id=group_id,
                user_id=user_id,
                phone_number=data.get("phone_number", ""),
                role=data.get("role", "MEMBER"),
            )
        member.status = "LEFT"
        member.left_at = timezone.now()
        member.removed_at = None
        member.save()
        GroupProjectionRepository.refresh_member_count(group_id)
        return member

    @staticmethod
    def mark_removed(**data):
        group_id = normalize_uuid(data.get("group_id"))
        user_id = normalize_uuid(data.get("user_id") or data.get("member_user_id"))
        if not group_id or not user_id:
            return None
        member = GroupMemberProjection.objects.filter(
            group_id=group_id, user_id=user_id
        ).first()
        if not member:
            member = GroupMemberProjection(
                group_id=group_id,
                user_id=user_id,
                phone_number=data.get("phone_number", ""),
                role=data.get("role", "MEMBER"),
            )
        member.status = "REMOVED"
        member.removed_at = timezone.now()
        member.left_at = None
        member.save()
        GroupProjectionRepository.refresh_member_count(group_id)
        return member

    @staticmethod
    def get_active_member(group_id, user_id):
        return GroupMemberProjection.objects.filter(
            group_id=normalize_uuid(group_id),
            user_id=normalize_uuid(user_id),
            status="ACTIVE",
        ).first()

    @staticmethod
    def get(group_id, user_id):
        return GroupMemberProjection.objects.filter(
            group_id=normalize_uuid(group_id), user_id=normalize_uuid(user_id)
        ).first()

    @staticmethod
    def list_active_members(group_id):
        return GroupMemberProjection.objects.filter(
            group_id=normalize_uuid(group_id), status="ACTIVE"
        )


class ExpenseProjectionRepository:
    @staticmethod
    def upsert_from_event(**data):
        expense_id = normalize_uuid(data.get("expense_id"))
        if not expense_id:
            return None
        current = ExpenseProjection.objects.filter(expense_id=expense_id).first()
        group_id = normalize_uuid(
            data.get("group_id") or (current.group_id if current else None)
        )
        created_by_user_id = normalize_uuid(
            data.get("created_by_user_id")
            or (current.created_by_user_id if current else group_id)
        )
        payer_user_id = normalize_uuid(
            data.get("payer_user_id")
            or (current.payer_user_id if current else created_by_user_id)
        )
        defaults = {
            "group_id": group_id,
            "created_by_user_id": created_by_user_id,
            "payer_user_id": payer_user_id,
            "currency": data.get("currency")
            or (current.currency if current else CurrencyChoices.IRR),
            "base_amount_minor": int(
                data.get("base_amount_minor")
                or (current.base_amount_minor if current else 0)
            ),
            "tax_amount_minor": int(
                data.get("tax_amount_minor")
                or (current.tax_amount_minor if current else 0)
            ),
            "service_fee_amount_minor": int(
                data.get("service_fee_amount_minor")
                or (current.service_fee_amount_minor if current else 0)
            ),
            "total_amount_minor": int(
                data.get("total_amount_minor")
                or (current.total_amount_minor if current else 0)
            ),
            "status": data.get("status")
            or (current.status if current else ExpenseStatusChoices.ACTIVE),
            "expense_version": int(
                data.get("expense_version")
                or data.get("new_version")
                or (current.expense_version if current else 1)
            ),
            "expense_date": data.get("expense_date")
            or (current.expense_date if current else timezone.now()),
        }
        obj, _ = ExpenseProjection.objects.update_or_create(
            expense_id=expense_id, defaults=defaults
        )
        return obj

    @staticmethod
    def get(expense_id):
        return ExpenseProjection.objects.filter(
            expense_id=normalize_uuid(expense_id)
        ).first()

    @staticmethod
    def mark_deleted(expense_id):
        expense = ExpenseProjectionRepository.get(expense_id)
        if not expense:
            return None
        expense.status = ExpenseStatusChoices.DELETED
        expense.deleted_at = timezone.now()
        expense.expense_version += 1
        expense.save(
            update_fields=["status", "deleted_at", "expense_version", "updated_at"]
        )
        return expense

    @staticmethod
    def list_by_group(group_id):
        return ExpenseProjection.objects.filter(
            group_id=normalize_uuid(group_id)
        ).order_by("-created_at")


class ExpenseParticipantProjectionRepository:
    @staticmethod
    def replace_for_expense(expense: ExpenseProjection, participants):
        ExpenseParticipantProjection.objects.filter(
            expense_id=expense.expense_id
        ).delete()
        rows = []
        for participant in participants:
            rows.append(
                ExpenseParticipantProjection(
                    expense_id=expense.expense_id,
                    group_id=expense.group_id,
                    user_id=normalize_uuid(participant.get("user_id")),
                    base_share_minor=int(participant.get("base_share_minor", 0)),
                    tax_share_minor=int(participant.get("tax_share_minor", 0)),
                    service_fee_share_minor=int(
                        participant.get("service_fee_share_minor", 0)
                    ),
                    total_share_minor=int(participant.get("total_share_minor", 0)),
                )
            )
        ExpenseParticipantProjection.objects.bulk_create(rows)
        return rows

    @staticmethod
    def list_for_expense(expense_id):
        return ExpenseParticipantProjection.objects.filter(
            expense_id=normalize_uuid(expense_id)
        ).order_by("created_at")

    @staticmethod
    def delete_for_expense(expense_id):
        ExpenseParticipantProjection.objects.filter(
            expense_id=normalize_uuid(expense_id)
        ).delete()


class DebtLedgerRepository:
    @staticmethod
    def create_expense_entries(expense: ExpenseProjection, participants):
        entries = []
        for participant in participants:
            user_id = normalize_uuid(participant.get("user_id"))
            if not user_id or user_id == expense.payer_user_id:
                continue
            amount_minor = int(participant.get("total_share_minor", 0))
            if amount_minor <= 0:
                continue
            entries.append(
                DebtLedgerEntry(
                    group_id=expense.group_id,
                    source_expense_id=expense.expense_id,
                    source_expense_version=expense.expense_version,
                    debtor_user_id=user_id,
                    creditor_user_id=expense.payer_user_id,
                    amount_minor=amount_minor,
                    currency=expense.currency,
                    entry_type=DebtLedgerEntryTypeChoices.EXPENSE_SHARE,
                    status=DebtLedgerStatusChoices.ACTIVE,
                )
            )
        return DebtLedgerEntry.objects.bulk_create(entries)

    @staticmethod
    def create_manual_settlement_entry(settlement: ManualSettlement):
        return DebtLedgerEntry.objects.create(
            group_id=settlement.group_id,
            source_expense_id=None,
            source_expense_version=0,
            debtor_user_id=settlement.receiver_user_id,
            creditor_user_id=settlement.payer_user_id,
            amount_minor=settlement.amount_minor,
            currency=settlement.currency,
            entry_type=DebtLedgerEntryTypeChoices.MANUAL_SETTLEMENT,
            status=DebtLedgerStatusChoices.ACTIVE,
            metadata={"settlement_id": str(settlement.id)},
        )

    @staticmethod
    def reverse_active_for_expense(expense_id):
        now = timezone.now()
        entries = DebtLedgerEntry.objects.filter(
            source_expense_id=normalize_uuid(expense_id),
            status=DebtLedgerStatusChoices.ACTIVE,
        )
        entries.update(status=DebtLedgerStatusChoices.REVERSED, reversed_at=now)
        return list(entries)

    @staticmethod
    def active_for_expense(expense_id):
        return DebtLedgerEntry.objects.filter(
            source_expense_id=normalize_uuid(expense_id),
            status=DebtLedgerStatusChoices.ACTIVE,
        )

    @staticmethod
    def active_by_group(group_id):
        return DebtLedgerEntry.objects.filter(
            group_id=normalize_uuid(group_id), status=DebtLedgerStatusChoices.ACTIVE
        ).order_by("created_at")

    @staticmethod
    def all_by_group(group_id):
        return DebtLedgerEntry.objects.filter(
            group_id=normalize_uuid(group_id)
        ).order_by("created_at")


class GroupBalanceSnapshotRepository:
    @staticmethod
    def upsert_snapshot(group_id, user_id, currency, totals):
        defaults = {
            "total_paid_minor": totals.get("total_paid_minor", 0),
            "total_share_minor": totals.get("total_share_minor", 0),
            "total_settled_paid_minor": totals.get("total_settled_paid_minor", 0),
            "total_settled_received_minor": totals.get(
                "total_settled_received_minor", 0
            ),
            "net_balance_minor": totals.get("net_balance_minor", 0),
            "calculated_at": timezone.now(),
        }
        obj, _ = GroupBalanceSnapshot.objects.update_or_create(
            group_id=normalize_uuid(group_id),
            user_id=normalize_uuid(user_id),
            currency=currency,
            defaults=defaults,
        )
        return obj

    @staticmethod
    def list_by_group(group_id, currency=None):
        qs = GroupBalanceSnapshot.objects.filter(
            group_id=normalize_uuid(group_id)
        ).order_by("user_id")
        if currency:
            qs = qs.filter(currency=currency)
        return qs

    @staticmethod
    def get(group_id, user_id, currency="IRR"):
        return GroupBalanceSnapshot.objects.filter(
            group_id=normalize_uuid(group_id),
            user_id=normalize_uuid(user_id),
            currency=currency,
        ).first()

    @staticmethod
    def delete_missing(group_id, user_ids, currency="IRR"):
        GroupBalanceSnapshot.objects.filter(
            group_id=normalize_uuid(group_id), currency=currency
        ).exclude(
            user_id__in=[normalize_uuid(user_id) for user_id in user_ids]
        ).delete()


class ManualSettlementRepository:
    @staticmethod
    def create_pending(**data):
        return ManualSettlement.objects.create(
            group_id=normalize_uuid(data.get("group_id")),
            payer_user_id=normalize_uuid(data.get("payer_user_id")),
            receiver_user_id=normalize_uuid(data.get("receiver_user_id")),
            amount_minor=int(data.get("amount_minor", 0)),
            currency=data.get("currency", CurrencyChoices.IRR),
            description=data.get("description"),
            status=ManualSettlementStatusChoices.PENDING_CONFIRMATION,
            created_by_user_id=normalize_uuid(
                data.get("created_by_user_id") or data.get("payer_user_id")
            ),
        )

    @staticmethod
    def get(settlement_id):
        return ManualSettlement.objects.filter(id=normalize_uuid(settlement_id)).first()

    @staticmethod
    def list_by_group(group_id, filters=None):
        qs = ManualSettlement.objects.filter(
            group_id=normalize_uuid(group_id)
        ).order_by("-created_at")
        filters = filters or {}
        if filters.get("status"):
            qs = qs.filter(status=filters["status"])
        if filters.get("payer_user_id"):
            qs = qs.filter(payer_user_id=normalize_uuid(filters["payer_user_id"]))
        if filters.get("receiver_user_id"):
            qs = qs.filter(receiver_user_id=normalize_uuid(filters["receiver_user_id"]))
        return qs

    @staticmethod
    def confirm(settlement: ManualSettlement, confirmed_by_user_id):
        settlement.status = ManualSettlementStatusChoices.CONFIRMED
        settlement.confirmed_by_user_id = normalize_uuid(confirmed_by_user_id)
        settlement.confirmed_at = timezone.now()
        settlement.save(
            update_fields=[
                "status",
                "confirmed_by_user_id",
                "confirmed_at",
                "updated_at",
            ]
        )
        return settlement

    @staticmethod
    def reject(settlement: ManualSettlement, rejected_by_user_id):
        settlement.status = ManualSettlementStatusChoices.REJECTED
        settlement.rejected_by_user_id = normalize_uuid(rejected_by_user_id)
        settlement.rejected_at = timezone.now()
        settlement.save(
            update_fields=["status", "rejected_by_user_id", "rejected_at", "updated_at"]
        )
        return settlement

    @staticmethod
    def cancel(settlement: ManualSettlement, cancelled_by_user_id):
        settlement.status = ManualSettlementStatusChoices.CANCELLED
        settlement.cancelled_by_user_id = normalize_uuid(cancelled_by_user_id)
        settlement.cancelled_at = timezone.now()
        settlement.save(
            update_fields=[
                "status",
                "cancelled_by_user_id",
                "cancelled_at",
                "updated_at",
            ]
        )
        return settlement


class ProcessedEventRepository:
    @staticmethod
    def was_processed(event_id):
        return ProcessedEvent.objects.filter(event_id=normalize_uuid(event_id)).exists()

    @staticmethod
    def mark_processed(event_id, event_type, source_service):
        event_id = normalize_uuid(event_id)
        if not event_id:
            return None, False
        obj, created = ProcessedEvent.objects.get_or_create(
            event_id=event_id,
            defaults={
                "event_type": event_type,
                "source_service": source_service,
                "processed_at": timezone.now(),
            },
        )
        return obj, created
