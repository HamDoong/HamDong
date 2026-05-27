"""Authentication API endpoints."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Request, HTTPException, status

from ...application.dtos import OTPRequestDTO, OTPResponseDTO
from ...application.use_cases.request_otp import RequestOTPUseCase
from ...domain.exceptions import ValidationException, RateLimitException
from ..dependencies import get_otp_use_case

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/auth",
    tags=["auth"],
)


@router.post(
    "/otp/request",
    response_model=OTPResponseDTO,
    status_code=status.HTTP_200_OK,
)
async def request_otp(
    request_data: OTPRequestDTO,
    request: Request,
    use_case: Annotated[RequestOTPUseCase, Depends(get_otp_use_case)],
) -> OTPResponseDTO:
    """Request an OTP for authentication.
    
    Send a one-time password to the user's phone number for authentication.
    
    Args:
        request_data: The OTP request containing phone number
        request: The FastAPI request object (for client IP)
        use_case: The RequestOTPUseCase use case
        
    Returns:
        OTPResponseDTO with success message and expiration time
        
    Raises:
        HTTPException: If validation or rate limiting fails
    """
    # Extract client IP address
    client_ip = request.client.host if request.client else "unknown"
    
    # Add observability context
    request_id = request.headers.get("X-Request-ID", "unknown")
    logger.info(
        "OTP request received",
        extra={
            "request_id": request_id,
            "phone_number": request_data.phone_number,
            "client_ip": client_ip,
        },
    )
    
    try:
        # Execute the use case
        response = await use_case.execute(request_data, client_ip)
        
        logger.info(
            "OTP sent successfully",
            extra={
                "request_id": request_id,
                "phone_number": request_data.phone_number,
            },
        )
        
        return response
        
    except ValidationException as e:
        logger.warning(
            f"Validation error: {e.message}",
            extra={
                "request_id": request_id,
                "error_code": e.code,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"success": False, "error": e.code},
        )
        
    except RateLimitException as e:
        logger.warning(
            f"Rate limit exceeded: {e.message}",
            extra={
                "request_id": request_id,
                "client_ip": client_ip,
                "error_code": e.code,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"success": False, "error": e.code},
        )
        
    except Exception as e:
        logger.error(
            f"Unexpected error during OTP request: {str(e)}",
            extra={
                "request_id": request_id,
                "error": str(e),
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"success": False, "error": "INTERNAL_SERVER_ERROR"},
        )
