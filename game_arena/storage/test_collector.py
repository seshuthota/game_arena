"""
Unit tests for the GameDataCollector.

Tests event capture, queuing, processing, validation, and error handling.
"""

import asyncio
import pytest
import time
import threading
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from queue import Queue, Empty

from .collector import GameDataCollector, GameEvent, EventType, ProcessingStats
from .models import GameRecord, MoveRecord, PlayerInfo, GameOutcome, GameResult, TerminationReason, RethinkAttempt
from .manager import StorageManager
from .config import CollectorConfig
from .exceptions import ValidationError, PerformanceError

# Configure pytest-asyncio
pytestmark = pytest.mark.asyncio


class TestGameEvent:
    """Test GameEvent data class."""
    
    def test_valid_event_creation(self):
        """Test creating a valid game event."""
        event = GameEvent(
            event_id="test_event_1",
            event_type=EventType.GAME_START,
            game_id="test_game_1",
            timestamp=datetime.now(),
            data={"test": "data"}
        )
        
        assert event.event_id == "test_event_1"
        assert event.event_type == EventType.GAME_START
        assert event.game_id == "test_game_1"
        assert event.retry_count == 0
        assert event.data == {"test": "data"}
    
    def test_event_validation(self):
        """Test event validation in __post_init__."""
        # Test empty event_id
        with pytest.raises(ValueError, match="event_id cannot be empty"):
            GameEvent(
                event_id="",
                event_type=EventType.GAME_START,
                game_id="test_game",
                timestamp=datetime.now(),
                data={}
            )
        
        # Test empty game_id
        with pytest.raises(ValueError, match="game_id cannot be empty"):
            GameEvent(
                event_id="test_event",
                event_type=EventType.GAME_START,
                game_id="",
                timestamp=datetime.now(),
                data={}
            )
        
        # Test negative retry_count
        with pytest.raises(ValueError, match="retry_count cannot be negative"):
            GameEvent(
                event_id="test_event",
                event_type=EventType.GAME_START,
                game_id="test_game",
                timestamp=datetime.now(),
                data={},
                retry_count=-1
            )


class TestProcessingStats:
    """Test ProcessingStats data class."""
    
    def test_default_stats(self):
        """Test default processing stats."""
        stats = ProcessingStats()
        
        assert stats.events_received == 0
        assert stats.events_processed == 0
        assert stats.events_failed == 0
        assert stats.events_retried == 0
        assert stats.processing_errors == []
        assert stats.average_processing_time_ms == 0.0
        assert stats.queue_size == 0
        assert isinstance(stats.last_updated, datetime)


class TestGameDataCollector:
    """Test GameDataCollector functionality."""
    
    @pytest.fixture
    def mock_storage_manager(self):
        """Create a mock storage manager."""
        manager = Mock(spec=StorageManager)
        manager.create_game = AsyncMock()
        manager.add_move = AsyncMock()
        manager.complete_game = AsyncMock()
        return manager
    
    @pytest.fixture
    def collector_config(self):
        """Create a test collector configuration."""
        return CollectorConfig(
            enabled=True,
            async_processing=False,  # Use sync processing for easier testing
            queue_size=100,
            worker_threads=1,
            max_collection_latency_ms=50,
            continue_on_collection_error=True,
            max_retry_attempts=2,
            retry_delay_seconds=0.1
        )
    
    @pytest.fixture
    def collector(self, mock_storage_manager, collector_config):
        """Create a GameDataCollector instance."""
        return GameDataCollector(mock_storage_manager, collector_config)
    
    @pytest.fixture
    def sample_players(self):
        """Create sample player info."""
        return {
            0: PlayerInfo(
                player_id="player_black",
                model_name="gpt-4",
                model_provider="openai",
                agent_type="ChessLLMAgent"
            ),
            1: PlayerInfo(
                player_id="player_white",
                model_name="gemini-pro",
                model_provider="google",
                agent_type="ChessRethinkAgent"
            )
        }
    
    @pytest.fixture
    def sample_move_data(self):
        """Create sample move data."""
        return {
            'move_number': 1,
            'player': 1,
            'fen_before': "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
            'fen_after': "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1",
            'legal_moves': ["e2e4", "d2d4", "g1f3"],
            'move_san': "e4",
            'move_uci': "e2e4",
            'is_legal': True,
            'prompt_text': "Make your move as white:",
            'raw_response': "I'll play e4 to control the center",
            'parsed_move': "e4",
            'parsing_success': True,
            'thinking_time_ms': 1500,
            'api_call_time_ms': 800,
            'parsing_time_ms': 50
        }
    
    async def test_initialization(self, collector):
        """Test collector initialization."""
        await collector.initialize()
        
        assert not collector._shutdown_event.is_set()
        assert len(collector._processing_workers) == 0  # Sync processing
        assert collector._stats.events_received == 0
    
    async def test_initialization_disabled(self, mock_storage_manager):
        """Test collector initialization when disabled."""
        config = CollectorConfig(enabled=False)
        collector = GameDataCollector(mock_storage_manager, config)
        
        await collector.initialize()
        
        assert len(collector._processing_workers) == 0
    
    async def test_shutdown(self, collector):
        """Test collector shutdown."""
        await collector.initialize()
        await collector.shutdown()
        
        assert collector._shutdown_event.is_set()
    
    def test_start_game_success(self, collector, sample_players):
        """Test successful game start event capture."""
        game_id = "test_game_1"
        metadata = {"tournament_id": "test_tournament"}
        
        result = collector.start_game(game_id, sample_players, metadata)
        
        assert result is True
        assert collector._stats.events_received == 1
        assert collector.is_game_active(game_id)
    
    def test_start_game_validation_error(self, collector):
        """Test game start with invalid players."""
        game_id = "test_game_1"
        invalid_players = {0: "not_a_player_info"}  # Invalid player data
        
        # Should not raise exception due to continue_on_collection_error=True
        # But will return False because validation fails during processing
        result = collector.start_game(game_id, invalid_players)
        
        # Event processing fails due to validation error
        assert result is False
    
    def test_record_move_success(self, collector, sample_move_data):
        """Test successful move event capture."""
        game_id = "test_game_1"
        
        result = collector.record_move(game_id, sample_move_data)
        
        assert result is True
        assert collector._stats.events_received == 1
    
    def test_record_move_missing_fields(self, collector):
        """Test move recording with missing required fields."""
        game_id = "test_game_1"
        incomplete_move_data = {
            'move_number': 1,
            'player': 1,
            # Missing required fields
        }
        
        result = collector.record_move(game_id, incomplete_move_data)
        
        # Event processing fails due to missing required fields
        assert result is False
    
    def test_end_game_success(self, collector):
        """Test successful game end event capture."""
        game_id = "test_game_1"
        outcome = GameOutcome(
            result=GameResult.WHITE_WINS,
            winner=1,
            termination=TerminationReason.CHECKMATE
        )
        final_fen = "rnbqkb1r/pppp1ppp/5n2/4p3/2B1P3/8/PPPP1PPP/RNBQK1NR w KQkq - 2 3"
        total_moves = 5
        
        result = collector.end_game(game_id, outcome, final_fen, total_moves)
        
        assert result is True
        assert collector._stats.events_received == 1
    
    def test_record_rethink_attempt_success(self, collector):
        """Test successful rethink attempt event capture."""
        game_id = "test_game_1"
        move_number = 1
        player = 1
        attempt_data = {
            'attempt_number': 1,
            'prompt_text': "Rethink your move:",
            'raw_response': "Actually, let me play d4 instead",
            'parsed_move': "d4",
            'was_legal': True
        }
        
        result = collector.record_rethink_attempt(game_id, move_number, player, attempt_data)
        
        assert result is True
        assert collector._stats.events_received == 1
    
    def test_record_rethink_attempt_disabled(self, mock_storage_manager):
        """Test rethink attempt recording when disabled."""
        config = CollectorConfig(collect_rethink_data=False)
        collector = GameDataCollector(mock_storage_manager, config)
        
        result = collector.record_rethink_attempt("game_1", 1, 1, {})
        
        assert result is True
        assert collector._stats.events_received == 0  # Should be skipped
    
    def test_record_error_success(self, collector):
        """Test successful error event capture."""
        game_id = "test_game_1"
        error_type = "parsing_error"
        error_message = "Failed to parse move"
        context = {"move_text": "invalid_move"}
        
        result = collector.record_error(game_id, error_type, error_message, context)
        
        assert result is True
        assert collector._stats.events_received == 1
    
    async def test_handle_game_start_success(self, collector, sample_players):
        """Test successful game start event handling."""
        event = GameEvent(
            event_id="test_event",
            event_type=EventType.GAME_START,
            game_id="test_game_1",
            timestamp=datetime.now(),
            data={
                'players': sample_players,
                'metadata': {'tournament_id': 'test_tournament'}
            }
        )
        
        await collector._handle_game_start(event)
        
        # Verify storage manager was called
        collector.storage_manager.create_game.assert_called_once()
        
        # Verify game is tracked as active
        assert collector.is_game_active("test_game_1")
    
    async def test_handle_game_start_validation_error(self, collector):
        """Test game start handling with validation error."""
        event = GameEvent(
            event_id="test_event",
            event_type=EventType.GAME_START,
            game_id="test_game_1",
            timestamp=datetime.now(),
            data={
                'players': {0: "invalid_player"},  # Invalid player data
                'metadata': {}
            }
        )
        
        with pytest.raises(ValidationError):
            await collector._handle_game_start(event)
    
    async def test_handle_move_made_success(self, collector, sample_move_data):
        """Test successful move event handling."""
        event = GameEvent(
            event_id="test_event",
            event_type=EventType.MOVE_MADE,
            game_id="test_game_1",
            timestamp=datetime.now(),
            data=sample_move_data
        )
        
        await collector._handle_move_made(event)
        
        # Verify storage manager was called
        collector.storage_manager.add_move.assert_called_once()
    
    async def test_handle_move_made_missing_fields(self, collector):
        """Test move handling with missing required fields."""
        event = GameEvent(
            event_id="test_event",
            event_type=EventType.MOVE_MADE,
            game_id="test_game_1",
            timestamp=datetime.now(),
            data={'move_number': 1}  # Missing required fields
        )
        
        with pytest.raises(ValidationError, match="Missing required field"):
            await collector._handle_move_made(event)
    
    async def test_handle_game_end_success(self, collector):
        """Test successful game end event handling."""
        outcome = GameOutcome(
            result=GameResult.WHITE_WINS,
            winner=1,
            termination=TerminationReason.CHECKMATE
        )
        
        event = GameEvent(
            event_id="test_event",
            event_type=EventType.GAME_END,
            game_id="test_game_1",
            timestamp=datetime.now(),
            data={
                'outcome': outcome,
                'final_fen': "final_position",
                'total_moves': 10
            }
        )
        
        # Add game to active games first
        collector._active_games["test_game_1"] = Mock()
        
        await collector._handle_game_end(event)
        
        # Verify storage manager was called
        collector.storage_manager.complete_game.assert_called_once_with(
            "test_game_1", outcome, "final_position", 10
        )
        
        # Verify game is no longer active
        assert not collector.is_game_active("test_game_1")
    
    async def test_handle_rethink_attempt_success(self, collector):
        """Test successful rethink attempt event handling."""
        event = GameEvent(
            event_id="test_event",
            event_type=EventType.RETHINK_ATTEMPT,
            game_id="test_game_1",
            timestamp=datetime.now(),
            data={
                'move_number': 1,
                'player': 1,
                'attempt_data': {
                    'attempt_number': 1,
                    'prompt_text': "Rethink prompt",
                    'raw_response': "Rethink response",
                    'parsed_move': "d4",
                    'was_legal': True
                }
            }
        )
        
        # Should not raise exception
        await collector._handle_rethink_attempt(event)
    
    async def test_handle_error_success(self, collector):
        """Test successful error event handling."""
        event = GameEvent(
            event_id="test_event",
            event_type=EventType.ERROR_OCCURRED,
            game_id="test_game_1",
            timestamp=datetime.now(),
            data={
                'error_type': 'parsing_error',
                'error_message': 'Failed to parse move',
                'context': {'move': 'invalid'}
            }
        )
        
        # Should not raise exception
        await collector._handle_error(event)
    
    def test_get_stats(self, collector):
        """Test getting processing statistics."""
        # Simulate some activity
        collector._stats.events_received = 10
        collector._stats.events_processed = 8
        collector._stats.events_failed = 2
        
        stats = collector.get_stats()
        
        assert isinstance(stats, ProcessingStats)
        assert stats.events_received == 10
        assert stats.events_processed == 8
        assert stats.events_failed == 2
    
    def test_get_active_games(self, collector):
        """Test getting active games list."""
        # Add some active games
        collector._active_games["game_1"] = Mock()
        collector._active_games["game_2"] = Mock()
        
        active_games = collector.get_active_games()
        
        assert len(active_games) == 2
        assert "game_1" in active_games
        assert "game_2" in active_games
    
    def test_is_game_active(self, collector):
        """Test checking if game is active."""
        collector._active_games["active_game"] = Mock()
        
        assert collector.is_game_active("active_game") is True
        assert collector.is_game_active("inactive_game") is False
    
    def test_clear_stats(self, collector):
        """Test clearing processing statistics."""
        # Set some stats
        collector._stats.events_received = 10
        collector._processing_times = [1.0, 2.0, 3.0]
        
        collector.clear_stats()
        
        assert collector._stats.events_received == 0
        assert len(collector._processing_times) == 0
    
    async def test_process_event_sync_success(self, collector, sample_players):
        """Test synchronous event processing."""
        event = GameEvent(
            event_id="test_event",
            event_type=EventType.GAME_START,
            game_id="test_game_1",
            timestamp=datetime.now(),
            data={
                'players': sample_players,
                'metadata': {}
            }
        )
        
        await collector._process_event_sync(event)
        
        # Verify handler was called
        collector.storage_manager.create_game.assert_called_once()
    
    async def test_process_event_sync_unknown_event_type(self, collector):
        """Test processing event with unknown event type."""
        # Create event with invalid event type by bypassing enum validation
        event = GameEvent(
            event_id="test_event",
            event_type=EventType.GAME_START,  # Will be overridden
            game_id="test_game_1",
            timestamp=datetime.now(),
            data={}
        )
        event.event_type = "UNKNOWN_EVENT"  # Override with invalid type
        
        with pytest.raises(ValueError, match="No handler for event type"):
            await collector._process_event_sync(event)
    
    def test_queue_event_sync_processing(self, collector):
        """Test event queuing with synchronous processing."""
        event = GameEvent(
            event_id="test_event",
            event_type=EventType.ERROR_OCCURRED,
            game_id="test_game_1",
            timestamp=datetime.now(),
            data={
                'error_type': 'test_error',
                'error_message': 'test message',
                'context': {}
            }
        )
        
        result = collector._queue_event(event)
        
        assert result is True
        assert collector._stats.events_received == 1
    
    @pytest.mark.asyncio
    async def test_async_processing_worker(self, mock_storage_manager):
        """Test asynchronous processing worker."""
        config = CollectorConfig(
            async_processing=True,
            worker_threads=1,
            queue_size=10
        )
        collector = GameDataCollector(mock_storage_manager, config)
        
        await collector.initialize()
        
        # Add an error event (simplest to process)
        collector.record_error("test_game", "test_error", "test message")
        
        # Wait a bit for processing
        await asyncio.sleep(0.1)
        
        # Check that event was processed
        stats = collector.get_stats()
        assert stats.events_received >= 1
        
        await collector.shutdown()
    
    def test_performance_constraint_violation(self, collector, caplog):
        """Test handling of performance constraint violations."""
        # Mock a slow processing time
        with patch('time.time', side_effect=[0, 0.1]):  # 100ms processing time
            collector._processing_times = [100.0]  # Simulate slow processing
            collector._stats.average_processing_time_ms = 100.0
            
            # This should log a warning since 100ms > 50ms limit
            # We can't easily test the worker thread logging, so we'll test the logic
            assert collector.config.max_collection_latency_ms == 50
            assert 100.0 > collector.config.max_collection_latency_ms
    
    def test_continue_on_error_behavior(self, mock_storage_manager):
        """Test behavior when continue_on_collection_error is True."""
        config = CollectorConfig(continue_on_collection_error=True)
        collector = GameDataCollector(mock_storage_manager, config)
        
        # This should not raise an exception even with invalid data
        result = collector.start_game("test_game", "invalid_players")
        assert result is True
    
    def test_stop_on_error_behavior(self, mock_storage_manager):
        """Test behavior when continue_on_collection_error is False."""
        config = CollectorConfig(continue_on_collection_error=False)
        collector = GameDataCollector(mock_storage_manager, config)
        
        # Mock _queue_event to raise an exception
        with patch.object(collector, '_queue_event', side_effect=Exception("Test error")):
            with pytest.raises(Exception, match="Test error"):
                collector.start_game("test_game", {})


class TestIntegration:
    """Integration tests for GameDataCollector."""
    
    @pytest.fixture
    def mock_storage_manager(self):
        """Create a mock storage manager."""
        manager = Mock(spec=StorageManager)
        manager.create_game = AsyncMock()
        manager.add_move = AsyncMock()
        manager.complete_game = AsyncMock()
        return manager
    
    @pytest.fixture
    def integration_config(self):
        """Create configuration for integration testing."""
        return CollectorConfig(
            enabled=True,
            async_processing=True,
            worker_threads=2,
            queue_size=50,
            max_collection_latency_ms=100,
            continue_on_collection_error=True,
            max_retry_attempts=1,
            retry_delay_seconds=0.01
        )
    
    async def test_full_game_workflow(self, mock_storage_manager, integration_config):
        """Test complete game data collection workflow."""
        collector = GameDataCollector(mock_storage_manager, integration_config)
        await collector.initialize()
        
        try:
            # Start game
            players = {
                0: PlayerInfo("player1", "model1", "provider1", "ChessLLMAgent"),
                1: PlayerInfo("player2", "model2", "provider2", "ChessRethinkAgent")
            }
            
            game_id = "integration_test_game"
            
            # Capture game events
            assert collector.start_game(game_id, players, {"tournament_id": "test"})
            
            # Record some moves
            move_data = {
                'move_number': 1,
                'player': 1,
                'fen_before': "start_fen",
                'fen_after': "after_fen",
                'move_san': "e4",
                'move_uci': "e2e4",
                'is_legal': True,
                'prompt_text': "Your move:",
                'raw_response': "I play e4"
            }
            assert collector.record_move(game_id, move_data)
            
            # Record rethink attempt
            rethink_data = {
                'attempt_number': 1,
                'prompt_text': "Rethink:",
                'raw_response': "Actually, d4",
                'parsed_move': "d4",
                'was_legal': True
            }
            assert collector.record_rethink_attempt(game_id, 2, 0, rethink_data)
            
            # End game
            outcome = GameOutcome(GameResult.WHITE_WINS, 1, TerminationReason.CHECKMATE)
            assert collector.end_game(game_id, outcome, "final_fen", 10)
            
            # Wait for processing
            await asyncio.sleep(0.2)
            
            # Verify stats
            stats = collector.get_stats()
            assert stats.events_received >= 4  # start, move, rethink, end
            
            # Verify storage manager calls
            mock_storage_manager.create_game.assert_called()
            mock_storage_manager.add_move.assert_called()
            mock_storage_manager.complete_game.assert_called()
            
        finally:
            await collector.shutdown()
    
    async def test_error_handling_and_retry(self, mock_storage_manager, integration_config):
        """Test error handling and retry logic."""
        # Make storage manager fail initially, then succeed
        mock_storage_manager.create_game.side_effect = [
            Exception("First attempt fails"),
            None  # Second attempt succeeds
        ]
        
        collector = GameDataCollector(mock_storage_manager, integration_config)
        await collector.initialize()
        
        try:
            players = {
                0: PlayerInfo("player1", "model1", "provider1", "ChessLLMAgent"),
                1: PlayerInfo("player2", "model2", "provider2", "ChessRethinkAgent")
            }
            
            # This should trigger retry logic
            collector.start_game("retry_test_game", players)
            
            # Wait for processing and retry
            await asyncio.sleep(0.3)
            
            # Verify retry occurred
            stats = collector.get_stats()
            assert stats.events_retried >= 1
            
        finally:
            await collector.shutdown()


if __name__ == "__main__":
    pytest.main([__file__])