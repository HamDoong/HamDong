from apps.settlements.application.reminder_service import ReminderService


class GetReminderSettingsUseCase:
    def __init__(self, reminder_service=None):
        self.reminder_service = reminder_service or ReminderService()

    def execute(self, user, group_id):
        return self.reminder_service.get_group_settings(group_id, user.sub)


class UpdateReminderSettingsUseCase:
    def __init__(self, reminder_service=None):
        self.reminder_service = reminder_service or ReminderService()

    def execute(self, user, group_id, payload):
        return self.reminder_service.update_group_settings(group_id, user.sub, payload)


class ListReminderHistoryUseCase:
    def __init__(self, reminder_service=None):
        self.reminder_service = reminder_service or ReminderService()

    def execute(self, user, group_id, filters):
        return self.reminder_service.list_group_history(group_id, user.sub, filters)


class GetReminderDetailUseCase:
    def __init__(self, reminder_service=None):
        self.reminder_service = reminder_service or ReminderService()

    def execute(self, user, reminder_id):
        return self.reminder_service.get_reminder_detail(reminder_id, user.sub)


class RunGroupReminderUseCase:
    def __init__(self, reminder_service=None):
        self.reminder_service = reminder_service or ReminderService()

    def execute(self, user, group_id, *, dry_run=False):
        return self.reminder_service.run_group_manual(group_id, user.sub, dry_run=dry_run)


class SendManualItemReminderUseCase:
    def __init__(self, reminder_service=None):
        self.reminder_service = reminder_service or ReminderService()

    def execute(self, user, item_id, payload):
        return self.reminder_service.send_manual_item_reminder(item_id, user.sub, payload)
