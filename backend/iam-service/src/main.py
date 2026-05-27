"""Main FastAPI application setup."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from src.configuration.settings import get_settings
from src.presentation.api.v1 import auth

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown events.
    
    Args:
        app: The FastAPI application instance
        
    Yields:
        Control back to FastAPI
    """
    # Startup
    logger.info("HamDong IAM Service starting up...")
    yield
    # Shutdown
    logger.info("HamDong IAM Service shutting down...")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.
    
    Returns:
        The configured FastAPI application instance
    """
    settings = get_settings()
    
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
        lifespan=lifespan,
    )
    
    # Include routers
    app.include_router(auth.router)
    
    # Root health check endpoint
    @app.get("/health")
    async def health_check():
        """Health check endpoint.
        
        Returns:
            Status OK
        """
        return {"status": "ok", "service": settings.app_name}
    
    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request, exc: Exception):
        """Handle uncaught exceptions globally.
        
        Args:
            request: The HTTP request
            exc: The exception that was raised
            
        Returns:
            JSON error response
        """
        logger.error(
            f"Unhandled exception: {str(exc)}",
            exc_info=True,
        )
        
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "INTERNAL_SERVER_ERROR",
            },
        )
    
    logger.info(f"{settings.app_name} v{settings.app_version} created")
    
    return app


# Create the app instance
app = create_app()
