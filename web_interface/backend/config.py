"""
Configuration settings for the Game Analysis Web Interface API.

This module provides configuration management using Pydantic settings
with environment variable support and validation.
"""

import os
from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application settings with environment variable support.
    
    All settings can be overridden using environment variables with
    the GAME_ANALYSIS_ prefix (e.g., GAME_ANALYSIS_DEBUG=true).
    """
    
    # Application settings
    version: str = "1.0.0"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000
    
    # CORS settings
    allowed_origins: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    
    # Database settings
    database_url: str = "sqlite:////home/seshu/Documents/Python/game_arena/demo_tournament.db"
    
    # Storage settings
    storage_backend: str = "sqlite"
    enable_data_validation: bool = True
    log_level: str = "INFO"
    
    # API settings
    max_page_size: int = 1000
    default_page_size: int = 50
    
    # Performance settings
    enable_query_caching: bool = True
    cache_ttl_seconds: int = 300  # 5 minutes
    
    class Config:
        """Pydantic configuration."""
        env_prefix = "GAME_ANALYSIS_"
        case_sensitive = False
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # Ignore extra fields from environment


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached application settings.
    
    Returns:
        Settings instance with current configuration
    """
    return Settings()