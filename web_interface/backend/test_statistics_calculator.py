"""
Comprehensive tests for the accurate statistics calculator.

This module tests the statistics calculation accuracy, data validation,
error handling, and leaderboard generation functionality.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock
from typing import List

from statistics_calculator import (
    AccurateStatisticsCalculator, 
    DataValidator, 
    AccuratePlayerStatistics,
    DataQualityMetrics,
    LeaderboardEntry
)
from game_arena.storage.models import GameRecord, PlayerInfo, GameOutcome, GameResult, TerminationReason
from elo_rating import ELORatingSystem


class TestDataValidator:
    """Test cases for the data validator."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.validator = DataValidator()
    
    def create_valid_game(self) -> GameRecord:
        """Create a valid game record for testing."""
        return GameRecord(
            game_id="test_game_1",
            start_time=datetime.now(),
            end_time=datetime.now() + timedelta(minutes=30),
            players={
                0: PlayerInfo(
                    player_id="player1",
                    model_name="TestModel1",
                    model_provider="TestProvider",
                    agent_type="TestAgent",
                    elo_rating=1500.0
                ),
                1: PlayerInfo(
                    player_id="player2", 
                    model_name="TestModel2",
                    model_provider="TestProvider",
                    agent_type="TestAgent",
                    elo_rating=1600.0
                )
            },
            outcome=GameOutcome(
                result=GameResult.WHITE_WINS,
                winner=1,
                termination=TerminationReason.CHECKMATE
            ),
            total_moves=50
        )
    
    def test_validate_valid_game(self):
        """Test validation of a valid game."""
        game = self.create_valid_game()
        is_valid, issues = self.validator.validate_game_for_statistics(game)
        
        assert is_valid is True
        assert len(issues) == 0
    
    def test_validate_game_missing_id(self):
        """Test validation of game with missing ID."""
        game = self.create_valid_game()
        game.game_id = ""
        
        is_valid, issues = self.validator.validate_game_for_statistics(game)
        
        assert is_valid is False
        assert "Missing game ID" in issues
    
    def test_validate_game_invalid_players(self):
        """Test validation of game with invalid player data."""
        game = self.create_valid_game()
        game.players = {0: game.players[0]}  # Only one player
        
        is_valid, issues = self.validator.validate_game_for_statistics(game)
        
        assert is_valid is False
        assert "Invalid player data" in issues
    
    def test_validate_incomplete_game(self):
        """Test validation of incomplete game."""
        game = self.create_valid_game()
        game.outcome = None
        game.end_time = None
        
        is_valid, issues = self.validator.validate_game_for_statistics(game)
        
        assert is_valid is False
        assert "Game not completed" in issues
        # Note: "Completed game missing outcome" won't appear because game is not completed
    
    def test_validate_game_missing_outcome_result(self):
        """Test validation of game with missing outcome result."""
        game = self.create_valid_game()
        game.outcome.result = None
        
        is_valid, issues = self.validator.validate_game_for_statistics(game)
        
        assert is_valid is False
        assert "Outcome missing result" in issues
    
    def test_validate_player_info_valid(self):
        """Test validation of valid player info."""
        player_info = PlayerInfo(
            player_id="test_player",
            model_name="TestModel",
            model_provider="TestProvider",
            agent_type="TestAgent",
            elo_rating=1500.0
        )
        
        is_valid, issues = self.validator.validate_player_info(player_info)
        
        assert is_valid is True
        assert len(issues) == 0
    
    def test_validate_player_info_missing_fields(self):
        """Test validation of player info with missing fields."""
        # Create a mock player info object that bypasses __post_init__ validation
        from dataclasses import dataclass
        
        @dataclass
        class MockPlayerInfo:
            player_id: str = ""
            model_name: str = ""
            model_provider: str = ""
            agent_type: str = "TestAgent"
            elo_rating: float = None
        
        player_info = MockPlayerInfo()
        
        is_valid, issues = self.validator.validate_player_info(player_info)
        
        assert is_valid is False
        assert "Missing player ID" in issues
        assert "Missing model name" in issues
        assert "Missing model provider" in issues
    
    def test_validate_player_info_invalid_elo(self):
        """Test validation of player info with invalid ELO rating."""
        player_info = PlayerInfo(
            player_id="test_player",
            model_name="TestModel",
            model_provider="TestProvider",
            agent_type="TestAgent",
            elo_rating=5000.0  # Too high
        )
        
        is_valid, issues = self.validator.validate_player_info(player_info)
        
        assert is_valid is False
        assert "ELO rating out of reasonable range" in issues


class TestAccurateStatisticsCalculator:
    """Test cases for the accurate statistics calculator."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_query_engine = Mock()
        self.mock_query_engine.get_games_by_players = AsyncMock()
        self.mock_query_engine.storage_manager = Mock()
        self.mock_query_engine.storage_manager.query_games = AsyncMock()
        
        self.calculator = AccurateStatisticsCalculator(self.mock_query_engine)
    
    def create_test_games(self, player_id: str, num_games: int = 5) -> List[GameRecord]:
        """Create test games for a player."""
        games = []
        base_time = datetime.now() - timedelta(days=num_games)
        
        for i in range(num_games):
            # Create consistent game outcomes
            if i % 3 == 0:
                # White wins
                result = GameResult.WHITE_WINS
                winner = 1
            elif i % 3 == 1:
                # Black wins
                result = GameResult.BLACK_WINS
                winner = 0
            else:
                # Draw
                result = GameResult.DRAW
                winner = None
            
            game = GameRecord(
                game_id=f"test_game_{i}",
                start_time=base_time + timedelta(days=i),
                end_time=base_time + timedelta(days=i, minutes=30),
                players={
                    0: PlayerInfo(
                        player_id=player_id if i % 2 == 0 else f"opponent_{i}",
                        model_name=f"TestModel{i}",
                        model_provider="TestProvider",
                        agent_type="TestAgent",
                        elo_rating=1500.0 + i * 10
                    ),
                    1: PlayerInfo(
                        player_id=f"opponent_{i}" if i % 2 == 0 else player_id,
                        model_name=f"TestModel{i+10}",
                        model_provider="TestProvider",
                        agent_type="TestAgent",
                        elo_rating=1600.0 + i * 5
                    )
                },
                outcome=GameOutcome(
                    result=result,
                    winner=winner,
                    termination=TerminationReason.CHECKMATE
                ),
                total_moves=40 + i * 5
            )
            games.append(game)
        
        return games
    
    @pytest.mark.asyncio
    async def test_calculate_player_statistics_basic(self):
        """Test basic player statistics calculation."""
        player_id = "test_player"
        test_games = self.create_test_games(player_id, 6)
        
        self.mock_query_engine.get_games_by_players.return_value = test_games
        
        stats = await self.calculator.calculate_player_statistics(player_id)
        
        assert stats is not None
        assert stats.player_id == player_id
        assert stats.total_games == 6
        assert stats.completed_games == 6
        assert stats.wins + stats.losses + stats.draws == stats.completed_games
        assert 0 <= stats.win_rate <= 100
        assert stats.current_elo > 0
    
    @pytest.mark.asyncio
    async def test_calculate_player_statistics_no_games(self):
        """Test statistics calculation when player has no games."""
        player_id = "nonexistent_player"
        
        self.mock_query_engine.get_games_by_players.return_value = []
        
        stats = await self.calculator.calculate_player_statistics(player_id)
        
        assert stats is None
    
    @pytest.mark.asyncio
    async def test_calculate_player_statistics_incomplete_data(self):
        """Test statistics calculation with incomplete data."""
        player_id = "test_player"
        test_games = self.create_test_games(player_id, 3)
        
        # Make some games incomplete
        test_games[0].outcome = None
        test_games[0].end_time = None
        test_games[1].outcome.result = None
        
        self.mock_query_engine.get_games_by_players.return_value = test_games
        
        stats = await self.calculator.calculate_player_statistics(player_id)
        
        assert stats is not None
        assert stats.total_games == 3
        assert stats.completed_games < stats.total_games  # Some games incomplete
        assert stats.data_quality.completeness_percentage < 100.0
        assert stats.data_quality.excluded_games > 0
    
    @pytest.mark.asyncio
    async def test_win_loss_draw_calculation_accuracy(self):
        """Test accurate win/loss/draw calculation."""
        player_id = "test_player"
        
        # Create specific games with known outcomes
        games = []
        
        # Game 1: Player wins as white
        game1 = GameRecord(
            game_id="game1",
            start_time=datetime.now(),
            end_time=datetime.now() + timedelta(minutes=30),
            players={
                0: PlayerInfo(player_id="opponent1", model_name="OpponentModel", 
                             model_provider="TestProvider", agent_type="TestAgent"),
                1: PlayerInfo(player_id=player_id, model_name="PlayerModel",
                             model_provider="TestProvider", agent_type="TestAgent")
            },
            outcome=GameOutcome(result=GameResult.WHITE_WINS, winner=1),
            total_moves=50
        )
        games.append(game1)
        
        # Game 2: Player loses as black
        game2 = GameRecord(
            game_id="game2",
            start_time=datetime.now(),
            end_time=datetime.now() + timedelta(minutes=30),
            players={
                0: PlayerInfo(player_id=player_id, model_name="PlayerModel",
                             model_provider="TestProvider", agent_type="TestAgent"),
                1: PlayerInfo(player_id="opponent2", model_name="OpponentModel",
                             model_provider="TestProvider", agent_type="TestAgent")
            },
            outcome=GameOutcome(result=GameResult.WHITE_WINS, winner=1),
            total_moves=45
        )
        games.append(game2)
        
        # Game 3: Draw
        game3 = GameRecord(
            game_id="game3",
            start_time=datetime.now(),
            end_time=datetime.now() + timedelta(minutes=30),
            players={
                0: PlayerInfo(player_id=player_id, model_name="PlayerModel",
                             model_provider="TestProvider", agent_type="TestAgent"),
                1: PlayerInfo(player_id="opponent3", model_name="OpponentModel",
                             model_provider="TestProvider", agent_type="TestAgent")
            },
            outcome=GameOutcome(result=GameResult.DRAW, winner=None),
            total_moves=60
        )
        games.append(game3)
        
        self.mock_query_engine.get_games_by_players.return_value = games
        
        stats = await self.calculator.calculate_player_statistics(player_id)
        
        assert stats is not None
        assert stats.wins == 1  # Won game 1
        assert stats.losses == 1  # Lost game 2
        assert stats.draws == 1  # Drew game 3
        assert stats.completed_games == 3
        assert abs(stats.win_rate - 33.33) < 0.1  # 1/3 * 100
        assert abs(stats.draw_rate - 33.33) < 0.1  # 1/3 * 100
        assert abs(stats.loss_rate - 33.33) < 0.1  # 1/3 * 100
    
    @pytest.mark.asyncio
    async def test_elo_calculation_progression(self):
        """Test ELO rating calculation and progression."""
        player_id = "test_player"
        
        # Create games with known ELO progression
        games = []
        base_time = datetime.now() - timedelta(days=3)
        
        for i in range(3):
            game = GameRecord(
                game_id=f"elo_game_{i}",
                start_time=base_time + timedelta(days=i),
                end_time=base_time + timedelta(days=i, minutes=30),
                players={
                    0: PlayerInfo(
                        player_id=player_id if i % 2 == 0 else f"opponent_{i}",
                        model_name="PlayerModel",
                        model_provider="TestProvider",
                        agent_type="TestAgent",
                        elo_rating=1500.0
                    ),
                    1: PlayerInfo(
                        player_id=f"opponent_{i}" if i % 2 == 0 else player_id,
                        model_name="OpponentModel",
                        model_provider="TestProvider", 
                        agent_type="TestAgent",
                        elo_rating=1500.0
                    )
                },
                outcome=GameOutcome(
                    result=GameResult.WHITE_WINS,
                    winner=1,  # White wins
                    termination=TerminationReason.CHECKMATE
                ),
                total_moves=50
            )
            games.append(game)
        
        self.mock_query_engine.get_games_by_players.return_value = games
        
        stats = await self.calculator.calculate_player_statistics(player_id)
        
        assert stats is not None
        assert stats.current_elo != 1500.0  # Should have changed from default
        assert len(stats.elo_history) > 1  # Should have history entries
        assert stats.peak_elo >= stats.current_elo  # Peak should be >= current
    
    @pytest.mark.asyncio
    async def test_recent_performance_calculation(self):
        """Test recent performance and streak calculation."""
        player_id = "test_player"
        
        # Create games with specific recent pattern: W-W-L-W-D
        games = []
        results = [
            (GameResult.WHITE_WINS, 1),  # Win (player as white)
            (GameResult.BLACK_WINS, 0),  # Win (player as black)
            (GameResult.WHITE_WINS, 1),  # Loss (player as black)
            (GameResult.BLACK_WINS, 0),  # Win (player as black)
            (GameResult.DRAW, None)      # Draw
        ]
        
        base_time = datetime.now() - timedelta(days=5)
        
        for i, (result, winner) in enumerate(results):
            game = GameRecord(
                game_id=f"recent_game_{i}",
                start_time=base_time + timedelta(days=i),
                end_time=base_time + timedelta(days=i, minutes=30),
                players={
                    0: PlayerInfo(
                        player_id=player_id if i % 2 == 0 else f"opponent_{i}",
                        model_name="PlayerModel",
                        model_provider="TestProvider",
                        agent_type="TestAgent"
                    ),
                    1: PlayerInfo(
                        player_id=f"opponent_{i}" if i % 2 == 0 else player_id,
                        model_name="OpponentModel",
                        model_provider="TestProvider",
                        agent_type="TestAgent"
                    )
                },
                outcome=GameOutcome(result=result, winner=winner),
                total_moves=50
            )
            games.append(game)
        
        self.mock_query_engine.get_games_by_players.return_value = games
        
        stats = await self.calculator.calculate_player_statistics(player_id)
        
        assert stats is not None
        assert len(stats.recent_games) <= 10  # Should limit to last 10 games
        assert stats.current_streak >= 0
        assert stats.streak_type in ["win", "loss", "draw", "none"]
        assert stats.longest_win_streak >= 0
    
    @pytest.mark.asyncio
    async def test_data_quality_metrics(self):
        """Test data quality metrics calculation."""
        player_id = "test_player"
        test_games = self.create_test_games(player_id, 5)
        
        # Make some games have quality issues
        test_games[0].outcome = None  # Incomplete
        test_games[1].end_time = None  # Missing end time
        test_games[2].total_moves = -1  # Invalid move count
        
        self.mock_query_engine.get_games_by_players.return_value = test_games
        
        stats = await self.calculator.calculate_player_statistics(player_id)
        
        assert stats is not None
        assert stats.data_quality.total_games == 5
        assert stats.data_quality.complete_games < 5
        assert stats.data_quality.excluded_games > 0
        assert stats.data_quality.completeness_percentage < 100.0
        assert stats.data_quality.confidence_level < 1.0
        assert len(stats.data_quality.exclusion_reasons) > 0
    
    @pytest.mark.asyncio
    async def test_generate_accurate_leaderboard(self):
        """Test accurate leaderboard generation."""
        # Mock multiple players with different statistics
        player_games = {
            "player1": self.create_test_games("player1", 10),
            "player2": self.create_test_games("player2", 8),
            "player3": self.create_test_games("player3", 6)
        }
        
        # Mock the storage manager to return all games
        all_games = []
        for games in player_games.values():
            all_games.extend(games)
        
        self.mock_query_engine.storage_manager.query_games.return_value = all_games
        
        # Mock get_games_by_players to return appropriate games for each player
        async def mock_get_games_by_players(player_id):
            return player_games.get(player_id, [])
        
        self.mock_query_engine.get_games_by_players.side_effect = mock_get_games_by_players
        
        leaderboard = await self.calculator.generate_accurate_leaderboard(
            sort_by="elo_rating",
            min_games=5,
            limit=10
        )
        
        assert len(leaderboard) <= 10
        assert all(isinstance(entry, LeaderboardEntry) for entry in leaderboard)
        assert all(entry.statistics.completed_games >= 5 for entry in leaderboard)
        
        # Check that rankings are assigned correctly
        for i, entry in enumerate(leaderboard):
            assert entry.rank == i + 1
        
        # Check that entries are sorted by the specified criteria
        if len(leaderboard) > 1:
            for i in range(len(leaderboard) - 1):
                assert leaderboard[i].ranking_score >= leaderboard[i + 1].ranking_score
    
    @pytest.mark.asyncio
    async def test_error_handling_invalid_player(self):
        """Test error handling for invalid player data."""
        self.mock_query_engine.get_games_by_players.side_effect = Exception("Database error")
        
        stats = await self.calculator.calculate_player_statistics("invalid_player")
        
        assert stats is None  # Should handle error gracefully
    
    @pytest.mark.asyncio
    async def test_performance_with_large_dataset(self):
        """Test performance with a large number of games."""
        player_id = "prolific_player"
        large_game_set = self.create_test_games(player_id, 100)
        
        self.mock_query_engine.get_games_by_players.return_value = large_game_set
        
        # This should complete without timeout or memory issues
        stats = await self.calculator.calculate_player_statistics(player_id)
        
        assert stats is not None
        assert stats.total_games == 100
        assert stats.current_elo > 0
        assert len(stats.elo_history) > 1


if __name__ == "__main__":
    pytest.main([__file__])