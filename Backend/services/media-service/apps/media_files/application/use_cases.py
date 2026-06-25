from django.db import transaction

from apps.media_files.application.file_validator import MediaFileNotFoundError, MediaPermissionDeniedError, NotGroupMemberError
from apps.media_files.application.media_service import ExpenseNotFoundError, InvalidCursorError, MediaService
from apps.media_files.application.upload_service import UploadReceiptService
from apps.media_files.domain.events import MediaDeleted
from apps.media_files.domain.models import MediaAccessActionChoices
from apps.media_files.infrastructure.rabbitmq_publisher import RabbitMQPublisher
from apps.media_files.infrastructure.repositories import GroupMemberProjectionRepository, MediaFileRepository


class UploadReceiptUseCase:
    def __init__(self, service=None):
        self.service = service or UploadReceiptService()

    def execute(self, user, group_id, uploaded_file, related_expense_id=None, request=None):
        return self.service.execute(user, group_id, uploaded_file, related_expense_id=related_expense_id, request=request)


class GetMediaDetailUseCase:
    def __init__(self, media_service=None):
        self.media_service = media_service or MediaService()

    def execute(self, user, media_file_id, request=None):
        media_file = self.media_service._get_media_or_raise(media_file_id)
        self.media_service.ensure_view_access(media_file, user.sub)
        self.media_service.upload_access_log(media_file, user.sub, MediaAccessActionChoices.VIEW, request=request)
        return media_file


class DownloadMediaUseCase:
    def __init__(self, media_service=None):
        self.media_service = media_service or MediaService()

    def execute(self, user, media_file_id, request=None):
        media_file = self.media_service._get_media_or_raise(media_file_id)
        self.media_service.ensure_view_access(media_file, user.sub)
        self.media_service.upload_access_log(media_file, user.sub, MediaAccessActionChoices.DOWNLOAD, request=request)
        return media_file, self.media_service.get_file_handle(media_file)


class ListGroupMediaUseCase:
    def __init__(self, media_service=None):
        self.media_service = media_service or MediaService()

    def execute(self, user, group_id, file_type=None, page=1, page_size=20):
        self.media_service._get_group_or_raise(group_id)
        self.media_service._get_active_member_or_raise(group_id, user.sub)
        items, count = MediaFileRepository.list_group_media(group_id, file_type=file_type, page=page, page_size=page_size)
        return items, count


class ListExpenseReceiptsUseCase:
    def __init__(self, media_service=None):
        self.media_service = media_service or MediaService()

    def execute(self, user, expense_id, *, cursor=None, page_size=20, request=None):
        expense = self.media_service._get_expense_or_raise(expense_id)
        self.media_service._get_group_or_raise(expense.group_id)
        self.media_service._get_active_member_or_raise(expense.group_id, user.sub)
        try:
            items, next_cursor = MediaFileRepository.list_expense_receipts(
                expense_id=expense.expense_id,
                group_id=expense.group_id,
                cursor=cursor,
                page_size=page_size,
            )
        except ValueError as exc:
            raise InvalidCursorError() from exc
        self.media_service.upload_list_access_logs(items, user.sub, MediaAccessActionChoices.VIEW, request=request)
        return items, next_cursor

    def serialize(self, items):
        return [self.media_service.to_receipt_payload(item, include_group=False) for item in items]


class ListMyReceiptsUseCase:
    def __init__(self, media_service=None):
        self.media_service = media_service or MediaService()

    def execute(self, user, filters, *, request=None):
        group_id = filters.get("group_id")
        expense_id = filters.get("expense_id")
        if group_id:
            self.media_service._get_group_or_raise(group_id)
            self.media_service._get_active_member_or_raise(group_id, user.sub)
        if expense_id:
            expense = self.media_service._get_expense_or_raise(expense_id)
            self.media_service._get_group_or_raise(expense.group_id)
            self.media_service._get_active_member_or_raise(expense.group_id, user.sub)
            if group_id and str(group_id) != str(expense.group_id):
                raise MediaPermissionDeniedError()
            group_id = expense.group_id

        active_group_ids = GroupMemberProjectionRepository.list_active_group_ids_for_user(user.sub)
        try:
            items, next_cursor = MediaFileRepository.list_user_receipts(
                user_id=user.sub,
                active_group_ids=active_group_ids,
                group_id=group_id,
                expense_id=expense_id,
                uploaded_by_me=filters.get("uploaded_by_me"),
                from_date=filters.get("from_date"),
                to_date=filters.get("to_date"),
                cursor=filters.get("cursor"),
                page_size=filters.get("page_size", 20),
            )
        except ValueError as exc:
            raise InvalidCursorError() from exc
        self.media_service.upload_list_access_logs(items, user.sub, MediaAccessActionChoices.VIEW, request=request)
        return items, next_cursor

    def serialize(self, items):
        return [self.media_service.to_receipt_payload(item, include_group=True) for item in items]


class DeleteMediaUseCase:
    def __init__(self, media_service=None, publisher=None):
        self.media_service = media_service or MediaService()
        self.publisher = publisher or RabbitMQPublisher()

    @transaction.atomic
    def execute(self, user, media_file_id, request=None):
        media_file = self.media_service._get_media_or_raise(media_file_id)
        self.media_service.ensure_delete_access(media_file, user.sub)
        MediaFileRepository.soft_delete(media_file)
        self.media_service.upload_access_log(media_file, user.sub, MediaAccessActionChoices.DELETE, request=request)
        event = MediaDeleted(media_file.id, media_file.group_id, user.sub)
        self.publisher.publish(event.event_type, event.to_dict(), "media.deleted")
        return media_file
