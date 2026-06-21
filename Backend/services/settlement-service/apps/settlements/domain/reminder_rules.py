from __future__ import annotations

from apps.settlements.domain.plan_rules import ensure_owner_or_admin, ensure_plan_member
from apps.settlements.domain.rules import GroupNotFoundError, SettlementServiceError


class ReminderError(SettlementServiceError):
    code = "REMINDER_ERROR"
    message = "A reminder error occurred."
    status_code = 400


class ReminderSettingsValidationError(ReminderError):
    code = "REMINDER_SETTINGS_INVALID"
    message = "Reminder settings are invalid."
    status_code = 400


class ReminderPermissionDeniedError(ReminderError):
    code = "REMINDER_PERMISSION_DENIED"
    message = "You do not have permission to perform this reminder action."
    status_code = 403


class ReminderNotFoundError(ReminderError):
    code = "REMINDER_NOT_FOUND"
    message = "Reminder was not found."
    status_code = 404


class ReminderRateLimitedError(ReminderError):
    code = "REMINDER_RATE_LIMITED"
    message = "A reminder was already requested recently for this settlement item."
    status_code = 409


class ReminderConflictError(ReminderError):
    code = "REMINDER_CONFLICT"
    message = "A reminder already exists for this item and reminder window."
    status_code = 409


class ReminderEligibilityError(ReminderError):
    code = "REMINDER_NOT_ELIGIBLE"
    message = "This settlement item is not eligible for a reminder."
    status_code = 400


def ensure_group_exists(group):
    if not group:
        raise GroupNotFoundError()


def ensure_can_view_settings(member):
    ensure_plan_member(member)


def ensure_can_manage_settings(member):
    try:
        ensure_owner_or_admin(member)
    except SettlementServiceError as exc:
        raise ReminderPermissionDeniedError(str(exc)) from exc


def ensure_can_view_reminder_detail(reminder, user_id, member):
    if str(reminder.recipient_user_id) == str(user_id):
        return
    ensure_can_manage_settings(member)
