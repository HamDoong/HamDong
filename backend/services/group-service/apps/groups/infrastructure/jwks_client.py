"""JWKS / public key loader for group-service."""

import time
import json
from typing import Optional, Dict

import httpx
from django.conf import settings

_cached_jwks: Optional[Dict] = None
_cached_at: float = 0.0
_cache_ttl = 600  # seconds


def get_jwks() -> Optional[Dict]:
    global _cached_jwks, _cached_at
    now = time.time()
    if _cached_jwks and (now - _cached_at) < _cache_ttl:
        return _cached_jwks

    # Prefer local public key file for development
    pub_path = getattr(settings, "IDENTITY_PUBLIC_KEY_PATH", None)
    if pub_path:
        try:
            with open(pub_path, "r", encoding="utf-8") as fh:
                pem = fh.read()
            # return a JWKS-like dict using a single key (consumer will load PEM directly)
            _cached_jwks = {"pem": pem}
            _cached_at = now
            return _cached_jwks
        except Exception:
            # fallthrough to HTTP JWKS
            pass

    jwks_url = getattr(settings, "IDENTITY_JWKS_URL", None)
    if not jwks_url:
        return None

    try:
        with httpx.Client(timeout=5.0) as client:
            resp = client.get(jwks_url)
            if resp.status_code == 200:
                _cached_jwks = resp.json()
                _cached_at = now
                return _cached_jwks
    except Exception:
        return None

    return None
