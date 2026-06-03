from __future__ import annotations

import json
import os
import time
from pathlib import Path
from threading import Lock
from typing import Any

import httpx
from django.conf import settings
from jwt import algorithms


class JWKSClientError(RuntimeError):
    """Raised when a verifier service cannot load a usable JWT public key."""


class JWKSClient:
    def __init__(
        self,
        jwks_url: str | None = None,
        public_key_path: str | None = None,
        cache_ttl: int = 600,
    ) -> None:
        self.jwks_url = jwks_url or os.getenv("IDENTITY_JWKS_URL") or getattr(settings, "IDENTITY_JWKS_URL", "")
        self.public_key_path = public_key_path or os.getenv("IDENTITY_PUBLIC_KEY_PATH") or getattr(settings, "IDENTITY_PUBLIC_KEY_PATH", "")
        self.cache_ttl = int(os.getenv("JWKS_CACHE_TTL", cache_ttl))
        self._cache: dict[str, Any] = {}
        self._lock = Lock()

    def _get_cached_value(self, cache_key: str):
        entry = self._cache.get(cache_key)
        if entry and (time.time() - entry["fetched_at"]) < self.cache_ttl:
            return entry["value"]
        return None

    def _set_cache_value(self, cache_key: str, value: Any) -> Any:
        self._cache[cache_key] = {"value": value, "fetched_at": time.time()}
        return value

    def _load_pem(self) -> str | None:
        if not self.public_key_path:
            return None

        path = Path(self.public_key_path)
        if not path.exists():
            return None

        cached_pem = self._get_cached_value("pem")
        if cached_pem is not None:
            return cached_pem

        try:
            pem = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise JWKSClientError("JWT public key is not available.") from exc

        return self._set_cache_value("pem", pem)

    def _fetch_jwks(self) -> dict[str, Any]:
        if not self.jwks_url:
            raise JWKSClientError("JWT public key is not available.")

        try:
            response = httpx.get(self.jwks_url, timeout=5.0)
            response.raise_for_status()
            data = response.json()
        except Exception as exc:
            raise JWKSClientError("JWT public key is not available.") from exc

        keys = data.get("keys")
        if not isinstance(keys, list) or not keys:
            raise JWKSClientError("JWT public key is not available.")
        return data

    def _get_cached_jwks(self) -> dict[str, Any]:
        with self._lock:
            cached_jwks = self._get_cached_value("jwks")
            if cached_jwks is not None:
                return cached_jwks
            return self._set_cache_value("jwks", self._fetch_jwks())

    def get_public_key(self, kid: str | None = None, header: dict | None = None):
        pem = self._load_pem()
        if pem:
            return pem

        jwks = self._get_cached_jwks()
        keys = jwks.get("keys", [])
        if kid is None and len(keys) == 1:
            return algorithms.RSAAlgorithm.from_jwk(json.dumps(keys[0]))

        for key in keys:
            if key.get("kid") == kid:
                return algorithms.RSAAlgorithm.from_jwk(json.dumps(key))

        raise JWKSClientError("JWT public key is not available.")

    def clear_cache(self) -> None:
        with self._lock:
            self._cache.clear()


_default_jwks_client: JWKSClient | None = None


def get_default_jwks_client() -> JWKSClient:
    global _default_jwks_client
    if _default_jwks_client is None:
        _default_jwks_client = JWKSClient()
    return _default_jwks_client


def get_jwks():
    return get_default_jwks_client()._get_cached_jwks()
