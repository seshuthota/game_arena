"""
Game Arena Storage System

This package provides comprehensive data storage and analytics capabilities
for chess games played between LLM agents.
"""

from .models import (
    GameRecord,
    PlayerInfo,
    GameOutcome,
    GameResult,
    TerminationReason,
    MoveRecord,
    RethinkAttempt,
    PlayerStats,
    MoveAccuracyStats,
)
from .config import StorageConfig, CollectorConfig, DatabaseConfig
from .manager import StorageManager
from .query_engine import QueryEngine, GameFilters, MoveFilters
from .export import GameExporter
from .exceptions import (
    StorageError,
    ValidationError,
    TransactionError,
    GameNotFoundError,
    DuplicateGameError,
)

__all__ = [
    "GameRecord",
    "PlayerInfo", 
    "GameOutcome",
    "GameResult",
    "TerminationReason",
    "MoveRecord",
    "RethinkAttempt",
    "PlayerStats",
    "MoveAccuracyStats",
    "StorageConfig",
    "CollectorConfig",
    "DatabaseConfig",
    "StorageManager",
    "StorageError",
    "ValidationError",
    "TransactionError",
    "GameNotFoundError",
    "DuplicateGameError",
]