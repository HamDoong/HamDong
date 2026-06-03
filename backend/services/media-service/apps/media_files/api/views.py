from django.conf import settings
from django.http import FileResponse
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.media_files.api.serializers import MediaListItemSerializer, MediaListResponseSerializer, MediaMetadataSerializer, MessageSerializer, ReceiptUploadSerializer
from apps.media_files.application.file_validator import FileTooLargeError, GroupNotFoundError, InvalidFileTypeError, MediaFileNotFoundError, MediaPermissionDeniedError, NotGroupMemberError
from apps.media_files.application.use_cases import DeleteMediaUseCase, DownloadMediaUseCase, GetMediaDetailUseCase, ListGroupMediaUseCase, UploadReceiptUseCase
from apps.media_files.infrastructure.jwt_authentication import JWTAuthentication


def _error_response(exc):
    return Response({"error": {"code": exc.code, "message": exc.message}}, status=exc.status_code)


class HealthView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        return Response({"service": settings.SERVICE_NAME, "status": "ok", "version": settings.SERVICE_VERSION})


class UploadReceiptView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(
        tags=["Media"],
        summary="Upload receipt",
        description="Upload a receipt file for an active group member and return the stored media metadata.",
        request=ReceiptUploadSerializer,
        responses={201: MediaMetadataSerializer},
    )
    def post(self, request, *args, **kwargs):
        serializer = ReceiptUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            media_file = UploadReceiptUseCase().execute(
                request.user,
                serializer.validated_data["group_id"],
                serializer.validated_data["file"],
                related_expense_id=serializer.validated_data.get("related_expense_id"),
                request=request,
            )
        except (FileTooLargeError, GroupNotFoundError, InvalidFileTypeError, MediaFileNotFoundError, NotGroupMemberError, MediaPermissionDeniedError) as exc:
            return _error_response(exc)
        return Response(MediaMetadataSerializer(UploadReceiptUseCase().service.media_service.to_metadata(media_file)).data, status=status.HTTP_201_CREATED)


class MediaDetailView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Media"],
        summary="Get media detail",
        description="Return safe metadata for an active media file visible to an active group member.",
        responses={200: MediaMetadataSerializer},
    )
    def get(self, request, file_id, *args, **kwargs):
        try:
            media_file = GetMediaDetailUseCase().execute(request.user, file_id, request=request)
        except (MediaFileNotFoundError, NotGroupMemberError, MediaPermissionDeniedError) as exc:
            return _error_response(exc)
        return Response(MediaMetadataSerializer(UploadReceiptUseCase().service.media_service.to_metadata(media_file)).data)

    @extend_schema(
        tags=["Media"],
        summary="Delete media",
        description="Soft delete a media file when the requester uploaded it or is an owner/admin of the file's group.",
        responses={200: MessageSerializer},
    )
    def delete(self, request, file_id, *args, **kwargs):
        try:
            DeleteMediaUseCase().execute(request.user, file_id, request=request)
        except (MediaFileNotFoundError, NotGroupMemberError, MediaPermissionDeniedError) as exc:
            return _error_response(exc)
        return Response({"message": "Media file deleted successfully."})


class MediaDownloadView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Media"],
        summary="Download media",
        description="Stream the underlying file for an active media file accessible by an active group member.",
        responses={200: OpenApiResponse(description="File stream")},
    )
    def get(self, request, file_id, *args, **kwargs):
        try:
            media_file, file_handle = DownloadMediaUseCase().execute(request.user, file_id, request=request)
        except (MediaFileNotFoundError, NotGroupMemberError, MediaPermissionDeniedError) as exc:
            return _error_response(exc)
        response = FileResponse(file_handle, content_type=media_file.content_type)
        response["Content-Disposition"] = f'attachment; filename="{media_file.original_filename}"'
        return response


class ListGroupMediaView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Media"],
        summary="List group media",
        description="List active media files for an active group member, optionally filtered by file type.",
        responses={200: MediaListResponseSerializer},
    )
    def get(self, request, group_id, *args, **kwargs):
        file_type = request.query_params.get("file_type")
        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 20))
        try:
            items, count = ListGroupMediaUseCase().execute(request.user, group_id, file_type=file_type, page=page, page_size=page_size)
        except (GroupNotFoundError, NotGroupMemberError, MediaPermissionDeniedError) as exc:
            return _error_response(exc)
        results = [
            {
                "id": str(item.id),
                "file_type": item.file_type,
                "original_filename": item.original_filename,
                "content_type": item.content_type,
                "size_bytes": item.size_bytes,
                "created_at": item.created_at.isoformat(),
            }
            for item in items
        ]
        return Response({"count": count, "results": results})


