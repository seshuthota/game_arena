"""
Tests for tournament integration utilities.

Tests verify that tournament data collection integration works correctly
with the Game Arena harness and provides comprehensive data capture.
"""

import asyncio
import unittest
from unittest.mock import Mock, MagicMock, patch
import tempfile
import os
from typing import Dict, Any

from .tournament_integration import (
    TournamentDataCollector,
    TournamentConfig,
    create_tournament_collector,
    create_demo_players,
    determine_game_outcome,
    enable_agent_data_collection
)
from .models import PlayerInfo, GameOutcome
from game_arena.harness.agent import ChessLLMAgent, default_chess_prompt_builder, default_response_parser

import pyspiel


class MockModel:
    """Mock model for testing."""
    
    def __init__(self, response_text: str = "e4"):
        self.response_text = response_text
        self.call_count = 0
    
    def generate_with_text_input(self, model_input):
        self.call_count += 1
        mock_response = Mock()
        mock_response.main_response = self.response_text
        return mock_response


class TestTournamentIntegration(unittest.TestCase):
    """Test tournament integration functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.db_path = self.temp_db.name
        
        self.config = TournamentConfig(
            enabled=True,
            storage_backend="sqlite",
            database_path=self.db_path,
            tournament_name="Test Tournament",
            async_processing=False  # Synchronous for testing
        )
    
    def tearDown(self):
        """Clean up test fixtures."""
        try:
            os.unlink(self.db_path)
        except:
            pass
    
    async def test_tournament_collector_initialization(self):
        """Test that tournament collector initializes correctly."""
        collector = TournamentDataCollector(self.config)
        
        # Should initialize without errors
        await collector.initialize()
        
        # Verify components are created
        self.assertIsNotNone(collector.storage_manager)
        self.assertIsNotNone(collector.game_collector)
        self.assertIsNotNone(collector.tournament_start_time)
        
        await collector.shutdown()
    
    async def test_tournament_collector_disabled(self):
        """Test that tournament collector works when disabled."""
        disabled_config = TournamentConfig(enabled=False)
        collector = TournamentDataCollector(disabled_config)
        
        # Should initialize quickly when disabled
        await collector.initialize()
        
        # Components should not be created
        self.assertIsNone(collector.storage_manager)
        self.assertIsNone(collector.game_collector)
        
        await collector.shutdown()
    
    async def test_agent_wrapping(self):
        """Test that agents are properly wrapped for data collection."""
        collector = TournamentDataCollector(self.config)
        await collector.initialize()
        
        try:
            # Create test agent
            mock_model = MockModel("e4")
            agent = ChessLLMAgent(
                model=mock_model,
                prompt_builder=default_chess_prompt_builder,
                response_parser=default_response_parser
            )
            
            # Create player info
            player_info = PlayerInfo(
                player_id="test_player",
                model_name="test_model",
                model_provider="test",
                agent_type="ChessLLMAgent"
            )
            
            # Wrap agent
            wrapped_agent = collector.wrap_agent(agent, player_info, "test_agent")
            
            # Verify wrapping
            self.assertNotEqual(wrapped_agent, agent)  # Should be wrapped
            self.assertEqual(len(collector.wrapped_agents), 1)
            self.assertIn("test_agent", collector.wrapped_agents)
            
        finally:
            await collector.shutdown()
    
    async def test_game_lifecycle(self):
        """Test complete game lifecycle with data collection."""
        collector = TournamentDataCollector(self.config)
        await collector.initialize()
        
        try:
            # Create players
            players = create_demo_players("Player 1", "Player 2", "Model A", "Model B")
            
            # Start game
            game_id = collector.start_game("Test Game", players, {"test": "metadata"})
            self.assertIsNotNone(game_id)
            self.assertEqual(len(collector.active_games), 1)
            
            # End game
            from .models import GameResult, TerminationReason
            outcome = GameOutcome(
                result=GameResult.WHITE_WINS,
                winner=1,
                termination=TerminationReason.CHECKMATE
            )
            
            success = collector.end_game(game_id, outcome, "final_fen", 25)
            self.assertTrue(success)
            self.assertEqual(len(collector.active_games), 0)
            self.assertEqual(collector.games_completed, 1)
            self.assertEqual(collector.total_moves_collected, 25)
            
        finally:
            await collector.shutdown()
    
    def test_create_demo_players(self):
        """Test demo player creation utility."""
        players = create_demo_players("Alice", "Bob", "GPT-4", "Claude")
        
        self.assertEqual(len(players), 2)
        self.assertIn(0, players)  # Black
        self.assertIn(1, players)  # White
        
        # Check player 0 (Black)
        player0 = players[0]
        self.assertEqual(player0.agent_config["player_name"], "Alice")
        self.assertEqual(player0.model_name, "GPT-4")
        self.assertEqual(player0.player_id, "demo_alice")
        
        # Check player 1 (White)
        player1 = players[1]
        self.assertEqual(player1.agent_config["player_name"], "Bob")
        self.assertEqual(player1.model_name, "Claude")
        self.assertEqual(player1.player_id, "demo_bob")
    
    def test_determine_game_outcome(self):
        """Test game outcome determination from pyspiel state."""
        # Create a chess game
        game = pyspiel.load_game("chess")
        
        # Test non-terminal state
        state = game.new_initial_state()
        outcome = determine_game_outcome(state)
        self.assertIsNone(outcome)
        
        # Mock terminal state with white win
        terminal_state = Mock()
        terminal_state.is_terminal.return_value = True
        terminal_state.returns.return_value = [0, 1]  # White wins
        terminal_state.to_string.return_value = "final_position"
        
        outcome = determine_game_outcome(terminal_state)
        self.assertIsNotNone(outcome)
        from .models import GameResult
        self.assertEqual(outcome.result, GameResult.WHITE_WINS)
        self.assertEqual(outcome.winner, 1)
        
        # Mock terminal state with black win
        terminal_state.returns.return_value = [1, 0]  # Black wins
        outcome = determine_game_outcome(terminal_state)
        self.assertEqual(outcome.result, GameResult.BLACK_WINS)
        self.assertEqual(outcome.winner, 0)
        
        # Mock terminal state with draw
        terminal_state.returns.return_value = [0, 0]  # Draw
        outcome = determine_game_outcome(terminal_state)
        self.assertEqual(outcome.result, GameResult.DRAW)
        self.assertIsNone(outcome.winner)
    
    def test_factory_function(self):
        """Test tournament collector factory function."""
        collector = create_tournament_collector(
            tournament_name="Factory Test",
            storage_backend="sqlite",
            database_path=self.db_path
        )
        
        self.assertIsInstance(collector, TournamentDataCollector)
        self.assertEqual(collector.config.tournament_name, "Factory Test")
        self.assertEqual(collector.config.storage_backend, "sqlite")
        self.assertEqual(collector.config.database_path, self.db_path)
    
    def test_enable_agent_data_collection(self):
        """Test direct agent data collection enablement."""
        mock_model = MockModel("e4")
        agent = ChessLLMAgent(
            model=mock_model,
            prompt_builder=default_chess_prompt_builder,
            response_parser=default_response_parser
        )
        
        callback_called = False
        def test_callback(event_type, data):
            nonlocal callback_called
            callback_called = True
        
        # Enable data collection
        enable_agent_data_collection(agent, test_callback)
        
        # Verify data collection is enabled
        self.assertTrue(agent.data_collection_enabled)
        self.assertEqual(agent.data_collection_callback, test_callback)
    
    async def test_tournament_stats(self):
        """Test tournament statistics collection."""
        collector = TournamentDataCollector(self.config)
        await collector.initialize()
        
        try:
            # Get initial stats
            stats = collector.get_tournament_stats()
            
            self.assertEqual(stats['tournament_name'], "Test Tournament")
            self.assertEqual(stats['games_completed'], 0)
            self.assertEqual(stats['total_moves_collected'], 0)
            self.assertEqual(stats['active_games'], 0)
            self.assertEqual(stats['wrapped_agents'], 0)
            
            # Add some activity
            players = create_demo_players()
            game_id = collector.start_game("Test Game", players)
            
            # Create and wrap an agent
            mock_model = MockModel("e4")
            agent = ChessLLMAgent(
                model=mock_model,
                prompt_builder=default_chess_prompt_builder,
                response_parser=default_response_parser
            )
            collector.wrap_agent(agent, players[0], "test_agent")
            
            # Get updated stats
            stats = collector.get_tournament_stats()
            self.assertEqual(stats['active_games'], 1)
            self.assertEqual(stats['wrapped_agents'], 1)
            
        finally:
            await collector.shutdown()


class TestTournamentIntegrationAsync(unittest.IsolatedAsyncioTestCase):
    """Async tests for tournament integration."""
    
    async def test_full_tournament_workflow(self):
        """Test a complete tournament workflow with data collection."""
        # Create temporary database
        temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_db.close()
        db_path = temp_db.name
        
        try:
            # Create tournament collector
            collector = create_tournament_collector(
                tournament_name="Full Workflow Test",
                storage_backend="sqlite",
                database_path=db_path,
                async_processing=False
            )
            
            await collector.initialize()
            
            # Create players and agents
            players = create_demo_players("Alice", "Bob", "GPT-4", "Claude")
            
            mock_model1 = MockModel("e4")
            mock_model2 = MockModel("d4")
            
            agent1 = ChessLLMAgent(
                model=mock_model1,
                prompt_builder=default_chess_prompt_builder,
                response_parser=default_response_parser
            )
            
            agent2 = ChessLLMAgent(
                model=mock_model2,
                prompt_builder=default_chess_prompt_builder,
                response_parser=default_response_parser
            )
            
            # Wrap agents
            wrapped_agent1 = collector.wrap_agent(agent1, players[0], "alice_agent")
            wrapped_agent2 = collector.wrap_agent(agent2, players[1], "bob_agent")
            
            # Start game
            game_id = collector.start_game("Alice vs Bob", players)
            collector.set_game_id_for_agents(game_id)
            
            # Simulate some moves (simplified)
            # In a real scenario, these would be actual game moves
            
            # End game
            from game_arena.storage.models import GameResult, TerminationReason
            outcome = GameOutcome(
                result=GameResult.WHITE_WINS,
                winner=1,
                termination=TerminationReason.RESIGNATION
            )
            
            collector.end_game(game_id, outcome, "final_fen", 30)
            
            # Verify final stats
            stats = collector.get_tournament_stats()
            self.assertEqual(stats['games_completed'], 1)
            self.assertEqual(stats['total_moves_collected'], 30)
            
            await collector.shutdown()
            
        finally:
            try:
                os.unlink(db_path)
            except:
                pass


if __name__ == '__main__':
    unittest.main()