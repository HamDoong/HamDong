"""Value objects for identity domain."""


class PhoneNumber:
    """Value object representing a phone number."""

    def __init__(self, number: str):
        """Initialize phone number value object."""
        self.number = number

    def __str__(self):
        return self.number

    def __eq__(self, other):
        return isinstance(other, PhoneNumber) and self.number == other.number

    def __hash__(self):
        return hash(self.number)

    @property
    def normalized(self) -> str:
        """Get normalized phone number."""
        return self.number


class Otp:
    """Value object representing an OTP."""

    def __init__(self, code: str):
        """Initialize OTP value object."""
        self.code = code

    def __str__(self):
        return "*" * len(self.code)  # Never expose OTP in string representation

    def __eq__(self, other):
        return isinstance(other, Otp) and self.code == other.code


class JwtToken:
    """Value object representing a JWT token."""

    def __init__(self, token: str, token_type: str = "Bearer"):
        """Initialize JWT token value object."""
        self.token = token
        self.token_type = token_type

    def __str__(self):
        return f"{self.token_type} {self.token[:20]}..."  # Don't expose full token

    @property
    def bearer_string(self) -> str:
        """Get Bearer token string."""
        return f"{self.token_type} {self.token}"
