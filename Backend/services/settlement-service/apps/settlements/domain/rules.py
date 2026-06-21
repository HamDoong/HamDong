from apps.settlements.domain.models import (
    GroupStatusChoices,
    GroupMemberStatusChoices,
    ManualSettlementStatusChoices,
)


class SettlementServiceError(Exception):
    code = "SETTLEMENT_SERVICE_ERROR"
    message = "A settlement service error occurred."
    status_code = 400

    def __init__(self, message=None):
        super().__init__(message or self.message)
        if message:
            self.message = message


class SettlementNotFoundError(SettlementServiceError):
    code = "SETTLEMENT_NOT_FOUND"
    message = "Settlement was not found."
    status_code = 404


class GroupNotFoundError(SettlementServiceError):
    code = "GROUP_NOT_FOUND"
    message = "Group was not found."
    status_code = 404


class NotGroupMemberError(SettlementServiceError):
    code = "NOT_GROUP_MEMBER"
    message = "You are not an active member of this group."
    status_code = 403


class SettlementPermissionDeniedError(SettlementServiceError):
    code = "SETTLEMENT_PERMISSION_DENIED"
    message = "You do not have permission to perform this settlement action."
    status_code = 403


class InvalidSettlementAmountError(SettlementServiceError):
    code = "INVALID_SETTLEMENT_AMOUNT"
    message = "Settlement amount must be greater than zero."
    status_code = 400


class SettlementAmountLimitExceededError(SettlementServiceError):
    code = "SETTLEMENT_AMOUNT_LIMIT_EXCEEDED"
    message = "Settlement amount exceeds the allowed maximum."
    status_code = 400


class InvalidSettlementParticipantError(SettlementServiceError):
    code = "INVALID_SETTLEMENT_PARTICIPANT"
    message = "Payer and receiver must be different active group members."
    status_code = 400


class InvalidSettlementStatusError(SettlementServiceError):
    code = "INVALID_SETTLEMENT_STATUS"
    message = "This settlement cannot be modified in its current status."
    status_code = 400


class InvalidCurrencyError(SettlementServiceError):
    code = "INVALID_CURRENCY"
    message = "Only IRR currency is supported in this phase."
    status_code = 400


class InvalidEventPayloadError(SettlementServiceError):
    code = "INVALID_EVENT_PAYLOAD"
    message = "Event payload is invalid."
    status_code = 400


def ensure_group_active(group):
    if not group:
        raise GroupNotFoundError()
    if group.status != GroupStatusChoices.ACTIVE:
        raise SettlementPermissionDeniedError("Group is not active.")


def ensure_active_member(member):
    if not member or member.status != GroupMemberStatusChoices.ACTIVE:
        raise NotGroupMemberError()


def ensure_settlement_can_be_modified(settlement):
    if settlement.status != ManualSettlementStatusChoices.PENDING_CONFIRMATION:
        raise InvalidSettlementStatusError()


def ensure_different_participants(payer_user_id, receiver_user_id):
    if str(payer_user_id) == str(receiver_user_id):
        raise InvalidSettlementParticipantError()


def ensure_positive_amount(amount_minor):
    if int(amount_minor) <= 0:
        raise InvalidSettlementAmountError()


def ensure_amount_within_limit(amount_minor, max_amount_minor):
    if int(amount_minor) > int(max_amount_minor):
        raise SettlementAmountLimitExceededError()


def ensure_irr_currency(currency):
    if currency != "IRR":
        raise InvalidCurrencyError()


def mask_email(email):
    if not email:
        return ""
    value = str(email).strip()
    if "@" not in value:
        return "***"
    local_part, domain = value.split("@", 1)
    if len(local_part) <= 2:
        masked_local = local_part[:1] + "***"
    else:
        masked_local = local_part[:2] + "***"
    return f"{masked_local}@{domain}"


def balance_status(net_balance_minor):
    if net_balance_minor > 0:
        return "CREDITOR"
    if net_balance_minor < 0:
        return "DEBTOR"
    return "SETTLED"
