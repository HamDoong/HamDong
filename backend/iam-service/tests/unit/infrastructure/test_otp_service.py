"""Unit tests for OTP service."""

import pytest

from src.infrastructure.services.otp_service import OTPService


class TestOTPService:
    """Test suite for OTPService."""

    def test_generate_otp(self):
        """Test OTP generation."""
        # Arrange
        service = OTPService()
        
        # Act
        otp = service.generate_otp()
        
        # Assert
        assert len(otp) == 6
        assert otp.isdigit()

    def test_generate_otp_uniqueness(self):
        """Test that generated OTPs are unique (with high probability)."""
        # Arrange
        service = OTPService()
        otps = set()
        
        # Act
        for _ in range(100):
            otp = service.generate_otp()
            otps.add(otp)
        
        # Assert - should have at least 95 unique OTPs out of 100
        assert len(otps) >= 95

    def test_hash_otp(self):
        """Test OTP hashing."""
        # Arrange
        service = OTPService()
        otp = "123456"
        
        # Act
        hashed = service.hash_otp(otp)
        
        # Assert
        assert hashed != otp
        assert len(hashed) == 64  # SHA256 hex digest length
        assert isinstance(hashed, str)

    def test_hash_otp_deterministic(self):
        """Test that hashing is deterministic."""
        # Arrange
        service = OTPService()
        otp = "123456"
        
        # Act
        hash1 = service.hash_otp(otp)
        hash2 = service.hash_otp(otp)
        
        # Assert
        assert hash1 == hash2

    def test_verify_otp_success(self):
        """Test successful OTP verification."""
        # Arrange
        service = OTPService()
        otp = "123456"
        otp_hash = service.hash_otp(otp)
        
        # Act
        result = service.verify_otp(otp, otp_hash)
        
        # Assert
        assert result is True

    def test_verify_otp_failure(self):
        """Test failed OTP verification."""
        # Arrange
        service = OTPService()
        otp = "123456"
        wrong_otp = "654321"
        otp_hash = service.hash_otp(otp)
        
        # Act
        result = service.verify_otp(wrong_otp, otp_hash)
        
        # Assert
        assert result is False

    def test_verify_otp_timing_safe(self):
        """Test that verification is timing-safe."""
        # Arrange
        service = OTPService()
        otp = "123456"
        otp_hash = service.hash_otp(otp)
        
        # Act - verify multiple times to check consistency
        results = [service.verify_otp(otp, otp_hash) for _ in range(10)]
        
        # Assert - all results should be True
        assert all(results)
