"""
Storage backend implementations for the Game Arena storage system.

This package provides different storage backend implementations including
SQLite for development and PostgreSQL for production use.
"""

from .base import StorageBackend
from .sqlite_backend import SQLiteBackend

try:
    from .postgresql_backend import PostgreSQLBackend
    _POSTGRESQL_AVAILABLE = True
except ImportError:
    PostgreSQLBackend = None
    _POSTGRESQL_AVAILABLE = False

__all__ = [
    "StorageBackend",
    "SQLiteBackend",
]

if _POSTGRESQL_AVAILABLE:
    __all__.append("PostgreSQLBackend")