"""API integration tests for auth endpoints."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock

from src.main import create_app
from src.application.dtos import OTPRequestDTO


@pytest.fixture
def app():
    """Create test FastAPI app."""
    return create_app()


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


class TestAuthAPI:
    """Test suite for authentication API endpoints."""

    def test_health_check(self, client):
        """Test health check endpoint."""
        # Act
        response = client.get("/health")
        
        # Assert
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_request_otp_success(self, client):
        """Test successful OTP request."""
        # Arrange
        payload = {"phone_number": "09123456789"}
        
        # Mock the use case
        with patch(
            "src.presentation.api.v1.auth.get_otp_use_case"
        ) as mock_get_use_case:
            mock_use_case = AsyncMock()
            mock_use_case.execute = AsyncMock(
                return_value=MagicMock(
                    message="OTP sent",
                    expires_in=120,
                )
            )
            mock_get_use_case.return_value = mock_use_case
            
            # Act
            response = client.post("/api/v1/auth/otp/request", json=payload)
        
        # Assert
        assert response.status_code == 200
        assert response.json()["message"] == "OTP sent"
        assert response.json()["expires_in"] == 120

    def test_request_otp_invalid_phone_format(self, client):
        """Test OTP request with invalid phone format."""
        # Arrange
        payload = {"phone_number": "123"}  # Too short
        
        # Act
        response = client.post("/api/v1/auth/otp/request", json=payload)
        
        # Assert
        assert response.status_code == 422  # Validation error

    def test_request_otp_missing_phone(self, client):
        """Test OTP request with missing phone number."""
        # Arrange
        payload = {}
        
        # Act
        response = client.post("/api/v1/auth/otp/request", json=payload)
        
        # Assert
        assert response.status_code == 422  # Validation error

    def test_request_otp_rate_limit_exceeded(self, client):
        """Test OTP request with rate limit exceeded."""
        # Arrange
        payload = {"phone_number": "09123456789"}
        
        # Mock the use case to raise RateLimitException
        with patch(
            "src.presentation.api.v1.auth.get_otp_use_case"
        ) as mock_get_use_case:
            mock_use_case = AsyncMock()
            
            from src.domain.exceptions import RateLimitException
            mock_use_case.execute = AsyncMock(side_effect=RateLimitException())
            mock_get_use_case.return_value = mock_use_case
            
            # Act
            response = client.post("/api/v1/auth/otp/request", json=payload)
        
        # Assert
        assert response.status_code == 429
        assert response.json()["success"] is False
        assert response.json()["error"] == "RATE_LIMIT_EXCEEDED"

    def test_request_otp_validation_error(self, client):
        """Test OTP request with validation error."""
        # Arrange
        payload = {"phone_number": "09123456789"}
        
        # Mock the use case to raise ValidationException
        with patch(
            "src.presentation.api.v1.auth.get_otp_use_case"
        ) as mock_get_use_case:
            mock_use_case = AsyncMock()
            
            from src.domain.exceptions import ValidationException
            mock_use_case.execute = AsyncMock(
                side_effect=ValidationException("Invalid format", "INVALID_FORMAT")
            )
            mock_get_use_case.return_value = mock_use_case
            
            # Act
            response = client.post("/api/v1/auth/otp/request", json=payload)
        
        # Assert
        assert response.status_code == 400
        assert response.json()["success"] is False
        assert response.json()["error"] == "INVALID_FORMAT"

    def test_request_otp_internal_error(self, client):
        """Test OTP request with internal server error."""
        # Arrange
        payload = {"phone_number": "09123456789"}
        
        # Mock the use case to raise unexpected exception
        with patch(
            "src.presentation.api.v1.auth.get_otp_use_case"
        ) as mock_get_use_case:
            mock_use_case = AsyncMock()
            mock_use_case.execute = AsyncMock(side_effect=Exception("Unexpected error"))
            mock_get_use_case.return_value = mock_use_case
            
            # Act
            response = client.post("/api/v1/auth/otp/request", json=payload)
        
        # Assert
        assert response.status_code == 500
        assert response.json()["success"] is False
        assert response.json()["error"] == "INTERNAL_SERVER_ERROR"
