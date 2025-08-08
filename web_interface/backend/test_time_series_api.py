"""
Comprehensive unit tests for time-series analytics API functionality.

This module tests the time-series endpoint including data aggregation,
different intervals, metrics, and date filtering.
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
def time_series_test_app(mock_storage_manager, mock_query_engine):
    """Create a test FastAPI application for time-series testing."""
    app = create_app()
    
    # Override the lifespan to avoid actual storage initialization
    app.state.storage_manager = mock_storage_manager
    app.state.query_engine = mock_query_engine
    
    return app


@pytest.fixture
def time_series_client(time_series_test_app):
    """Create a test client for time-series testing."""
    return TestClient(time_series_test_app)


@pytest.fixture
def sample_time_series_games():
    """Create comprehensive sample games for time-series testing."""
    base_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    
    games = []
    
    # Create games across multiple days/weeks/months for testing
    game_configs = [
        # Day 1 - 2 games
        {
            "game_id": "day1_game1",
            "start_time": base_time,  # Jan 1, 2024
            "end_time": base_time + timedelta(hours=1),
            "total_moves": 30,
            "players": ["alice", "bob"]
        },
        {
            "game_id": "day1_game2", 
            "start_time": base_time + timedelta(hours=2),
            "end_time": base_time + timedelta(hours=3),
            "total_moves": 45,
            "players": ["charlie", "david"]
        },
        
        # Day 2 - 1 game
        {
            "game_id": "day2_game1",
            "start_time": base_time + timedelta(days=1),  # Jan 2, 2024
            "end_time": base_time + timedelta(days=1, hours=2),
            "total_moves": 25,
            "players": ["alice", "charlie"]
        },
        
        # Day 8 (next week) - 1 game
        {
            "game_id": "week2_game1",
            "start_time": base_time + timedelta(days=7),  # Jan 8, 2024
            "end_time": base_time + timedelta(days=7, hours=1, minutes=30),
            "total_moves": 40,
            "players": ["bob", "eve"]
        },
        
        # Day 32 (next month) - 1 game
        {
            "game_id": "month2_game1",
            "start_time": base_time + timedelta(days=31),  # Feb 1, 2024
            "end_time": base_time + timedelta(days=31, hours=2, minutes=30),
            "total_moves": 35,
            "players": ["david", "frank"]
        },
        
        # Ongoing game (no end time)
        {
            "game_id": "ongoing_game",
            "start_time": base_time + timedelta(days=2),
            "end_time": None,
            "total_moves": 20,
            "players": ["alice", "eve"]
        }
    ]
    
    for config in game_configs:
        game = MagicMock(spec=GameRecord)
        game.game_id = config["game_id"]
        game.start_time = config["start_time"]
        game.end_time = config["end_time"]
        game.total_moves = config["total_moves"]
        game.is_completed = config["end_time"] is not None
        
        # Mock players
        game.players = {}
        for i, player_id in enumerate(config["players"]):
            game.players[str(i)] = MagicMock(
                player_id=player_id,
                model_name=f"model_{player_id}",
                model_provider="test_provider"
            )
        
        games.append(game)
    
    return games


class TestTimeSeriesValidation:
    """Test cases for time-series parameter validation."""
    
    def test_invalid_metric(self, time_series_client, mock_query_engine):
        """Test invalid metric parameter."""
        response = time_series_client.get("/api/statistics/time-series?metric=invalid_metric")
        
        assert response.status_code == 400
        data = response.json()
        assert "Invalid metric 'invalid_metric'" in data["detail"]
        assert "Valid metrics:" in data["detail"]
        assert "games" in data["detail"]
        assert "moves" in data["detail"]
        assert "duration" in data["detail"]
        assert "players" in data["detail"]
    
    def test_invalid_interval(self, time_series_client, mock_query_engine):
        """Test invalid interval parameter."""
        response = time_series_client.get("/api/statistics/time-series?metric=games&interval=invalid_interval")
        
        assert response.status_code == 400
        data = response.json()
        assert "Invalid interval 'invalid_interval'" in data["detail"]
        assert "Valid intervals:" in data["detail"]
        assert "daily" in data["detail"]
        assert "weekly" in data["detail"]
        assert "monthly" in data["detail"]
    
    def test_missing_metric(self, time_series_client, mock_query_engine):
        """Test missing required metric parameter."""
        response = time_series_client.get("/api/statistics/time-series")
        
        assert response.status_code == 422  # FastAPI validation error


class TestTimeSeriesGamesMetric:
    """Test cases for games metric time-series."""
    
    @pytest.mark.asyncio
    async def test_games_daily_metric(self, time_series_client, mock_query_engine, sample_time_series_games):
        """Test games metric with daily intervals."""
        mock_query_engine.query_games_advanced.return_value = sample_time_series_games
        
        response = time_series_client.get("/api/statistics/time-series?metric=games&interval=daily")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check response structure
        assert "time_series" in data
        assert "success" in data
        assert data["success"] is True
        
        time_series = data["time_series"]
        assert time_series["metric"] == "games"
        assert time_series["interval"] == "daily"
        assert time_series["total_count"] > 0
        
        # Should have multiple data points for different days
        data_points = time_series["data_points"]
        assert len(data_points) >= 3  # At least 3 different days
        
        # Check that timestamps are properly formatted and data makes sense
        for point in data_points:
            assert "timestamp" in point
            assert "value" in point
            assert "count" in point
            assert point["value"] >= 0
            assert point["count"] >= 0
    
    @pytest.mark.asyncio
    async def test_games_weekly_metric(self, time_series_client, mock_query_engine, sample_time_series_games):
        """Test games metric with weekly intervals."""
        mock_query_engine.query_games_advanced.return_value = sample_time_series_games
        
        response = time_series_client.get("/api/statistics/time-series?metric=games&interval=weekly")
        
        assert response.status_code == 200
        data = response.json()
        
        time_series = data["time_series"]
        assert time_series["metric"] == "games"
        assert time_series["interval"] == "weekly"
        
        # Should have fewer data points than daily
        data_points = time_series["data_points"]
        assert len(data_points) >= 2  # At least 2 different weeks
    
    @pytest.mark.asyncio
    async def test_games_monthly_metric(self, time_series_client, mock_query_engine, sample_time_series_games):
        """Test games metric with monthly intervals."""
        mock_query_engine.query_games_advanced.return_value = sample_time_series_games
        
        response = time_series_client.get("/api/statistics/time-series?metric=games&interval=monthly")
        
        assert response.status_code == 200
        data = response.json()
        
        time_series = data["time_series"]
        assert time_series["metric"] == "games"
        assert time_series["interval"] == "monthly"
        
        # Should have fewer data points than weekly
        data_points = time_series["data_points"]
        assert len(data_points) >= 2  # At least 2 different months


class TestTimeSeriesMovesMetric:
    """Test cases for moves metric time-series."""
    
    @pytest.mark.asyncio
    async def test_moves_daily_metric(self, time_series_client, mock_query_engine, sample_time_series_games):
        """Test moves metric with daily intervals."""
        mock_query_engine.query_games_advanced.return_value = sample_time_series_games
        
        response = time_series_client.get("/api/statistics/time-series?metric=moves&interval=daily")
        
        assert response.status_code == 200
        data = response.json()
        
        time_series = data["time_series"]
        assert time_series["metric"] == "moves"
        assert time_series["interval"] == "daily"
        
        # Verify that moves are aggregated correctly
        data_points = time_series["data_points"]
        
        # Find the first day which should have 2 games with 30 + 45 = 75 moves
        first_day_point = data_points[0]
        assert first_day_point["value"] == 75  # 30 + 45 moves from day 1


class TestTimeSeriesDurationMetric:
    """Test cases for duration metric time-series."""
    
    @pytest.mark.asyncio
    async def test_duration_daily_metric(self, time_series_client, mock_query_engine, sample_time_series_games):
        """Test duration metric with daily intervals."""
        mock_query_engine.query_games_advanced.return_value = sample_time_series_games
        
        response = time_series_client.get("/api/statistics/time-series?metric=duration&interval=daily")
        
        assert response.status_code == 200
        data = response.json()
        
        time_series = data["time_series"]
        assert time_series["metric"] == "duration"
        assert time_series["interval"] == "daily"
        
        data_points = time_series["data_points"]
        
        # Duration should be averaged per game in each time bucket
        for point in data_points:
            if point["count"] > 0:  # Only check points with completed games
                assert point["value"] >= 0  # Duration should be non-negative


class TestTimeSeriesPlayersMetric:
    """Test cases for players metric time-series."""
    
    @pytest.mark.asyncio
    async def test_players_daily_metric(self, time_series_client, mock_query_engine, sample_time_series_games):
        """Test players metric with daily intervals."""
        mock_query_engine.query_games_advanced.return_value = sample_time_series_games
        
        response = time_series_client.get("/api/statistics/time-series?metric=players&interval=daily")
        
        assert response.status_code == 200
        data = response.json()
        
        time_series = data["time_series"]
        assert time_series["metric"] == "players"
        assert time_series["interval"] == "daily"
        
        data_points = time_series["data_points"]
        
        # First day should have 4 unique players (alice, bob, charlie, david)
        first_day_point = data_points[0]
        assert first_day_point["value"] == 4
        assert first_day_point["count"] == 4


class TestTimeSeriesDateFiltering:
    """Test cases for date filtering in time-series."""
    
    @pytest.mark.asyncio
    async def test_with_date_filters(self, time_series_client, mock_query_engine, sample_time_series_games):
        """Test time-series with date range filters."""
        mock_query_engine.query_games_advanced.return_value = sample_time_series_games
        
        start_date = "2024-01-01T00:00:00Z"
        end_date = "2024-01-02T23:59:59Z"
        
        response = time_series_client.get(
            f"/api/statistics/time-series?metric=games&interval=daily&start_date={start_date}&end_date={end_date}"
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check that filters are applied correctly
        filters_applied = data["filters_applied"]
        assert "start_date" in filters_applied
        assert "end_date" in filters_applied
        assert filters_applied["metric"] == "games"
        assert filters_applied["interval"] == "daily"


class TestTimeSeriesEdgeCases:
    """Test cases for time-series edge cases."""
    
    @pytest.mark.asyncio
    async def test_empty_data(self, time_series_client, mock_query_engine):
        """Test time-series with no games."""
        mock_query_engine.query_games_advanced.return_value = []
        
        response = time_series_client.get("/api/statistics/time-series?metric=games&interval=daily")
        
        assert response.status_code == 200
        data = response.json()
        
        time_series = data["time_series"]
        assert time_series["metric"] == "games"
        assert time_series["interval"] == "daily"
        assert time_series["total_count"] == 0
        assert len(time_series["data_points"]) == 0
    
    @pytest.mark.asyncio
    async def test_single_data_point(self, time_series_client, mock_query_engine, sample_time_series_games):
        """Test time-series with single game."""
        single_game = [sample_time_series_games[0]]
        mock_query_engine.query_games_advanced.return_value = single_game
        
        response = time_series_client.get("/api/statistics/time-series?metric=games&interval=daily")
        
        assert response.status_code == 200
        data = response.json()
        
        time_series = data["time_series"]
        assert time_series["total_count"] == 1
        assert len(time_series["data_points"]) == 1
        assert time_series["data_points"][0]["value"] == 1
    
    @pytest.mark.asyncio
    async def test_error_handling(self, time_series_client, mock_query_engine):
        """Test error handling in time-series endpoint."""
        mock_query_engine.query_games_advanced.side_effect = Exception("Database error")
        
        response = time_series_client.get("/api/statistics/time-series?metric=games&interval=daily")
        
        assert response.status_code == 500
        data = response.json()
        assert "Failed to generate time series data" in data["detail"]


class TestTimeSeriesHelperFunctions:
    """Test cases for time-series helper functions."""
    
    def test_time_bucket_generation_daily(self):
        """Test daily time bucket generation."""
        from .routes.statistics import _generate_time_buckets
        
        start_date = datetime(2024, 1, 1, 12, 30, 45)
        end_date = datetime(2024, 1, 3, 8, 15, 20)
        
        buckets = _generate_time_buckets(start_date, end_date, "daily")
        
        # Should have 3 days: Jan 1, Jan 2, Jan 3
        assert len(buckets) == 3
        
        expected_dates = [
            datetime(2024, 1, 1, 0, 0, 0),
            datetime(2024, 1, 2, 0, 0, 0),
            datetime(2024, 1, 3, 0, 0, 0)
        ]
        
        for expected_date in expected_dates:
            # Remove timezone info for comparison
            expected_date = expected_date.replace(tzinfo=start_date.tzinfo)
            assert expected_date in buckets
    
    def test_time_bucket_key_generation(self):
        """Test time bucket key generation."""
        from .routes.statistics import _get_time_bucket_key
        
        timestamp = datetime(2024, 1, 15, 14, 30, 45, tzinfo=timezone.utc)
        
        # Daily bucket key
        daily_key = _get_time_bucket_key(timestamp, "daily")
        expected_daily = datetime(2024, 1, 15, 0, 0, 0, tzinfo=timezone.utc)
        assert daily_key == expected_daily
        
        # Weekly bucket key (Monday of that week)
        weekly_key = _get_time_bucket_key(timestamp, "weekly")  # Jan 15 is Monday
        expected_weekly = datetime(2024, 1, 15, 0, 0, 0, tzinfo=timezone.utc)
        assert weekly_key == expected_weekly
        
        # Monthly bucket key
        monthly_key = _get_time_bucket_key(timestamp, "monthly")
        expected_monthly = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        assert monthly_key == expected_monthly