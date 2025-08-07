"""
Tournament integration utilities for the Game Arena storage system.

This module provides utilities for integrating data collection with tournament
execution, including setup, configuration, and coordination between agents
and storage systems.
"""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass

from .collector import GameDataCollector
from .manager import StorageManager
from .config import CollectorConfig, StorageConfig
from .models import PlayerInfo, GameOutcome
from .agent_wrapper import DataCollectingAgent, create_data_collecting_agent
from .backends.sqlite_backend import SQLiteBackend
from .backends.postgresql_backend import PostgreSQLBackend

from game_arena.harness.agent import (
    KaggleSpielAgent, 
    KaggleSpielActionWithExtras,
    ChessLLMAgent,
    ChessRethinkAgent
)

import pyspiel


logger = logging.getLogger(__name__)


@dataclass
class TournamentConfig:
    """Configuration for tournament data collection."""
    enabled: bool = True
    storage_backend: str = "sqlite"  # "sqlite" or "postgresql"
    database_path: Optional[str] = None
    database_url: Optional[str] = None
    collect_timing: bool = True
    collect_rethink: bool = True
    async_processing: bool = True
    worker_threads: int = 2
    max_collection_latency_ms: float = 50.0
    tournament_id: Optional[str] = None
    tournament_name: Optional[str] = None


class TournamentDataCollector:
    """
    High-level coordinator for tournament data collection.
    
    Manages the setup and coordination of data collection across multiple
    games in a tournament, providing a simple interface for tournament
    organizers to enable comprehensive data capture.
    """
    
    def __init__(self, config: TournamentConfig):
        """Initialize tournament data collector."""
        self.config = config
        self.tournament_id = config.tournament_id or str(uuid.uuid4())
        
        # Storage components
        self.storage_manager: Optional[StorageManager] = None
        self.game_collector: Optional[GameDataCollector] = None
        
        # Active games and agents
        self.active_games: Dict[str, str] = {}  # game_id -> game_name mapping
        self.wrapped_agents: Dict[str, DataCollectingAgent] = {}
        
        # Setup logging
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Tournament metadata
        self.tournament_start_time: Optional[datetime] = None
        self.games_completed = 0
        self.total_moves_collected = 0
    
    async def initialize(self) -> None:
        """Initialize the tournament data collection system."""
        if not self.config.enabled:
            self.logger.info("Tournament data collection is disabled")
            return
        
        try:
            # Create storage backend
            from .config import DatabaseConfig, StorageBackendType
            
            if self.config.storage_backend == "sqlite":
                db_config = DatabaseConfig(
                    backend_type=StorageBackendType.SQLITE,
                    database=self.config.database_path or "tournament_data.db",
                    connection_timeout=30
                )
                backend = SQLiteBackend(db_config)
            elif self.config.storage_backend == "postgresql":
                if not self.config.database_url:
                    raise ValueError("PostgreSQL database URL is required")
                db_config = DatabaseConfig(
                    backend_type=StorageBackendType.POSTGRESQL,
                    database_url=self.config.database_url,
                    connection_timeout=30
                )
                backend = PostgreSQLBackend(db_config)
            else:
                raise ValueError(f"Unsupported storage backend: {self.config.storage_backend}")
            
            # Initialize storage manager
            storage_config = StorageConfig(
                database=db_config,
                batch_size=50,
                max_concurrent_writes=5,
                enable_data_validation=True
            )
            self.storage_manager = StorageManager(backend, storage_config)
            await self.storage_manager.initialize()
            
            # Initialize game data collector
            collector_config = CollectorConfig(
                enabled=True,
                async_processing=self.config.async_processing,
                worker_threads=self.config.worker_threads,
                max_collection_latency_ms=self.config.max_collection_latency_ms,
                collect_rethink_data=self.config.collect_rethink
            )
            self.game_collector = GameDataCollector(self.storage_manager, collector_config)
            await self.game_collector.initialize()
            
            self.tournament_start_time = datetime.now()
            self.logger.info(f"Tournament data collection initialized for tournament {self.tournament_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize tournament data collection: {e}")
            raise
    
    async def shutdown(self) -> None:
        """Shutdown the tournament data collection system."""
        try:
            if self.game_collector:
                await self.game_collector.shutdown()
            
            if self.storage_manager:
                await self.storage_manager.close()
            
            # Log tournament summary
            duration = (datetime.now() - self.tournament_start_time).total_seconds() if self.tournament_start_time else 0
            self.logger.info(
                f"Tournament {self.tournament_id} completed: "
                f"{self.games_completed} games, {self.total_moves_collected} moves, "
                f"{duration:.1f}s duration"
            )
            
        except Exception as e:
            self.logger.error(f"Error during tournament data collection shutdown: {e}")
    
    def wrap_agent(
        self, 
        agent: KaggleSpielAgent[KaggleSpielActionWithExtras],
        player_info: PlayerInfo,
        agent_name: Optional[str] = None
    ) -> DataCollectingAgent:
        """
        Wrap an agent for data collection.
        
        Args:
            agent: The agent to wrap
            player_info: Information about the player
            agent_name: Optional name for the agent (for tracking)
            
        Returns:
            DataCollectingAgent wrapper
        """
        if not self.config.enabled or not self.game_collector:
            # Return original agent if data collection is disabled
            return agent
        
        wrapped_agent = create_data_collecting_agent(
            agent=agent,
            collector=self.game_collector,
            player_info=player_info,
            collect_timing=self.config.collect_timing,
            collect_rethink=self.config.collect_rethink,
            max_collection_latency_ms=self.config.max_collection_latency_ms
        )
        
        # Track wrapped agent
        agent_key = agent_name or f"agent_{len(self.wrapped_agents)}"
        self.wrapped_agents[agent_key] = wrapped_agent
        
        self.logger.info(f"Wrapped agent {agent_key} for data collection")
        return wrapped_agent
    
    def start_game(
        self, 
        game_name: str,
        players: Dict[int, PlayerInfo],
        metadata: Dict[str, Any] = None
    ) -> str:
        """
        Start a new game with data collection.
        
        Args:
            game_name: Human-readable name for the game
            players: Dictionary mapping player indices to PlayerInfo
            metadata: Additional game metadata
            
        Returns:
            Game ID for tracking
        """
        if not self.config.enabled or not self.game_collector:
            return str(uuid.uuid4())  # Return dummy ID if disabled
        
        game_id = str(uuid.uuid4())
        
        # Add tournament metadata
        game_metadata = {
            'tournament_id': self.tournament_id,
            'tournament_name': self.config.tournament_name,
            'game_name': game_name,
            **(metadata or {})
        }
        
        # Start game collection
        success = self.game_collector.start_game(game_id, players, game_metadata)
        
        if success:
            self.active_games[game_id] = game_name
            self.logger.info(f"Started game {game_name} (ID: {game_id})")
        else:
            self.logger.warning(f"Failed to start data collection for game {game_name}")
        
        return game_id
    
    def end_game(
        self,
        game_id: str,
        outcome: GameOutcome,
        final_fen: str,
        total_moves: int
    ) -> bool:
        """
        End a game and finalize data collection.
        
        Args:
            game_id: ID of the game to end
            outcome: Final game outcome
            final_fen: Final board position
            total_moves: Total number of moves played
            
        Returns:
            True if game was ended successfully
        """
        if not self.config.enabled or not self.game_collector:
            return True
        
        success = self.game_collector.end_game(game_id, outcome, final_fen, total_moves)
        
        if success:
            game_name = self.active_games.pop(game_id, "Unknown")
            self.games_completed += 1
            self.total_moves_collected += total_moves
            self.logger.info(f"Completed game {game_name} (ID: {game_id}) with {total_moves} moves")
        else:
            self.logger.warning(f"Failed to end data collection for game {game_id}")
        
        return success
    
    def set_game_id_for_agents(self, game_id: str) -> None:
        """Set the current game ID for all wrapped agents."""
        for agent in self.wrapped_agents.values():
            agent.set_game_id(game_id)
    
    def get_tournament_stats(self) -> Dict[str, Any]:
        """Get current tournament statistics."""
        stats = {
            'tournament_id': self.tournament_id,
            'tournament_name': self.config.tournament_name,
            'start_time': self.tournament_start_time.isoformat() if self.tournament_start_time else None,
            'games_completed': self.games_completed,
            'total_moves_collected': self.total_moves_collected,
            'active_games': len(self.active_games),
            'wrapped_agents': len(self.wrapped_agents)
        }
        
        # Add collector stats if available
        if self.game_collector:
            collector_stats = self.game_collector.get_stats()
            stats.update({
                'events_processed': collector_stats.events_processed,
                'events_failed': collector_stats.events_failed,
                'average_processing_time_ms': collector_stats.average_processing_time_ms,
                'queue_size': collector_stats.queue_size
            })
        
        # Add agent collection stats
        agent_stats = {}
        for name, agent in self.wrapped_agents.items():
            agent_stats[name] = agent.get_collection_stats()
        stats['agent_stats'] = agent_stats
        
        return stats


def create_tournament_collector(
    tournament_name: str,
    storage_backend: str = "sqlite",
    database_path: Optional[str] = None,
    database_url: Optional[str] = None,
    **kwargs
) -> TournamentDataCollector:
    """
    Factory function to create a tournament data collector.
    
    Args:
        tournament_name: Name of the tournament
        storage_backend: Storage backend to use ("sqlite" or "postgresql")
        database_path: Path for SQLite database
        database_url: URL for PostgreSQL database
        **kwargs: Additional configuration options
        
    Returns:
        TournamentDataCollector instance
    """
    config = TournamentConfig(
        tournament_name=tournament_name,
        storage_backend=storage_backend,
        database_path=database_path,
        database_url=database_url,
        **kwargs
    )
    
    return TournamentDataCollector(config)


def enable_agent_data_collection(
    agent: KaggleSpielAgent[KaggleSpielActionWithExtras],
    callback_func
) -> None:
    """
    Enable data collection for an agent directly.
    
    This is a utility function for enabling data collection on agents
    without using the full tournament integration.
    
    Args:
        agent: Agent to enable data collection for
        callback_func: Callback function for data collection events
    """
    if hasattr(agent, 'enable_data_collection'):
        agent.enable_data_collection(callback_func)
    else:
        logger.warning(f"Agent {type(agent).__name__} does not support data collection")


def create_demo_players(
    player1_name: str = "Player 1",
    player2_name: str = "Player 2",
    player1_model: str = "Unknown",
    player2_model: str = "Unknown"
) -> Dict[int, PlayerInfo]:
    """
    Create player info for demo tournaments.
    
    Args:
        player1_name: Name of player 1 (Black)
        player2_name: Name of player 2 (White)
        player1_model: Model name for player 1
        player2_model: Model name for player 2
        
    Returns:
        Dictionary mapping player indices to PlayerInfo
    """
    return {
        0: PlayerInfo(  # Black
            player_id=f"demo_{player1_name.lower().replace(' ', '_')}",
            model_name=player1_model,
            model_provider="demo",
            agent_type="ChessLLMAgent",
            agent_config={"player_name": player1_name},
            elo_rating=1500.0
        ),
        1: PlayerInfo(  # White
            player_id=f"demo_{player2_name.lower().replace(' ', '_')}",
            model_name=player2_model,
            model_provider="demo",
            agent_type="ChessLLMAgent",
            agent_config={"player_name": player2_name},
            elo_rating=1500.0
        )
    }


def determine_game_outcome(pyspiel_state: pyspiel.State) -> Optional[GameOutcome]:
    """
    Determine the game outcome from a pyspiel state.
    
    Args:
        pyspiel_state: The final game state
        
    Returns:
        GameOutcome if game is terminal, None otherwise
    """
    if not pyspiel_state.is_terminal():
        return None
    
    from .models import GameResult, TerminationReason
    
    returns = pyspiel_state.returns()
    
    if returns[0] == 1:  # Black wins
        result = GameResult.BLACK_WINS
        winner_player = 0
    elif returns[1] == 1:  # White wins
        result = GameResult.WHITE_WINS
        winner_player = 1
    else:  # Draw
        result = GameResult.DRAW
        winner_player = None
    
    return GameOutcome(
        result=result,
        winner=winner_player,
        termination=TerminationReason.CHECKMATE  # Default, could be enhanced
    )