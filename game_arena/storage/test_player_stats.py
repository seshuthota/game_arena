"""
Unit tests for player statistics functionality in the Game Arena storage system.

Tests cover ELO rating calculations, player statistics tracking, head-to-head
analysis, and performance trends as specified in requirements 4.1, 4.2, and 4.3.
"""

import pytest
import pytest_asyncio
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

from .manager import StorageManager
from .models import (
    GameRecord, MoveRecord, PlayerInfo, PlayerStats, GameOutcome, 
    GameResult, TerminationReason, RethinkAttempt
)
from .config import StorageConfig, LogLevel
from .exceptions import StorageError, ValidationError


class MockStorageBackend:
    """Mock storage backend for testing."""
    
    def __init__(self):
        self.games = {}
        self.moves = {}
        self.player_stats = {}
        self.is_connected = True
    
    async def connect(self):
        pass
    
    async def disconnect(self):
        pass
    
    async def initialize_schema(self):
        pass
    
    async def create_game(self, game: GameRecord) -> str:
        self.games[game.game_id] = game
        return game.game_id
    
    async def get_game(self, game_id: str):
        return self.games.get(game_id)
    
    async def update_game(self, game_id: str, updates: dict) -> bool:
        if game_id in self.games:
            game = self.games[game_id]
            for key, value in updates.items():
                setattr(game, key, value)
            return True
        return False
    
    async def delete_game(self, game_id: str) -> bool:
        if game_id in self.games:
            del self.games[game_id]
            if game_id in self.moves:
                del self.moves[game_id]
            return True
        return False
    
    async def add_move(self, move: MoveRecord) -> bool:
        if move.game_id not in self.moves:
            self.moves[move.game_id] = []
        self.moves[move.game_id].append(move)
        return True
    
    async def get_moves(self, game_id: str, limit=None):
        moves = self.moves.get(game_id, [])
        if limit:
            moves = moves[:limit]
        return sorted(moves, key=lambda m: (m.move_number, m.player))
    
    async def get_move(self, game_id: str, move_number: int, player: int):
        moves = self.moves.get(game_id, [])
        for move in moves:
            if move.move_number == move_number and move.player == player:
                return move
        return None
    
    async def update_player_stats(self, player_id: str, stats: PlayerStats) -> bool:
        self.player_stats[player_id] = stats
        return True
    
    async def get_player_stats(self, player_id: str):
        return self.player_stats.get(player_id)
    
    async def query_games(self, filters: dict, limit=None, offset=None):
        games = list(self.games.values())
        
        # Apply filters
        if 'player_id' in filters:
            player_id = filters['player_id']
            games = [g for g in games if any(p.player_id == player_id for p in g.players.values())]
        
        if 'players' in filters:
            player_list = filters['players']
            games = [g for g in games if all(
                any(p.player_id == pid for p in g.players.values()) for pid in player_list
            )]
        
        if 'start_date' in filters:
            start_date = filters['start_date']
            games = [g for g in games if g.start_time >= start_date]
        
        if 'end_date' in filters:
            end_date = filters['end_date']
            games = [g for g in games if g.start_time <= end_date]
        
        # Apply pagination
        if offset:
            games = games[offset:]
        if limit:
            games = games[:limit]
        
        return games
    
    async def count_games(self, filters: dict) -> int:
        games = await self.query_games(filters)
        return len(games)
    
    async def cleanup_old_data(self, older_than: datetime) -> int:
        return 0
    
    async def get_storage_stats(self) -> dict:
        return {
            'total_games': len(self.games),
            'total_moves': sum(len(moves) for moves in self.moves.values()),
            'total_players': len(self.player_stats)
        }


@pytest.fixture
def storage_config():
    """Create a test storage configuration."""
    from .config import DatabaseConfig, StorageBackendType
    
    db_config = DatabaseConfig(
        backend_type=StorageBackendType.SQLITE,
        database=":memory:",
        connection_pool_size=1
    )
    
    return StorageConfig(
        database=db_config,
        enable_data_validation=True,
        log_level=LogLevel.DEBUG
    )


@pytest.fixture
def mock_backend():
    """Create a mock storage backend."""
    return MockStorageBackend()


@pytest_asyncio.fixture
async def storage_manager(mock_backend, storage_config):
    """Create a storage manager with mock backend."""
    manager = StorageManager(mock_backend, storage_config)
    await manager.initialize()
    return manager


@pytest.fixture
def sample_players():
    """Create sample player information."""
    return {
        0: PlayerInfo(
            player_id="player_black",
            model_name="gpt-4",
            model_provider="openai",
            agent_type="ChessLLMAgent",
            elo_rating=1400.0
        ),
        1: PlayerInfo(
            player_id="player_white", 
            model_name="gemini-pro",
            model_provider="google",
            agent_type="ChessRethinkAgent",
            elo_rating=1300.0
        )
    }


@pytest.fixture
def sample_game(sample_players):
    """Create a sample game record."""
    return GameRecord(
        game_id="test_game_001",
        start_time=datetime.now(),
        players=sample_players,
        tournament_id="test_tournament"
    )


@pytest.fixture
def completed_game(sample_game):
    """Create a completed game record."""
    game = sample_game
    game.end_time = game.start_time + timedelta(minutes=30)
    game.outcome = GameOutcome(
        result=GameResult.WHITE_WINS,
        winner=1,
        termination=TerminationReason.CHECKMATE
    )
    game.total_moves = 40
    game.game_duration_seconds = 1800.0
    return game


class TestPlayerStatsValidation:
    """Test player statistics validation."""
    
    @pytest.mark.asyncio
    async def test_validate_player_stats_valid(self, storage_manager):
        """Test validation of valid player stats."""
        stats = PlayerStats(
            player_id="test_player",
            games_played=10,
            wins=6,
            losses=3,
            draws=1,
            illegal_move_rate=0.05,
            average_thinking_time=2500.0,
            elo_rating=1450.0
        )
        
        # Should not raise exception
        storage_manager._validate_player_stats(stats)
    
    @pytest.mark.asyncio
    async def test_validate_player_stats_invalid_counts(self, storage_manager):
        """Test validation with invalid game counts."""
        # This should fail at model creation time due to __post_init__ validation
        with pytest.raises(ValueError, match="Sum of outcomes cannot exceed games played"):
            stats = PlayerStats(
                player_id="test_player",
                games_played=5,
                wins=3,
                losses=2,
                draws=2  # Sum exceeds games_played
            )
    
    @pytest.mark.asyncio
    async def test_validate_player_stats_negative_values(self, storage_manager):
        """Test validation with negative values."""
        # This should fail at model creation time due to __post_init__ validation
        with pytest.raises(ValueError, match="Game counts cannot be negative"):
            stats = PlayerStats(
                player_id="test_player",
                games_played=-1
            )
    
    @pytest.mark.asyncio
    async def test_validate_player_stats_invalid_rates(self, storage_manager):
        """Test validation with invalid rates."""
        # This should fail at model creation time due to __post_init__ validation
        with pytest.raises(ValueError, match="illegal_move_rate must be between 0 and 1"):
            stats = PlayerStats(
                player_id="test_player",
                illegal_move_rate=1.5  # > 1.0
            )


class TestPlayerStatsOperations:
    """Test basic player statistics operations."""
    
    @pytest.mark.asyncio
    async def test_update_player_stats(self, storage_manager):
        """Test updating player statistics."""
        stats = PlayerStats(
            player_id="test_player",
            games_played=5,
            wins=3,
            losses=1,
            draws=1,
            elo_rating=1350.0
        )
        
        result = await storage_manager.update_player_stats("test_player", stats)
        assert result is True
        
        # Verify stats were stored
        retrieved_stats = await storage_manager.get_player_stats("test_player")
        assert retrieved_stats is not None
        assert retrieved_stats.player_id == "test_player"
        assert retrieved_stats.games_played == 5
        assert retrieved_stats.wins == 3
        assert retrieved_stats.elo_rating == 1350.0
    
    @pytest.mark.asyncio
    async def test_get_player_stats_not_found(self, storage_manager):
        """Test getting stats for non-existent player."""
        stats = await storage_manager.get_player_stats("nonexistent_player")
        assert stats is None
    
    @pytest.mark.asyncio
    async def test_calculate_and_update_player_stats_new_player(self, storage_manager):
        """Test calculating stats for a new player with no games."""
        stats = await storage_manager.calculate_and_update_player_stats("new_player")
        
        assert stats.player_id == "new_player"
        assert stats.games_played == 0
        assert stats.wins == 0
        assert stats.losses == 0
        assert stats.draws == 0
        assert stats.elo_rating == 1200.0  # Default ELO


class TestELORatingCalculation:
    """Test ELO rating calculation system."""
    
    @pytest.mark.asyncio
    async def test_calculate_elo_change_equal_ratings(self, storage_manager):
        """Test ELO calculation with equal ratings."""
        # Equal ratings, white wins
        new_black, new_white = storage_manager._calculate_elo_change(
            1400.0, 1400.0, 0.0, 1.0  # Black loses, white wins
        )
        
        # With equal ratings, winner gains 16 points, loser loses 16 points
        assert abs(new_black - 1384.0) < 1.0
        assert abs(new_white - 1416.0) < 1.0
    
    @pytest.mark.asyncio
    async def test_calculate_elo_change_different_ratings(self, storage_manager):
        """Test ELO calculation with different ratings."""
        # Higher rated player wins against lower rated player
        new_black, new_white = storage_manager._calculate_elo_change(
            1500.0, 1300.0, 1.0, 0.0  # Black (higher) wins against white (lower)
        )
        
        # Higher rated player should gain fewer points when winning against lower rated player
        assert new_black > 1500.0
        assert new_white < 1300.0
        # The higher rated player gains fewer points than they would against an equal opponent
        black_gain = new_black - 1500.0
        white_loss = 1300.0 - new_white
        assert black_gain < 16.0  # Less than the 16 points gained against equal opponent
        assert white_loss < 16.0  # Less than the 16 points lost against equal opponent
    
    @pytest.mark.asyncio
    async def test_calculate_elo_change_draw(self, storage_manager):
        """Test ELO calculation for a draw."""
        new_black, new_white = storage_manager._calculate_elo_change(
            1400.0, 1400.0, 0.5, 0.5  # Draw
        )
        
        # With equal ratings and a draw, ratings should remain the same
        assert abs(new_black - 1400.0) < 0.1
        assert abs(new_white - 1400.0) < 0.1
    
    @pytest.mark.asyncio
    async def test_update_elo_ratings(self, storage_manager, completed_game):
        """Test updating ELO ratings after a completed game."""
        # Create the game first
        await storage_manager.create_game(completed_game)
        
        # Create initial player stats
        black_stats = PlayerStats(player_id="player_black", elo_rating=1400.0)
        white_stats = PlayerStats(player_id="player_white", elo_rating=1300.0)
        await storage_manager.update_player_stats("player_black", black_stats)
        await storage_manager.update_player_stats("player_white", white_stats)
        
        # Update ELO ratings (white wins)
        new_ratings = await storage_manager.update_elo_ratings(completed_game)
        
        assert "player_black" in new_ratings
        assert "player_white" in new_ratings
        assert new_ratings["player_black"] < 1400.0  # Black lost, rating decreases
        assert new_ratings["player_white"] > 1300.0  # White won, rating increases
    
    @pytest.mark.asyncio
    async def test_update_elo_ratings_new_players(self, storage_manager, completed_game):
        """Test updating ELO ratings for new players."""
        # Create the game first
        await storage_manager.create_game(completed_game)
        
        # Don't create initial stats - should use defaults
        new_ratings = await storage_manager.update_elo_ratings(completed_game)
        
        assert "player_black" in new_ratings
        assert "player_white" in new_ratings
        
        # Verify default stats were created
        black_stats = await storage_manager.get_player_stats("player_black")
        white_stats = await storage_manager.get_player_stats("player_white")
        assert black_stats is not None
        assert white_stats is not None


class TestPlayerStatsCalculation:
    """Test comprehensive player statistics calculation."""
    
    @pytest.mark.asyncio
    async def test_calculate_player_stats_with_games(self, storage_manager, sample_players):
        """Test calculating player stats from actual game data."""
        # Create multiple games for a player
        games = []
        for i in range(3):
            game = GameRecord(
                game_id=f"game_{i}",
                start_time=datetime.now() - timedelta(days=i),
                players=sample_players,
                end_time=datetime.now() - timedelta(days=i) + timedelta(hours=1),
                total_moves=30 + i * 5,
                game_duration_seconds=3600.0
            )
            
            # Set outcomes: player_white wins 2, player_black wins 1
            if i < 2:
                game.outcome = GameOutcome(
                    result=GameResult.WHITE_WINS,
                    winner=1,
                    termination=TerminationReason.CHECKMATE
                )
            else:
                game.outcome = GameOutcome(
                    result=GameResult.BLACK_WINS,
                    winner=0,
                    termination=TerminationReason.CHECKMATE
                )
            
            games.append(game)
            await storage_manager.create_game(game)
            
            # Add some moves for each game
            for move_num in range(1, 6):  # 5 moves per game
                for player in [0, 1]:
                    move = MoveRecord(
                        game_id=game.game_id,
                        move_number=move_num,
                        player=player,
                        timestamp=datetime.now(),
                        fen_before="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
                        fen_after="rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1",
                        legal_moves=["e4", "d4", "Nf3"],
                        move_san="e4",
                        move_uci="e2e4",
                        is_legal=True,
                        prompt_text="Make a move",
                        raw_response="I'll play e4",
                        thinking_time_ms=2000 + i * 100,  # Varying thinking times
                        parsing_success=True
                    )
                    await storage_manager.add_move(move)
        
        # Calculate stats for white player
        stats = await storage_manager.calculate_and_update_player_stats("player_white")
        
        assert stats.player_id == "player_white"
        assert stats.games_played == 3
        assert stats.wins == 2
        assert stats.losses == 1
        assert stats.draws == 0
        assert stats.win_rate == 2/3
        assert stats.illegal_move_rate == 0.0  # All moves were legal
        assert stats.average_thinking_time > 0  # Should have calculated average
    
    @pytest.mark.asyncio
    async def test_calculate_player_stats_with_illegal_moves(self, storage_manager, sample_players):
        """Test calculating stats with illegal moves."""
        # Create a game
        game = GameRecord(
            game_id="test_game",
            start_time=datetime.now(),
            players=sample_players,
            end_time=datetime.now() + timedelta(hours=1),
            outcome=GameOutcome(result=GameResult.DRAW, termination=TerminationReason.STALEMATE),
            total_moves=10
        )
        await storage_manager.create_game(game)
        
        # Add moves with some illegal ones
        for move_num in range(1, 6):
            move = MoveRecord(
                game_id="test_game",
                move_number=move_num,
                player=0,  # Black player
                timestamp=datetime.now(),
                fen_before="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
                fen_after="rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1",
                legal_moves=["e4", "d4", "Nf3"],
                move_san="e4",
                move_uci="e2e4",
                is_legal=(move_num % 2 == 1),  # Every other move is illegal
                prompt_text="Make a move",
                raw_response="I'll play e4",
                thinking_time_ms=2000
            )
            await storage_manager.add_move(move)
        
        stats = await storage_manager.calculate_and_update_player_stats("player_black")
        
        assert stats.illegal_move_rate == 0.4  # 2 out of 5 moves were illegal


class TestHeadToHeadStats:
    """Test head-to-head statistics functionality."""
    
    @pytest.mark.asyncio
    async def test_get_head_to_head_stats(self, storage_manager, sample_players):
        """Test getting head-to-head statistics between two players."""
        # Create multiple games between the same players
        for i in range(3):
            game = GameRecord(
                game_id=f"h2h_game_{i}",
                start_time=datetime.now() - timedelta(days=i),
                players=sample_players,
                end_time=datetime.now() - timedelta(days=i) + timedelta(hours=1),
                total_moves=30
            )
            
            # Vary the outcomes
            if i == 0:
                game.outcome = GameOutcome(result=GameResult.WHITE_WINS, winner=1)
            elif i == 1:
                game.outcome = GameOutcome(result=GameResult.BLACK_WINS, winner=0)
            else:
                game.outcome = GameOutcome(result=GameResult.DRAW)
            
            await storage_manager.create_game(game)
        
        # Get head-to-head stats
        h2h_stats = await storage_manager.get_head_to_head_stats("player_black", "player_white")
        
        assert h2h_stats['total_games'] == 3
        assert h2h_stats['completed_games'] == 3
        assert h2h_stats['player1_wins'] == 1  # player_black wins
        assert h2h_stats['player2_wins'] == 1  # player_white wins
        assert h2h_stats['draws'] == 1
        assert abs(h2h_stats['player1_win_rate'] - 1/3) < 0.01
        assert abs(h2h_stats['player2_win_rate'] - 1/3) < 0.01
        assert abs(h2h_stats['draw_rate'] - 1/3) < 0.01
        assert len(h2h_stats['games']) == 3
    
    @pytest.mark.asyncio
    async def test_get_head_to_head_stats_no_games(self, storage_manager):
        """Test head-to-head stats with no games between players."""
        h2h_stats = await storage_manager.get_head_to_head_stats("player1", "player2")
        
        assert h2h_stats['total_games'] == 0
        assert h2h_stats['player1_wins'] == 0
        assert h2h_stats['player2_wins'] == 0
        assert h2h_stats['draws'] == 0
        assert h2h_stats['player1_win_rate'] == 0.0
        assert len(h2h_stats['games']) == 0


class TestPerformanceTrends:
    """Test player performance trends functionality."""
    
    @pytest.mark.asyncio
    async def test_get_player_performance_trends(self, storage_manager, sample_players):
        """Test getting player performance trends over time."""
        # Create games over several days
        base_date = datetime.now() - timedelta(days=10)
        
        for i in range(5):
            game = GameRecord(
                game_id=f"trend_game_{i}",
                start_time=base_date + timedelta(days=i * 2),
                players=sample_players,
                end_time=base_date + timedelta(days=i * 2, hours=1),
                total_moves=30,
                game_duration_seconds=3600.0
            )
            
            # Vary outcomes to show trends
            if i < 3:
                game.outcome = GameOutcome(result=GameResult.WHITE_WINS, winner=1)
            else:
                game.outcome = GameOutcome(result=GameResult.BLACK_WINS, winner=0)
            
            await storage_manager.create_game(game)
        
        # Get performance trends for white player
        trends = await storage_manager.get_player_performance_trends("player_white", days=15)
        
        assert trends['period_days'] == 15
        assert trends['total_games'] == 5
        assert trends['completed_games'] == 5
        assert trends['wins'] == 3
        assert trends['losses'] == 2
        assert trends['draws'] == 0
        assert trends['win_rate'] == 0.6
        assert len(trends['daily_performance']) > 0
    
    @pytest.mark.asyncio
    async def test_get_player_performance_trends_no_games(self, storage_manager):
        """Test performance trends with no games."""
        trends = await storage_manager.get_player_performance_trends("new_player", days=30)
        
        assert trends['total_games'] == 0
        assert trends['wins'] == 0
        assert trends['losses'] == 0
        assert trends['draws'] == 0
        assert trends['win_rate'] == 0.0
        assert trends['daily_performance'] == []


class TestBulkOperations:
    """Test bulk player statistics operations."""
    
    @pytest.mark.asyncio
    async def test_update_all_player_stats(self, storage_manager, sample_players):
        """Test updating statistics for all players."""
        # Create games for multiple players
        game1 = GameRecord(
            game_id="bulk_game_1",
            start_time=datetime.now(),
            players=sample_players,
            end_time=datetime.now() + timedelta(hours=1),
            outcome=GameOutcome(result=GameResult.WHITE_WINS, winner=1),
            total_moves=30
        )
        await storage_manager.create_game(game1)
        
        # Create another set of players
        other_players = {
            0: PlayerInfo(
                player_id="player_c",
                model_name="claude-3",
                model_provider="anthropic",
                agent_type="ChessLLMAgent"
            ),
            1: PlayerInfo(
                player_id="player_d",
                model_name="gpt-3.5",
                model_provider="openai", 
                agent_type="ChessLLMAgent"
            )
        }
        
        game2 = GameRecord(
            game_id="bulk_game_2",
            start_time=datetime.now(),
            players=other_players,
            end_time=datetime.now() + timedelta(hours=1),
            outcome=GameOutcome(result=GameResult.BLACK_WINS, winner=0),
            total_moves=25
        )
        await storage_manager.create_game(game2)
        
        # Update all player stats
        updated_stats = await storage_manager.update_all_player_stats()
        
        # Should have stats for all 4 players
        assert len(updated_stats) == 4
        assert "player_black" in updated_stats
        assert "player_white" in updated_stats
        assert "player_c" in updated_stats
        assert "player_d" in updated_stats
        
        # Verify stats were calculated correctly
        assert updated_stats["player_white"].wins == 1
        assert updated_stats["player_black"].losses == 1
        assert updated_stats["player_c"].wins == 1
        assert updated_stats["player_d"].losses == 1


class TestGameCompletionIntegration:
    """Test integration of player stats with game completion."""
    
    @pytest.mark.asyncio
    async def test_complete_game_updates_player_stats(self, storage_manager, sample_game):
        """Test that completing a game automatically updates player statistics."""
        # Create the game
        await storage_manager.create_game(sample_game)
        
        # Complete the game
        outcome = GameOutcome(
            result=GameResult.WHITE_WINS,
            winner=1,
            termination=TerminationReason.CHECKMATE
        )
        
        success = await storage_manager.complete_game(
            sample_game.game_id,
            outcome,
            "rnbqkb1r/pppp1ppp/5n2/4p3/2B1P3/8/PPPP1PPP/RNBQK1NR w KQkq - 2 3",
            40
        )
        
        assert success is True
        
        # Verify player stats were updated
        black_stats = await storage_manager.get_player_stats("player_black")
        white_stats = await storage_manager.get_player_stats("player_white")
        
        assert black_stats is not None
        assert white_stats is not None
        assert black_stats.games_played == 1
        assert white_stats.games_played == 1
        assert black_stats.losses == 1
        assert white_stats.wins == 1
        
        # Verify ELO ratings were updated (should be different from initial)
        assert black_stats.elo_rating != 1400.0  # Initial rating
        assert white_stats.elo_rating != 1300.0  # Initial rating


if __name__ == "__main__":
    pytest.main([__file__])