import json
import os
import time
from threading import Lock

import httpx
from jwt import algorithms


class JWKSClient:
    def __init__(self, jwks_url: str | None = None, public_key_path: str | None = None, cache_ttl: int = 600):
        self.jwks_url = jwks_url or os.getenv("IDENTITY_JWKS_URL")
        self.public_key_path = public_key_path or os.getenv("IDENTITY_PUBLIC_KEY_PATH")
        self.cache_ttl = int(os.getenv("JWKS_CACHE_TTL", str(cache_ttl)))
        self._cache = {}
        self._lock = Lock()

    def _load_pem(self):
        if not self.public_key_path:
            return None
        try:
            with open(self.public_key_path, "r", encoding="utf-8") as file_handle:
                return file_handle.read()
        except OSError:
            return None

    def _fetch_jwks(self):
        if not self.jwks_url:
            return None
        response = httpx.get(self.jwks_url, timeout=5.0)
        response.raise_for_status()
        return response.json()

    def get_public_key(self, kid=None, header=None):
        pem = self._load_pem()
        if pem:
            return pem

        now = time.time()
        with self._lock:
            cache_entry = self._cache.get("jwks")
            if not cache_entry or now - cache_entry["fetched_at"] > self.cache_ttl:
                jwks = self._fetch_jwks()
                self._cache["jwks"] = {"jwks": jwks, "fetched_at": now}
            else:
                jwks = cache_entry["jwks"]

        if not jwks:
            raise RuntimeError("No JWKS available")

        keys = jwks.get("keys", [])
        if kid is None and len(keys) == 1:
            return algorithms.RSAAlgorithm.from_jwk(json.dumps(keys[0]))

        for key in keys:
            if key.get("kid") == kid:
                return algorithms.RSAAlgorithm.from_jwk(json.dumps(key))

        raise KeyError(f"JWKS key not found for kid={kid}")


_default_jwks_client = None


def get_default_jwks_client():
    global _default_jwks_client
    if _default_jwks_client is None:
        _default_jwks_client = JWKSClient()
    return _default_jwks_client
