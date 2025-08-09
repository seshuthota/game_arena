"""
Dependency injection for the Game Analysis Web Interface API.

This module provides dependency injection functions for FastAPI that handle
the creation and management of storage connections, query engines, and other
shared resources.
"""

import logging
from typing import AsyncGenerator

from fastapi import Depends, HTTPException, Request

from game_arena.storage import StorageManager, QueryEngine
from game_arena.storage.config import StorageConfig, DatabaseConfig, LogLevel
from game_arena.storage.backends.sqlite_backend import SQLiteBackend
from game_arena.storage.backends.postgresql_backend import PostgreSQLBackend

from config import get_settings, Settings
from exceptions import StorageConnectionError

logger = logging.getLogger(__name__)


async def get_storage_manager() -> StorageManager:
    """
    Create and return a configured StorageManager instance.
    
    This function creates the appropriate storage backend based on configuration
    and initializes the StorageManager with proper settings.
    
    Returns:
        Configured StorageManager instance
        
    Raises:
        StorageConnectionError: If storage initialization fails
    """
    settings = get_settings()
    
    try:
        # Create database configuration
        db_config = DatabaseConfig.from_url(settings.database_url)
        
        # Create storage configuration
        log_level_str = getattr(settings, 'log_level', 'INFO').upper()
        log_level_enum = getattr(LogLevel, log_level_str, LogLevel.INFO)
        
        storage_config = StorageConfig(
            database=db_config,
            enable_data_validation=settings.enable_data_validation,
            log_level=log_level_enum,
            enable_auto_backup=False  # Disable backup for web interface
        )
        
        # Create appropriate backend based on database URL
        if settings.database_url.startswith("sqlite"):
            backend = SQLiteBackend(db_config)
        elif settings.database_url.startswith("postgresql"):
            backend = PostgreSQLBackend(db_config)
        else:
            raise StorageConnectionError(f"Unsupported database URL: {settings.database_url}")
        
        # Create and return storage manager
        storage_manager = StorageManager(backend, storage_config)
        
        logger.info(f"Created StorageManager with {settings.storage_backend} backend")
        return storage_manager
        
    except Exception as e:
        logger.error(f"Failed to create StorageManager: {e}")
        raise StorageConnectionError(f"Storage initialization failed: {e}") from e


async def get_query_engine() -> QueryEngine:
    """
    Create and return a configured QueryEngine instance.
    
    Returns:
        Configured QueryEngine instance
        
    Raises:
        StorageConnectionError: If query engine initialization fails
    """
    try:
        storage_manager = await get_storage_manager()
        query_engine = QueryEngine(storage_manager)
        
        logger.info("Created QueryEngine instance")
        return query_engine
        
    except Exception as e:
        logger.error(f"Failed to create QueryEngine: {e}")
        raise StorageConnectionError(f"Query engine initialization failed: {e}") from e


def get_storage_manager_from_app(request: Request) -> StorageManager:
    """
    Get StorageManager from application state.
    
    This dependency function retrieves the StorageManager instance that was
    initialized during application startup and stored in the app state.
    
    Args:
        request: FastAPI request object
        
    Returns:
        StorageManager instance from app state
        
    Raises:
        HTTPException: If StorageManager is not available
    """
    if not hasattr(request.app.state, 'storage_manager'):
        logger.error("StorageManager not found in application state")
        raise HTTPException(
            status_code=500,
            detail="Storage manager not initialized"
        )
    
    return request.app.state.storage_manager


def get_query_engine_from_app(request: Request) -> QueryEngine:
    """
    Get QueryEngine from application state.
    
    This dependency function retrieves the QueryEngine instance that was
    initialized during application startup and stored in the app state.
    
    Args:
        request: FastAPI request object
        
    Returns:
        QueryEngine instance from app state
        
    Raises:
        HTTPException: If QueryEngine is not available
    """
    if not hasattr(request.app.state, 'query_engine'):
        logger.error("QueryEngine not found in application state")
        raise HTTPException(
            status_code=500,
            detail="Query engine not initialized"
        )
    
    return request.app.state.query_engine


def get_pagination_params(
    page: int = 1,
    limit: int = None
) -> tuple[int, int]:
    """
    Get and validate pagination parameters.
    
    Args:
        page: Page number (1-based)
        limit: Number of items per page
        
    Returns:
        Tuple of (page, limit) with validated values
        
    Raises:
        HTTPException: If pagination parameters are invalid
    """
    settings = get_settings()
    
    # Validate page number
    if page < 1:
        raise HTTPException(
            status_code=400,
            detail="Page number must be greater than 0"
        )
    
    # Set default limit if not provided
    if limit is None:
        limit = settings.default_page_size
    
    # Validate limit
    if limit < 1:
        raise HTTPException(
            status_code=400,
            detail="Limit must be greater than 0"
        )
    
    if limit > settings.max_page_size:
        raise HTTPException(
            status_code=400,
            detail=f"Limit cannot exceed {settings.max_page_size}"
        )
    
    return page, limit


def get_offset_from_page(page: int, limit: int) -> int:
    """
    Calculate offset from page number and limit.
    
    Args:
        page: Page number (1-based)
        limit: Number of items per page
        
    Returns:
        Offset for database queries (0-based)
    """
    return (page - 1) * limit