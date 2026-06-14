"""Tests for token refresh and logout endpoints."""

from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from rest_framework import status

from apps.identity.domain.models import *
from apps.identity.application.token_service import TokenService
from apps.identity.infrastructure.redis_otp_store import RedisOtpStore


@override_settings(DEBUG=True, OTP_DEBUG_RETURN_CODE=True)
class TokenRefreshTestCase(TestCase):
    """Test cases for token refresh endpoint."""

    def setUp(self):
        self.client = APIClient()
        self.token_service = TokenService()
        self.otp_store = RedisOtpStore()
        self.url = "/api/v1/auth/token/refresh/"

        # Create a test user
        self.user = User.objects.create(email="09123456789")

    def tearDown(self):
        self.otp_store.redis_client.flushdb()
        User.objects.all().delete()

    def test_refresh_token_success(self):
        """Test refreshing access token with valid refresh token."""
        # Generate initial tokens
        access_token, refresh_token, jti = self.token_service.generate_tokens(self.user)

        # Refresh token
        response = self.client.post(
            self.url,
            {"refresh_token": refresh_token},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "Bearer"
        assert data["expires_in"] == 900

        # New tokens should be different
        assert data["access_token"] != access_token
        assert data["refresh_token"] != refresh_token

    def test_refresh_token_rotation(self):
        """Test that refresh token is rotated."""
        # Generate initial tokens
        access_token1, refresh_token1, jti1 = self.token_service.generate_tokens(
            self.user
        )

        # Verify token exists in DB
        from apps.identity.infrastructure.repositories import RefreshTokenRepository

        token_hash1 = RefreshTokenRepository.hash_token(refresh_token1)
        db_token1 = RefreshTokenRepository.get_by_token_hash(token_hash1)
        assert db_token1 is not None
        assert db_token1.is_revoked is False

        # Refresh token
        response = self.client.post(
            self.url,
            {"refresh_token": refresh_token1},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        refresh_token2 = data["refresh_token"]

        # Old token should be revoked
        db_token1.refresh_from_db()
        assert db_token1.is_revoked is True

        # New token should exist
        token_hash2 = RefreshTokenRepository.hash_token(refresh_token2)
        db_token2 = RefreshTokenRepository.get_by_token_hash(token_hash2)
        assert db_token2 is not None
        assert db_token2.is_revoked is False

    def test_refresh_token_reuse_fails(self):
        """Test that reusing old refresh token fails after rotation."""
        # Generate and refresh
        access_token1, refresh_token1, jti1 = self.token_service.generate_tokens(
            self.user
        )

        response1 = self.client.post(
            self.url,
            {"refresh_token": refresh_token1},
            format="json",
        )

        assert response1.status_code == status.HTTP_200_OK

        # Try to use old token again
        response2 = self.client.post(
            self.url,
            {"refresh_token": refresh_token1},
            format="json",
        )

        assert response2.status_code == status.HTTP_401_UNAUTHORIZED
        data = response2.json()
        assert data["error"]["code"] == "INVALID_TOKEN"

    def test_refresh_token_invalid_token(self):
        """Test refresh with invalid token."""
        response = self.client.post(
            self.url,
            {"refresh_token": "invalid.token.here"},
            format="json",
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert data["error"]["code"] == "INVALID_TOKEN"


class LogoutTestCase(TestCase):
    """Test cases for logout endpoint."""

    def setUp(self):
        self.client = APIClient()
        self.token_service = TokenService()
        self.otp_store = RedisOtpStore()
        self.url = "/api/v1/auth/logout/"

        # Create a test user
        self.user = User.objects.create(email="09123456789")

    def tearDown(self):
        self.otp_store.redis_client.flushdb()
        User.objects.all().delete()

    def test_logout_success(self):
        """Test successful logout."""
        # Generate tokens
        access_token, refresh_token, jti = self.token_service.generate_tokens(self.user)

        # Logout
        response = self.client.post(
            self.url,
            {"refresh_token": refresh_token},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["message"] == "Logged out successfully."

    def test_logout_revokes_token(self):
        """Test that logout revokes refresh token."""
        from apps.identity.infrastructure.repositories import RefreshTokenRepository

        # Generate tokens
        access_token, refresh_token, jti = self.token_service.generate_tokens(self.user)

        token_hash = RefreshTokenRepository.hash_token(refresh_token)
        db_token = RefreshTokenRepository.get_by_token_hash(token_hash)
        assert db_token.is_revoked is False

        # Logout
        response = self.client.post(
            self.url,
            {"refresh_token": refresh_token},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK

        # Token should be revoked
        db_token.refresh_from_db()
        assert db_token.is_revoked is True

    def test_logout_with_invalid_token(self):
        """Test logout with invalid token."""
        response = self.client.post(
            self.url,
            {"refresh_token": "invalid.token"},
            format="json",
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert data["error"]["code"] == "INVALID_TOKEN"
