"""
Integration tests for ChessLLMAgent and ChessRethinkAgent data collection hooks.

Tests verify that data collection integration works correctly with minimal
performance impact and maintains compatibility with existing behavior.
"""

import unittest
from unittest.mock import Mock, MagicMock, patch
import time
from typing import Dict, Any, List

from game_arena.harness.agent import (
    ChessLLMAgent, 
    ChessRethinkAgent,
    default_chess_prompt_builder,
    default_response_parser,
    INVALID_ACTION,
    ERROR_ACTION_INT
)
from game_arena.harness import model_generation
from game_arena.harness import tournament_util
from game_arena.harness import prompts
from game_arena.harness import rethink

import pyspiel


class MockModel(model_generation.Model):
    """Mock model for testing."""
    
    def __init__(self, response_text: str = "e4", should_fail: bool = False):
        self.response_text = response_text
        self.should_fail = should_fail
        self.call_count = 0
    
    def generate_with_text_input(self, model_input):
        self.call_count += 1
        if self.should_fail:
            raise Exception("Mock model failure")
        
        mock_response = Mock()
        mock_response.main_response = self.response_text
        return mock_response


class MockRethinkSampler:
    """Mock rethink sampler for testing."""
    
    def __init__(self, action: str = "e4", move_type=None, should_fail: bool = False):
        self.action = action
        self.move_type = move_type or tournament_util.MoveType.LEGAL
        self.should_fail = should_fail
        self.call_count = 0
        
    def sample_action_with_text_and_state_input(self, state, template, **kwargs):
        self.call_count += 1
        if self.should_fail:
            raise Exception("Mock sampler failure")
        
        # Create mock generate returns
        mock_return1 = Mock()
        mock_return1.main_response = f"Initial response: {self.action}"
        
        mock_return2 = Mock()
        mock_return2.main_response = f"Rethink response: {self.action}"
        
        mock_output = Mock()
        mock_output.action = self.action
        mock_output.move_type = self.move_type
        mock_output.generate_returns = [mock_return1, mock_return2]
        mock_output.auxiliary_outputs = {
            'parsed_action_attempt_1': self.action,
            'maybe_legal_action_attempt_1': self.action,
            'rethink_prompt_attempt_1': 'Rethink prompt text'
        }
        
        return mock_output


class TestChessLLMAgentIntegration(unittest.TestCase):
    """Test ChessLLMAgent data collection integration."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.game = pyspiel.load_game("chess")
        self.state = self.game.new_initial_state()
        
        # Create observation
        self.observation = {
            "serializedGameAndState": pyspiel.serialize_game_and_state(
                self.game, self.state
            ),
            "legalActions": list(self.state.legal_actions())
        }
        self.configuration = {}
        
        # Mock model
        self.mock_model = MockModel("e4")
        
        # Data collection tracking
        self.collected_events = []
        
    def data_collection_callback(self, event_type: str, data: Dict[str, Any]):
        """Callback to capture data collection events."""
        self.collected_events.append({
            'event_type': event_type,
            'data': data
        })
    
    def test_agent_without_data_collection(self):
        """Test that agent works normally without data collection enabled."""
        agent = ChessLLMAgent(
            model=self.mock_model,
            prompt_builder=default_chess_prompt_builder,
            response_parser=default_response_parser
        )
        
        result = agent(self.observation, self.configuration)
        
        # Verify normal operation
        self.assertNotEqual(result['submission'], INVALID_ACTION)
        self.assertEqual(result['actionString'], 'e4')
        self.assertEqual(self.mock_model.call_count, 1)
        self.assertEqual(len(self.collected_events), 0)
    
    def test_agent_with_data_collection_enabled(self):
        """Test that agent collects data when enabled."""
        agent = ChessLLMAgent(
            model=self.mock_model,
            prompt_builder=default_chess_prompt_builder,
            response_parser=default_response_parser,
            data_collection_enabled=True,
            data_collection_callback=self.data_collection_callback
        )
        
        result = agent(self.observation, self.configuration)
        
        # Verify normal operation
        self.assertNotEqual(result['submission'], INVALID_ACTION)
        self.assertEqual(result['actionString'], 'e4')
        self.assertEqual(self.mock_model.call_count, 1)
        
        # Verify data collection
        self.assertEqual(len(self.collected_events), 1)
        event = self.collected_events[0]
        self.assertEqual(event['event_type'], 'move_made')
        
        move_data = event['data']
        self.assertEqual(move_data['move_number'], 1)
        self.assertEqual(move_data['player'], 1)  # White to move
        self.assertEqual(move_data['move_san'], 'e4')
        self.assertTrue(move_data['is_legal'])
        self.assertTrue(move_data['parsing_success'])
        self.assertGreaterEqual(move_data['thinking_time_ms'], 0)
        self.assertGreaterEqual(move_data['api_call_time_ms'], 0)
        self.assertEqual(len(move_data['rethink_attempts']), 0)
    
    def test_agent_data_collection_performance_impact(self):
        """Test that data collection has minimal performance impact."""
        # Agent without data collection
        agent_no_collection = ChessLLMAgent(
            model=MockModel("e4"),
            prompt_builder=default_chess_prompt_builder,
            response_parser=default_response_parser
        )
        
        # Agent with data collection
        agent_with_collection = ChessLLMAgent(
            model=MockModel("e4"),
            prompt_builder=default_chess_prompt_builder,
            response_parser=default_response_parser,
            data_collection_enabled=True,
            data_collection_callback=self.data_collection_callback
        )
        
        # Time both agents
        start_time = time.time()
        for _ in range(10):
            agent_no_collection(self.observation, self.configuration)
        no_collection_time = time.time() - start_time
        
        start_time = time.time()
        for _ in range(10):
            agent_with_collection(self.observation, self.configuration)
        with_collection_time = time.time() - start_time
        
        # Verify performance impact is minimal (less than 50ms per move)
        overhead_per_move = (with_collection_time - no_collection_time) / 10 * 1000
        self.assertLess(overhead_per_move, 50.0, 
                       f"Data collection overhead {overhead_per_move:.1f}ms exceeds 50ms limit")
    
    def test_agent_data_collection_error_handling(self):
        """Test that data collection errors don't interrupt game execution."""
        def failing_callback(event_type: str, data: Dict[str, Any]):
            raise Exception("Callback failure")
        
        agent = ChessLLMAgent(
            model=self.mock_model,
            prompt_builder=default_chess_prompt_builder,
            response_parser=default_response_parser,
            data_collection_enabled=True,
            data_collection_callback=failing_callback
        )
        
        # Should not raise exception despite callback failure
        result = agent(self.observation, self.configuration)
        
        # Verify normal operation continues
        self.assertNotEqual(result['submission'], INVALID_ACTION)
        self.assertEqual(result['actionString'], 'e4')
    
    def test_agent_model_call_error_collection(self):
        """Test that model call errors are properly collected."""
        failing_model = MockModel(should_fail=True)
        
        agent = ChessLLMAgent(
            model=failing_model,
            prompt_builder=default_chess_prompt_builder,
            response_parser=default_response_parser,
            data_collection_enabled=True,
            data_collection_callback=self.data_collection_callback
        )
        
        result = agent(self.observation, self.configuration)
        
        # Verify error handling
        self.assertEqual(result['submission'], INVALID_ACTION)
        
        # Verify error data collection
        self.assertEqual(len(self.collected_events), 1)
        event = self.collected_events[0]
        self.assertEqual(event['event_type'], 'move_made')
        
        move_data = event['data']
        self.assertEqual(move_data['error_type'], 'model_call_error')
        self.assertIsNotNone(move_data['error_message'])
        self.assertFalse(move_data['parsing_success'])
    
    def test_agent_enable_disable_data_collection(self):
        """Test enabling and disabling data collection dynamically."""
        agent = ChessLLMAgent(
            model=self.mock_model,
            prompt_builder=default_chess_prompt_builder,
            response_parser=default_response_parser
        )
        
        # Initially disabled
        agent(self.observation, self.configuration)
        self.assertEqual(len(self.collected_events), 0)
        
        # Enable data collection
        agent.enable_data_collection(self.data_collection_callback)
        agent(self.observation, self.configuration)
        self.assertEqual(len(self.collected_events), 1)
        
        # Disable data collection
        agent.disable_data_collection()
        agent(self.observation, self.configuration)
        self.assertEqual(len(self.collected_events), 1)  # No new events


class TestChessRethinkAgentIntegration(unittest.TestCase):
    """Test ChessRethinkAgent data collection integration."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.game = pyspiel.load_game("chess")
        self.state = self.game.new_initial_state()
        
        # Create observation
        self.observation = {
            "serializedGameAndState": pyspiel.serialize_game_and_state(
                self.game, self.state
            ),
            "legalActions": list(self.state.legal_actions())
        }
        self.configuration = {}
        
        # Mock sampler
        self.mock_sampler = MockRethinkSampler("e4")
        
        # Data collection tracking
        self.collected_events = []
        
    def data_collection_callback(self, event_type: str, data: Dict[str, Any]):
        """Callback to capture data collection events."""
        self.collected_events.append({
            'event_type': event_type,
            'data': data
        })
    
    def test_rethink_agent_without_data_collection(self):
        """Test that rethink agent works normally without data collection."""
        agent = ChessRethinkAgent(
            sampler=self.mock_sampler,
            prompt_template=prompts.PromptTemplate.NO_LEGAL_ACTIONS_RETHINK_APPENDED
        )
        
        result = agent(self.observation, self.configuration)
        
        # Verify normal operation
        self.assertNotEqual(result['submission'], INVALID_ACTION)
        self.assertEqual(result['actionString'], 'e4')
        self.assertEqual(self.mock_sampler.call_count, 1)
        self.assertEqual(len(self.collected_events), 0)
    
    def test_rethink_agent_with_data_collection(self):
        """Test that rethink agent collects comprehensive data."""
        agent = ChessRethinkAgent(
            sampler=self.mock_sampler,
            prompt_template=prompts.PromptTemplate.NO_LEGAL_ACTIONS_RETHINK_APPENDED,
            data_collection_enabled=True,
            data_collection_callback=self.data_collection_callback
        )
        
        result = agent(self.observation, self.configuration)
        
        # Verify normal operation
        self.assertNotEqual(result['submission'], INVALID_ACTION)
        self.assertEqual(result['actionString'], 'e4')
        self.assertEqual(self.mock_sampler.call_count, 1)
        
        # Verify data collection (should have move_made and rethink_attempt events)
        self.assertGreaterEqual(len(self.collected_events), 1)
        
        # Check move_made event
        move_events = [e for e in self.collected_events if e['event_type'] == 'move_made']
        self.assertEqual(len(move_events), 1)
        
        move_data = move_events[0]['data']
        self.assertEqual(move_data['move_number'], 1)
        self.assertEqual(move_data['player'], 1)  # White to move
        self.assertEqual(move_data['move_san'], 'e4')
        self.assertTrue(move_data['is_legal'])
        self.assertTrue(move_data['parsing_success'])
        self.assertGreater(move_data['parsing_attempts'], 1)  # Should include rethink attempts
        self.assertGreater(len(move_data['rethink_attempts']), 0)
        
        # Check rethink_attempt events
        rethink_events = [e for e in self.collected_events if e['event_type'] == 'rethink_attempt']
        self.assertGreaterEqual(len(rethink_events), 1)
    
    def test_rethink_agent_sampler_error_collection(self):
        """Test that sampler errors are properly collected."""
        failing_sampler = MockRethinkSampler(should_fail=True)
        
        agent = ChessRethinkAgent(
            sampler=failing_sampler,
            prompt_template=prompts.PromptTemplate.NO_LEGAL_ACTIONS_RETHINK_APPENDED,
            data_collection_enabled=True,
            data_collection_callback=self.data_collection_callback
        )
        
        result = agent(self.observation, self.configuration)
        
        # Verify error handling
        self.assertEqual(result['submission'], ERROR_ACTION_INT)
        
        # Verify error data collection
        self.assertEqual(len(self.collected_events), 1)
        event = self.collected_events[0]
        self.assertEqual(event['event_type'], 'move_made')
        
        move_data = event['data']
        self.assertEqual(move_data['error_type'], 'sampler_error')
        self.assertIsNotNone(move_data['error_message'])
    
    def test_rethink_agent_enable_disable_data_collection(self):
        """Test enabling and disabling data collection dynamically."""
        agent = ChessRethinkAgent(
            sampler=self.mock_sampler,
            prompt_template=prompts.PromptTemplate.NO_LEGAL_ACTIONS_RETHINK_APPENDED
        )
        
        # Initially disabled
        agent(self.observation, self.configuration)
        self.assertEqual(len(self.collected_events), 0)
        
        # Enable data collection
        agent.enable_data_collection(self.data_collection_callback)
        agent(self.observation, self.configuration)
        self.assertGreater(len(self.collected_events), 0)
        
        # Disable data collection
        events_count = len(self.collected_events)
        agent.disable_data_collection()
        agent(self.observation, self.configuration)
        self.assertEqual(len(self.collected_events), events_count)  # No new events


class TestAgentCompatibility(unittest.TestCase):
    """Test that agents maintain compatibility with existing behavior."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.game = pyspiel.load_game("chess")
        self.state = self.game.new_initial_state()
        
        self.observation = {
            "serializedGameAndState": pyspiel.serialize_game_and_state(
                self.game, self.state
            ),
            "legalActions": list(self.state.legal_actions())
        }
        self.configuration = {}
    
    def test_llm_agent_backward_compatibility(self):
        """Test that ChessLLMAgent maintains backward compatibility."""
        # Create agent with old interface (no data collection params)
        agent = ChessLLMAgent(
            model=MockModel("e4"),
            prompt_builder=default_chess_prompt_builder,
            response_parser=default_response_parser
        )
        
        # Should work exactly as before
        result = agent(self.observation, self.configuration)
        
        self.assertNotEqual(result['submission'], INVALID_ACTION)
        self.assertEqual(result['actionString'], 'e4')
        self.assertFalse(agent.data_collection_enabled)
        self.assertIsNone(agent.data_collection_callback)
    
    def test_rethink_agent_backward_compatibility(self):
        """Test that ChessRethinkAgent maintains backward compatibility."""
        # Create agent with old interface (no data collection params)
        agent = ChessRethinkAgent(
            sampler=MockRethinkSampler("e4"),
            prompt_template=prompts.PromptTemplate.NO_LEGAL_ACTIONS_RETHINK_APPENDED
        )
        
        # Should work exactly as before
        result = agent(self.observation, self.configuration)
        
        self.assertNotEqual(result['submission'], INVALID_ACTION)
        self.assertEqual(result['actionString'], 'e4')
        self.assertFalse(agent.data_collection_enabled)
        self.assertIsNone(agent.data_collection_callback)


if __name__ == '__main__':
    unittest.main()