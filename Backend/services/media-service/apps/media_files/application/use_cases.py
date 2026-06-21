from django.db import transaction

from apps.media_files.application.file_validator import MediaFileNotFoundError, MediaPermissionDeniedError, NotGroupMemberError
from apps.media_files.application.media_service import MediaService
from apps.media_files.application.upload_service import UploadReceiptService
from apps.media_files.domain.events import MediaDeleted
from apps.media_files.domain.models import MediaAccessActionChoices
from apps.media_files.infrastructure.rabbitmq_publisher import RabbitMQPublisher
from apps.media_files.infrastructure.repositories import MediaFileRepository


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
