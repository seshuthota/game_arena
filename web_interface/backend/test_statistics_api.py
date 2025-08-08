"""
Comprehensive unit tests for statistics API functionality.

This module tests the statistics overview endpoint including aggregate
calculations, data accuracy, and edge cases.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient

from game_arena.storage.models import GameRecord, GameResult, TerminationReason

from .main import create_app


@pytest.fixture
def mock_storage_manager():
    """Create a mock storage manager for testing."""
    mock = AsyncMock()
    mock.initialize = AsyncMock()
    mock.shutdown = AsyncMock()
    return mock


@pytest.fixture
def mock_query_engine():
    """Create a mock query engine for testing."""
    mock = AsyncMock()
    mock.storage_manager = AsyncMock()
    return mock


@pytest.fixture
def statistics_test_app(mock_storage_manager, mock_query_engine):
    """Create a test FastAPI application for statistics testing."""
    app = create_app()
    
    # Override the lifespan to avoid actual storage initialization
    app.state.storage_manager = mock_storage_manager
    app.state.query_engine = mock_query_engine
    
    return app


@pytest.fixture
def statistics_client(statistics_test_app):
    """Create a test client for statistics testing."""
    return TestClient(statistics_test_app)


@pytest.fixture
def sample_statistics_games():
    """Create comprehensive sample games for statistics testing."""
    base_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    
    games = []
    game_configs = [
        {
            "game_id": "completed_game_1",
            "is_completed": True,
            "total_moves": 45,
            "start_time": base_time,
            "end_time": base_time.replace(hour=13, minute=30),  # 90 minutes
            "players": {
                "0": {"player_id": "alice_gpt4", "model_name": "gpt-4", "model_provider": "openai"},
                "1": {"player_id": "bob_claude", "model_name": "claude-3", "model_provider": "anthropic"}
            },
            "result": "WHITE_WINS",
            "termination": "CHECKMATE"
        },
        {
            "game_id": "completed_game_2",
            "is_completed": True,
            "total_moves": 32,
            "start_time": base_time.replace(day=2),
            "end_time": base_time.replace(day=2, hour=13),  # 60 minutes
            "players": {
                "0": {"player_id": "charlie_gemini", "model_name": "gemini-pro", "model_provider": "google"},
                "1": {"player_id": "alice_gpt4", "model_name": "gpt-4", "model_provider": "openai"}
            },
            "result": "BLACK_WINS",
            "termination": "RESIGNATION"
        },
        {
            "game_id": "completed_game_3",
            "is_completed": True,
            "total_moves": 67,
            "start_time": base_time.replace(day=3),
            "end_time": base_time.replace(day=3, hour=14),  # 120 minutes
            "players": {
                "0": {"player_id": "bob_claude", "model_name": "claude-3", "model_provider": "anthropic"},
                "1": {"player_id": "david_llama", "model_name": "llama-2", "model_provider": "meta"}
            },
            "result": "DRAW",
            "termination": "STALEMATE"
        },
        {
            "game_id": "ongoing_game_1",
            "is_completed": False,
            "total_moves": 23,
            "start_time": base_time.replace(day=4),
            "end_time": None,
            "players": {
                "0": {"player_id": "alice_gpt4", "model_name": "gpt-4", "model_provider": "openai"},
                "1": {"player_id": "eve_mixtral", "model_name": "mixtral-8x7b", "model_provider": "mistral"}
            },
            "result": None,
            "termination": None
        },
        {
            "game_id": "short_game",
            "is_completed": True,
            "total_moves": 8,  # Shortest game
            "start_time": base_time.replace(day=5),
            "end_time": base_time.replace(day=5, minute=15),  # 15 minutes
            "players": {
                "0": {"player_id": "alice_gpt4", "model_name": "gpt-4", "model_provider": "openai"},
                "1": {"player_id": "bob_claude", "model_name": "claude-3", "model_provider": "anthropic"}
            },
            "result": "WHITE_WINS",
            "termination": "CHECKMATE"
        }
    ]
    
    for config in game_configs:
        game = MagicMock(spec=GameRecord)
        game.game_id = config["game_id"]
        game.is_completed = config["is_completed"]
        game.total_moves = config["total_moves"]
        game.start_time = config["start_time"]
        game.end_time = config["end_time"]
        
        # Mock players
        game.players = {}
        for position, player_info in config["players"].items():
            game.players[position] = MagicMock(
                player_id=player_info["player_id"],
                model_name=player_info["model_name"],
                model_provider=player_info["model_provider"]
            )
        
        # Mock outcome
        if config["result"] and config["termination"]:
            game.outcome = MagicMock()
            game.outcome.result = MagicMock()
            game.outcome.result.value = config["result"]
            game.outcome.termination = MagicMock()
            game.outcome.termination.value = config["termination"]
        else:
            game.outcome = None
        
        games.append(game)
    
    return games


class TestStatisticsOverview:
    """Test cases for statistics overview functionality."""
    
    @pytest.mark.asyncio
    async def test_statistics_overview_basic(self, statistics_client, mock_query_engine, sample_statistics_games):
        """Test basic statistics overview calculation."""
        mock_query_engine.query_games_advanced.return_value = sample_statistics_games
        
        response = statistics_client.get("/api/statistics/overview")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check response structure
        assert "statistics" in data
        assert "success" in data
        assert "timestamp" in data
        assert data["success"] is True
        
        stats = data["statistics"]
        
        # Verify basic counts
        assert stats["total_games"] == 5
        assert stats["completed_games"] == 4
        assert stats["ongoing_games"] == 1
        assert stats["total_players"] == 5  # alice, bob, charlie, david, eve
        
        # Verify total moves (45 + 32 + 67 + 23 + 8 = 175)
        assert stats["total_moves"] == 175
        
        # Verify averages
        assert stats["average_moves_per_game"] == 35.0  # 175 / 5
        # Average duration: (90 + 60 + 120 + 15) / 4 = 71.25 minutes
        assert stats["average_game_duration"] == 71.25
    
    @pytest.mark.asyncio
    async def test_statistics_games_by_result(self, statistics_client, mock_query_engine, sample_statistics_games):
        """Test games breakdown by result."""
        mock_query_engine.query_games_advanced.return_value = sample_statistics_games
        
        response = statistics_client.get("/api/statistics/overview")
        
        assert response.status_code == 200
        data = response.json()
        
        games_by_result = data["statistics"]["games_by_result"]
        
        # Check result counts
        assert games_by_result["white_wins"] == 2  # completed_game_1, short_game
        assert games_by_result["black_wins"] == 1  # completed_game_2
        assert games_by_result["draw"] == 1  # completed_game_3
        assert games_by_result["ongoing"] == 1  # ongoing_game_1
    
    @pytest.mark.asyncio
    async def test_statistics_games_by_termination(self, statistics_client, mock_query_engine, sample_statistics_games):
        """Test games breakdown by termination reason."""
        mock_query_engine.query_games_advanced.return_value = sample_statistics_games
        
        response = statistics_client.get("/api/statistics/overview")
        
        assert response.status_code == 200
        data = response.json()
        
        games_by_termination = data["statistics"]["games_by_termination"]
        
        # Check termination counts
        assert games_by_termination["checkmate"] == 2  # completed_game_1, short_game
        assert games_by_termination["resignation"] == 1  # completed_game_2
        assert games_by_termination["stalemate"] == 1  # completed_game_3
    
    @pytest.mark.asyncio
    async def test_statistics_most_active_player(self, statistics_client, mock_query_engine, sample_statistics_games):
        """Test most active player identification."""
        mock_query_engine.query_games_advanced.return_value = sample_statistics_games
        
        response = statistics_client.get("/api/statistics/overview")
        
        assert response.status_code == 200
        data = response.json()
        
        # alice_gpt4 appears in 3 games, others appear in 2 or fewer
        assert data["statistics"]["most_active_player"] == "alice_gpt4"
    
    @pytest.mark.asyncio
    async def test_statistics_longest_shortest_games(self, statistics_client, mock_query_engine, sample_statistics_games):
        """Test longest and shortest game identification."""
        mock_query_engine.query_games_advanced.return_value = sample_statistics_games
        
        response = statistics_client.get("/api/statistics/overview")
        
        assert response.status_code == 200
        data = response.json()
        
        stats = data["statistics"]
        
        # Longest game: completed_game_3 with 67 moves
        assert stats["longest_game_id"] == "completed_game_3"
        
        # Shortest game: short_game with 8 moves
        assert stats["shortest_game_id"] == "short_game"
    
    @pytest.mark.asyncio
    async def test_statistics_empty_database(self, statistics_client, mock_query_engine):
        """Test statistics with empty database."""
        mock_query_engine.query_games_advanced.return_value = []
        
        response = statistics_client.get("/api/statistics/overview")
        
        assert response.status_code == 200
        data = response.json()
        
        stats = data["statistics"]
        
        # All counts should be zero
        assert stats["total_games"] == 0
        assert stats["completed_games"] == 0
        assert stats["ongoing_games"] == 0
        assert stats["total_players"] == 0
        assert stats["total_moves"] == 0
        assert stats["average_moves_per_game"] == 0.0
        assert stats["average_game_duration"] == 0.0
        
        # Collections should be empty
        assert stats["games_by_result"] == {"white_wins": 0, "black_wins": 0, "draw": 0, "ongoing": 0}
        assert stats["games_by_termination"] == {}
        assert stats["most_active_player"] is None
        assert stats["longest_game_id"] is None
        assert stats["shortest_game_id"] is None
    
    @pytest.mark.asyncio
    async def test_statistics_single_game(self, statistics_client, mock_query_engine, sample_statistics_games):
        """Test statistics with single game."""
        single_game = [sample_statistics_games[0]]  # Just the first game
        mock_query_engine.query_games_advanced.return_value = single_game
        
        response = statistics_client.get("/api/statistics/overview")
        
        assert response.status_code == 200
        data = response.json()
        
        stats = data["statistics"]
        
        # Verify single game stats
        assert stats["total_games"] == 1
        assert stats["completed_games"] == 1
        assert stats["ongoing_games"] == 0
        assert stats["total_players"] == 2
        assert stats["total_moves"] == 45
        assert stats["average_moves_per_game"] == 45.0
        assert stats["average_game_duration"] == 90.0
        
        assert stats["longest_game_id"] == "completed_game_1"
        assert stats["shortest_game_id"] == "completed_game_1"
    
    @pytest.mark.asyncio
    async def test_statistics_games_without_duration(self, statistics_client, mock_query_engine):
        """Test statistics with games that have no duration data."""
        # Create game without end time
        game = MagicMock(spec=GameRecord)
        game.game_id = "no_duration_game"
        game.is_completed = False
        game.total_moves = 20
        game.start_time = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
        game.end_time = None
        game.players = {
            "0": MagicMock(player_id="player1", model_name="model1", model_provider="provider1"),
            "1": MagicMock(player_id="player2", model_name="model2", model_provider="provider2")
        }
        game.outcome = None
        
        mock_query_engine.query_games_advanced.return_value = [game]
        
        response = statistics_client.get("/api/statistics/overview")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should handle missing duration gracefully
        assert data["statistics"]["average_game_duration"] == 0.0
    
    @pytest.mark.asyncio
    async def test_statistics_error_handling(self, statistics_client, mock_query_engine):
        """Test error handling in statistics endpoint."""
        mock_query_engine.query_games_advanced.side_effect = Exception("Database error")
        
        response = statistics_client.get("/api/statistics/overview")
        
        assert response.status_code == 500
        data = response.json()
        assert "Failed to retrieve statistics" in data["detail"]
    
    @pytest.mark.asyncio
    async def test_statistics_filters_applied(self, statistics_client, mock_query_engine, sample_statistics_games):
        """Test that filters_applied is correctly set in response."""
        mock_query_engine.query_games_advanced.return_value = sample_statistics_games
        
        response = statistics_client.get("/api/statistics/overview")
        
        assert response.status_code == 200
        data = response.json()
        
        # No filters should be applied for overview
        assert "filters_applied" in data
        assert data["filters_applied"] == {}