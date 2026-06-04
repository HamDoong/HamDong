"""Tests for user endpoints."""

from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from rest_framework import status

from apps.identity.domain.models import *
from apps.identity.application.token_service import TokenService


@override_settings(DEBUG=True)
class GetCurrentUserTestCase(TestCase):
    """Test cases for GET /users/me/ endpoint."""

    def setUp(self):
        self.client = APIClient()
        self.token_service = TokenService()
        self.url = "/api/v1/users/me/"

        # Create a test user with full data
        self.user = User.objects.create(
            phone_number="09123456789",
            display_name="Ali Ahmadi",
            first_name="Ali",
            last_name="Ahmadi",
            is_phone_verified=True,
        )

    def tearDown(self):
        User.objects.all().delete()

    def test_get_current_user_without_token(self):
        """Test getting current user without authentication fails."""
        response = self.client.get(self.url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_current_user_with_invalid_token(self):
        """Test getting current user with invalid token fails."""
        response = self.client.get(
            self.url,
            HTTP_AUTHORIZATION="Bearer invalid.token.here",
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_current_user_with_valid_token(self):
        """Test getting current user with valid token."""
        # Generate tokens
        access_token, _, _ = self.token_service.generate_tokens(self.user)

        # Get current user
        response = self.client.get(
            self.url,
            HTTP_AUTHORIZATION=f"Bearer {access_token}",
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert str(data["id"]) == str(self.user.id)
        assert data["phone_number"] == "09123456789"
        assert data["display_name"] == "Ali Ahmadi"
        assert data["first_name"] == "Ali"
        assert data["last_name"] == "Ahmadi"
        assert data["is_phone_verified"] is True
        assert data["role"] == "USER"

    def test_get_current_user_minimal_data(self):
        """Test getting current user with minimal data."""
        # Create user with minimal data
        user = User.objects.create(phone_number="09999888777")
        access_token, _, _ = self.token_service.generate_tokens(user)

        response = self.client.get(
            self.url,
            HTTP_AUTHORIZATION=f"Bearer {access_token}",
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["phone_number"] == "09999888777"
        assert data["display_name"] is None
        assert data["first_name"] is None
        assert data["last_name"] is None


class UpdateCurrentUserTestCase(TestCase):
    """Test cases for PATCH /users/me/ endpoint."""

    def setUp(self):
        self.client = APIClient()
        self.token_service = TokenService()
        self.url = "/api/v1/users/me/"

        # Create a test user
        self.user = User.objects.create(
            phone_number="09123456789",
            display_name="Old Name",
        )

    def tearDown(self):
        User.objects.all().delete()

    def test_update_current_user_without_token(self):
        """Test updating current user without token fails."""
        response = self.client.patch(
            self.url,
            {"display_name": "New Name"},
            format="json",
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_update_current_user_display_name(self):
        """Test updating display name."""
        access_token, _, _ = self.token_service.generate_tokens(self.user)

        response = self.client.patch(
            self.url,
            {"display_name": "Ali Ahmadi"},
            format="json",
            HTTP_AUTHORIZATION=f"Bearer {access_token}",
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["display_name"] == "Ali Ahmadi"

        # Verify in database
        self.user.refresh_from_db()
        assert self.user.display_name == "Ali Ahmadi"

    def test_update_current_user_first_and_last_name(self):
        """Test updating first and last name."""
        access_token, _, _ = self.token_service.generate_tokens(self.user)

        response = self.client.patch(
            self.url,
            {"first_name": "Ali", "last_name": "Ahmadi"},
            format="json",
            HTTP_AUTHORIZATION=f"Bearer {access_token}",
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["first_name"] == "Ali"
        assert data["last_name"] == "Ahmadi"

    def test_update_current_user_all_fields(self):
        """Test updating allowed profile fields."""
        access_token, _, _ = self.token_service.generate_tokens(self.user)

        response = self.client.patch(
            self.url,
            {
                "display_name": "Ali Ahmadi",
                "first_name": "Ali",
                "last_name": "Ahmadi",
            },
            format="json",
            HTTP_AUTHORIZATION=f"Bearer {access_token}",
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["display_name"] == "Ali Ahmadi"
        assert data["first_name"] == "Ali"
        assert data["last_name"] == "Ahmadi"

    def test_update_current_user_cannot_change_avatar(self):
        """Test that avatar_url is ignored by this endpoint."""
        access_token, _, _ = self.token_service.generate_tokens(self.user)

        response = self.client.patch(
            self.url,
            {"avatar_url": "https://example.com/avatar.jpg"},
            format="json",
            HTTP_AUTHORIZATION=f"Bearer {access_token}",
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["avatar_url"] is None

    def test_update_current_user_partial_update(self):
        """Test partial update (only some fields)."""
        access_token, _, _ = self.token_service.generate_tokens(self.user)

        response = self.client.patch(
            self.url,
            {"first_name": "Ahmad"},
            format="json",
            HTTP_AUTHORIZATION=f"Bearer {access_token}",
        )

        assert response.status_code == status.HTTP_200_OK

        # Verify other fields unchanged
        self.user.refresh_from_db()
        assert self.user.first_name == "Ahmad"
        assert self.user.display_name == "Old Name"  # Unchanged

    def test_update_current_user_cant_change_phone(self):
        """Test that phone number can't be changed."""
        access_token, _, _ = self.token_service.generate_tokens(self.user)

        # Try to change phone (should be ignored)
        response = self.client.patch(
            self.url,
            {
                "display_name": "New Name",
                "phone_number": "09999999999",  # Should be ignored
            },
            format="json",
            HTTP_AUTHORIZATION=f"Bearer {access_token}",
        )

        assert response.status_code == status.HTTP_200_OK

        # Verify phone unchanged
        self.user.refresh_from_db()
        assert self.user.phone_number == "09123456789"
