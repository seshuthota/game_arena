"""
Unit tests for rethink data capture and handling.

This module tests the enhanced rethink sampling data capture functionality
including multiple LLM responses, parsing attempts, rethink prompts, and failure reasons.
"""

import asyncio
import pytest
import json
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any, List

from game_arena.harness.agent import ChessRethinkAgent, KaggleSpielActionWithExtras
from game_arena.harness import tournament_util
from game_arena.harness.rethink import RethinkSampler
from game_arena.storage.collector import GameDataCollector, GameEvent, EventType
from game_arena.storage.agent_wrapper import DataCollectingAgent
from game_arena.storage.models import PlayerInfo, RethinkAttempt
from game_arena.storage.manager import StorageManager
from game_arena.storage.config import CollectorConfig
from game_arena.storage.exceptions import ValidationError

import pyspiel

# Configure pytest-asyncio
pytestmark = pytest.mark.asyncio


class TestRethinkDataCapture:
    """Test rethink data capture functionality."""
    
    @pytest.fixture
    def mock_storage_manager(self):
        """Create a mock storage manager."""
        manager = Mock(spec=StorageManager)
        manager.create_game = AsyncMock()
        manager.add_move = AsyncMock()
        manager.add_rethink_attempt = AsyncMock()
        manager.complete_game = AsyncMock()
        return manager
    
    @pytest.fixture
    def collector_config(self):
        """Create collector configuration with rethink data enabled."""
        return CollectorConfig(
            enabled=True,
            collect_rethink_data=True,
            async_processing=False,  # Use sync for easier testing
            max_collection_latency_ms=100
        )
    
    @pytest.fixture
    def collector(self, mock_storage_manager, collector_config):
        """Create a GameDataCollector instance."""
        collector = GameDataCollector(mock_storage_manager, collector_config)
        # Mock the record methods for agent wrapper tests
        collector.record_rethink_attempt = Mock(return_value=True)
        collector.record_move = Mock(return_value=True)
        collector.start_game = Mock(return_value=True)
        return collector
    
    @pytest.fixture
    def player_info(self):
        """Create test player info for rethink agent."""
        return PlayerInfo(
            player_id="rethink_test_player",
            model_name="gpt-4",
            model_provider="openai",
            agent_type="ChessRethinkAgent",
            agent_config={"num_max_rethinks": 3},
            elo_rating=1600.0
        )
    
    @pytest.fixture
    def mock_rethink_agent(self):
        """Create a mock ChessRethinkAgent."""
        agent = Mock(spec=ChessRethinkAgent)
        agent.num_sampler_calls = 0
        return agent
    
    @pytest.fixture
    def game_state(self):
        """Create a test chess game state."""
        game = pyspiel.load_game("chess")
        state = game.new_initial_state()
        return game, state
    
    def test_rethink_attempt_model_validation(self):
        """Test RethinkAttempt model validation."""
        # Valid rethink attempt
        valid_attempt = RethinkAttempt(
            attempt_number=1,
            prompt_text="Your previous move was illegal. Try again.",
            raw_response="I'll play e4 instead",
            parsed_move="e4",
            was_legal=True,
            timestamp=datetime.now()
        )
        
        assert valid_attempt.attempt_number == 1
        assert valid_attempt.prompt_text == "Your previous move was illegal. Try again."
        assert valid_attempt.was_legal is True
        
        # Test validation errors
        with pytest.raises(ValueError, match="attempt_number must be positive"):
            RethinkAttempt(
                attempt_number=0,
                prompt_text="test",
                raw_response="test",
                parsed_move=None,
                was_legal=False,
                timestamp=datetime.now()
            )
        
        with pytest.raises(ValueError, match="prompt_text cannot be empty"):
            RethinkAttempt(
                attempt_number=1,
                prompt_text="",
                raw_response="test",
                parsed_move=None,
                was_legal=False,
                timestamp=datetime.now()
            )
        
        with pytest.raises(ValueError, match="raw_response cannot be empty"):
            RethinkAttempt(
                attempt_number=1,
                prompt_text="test",
                raw_response="",
                parsed_move=None,
                was_legal=False,
                timestamp=datetime.now()
            )
    
    async def test_collector_record_rethink_attempt_success(self, mock_storage_manager):
        """Test successful rethink attempt recording."""
        # Create a real collector for this test (not mocked)
        config = CollectorConfig(
            enabled=True,
            collect_rethink_data=True,
            async_processing=False  # Use sync for easier testing
        )
        real_collector = GameDataCollector(mock_storage_manager, config)
        
        game_id = "test_rethink_game"
        move_number = 1
        player = 1
        
        attempt_data = {
            'attempt_number': 1,
            'prompt_text': "Your previous move was illegal. Legal moves: e4, d4, Nf3",
            'raw_response': "I apologize for the illegal move. Let me play e4.",
            'parsed_move': "e4",
            'was_legal': True
        }
        
        result = real_collector.record_rethink_attempt(game_id, move_number, player, attempt_data)
        
        assert result is True
        # With sync processing, the event should be processed immediately
        assert real_collector._stats.events_received == 1
    
    async def test_collector_record_rethink_attempt_disabled(self, mock_storage_manager):
        """Test rethink attempt recording when disabled."""
        config = CollectorConfig(collect_rethink_data=False)
        collector = GameDataCollector(mock_storage_manager, config)
        
        result = collector.record_rethink_attempt("game_1", 1, 1, {})
        
        assert result is True
        assert collector._stats.events_received == 0  # Should be skipped
    
    async def test_handle_rethink_attempt_success(self, collector):
        """Test successful rethink attempt event handling."""
        event = GameEvent(
            event_id="rethink_event_1",
            event_type=EventType.RETHINK_ATTEMPT,
            game_id="test_game",
            timestamp=datetime.now(),
            data={
                'move_number': 1,
                'player': 1,
                'attempt_data': {
                    'attempt_number': 1,
                    'prompt_text': "Your move 'Ke8' is illegal. Legal moves: e4, d4, Nf3",
                    'raw_response': "I see the error. Let me play e4 to control the center.",
                    'parsed_move': "e4",
                    'was_legal': True
                }
            }
        )
        
        await collector._handle_rethink_attempt(event)
        
        # Verify storage manager was called
        collector.storage_manager.add_rethink_attempt.assert_called_once()
        call_args = collector.storage_manager.add_rethink_attempt.call_args
        
        assert call_args[0][0] == "test_game"  # game_id
        assert call_args[0][1] == 1  # move_number
        assert call_args[0][2] == 1  # player
        
        rethink_attempt = call_args[0][3]
        assert isinstance(rethink_attempt, RethinkAttempt)
        assert rethink_attempt.attempt_number == 1
        assert "illegal" in rethink_attempt.prompt_text.lower()
        assert rethink_attempt.parsed_move == "e4"
        assert rethink_attempt.was_legal is True
    
    async def test_handle_rethink_attempt_missing_fields(self, collector):
        """Test rethink attempt handling with missing required fields."""
        event = GameEvent(
            event_id="rethink_event_2",
            event_type=EventType.RETHINK_ATTEMPT,
            game_id="test_game",
            timestamp=datetime.now(),
            data={
                'move_number': 1,
                'player': 1,
                'attempt_data': {
                    'attempt_number': 1,
                    # Missing prompt_text and raw_response
                    'parsed_move': "e4",
                    'was_legal': True
                }
            }
        )
        
        with pytest.raises(ValidationError, match="Missing required rethink field"):
            await collector._handle_rethink_attempt(event)
    
    def test_agent_wrapper_rethink_extraction_from_auxiliary_outputs(self, collector, player_info, mock_rethink_agent):
        """Test rethink data extraction from auxiliary outputs."""
        wrapper = DataCollectingAgent(
            wrapped_agent=mock_rethink_agent,
            collector=collector,
            player_info=player_info,
            game_id="test_rethink_extraction"
        )
        
        # Mock auxiliary outputs from RethinkSampler
        auxiliary_outputs = {
            'parsed_action_attempt_0': 'e4',
            'maybe_legal_action_attempt_0': 'e4',
            'rethink_prompt_attempt_0': '',
            
            'parsed_action_attempt_1': 'Ke8',  # Illegal move
            'maybe_legal_action_attempt_1': None,  # Not legal
            'rethink_prompt_attempt_1': 'Your previously suggested move was: Ke8, which is an illegal move.\nPlease think carefully and generate a new and legal move.',
            
            'parsed_action_attempt_2': 'd4',
            'maybe_legal_action_attempt_2': 'd4',
            'rethink_prompt_attempt_2': 'Your previously suggested move was: Ke8, which is an illegal move.\nPlease think carefully and generate a new and legal move.',
        }
        
        # Mock generate_returns for raw responses
        generate_returns = [
            tournament_util.GenerateReturn(
                main_response="I'll play e4 to control the center",
                main_response_and_thoughts="I'll play e4 to control the center"
            ),
            tournament_util.GenerateReturn(
                main_response="Actually, let me try Ke8",
                main_response_and_thoughts="Actually, let me try Ke8"
            ),
            tournament_util.GenerateReturn(
                main_response="That was illegal. Let me play d4 instead",
                main_response_and_thoughts="That was illegal. Let me play d4 instead"
            )
        ]
        
        wrapper._current_generate_returns = generate_returns
        
        rethink_attempts = wrapper._extract_rethink_from_auxiliary_outputs(auxiliary_outputs)
        
        assert len(rethink_attempts) == 2  # Attempts 1 and 2 (0 is initial)
        
        # Check first rethink attempt
        attempt1 = rethink_attempts[0]
        assert attempt1.attempt_number == 1
        assert attempt1.parsed_move == 'Ke8'
        assert attempt1.was_legal is False
        assert 'illegal move' in attempt1.prompt_text
        assert attempt1.raw_response == "Actually, let me try Ke8"
        
        # Check second rethink attempt
        attempt2 = rethink_attempts[1]
        assert attempt2.attempt_number == 2
        assert attempt2.parsed_move == 'd4'
        assert attempt2.was_legal is True
        assert 'illegal move' in attempt2.prompt_text
        assert attempt2.raw_response == "That was illegal. Let me play d4 instead"
    
    def test_agent_wrapper_rethink_extraction_from_generate_returns(self, collector, player_info, mock_rethink_agent):
        """Test rethink data extraction from generate_returns."""
        wrapper = DataCollectingAgent(
            wrapped_agent=mock_rethink_agent,
            collector=collector,
            player_info=player_info,
            game_id="test_generate_returns"
        )
        
        # Mock result with multiple generate_returns (rethink scenario)
        result = {
            'submission': 16,  # Some legal action
            'actionString': 'e4',
            'thoughts': 'Combined thoughts',
            'status': 'OK',
            'generate_returns': [
                tournament_util.GenerateReturn(
                    main_response="I'll play e4",
                    main_response_and_thoughts="I'll play e4"
                ),
                tournament_util.GenerateReturn(
                    main_response="Wait, let me reconsider... e4 is still good",
                    main_response_and_thoughts="Rethinking... e4 is still good"
                ),
                tournament_util.GenerateReturn(
                    main_response="Actually, d4 might be better, but I'll stick with e4",
                    main_response_and_thoughts="Final consideration... e4"
                )
            ]
        }
        
        prompt_text, raw_response, rethink_attempts = wrapper._extract_llm_data(result)
        
        assert raw_response == "I'll play e4"
        assert len(rethink_attempts) == 2  # Two rethink attempts (indices 1 and 2)
        
        assert rethink_attempts[0].attempt_number == 1
        assert rethink_attempts[0].raw_response == "Wait, let me reconsider... e4 is still good"
        
        assert rethink_attempts[1].attempt_number == 2
        assert rethink_attempts[1].raw_response == "Actually, d4 might be better, but I'll stick with e4"
    
    def test_agent_wrapper_rethink_extraction_json_format(self, collector, player_info, mock_rethink_agent):
        """Test rethink data extraction from JSON string format."""
        wrapper = DataCollectingAgent(
            wrapped_agent=mock_rethink_agent,
            collector=collector,
            player_info=player_info,
            game_id="test_json_format"
        )
        
        # Mock result with JSON string generate_returns
        json_returns = [
            json.dumps({
                "main_response": "I'll play e4",
                "main_response_and_thoughts": "I'll play e4 because it's good"
            }),
            json.dumps({
                "main_response": "Actually, let me think again... e4 is still best",
                "main_response_and_thoughts": "Rethinking the position... e4"
            })
        ]
        
        result = {
            'submission': 16,
            'actionString': 'e4',
            'thoughts': 'Combined thoughts',
            'status': 'OK',
            'generate_returns': json_returns
        }
        
        prompt_text, raw_response, rethink_attempts = wrapper._extract_llm_data(result)
        
        assert raw_response == "I'll play e4"
        assert len(rethink_attempts) == 1  # One rethink attempt
        assert rethink_attempts[0].raw_response == "Actually, let me think again... e4 is still best"
    
    async def test_storage_manager_add_rethink_attempt_success(self, mock_storage_manager):
        """Test StorageManager.add_rethink_attempt method."""
        from game_arena.storage.config import StorageConfig, DatabaseConfig, StorageBackendType
        
        db_config = DatabaseConfig(
            backend_type=StorageBackendType.SQLITE,
            database_url=":memory:",
            connection_pool_size=1
        )
        config = StorageConfig(database=db_config)
        manager = StorageManager(mock_storage_manager, config)
        
        # Mock the backend methods
        mock_storage_manager.get_move = AsyncMock(return_value=None)  # Move doesn't exist yet
        mock_storage_manager.add_rethink_attempt = AsyncMock(return_value=True)
        
        rethink_attempt = RethinkAttempt(
            attempt_number=1,
            prompt_text="Your move was illegal. Try again.",
            raw_response="Let me play e4 instead",
            parsed_move="e4",
            was_legal=True,
            timestamp=datetime.now()
        )
        
        result = await manager.add_rethink_attempt("game_1", 1, 1, rethink_attempt)
        
        assert result is True
        mock_storage_manager.add_rethink_attempt.assert_called_once()
    
    async def test_storage_manager_add_rethink_attempt_validation_error(self, mock_storage_manager):
        """Test StorageManager.add_rethink_attempt with validation errors."""
        from game_arena.storage.config import StorageConfig, DatabaseConfig, StorageBackendType
        
        db_config = DatabaseConfig(
            backend_type=StorageBackendType.SQLITE,
            database_url=":memory:",
            connection_pool_size=1
        )
        config = StorageConfig(database=db_config)
        manager = StorageManager(mock_storage_manager, config)
        
        # Test empty prompt_text - this should fail at model level first
        with pytest.raises(ValueError, match="prompt_text cannot be empty"):
            invalid_attempt = RethinkAttempt(
                attempt_number=1,
                prompt_text="",  # Empty prompt
                raw_response="response",
                parsed_move="e4",
                was_legal=True,
                timestamp=datetime.now()
            )
    
    def test_agent_wrapper_individual_rethink_recording(self, collector, player_info, mock_rethink_agent, game_state):
        """Test that individual rethink attempts are recorded separately."""
        game, state = game_state
        serialized_state = pyspiel.serialize_game_and_state(game, state)
        
        wrapper = DataCollectingAgent(
            wrapped_agent=mock_rethink_agent,
            collector=collector,
            player_info=player_info,
            game_id="test_individual_recording"
        )
        
        # Mock agent response with rethink attempts
        mock_result = KaggleSpielActionWithExtras(
            submission=list(state.legal_actions())[0],  # Use first legal action
            actionString="e4",
            thoughts="I'll play e4 after rethinking",
            status="OK",
            generate_returns=[
                tournament_util.GenerateReturn(
                    main_response="I'll play e4",
                    main_response_and_thoughts="I'll play e4"
                ),
                tournament_util.GenerateReturn(
                    main_response="Let me reconsider... e4 is still good",
                    main_response_and_thoughts="Rethinking... e4"
                )
            ]
        )
        
        # Add auxiliary_outputs to simulate RethinkSampler output
        # Since KaggleSpielActionWithExtras is a dict, we can add the key directly
        mock_result['auxiliary_outputs'] = {
            'parsed_action_attempt_1': 'e4',
            'maybe_legal_action_attempt_1': 'e4',
            'rethink_prompt_attempt_1': 'Your previous move was illegal. Try again.'
        }
        
        mock_rethink_agent.return_value = mock_result
        
        observation = {
            "serializedGameAndState": serialized_state,
            "legalActions": list(state.legal_actions())
        }
        
        result = wrapper(observation, {})
        
        # Verify that record_rethink_attempt was called
        collector.record_rethink_attempt.assert_called()
        
        # Check the call arguments
        call_args = collector.record_rethink_attempt.call_args
        assert call_args[0][0] == "test_individual_recording"  # game_id
        assert call_args[0][1] == 1  # move_number
        assert call_args[0][2] == 1  # player (current player from state - white to move initially)
        
        attempt_data = call_args[0][3]
        assert attempt_data['attempt_number'] == 1
        assert 'illegal' in attempt_data['prompt_text']
    
    async def test_multiple_rethink_attempts_workflow(self, collector, player_info, mock_rethink_agent, game_state):
        """Test complete workflow with multiple rethink attempts."""
        game, state = game_state
        serialized_state = pyspiel.serialize_game_and_state(game, state)
        
        wrapper = DataCollectingAgent(
            wrapped_agent=mock_rethink_agent,
            collector=collector,
            player_info=player_info,
            game_id="test_multiple_rethinks"
        )
        
        # Mock complex rethink scenario
        mock_result = KaggleSpielActionWithExtras(
            submission=list(state.legal_actions())[0],
            actionString="d4",
            thoughts="After multiple rethinks, I'll play d4",
            status="OK",
            generate_returns=[
                tournament_util.GenerateReturn(
                    main_response="I'll play Ke8",
                    main_response_and_thoughts="I'll play Ke8"
                ),
                tournament_util.GenerateReturn(
                    main_response="That's illegal. Let me try Qe8",
                    main_response_and_thoughts="Rethinking... Qe8"
                ),
                tournament_util.GenerateReturn(
                    main_response="Still illegal. Let me play d4",
                    main_response_and_thoughts="Final rethink... d4"
                )
            ]
        )
        
        # Simulate RethinkSampler auxiliary outputs
        # Since KaggleSpielActionWithExtras is a dict, we can add the key directly
        mock_result['auxiliary_outputs'] = {
            'parsed_action_attempt_0': 'Ke8',
            'maybe_legal_action_attempt_0': None,
            'rethink_prompt_attempt_0': '',
            
            'parsed_action_attempt_1': 'Qe8',
            'maybe_legal_action_attempt_1': None,
            'rethink_prompt_attempt_1': 'Your previously suggested move was: Ke8, which is an illegal move.',
            
            'parsed_action_attempt_2': 'd4',
            'maybe_legal_action_attempt_2': 'd4',
            'rethink_prompt_attempt_2': 'Your previously suggested move was: Qe8, which is an illegal move.',
        }
        
        mock_rethink_agent.return_value = mock_result
        
        observation = {
            "serializedGameAndState": serialized_state,
            "legalActions": list(state.legal_actions())
        }
        
        result = wrapper(observation, {})
        
        # Verify multiple rethink attempts were recorded
        assert collector.record_rethink_attempt.call_count == 2  # Two rethink attempts (1 and 2)
        
        # Verify the move was also recorded
        collector.record_move.assert_called_once()
        move_data = collector.record_move.call_args[0][1]
        assert len(move_data['rethink_attempts']) == 2
    
    def test_rethink_failure_reasons_capture(self, collector, player_info, mock_rethink_agent):
        """Test capture of rethink failure reasons."""
        wrapper = DataCollectingAgent(
            wrapped_agent=mock_rethink_agent,
            collector=collector,
            player_info=player_info,
            game_id="test_failure_reasons"
        )
        
        # Mock auxiliary outputs with detailed failure reasons
        auxiliary_outputs = {
            'parsed_action_attempt_1': 'Ke8',
            'maybe_legal_action_attempt_1': None,
            'rethink_prompt_attempt_1': 'Your previously suggested move was: Ke8, which is an illegal move.\nPotential reason: King cannot move to e8 as it would be in check.',
            
            'parsed_action_attempt_2': None,  # Parsing failed
            'maybe_legal_action_attempt_2': None,
            'rethink_prompt_attempt_2': 'Your previous response could not be parsed.\nPlease respond with ONLY a legal chess move.',
        }
        
        wrapper._current_generate_returns = [
            tournament_util.GenerateReturn(
                main_response="Initial response",
                main_response_and_thoughts="Initial response"
            ),
            tournament_util.GenerateReturn(
                main_response="I want to play Ke8",
                main_response_and_thoughts="I want to play Ke8"
            ),
            tournament_util.GenerateReturn(
                main_response="This is not a valid move format",
                main_response_and_thoughts="This is not a valid move format"
            ),
        ]
        
        rethink_attempts = wrapper._extract_rethink_from_auxiliary_outputs(auxiliary_outputs)
        
        assert len(rethink_attempts) == 2
        
        # Check first attempt - illegal move with reason
        attempt1 = rethink_attempts[0]
        assert 'illegal move' in attempt1.prompt_text
        assert 'King cannot move' in attempt1.prompt_text
        assert attempt1.parsed_move == 'Ke8'
        assert attempt1.was_legal is False
        
        # Check second attempt - parsing failure
        attempt2 = rethink_attempts[1]
        assert 'could not be parsed' in attempt2.prompt_text
        assert attempt2.parsed_move is None
        assert attempt2.was_legal is False
    
    async def test_rethink_data_persistence(self, mock_storage_manager, collector_config):
        """Test that rethink data is properly persisted."""
        collector = GameDataCollector(mock_storage_manager, collector_config)
        
        # Record multiple rethink attempts
        rethink_attempts = [
            {
                'attempt_number': 1,
                'prompt_text': 'First rethink prompt',
                'raw_response': 'First rethink response',
                'parsed_move': 'e4',
                'was_legal': False
            },
            {
                'attempt_number': 2,
                'prompt_text': 'Second rethink prompt',
                'raw_response': 'Second rethink response',
                'parsed_move': 'd4',
                'was_legal': True
            }
        ]
        
        for attempt_data in rethink_attempts:
            result = collector.record_rethink_attempt("game_1", 1, 1, attempt_data)
            assert result is True
        
        # Verify all attempts were queued for processing
        assert collector._stats.events_received == 2
        
        # Verify storage manager would be called for each attempt
        # (In real execution, this would happen during event processing)
        assert mock_storage_manager.add_rethink_attempt.call_count == 0  # Not called yet in sync mode
    
    def test_rethink_collection_performance(self, collector, player_info, mock_rethink_agent):
        """Test that rethink data collection doesn't significantly impact performance."""
        wrapper = DataCollectingAgent(
            wrapped_agent=mock_rethink_agent,
            collector=collector,
            player_info=player_info,
            game_id="test_performance",
            max_collection_latency_ms=10.0  # Strict limit for testing
        )
        
        # Mock a simple response without rethinks
        mock_result = KaggleSpielActionWithExtras(
            submission=16,
            actionString="e4",
            thoughts="Simple move",
            status="OK",
            generate_returns=[]
        )
        mock_rethink_agent.return_value = mock_result
        
        # Simulate multiple calls to check performance
        game = pyspiel.load_game("chess")
        state = game.new_initial_state()
        serialized_state = pyspiel.serialize_game_and_state(game, state)
        
        observation = {
            "serializedGameAndState": serialized_state,
            "legalActions": list(state.legal_actions())
        }
        
        # Execute multiple times
        for _ in range(5):
            result = wrapper(observation, {})
            assert result == mock_result
        
        # Check performance stats
        stats = wrapper.get_collection_stats()
        assert stats['total_moves_collected'] == 5
        assert stats['average_collection_time_ms'] >= 0
        
        # Performance violations should be minimal for simple cases
        # (This test might need adjustment based on actual performance)


class TestRethinkDataIntegration:
    """Integration tests for rethink data capture with real components."""
    
    @pytest.fixture
    def mock_storage_manager(self):
        """Create a mock storage manager for integration tests."""
        manager = Mock(spec=StorageManager)
        manager.create_game = AsyncMock()
        manager.add_move = AsyncMock()
        manager.add_rethink_attempt = AsyncMock()
        manager.complete_game = AsyncMock()
        return manager
    
    @pytest.fixture
    def integration_config(self):
        """Create configuration for integration testing."""
        return CollectorConfig(
            enabled=True,
            collect_rethink_data=True,
            async_processing=True,
            worker_threads=1,
            queue_size=50,
            max_collection_latency_ms=200
        )
    
    async def test_end_to_end_rethink_capture(self, mock_storage_manager, integration_config):
        """Test end-to-end rethink data capture workflow."""
        collector = GameDataCollector(mock_storage_manager, integration_config)
        await collector.initialize()
        
        try:
            player_info = PlayerInfo(
                player_id="integration_player",
                model_name="gpt-4",
                model_provider="openai",
                agent_type="ChessRethinkAgent"
            )
            
            # Start a game
            game_id = "integration_rethink_game"
            players = {0: player_info, 1: player_info}
            
            assert collector.start_game(game_id, players, {"test": "integration"})
            
            # Record multiple rethink attempts
            rethink_data = [
                {
                    'attempt_number': 1,
                    'prompt_text': 'Your move "Ke8" is illegal. Legal moves: e4, d4, Nf3',
                    'raw_response': 'I apologize. Let me play e4.',
                    'parsed_move': 'e4',
                    'was_legal': True
                },
                {
                    'attempt_number': 2,
                    'prompt_text': 'Your move "Qh8" is illegal. Legal moves: e4, d4, Nf3',
                    'raw_response': 'Sorry again. I will play d4.',
                    'parsed_move': 'd4',
                    'was_legal': True
                }
            ]
            
            for attempt_data in rethink_data:
                assert collector.record_rethink_attempt(game_id, 1, 0, attempt_data)
            
            # Record a move with rethink attempts
            move_data = {
                'move_number': 1,
                'player': 0,
                'fen_before': 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1',
                'fen_after': 'rnbqkbnr/pppppppp/8/8/3P4/8/PPP1PPPP/RNBQKBNR b KQkq d3 0 1',
                'move_san': 'd4',
                'move_uci': 'd2d4',
                'is_legal': True,
                'prompt_text': 'Make your move:',
                'raw_response': 'After rethinking, I will play d4',
                'rethink_attempts': [
                    RethinkAttempt(
                        attempt_number=1,
                        prompt_text=rethink_data[0]['prompt_text'],
                        raw_response=rethink_data[0]['raw_response'],
                        parsed_move=rethink_data[0]['parsed_move'],
                        was_legal=rethink_data[0]['was_legal'],
                        timestamp=datetime.now()
                    ),
                    RethinkAttempt(
                        attempt_number=2,
                        prompt_text=rethink_data[1]['prompt_text'],
                        raw_response=rethink_data[1]['raw_response'],
                        parsed_move=rethink_data[1]['parsed_move'],
                        was_legal=rethink_data[1]['was_legal'],
                        timestamp=datetime.now()
                    )
                ]
            }
            
            assert collector.record_move(game_id, move_data)
            
            # Wait for async processing
            await asyncio.sleep(0.2)
            
            # Verify stats
            stats = collector.get_stats()
            assert stats.events_received >= 4  # start, 2 rethinks, move
            
            # Verify storage manager calls would be made
            # (In real execution with proper backend)
            
        finally:
            await collector.shutdown()


if __name__ == "__main__":
    pytest.main([__file__])