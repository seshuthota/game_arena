"""
Comprehensive unit tests for player statistics API functionality.

This module tests the player statistics endpoint including detailed analytics,
move analysis, performance metrics, and edge cases.
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient

from game_arena.storage.models import GameRecord

from .main import create_app


@pytest.fixture
def mock_storage_manager():
    """Create a mock storage manager for testing."""
    mock = AsyncMock()
    mock.initialize = AsyncMock()
    mock.shutdown = AsyncMock()
    mock.get_moves = AsyncMock()
    return mock


@pytest.fixture
def mock_query_engine(mock_storage_manager):
    """Create a mock query engine for testing."""
    mock = AsyncMock()
    mock.storage_manager = mock_storage_manager
    mock.get_games_by_players = AsyncMock()
    mock.get_player_winrate = AsyncMock()
    mock.get_move_accuracy_stats = AsyncMock()
    return mock


@pytest.fixture
def player_stats_test_app(mock_storage_manager, mock_query_engine):
    """Create a test FastAPI application for player statistics testing."""
    app = create_app()
    
    # Override the lifespan to avoid actual storage initialization
    app.state.storage_manager = mock_storage_manager
    app.state.query_engine = mock_query_engine
    
    return app


@pytest.fixture
def player_stats_client(player_stats_test_app):
    """Create a test client for player statistics testing."""
    return TestClient(player_stats_test_app)


@pytest.fixture
def sample_player_games_and_moves():
    """Create comprehensive sample games and moves for player statistics testing."""
    base_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    player_id = "alice_gpt4"
    
    # Create sample games
    games = []
    all_moves = []
    
    # Game 1: Alice wins as White
    game1 = MagicMock(spec=GameRecord)
    game1.game_id = "game1_alice_win"
    game1.start_time = base_time
    game1.end_time = base_time + timedelta(hours=1, minutes=30)
    game1.total_moves = 60
    game1.is_completed = True
    game1.players = {
        "0": MagicMock(
            player_id="alice_gpt4",
            model_name="gpt-4",
            model_provider="openai",
            elo_rating=1600.0
        ),
        "1": MagicMock(
            player_id="bob_claude",
            model_name="claude-3",
            model_provider="anthropic",
            elo_rating=1550.0
        )
    }
    game1.outcome = MagicMock()
    game1.outcome.result = MagicMock()
    game1.outcome.result.value = "WHITE_WINS"
    games.append(game1)
    
    # Sample moves for game1 - Alice's moves (player 0)
    game1_moves = []
    for i in range(30):  # Alice made 30 moves (half of 60 total)
        move = MagicMock()
        move.game_id = "game1_alice_win"
        move.move_number = i + 1
        move.player = 0  # Alice is player 0
        move.is_legal = True if i < 28 else False  # 2 illegal moves
        move.parsing_success = True if i < 29 else False  # 1 parsing failure
        move.thinking_time_ms = 2000 + (i * 100)  # Varying thinking time
        move.api_call_time_ms = 500
        move.blunder_flag = True if i in [10, 20] else False  # 2 blunders
        game1_moves.extend([move])
    all_moves.extend(game1_moves)
    
    # Game 2: Alice loses as Black
    game2 = MagicMock(spec=GameRecord)
    game2.game_id = "game2_alice_loss"
    game2.start_time = base_time + timedelta(days=1)
    game2.end_time = base_time + timedelta(days=1, hours=2)
    game2.total_moves = 80
    game2.is_completed = True
    game2.players = {
        "0": MagicMock(
            player_id="charlie_gemini",
            model_name="gemini-pro",
            model_provider="google",
            elo_rating=1650.0
        ),
        "1": MagicMock(
            player_id="alice_gpt4",
            model_name="gpt-4", 
            model_provider="openai",
            elo_rating=1600.0
        )
    }
    game2.outcome = MagicMock()
    game2.outcome.result = MagicMock()
    game2.outcome.result.value = "WHITE_WINS"  # Charlie wins, Alice loses
    games.append(game2)
    
    # Sample moves for game2 - Alice's moves (player 1)
    game2_moves = []
    for i in range(40):  # Alice made 40 moves
        move = MagicMock()
        move.game_id = "game2_alice_loss"
        move.move_number = i + 1
        move.player = 1  # Alice is player 1
        move.is_legal = True if i < 38 else False  # 2 illegal moves
        move.parsing_success = True
        move.thinking_time_ms = 1800 + (i * 50)
        move.api_call_time_ms = 400
        move.blunder_flag = True if i in [15, 25, 35] else False  # 3 blunders
        game2_moves.extend([move])
    all_moves.extend(game2_moves)
    
    # Game 3: Alice draws
    game3 = MagicMock(spec=GameRecord)
    game3.game_id = "game3_alice_draw"
    game3.start_time = base_time + timedelta(days=2)
    game3.end_time = base_time + timedelta(days=2, hours=3)
    game3.total_moves = 120
    game3.is_completed = True
    game3.players = {
        "0": MagicMock(
            player_id="alice_gpt4",
            model_name="gpt-4",
            model_provider="openai",
            elo_rating=1600.0
        ),
        "1": MagicMock(
            player_id="david_llama",
            model_name="llama-2",
            model_provider="meta",
            elo_rating=1580.0
        )
    }
    game3.outcome = MagicMock()
    game3.outcome.result = MagicMock()
    game3.outcome.result.value = "DRAW"
    games.append(game3)
    
    # Sample moves for game3 - Alice's moves (player 0)
    game3_moves = []
    for i in range(60):  # Alice made 60 moves
        move = MagicMock()
        move.game_id = "game3_alice_draw"
        move.move_number = i + 1
        move.player = 0  # Alice is player 0
        move.is_legal = True  # All legal moves in this game
        move.parsing_success = True
        move.thinking_time_ms = 2200 + (i * 25)
        move.api_call_time_ms = 450
        move.blunder_flag = True if i == 30 else False  # 1 blunder
        game3_moves.extend([move])
    all_moves.extend(game3_moves)
    
    return games, all_moves


class TestPlayerStatisticsBasic:
    """Test cases for basic player statistics functionality."""
    
    @pytest.mark.asyncio
    async def test_player_statistics_basic(self, player_stats_client, mock_query_engine, sample_player_games_and_moves):
        """Test basic player statistics retrieval."""
        games, all_moves = sample_player_games_and_moves
        mock_query_engine.get_games_by_players.return_value = games
        
        # Mock move data for each game
        def mock_get_moves(game_id):
            return [move for move in all_moves if move.game_id == game_id]
        
        mock_query_engine.storage_manager.get_moves.side_effect = mock_get_moves
        
        response = player_stats_client.get("/api/players/alice_gpt4/statistics")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check response structure
        assert "statistics" in data
        assert "success" in data
        assert data["success"] is True
        
        stats = data["statistics"]
        
        # Check required fields
        required_fields = [
            "player_id", "model_name", "total_games", "wins", "losses", "draws",
            "win_rate", "average_game_duration", "total_moves", "legal_moves",
            "illegal_moves", "move_accuracy", "parsing_success_rate",
            "average_thinking_time", "blunders", "elo_rating"
        ]
        
        for field in required_fields:
            assert field in stats, f"Missing field: {field}"
    
    @pytest.mark.asyncio
    async def test_player_statistics_calculations(self, player_stats_client, mock_query_engine, sample_player_games_and_moves):
        """Test that player statistics are calculated correctly."""
        games, all_moves = sample_player_games_and_moves
        mock_query_engine.get_games_by_players.return_value = games
        
        def mock_get_moves(game_id):
            return [move for move in all_moves if move.game_id == game_id]
        
        mock_query_engine.storage_manager.get_moves.side_effect = mock_get_moves
        
        # Set up QueryEngine method returns to avoid interfering with calculations
        mock_query_engine.get_player_winrate.return_value = None
        mock_query_engine.get_move_accuracy_stats.side_effect = Exception("Not available")
        
        response = player_stats_client.get("/api/players/alice_gpt4/statistics")
        
        assert response.status_code == 200
        data = response.json()
        
        stats = data["statistics"]
        
        # Verify basic counts
        assert stats["player_id"] == "alice_gpt4"
        assert stats["model_name"] == "gpt-4"
        assert stats["total_games"] == 3
        assert stats["wins"] == 1  # Won game 1
        assert stats["losses"] == 1  # Lost game 2
        assert stats["draws"] == 1  # Drew game 3
        assert stats["win_rate"] == 33.33  # 1/3 * 100
        
        # Verify move counts (30 + 40 + 60 = 130 total moves)
        assert stats["total_moves"] == 130
        assert stats["legal_moves"] == 126  # 4 illegal moves total (2+2+0)
        assert stats["illegal_moves"] == 4
        assert stats["move_accuracy"] == 96.92  # 126/130 * 100
        
        # Verify other metrics
        assert stats["blunders"] == 6  # 2 + 3 + 1
        assert stats["parsing_success_rate"] == 99.23  # 129/130 * 100 (1 parsing failure)
        assert stats["elo_rating"] == 1600.0


class TestPlayerStatisticsAdvanced:
    """Test cases for advanced player statistics functionality."""
    
    @pytest.mark.asyncio
    async def test_with_query_engine_integration(self, player_stats_client, mock_query_engine, sample_player_games_and_moves):
        """Test integration with QueryEngine methods."""
        games, all_moves = sample_player_games_and_moves
        mock_query_engine.get_games_by_players.return_value = games
        
        def mock_get_moves(game_id):
            return [move for move in all_moves if move.game_id == game_id]
        
        mock_query_engine.storage_manager.get_moves.side_effect = mock_get_moves
        
        # Mock QueryEngine methods
        mock_query_engine.get_player_winrate.return_value = 35.5  # Different from calculated
        
        # Mock accuracy stats
        mock_accuracy_stats = MagicMock()
        mock_accuracy_stats.total_moves = 150
        mock_accuracy_stats.legal_moves = 145
        mock_accuracy_stats.illegal_moves = 5
        mock_query_engine.get_move_accuracy_stats.return_value = mock_accuracy_stats
        
        response = player_stats_client.get("/api/players/alice_gpt4/statistics")
        
        assert response.status_code == 200
        data = response.json()
        
        stats = data["statistics"]
        
        # Should use QueryEngine win rate
        assert stats["win_rate"] == 35.5
        
        # Should use QueryEngine move stats
        assert stats["total_moves"] == 150
        assert stats["legal_moves"] == 145
        assert stats["illegal_moves"] == 5
        assert stats["move_accuracy"] == 96.67  # 145/150 * 100
    
    @pytest.mark.asyncio
    async def test_thinking_time_calculation(self, player_stats_client, mock_query_engine, sample_player_games_and_moves):
        """Test average thinking time calculation."""
        games, all_moves = sample_player_games_and_moves
        mock_query_engine.get_games_by_players.return_value = games
        
        def mock_get_moves(game_id):
            return [move for move in all_moves if move.game_id == game_id]
        
        mock_query_engine.storage_manager.get_moves.side_effect = mock_get_moves
        
        response = player_stats_client.get("/api/players/alice_gpt4/statistics")
        
        assert response.status_code == 200
        data = response.json()
        
        stats = data["statistics"]
        
        # Verify thinking time is calculated (should be > 0)
        assert stats["average_thinking_time"] > 0
        assert isinstance(stats["average_thinking_time"], (int, float))
    
    @pytest.mark.asyncio
    async def test_game_duration_calculation(self, player_stats_client, mock_query_engine, sample_player_games_and_moves):
        """Test average game duration calculation."""
        games, all_moves = sample_player_games_and_moves
        mock_query_engine.get_games_by_players.return_value = games
        
        def mock_get_moves(game_id):
            return [move for move in all_moves if move.game_id == game_id]
        
        mock_query_engine.storage_manager.get_moves.side_effect = mock_get_moves
        
        response = player_stats_client.get("/api/players/alice_gpt4/statistics")
        
        assert response.status_code == 200
        data = response.json()
        
        stats = data["statistics"]
        
        # Verify average game duration calculation
        # Game 1: 1.5 hours = 90 minutes
        # Game 2: 2 hours = 120 minutes  
        # Game 3: 3 hours = 180 minutes
        # Average: (90 + 120 + 180) / 3 = 130 minutes
        assert stats["average_game_duration"] == 130.0


class TestPlayerStatisticsEdgeCases:
    """Test cases for player statistics edge cases."""
    
    @pytest.mark.asyncio
    async def test_player_not_found(self, player_stats_client, mock_query_engine):
        """Test behavior when player is not found."""
        mock_query_engine.get_games_by_players.return_value = []
        
        response = player_stats_client.get("/api/players/nonexistent_player/statistics")
        
        assert response.status_code == 404
        data = response.json()
        assert "Player 'nonexistent_player' not found" in data["detail"]
    
    @pytest.mark.asyncio
    async def test_player_with_no_completed_games(self, player_stats_client, mock_query_engine):
        """Test player statistics with only ongoing games."""
        # Create an ongoing game
        ongoing_game = MagicMock(spec=GameRecord)
        ongoing_game.game_id = "ongoing_game"
        ongoing_game.start_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        ongoing_game.end_time = None
        ongoing_game.total_moves = 20
        ongoing_game.is_completed = False
        ongoing_game.outcome = None
        ongoing_game.players = {
            "0": MagicMock(
                player_id="alice_gpt4",
                model_name="gpt-4",
                model_provider="openai",
                elo_rating=1500.0
            ),
            "1": MagicMock(player_id="opponent", model_name="other", model_provider="other")
        }
        
        mock_query_engine.get_games_by_players.return_value = [ongoing_game]
        mock_query_engine.storage_manager.get_moves.return_value = []
        
        # Set up QueryEngine method returns
        mock_query_engine.get_player_winrate.return_value = None
        mock_query_engine.get_move_accuracy_stats.side_effect = Exception("Not available")
        
        response = player_stats_client.get("/api/players/alice_gpt4/statistics")
        
        assert response.status_code == 200
        data = response.json()
        
        stats = data["statistics"]
        
        # Should handle ongoing games gracefully
        assert stats["total_games"] == 1
        assert stats["wins"] == 0
        assert stats["losses"] == 0
        assert stats["draws"] == 0
        assert stats["win_rate"] == 0.0
        assert stats["average_game_duration"] == 0.0  # No completed games
    
    @pytest.mark.asyncio
    async def test_missing_move_data(self, player_stats_client, mock_query_engine, sample_player_games_and_moves):
        """Test handling when move data is missing."""
        games, _ = sample_player_games_and_moves
        mock_query_engine.get_games_by_players.return_value = games
        
        # Simulate missing move data
        mock_query_engine.storage_manager.get_moves.side_effect = Exception("Move data not available")
        
        response = player_stats_client.get("/api/players/alice_gpt4/statistics")
        
        assert response.status_code == 200
        data = response.json()
        
        stats = data["statistics"]
        
        # Should fall back to approximation
        assert stats["total_games"] == 3
        assert stats["total_moves"] > 0  # Should have approximated move count
        assert stats["legal_moves"] == stats["total_moves"]  # Assumes all legal when approximating
    
    @pytest.mark.asyncio
    async def test_query_engine_method_failures(self, player_stats_client, mock_query_engine, sample_player_games_and_moves):
        """Test graceful handling when QueryEngine methods fail."""
        games, all_moves = sample_player_games_and_moves
        mock_query_engine.get_games_by_players.return_value = games
        
        def mock_get_moves(game_id):
            return [move for move in all_moves if move.game_id == game_id]
        
        mock_query_engine.storage_manager.get_moves.side_effect = mock_get_moves
        
        # Make QueryEngine methods fail
        mock_query_engine.get_player_winrate.side_effect = Exception("Win rate calculation failed")
        mock_query_engine.get_move_accuracy_stats.side_effect = Exception("Accuracy calculation failed")
        
        response = player_stats_client.get("/api/players/alice_gpt4/statistics")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should still return statistics using fallback calculations
        stats = data["statistics"]
        assert stats["total_games"] == 3
        assert "win_rate" in stats
        assert "move_accuracy" in stats
    
    @pytest.mark.asyncio
    async def test_database_error_handling(self, player_stats_client, mock_query_engine):
        """Test error handling when database operations fail."""
        mock_query_engine.get_games_by_players.side_effect = Exception("Database connection failed")
        
        response = player_stats_client.get("/api/players/alice_gpt4/statistics")
        
        # The current implementation returns 404 when get_games_by_players fails
        # This could be improved to distinguish between "player not found" and "database error"
        assert response.status_code == 404
        data = response.json()
        assert "Player 'alice_gpt4' not found" in data["detail"]


class TestPlayerStatisticsHelperFunctions:
    """Test cases for player statistics helper functions."""
    
    @pytest.mark.asyncio
    async def test_detailed_player_statistics_generation(self, mock_query_engine, sample_player_games_and_moves):
        """Test the detailed player statistics generation helper function."""
        from .routes.players import _generate_detailed_player_statistics
        
        games, all_moves = sample_player_games_and_moves
        mock_query_engine.get_games_by_players.return_value = games
        
        def mock_get_moves(game_id):
            return [move for move in all_moves if move.game_id == game_id]
        
        mock_query_engine.storage_manager.get_moves.side_effect = mock_get_moves
        
        stats = await _generate_detailed_player_statistics(mock_query_engine, "alice_gpt4")
        
        assert stats is not None
        assert stats.player_id == "alice_gpt4"
        assert stats.total_games == 3
        assert stats.wins == 1
        assert stats.losses == 1
        assert stats.draws == 1
        assert 0 <= stats.win_rate <= 100
        assert stats.total_moves > 0
        assert stats.legal_moves >= 0
        assert stats.illegal_moves >= 0
        assert 0 <= stats.move_accuracy <= 100
        assert 0 <= stats.parsing_success_rate <= 100
    
    @pytest.mark.asyncio
    async def test_statistics_with_empty_games(self, mock_query_engine):
        """Test statistics generation with empty games list."""
        from .routes.players import _generate_detailed_player_statistics
        
        mock_query_engine.get_games_by_players.return_value = []
        
        stats = await _generate_detailed_player_statistics(mock_query_engine, "nonexistent_player")
        
        assert stats is None