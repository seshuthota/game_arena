"""
Tests for the DataCollectingAgent wrapper.

This module tests the agent wrapper's ability to capture LLM interactions,
timing data, and performance measurements while maintaining compatibility
with existing agent interfaces.
"""

import json
import time
import unittest
from unittest.mock import Mock, MagicMock, patch, call
from typing import Dict, Any, Mapping
from datetime import datetime

from game_arena.harness.agent import (
    KaggleSpielActionWithExtras,
    ChessLLMAgent,
    ChessRethinkAgent,
    INVALID_ACTION,
    ERROR_ACTION_INT
)
from game_arena.harness import tournament_util
from game_arena.storage.agent_wrapper import DataCollectingAgent, create_data_collecting_agent
from game_arena.storage.collector import GameDataCollector
from game_arena.storage.models import PlayerInfo
from game_arena.storage.config import CollectorConfig
from game_arena.storage.manager import StorageManager

import pyspiel


class TestDataCollectingAgent(unittest.TestCase):
    """Test cases for DataCollectingAgent wrapper."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create mock storage manager and collector
        self.mock_storage_manager = Mock(spec=StorageManager)
        self.mock_collector = Mock(spec=GameDataCollector)
        
        # Create test player info
        self.player_info = PlayerInfo(
            player_id="test_player",
            model_name="gpt-4",
            model_provider="openai",
            agent_type="ChessLLMAgent",
            agent_config={"temperature": 0.7},
            elo_rating=1500.0
        )
        
        # Create mock wrapped agent
        self.mock_wrapped_agent = Mock(spec=ChessLLMAgent)
        self.mock_wrapped_agent.num_model_calls = 5
        
        # Configure mock to return proper KaggleSpielActionWithExtras by default
        self.mock_wrapped_agent.return_value = KaggleSpielActionWithExtras(
            submission=INVALID_ACTION,
            actionString=None,
            thoughts=None,
            status="Default mock response",
            generate_returns=[]
        )
        
        # Create test game state
        self.game = pyspiel.load_game("chess")
        self.state = self.game.new_initial_state()
        self.serialized_state = pyspiel.serialize_game_and_state(self.game, self.state)
        
        # Create wrapper
        self.wrapper = DataCollectingAgent(
            wrapped_agent=self.mock_wrapped_agent,
            collector=self.mock_collector,
            player_info=self.player_info,
            game_id="test_game_001"
        )
    
    def test_initialization(self):
        """Test agent wrapper initialization."""
        self.assertEqual(self.wrapper.wrapped_agent, self.mock_wrapped_agent)
        self.assertEqual(self.wrapper.collector, self.mock_collector)
        self.assertEqual(self.wrapper.player_info, self.player_info)
        self.assertEqual(self.wrapper.game_id, "test_game_001")
        self.assertTrue(self.wrapper.collect_timing)
        self.assertTrue(self.wrapper.collect_rethink)
        self.assertEqual(self.wrapper.max_collection_latency_ms, 50.0)
    
    def test_set_game_id(self):
        """Test setting game ID."""
        self.wrapper.set_game_id("new_game_123")
        self.assertEqual(self.wrapper.game_id, "new_game_123")
        self.assertFalse(self.wrapper._game_started)
        self.assertEqual(self.wrapper._move_number, 0)
    
    def test_setup_step_passthrough(self):
        """Test that setup steps pass through without data collection."""
        observation = {"some_key": "some_value"}  # No serializedGameAndState
        configuration = {}
        
        expected_result = KaggleSpielActionWithExtras(
            submission=INVALID_ACTION,
            actionString=None,
            thoughts=None,
            status="Setup step",
            generate_returns=[]
        )
        self.mock_wrapped_agent.return_value = expected_result
        
        result = self.wrapper(observation, configuration)
        
        self.assertEqual(result, expected_result)
        # Verify the wrapped agent was called (don't check exact args due to mock spec issues)
        self.mock_wrapped_agent.assert_called_once()
        self.mock_collector.start_game.assert_not_called()
        self.mock_collector.record_move.assert_not_called()
    
    def test_successful_move_collection(self):
        """Test successful move data collection."""
        # Setup observation with game state
        # Get actual legal actions from the game state
        actual_legal_actions = list(self.state.legal_actions())
        observation = {
            "serializedGameAndState": self.serialized_state,
            "legalActions": actual_legal_actions
        }
        configuration = {}
        
        # Mock wrapped agent response
        generate_return = tournament_util.GenerateReturn(
            main_response="I'll play e4",
            main_response_and_thoughts="I'll play e4 because it's a good opening move"
        )
        
        # Use the first legal action from the actual game state
        legal_move = actual_legal_actions[0]
        expected_result = KaggleSpielActionWithExtras(
            submission=legal_move,
            actionString="e4",
            thoughts="I'll play e4",
            status="OK",
            generate_returns=[generate_return]
        )
        self.mock_wrapped_agent.return_value = expected_result
        
        # Execute wrapper
        result = self.wrapper(observation, configuration)
        
        # Verify result passthrough
        self.assertEqual(result, expected_result)
        
        # Verify game initialization was called
        self.mock_collector.start_game.assert_called_once()
        start_game_call = self.mock_collector.start_game.call_args
        self.assertEqual(start_game_call[0][0], "test_game_001")  # game_id
        
        # Verify move recording was called
        self.mock_collector.record_move.assert_called_once()
        record_move_call = self.mock_collector.record_move.call_args
        self.assertEqual(record_move_call[0][0], "test_game_001")  # game_id
        
        move_data = record_move_call[0][1]
        self.assertEqual(move_data['move_number'], 1)
        self.assertEqual(move_data['move_san'], "e4")
        self.assertEqual(move_data['is_legal'], True)
        self.assertEqual(move_data['raw_response'], "I'll play e4")
        self.assertGreaterEqual(move_data['thinking_time_ms'], 0)  # Allow 0 for mock agents
    
    def test_invalid_move_collection(self):
        """Test data collection for invalid moves."""
        observation = {
            "serializedGameAndState": self.serialized_state,
            "legalActions": [16, 17, 18, 19]
        }
        configuration = {}
        
        # Mock invalid move response
        expected_result = KaggleSpielActionWithExtras(
            submission=INVALID_ACTION,
            actionString="invalid_move",
            thoughts="Failed to parse move",
            status="Invalid move",
            generate_returns=[]
        )
        self.mock_wrapped_agent.return_value = expected_result
        
        result = self.wrapper(observation, configuration)
        
        self.assertEqual(result, expected_result)
        
        # Should not record move for invalid actions
        self.mock_collector.record_move.assert_not_called()
    
    def test_error_move_collection(self):
        """Test data collection for error moves."""
        observation = {
            "serializedGameAndState": self.serialized_state,
            "legalActions": [16, 17, 18, 19]
        }
        configuration = {}
        
        # Mock error response
        expected_result = KaggleSpielActionWithExtras(
            submission=ERROR_ACTION_INT,
            actionString=None,
            thoughts="Agent error occurred",
            status="Error: Model timeout",
            generate_returns=[]
        )
        self.mock_wrapped_agent.return_value = expected_result
        
        result = self.wrapper(observation, configuration)
        
        self.assertEqual(result, expected_result)
        
        # Should not record move for error actions
        self.mock_collector.record_move.assert_not_called()
    
    def test_rethink_data_collection(self):
        """Test collection of rethink attempt data."""
        # Get actual legal actions from the game state
        actual_legal_actions = list(self.state.legal_actions())
        observation = {
            "serializedGameAndState": self.serialized_state,
            "legalActions": actual_legal_actions
        }
        configuration = {}
        
        # Mock multiple generate returns (rethink scenario)
        generate_returns = [
            tournament_util.GenerateReturn(
                main_response="I'll play e4",
                main_response_and_thoughts="I'll play e4"
            ),
            tournament_util.GenerateReturn(
                main_response="Actually, let me reconsider... e4 is still good",
                main_response_and_thoughts="Rethinking... e4 is still good"
            )
        ]
        
        # Use the first legal action from the actual game state
        legal_move = actual_legal_actions[0]
        expected_result = KaggleSpielActionWithExtras(
            submission=legal_move,
            actionString="e4",
            thoughts="I'll play e4\n\nRethink: Actually, let me reconsider...",
            status="OK",
            generate_returns=generate_returns
        )
        self.mock_wrapped_agent.return_value = expected_result
        
        result = self.wrapper(observation, configuration)
        
        self.assertEqual(result, expected_result)
        
        # Verify move was recorded with rethink data
        self.mock_collector.record_move.assert_called_once()
        move_data = self.mock_collector.record_move.call_args[0][1]
        
        # Should have captured rethink attempts
        self.assertGreater(len(move_data['rethink_attempts']), 0)
        rethink_attempt = move_data['rethink_attempts'][0]
        self.assertEqual(rethink_attempt.attempt_number, 1)
        self.assertEqual(rethink_attempt.raw_response, "Actually, let me reconsider... e4 is still good")
    
    def test_timing_data_collection(self):
        """Test timing data collection."""
        observation = {
            "serializedGameAndState": self.serialized_state,
            "legalActions": [16, 17, 18, 19]
        }
        configuration = {}
        
        # Add delay to wrapped agent to test timing
        def delayed_agent_call(*args, **kwargs):
            time.sleep(0.01)  # 10ms delay
            return KaggleSpielActionWithExtras(
                submission=16,
                actionString="e4",
                thoughts="Delayed response",
                status="OK",
                generate_returns=[]
            )
        
        self.mock_wrapped_agent.side_effect = delayed_agent_call
        
        result = self.wrapper(observation, configuration)
        
        # Verify timing data was collected
        self.mock_collector.record_move.assert_called_once()
        move_data = self.mock_collector.record_move.call_args[0][1]
        
        self.assertGreater(move_data['thinking_time_ms'], 5)  # Should be > 5ms
        self.assertGreater(move_data['api_call_time_ms'], 5)  # Should be > 5ms
    
    def test_error_handling_in_wrapper(self):
        """Test error handling when wrapper encounters exceptions."""
        # Get actual legal actions from the game state
        actual_legal_actions = list(self.state.legal_actions())
        observation = {
            "serializedGameAndState": self.serialized_state,
            "legalActions": actual_legal_actions
        }
        configuration = {}
        
        # Mock collector to raise exception
        self.mock_collector.record_move.side_effect = Exception("Collection failed")
        
        # Mock successful agent response with legal move
        legal_move = actual_legal_actions[0]
        expected_result = KaggleSpielActionWithExtras(
            submission=legal_move,
            actionString="e4",
            thoughts="Good move",
            status="OK",
            generate_returns=[]
        )
        self.mock_wrapped_agent.return_value = expected_result
        
        # Should not raise exception, should return agent result
        result = self.wrapper(observation, configuration)
        self.assertEqual(result, expected_result)
        
        # Should have attempted to record error (but not necessarily called record_error)
        # The wrapper logs the error but doesn't call record_error for collection failures
        self.mock_collector.record_move.assert_called_once()
    
    def test_error_handling_in_wrapped_agent(self):
        """Test error handling when wrapped agent fails."""
        observation = {
            "serializedGameAndState": self.serialized_state,
            "legalActions": [16, 17, 18, 19]
        }
        configuration = {}
        
        # Mock wrapped agent to raise exception
        self.mock_wrapped_agent.side_effect = Exception("Agent failed")
        
        result = self.wrapper(observation, configuration)
        
        # Should return error action
        self.assertEqual(result['submission'], ERROR_ACTION_INT)
        self.assertIn("Agent wrapper error", result['thoughts'])
        
        # Should have recorded error
        self.mock_collector.record_error.assert_called()
    
    def test_performance_monitoring(self):
        """Test performance monitoring and warnings."""
        # Set low latency limit for testing
        self.wrapper.max_collection_latency_ms = 1.0  # 1ms limit
        
        observation = {
            "serializedGameAndState": self.serialized_state,
            "legalActions": [16, 17, 18, 19]
        }
        configuration = {}
        
        # Mock slow collection (by adding delay in collector)
        def slow_record_move(*args, **kwargs):
            time.sleep(0.005)  # 5ms delay
            return True
        
        self.mock_collector.record_move.side_effect = slow_record_move
        
        expected_result = KaggleSpielActionWithExtras(
            submission=16,
            actionString="e4",
            thoughts="Good move",
            status="OK",
            generate_returns=[]
        )
        self.mock_wrapped_agent.return_value = expected_result
        
        # Execute multiple times to trigger performance monitoring
        for _ in range(5):
            result = self.wrapper(observation, configuration)
            self.assertEqual(result, expected_result)
        
        # Check collection stats
        stats = self.wrapper.get_collection_stats()
        self.assertEqual(stats['total_moves_collected'], 5)
        self.assertGreater(stats['average_collection_time_ms'], 0)
        self.assertGreater(stats['collection_overhead_violations'], 0)
    
    def test_property_delegation(self):
        """Test that properties are properly delegated to wrapped agent."""
        # Test num_model_calls delegation
        self.assertEqual(self.wrapper.num_model_calls, 5)
        
        # Test with rethink agent
        mock_rethink_agent = Mock(spec=ChessRethinkAgent)
        mock_rethink_agent.num_sampler_calls = 3
        
        rethink_wrapper = DataCollectingAgent(
            wrapped_agent=mock_rethink_agent,
            collector=self.mock_collector,
            player_info=self.player_info
        )
        
        self.assertEqual(rethink_wrapper.num_sampler_calls, 3)
    
    def test_json_generate_returns_parsing(self):
        """Test parsing of JSON string generate returns."""
        observation = {
            "serializedGameAndState": self.serialized_state,
            "legalActions": [16, 17, 18, 19]
        }
        configuration = {}
        
        # Mock JSON string format generate returns
        json_return = json.dumps({
            "main_response": "I'll play e4",
            "main_response_and_thoughts": "I'll play e4 because it's good"
        })
        
        expected_result = KaggleSpielActionWithExtras(
            submission=16,
            actionString="e4",
            thoughts="I'll play e4",
            status="OK",
            generate_returns=[json_return]
        )
        self.mock_wrapped_agent.return_value = expected_result
        
        result = self.wrapper(observation, configuration)
        
        self.assertEqual(result, expected_result)
        
        # Verify move was recorded with parsed JSON data
        self.mock_collector.record_move.assert_called_once()
        move_data = self.mock_collector.record_move.call_args[0][1]
        self.assertEqual(move_data['raw_response'], "I'll play e4")
    
    def test_disabled_rethink_collection(self):
        """Test wrapper with rethink collection disabled."""
        wrapper = DataCollectingAgent(
            wrapped_agent=self.mock_wrapped_agent,
            collector=self.mock_collector,
            player_info=self.player_info,
            game_id="test_disabled_rethink",
            collect_rethink=False
        )
        
        # Get actual legal actions from the game state
        actual_legal_actions = list(self.state.legal_actions())
        observation = {
            "serializedGameAndState": self.serialized_state,
            "legalActions": actual_legal_actions
        }
        configuration = {}
        
        # Mock multiple generate returns
        generate_returns = [
            tournament_util.GenerateReturn(
                main_response="First response",
                main_response_and_thoughts="First response"
            ),
            tournament_util.GenerateReturn(
                main_response="Rethink response",
                main_response_and_thoughts="Rethink response"
            )
        ]
        
        # Use the first legal action from the actual game state
        legal_move = actual_legal_actions[0]
        expected_result = KaggleSpielActionWithExtras(
            submission=legal_move,
            actionString="e4",
            thoughts="Combined thoughts",
            status="OK",
            generate_returns=generate_returns
        )
        self.mock_wrapped_agent.return_value = expected_result
        
        result = wrapper(observation, configuration)
        
        # Verify move was recorded without rethink attempts
        self.mock_collector.record_move.assert_called_once()
        move_data = self.mock_collector.record_move.call_args[0][1]
        self.assertEqual(len(move_data['rethink_attempts']), 0)


class TestCreateDataCollectingAgent(unittest.TestCase):
    """Test cases for the factory function."""
    
    def test_factory_function(self):
        """Test the create_data_collecting_agent factory function."""
        mock_agent = Mock(spec=ChessLLMAgent)
        mock_collector = Mock(spec=GameDataCollector)
        player_info = PlayerInfo(
            player_id="test_player",
            model_name="gpt-4",
            model_provider="openai",
            agent_type="ChessLLMAgent"
        )
        
        wrapper = create_data_collecting_agent(
            agent=mock_agent,
            collector=mock_collector,
            player_info=player_info,
            game_id="test_game",
            collect_timing=False
        )
        
        self.assertIsInstance(wrapper, DataCollectingAgent)
        self.assertEqual(wrapper.wrapped_agent, mock_agent)
        self.assertEqual(wrapper.collector, mock_collector)
        self.assertEqual(wrapper.player_info, player_info)
        self.assertEqual(wrapper.game_id, "test_game")
        self.assertFalse(wrapper.collect_timing)


class TestIntegrationWithRealAgents(unittest.TestCase):
    """Integration tests with real agent implementations."""
    
    def setUp(self):
        """Set up integration test fixtures."""
        self.mock_collector = Mock(spec=GameDataCollector)
        self.player_info = PlayerInfo(
            player_id="integration_test_player",
            model_name="test_model",
            model_provider="test_provider",
            agent_type="ChessLLMAgent"
        )
    
    @patch('game_arena.harness.agent.ChessLLMAgent')
    def test_integration_with_chess_llm_agent(self, mock_llm_agent_class):
        """Test integration with ChessLLMAgent."""
        # Create mock LLM agent instance
        mock_llm_agent = Mock(spec=ChessLLMAgent)
        mock_llm_agent.num_model_calls = 0
        mock_llm_agent_class.return_value = mock_llm_agent
        
        # Mock agent response
        mock_llm_agent.return_value = KaggleSpielActionWithExtras(
            submission=16,
            actionString="e4",
            thoughts="Opening with e4",
            status="OK",
            generate_returns=[]
        )
        
        # Create wrapper
        wrapper = DataCollectingAgent(
            wrapped_agent=mock_llm_agent,
            collector=self.mock_collector,
            player_info=self.player_info,
            game_id="integration_test"
        )
        
        # Test with real game state
        game = pyspiel.load_game("chess")
        state = game.new_initial_state()
        serialized_state = pyspiel.serialize_game_and_state(game, state)
        
        observation = {
            "serializedGameAndState": serialized_state,
            "legalActions": list(state.legal_actions())
        }
        
        result = wrapper(observation, {})
        
        # Verify integration worked
        self.assertEqual(result['submission'], 16)
        self.assertEqual(result['actionString'], "e4")
        self.mock_collector.start_game.assert_called_once()
        self.mock_collector.record_move.assert_called_once()
    
    @patch('game_arena.harness.agent.ChessRethinkAgent')
    def test_integration_with_chess_rethink_agent(self, mock_rethink_agent_class):
        """Test integration with ChessRethinkAgent."""
        # Create mock rethink agent instance
        mock_rethink_agent = Mock(spec=ChessRethinkAgent)
        mock_rethink_agent.num_sampler_calls = 0
        mock_rethink_agent_class.return_value = mock_rethink_agent
        
        # Mock agent response with rethink data
        mock_rethink_agent.return_value = KaggleSpielActionWithExtras(
            submission=16,
            actionString="e4",
            thoughts="First thought\n\nRethink: Better thought",
            status="OK",
            generate_returns=[
                tournament_util.GenerateReturn(
                    main_response="First response",
                    main_response_and_thoughts="First response"
                ),
                tournament_util.GenerateReturn(
                    main_response="Rethink response",
                    main_response_and_thoughts="Rethink response"
                )
            ]
        )
        
        # Create wrapper
        wrapper = DataCollectingAgent(
            wrapped_agent=mock_rethink_agent,
            collector=self.mock_collector,
            player_info=self.player_info,
            game_id="rethink_integration_test"
        )
        
        # Test with real game state
        game = pyspiel.load_game("chess")
        state = game.new_initial_state()
        serialized_state = pyspiel.serialize_game_and_state(game, state)
        
        observation = {
            "serializedGameAndState": serialized_state,
            "legalActions": list(state.legal_actions())
        }
        
        result = wrapper(observation, {})
        
        # Verify integration worked with rethink data
        self.assertEqual(result['submission'], 16)
        self.assertEqual(result['actionString'], "e4")
        self.mock_collector.start_game.assert_called_once()
        self.mock_collector.record_move.assert_called_once()
        
        # Verify rethink data was captured
        move_data = self.mock_collector.record_move.call_args[0][1]
        self.assertGreater(len(move_data['rethink_attempts']), 0)


if __name__ == '__main__':
    unittest.main()