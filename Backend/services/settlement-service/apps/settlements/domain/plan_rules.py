from apps.settlements.domain.models import (
    GroupMemberStatusChoices,
    GroupStatusChoices,
    SettlementPlanItemStatusChoices,
    SettlementPlanStatusChoices,
)
from apps.settlements.domain.rules import GroupNotFoundError, SettlementServiceError


class SettlementPlanError(SettlementServiceError):
    code = "SETTLEMENT_PLAN_ERROR"
    message = "A settlement plan error occurred."
    status_code = 400

    def __init__(self, message=None):
        super().__init__(message or self.message)
        if message:
            self.message = message


class NoBalancesFoundError(SettlementPlanError):
    code = "NO_BALANCES_FOUND"
    message = "No balances were found for this group."
    status_code = 404


class SettlementPlanNotFoundError(SettlementPlanError):
    code = "SETTLEMENT_PLAN_NOT_FOUND"
    message = "Settlement plan was not found."
    status_code = 404


class SettlementPlanAlreadyActiveError(SettlementPlanError):
    code = "SETTLEMENT_PLAN_ALREADY_ACTIVE"
    message = "There is already an active settlement plan for this group."
    status_code = 409


class SettlementPlanExpiredError(SettlementPlanError):
    code = "SETTLEMENT_PLAN_EXPIRED"
    message = "This settlement plan is no longer valid because group balances changed."
    status_code = 409


class InvalidPlanItemActionError(SettlementPlanError):
    code = "INVALID_PLAN_ITEM_ACTION"
    message = "This action is not allowed for the current plan item status."
    status_code = 400


class SettlementPlanPermissionDeniedError(SettlementPlanError):
    code = "SETTLEMENT_PLAN_PERMISSION_DENIED"
    message = "You do not have permission to perform this plan action."
    status_code = 403


def ensure_active_group(group):
    if not group:
        raise GroupNotFoundError()
    if group.status != GroupStatusChoices.ACTIVE:
        raise SettlementPlanPermissionDeniedError("Group is not active.")


def ensure_plan_member(member):
    if not member or member.status != GroupMemberStatusChoices.ACTIVE:
        raise SettlementPlanPermissionDeniedError(
            "You are not an active member of this group."
        )


def ensure_owner_or_admin(member):
    ensure_plan_member(member)
    if member.role not in ("OWNER", "ADMIN"):
        raise SettlementPlanPermissionDeniedError()


def ensure_plan_status(plan, allowed_statuses):
    if not plan or plan.status not in allowed_statuses:
        raise InvalidPlanItemActionError()


def ensure_plan_item_status(item, allowed_statuses):
    if not item or item.status not in allowed_statuses:
        raise InvalidPlanItemActionError()


def ensure_plan_item_actor(item, user_id, actor_field):
    if str(getattr(item, actor_field)) != str(user_id):
        raise SettlementPlanPermissionDeniedError()


def is_plan_terminal(status):
    return status in {
        SettlementPlanStatusChoices.COMPLETED,
        SettlementPlanStatusChoices.CANCELLED,
        SettlementPlanStatusChoices.EXPIRED,
    }


def is_item_terminal(status):
    return status in {
        SettlementPlanItemStatusChoices.CONFIRMED,
        SettlementPlanItemStatusChoices.REJECTED,
        SettlementPlanItemStatusChoices.CANCELLED,
    }
