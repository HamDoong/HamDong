"""Domain exceptions module."""


class DomainException(Exception):
    """Base domain exception."""

    def __init__(self, message: str, code: str) -> None:
        """Initialize domain exception.
        
        Args:
            message: Human-readable error message
            code: Machine-readable error code
        """
        self.message = message
        self.code = code
        super().__init__(self.message)


class ValidationException(DomainException):
    """Raised when domain validation fails."""

    def __init__(self, message: str, code: str = "VALIDATION_ERROR") -> None:
        """Initialize validation exception."""
        super().__init__(message, code)


class RateLimitException(DomainException):
    """Raised when rate limit is exceeded."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        code: str = "RATE_LIMIT_EXCEEDED",
    ) -> None:
        """Initialize rate limit exception."""
        super().__init__(message, code)


class OTPException(DomainException):
    """Raised for OTP-related errors."""

    def __init__(self, message: str, code: str = "OTP_ERROR") -> None:
        """Initialize OTP exception."""
        super().__init__(message, code)


class AuthenticationException(DomainException):
    """Raised when authentication fails."""

    def __init__(
        self,
        message: str = "Authentication failed",
        code: str = "AUTHENTICATION_FAILED",
    ) -> None:
        """Initialize authentication exception."""
        super().__init__(message, code)
