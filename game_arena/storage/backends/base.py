"""
Base storage backend interface for the Game Arena storage system.

This module defines the abstract interface that all storage backends
must implement to provide consistent data access patterns.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime

from ..models import GameRecord, MoveRecord, PlayerStats
from ..config import DatabaseConfig


class StorageBackend(ABC):
    """Abstract base class for storage backends."""
    
    def __init__(self, config: DatabaseConfig):
        """Initialize the storage backend with configuration."""
        self.config = config
        self._connected = False
    
    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to the storage backend."""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection to the storage backend."""
        pass
    
    @abstractmethod
    async def initialize_schema(self) -> None:
        """Initialize database schema and tables."""
        pass
    
    @property
    def is_connected(self) -> bool:
        """Check if backend is connected."""
        return self._connected
    
    # Game operations
    @abstractmethod
    async def create_game(self, game: GameRecord) -> str:
        """Create a new game record and return the game ID."""
        pass
    
    @abstractmethod
    async def get_game(self, game_id: str) -> Optional[GameRecord]:
        """Retrieve a game record by ID."""
        pass
    
    @abstractmethod
    async def update_game(self, game_id: str, updates: Dict[str, Any]) -> bool:
        """Update a game record with new data."""
        pass
    
    @abstractmethod
    async def delete_game(self, game_id: str) -> bool:
        """Delete a game record and all associated data."""
        pass
    
    # Move operations
    @abstractmethod
    async def add_move(self, move: MoveRecord) -> bool:
        """Add a move record to the database."""
        pass
    
    @abstractmethod
    async def get_moves(self, game_id: str, limit: Optional[int] = None) -> List[MoveRecord]:
        """Get all moves for a game."""
        pass
    
    @abstractmethod
    async def get_move(self, game_id: str, move_number: int, player: int) -> Optional[MoveRecord]:
        """Get a specific move record."""
        pass
    
    @abstractmethod
    async def update_move(self, move: MoveRecord) -> bool:
        """Update an existing move record."""
        pass
    
    @abstractmethod
    async def add_rethink_attempt(self, game_id: str, move_number: int, 
                                 player: int, rethink_attempt: 'RethinkAttempt') -> bool:
        """Add a rethink attempt record."""
        pass
    
    # Player statistics operations
    @abstractmethod
    async def update_player_stats(self, player_id: str, stats: PlayerStats) -> bool:
        """Update player statistics."""
        pass
    
    @abstractmethod
    async def get_player_stats(self, player_id: str) -> Optional[PlayerStats]:
        """Get player statistics."""
        pass
    
    # Query operations
    @abstractmethod
    async def query_games(self, filters: Dict[str, Any], limit: Optional[int] = None, 
                         offset: Optional[int] = None) -> List[GameRecord]:
        """Query games with filters."""
        pass
    
    @abstractmethod
    async def count_games(self, filters: Dict[str, Any]) -> int:
        """Count games matching filters."""
        pass
    
    # Maintenance operations
    @abstractmethod
    async def cleanup_old_data(self, older_than: datetime) -> int:
        """Clean up data older than specified date."""
        pass
    
    @abstractmethod
    async def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage backend statistics."""
        pass