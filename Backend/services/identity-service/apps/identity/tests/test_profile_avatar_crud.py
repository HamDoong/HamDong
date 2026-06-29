"""Tests for current-user avatar CRUD endpoints."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import clear_url_caches
from rest_framework import status
from rest_framework.test import APIClient
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.identity.application.token_service import TokenService
from apps.identity.domain.models import User


def make_png_file(name: str = "avatar.png", *, size: int | None = None) -> SimpleUploadedFile:
    payload = b"\x89PNG\r\n\x1a\n" + b"0" * 64
    if size is not None and size > len(payload):
        payload = b"\x89PNG\r\n\x1a\n" + b"0" * (size - 8)
    return SimpleUploadedFile(name, payload, content_type="image/png")


def make_jpeg_file(name: str = "avatar.jpg") -> SimpleUploadedFile:
    payload = b"\xff\xd8\xff" + b"0" * 64
    return SimpleUploadedFile(name, payload, content_type="image/jpeg")


def make_text_file() -> SimpleUploadedFile:
    return SimpleUploadedFile("notes.txt", b"hello world", content_type="text/plain")


@override_settings(
    DEBUG=True,
    JWT_PRIVATE_KEY_PATH="keys/private.pem",
    JWT_PUBLIC_KEY_PATH="keys/public.pem",
)
class ProfileAvatarCrudTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.token_service = TokenService()
        self.user = User.objects.create(
            email="avatar@example.com",
            art_name="avatar-user",
            first_name="Amir",
            last_name="Hosseini",
            is_email_verified=True,
        )
        access_token, _, _ = self.token_service.generate_tokens(self.user)
        self.auth_headers = {"HTTP_AUTHORIZATION": f"Bearer {access_token}"}
        self.avatar_url = "/api/v1/users/me/avatar/"
        self.me_url = "/api/v1/users/me/"
        self.media_root = tempfile.mkdtemp(prefix="identity-avatar-tests-")
        self.override = override_settings(MEDIA_ROOT=self.media_root, MEDIA_URL="/media/")
        self.override.enable()
        clear_url_caches()
        self.publisher = patch(
            "apps.identity.infrastructure.rabbitmq_publisher.RabbitMqPublisher.publish",
            return_value=True,
        )
        self.mock_publish = self.publisher.start()
        self.addCleanup(self.publisher.stop)

    def tearDown(self):
        self.override.disable()
        clear_url_caches()
        shutil.rmtree(self.media_root, ignore_errors=True)

    def test_get_avatar_when_none_exists_returns_null_payload(self):
        response = self.client.get(self.avatar_url, **self.auth_headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json(),
            {"avatar_url": None, "file_id": None, "updated_at": None},
        )

    def test_upload_avatar_successfully_updates_me_profile_and_emits_event(self):
        response = self.client.post(
            self.avatar_url,
            {"file": make_png_file()},
            format="multipart",
            **self.auth_headers,
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        payload = response.json()
        self.assertIsNotNone(payload["avatar_url"])
        self.assertIsNotNone(payload["file_id"])
        self.assertEqual(payload["user"]["id"], str(self.user.id))
        self.assertEqual(payload["user"]["art_name"], self.user.art_name)
        self.assertNotIn(self.media_root, str(payload))
        self.user.refresh_from_db()
        self.assertEqual(self.user.avatar_url, payload["avatar_url"])
        me_response = self.client.get(self.me_url, **self.auth_headers)
        self.assertEqual(me_response.status_code, status.HTTP_200_OK)
        self.assertEqual(me_response.json()["avatar_url"], payload["avatar_url"])
        avatar_dir = Path(self.media_root) / "avatars" / str(self.user.id)
        self.assertTrue(any(avatar_dir.glob(f"{payload['file_id']}.*")))
        self.mock_publish.assert_called()

    def test_replace_avatar_changes_url_and_replaces_old_file(self):
        first = self.client.post(
            self.avatar_url,
            {"file": make_png_file("first.png")},
            format="multipart",
            **self.auth_headers,
        )
        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        first_payload = first.json()

        second = self.client.put(
            self.avatar_url,
            {"file": make_jpeg_file("second.jpg")},
            format="multipart",
            **self.auth_headers,
        )
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        second_payload = second.json()
        self.assertNotEqual(first_payload["avatar_url"], second_payload["avatar_url"])
        self.assertNotEqual(first_payload["file_id"], second_payload["file_id"])

        avatar_dir = Path(self.media_root) / "avatars" / str(self.user.id)
        self.assertFalse(any(avatar_dir.glob(f"{first_payload['file_id']}.*")))
        self.assertTrue(any(avatar_dir.glob(f"{second_payload['file_id']}.*")))

        me_response = self.client.get(self.me_url, **self.auth_headers)
        self.assertEqual(me_response.json()["avatar_url"], second_payload["avatar_url"])

    def test_delete_avatar_is_idempotent_and_updates_me_profile(self):
        self.client.post(
            self.avatar_url,
            {"file": make_png_file()},
            format="multipart",
            **self.auth_headers,
        )

        deleted = self.client.delete(self.avatar_url, **self.auth_headers)
        self.assertEqual(deleted.status_code, status.HTTP_200_OK)
        self.assertEqual(deleted.json()["avatar_url"], None)
        self.assertEqual(deleted.json()["file_id"], None)
        self.assertEqual(
            deleted.json()["message"],
            "Profile avatar has been removed successfully.",
        )

        deleted_again = self.client.delete(self.avatar_url, **self.auth_headers)
        self.assertEqual(deleted_again.status_code, status.HTTP_200_OK)
        self.assertEqual(deleted_again.json()["avatar_url"], None)
        self.assertEqual(deleted_again.json()["file_id"], None)

        me_response = self.client.get(self.me_url, **self.auth_headers)
        self.assertEqual(me_response.json()["avatar_url"], None)

    def test_upload_without_file_returns_avatar_file_required(self):
        response = self.client.post(
            self.avatar_url,
            {},
            format="multipart",
            **self.auth_headers,
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["error"]["code"], "AVATAR_FILE_REQUIRED")

    def test_invalid_file_type_is_rejected(self):
        response = self.client.post(
            self.avatar_url,
            {"file": make_text_file()},
            format="multipart",
            **self.auth_headers,
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["error"]["code"], "INVALID_AVATAR_FILE_TYPE")

    def test_file_too_large_is_rejected(self):
        response = self.client.post(
            self.avatar_url,
            {"file": make_png_file(size=(5 * 1024 * 1024) + 1)},
            format="multipart",
            **self.auth_headers,
        )

        self.assertEqual(response.status_code, status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)
        self.assertEqual(response.json()["error"]["code"], "AVATAR_FILE_TOO_LARGE")

    def test_unauthenticated_requests_are_rejected(self):
        response = self.client.get(self.avatar_url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_inactive_user_is_rejected(self):
        self.user.is_active = False
        self.user.save(update_fields=["is_active", "updated_at"])
        self.client.force_authenticate(user=self.user)

        response = self.client.get(self.avatar_url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.json()["error"]["code"], "ACCOUNT_DEACTIVATED")

    def test_schema_includes_avatar_paths_and_multipart_request_bodies(self):
        response = self.client.get("/api/schema/?format=json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = response.json()

        for path_name in (
            "/api/v1/users/me/avatar/",
        ):
            self.assertIn(path_name, payload["paths"])

        post_operation = payload["paths"]["/api/v1/users/me/avatar/"]["post"]
        put_operation = payload["paths"]["/api/v1/users/me/avatar/"]["put"]
        self.assertIn("multipart/form-data", post_operation["requestBody"]["content"])
        self.assertIn("multipart/form-data", put_operation["requestBody"]["content"])
        avatar_schema = payload["components"]["schemas"]["AvatarResponse"]
        self.assertIn("avatar_url", avatar_schema["properties"])
        self.assertIn("file_id", avatar_schema["properties"])
