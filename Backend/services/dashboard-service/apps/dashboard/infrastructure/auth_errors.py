from __future__ import annotations

from rest_framework.exceptions import APIException


class JWTPublicKeyUnavailable(APIException):
    status_code = 503
    default_code = "JWT_PUBLIC_KEY_UNAVAILABLE"
    default_detail = {
        "code": "JWT_PUBLIC_KEY_UNAVAILABLE",
        "message": "JWT public key is not available.",
    }
