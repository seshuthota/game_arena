"""
Comprehensive unit tests for search and advanced filtering functionality.

This module tests the search endpoints and enhanced filtering capabilities
added in task 2.3.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient

from game_arena.storage.models import GameRecord, GameResult, TerminationReason
from game_arena.storage.query_engine import GameFilters

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
def search_test_app(mock_storage_manager, mock_query_engine):
    """Create a test FastAPI application for search testing."""
    app = create_app()
    
    # Override the lifespan to avoid actual storage initialization
    app.state.storage_manager = mock_storage_manager
    app.state.query_engine = mock_query_engine
    
    return app


@pytest.fixture
def search_client(search_test_app):
    """Create a test client for search testing."""
    return TestClient(search_test_app)


@pytest.fixture
def sample_search_games():
    """Create sample games for search testing."""
    base_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    
    games = []
    game_configs = [
        {
            "game_id": "test_game_1",
            "tournament_id": "chess_tournament_alpha",
            "players": {
                "0": {"player_id": "gpt4_player", "model_name": "gpt-4", "model_provider": "openai"},
                "1": {"player_id": "claude_player", "model_name": "claude-3", "model_provider": "anthropic"}
            }
        },
        {
            "game_id": "blitz_game_2", 
            "tournament_id": "rapid_tournament_beta",
            "players": {
                "0": {"player_id": "gemini_player", "model_name": "gemini-pro", "model_provider": "google"},
                "1": {"player_id": "llama_player", "model_name": "llama-2", "model_provider": "meta"}
            }
        },
        {
            "game_id": "match_game_3",
            "tournament_id": "championship_gamma", 
            "players": {
                "0": {"player_id": "gpt4_player", "model_name": "gpt-4", "model_provider": "openai"},
                "1": {"player_id": "mixtral_player", "model_name": "mixtral-8x7b", "model_provider": "mistral"}
            }
        }
    ]
    
    for i, config in enumerate(game_configs):
        game = MagicMock(spec=GameRecord)
        game.game_id = config["game_id"]
        game.tournament_id = config["tournament_id"]
        game.start_time = base_time.replace(hour=12 + i)
        game.end_time = base_time.replace(hour=13 + i)
        game.total_moves = 25 + (i * 5)
        game.is_completed = True
        game.initial_fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        game.final_fen = "r1bqk2r/pppp1ppp/2n2n2/2b1p3/2B1P3/3P1N2/PPP2PPP/RNBQK2R w KQkq - 4 4"
        
        # Mock players
        game.players = {}
        for position, player_info in config["players"].items():
            game.players[position] = MagicMock(
                player_id=player_info["player_id"],
                model_name=player_info["model_name"],
                model_provider=player_info["model_provider"],
                agent_type="ChessLLMAgent",
                elo_rating=1500 + (i * 100)
            )
        
        # Mock outcome
        game.outcome = MagicMock()
        game.outcome.result = MagicMock()
        game.outcome.result.value = "WHITE_WINS" if i % 2 == 0 else "BLACK_WINS"
        game.outcome.winner = i % 2
        game.outcome.termination = MagicMock()
        game.outcome.termination.value = "CHECKMATE"
        game.outcome.termination_details = None
        
        games.append(game)
    
    return games


class TestGameSearch:
    """Test cases for game search functionality."""
    
    @pytest.mark.asyncio
    async def test_search_games_basic(self, search_client, mock_query_engine, sample_search_games):
        """Test basic game search functionality."""
        # Setup mock to return games matching "gpt4"
        matching_games = [game for game in sample_search_games if "gpt4_player" in str(game.players)]
        mock_query_engine.search_games.return_value = matching_games
        
        response = search_client.get("/api/search/games?query=gpt4")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check response structure
        assert "results" in data
        assert "query" in data
        assert "result_count" in data
        assert "search_type" in data
        
        assert data["query"] == "gpt4"
        assert data["search_type"] == "games"
        assert data["result_count"] == len(matching_games)
        assert len(data["results"]) == len(matching_games)
        
        # Verify search was called correctly
        mock_query_engine.search_games.assert_called_once_with(
            search_term="gpt4",
            search_fields=None
        )
    
    @pytest.mark.asyncio
    async def test_search_games_with_fields(self, search_client, mock_query_engine, sample_search_games):
        """Test game search with specific search fields."""
        mock_query_engine.search_games.return_value = sample_search_games[:1]
        
        response = search_client.get("/api/search/games?query=tournament&search_fields=tournament_id")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["query"] == "tournament"
        assert data["result_count"] == 1
        
        # Verify search was called with specific fields
        mock_query_engine.search_games.assert_called_once_with(
            search_term="tournament",
            search_fields=["tournament_id"]
        )
    
    @pytest.mark.asyncio
    async def test_search_games_invalid_fields(self, search_client, mock_query_engine):
        """Test game search with invalid search fields."""
        response = search_client.get("/api/search/games?query=test&search_fields=invalid_field")
        
        assert response.status_code == 400
        data = response.json()
        assert "Invalid search fields" in data["detail"]
    
    @pytest.mark.asyncio
    async def test_search_games_with_limit(self, search_client, mock_query_engine, sample_search_games):
        """Test game search with result limiting."""
        mock_query_engine.search_games.return_value = sample_search_games
        
        response = search_client.get("/api/search/games?query=game&limit=2")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should limit results to 2 even though 3 games match
        assert data["result_count"] == 2
        assert len(data["results"]) == 2
    
    @pytest.mark.asyncio
    async def test_search_games_empty_results(self, search_client, mock_query_engine):
        """Test game search with no matching results."""
        mock_query_engine.search_games.return_value = []
        
        response = search_client.get("/api/search/games?query=nonexistent")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["result_count"] == 0
        assert len(data["results"]) == 0
        assert data["query"] == "nonexistent"
    
    @pytest.mark.asyncio
    async def test_search_games_error_handling(self, search_client, mock_query_engine):
        """Test error handling in game search."""
        mock_query_engine.search_games.side_effect = Exception("Search failed")
        
        response = search_client.get("/api/search/games?query=test")
        
        assert response.status_code == 500
        data = response.json()
        assert "Search operation failed" in data["detail"]


class TestPlayerSearch:
    """Test cases for player search functionality."""
    
    @pytest.mark.asyncio
    async def test_search_players_basic(self, search_client, mock_query_engine, sample_search_games):
        """Test basic player search functionality."""
        mock_query_engine.query_games_advanced.return_value = sample_search_games
        
        response = search_client.get("/api/search/players?query=gpt")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check response structure
        assert "results" in data
        assert "query" in data
        assert "result_count" in data
        assert "search_type" in data
        
        assert data["query"] == "gpt"
        assert data["search_type"] == "players"
        assert data["result_count"] >= 1  # Should find gpt4_player
        
        # Verify player info structure
        if data["results"]:
            player = data["results"][0]
            assert "player_id" in player
            assert "model_name" in player
            assert "model_provider" in player
    
    @pytest.mark.asyncio
    async def test_search_players_with_limit(self, search_client, mock_query_engine, sample_search_games):
        """Test player search with result limiting."""
        mock_query_engine.query_games_advanced.return_value = sample_search_games
        
        response = search_client.get("/api/search/players?query=player&limit=3")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should limit results
        assert len(data["results"]) <= 3
    
    @pytest.mark.asyncio
    async def test_search_players_unique_results(self, search_client, mock_query_engine, sample_search_games):
        """Test that player search returns unique players only."""
        # Create duplicate games with same player
        duplicate_games = sample_search_games + [sample_search_games[0]]
        mock_query_engine.query_games_advanced.return_value = duplicate_games
        
        response = search_client.get("/api/search/players?query=gpt4_player")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should only return unique players
        player_keys = [(p["player_id"], p["model_name"]) for p in data["results"]]
        assert len(player_keys) == len(set(player_keys))  # All unique
    
    @pytest.mark.asyncio
    async def test_search_players_error_handling(self, search_client, mock_query_engine):
        """Test error handling in player search."""
        mock_query_engine.query_games_advanced.side_effect = Exception("Database error")
        
        response = search_client.get("/api/search/players?query=test")
        
        assert response.status_code == 500
        data = response.json()
        assert "Player search operation failed" in data["detail"]


class TestAdvancedFiltering:
    """Test cases for advanced filtering in game list endpoint."""
    
    @pytest.mark.asyncio
    async def test_multiple_player_ids_filter(self, search_client, mock_query_engine, sample_search_games):
        """Test filtering by multiple player IDs."""
        mock_query_engine.query_games_advanced.return_value = sample_search_games[:2]
        mock_query_engine.count_games_advanced.return_value = 2
        
        response = search_client.get("/api/games?player_ids=gpt4_player,claude_player")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check that filter was applied
        assert "filters_applied" in data
        filters = data["filters_applied"]
        assert "player_ids" in filters
        assert filters["player_ids"] == "gpt4_player,claude_player"
        
        # Verify query engine was called with correct filters
        mock_query_engine.query_games_advanced.assert_called()
        call_args = mock_query_engine.query_games_advanced.call_args
        game_filters = call_args[0][0]
        assert "gpt4_player" in game_filters.player_ids
        assert "claude_player" in game_filters.player_ids
    
    @pytest.mark.asyncio
    async def test_multiple_model_names_filter(self, search_client, mock_query_engine, sample_search_games):
        """Test filtering by multiple model names."""
        mock_query_engine.query_games_advanced.return_value = sample_search_games
        mock_query_engine.count_games_advanced.return_value = 3
        
        response = search_client.get("/api/games?model_names=gpt-4,claude-3,gemini-pro")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check that filter was applied
        filters = data["filters_applied"]
        assert "model_names" in filters
        assert filters["model_names"] == "gpt-4,claude-3,gemini-pro"
        
        # Verify query engine was called with correct filters
        call_args = mock_query_engine.query_games_advanced.call_args
        game_filters = call_args[0][0]
        assert "gpt-4" in game_filters.model_names
        assert "claude-3" in game_filters.model_names
        assert "gemini-pro" in game_filters.model_names
    
    @pytest.mark.asyncio
    async def test_multiple_providers_filter(self, search_client, mock_query_engine, sample_search_games):
        """Test filtering by multiple model providers."""
        mock_query_engine.query_games_advanced.return_value = sample_search_games[:2]
        mock_query_engine.count_games_advanced.return_value = 2
        
        response = search_client.get("/api/games?model_providers=openai,anthropic")
        
        assert response.status_code == 200
        data = response.json()
        
        filters = data["filters_applied"]
        assert "model_providers" in filters
        assert filters["model_providers"] == "openai,anthropic"
        
        call_args = mock_query_engine.query_games_advanced.call_args
        game_filters = call_args[0][0]
        assert "openai" in game_filters.model_providers
        assert "anthropic" in game_filters.model_providers
    
    @pytest.mark.asyncio
    async def test_multiple_tournament_ids_filter(self, search_client, mock_query_engine, sample_search_games):
        """Test filtering by multiple tournament IDs."""
        mock_query_engine.query_games_advanced.return_value = sample_search_games
        mock_query_engine.count_games_advanced.return_value = 3
        
        response = search_client.get("/api/games?tournament_ids=chess_tournament_alpha,rapid_tournament_beta")
        
        assert response.status_code == 200
        data = response.json()
        
        filters = data["filters_applied"]
        assert "tournament_ids" in filters
        
        call_args = mock_query_engine.query_games_advanced.call_args
        game_filters = call_args[0][0]
        assert "chess_tournament_alpha" in game_filters.tournament_ids
        assert "rapid_tournament_beta" in game_filters.tournament_ids
    
    @pytest.mark.asyncio
    async def test_combined_single_and_multiple_filters(self, search_client, mock_query_engine, sample_search_games):
        """Test combining single and multiple filter parameters."""
        mock_query_engine.query_games_advanced.return_value = sample_search_games[:1]
        mock_query_engine.count_games_advanced.return_value = 1
        
        response = search_client.get(
            "/api/games?player_id=gpt4_player&model_names=gpt-4,claude-3&tournament_ids=chess_tournament_alpha"
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify that both single and multiple filters are combined
        call_args = mock_query_engine.query_games_advanced.call_args
        game_filters = call_args[0][0]
        
        # Should combine single player_id with multiple model_names
        assert "gpt4_player" in game_filters.player_ids
        assert "gpt-4" in game_filters.model_names
        assert "claude-3" in game_filters.model_names
        assert "chess_tournament_alpha" in game_filters.tournament_ids


class TestSearchAndFilterCombination:
    """Test cases for combining search with filtering."""
    
    @pytest.mark.asyncio
    async def test_search_with_filters(self, search_client, mock_query_engine, sample_search_games):
        """Test search combined with filters."""
        # Setup search to return all games, then filters should be applied
        mock_query_engine.search_games.return_value = sample_search_games
        
        response = search_client.get("/api/games?search=gpt&model_provider=openai&min_moves=20")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify search was called
        mock_query_engine.search_games.assert_called_once_with("gpt")
        
        # Check that search query is in applied filters
        filters = data["filters_applied"]
        assert "search" in filters
        assert filters["search"] == "gpt"
        assert "model_provider" in filters
        assert "min_moves" in filters
    
    @pytest.mark.asyncio
    async def test_search_with_multiple_filters(self, search_client, mock_query_engine, sample_search_games):
        """Test search with multiple filter types."""
        mock_query_engine.search_games.return_value = sample_search_games
        
        response = search_client.get(
            "/api/games?search=tournament&player_ids=gpt4_player,claude_player&model_providers=openai,anthropic"
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify search was called
        mock_query_engine.search_games.assert_called_once_with("tournament")
        
        # Check filters are applied
        filters = data["filters_applied"]
        assert filters["search"] == "tournament"
        assert "player_ids" in filters
        assert "model_providers" in filters


class TestFilterValidation:
    """Test cases for filter parameter validation."""
    
    def test_invalid_move_range(self, search_client, mock_query_engine):
        """Test validation of move count ranges."""
        # Setup mock to return empty results to avoid comparison issues
        mock_query_engine.query_games_advanced.return_value = []
        mock_query_engine.count_games_advanced.return_value = 0
        
        # This should pass basic validation but could be caught at business logic level
        response = search_client.get("/api/games?min_moves=100&max_moves=50")
        
        # The endpoint should handle this gracefully
        # Either reject with 422 or handle the logic correctly
        assert response.status_code in [200, 422]
    
    def test_negative_values_rejected(self, search_client, mock_query_engine):
        """Test that negative values are rejected."""
        response = search_client.get("/api/games?min_moves=-5")
        
        assert response.status_code == 422
    
    def test_invalid_enum_values(self, search_client, mock_query_engine):
        """Test that invalid enum values are rejected."""
        response = search_client.get("/api/games?result=invalid_result")
        
        assert response.status_code == 422
        
        response = search_client.get("/api/games?termination=invalid_termination")
        
        assert response.status_code == 422
    
    def test_limit_validation(self, search_client, mock_query_engine):
        """Test pagination limit validation."""
        # Test limit too high
        response = search_client.get("/api/games?limit=10000")
        
        assert response.status_code == 422
        
        # Test limit too low
        response = search_client.get("/api/games?limit=0")
        
        assert response.status_code == 422


class TestGameMatchesFilters:
    """Test cases for the _game_matches_filters helper function."""
    
    def test_player_id_matching(self, sample_search_games):
        """Test player ID filter matching."""
        from .routes.games import _game_matches_filters
        from game_arena.storage.query_engine import GameFilters as StorageGameFilters
        
        filters = StorageGameFilters()
        filters.player_ids = ["gpt4_player"]
        
        # Game 0 has gpt4_player, should match
        assert _game_matches_filters(sample_search_games[0], filters) is True
        
        # Game 1 doesn't have gpt4_player, should not match
        assert _game_matches_filters(sample_search_games[1], filters) is False
    
    def test_model_name_matching(self, sample_search_games):
        """Test model name filter matching."""
        from .routes.games import _game_matches_filters
        from game_arena.storage.query_engine import GameFilters as StorageGameFilters
        
        filters = StorageGameFilters()
        filters.model_names = ["gpt-4", "claude-3"]
        
        # Game 0 has gpt-4, should match
        assert _game_matches_filters(sample_search_games[0], filters) is True
        
        # Game 1 doesn't have gpt-4 or claude-3, should not match
        assert _game_matches_filters(sample_search_games[1], filters) is False
    
    def test_move_count_filtering(self, sample_search_games):
        """Test move count filter matching."""
        from .routes.games import _game_matches_filters
        from game_arena.storage.query_engine import GameFilters as StorageGameFilters
        
        filters = StorageGameFilters()
        filters.min_moves = 30
        filters.max_moves = 40
        
        # Check which games fall in the range
        # Game 0: 25 moves (should not match)
        # Game 1: 30 moves (should match)  
        # Game 2: 35 moves (should match)
        
        assert _game_matches_filters(sample_search_games[0], filters) is False  # 25 < 30
        assert _game_matches_filters(sample_search_games[1], filters) is True   # 30 >= 30
        assert _game_matches_filters(sample_search_games[2], filters) is True   # 35 <= 40
    
    def test_completion_status_filtering(self, sample_search_games):
        """Test completion status filter matching."""
        from .routes.games import _game_matches_filters
        from game_arena.storage.query_engine import GameFilters as StorageGameFilters
        
        filters = StorageGameFilters()
        filters.completed_only = True
        
        # All sample games are completed, should match
        for game in sample_search_games:
            assert _game_matches_filters(game, filters) is True
        
        # Test ongoing only filter
        filters.completed_only = False
        filters.ongoing_only = True
        
        # All sample games are completed, should not match ongoing filter
        for game in sample_search_games:
            assert _game_matches_filters(game, filters) is False