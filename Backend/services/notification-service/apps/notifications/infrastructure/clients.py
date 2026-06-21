"""HTTP clients for notification-service dependencies."""

import httpx


def create_http_client(timeout_seconds: int = 15) -> httpx.Client:
    return httpx.Client(timeout=timeout_seconds)
