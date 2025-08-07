"""
Unit tests for storage backend implementations.

This module contains comprehensive tests for the StorageBackend interface
and its implementations, focusing on CRUD operations and data integrity.
"""

import pytest
import pytest_asyncio
import asyncio
import tempfile
import os
from datetime import datetime, timedelta
from pathlib import Path

from game_arena.storage.backends.base import StorageBackend
from game_arena.storage.backends.sqlite_backend import SQLiteBackend
from game_arena.storage.config import DatabaseConfig, StorageBackendType
from game_arena.storage.models import (
    GameRecord, PlayerInfo, GameOutcome, MoveRecord, RethinkAttempt,
    PlayerStats, GameResult, TerminationReason
)

# Try to import PostgreSQL backend
try:
    from game_arena.storage.backends.postgresql_backend import PostgreSQLBackend
    POSTGRESQL_AVAILABLE = True
except ImportError:
    PostgreSQLBackend = None
    POSTGRESQL_AVAILABLE = False


@pytest_asyncio.fixture
async def sqlite_backend():
    """Create a temporary SQLite backend for testing."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_file:
        db_path = tmp_file.name
    
    config = DatabaseConfig(
        backend_type=StorageBackendType.SQLITE,
        database=db_path,
        connection_timeout=5
    )
    
    backend = SQLiteBackend(config)
    await backend.connect()
    await backend.initialize_schema()
    
    yield backend
    
    await backend.disconnect()
    # Clean up temporary file
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest_asyncio.fixture
async def postgresql_backend():
    """Create a PostgreSQL backend for testing (requires running PostgreSQL)."""
    if not POSTGRESQL_AVAILABLE:
        pytest.skip("PostgreSQL backend not available")
    
    # Use environment variables or default test database
    config = DatabaseConfig(
        backend_type=StorageBackendType.POSTGRESQL,
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        database=os.getenv("POSTGRES_DB", "game_arena_test"),
        username=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD", ""),
        connection_pool_size=5,
        connection_timeout=10
    )
    
    backend = PostgreSQLBackend(config)
    
    try:
        await backend.connect()
        await backend.initialize_schema()
        
        # Clean up any existing test data
        await backend.cleanup_old_data(datetime.now() + timedelta(days=1))
        
        yield backend
        
    except Exception as e:
        pytest.skip(f"Could not connect to PostgreSQL: {e}")
    finally:
        if backend.is_connected:
            # Clean up test data
            try:
                await backend.cleanup_old_data(datetime.now() + timedelta(days=1))
            except:
                pass
            await backend.disconnect()


@pytest.fixture
def sample_players():
    """Create sample player info for testing."""
    return {
        0: PlayerInfo(
            player_id="black_player",
            model_name="gpt-4",
            model_provider="openai",
            agent_type="ChessLLMAgent",
            agent_config={"temperature": 0.7},
            elo_rating=1500.0
        ),
        1: PlayerInfo(
            player_id="white_player",
            model_name="gemini-pro",
            model_provider="google",
            agent_type="ChessRethinkAgent",
            agent_config={"max_retries": 3},
            elo_rating=1600.0
        )
    }


@pytest.fixture
def sample_game(sample_players):
    """Create a sample game record for testing."""
    return GameRecord(
        game_id="test_game_001",
        tournament_id="test_tournament",
        start_time=datetime.now(),
        players=sample_players,
        initial_fen="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
        metadata={"test": True}
    )


@pytest.fixture
def sample_move():
    """Create a sample move record for testing."""
    return MoveRecord(
        game_id="test_game_001",
        move_number=1,
        player=1,
        timestamp=datetime.now(),
        fen_before="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
        fen_after="rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1",
        legal_moves=["e4", "d4", "Nf3", "Nc3"],
        move_san="e4",
        move_uci="e2e4",
        is_legal=True,
        prompt_text="Make your opening move",
        raw_response="I'll play e4 to control the center",
        parsed_move="e4",
        thinking_time_ms=1500,
        api_call_time_ms=800,
        parsing_time_ms=50,
        rethink_attempts=[
            RethinkAttempt(
                attempt_number=1,
                prompt_text="Reconsider your move",
                raw_response="Actually, e4 is good",
                parsed_move="e4",
                was_legal=True,
                timestamp=datetime.now()
            )
        ]
    )


class TestStorageBackendInterface:
    """Test the StorageBackend abstract interface."""
    
    def test_backend_interface_methods(self):
        """Test that StorageBackend defines all required abstract methods."""
        abstract_methods = StorageBackend.__abstractmethods__
        
        expected_methods = {
            'connect', 'disconnect', 'initialize_schema',
            'create_game', 'get_game', 'update_game', 'delete_game',
            'add_move', 'get_moves', 'get_move', 'update_move', 'add_rethink_attempt',
            'update_player_stats', 'get_player_stats',
            'query_games', 'count_games',
            'cleanup_old_data', 'get_storage_stats'
        }
        
        assert abstract_methods == expected_methods


class TestSQLiteBackend:
    """Test SQLite backend implementation."""
    
    @pytest.mark.asyncio
    async def test_connection_lifecycle(self):
        """Test backend connection and disconnection."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_file:
            db_path = tmp_file.name
        
        config = DatabaseConfig(
            backend_type=StorageBackendType.SQLITE,
            database=db_path
        )
        
        backend = SQLiteBackend(config)
        
        # Initially not connected
        assert not backend.is_connected
        
        # Connect
        await backend.connect()
        assert backend.is_connected
        
        # Initialize schema
        await backend.initialize_schema()
        
        # Disconnect
        await backend.disconnect()
        assert not backend.is_connected
        
        # Clean up
        os.unlink(db_path)
    
    @pytest.mark.asyncio
    async def test_schema_initialization(self, sqlite_backend):
        """Test database schema creation."""
        # Schema should be initialized by fixture
        stats = await sqlite_backend.get_storage_stats()
        
        assert stats["backend_type"] == "sqlite"
        assert stats["game_count"] == 0
        assert stats["move_count"] == 0
        assert stats["player_count"] == 0
    
    @pytest.mark.asyncio
    async def test_game_crud_operations(self, sqlite_backend, sample_game):
        """Test game CRUD operations."""
        # Create game
        game_id = await sqlite_backend.create_game(sample_game)
        assert game_id == sample_game.game_id
        
        # Read game
        retrieved_game = await sqlite_backend.get_game(game_id)
        assert retrieved_game is not None
        assert retrieved_game.game_id == sample_game.game_id
        assert retrieved_game.tournament_id == sample_game.tournament_id
        assert len(retrieved_game.players) == 2
        assert retrieved_game.players[0].player_id == "black_player"
        assert retrieved_game.players[1].player_id == "white_player"
        
        # Update game
        outcome = GameOutcome(
            result=GameResult.WHITE_WINS,
            winner=1,
            termination=TerminationReason.CHECKMATE
        )
        
        updates = {
            "end_time": datetime.now(),
            "outcome": outcome,
            "total_moves": 25,
            "final_fen": "r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/3P1N2/PPP2PPP/RNBQK2R w KQkq - 4 4"
        }
        
        success = await sqlite_backend.update_game(game_id, updates)
        assert success
        
        # Verify update
        updated_game = await sqlite_backend.get_game(game_id)
        assert updated_game.outcome is not None
        assert updated_game.outcome.result == GameResult.WHITE_WINS
        assert updated_game.total_moves == 25
        
        # Delete game
        deleted = await sqlite_backend.delete_game(game_id)
        assert deleted
        
        # Verify deletion
        deleted_game = await sqlite_backend.get_game(game_id)
        assert deleted_game is None
    
    @pytest.mark.asyncio
    async def test_move_operations(self, sqlite_backend, sample_game, sample_move):
        """Test move storage and retrieval operations."""
        # First create the game
        await sqlite_backend.create_game(sample_game)
        
        # Add move
        success = await sqlite_backend.add_move(sample_move)
        assert success
        
        # Get moves for game
        moves = await sqlite_backend.get_moves(sample_game.game_id)
        assert len(moves) == 1
        
        retrieved_move = moves[0]
        assert retrieved_move.game_id == sample_move.game_id
        assert retrieved_move.move_number == sample_move.move_number
        assert retrieved_move.player == sample_move.player
        assert retrieved_move.move_san == sample_move.move_san
        assert retrieved_move.is_legal == sample_move.is_legal
        assert len(retrieved_move.rethink_attempts) == 1
        
        # Get specific move
        specific_move = await sqlite_backend.get_move(
            sample_game.game_id, 
            sample_move.move_number, 
            sample_move.player
        )
        assert specific_move is not None
        assert specific_move.move_san == sample_move.move_san
        
        # Test move limit
        limited_moves = await sqlite_backend.get_moves(sample_game.game_id, limit=1)
        assert len(limited_moves) == 1
    
    @pytest.mark.asyncio
    async def test_player_stats_operations(self, sqlite_backend):
        """Test player statistics operations."""
        player_id = "test_player"
        
        # Initially no stats
        stats = await sqlite_backend.get_player_stats(player_id)
        assert stats is None
        
        # Create stats
        new_stats = PlayerStats(
            player_id=player_id,
            games_played=10,
            wins=6,
            losses=3,
            draws=1,
            illegal_move_rate=0.05,
            average_thinking_time=2.5,
            elo_rating=1550.0,
            last_updated=datetime.now()
        )
        
        success = await sqlite_backend.update_player_stats(player_id, new_stats)
        assert success
        
        # Retrieve stats
        retrieved_stats = await sqlite_backend.get_player_stats(player_id)
        assert retrieved_stats is not None
        assert retrieved_stats.player_id == player_id
        assert retrieved_stats.games_played == 10
        assert retrieved_stats.wins == 6
        assert retrieved_stats.win_rate == 0.6
        
        # Update stats
        updated_stats = PlayerStats(
            player_id=player_id,
            games_played=11,
            wins=7,
            losses=3,
            draws=1,
            elo_rating=1575.0,
            last_updated=datetime.now()
        )
        
        success = await sqlite_backend.update_player_stats(player_id, updated_stats)
        assert success
        
        # Verify update
        final_stats = await sqlite_backend.get_player_stats(player_id)
        assert final_stats.games_played == 11
        assert final_stats.wins == 7
        assert final_stats.elo_rating == 1575.0
    
    @pytest.mark.asyncio
    async def test_game_queries(self, sqlite_backend, sample_players):
        """Test game querying with filters."""
        # Create multiple games
        games = []
        for i in range(3):
            game = GameRecord(
                game_id=f"test_game_{i:03d}",
                tournament_id="test_tournament" if i < 2 else "other_tournament",
                start_time=datetime.now() - timedelta(days=i),
                players=sample_players
            )
            games.append(game)
            await sqlite_backend.create_game(game)
        
        # Query all games
        all_games = await sqlite_backend.query_games({})
        assert len(all_games) == 3
        
        # Query by tournament
        tournament_games = await sqlite_backend.query_games({
            "tournament_id": "test_tournament"
        })
        assert len(tournament_games) == 2
        
        # Query with date filter
        recent_games = await sqlite_backend.query_games({
            "start_date": datetime.now() - timedelta(days=1)
        })
        assert len(recent_games) >= 1
        
        # Query with limit
        limited_games = await sqlite_backend.query_games({}, limit=2)
        assert len(limited_games) == 2
        
        # Count games
        total_count = await sqlite_backend.count_games({})
        assert total_count == 3
        
        tournament_count = await sqlite_backend.count_games({
            "tournament_id": "test_tournament"
        })
        assert tournament_count == 2
    
    @pytest.mark.asyncio
    async def test_data_cleanup(self, sqlite_backend, sample_players):
        """Test old data cleanup functionality."""
        # Create games with different dates
        old_date = datetime.now() - timedelta(days=30)
        recent_date = datetime.now() - timedelta(days=1)
        
        old_game = GameRecord(
            game_id="old_game",
            start_time=old_date,
            players=sample_players
        )
        
        recent_game = GameRecord(
            game_id="recent_game", 
            start_time=recent_date,
            players=sample_players
        )
        
        await sqlite_backend.create_game(old_game)
        await sqlite_backend.create_game(recent_game)
        
        # Verify both games exist
        all_games = await sqlite_backend.query_games({})
        assert len(all_games) == 2
        
        # Clean up old data
        cleanup_date = datetime.now() - timedelta(days=7)
        deleted_count = await sqlite_backend.cleanup_old_data(cleanup_date)
        assert deleted_count == 1
        
        # Verify only recent game remains
        remaining_games = await sqlite_backend.query_games({})
        assert len(remaining_games) == 1
        assert remaining_games[0].game_id == "recent_game"
    
    @pytest.mark.asyncio
    async def test_storage_stats(self, sqlite_backend, sample_game, sample_move):
        """Test storage statistics reporting."""
        # Initial stats
        stats = await sqlite_backend.get_storage_stats()
        assert stats["game_count"] == 0
        assert stats["move_count"] == 0
        assert stats["connected"] == True
        
        # Add data
        await sqlite_backend.create_game(sample_game)
        await sqlite_backend.add_move(sample_move)
        
        # Updated stats
        updated_stats = await sqlite_backend.get_storage_stats()
        assert updated_stats["game_count"] == 1
        assert updated_stats["move_count"] == 1
        assert updated_stats["database_size_bytes"] > 0
    
    @pytest.mark.asyncio
    async def test_error_handling(self, sqlite_backend):
        """Test error handling for invalid operations."""
        # Test getting non-existent game
        game = await sqlite_backend.get_game("non_existent_game")
        assert game is None
        
        # Test getting non-existent player stats
        stats = await sqlite_backend.get_player_stats("non_existent_player")
        assert stats is None
        
        # Test deleting non-existent game
        deleted = await sqlite_backend.delete_game("non_existent_game")
        assert not deleted
        
        # Test updating non-existent game
        updated = await sqlite_backend.update_game("non_existent_game", {"total_moves": 10})
        assert not updated
    
    @pytest.mark.asyncio
    async def test_concurrent_operations(self, sqlite_backend, sample_players):
        """Test concurrent database operations."""
        # Create multiple games concurrently
        async def create_game(game_id):
            game = GameRecord(
                game_id=game_id,
                start_time=datetime.now(),
                players=sample_players
            )
            return await sqlite_backend.create_game(game)
        
        # Create 5 games concurrently
        tasks = [create_game(f"concurrent_game_{i}") for i in range(5)]
        results = await asyncio.gather(*tasks)
        
        # All should succeed
        assert len(results) == 5
        assert all(result.startswith("concurrent_game_") for result in results)
        
        # Verify all games were created
        all_games = await sqlite_backend.query_games({})
        assert len(all_games) == 5


@pytest.mark.skipif(not POSTGRESQL_AVAILABLE, reason="PostgreSQL backend not available")
class TestPostgreSQLBackend:
    """Test PostgreSQL backend implementation."""
    
    @pytest.mark.asyncio
    async def test_connection_lifecycle(self):
        """Test PostgreSQL backend connection and disconnection."""
        config = DatabaseConfig(
            backend_type=StorageBackendType.POSTGRESQL,
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=int(os.getenv("POSTGRES_PORT", "5432")),
            database=os.getenv("POSTGRES_DB", "game_arena_test"),
            username=os.getenv("POSTGRES_USER", "postgres"),
            password=os.getenv("POSTGRES_PASSWORD", ""),
            connection_pool_size=3
        )
        
        backend = PostgreSQLBackend(config)
        
        # Initially not connected
        assert not backend.is_connected
        
        try:
            # Connect
            await backend.connect()
            assert backend.is_connected
            
            # Initialize schema
            await backend.initialize_schema()
            
            # Disconnect
            await backend.disconnect()
            assert not backend.is_connected
            
        except Exception as e:
            pytest.skip(f"Could not connect to PostgreSQL: {e}")
    
    @pytest.mark.asyncio
    async def test_schema_initialization(self, postgresql_backend):
        """Test PostgreSQL database schema creation."""
        stats = await postgresql_backend.get_storage_stats()
        
        assert stats["backend_type"] == "postgresql"
        assert stats["game_count"] == 0
        assert stats["move_count"] == 0
        assert stats["player_count"] == 0
        assert "connection_pool" in stats
    
    @pytest.mark.asyncio
    async def test_game_crud_operations(self, postgresql_backend, sample_game):
        """Test PostgreSQL game CRUD operations."""
        # Create game
        game_id = await postgresql_backend.create_game(sample_game)
        assert game_id == sample_game.game_id
        
        # Read game
        retrieved_game = await postgresql_backend.get_game(game_id)
        assert retrieved_game is not None
        assert retrieved_game.game_id == sample_game.game_id
        assert retrieved_game.tournament_id == sample_game.tournament_id
        assert len(retrieved_game.players) == 2
        assert retrieved_game.players[0].player_id == "black_player"
        assert retrieved_game.players[1].player_id == "white_player"
        
        # Update game
        outcome = GameOutcome(
            result=GameResult.WHITE_WINS,
            winner=1,
            termination=TerminationReason.CHECKMATE
        )
        
        updates = {
            "end_time": datetime.now(),
            "outcome": outcome,
            "total_moves": 25,
            "final_fen": "r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/3P1N2/PPP2PPP/RNBQK2R w KQkq - 4 4"
        }
        
        success = await postgresql_backend.update_game(game_id, updates)
        assert success
        
        # Verify update
        updated_game = await postgresql_backend.get_game(game_id)
        assert updated_game.outcome is not None
        assert updated_game.outcome.result == GameResult.WHITE_WINS
        assert updated_game.total_moves == 25
        
        # Delete game
        deleted = await postgresql_backend.delete_game(game_id)
        assert deleted
        
        # Verify deletion
        deleted_game = await postgresql_backend.get_game(game_id)
        assert deleted_game is None
    
    @pytest.mark.asyncio
    async def test_move_operations(self, postgresql_backend, sample_game, sample_move):
        """Test PostgreSQL move storage and retrieval operations."""
        # First create the game
        await postgresql_backend.create_game(sample_game)
        
        # Add move
        success = await postgresql_backend.add_move(sample_move)
        assert success
        
        # Get moves for game
        moves = await postgresql_backend.get_moves(sample_game.game_id)
        assert len(moves) == 1
        
        retrieved_move = moves[0]
        assert retrieved_move.game_id == sample_move.game_id
        assert retrieved_move.move_number == sample_move.move_number
        assert retrieved_move.player == sample_move.player
        assert retrieved_move.move_san == sample_move.move_san
        assert retrieved_move.is_legal == sample_move.is_legal
        assert len(retrieved_move.rethink_attempts) == 1
        
        # Get specific move
        specific_move = await postgresql_backend.get_move(
            sample_game.game_id, 
            sample_move.move_number, 
            sample_move.player
        )
        assert specific_move is not None
        assert specific_move.move_san == sample_move.move_san
        
        # Test move limit
        limited_moves = await postgresql_backend.get_moves(sample_game.game_id, limit=1)
        assert len(limited_moves) == 1
    
    @pytest.mark.asyncio
    async def test_player_stats_operations(self, postgresql_backend):
        """Test PostgreSQL player statistics operations."""
        player_id = "test_player_pg"
        
        # Initially no stats
        stats = await postgresql_backend.get_player_stats(player_id)
        assert stats is None
        
        # Create stats
        new_stats = PlayerStats(
            player_id=player_id,
            games_played=10,
            wins=6,
            losses=3,
            draws=1,
            illegal_move_rate=0.05,
            average_thinking_time=2.5,
            elo_rating=1550.0,
            last_updated=datetime.now()
        )
        
        success = await postgresql_backend.update_player_stats(player_id, new_stats)
        assert success
        
        # Retrieve stats
        retrieved_stats = await postgresql_backend.get_player_stats(player_id)
        assert retrieved_stats is not None
        assert retrieved_stats.player_id == player_id
        assert retrieved_stats.games_played == 10
        assert retrieved_stats.wins == 6
        assert retrieved_stats.win_rate == 0.6
        
        # Update stats (test UPSERT functionality)
        updated_stats = PlayerStats(
            player_id=player_id,
            games_played=11,
            wins=7,
            losses=3,
            draws=1,
            elo_rating=1575.0,
            last_updated=datetime.now()
        )
        
        success = await postgresql_backend.update_player_stats(player_id, updated_stats)
        assert success
        
        # Verify update
        final_stats = await postgresql_backend.get_player_stats(player_id)
        assert final_stats.games_played == 11
        assert final_stats.wins == 7
        assert final_stats.elo_rating == 1575.0
    
    @pytest.mark.asyncio
    async def test_game_queries(self, postgresql_backend, sample_players):
        """Test PostgreSQL game querying with filters."""
        # Create multiple games
        games = []
        for i in range(3):
            game = GameRecord(
                game_id=f"test_game_pg_{i:03d}",
                tournament_id="test_tournament_pg" if i < 2 else "other_tournament_pg",
                start_time=datetime.now() - timedelta(days=i),
                players=sample_players
            )
            games.append(game)
            await postgresql_backend.create_game(game)
        
        # Query all games
        all_games = await postgresql_backend.query_games({})
        assert len(all_games) == 3
        
        # Query by tournament
        tournament_games = await postgresql_backend.query_games({
            "tournament_id": "test_tournament_pg"
        })
        assert len(tournament_games) == 2
        
        # Query with date filter
        recent_games = await postgresql_backend.query_games({
            "start_date": datetime.now() - timedelta(days=1)
        })
        assert len(recent_games) >= 1
        
        # Query with limit
        limited_games = await postgresql_backend.query_games({}, limit=2)
        assert len(limited_games) == 2
        
        # Query with offset
        offset_games = await postgresql_backend.query_games({}, limit=2, offset=1)
        assert len(offset_games) == 2
        
        # Count games
        total_count = await postgresql_backend.count_games({})
        assert total_count == 3
        
        tournament_count = await postgresql_backend.count_games({
            "tournament_id": "test_tournament_pg"
        })
        assert tournament_count == 2
    
    @pytest.mark.asyncio
    async def test_transaction_handling(self, postgresql_backend, sample_players):
        """Test PostgreSQL transaction management."""
        game = GameRecord(
            game_id="transaction_test_game",
            start_time=datetime.now(),
            players=sample_players
        )
        
        # Create game
        await postgresql_backend.create_game(game)
        
        # Test that failed operations don't leave partial data
        try:
            # This should fail due to duplicate key
            await postgresql_backend.create_game(game)
            assert False, "Should have raised an exception"
        except Exception:
            # Expected - duplicate key error
            pass
        
        # Verify original game still exists and is complete
        retrieved_game = await postgresql_backend.get_game(game.game_id)
        assert retrieved_game is not None
        assert len(retrieved_game.players) == 2
    
    @pytest.mark.asyncio
    async def test_connection_pooling(self, postgresql_backend):
        """Test PostgreSQL connection pooling functionality."""
        stats = await postgresql_backend.get_storage_stats()
        pool_stats = stats["connection_pool"]
        
        assert pool_stats["pool_max_size"] > 0
        assert pool_stats["pool_size"] >= 0
        assert pool_stats["pool_idle_connections"] >= 0
        
        # Test concurrent operations to stress the pool
        async def get_stats():
            return await postgresql_backend.get_storage_stats()
        
        # Run multiple concurrent operations
        tasks = [get_stats() for _ in range(10)]
        results = await asyncio.gather(*tasks)
        
        # All should succeed
        assert len(results) == 10
        assert all("backend_type" in result for result in results)
    
    @pytest.mark.asyncio
    async def test_bulk_operations(self, postgresql_backend, sample_players):
        """Test PostgreSQL bulk insert operations."""
        # Create a game first
        game = GameRecord(
            game_id="bulk_test_game",
            start_time=datetime.now(),
            players=sample_players
        )
        await postgresql_backend.create_game(game)
        
        # Create multiple moves for bulk insert
        moves = []
        for i in range(5):
            move = MoveRecord(
                game_id="bulk_test_game",
                move_number=i + 1,
                player=i % 2,
                timestamp=datetime.now(),
                fen_before=f"fen_before_{i}",
                fen_after=f"fen_after_{i}",
                legal_moves=[f"move_{i}", f"move_{i+1}"],
                move_san=f"move_{i}",
                move_uci=f"move_{i}_uci",
                is_legal=True,
                prompt_text=f"prompt_{i}",
                raw_response=f"response_{i}",
                thinking_time_ms=1000 + i * 100,
                api_call_time_ms=500 + i * 50,
                parsing_time_ms=50 + i * 5
            )
            moves.append(move)
        
        # Bulk insert moves
        success = await postgresql_backend.bulk_insert_moves(moves)
        assert success
        
        # Verify all moves were inserted
        retrieved_moves = await postgresql_backend.get_moves("bulk_test_game")
        assert len(retrieved_moves) == 5
        
        # Verify move data integrity
        for i, move in enumerate(retrieved_moves):
            assert move.move_number == i + 1
            assert move.move_san == f"move_{i}"
    
    @pytest.mark.asyncio
    async def test_jsonb_operations(self, postgresql_backend, sample_players):
        """Test PostgreSQL JSONB functionality."""
        # Create game with complex metadata
        complex_metadata = {
            "tournament_settings": {
                "time_control": "5+3",
                "rated": True,
                "variant": "standard"
            },
            "analysis": {
                "engine": "stockfish",
                "depth": 20,
                "evaluations": [0.2, 0.1, -0.3, 0.5]
            },
            "tags": ["important", "analysis", "tournament"]
        }
        
        game = GameRecord(
            game_id="jsonb_test_game",
            start_time=datetime.now(),
            players=sample_players,
            metadata=complex_metadata
        )
        
        await postgresql_backend.create_game(game)
        
        # Retrieve and verify complex metadata
        retrieved_game = await postgresql_backend.get_game("jsonb_test_game")
        assert retrieved_game is not None
        assert retrieved_game.metadata == complex_metadata
        assert retrieved_game.metadata["tournament_settings"]["time_control"] == "5+3"
        assert len(retrieved_game.metadata["analysis"]["evaluations"]) == 4
    
    @pytest.mark.asyncio
    async def test_concurrent_operations(self, postgresql_backend, sample_players):
        """Test PostgreSQL concurrent database operations."""
        # Create multiple games concurrently
        async def create_game(game_id):
            game = GameRecord(
                game_id=game_id,
                start_time=datetime.now(),
                players=sample_players
            )
            return await postgresql_backend.create_game(game)
        
        # Create 10 games concurrently to test connection pooling
        tasks = [create_game(f"concurrent_pg_game_{i}") for i in range(10)]
        results = await asyncio.gather(*tasks)
        
        # All should succeed
        assert len(results) == 10
        assert all(result.startswith("concurrent_pg_game_") for result in results)
        
        # Verify all games were created
        all_games = await postgresql_backend.query_games({})
        concurrent_games = [g for g in all_games if g.game_id.startswith("concurrent_pg_game_")]
        assert len(concurrent_games) == 10
    
    @pytest.mark.asyncio
    async def test_raw_query_execution(self, postgresql_backend, sample_players):
        """Test PostgreSQL raw query execution."""
        # Create some test data
        game = GameRecord(
            game_id="raw_query_test",
            start_time=datetime.now(),
            players=sample_players,
            total_moves=10
        )
        await postgresql_backend.create_game(game)
        
        # Execute raw query
        results = await postgresql_backend.execute_raw_query(
            "SELECT game_id, total_moves FROM games WHERE game_id = $1",
            ["raw_query_test"]
        )
        
        assert len(results) == 1
        assert results[0]["game_id"] == "raw_query_test"
        assert results[0]["total_moves"] == 10
        
        # Test query without parameters
        count_results = await postgresql_backend.execute_raw_query(
            "SELECT COUNT(*) as game_count FROM games"
        )
        
        assert len(count_results) == 1
        assert "game_count" in count_results[0]
        assert count_results[0]["game_count"] >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])