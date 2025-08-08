"""
Performance tests for the games API endpoints.

This module tests response times and ensures they meet requirements.
"""

import time
import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient

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
def performance_test_app(mock_storage_manager, mock_query_engine):
  """Create a test FastAPI application for performance testing."""
  app = create_app()

  # Override the lifespan to avoid actual storage initialization
  app.state.storage_manager = mock_storage_manager
  app.state.query_engine = mock_query_engine

  return app


@pytest.fixture
def performance_client(performance_test_app):
  """Create a test client for performance testing."""
  return TestClient(performance_test_app)


class TestGameDetailPerformance:
  """Performance tests for game detail endpoint."""

  def create_large_game_with_moves(self, num_moves):
    """Create a game record with specified number of moves."""
    # Create game record
    game_record = MagicMock()
    game_record.game_id = f"perf_test_game_{num_moves}"
    game_record.tournament_id = "performance_test"
    from datetime import datetime, timezone

    game_record.start_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    game_record.end_time = datetime(2024, 1, 1, 13, 0, 0, tzinfo=timezone.utc)
    game_record.total_moves = num_moves
    game_record.is_completed = True
    game_record.initial_fen = (
        "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    )
    game_record.final_fen = (
        "r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3"
    )

    # Mock players
    game_record.players = {
        "0": MagicMock(
            player_id="performance_player_white",
            model_name="performance_model_white",
            model_provider="test_provider",
            agent_type="ChessLLMAgent",
            elo_rating=1500,
        ),
        "1": MagicMock(
            player_id="performance_player_black",
            model_name="performance_model_black",
            model_provider="test_provider",
            agent_type="ChessLLMAgent",
            elo_rating=1500,
        ),
    }

    # Mock outcome
    game_record.outcome = MagicMock()
    game_record.outcome.result = MagicMock()
    game_record.outcome.result.value = "WHITE_WINS"
    game_record.outcome.winner = 0
    game_record.outcome.termination = MagicMock()
    game_record.outcome.termination.value = "CHECKMATE"
    game_record.outcome.termination_details = None

    # Create moves
    moves = []
    for i in range(num_moves):
      move = MagicMock()
      move.move_number = i + 1
      move.player = i % 2
      move.move_san = f"Move{i + 1}"
      move.move_uci = f"move{i + 1}_uci"
      move.fen_before = f"fen_before_{i}"
      move.fen_after = f"fen_after_{i}"
      move.is_legal = True
      move.parsing_success = True
      move.thinking_time_ms = 1000
      move.api_call_time_ms = 200
      move.total_time_ms = 1200
      move.had_rethink = i % 10 == 0  # Every 10th move has rethink
      move.rethink_attempts = ["rethink"] if i % 10 == 0 else []
      move.blunder_flag = i % 15 == 0  # Every 15th move is a blunder
      move.move_quality_score = 0.85
      move.raw_response = (
          f"LLM response for move {i + 1} with detailed analysis"
      )
      moves.append(move)

    return game_record, moves

  def test_game_detail_small_game_performance(
      self, performance_client, mock_query_engine
  ):
    """Test performance with small game (10 moves)."""
    game_record, moves = self.create_large_game_with_moves(10)

    mock_query_engine.storage_manager.get_game.return_value = game_record
    mock_query_engine.storage_manager.get_moves.return_value = moves

    # Measure response time
    start_time = time.time()
    response = performance_client.get("/api/games/perf_test_game_10")
    end_time = time.time()

    response_time = end_time - start_time

    assert response.status_code == 200
    data = response.json()
    assert len(data["game"]["moves"]) == 10

    # Response should be very fast for small games (< 100ms)
    assert (
        response_time < 0.1
    ), f"Small game response time {response_time:.3f}s exceeds 100ms"

  def test_game_detail_medium_game_performance(
      self, performance_client, mock_query_engine
  ):
    """Test performance with medium game (100 moves)."""
    game_record, moves = self.create_large_game_with_moves(100)

    mock_query_engine.storage_manager.get_game.return_value = game_record
    mock_query_engine.storage_manager.get_moves.return_value = moves

    # Measure response time
    start_time = time.time()
    response = performance_client.get("/api/games/perf_test_game_100")
    end_time = time.time()

    response_time = end_time - start_time

    assert response.status_code == 200
    data = response.json()
    assert len(data["game"]["moves"]) == 100

    # Response should be under 500ms for medium games
    assert (
        response_time < 0.5
    ), f"Medium game response time {response_time:.3f}s exceeds 500ms"

  def test_game_detail_large_game_performance(
      self, performance_client, mock_query_engine
  ):
    """Test performance with large game (300 moves)."""
    game_record, moves = self.create_large_game_with_moves(300)

    mock_query_engine.storage_manager.get_game.return_value = game_record
    mock_query_engine.storage_manager.get_moves.return_value = moves

    # Measure response time
    start_time = time.time()
    response = performance_client.get("/api/games/perf_test_game_300")
    end_time = time.time()

    response_time = end_time - start_time

    assert response.status_code == 200
    data = response.json()
    assert len(data["game"]["moves"]) == 300

    # Response should be under 2 seconds for large games (as per requirements)
    assert (
        response_time < 2.0
    ), f"Large game response time {response_time:.3f}s exceeds 2s requirement"

    # Verify all data is properly serialized
    for i, move in enumerate(data["game"]["moves"]):
      assert move["move_number"] == i + 1
      assert "llm_response" in move
      assert "thinking_time_ms" in move

  def test_game_detail_very_large_game_performance(
      self, performance_client, mock_query_engine
  ):
    """Test performance with very large game (500 moves)."""
    game_record, moves = self.create_large_game_with_moves(500)

    mock_query_engine.storage_manager.get_game.return_value = game_record
    mock_query_engine.storage_manager.get_moves.return_value = moves

    # Measure response time
    start_time = time.time()
    response = performance_client.get("/api/games/perf_test_game_500")
    end_time = time.time()

    response_time = end_time - start_time

    assert response.status_code == 200
    data = response.json()
    assert len(data["game"]["moves"]) == 500

    # Even very large games should be under 3 seconds
    assert (
        response_time < 3.0
    ), f"Very large game response time {response_time:.3f}s exceeds 3s"

    print(f"Performance test results:")
    print(f"  500 moves: {response_time:.3f}s")

  def test_concurrent_requests_performance(
      self, performance_client, mock_query_engine
  ):
    """Test performance with concurrent requests."""
    import threading

    game_record, moves = self.create_large_game_with_moves(50)
    mock_query_engine.storage_manager.get_game.return_value = game_record
    mock_query_engine.storage_manager.get_moves.return_value = moves

    results = []

    def make_request():
      start_time = time.time()
      response = performance_client.get("/api/games/perf_test_game_50")
      end_time = time.time()
      results.append({
          "status_code": response.status_code,
          "response_time": end_time - start_time,
      })

    # Launch 5 concurrent requests
    threads = []
    for _ in range(5):
      thread = threading.Thread(target=make_request)
      threads.append(thread)
      thread.start()

    # Wait for all threads to complete
    for thread in threads:
      thread.join()

    # Verify all requests succeeded
    for result in results:
      assert result["status_code"] == 200
      assert (
          result["response_time"] < 1.0
      ), f"Concurrent request took {result['response_time']:.3f}s"

    avg_response_time = sum(r["response_time"] for r in results) / len(results)
    print(
        "Average response time for 5 concurrent requests:"
        f" {avg_response_time:.3f}s"
    )


class TestGameListPerformance:
  """Performance tests for game list endpoint."""

  def test_game_list_performance(self, performance_client, mock_query_engine):
    """Test game list endpoint performance with many games."""
    from datetime import datetime, timezone
    # Create 1000 mock games
    games = []
    for i in range(1000):
      game = MagicMock()
      game.game_id = f"perf_game_{i}"
      game.tournament_id = f"tournament_{i % 10}"
      game.start_time = datetime(
          2024, 1, 1, 12 + (i % 10), 0, 0, tzinfo=timezone.utc
      )
      game.end_time = datetime(
          2024, 1, 1, 13 + (i % 10), 0, 0, tzinfo=timezone.utc
      )
      game.total_moves = 50 + (i % 50)
      game.is_completed = True
      game.players = {
          "0": MagicMock(
              player_id=f"player_{i}_white",
              model_name=f"model_{i % 5}",
              model_provider=f"provider_{i % 3}",
              agent_type="ChessLLMAgent",
          ),
          "1": MagicMock(
              player_id=f"player_{i}_black",
              model_name=f"model_{(i + 1) % 5}",
              model_provider=f"provider_{(i + 1) % 3}",
              agent_type="ChessLLMAgent",
          ),
      }
      game.outcome = MagicMock()
      game.outcome.result = MagicMock()
      game.outcome.result.value = "WHITE_WINS" if i % 2 == 0 else "BLACK_WINS"
      game.outcome.winner = i % 2
      game.outcome.termination = MagicMock()
      game.outcome.termination.value = "CHECKMATE"
      game.outcome.termination_details = None
      games.append(game)

    mock_query_engine.query_games_advanced.return_value = games[
        :50
    ]  # Return first 50
    mock_query_engine.count_games_advanced.return_value = 1000

    # Measure response time
    start_time = time.time()
    response = performance_client.get("/api/games?page=1&limit=50")
    end_time = time.time()

    response_time = end_time - start_time

    assert response.status_code == 200
    data = response.json()
    assert len(data["games"]) == 50
    assert data["pagination"]["total_count"] == 1000

    # Game list should be fast even with large datasets
    assert (
        response_time < 1.0
    ), f"Game list response time {response_time:.3f}s exceeds 1s"

    print(
        f"Game list performance: {response_time:.3f}s for 50 games from 1000"
        " total"
    )
