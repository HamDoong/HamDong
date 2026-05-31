import json
import logging
from functools import lru_cache
from pathlib import Path

import httpx
import jwt
from cryptography.hazmat.primitives import serialization
from django.conf import settings

logger = logging.getLogger(__name__)


class JWKSClient:
    def __init__(self, jwks_url=None, public_key_path=None):
        self.jwks_url = jwks_url or getattr(settings, "IDENTITY_JWKS_URL", "")
        self.public_key_path = public_key_path or getattr(settings, "IDENTITY_PUBLIC_KEY_PATH", "")

    def _load_pem(self):
        if not self.public_key_path:
            return None
        path = Path(self.public_key_path)
        if not path.exists():
            return None
        with path.open("rb") as handle:
            return serialization.load_pem_public_key(handle.read())

    def _fetch_jwks(self):
        if not self.jwks_url:
            return None
        return get_cached_jwks(self.jwks_url)

    def get_public_key(self, kid=None, header=None):
        pem_key = self._load_pem()
        if pem_key is not None:
            return pem_key
        jwks = self._fetch_jwks()
        if not jwks:
            return None
        keys = jwks.get("keys", [])
        if kid:
            keys = [key for key in keys if key.get("kid") == kid]
        if not keys:
            return None
        return jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(keys[0]))


@lru_cache(maxsize=1)
def get_default_jwks_client():
    return JWKSClient()


@lru_cache(maxsize=8)
def get_cached_jwks(jwks_url):
    response = httpx.get(jwks_url, timeout=5.0)
    response.raise_for_status()
    return response.json()


def get_jwks():
    return get_default_jwks_client()._fetch_jwks()