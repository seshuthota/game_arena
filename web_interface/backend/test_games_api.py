"""
Comprehensive unit tests for the games API endpoint.

This module tests the game list API endpoint with pagination and filtering,
ensuring all requirements for task 2.1 are met.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient

from game_arena.storage.models import GameRecord, GameResult, TerminationReason, PlayerStats
from game_arena.storage.query_engine import GameFilters

from .main import create_app
from .models import GameResultEnum, TerminationReasonEnum, SortOptions


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
def sample_game_records():
  """Create sample game records for testing."""
  base_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

  games = []
  for i in range(5):
    game = MagicMock(spec=GameRecord)
    game.game_id = f"game_{i}"
    game.tournament_id = f"tournament_{i % 2}"
    game.start_time = base_time.replace(hour=12 + i)
    game.end_time = base_time.replace(hour=12 + i + 1) if i < 4 else None
    game.total_moves = 20 + (i * 5)
    game.is_completed = i < 4

    # Add required attributes for GameDetail model
    game.initial_fen = (
        "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    )
    game.final_fen = (
        "r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3"
    )

    # Mock players
    game.players = {
        "0": MagicMock(
            player_id=f"player_{i}_white",
            model_name=f"model_{i}",
            model_provider=f"provider_{i % 2}",
            agent_type="ChessLLMAgent",
            elo_rating=1200 + (i * 50),
        ),
        "1": MagicMock(
            player_id=f"player_{i}_black",
            model_name=f"model_{i + 5}",
            model_provider=f"provider_{(i + 1) % 2}",
            agent_type="ChessLLMAgent",
            elo_rating=1200 + ((i + 1) * 50),
        ),
    }

    # Mock outcome for completed games
    if i < 4:
      game.outcome = MagicMock()
      game.outcome.result = MagicMock()
      game.outcome.result.value = "WHITE_WINS" if i % 2 == 0 else "BLACK_WINS"
      game.outcome.winner = 0 if i % 2 == 0 else 1
      game.outcome.termination = MagicMock()
      game.outcome.termination.value = "CHECKMATE"
      game.outcome.termination_details = None
    else:
      game.outcome = None

    games.append(game)

  return games


@pytest.fixture
def test_app(mock_storage_manager, mock_query_engine):
  """Create a test FastAPI application with mocked dependencies."""
  app = create_app()

  # Override the lifespan to avoid actual storage initialization
  app.state.storage_manager = mock_storage_manager
  app.state.query_engine = mock_query_engine

  return app


@pytest.fixture
def client(test_app):
  """Create a test client for the FastAPI application."""
  return TestClient(test_app)


class TestGameListEndpoint:
  """Test cases for the game list API endpoint."""

  @pytest.mark.asyncio
  async def test_get_games_basic_functionality(
      self, client, mock_query_engine, sample_game_records
  ):
    """Test basic game list retrieval."""
    # Setup mock responses
    mock_query_engine.query_games_advanced.return_value = sample_game_records[
        :3
    ]
    mock_query_engine.count_games_advanced.return_value = 3

    response = client.get("/api/games")

    assert response.status_code == 200
    data = response.json()

    # Check response structure
    assert "success" in data
    assert data["success"] is True
    assert "games" in data
    assert "pagination" in data
    assert "filters_applied" in data

    # Check games data
    assert len(data["games"]) == 3
    for game in data["games"]:
      assert game["game_id"] in [f"game_{i}" for i in range(3)]
      assert "players" in game
      assert "start_time" in game
      assert "total_moves" in game
      assert "is_completed" in game

  @pytest.mark.asyncio
  async def test_pagination_parameters(
      self, client, mock_query_engine, sample_game_records
  ):
    """Test pagination parameters work correctly."""
    # Setup mock responses
    mock_query_engine.query_games_advanced.return_value = sample_game_records[
        2:4
    ]
    mock_query_engine.count_games_advanced.return_value = 5

    response = client.get("/api/games?page=2&limit=2")

    assert response.status_code == 200
    data = response.json()

    # Check pagination metadata
    pagination = data["pagination"]
    assert pagination["page"] == 2
    assert pagination["limit"] == 2
    assert pagination["total_count"] == 5
    assert pagination["total_pages"] == 3
    assert pagination["has_next"] is True
    assert pagination["has_previous"] is True

    # Verify mock was called with correct offset
    mock_query_engine.query_games_advanced.assert_called_once()
    call_args = mock_query_engine.query_games_advanced.call_args
    assert call_args[1]["limit"] == 2
    assert call_args[1]["offset"] == 2  # (page-1) * limit = (2-1) * 2

  @pytest.mark.asyncio
  async def test_pagination_edge_cases(self, client, mock_query_engine):
    """Test pagination edge cases."""
    # Test invalid page number
    response = client.get("/api/games?page=0")
    assert response.status_code == 422

    # Test invalid limit
    response = client.get("/api/games?limit=0")
    assert response.status_code == 422

    # Test limit exceeding maximum
    response = client.get("/api/games?limit=10000")
    assert response.status_code == 422

  @pytest.mark.asyncio
  async def test_basic_filtering(
      self, client, mock_query_engine, sample_game_records
  ):
    """Test basic filtering parameters."""
    # Setup mock responses
    filtered_games = [sample_game_records[0]]
    mock_query_engine.query_games_advanced.return_value = filtered_games
    mock_query_engine.count_games_advanced.return_value = 1

    response = client.get(
        "/api/games?player_id=player_0_white&model_name=model_0"
    )

    assert response.status_code == 200
    data = response.json()

    # Check that filters were applied
    assert "filters_applied" in data
    filters = data["filters_applied"]
    assert filters["player_id"] == "player_0_white"
    assert filters["model_name"] == "model_0"

    # Verify correct filters were passed to query engine
    mock_query_engine.query_games_advanced.assert_called_once()
    call_args = mock_query_engine.query_games_advanced.call_args
    game_filters = call_args[0][
        0
    ]  # First positional argument should be GameFilters
    assert isinstance(game_filters, GameFilters)
    assert game_filters.player_ids == ["player_0_white"]
    assert game_filters.model_names == ["model_0"]

  @pytest.mark.asyncio
  async def test_advanced_filtering(
      self, client, mock_query_engine, sample_game_records
  ):
    """Test advanced filtering parameters."""
    # Setup mock responses
    mock_query_engine.query_games_advanced.return_value = [
        sample_game_records[0]
    ]
    mock_query_engine.count_games_advanced.return_value = 1

    params = {
        "model_provider": "provider_0",
        "tournament_id": "tournament_0",
        "start_date": "2024-01-01T10:00:00Z",
        "end_date": "2024-01-01T15:00:00Z",
        "result": "white_wins",
        "termination": "checkmate",
        "min_moves": "10",
        "max_moves": "50",
        "completed_only": "true",
    }

    response = client.get("/api/games", params=params)

    assert response.status_code == 200
    data = response.json()

    # Verify filters were applied
    filters = data["filters_applied"]
    assert filters["model_provider"] == "provider_0"
    assert filters["tournament_id"] == "tournament_0"
    assert filters["min_moves"] == 10
    assert filters["max_moves"] == 50

    # Verify GameFilters object was constructed correctly
    mock_query_engine.query_games_advanced.assert_called_once()
    call_args = mock_query_engine.query_games_advanced.call_args
    game_filters = call_args[0][0]
    assert game_filters.model_providers == ["provider_0"]
    assert game_filters.tournament_ids == ["tournament_0"]
    assert game_filters.min_moves == 10
    assert game_filters.max_moves == 50
    assert game_filters.completed_only is True

  @pytest.mark.asyncio
  async def test_date_filtering(
      self, client, mock_query_engine, sample_game_records
  ):
    """Test date range filtering."""
    # Setup mock responses
    mock_query_engine.query_games_advanced.return_value = sample_game_records[
        :2
    ]
    mock_query_engine.count_games_advanced.return_value = 2

    start_date = "2024-01-01T12:00:00Z"
    end_date = "2024-01-01T14:00:00Z"

    response = client.get(
        f"/api/games?start_date={start_date}&end_date={end_date}"
    )

    assert response.status_code == 200
    data = response.json()

    # Verify date filters were applied
    filters = data["filters_applied"]
    # The date format in response may use +00:00 instead of Z
    assert "start_date" in filters
    assert "end_date" in filters
    assert "2024-01-01T12:00:00" in filters["start_date"]
    assert "2024-01-01T14:00:00" in filters["end_date"]

    # Verify GameFilters received proper datetime objects
    mock_query_engine.query_games_advanced.assert_called_once()
    call_args = mock_query_engine.query_games_advanced.call_args
    game_filters = call_args[0][0]
    assert game_filters.start_time_after is not None
    assert game_filters.start_time_before is not None
    assert isinstance(game_filters.start_time_after, datetime)
    assert isinstance(game_filters.start_time_before, datetime)

  @pytest.mark.asyncio
  async def test_sorting_options(
      self, client, mock_query_engine, sample_game_records
  ):
    """Test different sorting options."""
    # Setup mock responses
    mock_query_engine.query_games_advanced.return_value = sample_game_records
    mock_query_engine.count_games_advanced.return_value = 5

    # Test each sort option
    sort_options = [
        SortOptions.START_TIME_ASC,
        SortOptions.START_TIME_DESC,
        SortOptions.DURATION_ASC,
        SortOptions.DURATION_DESC,
        SortOptions.MOVES_ASC,
        SortOptions.MOVES_DESC,
    ]

    for sort_option in sort_options:
      response = client.get(f"/api/games?sort_by={sort_option.value}")
      assert response.status_code == 200

      data = response.json()
      assert len(data["games"]) == 5  # Should return all games, just sorted

  @pytest.mark.asyncio
  async def test_empty_results(self, client, mock_query_engine):
    """Test handling of empty results."""
    # Setup mock responses for no games
    mock_query_engine.query_games_advanced.return_value = []
    mock_query_engine.count_games_advanced.return_value = 0

    response = client.get("/api/games")

    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert data["games"] == []
    assert data["pagination"]["total_count"] == 0
    assert data["pagination"]["total_pages"] == 0
    assert data["pagination"]["has_next"] is False
    assert data["pagination"]["has_previous"] is False

  @pytest.mark.asyncio
  async def test_error_handling(self, client, mock_query_engine):
    """Test error handling in the endpoint."""
    # Setup mock to raise an exception
    mock_query_engine.query_games_advanced.side_effect = Exception(
        "Database error"
    )

    response = client.get("/api/games")

    assert response.status_code == 500
    data = response.json()
    assert "Failed to retrieve games" in data["detail"]

  @pytest.mark.asyncio
  async def test_response_model_structure(
      self, client, mock_query_engine, sample_game_records
  ):
    """Test that response follows the expected model structure."""
    # Setup mock responses
    mock_query_engine.query_games_advanced.return_value = [
        sample_game_records[0]
    ]
    mock_query_engine.count_games_advanced.return_value = 1

    response = client.get("/api/games")

    assert response.status_code == 200
    data = response.json()

    # Validate GameListResponse structure
    assert "success" in data
    assert "timestamp" in data
    assert "games" in data
    assert "pagination" in data
    assert "filters_applied" in data

    # Validate GameSummary structure
    game = data["games"][0]
    required_fields = [
        "game_id",
        "tournament_id",
        "start_time",
        "end_time",
        "players",
        "outcome",
        "total_moves",
        "duration_minutes",
        "is_completed",
    ]
    for field in required_fields:
      assert field in game

    # Validate PlayerInfo structure
    assert "0" in game["players"]
    assert "1" in game["players"]
    player = game["players"]["0"]
    player_fields = [
        "player_id",
        "model_name",
        "model_provider",
        "agent_type",
        "elo_rating",
    ]
    for field in player_fields:
      assert field in player

    # Validate PaginationMeta structure
    pagination = data["pagination"]
    pagination_fields = [
        "page",
        "limit",
        "total_count",
        "total_pages",
        "has_next",
        "has_previous",
    ]
    for field in pagination_fields:
      assert field in pagination

  @pytest.mark.asyncio
  async def test_filter_parameter_validation(self, client, mock_query_engine):
    """Test validation of filter parameters."""
    # Test invalid enum values
    response = client.get("/api/games?result=invalid_result")
    assert response.status_code == 422

    response = client.get("/api/games?termination=invalid_termination")
    assert response.status_code == 422

    response = client.get("/api/games?sort_by=invalid_sort")
    assert response.status_code == 422

    # Test invalid integer values
    response = client.get("/api/games?min_moves=-1")
    assert response.status_code == 422

    response = client.get("/api/games?max_moves=-1")
    assert response.status_code == 422

  @pytest.mark.asyncio
  async def test_all_filter_combinations(
      self, client, mock_query_engine, sample_game_records
  ):
    """Test combinations of all available filters."""
    # Setup mock responses
    mock_query_engine.query_games_advanced.return_value = [
        sample_game_records[0]
    ]
    mock_query_engine.count_games_advanced.return_value = 1

    # Test with all possible filters applied
    params = {
        "page": "1",
        "limit": "10",
        "sort_by": "start_time_desc",
        "player_id": "test_player",
        "model_name": "test_model",
        "model_provider": "test_provider",
        "tournament_id": "test_tournament",
        "start_date": "2024-01-01T00:00:00Z",
        "end_date": "2024-01-02T00:00:00Z",
        "result": "white_wins",
        "termination": "checkmate",
        "min_moves": "10",
        "max_moves": "100",
        "completed_only": "true",
    }

    response = client.get("/api/games", params=params)

    assert response.status_code == 200
    data = response.json()

    # Verify all filters are present in the response
    filters = data["filters_applied"]
    assert len(filters) == len([
        k
        for k, v in params.items()
        if k not in ["page", "limit", "sort_by"] and v
    ])

    # Verify the GameFilters object received all parameters
    mock_query_engine.query_games_advanced.assert_called_once()
    call_args = mock_query_engine.query_games_advanced.call_args
    game_filters = call_args[0][0]

    assert game_filters.player_ids == ["test_player"]
    assert game_filters.model_names == ["test_model"]
    assert game_filters.model_providers == ["test_provider"]
    assert game_filters.tournament_ids == ["test_tournament"]
    assert game_filters.min_moves == 10
    assert game_filters.max_moves == 100
    assert game_filters.completed_only is True


@pytest.fixture
def sample_move_records():
  """Create sample move records for testing."""
  moves = []
  for i in range(5):
    move = MagicMock()
    move.move_number = i + 1
    move.player = i % 2  # Alternating players
    move.move_san = f"Nf{i + 3}"
    move.move_uci = f"g1f{i + 3}"
    move.fen_before = f"position_before_{i}"
    move.fen_after = f"position_after_{i}"
    move.is_legal = True
    move.parsing_success = True
    move.thinking_time_ms = 1000 + (i * 100)
    move.api_call_time_ms = 500 + (i * 50)
    move.total_time_ms = 1500 + (i * 150)
    move.had_rethink = i % 3 == 0  # Some moves have rethinking
    move.rethink_attempts = [f"rethink_{i}"] if i % 3 == 0 else []
    move.blunder_flag = i == 2  # Mark one move as blunder
    move.move_quality_score = 0.8 - (i * 0.1) if i < 4 else None
    move.raw_response = f"LLM response for move {i + 1}"
    moves.append(move)
  return moves


class TestGameDetailEndpoint:
  """Test cases for the game detail API endpoint."""

  @pytest.mark.asyncio
  async def test_get_game_detail_success(
      self, client, mock_query_engine, sample_game_records
  ):
    """Test successful game detail retrieval."""
    # Setup mock responses
    game_record = sample_game_records[0]
    moves_data = []  # Empty moves for simplicity

    mock_query_engine.storage_manager.get_game.return_value = game_record
    mock_query_engine.storage_manager.get_moves.return_value = moves_data

    response = client.get("/api/games/game_0")

    assert response.status_code == 200
    data = response.json()

    assert "success" in data
    assert data["success"] is True
    assert "game" in data

    game = data["game"]
    assert game["game_id"] == "game_0"
    assert "moves" in game
    assert isinstance(game["moves"], list)

  @pytest.mark.asyncio
  async def test_get_game_detail_with_moves(
      self, client, mock_query_engine, sample_game_records, sample_move_records
  ):
    """Test game detail retrieval with comprehensive move data."""
    # Setup mock responses
    game_record = sample_game_records[0]
    moves_data = sample_move_records

    mock_query_engine.storage_manager.get_game.return_value = game_record
    mock_query_engine.storage_manager.get_moves.return_value = moves_data

    response = client.get("/api/games/game_0")

    assert response.status_code == 200
    data = response.json()

    game = data["game"]
    assert len(game["moves"]) == 5

    # Test first move in detail
    first_move = game["moves"][0]
    expected_move_fields = [
        "move_number",
        "player",
        "move_notation",
        "fen_before",
        "fen_after",
        "is_legal",
        "parsing_success",
        "thinking_time_ms",
        "api_call_time_ms",
        "total_time_ms",
        "had_rethink",
        "rethink_attempts",
        "blunder_flag",
        "move_quality_score",
        "llm_response",
    ]

    for field in expected_move_fields:
      assert field in first_move

    # Verify specific values
    assert first_move["move_number"] == 1
    assert first_move["player"] == 0
    assert first_move["move_notation"] == "Nf3"
    assert first_move["is_legal"] is True
    assert first_move["thinking_time_ms"] == 1000
    assert first_move["had_rethink"] is True
    assert first_move["rethink_attempts"] == 1

  @pytest.mark.asyncio
  async def test_game_detail_response_structure(
      self, client, mock_query_engine, sample_game_records, sample_move_records
  ):
    """Test that game detail response has complete structure."""
    # Setup mock responses
    game_record = sample_game_records[0]
    mock_query_engine.storage_manager.get_game.return_value = game_record
    mock_query_engine.storage_manager.get_moves.return_value = sample_move_records

    response = client.get("/api/games/game_0")

    assert response.status_code == 200
    data = response.json()

    # Validate GameDetailResponse structure
    assert "success" in data
    assert "timestamp" in data
    assert "game" in data

    game = data["game"]

    # Validate GameDetail structure (extends GameSummary)
    required_fields = [
        "game_id",
        "tournament_id",
        "start_time",
        "end_time",
        "players",
        "outcome",
        "total_moves",
        "duration_minutes",
        "is_completed",
        "initial_fen",
        "final_fen",
        "moves",
    ]

    for field in required_fields:
      assert field in game

    # Validate specific fields
    assert game["initial_fen"] == (
        "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    )
    assert game["final_fen"] == (
        "r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3"
    )
    assert isinstance(game["moves"], list)

  @pytest.mark.asyncio
  async def test_game_detail_move_metadata(
      self, client, mock_query_engine, sample_game_records, sample_move_records
  ):
    """Test that all move metadata is properly included."""
    # Setup mock responses
    game_record = sample_game_records[0]
    mock_query_engine.storage_manager.get_game.return_value = game_record
    mock_query_engine.storage_manager.get_moves.return_value = sample_move_records

    response = client.get("/api/games/game_0")

    assert response.status_code == 200
    data = response.json()

    moves = data["game"]["moves"]

    # Test move with rethink
    rethink_move = moves[0]  # First move has rethink
    assert rethink_move["had_rethink"] is True
    assert rethink_move["rethink_attempts"] == 1

    # Test move with blunder flag
    blunder_move = moves[2]  # Third move is marked as blunder
    assert blunder_move["blunder_flag"] is True

    # Test move quality scores
    for i, move in enumerate(moves[:4]):  # First 4 moves have quality scores
      assert "move_quality_score" in move
      assert move["move_quality_score"] is not None

    # Test LLM responses are included
    for i, move in enumerate(moves):
      assert move["llm_response"] == f"LLM response for move {i + 1}"

    # Test timing data
    for move in moves:
      assert move["thinking_time_ms"] > 0
      assert move["api_call_time_ms"] > 0
      assert move["total_time_ms"] > 0

  @pytest.mark.asyncio
  async def test_game_detail_incomplete_game(
      self, client, mock_query_engine, sample_game_records
  ):
    """Test game detail for incomplete game."""
    # Setup mock with incomplete game (last game in sample)
    game_record = sample_game_records[4]  # Last game is incomplete
    moves_data = []

    mock_query_engine.storage_manager.get_game.return_value = game_record
    mock_query_engine.storage_manager.get_moves.return_value = moves_data

    response = client.get("/api/games/game_4")

    assert response.status_code == 200
    data = response.json()

    game = data["game"]
    assert game["is_completed"] is False
    assert game["outcome"] is None
    assert game["end_time"] is None

  @pytest.mark.asyncio
  async def test_game_detail_edge_case_moves(
      self, client, mock_query_engine, sample_game_records
  ):
    """Test game detail with edge case move data."""
    # Setup mock with moves that have missing optional fields
    game_record = sample_game_records[0]
    
    # Create a simple object with only required attributes
    class MoveWithMissingFields:
      def __init__(self):
        self.move_number = 1
        self.player = 0
        self.move_uci = "e2e4"  # No move_san attribute
        self.fen_before = "start_position"
        self.fen_after = "after_e4"
        self.is_legal = True
        self.parsing_success = True
        self.thinking_time_ms = 1000
        self.api_call_time_ms = 500
        self.total_time_ms = 1500
        self.had_rethink = False
        self.rethink_attempts = []
        self.blunder_flag = False
        # No move_quality_score attribute
        # No raw_response attribute
    
    edge_case_move = MoveWithMissingFields()

    moves_data = [edge_case_move]

    mock_query_engine.storage_manager.get_game.return_value = game_record
    mock_query_engine.storage_manager.get_moves.return_value = moves_data

    response = client.get("/api/games/game_0")

    assert response.status_code == 200
    data = response.json()

    move = data["game"]["moves"][0]
    assert move["move_notation"] == "e2e4"  # Should fallback to move_uci
    assert move["move_quality_score"] is None
    assert move["llm_response"] is None

  @pytest.mark.asyncio
  async def test_game_detail_large_game(
      self, client, mock_query_engine, sample_game_records
  ):
    """Test game detail with a large number of moves."""
    # Setup mock with many moves
    game_record = sample_game_records[0]
    
    # Create 100 moves
    large_moves_data = []
    for i in range(100):
      move = MagicMock()
      move.move_number = i + 1
      move.player = i % 2
      move.move_san = f"Move{i + 1}"
      move.move_uci = f"move{i + 1}"
      move.fen_before = f"fen_before_{i}"
      move.fen_after = f"fen_after_{i}"
      move.is_legal = True
      move.parsing_success = True
      move.thinking_time_ms = 1000
      move.api_call_time_ms = 500
      move.total_time_ms = 1500
      move.had_rethink = False
      move.rethink_attempts = []
      move.blunder_flag = False
      move.move_quality_score = 0.8
      move.raw_response = f"Response {i + 1}"
      large_moves_data.append(move)

    mock_query_engine.storage_manager.get_game.return_value = game_record
    mock_query_engine.storage_manager.get_moves.return_value = large_moves_data

    response = client.get("/api/games/game_0")

    assert response.status_code == 200
    data = response.json()

    game = data["game"]
    assert len(game["moves"]) == 100
    assert game["moves"][0]["move_number"] == 1
    assert game["moves"][99]["move_number"] == 100

  @pytest.mark.asyncio
  async def test_get_game_detail_not_found(self, client, mock_query_engine):
    """Test game detail with non-existent game ID."""
    from game_arena.storage.exceptions import GameNotFoundError as StorageGameNotFoundError

    # Setup mock to raise GameNotFoundError
    mock_query_engine.storage_manager.get_game.side_effect = (
        StorageGameNotFoundError("Game not found")
    )

    response = client.get("/api/games/nonexistent_game")

    assert response.status_code == 404
    data = response.json()
    assert "Game nonexistent_game not found" in data["detail"]

  @pytest.mark.asyncio
  async def test_get_game_detail_moves_error(
      self, client, mock_query_engine, sample_game_records
  ):
    """Test error handling when moves retrieval fails."""
    # Setup mocks
    game_record = sample_game_records[0]
    mock_query_engine.storage_manager.get_game.return_value = game_record
    mock_query_engine.storage_manager.get_moves.side_effect = Exception(
        "Moves database error"
    )

    response = client.get("/api/games/game_0")

    assert response.status_code == 500
    data = response.json()
    assert "Failed to retrieve game details" in data["detail"]

  @pytest.mark.asyncio
  async def test_get_game_detail_error_handling(
      self, client, mock_query_engine
  ):
    """Test error handling in game detail endpoint."""
    # Setup mock to raise a general exception
    mock_query_engine.storage_manager.get_game.side_effect = Exception(
        "Database error"
    )

    response = client.get("/api/games/game_0")

    assert response.status_code == 500
    data = response.json()
    assert "Failed to retrieve game details" in data["detail"]

  @pytest.mark.asyncio
  async def test_game_detail_special_characters_game_id(
      self, client, mock_query_engine, sample_game_records
  ):
    """Test game detail endpoint with special characters in game ID."""
    game_record = sample_game_records[0]
    game_record.game_id = "game-with-special_chars.123"
    
    mock_query_engine.storage_manager.get_game.return_value = game_record
    mock_query_engine.storage_manager.get_moves.return_value = []

    # URL encode the game ID
    response = client.get("/api/games/game-with-special_chars.123")

    assert response.status_code == 200
    data = response.json()
    assert data["game"]["game_id"] == "game-with-special_chars.123"
