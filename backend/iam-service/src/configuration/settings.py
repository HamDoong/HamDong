"""Application configuration and settings."""

from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings.
    
    Settings are loaded from environment variables or .env file.
    """

    # Application
    app_name: str = "HamDong IAM Service"
    app_version: str = "1.0.0"
    debug: bool = False
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    
    # Database
    database_url: str = "postgresql://user:password@localhost/hamdong_iam"
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    
    # Security
    jwt_secret_key: str = "your-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24
    otp_secret_key: str = "otp-secret-key-change-in-production"
    
    # OTP Configuration
    otp_ttl_seconds: int = 120
    otp_length: int = 6
    
    # Rate Limiting
    otp_requests_per_phone: int = 3
    otp_requests_window_minutes: int = 5
    otp_requests_per_ip: int = 10
    otp_requests_window_seconds: int = 60
    
    # SMS Service
    sms_provider: str = "mock"  # "mock" or "twilio"
    twilio_account_sid: Optional[str] = None
    twilio_auth_token: Optional[str] = None
    twilio_phone_number: Optional[str] = None
    
    # Observability
    log_level: str = "INFO"
    
    class Config:
        """Pydantic config."""
        
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get application settings (cached).
    
    Returns:
        The application settings instance
    """
    return Settings()
