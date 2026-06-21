"""JWT key loading and management."""

import logging
from pathlib import Path
from typing import Optional

from django.conf import settings

logger = logging.getLogger(__name__)


class JwtKeyLoader:
    """Loads and caches JWT keys from filesystem."""

    _private_key: Optional[str] = None
    _public_key: Optional[str] = None

    @classmethod
    def get_private_key(cls) -> str:
        """Get private key for signing tokens."""
        if cls._private_key is not None:
            return cls._private_key

        key_path = Path(settings.JWT_PRIVATE_KEY_PATH)

        if not key_path.exists():
            raise FileNotFoundError(
                f"Private key not found at {settings.JWT_PRIVATE_KEY_PATH}. "
                "Please generate keys using: python manage.py shell < generate_keys.py"
            )

        with open(key_path, "r") as f:
            cls._private_key = f.read()

        logger.info(f"Loaded private key from {key_path}")
        return cls._private_key

    @classmethod
    def get_public_key(cls) -> str:
        """Get public key for verifying tokens."""
        if cls._public_key is not None:
            return cls._public_key

        key_path = Path(settings.JWT_PUBLIC_KEY_PATH)

        if not key_path.exists():
            raise FileNotFoundError(
                f"Public key not found at {settings.JWT_PUBLIC_KEY_PATH}. "
                "Please generate keys using: python manage.py shell < generate_keys.py"
            )

        with open(key_path, "r") as f:
            cls._public_key = f.read()

        logger.info(f"Loaded public key from {key_path}")
        return cls._public_key

    @classmethod
    def clear_cache(cls):
        """Clear cached keys (useful for testing)."""
        cls._private_key = None
        cls._public_key = None
