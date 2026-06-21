import hashlib
import os
import tempfile
import uuid
from pathlib import Path

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APIClient

from apps.media_files.domain.models import GroupMemberProjection, GroupProjection, MediaAccessLog, MediaFile, GroupStatusChoices, GroupMemberRoleChoices, GroupMemberStatusChoices, MediaStatusChoices, UserProjection
from apps.media_files.infrastructure.jwt_authentication import JWTAuthentication
from apps.media_files.infrastructure.rabbitmq_publisher import RabbitMQPublisher
from apps.media_files.infrastructure.rabbitmq_consumer import MediaEventConsumer
from apps.media_files.infrastructure.event_envelope import build_event_envelope

class FakeUser:
    def __init__(self, sub=None, email="+10000000000", art_name="Test User", role="USER"):
        self.sub = sub or uuid.uuid4()
        self.email = email
        self.art_name = art_name
        self.role = role
        self.is_authenticated = True


def auth_client(monkeypatch, user=None):
    client = APIClient()

    def fake_auth(self, request):
        return (user or FakeUser(), None)

    monkeypatch.setattr(JWTAuthentication, "authenticate", fake_auth)
    return client


def seed_active_group(member_role="MEMBER", member_user_id=None, uploaded_by=None):
    group_id = uuid.uuid4()
    actor_id = uploaded_by or member_user_id or uuid.uuid4()
    GroupProjection.objects.create(
        group_id=group_id,
        title="Trip",
        group_type="TRIP",
        status=GroupStatusChoices.ACTIVE,
        created_by_user_id=actor_id,
        member_count=1,
    )
    if member_user_id:
        UserProjection.objects.create(identity_user_id=member_user_id, email="+9891", art_name="Member", role="USER")
        GroupMemberProjection.objects.create(
            group_id=group_id,
            user_id=member_user_id,
            email="+9891",
            art_name_snapshot="Member",
            role=member_role,
            status=GroupMemberStatusChoices.ACTIVE,
        )
    return group_id


def receipt_file(name="receipt.jpg", content=b"hello receipt", content_type="image/jpeg"):
    return SimpleUploadedFile(name, content, content_type=content_type)


def storage_payload(name="receipt.jpg", content=b"hello receipt", content_type="image/jpeg"):
    return SimpleUploadedFile(name, content, content_type=content_type)

def envelope(event_type, data, routing_key):
    return build_event_envelope(
        event_type=event_type,
        data=data,
        source_service="test-service",
        routing_key=routing_key,
    )

@pytest.mark.django_db
def test_consumer_creates_and_updates_projections():
    
    consumer = MediaEventConsumer()
    uid = str(uuid.uuid4())
    gid = str(uuid.uuid4())
    consumer.process_identity_payload(envelope(
        "UserCreated",
        {
            "user_id": uid,
            "email": "+123",
            "art_name": "Alice",
            "role": "ADMIN",
            "is_active": True,
        },
        "identity.user.created",
    ))

    consumer.process_identity_payload(envelope(
        "UserUpdated",
        {
            "user_id": uid,
            "email": "+456",
            "art_name": "Alice B",
            "role": "ADMIN",
            "is_active": False,
        },
        "identity.user.updated",
    ))

    consumer.process_group_payload(envelope(
        "GroupCreated",
        {
            "group_id": gid,
            "title": "Trip 1",
            "group_type": "TRIP",
            "created_by_user_id": uid,
            "member_count": 1,
        },
        "group.created",
    ))

    consumer.process_group_payload(envelope(
        "GroupUpdated",
        {
            "group_id": gid,
            "title": "Trip 2",
            "group_type": "GENERAL",
            "member_count": 2,
        },
        "group.updated",
    ))

    consumer.process_group_payload(envelope(
        "GroupArchived",
        {
            "group_id": gid,
        },
        "group.archived",
    ))

    consumer.process_group_payload(envelope(
        "GroupMemberJoined",
        {
            "group_id": gid,
            "user_id": uid,
            "role": "OWNER",
        },
        "group.member.joined",
    ))

    consumer.process_group_payload(envelope(
        "GroupMemberRemoved",
        {
            "group_id": gid,
            "user_id": uid,
        },
        "group.member.removed",
    ))

    consumer.process_group_payload(envelope(
        "GroupMemberLeft",
        {
            "group_id": gid,
            "user_id": uid,
        },
        "group.member.left",
    ))

    user = UserProjection.objects.get(identity_user_id=uid)
    group = GroupProjection.objects.get(group_id=gid)
    member = GroupMemberProjection.objects.get(group_id=gid, user_id=uid)
    assert user.email == "+456"
    assert user.art_name == "Alice B"
    assert user.is_active is False
    assert group.title == "Trip 2"
    assert group.status == "ARCHIVED"
    assert member.status == "LEFT"


@pytest.mark.django_db
def test_upload_receipt_success(monkeypatch):
    user = FakeUser()
    client = auth_client(monkeypatch, user=user)
    calls = []

    def fake_publish(self, event_type, data, routing_key):
        calls.append((event_type, routing_key, data))
        return True

    monkeypatch.setattr(RabbitMQPublisher, "publish", fake_publish)
    group_id = seed_active_group(member_user_id=user.sub, uploaded_by=user.sub)

    with tempfile.TemporaryDirectory() as temp_dir:
        with override_settings(
            MEDIA_ROOT=temp_dir,
            MEDIA_MAX_FILE_SIZE_BYTES=5242880,
            MEDIA_ALLOWED_EXTENSIONS=["jpg", "jpeg", "png", "webp", "pdf"],
            MEDIA_ALLOWED_CONTENT_TYPES=["image/jpeg", "image/png", "image/webp", "application/pdf"],
        ):
            response = client.post(
                "/api/v1/media/receipts/",
                {"group_id": str(group_id), "file": receipt_file()},
                format="multipart",
            )
            media = MediaFile.objects.get(group_id=group_id)
            assert Path(temp_dir, media.object_key).exists()

    assert response.status_code == status.HTTP_201_CREATED
    media = MediaFile.objects.get(group_id=group_id)
    assert media.original_filename == "receipt.jpg"
    assert media.stored_filename != media.original_filename
    assert media.checksum_sha256 == hashlib.sha256(b"hello receipt").hexdigest()
    assert MediaAccessLog.objects.filter(media_file=media, action="UPLOAD").count() == 1
    assert any(routing_key == "media.uploaded" for _, routing_key, _ in calls)
    assert media.status == MediaStatusChoices.ACTIVE


@pytest.mark.django_db
def test_upload_requires_jwt():
    client = APIClient()
    group_id = seed_active_group()
    response = client.post("/api/v1/media/receipts/", {"group_id": str(group_id), "file": receipt_file()}, format="multipart")
    assert response.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)


@pytest.mark.django_db
def test_upload_fails_for_non_member(monkeypatch):
    user = FakeUser()
    client = auth_client(monkeypatch, user=user)
    group_id = seed_active_group(member_user_id=uuid.uuid4())
    response = client.post("/api/v1/media/receipts/", {"group_id": str(group_id), "file": receipt_file()}, format="multipart")
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()["error"]["code"] == "MEDIA_PERMISSION_DENIED"


@pytest.mark.django_db
def test_upload_fails_for_archived_group(monkeypatch):
    user = FakeUser()
    client = auth_client(monkeypatch, user=user)
    group_id = seed_active_group(member_user_id=user.sub)
    group = GroupProjection.objects.get(group_id=group_id)
    group.status = GroupStatusChoices.ARCHIVED
    group.save(update_fields=["status"])
    response = client.post("/api/v1/media/receipts/", {"group_id": str(group_id), "file": receipt_file()}, format="multipart")
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_upload_validation_errors(monkeypatch):
    user = FakeUser()
    client = auth_client(monkeypatch, user=user)
    group_id = seed_active_group(member_user_id=user.sub)
    with override_settings(MEDIA_MAX_FILE_SIZE_BYTES=5):
        response = client.post("/api/v1/media/receipts/", {"group_id": str(group_id), "file": receipt_file(content=b"123456")}, format="multipart")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json()["error"]["code"] == "FILE_TOO_LARGE"

    response = client.post("/api/v1/media/receipts/", {"group_id": str(group_id), "file": receipt_file(name="receipt.exe", content_type="application/octet-stream")}, format="multipart")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["error"]["code"] == "INVALID_FILE_TYPE"

    response = client.post("/api/v1/media/receipts/", {"group_id": str(group_id), "file": receipt_file(name="receipt.ps1", content_type="image/jpeg")}, format="multipart")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["error"]["code"] == "INVALID_FILE_TYPE"

    response = client.post("/api/v1/media/receipts/", {"group_id": str(group_id), "file": receipt_file(name="receipt.jpg", content_type="text/plain")}, format="multipart")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["error"]["code"] == "INVALID_FILE_TYPE"


@pytest.mark.django_db
def test_detail_download_list_and_delete_flow(monkeypatch):
    uploader = FakeUser(role="USER")
    owner = FakeUser(role="ADMIN")
    member = FakeUser(role="USER")
    group_id = seed_active_group(member_role="OWNER", member_user_id=owner.sub, uploaded_by=uploader.sub)
    GroupMemberProjection.objects.create(group_id=group_id, user_id=uploader.sub, email=uploader.email, art_name_snapshot=uploader.art_name, role="MEMBER", status="ACTIVE")
    GroupMemberProjection.objects.create(group_id=group_id, user_id=member.sub, email=member.email, art_name_snapshot=member.art_name, role="MEMBER", status="ACTIVE")

    publisher_calls = []

    def fake_publish(self, event_type, data, routing_key):
        publisher_calls.append((event_type, routing_key))
        return True

    monkeypatch.setattr(RabbitMQPublisher, "publish", fake_publish)

    client = auth_client(monkeypatch, user=uploader)
    with tempfile.TemporaryDirectory() as temp_dir:
        with override_settings(MEDIA_ROOT=temp_dir):
            upload = client.post("/api/v1/media/receipts/", {"group_id": str(group_id), "file": receipt_file()}, format="multipart")
            assert upload.status_code == status.HTTP_201_CREATED
            media_id = upload.json()["id"]

            detail = client.get(f"/api/v1/media/files/{media_id}/")
            assert detail.status_code == status.HTTP_200_OK
            assert MediaAccessLog.objects.filter(action="VIEW").count() == 1

            download = client.get(f"/api/v1/media/files/{media_id}/download/")
            assert download.status_code == status.HTTP_200_OK
            assert MediaAccessLog.objects.filter(action="DOWNLOAD").count() == 1

            listing = client.get(f"/api/v1/media/groups/{group_id}/media/")
            assert listing.status_code == status.HTTP_200_OK
            assert listing.json()["count"] == 1

            delete_response = client.delete(f"/api/v1/media/files/{media_id}/")
            assert delete_response.status_code == status.HTTP_200_OK
            assert MediaFile.objects.get(id=media_id).status == MediaStatusChoices.DELETED
            assert MediaAccessLog.objects.filter(action="DELETE").count() == 1
            assert any(routing_key == "media.deleted" for _, routing_key in publisher_calls)

            deleted_download = client.get(f"/api/v1/media/files/{media_id}/download/")
            assert deleted_download.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_delete_media_permissions(monkeypatch):
    uploader = FakeUser(role="USER")
    owner = FakeUser(role="ADMIN")
    member = FakeUser(role="USER")
    group_id = seed_active_group(member_role="OWNER", member_user_id=owner.sub, uploaded_by=uploader.sub)
    GroupMemberProjection.objects.create(group_id=group_id, user_id=uploader.sub, email=uploader.email, art_name_snapshot=uploader.art_name, role="MEMBER", status="ACTIVE")
    GroupMemberProjection.objects.create(group_id=group_id, user_id=member.sub, email=member.email, art_name_snapshot=member.art_name, role="MEMBER", status="ACTIVE")

    publisher_calls = []

    def fake_publish(self, event_type, data, routing_key):
        publisher_calls.append((event_type, routing_key))
        return True

    monkeypatch.setattr(RabbitMQPublisher, "publish", fake_publish)

    with tempfile.TemporaryDirectory() as temp_dir:
        with override_settings(MEDIA_ROOT=temp_dir):
            uploader_client = auth_client(monkeypatch, user=uploader)
            upload = uploader_client.post("/api/v1/media/receipts/", {"group_id": str(group_id), "file": receipt_file()}, format="multipart")
            assert upload.status_code == status.HTTP_201_CREATED
            uploader_media_id = upload.json()["id"]

            owner_client = auth_client(monkeypatch, user=owner)
            owner_delete = owner_client.delete(f"/api/v1/media/files/{uploader_media_id}/")
            assert owner_delete.status_code == status.HTTP_200_OK

            owner_upload = owner_client.post("/api/v1/media/receipts/", {"group_id": str(group_id), "file": receipt_file(name="owner.jpg")}, format="multipart")
            assert owner_upload.status_code == status.HTTP_201_CREATED
            owner_media_id = owner_upload.json()["id"]

            member_client = auth_client(monkeypatch, user=member)
            member_delete = member_client.delete(f"/api/v1/media/files/{owner_media_id}/")
            assert member_delete.status_code == status.HTTP_403_FORBIDDEN

            assert any(routing_key == "media.deleted" for _, routing_key in publisher_calls)


@pytest.mark.django_db
def test_media_event_publishing(monkeypatch):
    user = FakeUser()
    client = auth_client(monkeypatch, user=user)
    publisher_calls = []

    def fake_publish(self, event_type, data, routing_key):
        publisher_calls.append((event_type, routing_key, data))
        return True

    monkeypatch.setattr(RabbitMQPublisher, "publish", fake_publish)
    group_id = seed_active_group(member_user_id=user.sub, uploaded_by=user.sub)

    with tempfile.TemporaryDirectory() as temp_dir:
        with override_settings(MEDIA_ROOT=temp_dir):
            upload = client.post("/api/v1/media/receipts/", {"group_id": str(group_id), "file": receipt_file()}, format="multipart")
            assert upload.status_code == status.HTTP_201_CREATED
            media_id = upload.json()["id"]
            assert any(event_type == "MediaUploaded" and routing_key == "media.uploaded" for event_type, routing_key, _ in publisher_calls)

            delete_response = client.delete(f"/api/v1/media/files/{media_id}/")
            assert delete_response.status_code == status.HTTP_200_OK
            assert any(event_type == "MediaDeleted" and routing_key == "media.deleted" for event_type, routing_key, _ in publisher_calls)
