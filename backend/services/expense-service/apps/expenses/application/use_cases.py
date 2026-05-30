from django.conf import settings
from decimal import Decimal
from apps.expenses.infrastructure.repositories import ProjectionRepository, ExpenseRepository
from apps.expenses.application.split_calculator import equal_split, custom_split
from apps.expenses.application.tax_calculator import compute_percentage_amount, distribute_proportional
from apps.expenses.infrastructure.rabbitmq_publisher import RabbitMQPublisher
from apps.expenses.domain.models import Expense
from django.utils import timezone


class ExpenseService:
    def __init__(self, publisher: RabbitMQPublisher = None):
        self.publisher = publisher or RabbitMQPublisher()

    def create_expense(self, group_id, creator, payload):
        # basic validations
        group = ProjectionRepository.get_group(group_id)
        if not group or group.status != "ACTIVE":
            raise ValueError("GROUP_NOT_ACTIVE")

        if not ProjectionRepository.is_active_member(group_id, creator.sub):
            raise PermissionError("NOT_GROUP_MEMBER")

        payer = payload.get("payer_user_id")
        if not ProjectionRepository.is_active_member(group_id, payer):
            raise ValueError("INVALID_PARTICIPANT")

        base_amount = int(payload.get("base_amount_minor"))
        if base_amount <= 0:
            raise ValueError("INVALID_AMOUNT")

        split_method = payload.get("split_method")
        participants_map = {}
        if split_method == "EQUAL":
            pids = payload.get("participant_user_ids", [])
            shares = equal_split(pids, base_amount)
            participants_map = {pid: shares[pid] for pid in pids}
        elif split_method == "CUSTOM_AMOUNT":
            parts = payload.get("participants", [])
            shares = custom_split(parts, base_amount)
            participants_map = shares
        else:
            raise ValueError("INVALID_SPLIT_METHOD")

        # tax
        tax_type = payload.get("tax_type", "NONE")
        tax_amount = 0
        if tax_type == "PERCENTAGE":
            tax_percentage = Decimal(str(payload.get("tax_percentage", "0")))
            tax_amount = compute_percentage_amount(base_amount, tax_percentage)
        elif tax_type == "FIXED":
            tax_amount = int(payload.get("tax_amount_minor", 0))

        service_fee_type = payload.get("service_fee_type", "NONE")
        service_fee_amount = 0
        if service_fee_type == "PERCENTAGE":
            sf_percentage = Decimal(str(payload.get("service_fee_percentage", "0")))
            service_fee_amount = compute_percentage_amount(base_amount, sf_percentage)
        elif service_fee_type == "FIXED":
            service_fee_amount = int(payload.get("service_fee_amount_minor", 0))

        total = base_amount + tax_amount + service_fee_amount

        # distribute tax & service fee proportionally
        tax_shares = distribute_proportional(tax_amount, participants_map)
        sf_shares = distribute_proportional(service_fee_amount, participants_map)

        # create expense
        expense = ExpenseRepository.create_expense(
            group_id=group_id,
            created_by_user_id=creator.sub,
            payer_user_id=payer,
            title=payload.get("title"),
            description=payload.get("description"),
            currency=payload.get("currency", "IRR"),
            base_amount_minor=base_amount,
            tax_type=tax_type,
            tax_amount_minor=tax_amount,
            service_fee_type=service_fee_type,
            service_fee_amount_minor=service_fee_amount,
            total_amount_minor=total,
            split_method=split_method,
            expense_date=payload.get("expense_date", timezone.now()),
        )

        participants = []
        for uid, base_share in participants_map.items():
            tshare = tax_shares.get(uid, 0)
            sfshare = sf_shares.get(uid, 0)
            participants.append({
                "user_id": uid,
                "phone_number": "",
                "display_name_snapshot": None,
                "base_share_minor": base_share,
                "tax_share_minor": tshare,
                "service_fee_share_minor": sfshare,
                "total_share_minor": base_share + tshare + sfshare,
            })

        ExpenseRepository.add_participants(expense, participants)

        # publish event
        # publish created event including participants
        self.publisher.publish("ExpenseCreated", {
            "expense_id": str(expense.id),
            "group_id": str(group_id),
            "created_by_user_id": str(creator.sub),
            "payer_user_id": str(payer),
            "currency": expense.currency,
            "base_amount_minor": base_amount,
            "tax_amount_minor": tax_amount,
            "service_fee_amount_minor": service_fee_amount,
            "total_amount_minor": total,
            "participants": participants,
        }, "expense.created")

        return expense
    
    def list_expenses(self, group_id, requester, filters: dict = None, page: int = 1, page_size: int = 50):
        group = ProjectionRepository.get_group(group_id)
        if not group or group.status != "ACTIVE":
            raise ValueError("GROUP_NOT_ACTIVE")
        if not ProjectionRepository.is_active_member(group_id, requester.sub):
            raise PermissionError("NOT_GROUP_MEMBER")

        return ExpenseRepository.list_by_group(group_id, filters=filters, page=page, page_size=page_size)

    def get_expense(self, expense_id, requester):
        expense = ExpenseRepository.get_by_id(expense_id)
        if not expense or expense.status == "DELETED":
            raise ValueError("NOT_FOUND")
        if not ProjectionRepository.is_active_member(expense.group_id, requester.sub):
            raise PermissionError("NOT_GROUP_MEMBER")
        return expense

    def update_expense(self, expense_id, requester, payload):
        expense = ExpenseRepository.get_by_id(expense_id)
        if not expense or expense.status == "DELETED":
            raise ValueError("NOT_FOUND")

        # check permissions: creator or group owner/admin
        if str(requester.sub) != str(expense.created_by_user_id):
            member = ProjectionRepository.get_member(expense.group_id, requester.sub)
            if not member or member.role not in ("OWNER", "ADMIN"):
                raise PermissionError("NOT_ALLOWED")

        # For brevity, support updating title, description, base_amount_minor, tax/service params, participants
        updatable = {}
        allowed = ["title", "description", "base_amount_minor", "tax_type", "tax_percentage", "tax_amount_minor", "service_fee_type", "service_fee_percentage", "service_fee_amount_minor", "split_method", "expense_date"]
        for k in allowed:
            if k in payload:
                updatable[k] = payload[k]

        # Recalculate total and shares using existing create logic patterns
        # Simplified: reuse create logic by constructing a create-like payload
        merged_payload = {
            **{
                "payer_user_id": expense.payer_user_id,
                "base_amount_minor": updatable.get("base_amount_minor", expense.base_amount_minor),
                "split_method": updatable.get("split_method", expense.split_method),
                "participant_user_ids": payload.get("participant_user_ids", []),
                "participants": payload.get("participants", []),
                "tax_type": updatable.get("tax_type", expense.tax_type),
                "tax_percentage": updatable.get("tax_percentage", expense.tax_percentage),
                "tax_amount_minor": updatable.get("tax_amount_minor", expense.tax_amount_minor),
                "service_fee_type": updatable.get("service_fee_type", expense.service_fee_type),
                "service_fee_percentage": updatable.get("service_fee_percentage", expense.service_fee_percentage),
                "service_fee_amount_minor": updatable.get("service_fee_amount_minor", expense.service_fee_amount_minor),
            },
            **updatable,
        }

        # Basic validations similar to create
        base_amount = int(merged_payload.get("base_amount_minor"))
        if base_amount <= 0:
            raise ValueError("INVALID_AMOUNT")

        split_method = merged_payload.get("split_method")
        participants_map = {}
        if split_method == "EQUAL":
            pids = merged_payload.get("participant_user_ids", [])
            shares = equal_split(pids, base_amount)
            participants_map = shares
        elif split_method == "CUSTOM_AMOUNT":
            parts = merged_payload.get("participants", [])
            shares = custom_split(parts, base_amount)
            participants_map = shares
        else:
            raise ValueError("INVALID_SPLIT_METHOD")

        # tax and service fee
        tax_type = merged_payload.get("tax_type", "NONE")
        tax_amount = 0
        if tax_type == "PERCENTAGE":
            tax_percentage = merged_payload.get("tax_percentage")
            tax_amount = compute_percentage_amount(base_amount, tax_percentage)
        elif tax_type == "FIXED":
            tax_amount = int(merged_payload.get("tax_amount_minor", 0))

        service_fee_type = merged_payload.get("service_fee_type", "NONE")
        service_fee_amount = 0
        if service_fee_type == "PERCENTAGE":
            sf_percentage = merged_payload.get("service_fee_percentage")
            service_fee_amount = compute_percentage_amount(base_amount, sf_percentage)
        elif service_fee_type == "FIXED":
            service_fee_amount = int(merged_payload.get("service_fee_amount_minor", 0))

        total = base_amount + tax_amount + service_fee_amount

        tax_shares = distribute_proportional(tax_amount, participants_map)
        sf_shares = distribute_proportional(service_fee_amount, participants_map)

        # persist
        ExpenseRepository.update_expense(expense, **updatable, tax_type=tax_type, tax_amount_minor=tax_amount, service_fee_type=service_fee_type, service_fee_amount_minor=service_fee_amount, total_amount_minor=total, version=expense.version + 1, status="UPDATED")

        # rebuild participants
        participants = []
        for uid, base_share in participants_map.items():
            tshare = tax_shares.get(uid, 0)
            sfshare = sf_shares.get(uid, 0)
            participants.append({
                "user_id": uid,
                "phone_number": "",
                "display_name_snapshot": None,
                "base_share_minor": base_share,
                "tax_share_minor": tshare,
                "service_fee_share_minor": sfshare,
                "total_share_minor": base_share + tshare + sfshare,
            })

        # replace participants (naive approach: delete and add)
        expense.participants.all().delete()
        ExpenseRepository.add_participants(expense, participants)

        # publish
        # publish updated event including participants and versioning
        self.publisher.publish("ExpenseUpdated", {
            "expense_id": str(expense.id),
            "previous_version": expense.version,
            "new_version": expense.version + 1,
            "participants": participants,
            "total_amount_minor": total,
        }, "expense.updated")

        return expense

    def delete_expense(self, expense_id, requester):
        expense = ExpenseRepository.get_by_id(expense_id)
        if not expense or expense.status == "DELETED":
            raise ValueError("NOT_FOUND")

        if str(requester.sub) != str(expense.created_by_user_id):
            member = ProjectionRepository.get_member(expense.group_id, requester.sub)
            if not member or member.role not in ("OWNER", "ADMIN"):
                raise PermissionError("NOT_ALLOWED")

        ExpenseRepository.soft_delete(expense)
        self.publisher.publish("ExpenseDeleted", {"expense_id": str(expense.id)}, "expense.deleted")
        return expense
"""Use case orchestration for expense-service."""
