"""Tests for current-user profile endpoints."""

from __future__ import annotations

from datetime import timedelta

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.identity.application.token_service import TokenService
from apps.identity.domain.models import OutboxMessage, User


@override_settings(DEBUG=True)
class GetCurrentUserTestCase(TestCase):
    """Test cases for GET /users/me/ endpoint."""

    def setUp(self):
        self.client = APIClient()
        self.token_service = TokenService()
        self.url = "/api/v1/users/me/"
        self.user = User.objects.create(
            email="ali@example.com",
            art_name="ali-ahmadi",
            first_name="Ali",
            last_name="Ahmadi",
            display_name="Ali Ahmadi",
            phone_number="+989123456789",
            city="Tehran",
            bio="Backend developer",
            is_email_verified=True,
        )

    def test_get_current_user_without_token(self):
        response = self.client.get(self.url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_current_user_with_invalid_token(self):
        response = self.client.get(
            self.url,
            HTTP_AUTHORIZATION="Bearer invalid.token.here",
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_current_user_with_expired_token(self):
        with override_settings(JWT_ACCESS_TOKEN_LIFETIME_SECONDS=-1):
            expired_token = TokenService().generate_tokens(self.user)[0]
        response = self.client.get(
            self.url,
            HTTP_AUTHORIZATION=f"Bearer {expired_token}",
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.json()["error"]["code"] == "TOKEN_EXPIRED"

    def test_get_current_user_with_valid_token(self):
        access_token, _, _ = self.token_service.generate_tokens(self.user)
        response = self.client.get(
            self.url,
            HTTP_AUTHORIZATION=f"Bearer {access_token}",
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert str(data["id"]) == str(self.user.id)
        assert data["email"] == "ali@example.com"
        assert data["art_name"] == "ali-ahmadi"
        assert data["first_name"] == "Ali"
        assert data["last_name"] == "Ahmadi"
        assert data["display_name"] == "Ali Ahmadi"
        assert data["phone_number"] == "+989123456789"
        assert data["city"] == "Tehran"
        assert data["bio"] == "Backend developer"
        assert data["is_email_verified"] is True
        assert data["role"] == "USER"
        assert "password_hash" not in data

    def test_get_current_user_with_inactive_user_rejected(self):
        self.user.is_active = False
        self.user.save(update_fields=["is_active", "updated_at"])
        access_token, _, _ = self.token_service.generate_tokens(self.user)
        response = self.client.get(
            self.url,
            HTTP_AUTHORIZATION=f"Bearer {access_token}",
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.json()["error"]["code"] == "USER_INACTIVE"

    def test_get_current_user_minimal_data(self):
        user = User.objects.create(email="minimal@example.com", art_name="minimal-user")
        access_token, _, _ = self.token_service.generate_tokens(user)

        response = self.client.get(
            self.url,
            HTTP_AUTHORIZATION=f"Bearer {access_token}",
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["email"] == "minimal@example.com"
        assert data["art_name"] == "minimal-user"
        assert data["first_name"] is None
        assert data["last_name"] is None
        assert data["display_name"] is None
        assert data["phone_number"] is None
        assert data["date_of_birth"] is None
        assert data["city"] is None
        assert data["bio"] is None


class UpdateCurrentUserTestCase(TestCase):
    """Test cases for PATCH /users/me/ endpoint."""

    def setUp(self):
        self.client = APIClient()
        self.token_service = TokenService()
        self.url = "/api/v1/users/me/"
        self.user = User.objects.create(
            email="ali@example.com",
            art_name="old-name",
        )

    def _auth_header(self):
        access_token, _, _ = self.token_service.generate_tokens(self.user)
        return {"HTTP_AUTHORIZATION": f"Bearer {access_token}"}

    def test_update_current_user_without_token(self):
        response = self.client.patch(
            self.url,
            {"art_name": "new-name"},
            format="json",
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_update_current_user_all_supported_fields(self):
        response = self.client.patch(
            self.url,
            {
                "art_name": "ali-ahmadi",
                "first_name": "Ali",
                "last_name": "Ahmadi",
                "display_name": "  علی   احمدی  ",
                "phone_number": "0912-345-6789",
                "date_of_birth": "1998-07-01",
                "city": "  Tehran  ",
                "bio": "  Backend developer  ",
            },
            format="json",
            **self._auth_header(),
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["art_name"] == "ali-ahmadi"
        assert data["first_name"] == "Ali"
        assert data["last_name"] == "Ahmadi"
        assert data["display_name"] == "علی احمدی"
        assert data["phone_number"] == "+989123456789"
        assert data["date_of_birth"] == "1998-07-01"
        assert data["city"] == "Tehran"
        assert data["bio"] == "Backend developer"

        self.user.refresh_from_db()
        assert self.user.display_name == "علی احمدی"
        assert self.user.phone_number == "+989123456789"
        assert OutboxMessage.objects.filter(event_type="UserUpdated").exists()

    def test_update_current_user_partial_update_preserves_unspecified_fields(self):
        self.user.display_name = "Old Name"
        self.user.city = "Mashhad"
        self.user.save(update_fields=["display_name", "city", "updated_at"])

        response = self.client.patch(
            self.url,
            {"first_name": "Ahmad"},
            format="json",
            **self._auth_header(),
        )

        assert response.status_code == status.HTTP_200_OK
        self.user.refresh_from_db()
        assert self.user.first_name == "Ahmad"
        assert self.user.display_name == "Old Name"
        assert self.user.city == "Mashhad"

    def test_update_current_user_clears_nullable_fields(self):
        self.user.display_name = "Old Name"
        self.user.phone_number = "+989121111111"
        self.user.city = "Tehran"
        self.user.bio = "Bio"
        self.user.save(update_fields=["display_name", "phone_number", "city", "bio", "updated_at"])

        response = self.client.patch(
            self.url,
            {
                "display_name": None,
                "phone_number": "",
                "city": "   ",
                "bio": None,
            },
            format="json",
            **self._auth_header(),
        )

        assert response.status_code == status.HTTP_200_OK
        self.user.refresh_from_db()
        assert self.user.display_name is None
        assert self.user.phone_number is None
        assert self.user.city is None
        assert self.user.bio is None

    def test_update_current_user_ignores_read_only_fields(self):
        response = self.client.patch(
            self.url,
            {
                "email": "changed@example.com",
                "role": "ADMIN",
                "is_active": False,
                "is_email_verified": False,
                "avatar_url": "https://example.com/avatar.jpg",
                "display_name": "Safe Name",
            },
            format="json",
            **self._auth_header(),
        )

        assert response.status_code == status.HTTP_200_OK
        self.user.refresh_from_db()
        assert self.user.email == "ali@example.com"
        assert self.user.role == "USER"
        assert self.user.is_active is True
        assert self.user.is_email_verified is False
        assert self.user.avatar_url is None
        assert self.user.display_name == "Safe Name"

    def test_duplicate_art_name_fails(self):
        User.objects.create(email="taken@example.com", art_name="taken-name")
        response = self.client.patch(
            self.url,
            {"art_name": "taken-name"},
            format="json",
            **self._auth_header(),
        )

        assert response.status_code == status.HTTP_409_CONFLICT
        assert response.json()["error"]["code"] == "ART_NAME_ALREADY_EXISTS"

    def test_duplicate_phone_number_fails_safely(self):
        User.objects.create(email="taken@example.com", art_name="taken-name", phone_number="+989121111111")
        response = self.client.patch(
            self.url,
            {"phone_number": "0912 111 1111"},
            format="json",
            **self._auth_header(),
        )

        assert response.status_code == status.HTTP_409_CONFLICT
        assert response.json()["error"]["code"] == "PHONE_NUMBER_ALREADY_EXISTS"

    def test_invalid_display_name_rejected(self):
        response = self.client.patch(
            self.url,
            {"display_name": "\u0000bad"},
            format="json",
            **self._auth_header(),
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json()["error"]["code"] == "INVALID_DISPLAY_NAME"

    def test_invalid_phone_number_rejected(self):
        response = self.client.patch(
            self.url,
            {"phone_number": "12345"},
            format="json",
            **self._auth_header(),
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json()["error"]["code"] == "INVALID_PHONE_NUMBER"

    def test_invalid_date_of_birth_rejected(self):
        response = self.client.patch(
            self.url,
            {"date_of_birth": (timezone.now() + timedelta(days=1)).date().isoformat()},
            format="json",
            **self._auth_header(),
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json()["error"]["code"] == "INVALID_DATE_OF_BIRTH"

    def test_datetime_date_of_birth_rejected(self):
        response = self.client.patch(
            self.url,
            {"date_of_birth": "1998-07-01T12:00:00Z"},
            format="json",
            **self._auth_header(),
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json()["error"]["code"] == "INVALID_DATE_OF_BIRTH"
