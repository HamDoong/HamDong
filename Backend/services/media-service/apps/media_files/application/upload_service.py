from django.conf import settings
from django.db import transaction

from apps.media_files.application.file_validator import FileValidator, MediaPermissionDeniedError, NotGroupMemberError
from apps.media_files.application.media_service import MediaService
from apps.media_files.domain.events import MediaUploaded
from apps.media_files.domain.models import MediaFileTypeChoices, MediaStorageProviderChoices, MediaVisibilityChoices
from apps.media_files.infrastructure.rabbitmq_publisher import RabbitMQPublisher
from apps.media_files.infrastructure.repositories import GroupMemberProjectionRepository, GroupProjectionRepository, MediaAccessLogRepository, MediaFileRepository


class UploadReceiptService:
    def __init__(self, publisher=None, media_service=None, validator=None):
        self.publisher = publisher or RabbitMQPublisher()
        self.media_service = media_service or MediaService()
        self.validator = validator or FileValidator(
            getattr(settings, "MEDIA_MAX_FILE_SIZE_BYTES", 5242880),
            getattr(settings, "MEDIA_ALLOWED_EXTENSIONS", ["jpg", "jpeg", "png", "webp", "pdf"]),
            getattr(settings, "MEDIA_ALLOWED_CONTENT_TYPES", ["image/jpeg", "image/png", "image/webp", "application/pdf"]),
        )

    @transaction.atomic
    def execute(self, user, group_id, uploaded_file, related_expense_id=None, request=None):
        validated = self.validator.validate(uploaded_file)
        group = self.media_service._get_group_or_raise(group_id)
        try:
            self.media_service._get_active_member_or_raise(group_id, user.sub)
        except NotGroupMemberError as exc:
            raise MediaPermissionDeniedError() from exc

        object_key = self.media_service.build_object_key(group_id, validated.file_extension)
        stored_file_result, content_bytes = self.media_service.save_blob(uploaded_file, object_key)
        checksum = self.media_service.checksum(content_bytes)
        stored_filename = object_key.rsplit("/", 1)[-1]

        media_file = MediaFileRepository.create(
            uploaded_by_user_id=user.sub,
            group_id=group_id,
            related_expense_id=related_expense_id,
            file_type=MediaFileTypeChoices.RECEIPT,
            storage_provider=MediaStorageProviderChoices.LOCAL,
            bucket_name=None,
            object_key=stored_file_result.object_key,
            original_filename=validated.original_filename,
            stored_filename=stored_filename,
            content_type=validated.content_type,
            file_extension=validated.file_extension,
            size_bytes=validated.size_bytes,
            checksum_sha256=checksum,
            status="ACTIVE",
            visibility=MediaVisibilityChoices.GROUP_MEMBERS,
        )

        MediaAccessLogRepository.create(media_file, user.sub, "UPLOAD", ip_address=request.META.get("REMOTE_ADDR") if request else None, user_agent=request.META.get("HTTP_USER_AGENT") if request else None)

        event = MediaUploaded(media_file.id, media_file.group_id, media_file.related_expense_id, media_file.uploaded_by_user_id, media_file.file_type, media_file.content_type, media_file.size_bytes)
        self.publisher.publish(event.event_type, event.to_dict(), "media.uploaded")
        return media_file
