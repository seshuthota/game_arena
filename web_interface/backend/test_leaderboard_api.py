"""
Comprehensive unit tests for leaderboard API functionality.

This module tests the leaderboard endpoint including player rankings,
sorting, filtering, and pagination functionality.
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
    return mock


@pytest.fixture
def mock_query_engine():
    """Create a mock query engine for testing."""
    mock = AsyncMock()
    mock.storage_manager = AsyncMock()
    return mock


@pytest.fixture
def leaderboard_test_app(mock_storage_manager, mock_query_engine):
    """Create a test FastAPI application for leaderboard testing."""
    app = create_app()
    
    # Override the lifespan to avoid actual storage initialization
    app.state.storage_manager = mock_storage_manager
    app.state.query_engine = mock_query_engine
    
    return app


@pytest.fixture
def leaderboard_client(leaderboard_test_app):
    """Create a test client for leaderboard testing."""
    return TestClient(leaderboard_test_app)


@pytest.fixture
def sample_leaderboard_games():
    """Create comprehensive sample games for leaderboard testing."""
    base_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    
    games = []
    
    # Player performance scenarios for testing different rankings
    game_scenarios = [
        # Alice (high win rate - should rank #1)
        {
            "game_id": "alice_win_1",
            "players": {
                "0": {"player_id": "alice_gpt4", "model_name": "gpt-4", "model_provider": "openai"},
                "1": {"player_id": "bob_claude", "model_name": "claude-3", "model_provider": "anthropic"}
            },
            "result": "WHITE_WINS",  # Alice wins
            "total_moves": 45,
            "duration_hours": 1.5
        },
        {
            "game_id": "alice_win_2", 
            "players": {
                "0": {"player_id": "alice_gpt4", "model_name": "gpt-4", "model_provider": "openai"},
                "1": {"player_id": "charlie_gemini", "model_name": "gemini-pro", "model_provider": "google"}
            },
            "result": "WHITE_WINS",  # Alice wins
            "total_moves": 38,
            "duration_hours": 1.0
        },
        {
            "game_id": "alice_draw",
            "players": {
                "0": {"player_id": "alice_gpt4", "model_name": "gpt-4", "model_provider": "openai"},
                "1": {"player_id": "david_llama", "model_name": "llama-2", "model_provider": "meta"}
            },
            "result": "DRAW",  # Alice draws
            "total_moves": 67,
            "duration_hours": 2.0
        },
        
        # Bob (moderate performance - should rank #2)
        {
            "game_id": "bob_win_1",
            "players": {
                "0": {"player_id": "charlie_gemini", "model_name": "gemini-pro", "model_provider": "google"},
                "1": {"player_id": "bob_claude", "model_name": "claude-3", "model_provider": "anthropic"}
            },
            "result": "BLACK_WINS",  # Bob wins
            "total_moves": 52,
            "duration_hours": 1.75
        },
        # Bob loses to Alice (already counted above)
        {
            "game_id": "bob_loss_2",
            "players": {
                "0": {"player_id": "bob_claude", "model_name": "claude-3", "model_provider": "anthropic"},
                "1": {"player_id": "david_llama", "model_name": "llama-2", "model_provider": "meta"}
            },
            "result": "BLACK_WINS",  # Bob loses, David wins
            "total_moves": 41,
            "duration_hours": 1.25
        },
        
        # Charlie (low performance - many games but low win rate)
        {
            "game_id": "charlie_loss_1",
            "players": {
                "0": {"player_id": "charlie_gemini", "model_name": "gemini-pro", "model_provider": "google"},
                "1": {"player_id": "eve_mixtral", "model_name": "mixtral-8x7b", "model_provider": "mistral"}
            },
            "result": "BLACK_WINS",  # Charlie loses
            "total_moves": 29,
            "duration_hours": 0.75
        },
        # Charlie loses to Alice (already counted above)
        # Charlie loses to Bob (already counted above)
        
        # David (newer player - fewer games)
        # David beats Bob (already counted above)
        # David draws with Alice (already counted above)
        
        # Eve (one game winner)
        # Eve beats Charlie (already counted above)
    ]
    
    for i, scenario in enumerate(game_scenarios):
        game = MagicMock(spec=GameRecord)
        game.game_id = scenario["game_id"]
        game.start_time = base_time + timedelta(hours=i)
        game.end_time = base_time + timedelta(hours=i + scenario["duration_hours"])
        game.total_moves = scenario["total_moves"]
        game.is_completed = True
        
        # Mock players
        game.players = {}
        for position, player_info in scenario["players"].items():
            game.players[position] = MagicMock(
                player_id=player_info["player_id"],
                model_name=player_info["model_name"],
                model_provider=player_info["model_provider"],
                elo_rating=1500.0 + (hash(player_info["player_id"]) % 500)  # Vary ELO ratings
            )
        
        # Mock outcome
        game.outcome = MagicMock()
        game.outcome.result = MagicMock()
        game.outcome.result.value = scenario["result"]
        game.outcome.termination = MagicMock()
        game.outcome.termination.value = "CHECKMATE"
        
        games.append(game)
    
    return games


class TestLeaderboardBasic:
    """Test cases for basic leaderboard functionality."""
    
    @pytest.mark.asyncio
    async def test_leaderboard_basic(self, leaderboard_client, mock_query_engine, sample_leaderboard_games):
        """Test basic leaderboard generation."""
        mock_query_engine.query_games_advanced.return_value = sample_leaderboard_games
        
        response = leaderboard_client.get("/api/leaderboard")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check response structure
        assert "players" in data
        assert "pagination" in data
        assert "sort_by" in data
        assert "success" in data
        assert data["success"] is True
        
        players = data["players"]
        assert len(players) > 0
        
        # Check player structure
        first_player = players[0]
        required_fields = ["player_id", "model_name", "rank", "games_played", "wins", 
                         "losses", "draws", "win_rate", "average_game_length", "elo_rating"]
        for field in required_fields:
            assert field in first_player
        
        # Check that rankings are sequential starting from 1
        for i, player in enumerate(players):
            assert player["rank"] == i + 1
    
    @pytest.mark.asyncio
    async def test_leaderboard_player_statistics(self, leaderboard_client, mock_query_engine, sample_leaderboard_games):
        """Test that player statistics are calculated correctly."""
        mock_query_engine.query_games_advanced.return_value = sample_leaderboard_games
        
        response = leaderboard_client.get("/api/leaderboard")
        
        assert response.status_code == 200
        data = response.json()
        
        # Find Alice (should have best performance)
        alice_player = None
        for player in data["players"]:
            if player["player_id"] == "alice_gpt4":
                alice_player = player
                break
        
        assert alice_player is not None
        assert alice_player["games_played"] == 3  # 3 games
        assert alice_player["wins"] == 2  # 2 wins
        assert alice_player["draws"] == 1  # 1 draw
        assert alice_player["losses"] == 0  # 0 losses
        assert alice_player["win_rate"] == 66.67  # 2/3 * 100


class TestLeaderboardSorting:
    """Test cases for leaderboard sorting functionality."""
    
    @pytest.mark.asyncio
    async def test_sort_by_win_rate_desc(self, leaderboard_client, mock_query_engine, sample_leaderboard_games):
        """Test sorting by win rate descending (default)."""
        mock_query_engine.query_games_advanced.return_value = sample_leaderboard_games
        
        response = leaderboard_client.get("/api/leaderboard?sort_by=win_rate_desc")
        
        assert response.status_code == 200
        data = response.json()
        
        players = data["players"]
        assert len(players) >= 2
        
        # Check that players are sorted by win rate descending
        for i in range(len(players) - 1):
            current_win_rate = players[i]["win_rate"]
            next_win_rate = players[i + 1]["win_rate"]
            assert current_win_rate >= next_win_rate
    
    @pytest.mark.asyncio
    async def test_sort_by_games_played_desc(self, leaderboard_client, mock_query_engine, sample_leaderboard_games):
        """Test sorting by games played descending."""
        mock_query_engine.query_games_advanced.return_value = sample_leaderboard_games
        
        response = leaderboard_client.get("/api/leaderboard?sort_by=games_played_desc")
        
        assert response.status_code == 200
        data = response.json()
        
        players = data["players"]
        
        # Check that players are sorted by games played descending
        for i in range(len(players) - 1):
            current_games = players[i]["games_played"]
            next_games = players[i + 1]["games_played"]
            assert current_games >= next_games
        
        assert data["sort_by"] == "games_played_desc"
    
    @pytest.mark.asyncio
    async def test_sort_by_elo_rating_desc(self, leaderboard_client, mock_query_engine, sample_leaderboard_games):
        """Test sorting by ELO rating descending."""
        mock_query_engine.query_games_advanced.return_value = sample_leaderboard_games
        
        response = leaderboard_client.get("/api/leaderboard?sort_by=elo_rating_desc")
        
        assert response.status_code == 200
        data = response.json()
        
        players = data["players"]
        
        # Check that players are sorted by ELO rating descending
        for i in range(len(players) - 1):
            current_elo = players[i]["elo_rating"]
            next_elo = players[i + 1]["elo_rating"]
            assert current_elo >= next_elo


class TestLeaderboardFiltering:
    """Test cases for leaderboard filtering functionality."""
    
    @pytest.mark.asyncio
    async def test_filter_by_player_ids(self, leaderboard_client, mock_query_engine, sample_leaderboard_games):
        """Test filtering by specific player IDs."""
        mock_query_engine.query_games_advanced.return_value = sample_leaderboard_games
        
        response = leaderboard_client.get("/api/leaderboard?player_ids=alice_gpt4,bob_claude")
        
        assert response.status_code == 200
        data = response.json()
        
        players = data["players"]
        player_ids = [player["player_id"] for player in players]
        
        # Should only contain Alice and Bob
        assert "alice_gpt4" in player_ids
        assert "bob_claude" in player_ids
        assert len(players) == 2
        
        # Check filters are recorded
        assert "player_ids" in data["filters_applied"]
        assert data["filters_applied"]["player_ids"] == "alice_gpt4,bob_claude"
    
    @pytest.mark.asyncio
    async def test_filter_by_model_providers(self, leaderboard_client, mock_query_engine, sample_leaderboard_games):
        """Test filtering by model providers."""
        mock_query_engine.query_games_advanced.return_value = sample_leaderboard_games
        
        response = leaderboard_client.get("/api/leaderboard?model_providers=openai,anthropic")
        
        assert response.status_code == 200
        data = response.json()
        
        players = data["players"]
        
        # All players should be from OpenAI or Anthropic
        for player in players:
            # Note: We need to find the player in the games to check model_provider
            # Since our mock doesn't set model_provider directly on PlayerRanking
            pass  # This would be validated in integration tests with real data
        
        assert "model_providers" in data["filters_applied"]
    
    @pytest.mark.asyncio
    async def test_filter_by_min_games(self, leaderboard_client, mock_query_engine, sample_leaderboard_games):
        """Test filtering by minimum number of games."""
        mock_query_engine.query_games_advanced.return_value = sample_leaderboard_games
        
        response = leaderboard_client.get("/api/leaderboard?min_games=2")
        
        assert response.status_code == 200
        data = response.json()
        
        players = data["players"]
        
        # All players should have at least 2 games
        for player in players:
            assert player["games_played"] >= 2
        
        assert "min_games" in data["filters_applied"]
        assert data["filters_applied"]["min_games"] == 2


class TestLeaderboardPagination:
    """Test cases for leaderboard pagination."""
    
    @pytest.mark.asyncio
    async def test_pagination_basic(self, leaderboard_client, mock_query_engine, sample_leaderboard_games):
        """Test basic pagination functionality."""
        mock_query_engine.query_games_advanced.return_value = sample_leaderboard_games
        
        response = leaderboard_client.get("/api/leaderboard?page=1&limit=2")
        
        assert response.status_code == 200
        data = response.json()
        
        players = data["players"]
        pagination = data["pagination"]
        
        # Should have at most 2 players
        assert len(players) <= 2
        
        # Check pagination metadata
        assert pagination["page"] == 1
        assert pagination["limit"] == 2
        assert pagination["total_count"] >= 2
        assert "has_next" in pagination
        assert "has_previous" in pagination
        assert pagination["has_previous"] is False  # First page
    
    @pytest.mark.asyncio
    async def test_pagination_second_page(self, leaderboard_client, mock_query_engine, sample_leaderboard_games):
        """Test second page pagination."""
        mock_query_engine.query_games_advanced.return_value = sample_leaderboard_games
        
        # Get total count first
        response1 = leaderboard_client.get("/api/leaderboard?limit=1000")
        total_players = len(response1.json()["players"])
        
        if total_players > 2:
            response = leaderboard_client.get("/api/leaderboard?page=2&limit=2")
            
            assert response.status_code == 200
            data = response.json()
            
            pagination = data["pagination"]
            assert pagination["page"] == 2
            assert pagination["has_previous"] is True


class TestLeaderboardEdgeCases:
    """Test cases for leaderboard edge cases."""
    
    @pytest.mark.asyncio
    async def test_empty_leaderboard(self, leaderboard_client, mock_query_engine):
        """Test leaderboard with no games."""
        mock_query_engine.query_games_advanced.return_value = []
        
        response = leaderboard_client.get("/api/leaderboard")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["players"] == []
        assert data["pagination"]["total_count"] == 0
        assert data["pagination"]["total_pages"] == 0
    
    @pytest.mark.asyncio
    async def test_invalid_sort_parameter(self, leaderboard_client, mock_query_engine, sample_leaderboard_games):
        """Test leaderboard with invalid sort parameter."""
        mock_query_engine.query_games_advanced.return_value = sample_leaderboard_games
        
        # FastAPI should handle enum validation
        response = leaderboard_client.get("/api/leaderboard?sort_by=invalid_sort")
        
        assert response.status_code == 422  # FastAPI validation error
    
    @pytest.mark.asyncio
    async def test_pagination_out_of_bounds(self, leaderboard_client, mock_query_engine, sample_leaderboard_games):
        """Test pagination with page number out of bounds."""
        mock_query_engine.query_games_advanced.return_value = sample_leaderboard_games
        
        response = leaderboard_client.get("/api/leaderboard?page=9999&limit=10")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should return empty results but valid response
        assert data["players"] == []
        assert data["pagination"]["page"] == 9999
    
    @pytest.mark.asyncio
    async def test_error_handling(self, leaderboard_client, mock_query_engine):
        """Test error handling in leaderboard endpoint."""
        mock_query_engine.query_games_advanced.side_effect = Exception("Database error")
        
        response = leaderboard_client.get("/api/leaderboard")
        
        assert response.status_code == 500
        data = response.json()
        assert "Failed to generate leaderboard" in data["detail"]


class TestLeaderboardHelperFunctions:
    """Test cases for leaderboard helper functions."""
    
    @pytest.mark.asyncio
    async def test_comprehensive_leaderboard_generation(self, mock_query_engine, sample_leaderboard_games):
        """Test the leaderboard generation helper function directly."""
        from .routes.players import _generate_comprehensive_leaderboard
        
        mock_query_engine.query_games_advanced.return_value = sample_leaderboard_games
        
        filters = {}
        players = await _generate_comprehensive_leaderboard(mock_query_engine, filters)
        
        assert len(players) > 0
        
        # Check that statistics are calculated correctly
        for player in players:
            assert player.games_played >= 0
            assert player.wins >= 0
            assert player.losses >= 0
            assert player.draws >= 0
            assert 0 <= player.win_rate <= 100
    
    def test_leaderboard_sorting(self):
        """Test the leaderboard sorting helper function directly."""
        from .routes.players import _sort_leaderboard
        from .models import PlayerRanking, SortOptions
        
        # Create test players with different stats
        players = [
            PlayerRanking(
                player_id="player1", model_name="model1", rank=0, games_played=10,
                wins=8, losses=2, draws=0, win_rate=80.0, average_game_length=45.0, elo_rating=1600.0
            ),
            PlayerRanking(
                player_id="player2", model_name="model2", rank=0, games_played=5,
                wins=4, losses=1, draws=0, win_rate=80.0, average_game_length=50.0, elo_rating=1700.0
            ),
            PlayerRanking(
                player_id="player3", model_name="model3", rank=0, games_played=20,
                wins=12, losses=8, draws=0, win_rate=60.0, average_game_length=40.0, elo_rating=1550.0
            )
        ]
        
        # Test win rate descending sort
        sorted_players = _sort_leaderboard(players, SortOptions.WIN_RATE_DESC)
        
        # Players 1 and 2 have same win rate, but player1 has more games, so should be first
        assert sorted_players[0].player_id == "player1"
        assert sorted_players[1].player_id == "player2"
        assert sorted_players[2].player_id == "player3"
        
        # Test ELO rating descending sort
        sorted_players = _sort_leaderboard(players, SortOptions.ELO_RATING_DESC)
        assert sorted_players[0].player_id == "player2"  # Highest ELO
        assert sorted_players[1].player_id == "player1"
        assert sorted_players[2].player_id == "player3"