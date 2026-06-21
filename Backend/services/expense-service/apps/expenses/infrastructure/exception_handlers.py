from __future__ import annotations

from rest_framework.exceptions import AuthenticationFailed, NotAuthenticated
from rest_framework.views import exception_handler


def _build_error(detail, *, default_code: str, default_message: str) -> dict:
    if isinstance(detail, dict):
        code = str(detail.get("code") or default_code)
        message = str(detail.get("message") or default_message)
        return {"code": code, "message": message}
    if hasattr(detail, "code") and hasattr(detail, "string"):
        return {
            "code": str(getattr(detail, "code", default_code) or default_code).upper(),
            "message": str(getattr(detail, "string", default_message) or default_message),
        }
    return {"code": default_code, "message": default_message}


def api_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        return None

    if isinstance(exc, NotAuthenticated):
        response.data = {
            "error": _build_error(
                getattr(exc, "detail", None),
                default_code="NOT_AUTHENTICATED",
                default_message="Authentication credentials were not provided.",
            )
        }
        return response

    if isinstance(exc, AuthenticationFailed):
        detail = getattr(exc, "detail", None)
        default_code = "INVALID_TOKEN"
        default_message = "The provided token is invalid."
        if isinstance(detail, dict) and detail.get("code") == "TOKEN_EXPIRED":
            default_code = "TOKEN_EXPIRED"
            default_message = "The provided token has expired."
        elif isinstance(detail, dict) and detail.get("code") == "INVALID_TOKEN_TYPE":
            default_code = "INVALID_TOKEN_TYPE"
            default_message = "Access token is required."
        response.data = {
            "error": _build_error(
                detail,
                default_code=default_code,
                default_message=default_message,
            )
        }
        return response

    detail = getattr(exc, "detail", None)
    if isinstance(detail, dict) and {"code", "message"} <= set(detail.keys()):
        response.data = {
            "error": _build_error(
                detail,
                default_code=str(detail["code"]),
                default_message=str(detail["message"]),
            )
        }
    return response
