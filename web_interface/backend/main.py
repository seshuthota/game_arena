"""
FastAPI application for Game Analysis Web Interface.

This module provides the main FastAPI application with proper configuration,
middleware setup, and route registration for the game analysis web interface.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from config import get_settings
from dependencies import get_storage_manager, get_query_engine
from exceptions import GameAnalysisError, GameNotFoundError, InvalidFiltersError
from routes import games, statistics, players, search

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan manager for startup and shutdown tasks.
    
    Handles initialization and cleanup of storage connections and resources.
    """
    settings = get_settings()
    logger.info(f"Starting Game Analysis API v{settings.version}")
    
    try:
        # Initialize storage manager
        storage_manager = await get_storage_manager()
        await storage_manager.initialize()
        logger.info("Storage manager initialized successfully")
        
        # Create query engine with the initialized storage manager
        from game_arena.storage import QueryEngine
        query_engine = QueryEngine(storage_manager)
        logger.info("Query engine initialized successfully")
        
        # Store in app state for access in dependencies
        app.state.storage_manager = storage_manager
        app.state.query_engine = query_engine
        
        yield
        
    except Exception as e:
        logger.error(f"Failed to initialize application: {e}")
        raise
    finally:
        # Cleanup on shutdown
        if hasattr(app.state, 'storage_manager'):
            try:
                await app.state.storage_manager.shutdown()
                logger.info("Storage manager shutdown complete")
            except Exception as e:
                logger.error(f"Error during storage manager shutdown: {e}")


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.
    
    Returns:
        Configured FastAPI application instance
    """
    settings = get_settings()
    
    app = FastAPI(
        title="Game Analysis API",
        description="REST API for analyzing chess games played between LLM agents",
        version=settings.version,
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        lifespan=lifespan
    )
    
    # Add middleware
    setup_middleware(app, settings)
    
    # Add exception handlers
    setup_exception_handlers(app)
    
    # Include routers
    setup_routes(app)
    
    return app


def setup_middleware(app: FastAPI, settings) -> None:
    """Configure application middleware."""
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )
    
    # Compression middleware
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    
    # Request logging middleware
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        """Log all HTTP requests for debugging and monitoring."""
        start_time = time.time()
        
        # Log request
        logger.info(f"{request.method} {request.url.path} - Client: {request.client.host}")
        
        try:
            response = await call_next(request)
            
            # Log response
            process_time = time.time() - start_time
            logger.info(
                f"{request.method} {request.url.path} - "
                f"Status: {response.status_code} - "
                f"Time: {process_time:.3f}s"
            )
            
            # Add timing header
            response.headers["X-Process-Time"] = str(process_time)
            
            return response
            
        except Exception as e:
            process_time = time.time() - start_time
            logger.error(
                f"{request.method} {request.url.path} - "
                f"Error: {str(e)} - "
                f"Time: {process_time:.3f}s"
            )
            raise


def setup_exception_handlers(app: FastAPI) -> None:
    """Configure global exception handlers."""
    
    @app.exception_handler(GameNotFoundError)
    async def game_not_found_handler(request: Request, exc: GameNotFoundError):
        """Handle game not found errors."""
        logger.warning(f"Game not found: {exc}")
        return JSONResponse(
            status_code=404,
            content={
                "error": "Game not found",
                "detail": str(exc),
                "error_code": "GAME_NOT_FOUND"
            }
        )
    
    @app.exception_handler(InvalidFiltersError)
    async def invalid_filters_handler(request: Request, exc: InvalidFiltersError):
        """Handle invalid filter parameter errors."""
        logger.warning(f"Invalid filters: {exc}")
        return JSONResponse(
            status_code=400,
            content={
                "error": "Invalid filters",
                "detail": str(exc),
                "error_code": "INVALID_FILTERS"
            }
        )
    
    @app.exception_handler(GameAnalysisError)
    async def game_analysis_error_handler(request: Request, exc: GameAnalysisError):
        """Handle general game analysis errors."""
        logger.error(f"Game analysis error: {exc}")
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "detail": "An error occurred while processing your request",
                "error_code": "INTERNAL_ERROR"
            }
        )
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Handle request validation errors."""
        logger.warning(f"Validation error: {exc}")
        return JSONResponse(
            status_code=422,
            content={
                "error": "Validation error",
                "detail": exc.errors(),
                "error_code": "VALIDATION_ERROR"
            }
        )
    
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        """Handle HTTP exceptions."""
        logger.warning(f"HTTP exception: {exc.status_code} - {exc.detail}")
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": "HTTP error",
                "detail": exc.detail,
                "error_code": f"HTTP_{exc.status_code}"
            }
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle unexpected exceptions."""
        logger.error(f"Unexpected error: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "detail": "An unexpected error occurred",
                "error_code": "UNEXPECTED_ERROR"
            }
        )


def setup_routes(app: FastAPI) -> None:
    """Configure application routes."""
    
    # Health check endpoint
    @app.get("/health")
    async def health_check():
        """Health check endpoint for monitoring."""
        return {
            "status": "healthy",
            "version": get_settings().version,
            "timestamp": datetime.now().isoformat()
        }
    
    # Include API routers
    app.include_router(games.router, prefix="/api", tags=["games"])
    app.include_router(statistics.router, prefix="/api", tags=["statistics"])
    app.include_router(players.router, prefix="/api", tags=["players"])
    app.include_router(search.router, prefix="/api", tags=["search"])


# Import required modules for middleware
import time
from datetime import datetime

# Create the application instance
app = create_app()

if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info"
    )