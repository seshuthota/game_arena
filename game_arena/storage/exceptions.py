"""
Exception classes for the Game Arena storage system.

This module defines custom exceptions used throughout the storage system
to provide clear error handling and debugging information.
"""


class StorageError(Exception):
    """Base exception for storage system errors."""
    pass


class ValidationError(StorageError):
    """Raised when data validation fails."""
    pass


class TransactionError(StorageError):
    """Raised when transaction operations fail."""
    pass


class GameNotFoundError(StorageError):
    """Raised when a requested game cannot be found."""
    pass


class DuplicateGameError(StorageError):
    """Raised when attempting to create a game that already exists."""
    pass


class MoveNotFoundError(StorageError):
    """Raised when a requested move cannot be found."""
    pass


class PlayerNotFoundError(StorageError):
    """Raised when a requested player cannot be found."""
    pass


class BackendError(StorageError):
    """Raised when storage backend operations fail."""
    pass


class ConfigurationError(StorageError):
    """Raised when storage configuration is invalid."""
    pass


class PerformanceError(StorageError):
    """Raised when performance constraints are violated."""
    pass