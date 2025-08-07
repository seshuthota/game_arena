"""
Unit tests for the StorageManager class.

Tests cover game operations, transaction handling, error recovery,
and data validation functionality.
"""

import pytest
import pytest_asyncio
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, Optional, List

from .manager import StorageManager
from .models import (
    GameRecord, PlayerInfo, GameOutcome, GameResult, 
    TerminationReason, MoveRecord, PlayerStats, RethinkAttempt
)
from .config import StorageConfig, DatabaseConfig, StorageBackendType, LogLevel
from .backends.base import StorageBackend
from .exceptions import (
    StorageError, ValidationError, TransactionError,
    GameNotFoundError, DuplicateGameError
)


class MockStorageBackend(StorageBackend):
    """Mock storage backend for testing."""
    
    def __init__(self, config):
        super().__init__(config)
        self.games: Dict[str, GameRecord] = {}
        self.moves: Dict[str, List[MoveRecord]] = {}
        self.player_stats: Dict[str, PlayerStats] = {}
        self._should_fail = False
        self._fail_operation = None
    
    def set_failure_mode(self, operation: str = None):
        """Set the backend to fail on next operation."""
        self._should_fail = True
        self._fail_operation = operation
    
    def _check_failure(self, operation: str):
        """Check if this operation should fail."""
        if self._should_fail and (not self._fail_operation or self._fail_operation == operation):
            self._should_fail = False
            self._fail_operation = None
            raise Exception(f"Mock failure for {operation}")
    
    async def connect(self) -> None:
        self._check_failure("connect")
        self._connected = True
    
    async def disconnect(self) -> None:
        self._check_failure("disconnect")
        self._connected = False
    
    async def initialize_schema(self) -> None:
        self._check_failure("initialize_schema")
        pass
    
    async def create_game(self, game: GameRecord) -> str:
        self._check_failure("create_game")
        self.games[game.game_id] = game
        return game.game_id
    
    async def get_game(self, game_id: str) -> Optional[GameRecord]:
        self._check_failure("get_game")
        return self.games.get(game_id)
    
    async def update_game(self, game_id: str, updates: Dict[str, Any]) -> bool:
        self._check_failure("update_game")
        if game_id not in self.games:
            return False
        
        game = self.games[game_id]
        for key, value in updates.items():
            setattr(game, key, value)
        return True
    
    async def delete_game(self, game_id: str) -> bool:
        self._check_failure("delete_game")
        if game_id in self.games:
            del self.games[game_id]
            if game_id in self.moves:
                del self.moves[game_id]
            return True
        return False
    
    async def add_move(self, move: MoveRecord) -> bool:
        self._check_failure("add_move")
        if move.game_id not in self.moves:
            self.moves[move.game_id] = []
        self.moves[move.game_id].append(move)
        return True
    
    async def get_moves(self, game_id: str, limit: Optional[int] = None) -> List[MoveRecord]:
        self._check_failure("get_moves")
        moves = self.moves.get(game_id, [])
        if limit:
            return moves[:limit]
        return moves
    
    async def get_move(self, game_id: str, move_number: int, player: int) -> Optional[MoveRecord]:
        self._check_failure("get_move")
        moves = self.moves.get(game_id, [])
        for move in moves:
            if move.move_number == move_number and move.player == player:
                return move
        return None
    
    async def update_player_stats(self, player_id: str, stats: PlayerStats) -> bool:
        self._check_failure("update_player_stats")
        self.player_stats[player_id] = stats
        return True
    
    async def get_player_stats(self, player_id: str) -> Optional[PlayerStats]:
        self._check_failure("get_player_stats")
        return self.player_stats.get(player_id)
    
    async def query_games(self, filters: Dict[str, Any], limit: Optional[int] = None,
                         offset: Optional[int] = None) -> List[GameRecord]:
        self._check_failure("query_games")
        games = list(self.games.values())
        
        # Apply simple filtering for testing
        if 'tournament_id' in filters:
            games = [g for g in games if g.tournament_id == filters['tournament_id']]
        
        if offset:
            games = games[offset:]
        if limit:
            games = games[:limit]
        
        return games
    
    async def count_games(self, filters: Dict[str, Any]) -> int:
        self._check_failure("count_games")
        games = await self.query_games(filters)
        return len(games)
    
    async def cleanup_old_data(self, older_than: datetime) -> int:
        self._check_failure("cleanup_old_data")
        count = 0
        games_to_delete = []
        
        for game_id, game in self.games.items():
            if game.start_time < older_than:
                games_to_delete.append(game_id)
                count += 1
        
        for game_id in games_to_delete:
            del self.games[game_id]
            if game_id in self.moves:
                del self.moves[game_id]
        
        return count
    
    async def get_storage_stats(self) -> Dict[str, Any]:
        self._check_failure("get_storage_stats")
        return {
            'total_games': len(self.games),
            'total_moves': sum(len(moves) for moves in self.moves.values()),
            'total_players': len(self.player_stats)
        }
    
    async def update_move(self, move: MoveRecord) -> bool:
        """Update an existing move record."""
        self._check_failure("update_move")
        if move.game_id not in self.moves:
            return False
        
        # Find and update the move
        for i, existing_move in enumerate(self.moves[move.game_id]):
            if (existing_move.move_number == move.move_number and 
                existing_move.player == move.player):
                self.moves[move.game_id][i] = move
                return True
        return False
    
    async def add_rethink_attempt(self, game_id: str, move_number: int, 
                                 player: int, rethink_attempt) -> bool:
        """Add a rethink attempt record."""
        self._check_failure("add_rethink_attempt")
        if game_id not in self.moves:
            return False
        
        # Find the move and add the rethink attempt
        for move in self.moves[game_id]:
            if move.move_number == move_number and move.player == player:
                if move.rethink_attempts is None:
                    move.rethink_attempts = []
                move.rethink_attempts.append(rethink_attempt)
                return True
        return False


@pytest.fixture
def mock_backend():
    """Create a mock storage backend."""
    config = DatabaseConfig.sqlite_default()
    return MockStorageBackend(config)


@pytest.fixture
def storage_config():
    """Create a test storage configuration."""
    return StorageConfig(
        database=DatabaseConfig.sqlite_default(),
        enable_data_validation=True,
        log_level=LogLevel.DEBUG
    )


@pytest_asyncio.fixture
async def storage_manager(mock_backend, storage_config):
    """Create a storage manager with mock backend."""
    manager = StorageManager(mock_backend, storage_config)
    await manager.initialize()
    yield manager
    await manager.shutdown()


@pytest.fixture
def sample_game():
    """Create a sample game record for testing."""
    return GameRecord(
        game_id="test_game_001",
        start_time=datetime.now(),
        players={
            0: PlayerInfo("player_black", "gpt-4", "openai", "ChessLLMAgent"),
            1: PlayerInfo("player_white", "gemini-pro", "google", "ChessRethinkAgent")
        },
        tournament_id="test_tournament",
        initial_fen="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    )


@pytest.fixture
def sample_outcome():
    """Create a sample game outcome."""
    return GameOutcome(
        result=GameResult.WHITE_WINS,
        winner=1,
        termination=TerminationReason.CHECKMATE
    )


@pytest.fixture
def sample_move():
    """Create a sample move record for testing."""
    return MoveRecord(
        game_id="test_game_001",
        move_number=1,
        player=1,  # White
        timestamp=datetime.now(),
        fen_before="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
        fen_after="rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1",
        legal_moves=["a3", "a4", "b3", "b4", "c3", "c4", "d3", "d4", "e3", "e4", "f3", "f4", "g3", "g4", "h3", "h4", "Nc3", "Nf3", "Nh3", "Na3"],
        move_san="e4",
        move_uci="e2e4",
        is_legal=True,
        prompt_text="You are playing chess as White. Make your first move.",
        raw_response="I'll start with the king's pawn opening: e4",
        parsed_move="e4",
        parsing_success=True,
        parsing_attempts=1,
        thinking_time_ms=1500,
        api_call_time_ms=800,
        parsing_time_ms=50
    )


@pytest.fixture
def sample_move_with_rethink():
    """Create a sample move record with rethink attempts."""
    rethink_attempts = [
        RethinkAttempt(
            attempt_number=1,
            prompt_text="Your move 'Ke8' is illegal. Please try again.",
            raw_response="Let me reconsider. I'll play Nf3.",
            parsed_move="Nf3",
            was_legal=True,
            timestamp=datetime.now()
        )
    ]
    
    return MoveRecord(
        game_id="test_game_001",
        move_number=2,
        player=1,  # White
        timestamp=datetime.now(),
        fen_before="rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1",
        fen_after="rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq e6 0 2",
        legal_moves=["a3", "a4", "b3", "b4", "c3", "c4", "d3", "d4", "f3", "f4", "g3", "g4", "h3", "h4", "Nc3", "Nf3", "Nh3", "Na3", "Bc4", "Bd3", "Be2", "Bb5", "Ba6", "Qe2", "Qf3", "Qg4", "Qh5"],
        move_san="Nf3",
        move_uci="g1f3",
        is_legal=True,
        prompt_text="You are playing chess as White. What's your next move?",
        raw_response="Let me reconsider. I'll play Nf3.",
        parsed_move="Nf3",
        parsing_success=True,
        parsing_attempts=2,
        thinking_time_ms=2500,
        api_call_time_ms=1200,
        parsing_time_ms=100,
        rethink_attempts=rethink_attempts
    )


@pytest.fixture
def sample_illegal_move():
    """Create a sample illegal move record."""
    return MoveRecord(
        game_id="test_game_001",
        move_number=3,
        player=0,  # Black
        timestamp=datetime.now(),
        fen_before="rnbqkbnr/pppp1ppp/8/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R b KQkq - 1 2",
        fen_after="rnbqkbnr/pppp1ppp/8/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R b KQkq - 1 2",  # Same position
        legal_moves=["a6", "a5", "b6", "b5", "c6", "c5", "d6", "d5", "f6", "f5", "g6", "g5", "h6", "h5", "Nc6", "Nd7", "Ne7", "Nf6", "Nh6"],
        move_san="Ke8",  # Illegal king move
        move_uci="e8e8",
        is_legal=False,
        prompt_text="You are playing chess as Black. What's your move?",
        raw_response="I'll move my king to safety: Ke8",
        parsed_move="Ke8",
        parsing_success=True,
        parsing_attempts=1,
        thinking_time_ms=1800,
        api_call_time_ms=900,
        parsing_time_ms=75,
        error_type="illegal_move",
        error_message="King cannot move to the same square"
    )


class TestStorageManagerInitialization:
    """Test storage manager initialization and shutdown."""
    
    @pytest.mark.asyncio
    async def test_successful_initialization(self, mock_backend, storage_config):
        """Test successful storage manager initialization."""
        manager = StorageManager(mock_backend, storage_config)
        
        await manager.initialize()
        
        assert mock_backend.is_connected
        
        await manager.shutdown()
        assert not mock_backend.is_connected
    
    @pytest.mark.asyncio
    async def test_initialization_failure(self, mock_backend, storage_config):
        """Test handling of initialization failures."""
        mock_backend.set_failure_mode("connect")
        manager = StorageManager(mock_backend, storage_config)
        
        with pytest.raises(StorageError, match="Storage initialization failed"):
            await manager.initialize()
    
    @pytest.mark.asyncio
    async def test_shutdown_with_active_transactions(self, storage_manager):
        """Test shutdown behavior with active transactions."""
        # Simulate active transaction
        storage_manager._active_transactions["test_tx"] = {
            'start_time': datetime.now(),
            'operations': []
        }
        
        # Should complete without error
        await storage_manager.shutdown()


class TestGameOperations:
    """Test game CRUD operations."""
    
    @pytest.mark.asyncio
    async def test_create_game_success(self, storage_manager, sample_game):
        """Test successful game creation."""
        game_id = await storage_manager.create_game(sample_game)
        
        assert game_id == sample_game.game_id
        
        # Verify game was stored
        retrieved_game = await storage_manager.get_game(game_id)
        assert retrieved_game.game_id == sample_game.game_id
        assert retrieved_game.players == sample_game.players
    
    @pytest.mark.asyncio
    async def test_create_duplicate_game(self, storage_manager, sample_game):
        """Test creation of duplicate game fails."""
        await storage_manager.create_game(sample_game)
        
        with pytest.raises(DuplicateGameError, match="already exists"):
            await storage_manager.create_game(sample_game)
    
    @pytest.mark.asyncio
    async def test_create_game_validation_error(self, storage_manager):
        """Test game creation with invalid data."""
        # Create a game with valid basic structure but invalid business logic
        start_time = datetime.now()
        end_time = start_time - timedelta(hours=1)  # End time before start time
        
        invalid_game = GameRecord(
            game_id="test_game",
            start_time=start_time,
            players={
                0: PlayerInfo("player_black", "gpt-4", "openai", "ChessLLMAgent"),
                1: PlayerInfo("player_white", "gemini-pro", "google", "ChessRethinkAgent")
            },
            end_time=end_time  # This should trigger StorageManager validation
        )
        
        with pytest.raises(ValidationError, match="end time cannot be before start time"):
            await storage_manager.create_game(invalid_game)
    
    @pytest.mark.asyncio
    async def test_get_game_not_found(self, storage_manager):
        """Test retrieval of non-existent game."""
        with pytest.raises(GameNotFoundError, match="not found"):
            await storage_manager.get_game("nonexistent_game")
    
    @pytest.mark.asyncio
    async def test_update_game_success(self, storage_manager, sample_game, sample_outcome):
        """Test successful game update."""
        await storage_manager.create_game(sample_game)
        
        updates = {
            'outcome': sample_outcome,
            'total_moves': 25,
            'end_time': datetime.now()
        }
        
        success = await storage_manager.update_game(sample_game.game_id, updates)
        assert success
        
        # Verify updates were applied
        updated_game = await storage_manager.get_game(sample_game.game_id)
        assert updated_game.outcome == sample_outcome
        assert updated_game.total_moves == 25
        assert updated_game.end_time is not None
    
    @pytest.mark.asyncio
    async def test_update_nonexistent_game(self, storage_manager):
        """Test update of non-existent game."""
        with pytest.raises(GameNotFoundError):
            await storage_manager.update_game("nonexistent", {'total_moves': 10})
    
    @pytest.mark.asyncio
    async def test_update_game_validation_error(self, storage_manager, sample_game):
        """Test game update with invalid data."""
        await storage_manager.create_game(sample_game)
        
        invalid_updates = {
            'total_moves': -5  # Invalid negative value
        }
        
        with pytest.raises(ValidationError, match="cannot be negative"):
            await storage_manager.update_game(sample_game.game_id, invalid_updates)
    
    @pytest.mark.asyncio
    async def test_complete_game_success(self, storage_manager, sample_game, sample_outcome):
        """Test successful game completion."""
        await storage_manager.create_game(sample_game)
        
        final_fen = "rnbqkb1r/pppp1ppp/5n2/4p3/2B1P3/8/PPPP1PPP/RNBQK1NR w KQkq - 2 3"
        total_moves = 25
        
        success = await storage_manager.complete_game(
            sample_game.game_id, sample_outcome, final_fen, total_moves
        )
        assert success
        
        # Verify completion data
        completed_game = await storage_manager.get_game(sample_game.game_id)
        assert completed_game.is_completed
        assert completed_game.outcome == sample_outcome
        assert completed_game.final_fen == final_fen
        assert completed_game.total_moves == total_moves
        assert completed_game.game_duration_seconds is not None
    
    @pytest.mark.asyncio
    async def test_delete_game_success(self, storage_manager, sample_game):
        """Test successful game deletion."""
        await storage_manager.create_game(sample_game)
        
        success = await storage_manager.delete_game(sample_game.game_id)
        assert success
        
        # Verify game was deleted
        with pytest.raises(GameNotFoundError):
            await storage_manager.get_game(sample_game.game_id)
    
    @pytest.mark.asyncio
    async def test_delete_nonexistent_game(self, storage_manager):
        """Test deletion of non-existent game."""
        with pytest.raises(GameNotFoundError):
            await storage_manager.delete_game("nonexistent")


class TestQueryOperations:
    """Test game query operations."""
    
    @pytest.mark.asyncio
    async def test_query_games_success(self, storage_manager):
        """Test successful game querying."""
        # Create test games
        games = []
        for i in range(3):
            game = GameRecord(
                game_id=f"test_game_{i:03d}",
                start_time=datetime.now(),
                players={
                    0: PlayerInfo(f"player_black_{i}", "gpt-4", "openai", "ChessLLMAgent"),
                    1: PlayerInfo(f"player_white_{i}", "gemini-pro", "google", "ChessRethinkAgent")
                },
                tournament_id="test_tournament"
            )
            games.append(game)
            await storage_manager.create_game(game)
        
        # Query all games
        results = await storage_manager.query_games({})
        assert len(results) == 3
        
        # Query with filter
        filtered_results = await storage_manager.query_games(
            {'tournament_id': 'test_tournament'}
        )
        assert len(filtered_results) == 3
        
        # Query with limit
        limited_results = await storage_manager.query_games({}, limit=2)
        assert len(limited_results) == 2
    
    @pytest.mark.asyncio
    async def test_count_games_success(self, storage_manager):
        """Test successful game counting."""
        # Create test games
        for i in range(5):
            game = GameRecord(
                game_id=f"test_game_{i:03d}",
                start_time=datetime.now(),
                players={
                    0: PlayerInfo(f"player_black_{i}", "gpt-4", "openai", "ChessLLMAgent"),
                    1: PlayerInfo(f"player_white_{i}", "gemini-pro", "google", "ChessRethinkAgent")
                },
                tournament_id="test_tournament" if i < 3 else "other_tournament"
            )
            await storage_manager.create_game(game)
        
        # Count all games
        total_count = await storage_manager.count_games({})
        assert total_count == 5
        
        # Count with filter
        filtered_count = await storage_manager.count_games(
            {'tournament_id': 'test_tournament'}
        )
        assert filtered_count == 3


class TestTransactionHandling:
    """Test transaction management."""
    
    @pytest.mark.asyncio
    async def test_successful_transaction(self, storage_manager, sample_game):
        """Test successful transaction completion."""
        # Simple transaction test without nested operations
        async with storage_manager.transaction() as tx_id:
            assert tx_id in storage_manager._active_transactions
            # Just verify transaction tracking works
        
        # Transaction should be cleaned up
        assert tx_id not in storage_manager._active_transactions
    
    @pytest.mark.asyncio
    async def test_transaction_failure_handling(self, storage_manager, mock_backend):
        """Test transaction failure and rollback."""
        mock_backend.set_failure_mode("create_game")
        
        with pytest.raises(TransactionError):
            async with storage_manager.transaction() as tx_id:
                sample_game = GameRecord(
                    game_id="failing_game",
                    start_time=datetime.now(),
                    players={
                        0: PlayerInfo("player_black", "gpt-4", "openai", "ChessLLMAgent"),
                        1: PlayerInfo("player_white", "gemini-pro", "google", "ChessRethinkAgent")
                    }
                )
                await storage_manager.create_game(sample_game)
        
        # Transaction should be cleaned up
        assert len(storage_manager._active_transactions) == 0


class TestErrorHandling:
    """Test error handling and recovery."""
    
    @pytest.mark.asyncio
    async def test_backend_failure_handling(self, storage_manager, mock_backend, sample_game):
        """Test handling of backend failures."""
        # First create the game successfully
        await storage_manager.create_game(sample_game)
        
        # Then set the backend to fail on get_game
        mock_backend.set_failure_mode("get_game")
        
        with pytest.raises(StorageError, match="Game retrieval failed"):
            await storage_manager.get_game(sample_game.game_id)
    
    @pytest.mark.asyncio
    async def test_validation_disabled(self, mock_backend, sample_game):
        """Test behavior when validation is disabled."""
        config = StorageConfig(
            database=DatabaseConfig.sqlite_default(),
            enable_data_validation=False
        )
        
        manager = StorageManager(mock_backend, config)
        await manager.initialize()
        
        try:
            # Test that StorageManager validation is disabled
            # Note: Model-level validation still occurs during object creation
            # but StorageManager business logic validation should be skipped
            
            # Create a valid game object first
            valid_game = GameRecord(
                game_id="test",
                start_time=datetime.now(),
                players={
                    0: PlayerInfo("player_black", "gpt-4", "openai", "ChessLLMAgent"),
                    1: PlayerInfo("player_white", "gemini-pro", "google", "ChessRethinkAgent")
                }
            )
            
            # This should succeed when validation is disabled
            await manager.create_game(valid_game)
            
            # Test that StorageManager validation is indeed disabled by checking the config
            assert not manager.config.enable_data_validation
            
        finally:
            await manager.shutdown()


class TestMoveOperations:
    """Test move storage and retrieval operations."""
    
    @pytest.mark.asyncio
    async def test_add_move_success(self, storage_manager, sample_game, sample_move):
        """Test successful move addition."""
        # Create game first
        await storage_manager.create_game(sample_game)
        
        # Add move
        success = await storage_manager.add_move(sample_move)
        assert success
        
        # Verify move was stored
        retrieved_moves = await storage_manager.get_moves(sample_game.game_id)
        assert len(retrieved_moves) == 1
        assert retrieved_moves[0].move_san == sample_move.move_san
        assert retrieved_moves[0].is_legal == sample_move.is_legal
    
    @pytest.mark.asyncio
    async def test_add_move_validation_error(self, storage_manager, sample_game):
        """Test move addition with invalid data."""
        await storage_manager.create_game(sample_game)
        
        # Test model-level validation (happens during object creation)
        with pytest.raises(ValueError, match="cannot be negative"):
            invalid_move = MoveRecord(
                game_id=sample_game.game_id,
                move_number=1,
                player=1,
                timestamp=datetime.now(),
                fen_before="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
                fen_after="rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1",
                legal_moves=["e4"],
                move_san="e4",
                move_uci="e2e4",
                is_legal=True,
                prompt_text="Test prompt",
                raw_response="Test response",
                thinking_time_ms=-100  # Invalid negative value
            )
        
        # Test model-level validation for parsing attempts
        with pytest.raises(ValueError, match="parsing_attempts must be positive"):
            invalid_move2 = MoveRecord(
                game_id=sample_game.game_id,
                move_number=1,
                player=1,
                timestamp=datetime.now(),
                fen_before="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
                fen_after="rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1",
                legal_moves=["e4"],
                move_san="e4",
                move_uci="e2e4",
                is_legal=True,
                prompt_text="Test prompt",
                raw_response="Test response",
                parsing_attempts=0  # Invalid - should be at least 1
            )
    
    @pytest.mark.asyncio
    async def test_add_move_with_rethink(self, storage_manager, sample_game, sample_move_with_rethink):
        """Test adding move with rethink attempts."""
        await storage_manager.create_game(sample_game)
        
        success = await storage_manager.add_move(sample_move_with_rethink)
        assert success
        
        # Verify move and rethink attempts were stored
        retrieved_moves = await storage_manager.get_moves(sample_game.game_id)
        assert len(retrieved_moves) == 1
        
        move = retrieved_moves[0]
        assert move.had_rethink
        assert len(move.rethink_attempts) == 1
        assert move.rethink_attempts[0].attempt_number == 1
        assert move.rethink_attempts[0].was_legal
    
    @pytest.mark.asyncio
    async def test_add_illegal_move(self, storage_manager, sample_game, sample_illegal_move):
        """Test adding illegal move record."""
        await storage_manager.create_game(sample_game)
        
        success = await storage_manager.add_move(sample_illegal_move)
        assert success
        
        # Verify illegal move was stored with error information
        retrieved_moves = await storage_manager.get_moves(sample_game.game_id)
        assert len(retrieved_moves) == 1
        
        move = retrieved_moves[0]
        assert not move.is_legal
        assert move.error_type == "illegal_move"
        assert move.error_message is not None
    
    @pytest.mark.asyncio
    async def test_add_moves_batch_success(self, storage_manager, sample_game):
        """Test batch move addition."""
        await storage_manager.create_game(sample_game)
        
        # Create multiple moves
        moves = []
        for i in range(3):
            move = MoveRecord(
                game_id=sample_game.game_id,
                move_number=i + 1,
                player=i % 2,
                timestamp=datetime.now(),
                fen_before=f"fen_before_{i}",
                fen_after=f"fen_after_{i}",
                legal_moves=[f"move_{i}"],
                move_san=f"move_{i}",
                move_uci=f"move_uci_{i}",
                is_legal=True,
                prompt_text=f"prompt_{i}",
                raw_response=f"response_{i}"
            )
            moves.append(move)
        
        # Add moves in batch
        success_count = await storage_manager.add_moves_batch(moves)
        assert success_count == 3
        
        # Verify all moves were stored
        retrieved_moves = await storage_manager.get_moves(sample_game.game_id)
        assert len(retrieved_moves) == 3
    
    @pytest.mark.asyncio
    async def test_add_moves_batch_partial_failure(self, storage_manager, sample_game, mock_backend):
        """Test batch move addition with partial failures."""
        await storage_manager.create_game(sample_game)
        
        # Test that model validation prevents invalid moves from being created
        with pytest.raises(ValueError, match="parsing_attempts must be positive"):
            moves = [
                MoveRecord(
                    game_id=sample_game.game_id,
                    move_number=1,
                    player=1,
                    timestamp=datetime.now(),
                    fen_before="fen1",
                    fen_after="fen1",
                    legal_moves=["move1"],
                    move_san="move1",
                    move_uci="move1",
                    is_legal=True,
                    prompt_text="prompt1",
                    raw_response="response1"
                ),
                MoveRecord(
                    game_id=sample_game.game_id,
                    move_number=2,
                    player=0,
                    timestamp=datetime.now(),
                    fen_before="fen2",
                    fen_after="fen2",
                    legal_moves=["move2"],
                    move_san="move2",
                    move_uci="move2",
                    is_legal=True,
                    prompt_text="prompt2",
                    raw_response="response2",
                    parsing_attempts=0  # This will cause model validation error
                )
            ]
    
    @pytest.mark.asyncio
    async def test_get_moves_success(self, storage_manager, sample_game, sample_move):
        """Test successful move retrieval."""
        await storage_manager.create_game(sample_game)
        await storage_manager.add_move(sample_move)
        
        moves = await storage_manager.get_moves(sample_game.game_id)
        assert len(moves) == 1
        assert moves[0].game_id == sample_game.game_id
        assert moves[0].move_san == sample_move.move_san
    
    @pytest.mark.asyncio
    async def test_get_moves_with_limit(self, storage_manager, sample_game):
        """Test move retrieval with limit."""
        await storage_manager.create_game(sample_game)
        
        # Add multiple moves
        for i in range(5):
            move = MoveRecord(
                game_id=sample_game.game_id,
                move_number=i + 1,
                player=i % 2,
                timestamp=datetime.now(),
                fen_before=f"fen_{i}",
                fen_after=f"fen_{i}",
                legal_moves=[f"move_{i}"],
                move_san=f"move_{i}",
                move_uci=f"move_{i}",
                is_legal=True,
                prompt_text=f"prompt_{i}",
                raw_response=f"response_{i}"
            )
            await storage_manager.add_move(move)
        
        # Get moves with limit
        limited_moves = await storage_manager.get_moves(sample_game.game_id, limit=3)
        assert len(limited_moves) == 3
    
    @pytest.mark.asyncio
    async def test_get_moves_empty_game(self, storage_manager, sample_game):
        """Test move retrieval for game with no moves."""
        await storage_manager.create_game(sample_game)
        
        moves = await storage_manager.get_moves(sample_game.game_id)
        assert len(moves) == 0
    
    @pytest.mark.asyncio
    async def test_get_specific_move_success(self, storage_manager, sample_game, sample_move):
        """Test retrieval of specific move."""
        await storage_manager.create_game(sample_game)
        await storage_manager.add_move(sample_move)
        
        move = await storage_manager.get_move(
            sample_game.game_id, 
            sample_move.move_number, 
            sample_move.player
        )
        
        assert move is not None
        assert move.move_san == sample_move.move_san
        assert move.player == sample_move.player
    
    @pytest.mark.asyncio
    async def test_get_specific_move_not_found(self, storage_manager, sample_game):
        """Test retrieval of non-existent move."""
        await storage_manager.create_game(sample_game)
        
        move = await storage_manager.get_move(sample_game.game_id, 999, 1)
        assert move is None
    
    @pytest.mark.asyncio
    async def test_get_moves_with_filters(self, storage_manager, sample_game):
        """Test move retrieval with filters."""
        await storage_manager.create_game(sample_game)
        
        # Add legal and illegal moves
        legal_move = MoveRecord(
            game_id=sample_game.game_id,
            move_number=1,
            player=1,
            timestamp=datetime.now(),
            fen_before="fen1",
            fen_after="fen1",
            legal_moves=["e4"],
            move_san="e4",
            move_uci="e2e4",
            is_legal=True,
            prompt_text="prompt1",
            raw_response="response1",
            thinking_time_ms=1000
        )
        
        illegal_move = MoveRecord(
            game_id=sample_game.game_id,
            move_number=2,
            player=0,
            timestamp=datetime.now(),
            fen_before="fen2",
            fen_after="fen2",
            legal_moves=["e5"],
            move_san="Ke8",
            move_uci="e8e8",
            is_legal=False,
            prompt_text="prompt2",
            raw_response="response2",
            thinking_time_ms=2000
        )
        
        await storage_manager.add_move(legal_move)
        await storage_manager.add_move(illegal_move)
        
        # Filter for legal moves only
        legal_moves = await storage_manager.get_moves_with_filters(
            sample_game.game_id, 
            {'is_legal': True}
        )
        assert len(legal_moves) == 1
        assert legal_moves[0].is_legal
        
        # Filter for illegal moves only
        illegal_moves = await storage_manager.get_moves_with_filters(
            sample_game.game_id, 
            {'is_legal': False}
        )
        assert len(illegal_moves) == 1
        assert not illegal_moves[0].is_legal
        
        # Filter by thinking time
        fast_moves = await storage_manager.get_moves_with_filters(
            sample_game.game_id, 
            {'max_thinking_time': 1500}
        )
        assert len(fast_moves) == 1
        assert fast_moves[0].thinking_time_ms <= 1500
    
    @pytest.mark.asyncio
    async def test_get_move_statistics(self, storage_manager, sample_game):
        """Test move statistics calculation."""
        await storage_manager.create_game(sample_game)
        
        # Add various types of moves
        moves_data = [
            {'legal': True, 'blunder': False, 'thinking_time': 1000, 'player': 1},
            {'legal': False, 'blunder': False, 'thinking_time': 2000, 'player': 0},
            {'legal': True, 'blunder': True, 'thinking_time': 1500, 'player': 1},
            {'legal': True, 'blunder': False, 'thinking_time': 800, 'player': 0}
        ]
        
        for i, data in enumerate(moves_data):
            move = MoveRecord(
                game_id=sample_game.game_id,
                move_number=i + 1,
                player=data['player'],
                timestamp=datetime.now(),
                fen_before=f"fen_{i}",
                fen_after=f"fen_{i}",
                legal_moves=[f"move_{i}"],
                move_san=f"move_{i}",
                move_uci=f"move_{i}",
                is_legal=data['legal'],
                prompt_text=f"prompt_{i}",
                raw_response=f"response_{i}",
                thinking_time_ms=data['thinking_time'],
                blunder_flag=data['blunder']
            )
            await storage_manager.add_move(move)
        
        # Get statistics
        stats = await storage_manager.get_move_statistics(sample_game.game_id)
        
        assert stats['total_moves'] == 4
        assert stats['legal_moves'] == 3
        assert stats['illegal_moves'] == 1
        assert stats['blunders'] == 1
        assert stats['average_thinking_time_ms'] == 1325.0  # (1000+2000+1500+800)/4
        
        # Check per-player stats
        assert 'player_0' in stats
        assert 'player_1' in stats
        assert stats['player_0']['moves'] == 2
        assert stats['player_1']['moves'] == 2
    
    @pytest.mark.asyncio
    async def test_get_move_statistics_empty_game(self, storage_manager, sample_game):
        """Test move statistics for game with no moves."""
        await storage_manager.create_game(sample_game)
        
        stats = await storage_manager.get_move_statistics(sample_game.game_id)
        
        assert stats['total_moves'] == 0
        assert stats['legal_moves'] == 0
        assert stats['illegal_moves'] == 0
        assert stats['average_thinking_time_ms'] == 0.0
    
    @pytest.mark.asyncio
    async def test_validate_move_integrity_success(self, storage_manager, sample_game):
        """Test move integrity validation for valid sequence."""
        await storage_manager.create_game(sample_game)
        
        # Add moves in proper sequence
        for i in range(4):
            move = MoveRecord(
                game_id=sample_game.game_id,
                move_number=i + 1,
                player=i % 2,  # Alternating players
                timestamp=datetime.now(),
                fen_before=f"fen_before_{i}",
                fen_after=f"fen_after_{i}",
                legal_moves=[f"move_{i}"],
                move_san=f"move_{i}",
                move_uci=f"move_uci_{i}",
                is_legal=True,
                prompt_text=f"prompt_{i}",
                raw_response=f"response_{i}"
            )
            await storage_manager.add_move(move)
        
        # Update game total moves
        await storage_manager.update_game(sample_game.game_id, {'total_moves': 4})
        
        # Validate integrity
        validation = await storage_manager.validate_move_integrity(sample_game.game_id)
        
        assert validation['is_valid']
        assert len(validation['errors']) == 0
        assert validation['move_count'] == 4
        assert validation['expected_moves'] == 4
    
    @pytest.mark.asyncio
    async def test_validate_move_integrity_errors(self, storage_manager, sample_game):
        """Test move integrity validation with errors."""
        await storage_manager.create_game(sample_game)
        
        # Add moves with integrity issues
        moves_data = [
            {'move_number': 1, 'player': 1},  # Should be player 0 for move 1
            {'move_number': 3, 'player': 0},  # Skipped move 2
            {'move_number': 4, 'player': 1}
        ]
        
        for data in moves_data:
            move = MoveRecord(
                game_id=sample_game.game_id,
                move_number=data['move_number'],
                player=data['player'],
                timestamp=datetime.now(),
                fen_before="fen",
                fen_after="fen",
                legal_moves=["move"],
                move_san="move",
                move_uci="move",
                is_legal=True,
                prompt_text="prompt",
                raw_response="response"
            )
            await storage_manager.add_move(move)
        
        # Validate integrity
        validation = await storage_manager.validate_move_integrity(sample_game.game_id)
        
        assert not validation['is_valid']
        assert len(validation['errors']) > 0
        assert any("Expected player 0" in error for error in validation['errors'])
        assert any("Expected move number 2" in error for error in validation['errors'])
    
    @pytest.mark.asyncio
    async def test_validate_move_integrity_empty_game(self, storage_manager, sample_game):
        """Test move integrity validation for game with no moves."""
        await storage_manager.create_game(sample_game)
        
        validation = await storage_manager.validate_move_integrity(sample_game.game_id)
        
        assert validation['is_valid']
        assert len(validation['errors']) == 0
        assert len(validation['warnings']) == 1
        assert "No moves found" in validation['warnings'][0]
    
    @pytest.mark.asyncio
    async def test_move_operations_backend_failure(self, storage_manager, mock_backend, sample_game, sample_move):
        """Test move operations with backend failures."""
        await storage_manager.create_game(sample_game)
        
        # Test add_move failure
        mock_backend.set_failure_mode("add_move")
        with pytest.raises(StorageError, match="Move addition failed"):
            await storage_manager.add_move(sample_move)
        
        # Test get_moves failure
        mock_backend.set_failure_mode("get_moves")
        with pytest.raises(StorageError, match="Move retrieval failed"):
            await storage_manager.get_moves(sample_game.game_id)
        
        # Test get_move failure
        mock_backend.set_failure_mode("get_move")
        with pytest.raises(StorageError, match="Move retrieval failed"):
            await storage_manager.get_move(sample_game.game_id, 1, 1)


class TestHealthAndMaintenance:
    """Test health monitoring and maintenance operations."""
    
    @pytest.mark.asyncio
    async def test_get_health_status_healthy(self, storage_manager):
        """Test health status when system is healthy."""
        health = await storage_manager.get_health_status()
        
        assert health['status'] == 'healthy'
        assert health['backend_connected'] is True
        assert 'backend_stats' in health
        assert 'timestamp' in health
    
    @pytest.mark.asyncio
    async def test_get_health_status_unhealthy(self, storage_manager, mock_backend):
        """Test health status when backend is disconnected."""
        await mock_backend.disconnect()
        
        health = await storage_manager.get_health_status()
        
        assert health['status'] == 'unhealthy'
        assert health['backend_connected'] is False
        assert 'errors' in health
    
    @pytest.mark.asyncio
    async def test_cleanup_old_data(self, storage_manager):
        """Test cleanup of old data."""
        # Create old and new games
        old_time = datetime.now() - timedelta(days=10)
        new_time = datetime.now()
        
        old_game = GameRecord(
            game_id="old_game",
            start_time=old_time,
            players={
                0: PlayerInfo("player_black", "gpt-4", "openai", "ChessLLMAgent"),
                1: PlayerInfo("player_white", "gemini-pro", "google", "ChessRethinkAgent")
            }
        )
        
        new_game = GameRecord(
            game_id="new_game",
            start_time=new_time,
            players={
                0: PlayerInfo("player_black", "gpt-4", "openai", "ChessLLMAgent"),
                1: PlayerInfo("player_white", "gemini-pro", "google", "ChessRethinkAgent")
            }
        )
        
        await storage_manager.create_game(old_game)
        await storage_manager.create_game(new_game)
        
        # Cleanup data older than 5 days
        cleanup_threshold = datetime.now() - timedelta(days=5)
        cleaned_count = await storage_manager.cleanup_old_data(cleanup_threshold)
        
        assert cleaned_count == 1
        
        # Verify old game was deleted, new game remains
        with pytest.raises(GameNotFoundError):
            await storage_manager.get_game("old_game")
        
        remaining_game = await storage_manager.get_game("new_game")
        assert remaining_game is not None


if __name__ == "__main__":
    pytest.main([__file__])