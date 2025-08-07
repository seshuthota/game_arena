"""
Unit tests for the QueryEngine class.

Tests the game filtering, search, and query functionality
to ensure proper data retrieval and filtering operations.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from typing import List

from .query_engine import QueryEngine, GameFilters, MoveFilters
from .models import (
    GameRecord, MoveRecord, PlayerInfo, GameOutcome, RethinkAttempt,
    GameResult, TerminationReason
)
from .exceptions import StorageError, ValidationError


class TestQueryEngine:
    """Test cases for QueryEngine functionality."""
    
    @pytest.fixture
    def mock_storage_manager(self):
        """Create a mock storage manager."""
        return AsyncMock()
    
    @pytest.fixture
    def query_engine(self, mock_storage_manager):
        """Create a QueryEngine instance with mock storage manager."""
        return QueryEngine(mock_storage_manager)
    
    @pytest.fixture
    def sample_players(self):
        """Create sample player info."""
        return {
            0: PlayerInfo(
                player_id="player_black",
                model_name="gpt-4",
                model_provider="openai",
                agent_type="ChessLLMAgent",
                elo_rating=1500.0
            ),
            1: PlayerInfo(
                player_id="player_white",
                model_name="gemini-pro",
                model_provider="google",
                agent_type="ChessRethinkAgent",
                elo_rating=1600.0
            )
        }
    
    @pytest.fixture
    def sample_game(self, sample_players):
        """Create a sample game record."""
        return GameRecord(
            game_id="test_game_001",
            tournament_id="test_tournament",
            start_time=datetime(2024, 1, 15, 10, 0, 0),
            end_time=datetime(2024, 1, 15, 10, 30, 0),
            players=sample_players,
            initial_fen="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
            final_fen="rnbqkb1r/pppp1ppp/5n2/4p3/2B1P3/8/PPPP1PPP/RNBQK1NR w KQkq - 2 3",
            outcome=GameOutcome(
                result=GameResult.WHITE_WINS,
                winner=1,
                termination=TerminationReason.CHECKMATE
            ),
            total_moves=5,
            game_duration_seconds=1800.0
        )
    
    @pytest.fixture
    def sample_games(self, sample_players):
        """Create a list of sample game records."""
        games = []
        
        # Game 1: White wins
        games.append(GameRecord(
            game_id="game_001",
            tournament_id="tournament_1",
            start_time=datetime(2024, 1, 15, 10, 0, 0),
            end_time=datetime(2024, 1, 15, 10, 30, 0),
            players=sample_players,
            outcome=GameOutcome(GameResult.WHITE_WINS, 1, TerminationReason.CHECKMATE),
            total_moves=25
        ))
        
        # Game 2: Black wins
        games.append(GameRecord(
            game_id="game_002",
            tournament_id="tournament_1",
            start_time=datetime(2024, 1, 16, 14, 0, 0),
            end_time=datetime(2024, 1, 16, 14, 45, 0),
            players=sample_players,
            outcome=GameOutcome(GameResult.BLACK_WINS, 0, TerminationReason.RESIGNATION),
            total_moves=40
        ))
        
        # Game 3: Draw
        games.append(GameRecord(
            game_id="game_003",
            tournament_id="tournament_2",
            start_time=datetime(2024, 1, 17, 9, 0, 0),
            end_time=datetime(2024, 1, 17, 9, 20, 0),
            players=sample_players,
            outcome=GameOutcome(GameResult.DRAW, None, TerminationReason.STALEMATE),
            total_moves=15
        ))
        
        return games
    
    @pytest.fixture
    def sample_moves(self):
        """Create sample move records."""
        moves = []
        
        # Legal move
        moves.append(MoveRecord(
            game_id="test_game_001",
            move_number=1,
            player=1,
            timestamp=datetime(2024, 1, 15, 10, 1, 0),
            fen_before="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
            fen_after="rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1",
            legal_moves=["e4", "d4", "Nf3"],
            move_san="e4",
            move_uci="e2e4",
            is_legal=True,
            prompt_text="Make your first move",
            raw_response="I'll play e4",
            parsing_success=True,
            thinking_time_ms=2000,
            api_call_time_ms=500,
            parsing_time_ms=100
        ))
        
        # Illegal move with rethink
        moves.append(MoveRecord(
            game_id="test_game_001",
            move_number=2,
            player=0,
            timestamp=datetime(2024, 1, 15, 10, 2, 0),
            fen_before="rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1",
            fen_after="rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq e6 0 2",
            legal_moves=["e5", "e6", "Nf6"],
            move_san="e5",
            move_uci="e7e5",
            is_legal=True,
            prompt_text="Respond to e4",
            raw_response="I'll play e5",
            parsing_success=True,
            thinking_time_ms=3000,
            api_call_time_ms=800,
            parsing_time_ms=150,
            rethink_attempts=[
                RethinkAttempt(
                    attempt_number=1,
                    prompt_text="That move is illegal, try again",
                    raw_response="Let me play e5 instead",
                    parsed_move="e5",
                    was_legal=True,
                    timestamp=datetime(2024, 1, 15, 10, 1, 30)
                )
            ]
        ))
        
        return moves
    
    # Basic Game Query Tests
    
    @pytest.mark.asyncio
    async def test_get_games_by_players_single_player(self, query_engine, mock_storage_manager, sample_games):
        """Test querying games by single player."""
        mock_storage_manager.query_games.return_value = sample_games
        
        result = await query_engine.get_games_by_players("player_black")
        
        assert len(result) == 3
        mock_storage_manager.query_games.assert_called_once_with({'player_ids': ['player_black']})
    
    @pytest.mark.asyncio
    async def test_get_games_by_players_head_to_head(self, query_engine, mock_storage_manager, sample_games):
        """Test querying head-to-head games between two players."""
        mock_storage_manager.query_games.return_value = sample_games
        
        result = await query_engine.get_games_by_players("player_black", "player_white")
        
        assert len(result) == 3  # All sample games have these two players
        mock_storage_manager.query_games.assert_called_once_with({'players': ['player_black', 'player_white']})
    
    @pytest.mark.asyncio
    async def test_get_games_by_players_storage_error(self, query_engine, mock_storage_manager):
        """Test handling of storage errors in player queries."""
        mock_storage_manager.query_games.side_effect = Exception("Database error")
        
        with pytest.raises(StorageError, match="Player games query failed"):
            await query_engine.get_games_by_players("player_black")
    
    @pytest.mark.asyncio
    async def test_get_games_by_date_range(self, query_engine, mock_storage_manager, sample_games):
        """Test querying games by date range."""
        start_date = datetime(2024, 1, 15)
        end_date = datetime(2024, 1, 17)
        mock_storage_manager.query_games.return_value = sample_games
        
        result = await query_engine.get_games_by_date_range(start_date, end_date)
        
        assert len(result) == 3
        expected_filters = {
            'start_time_after': start_date,
            'start_time_before': end_date
        }
        mock_storage_manager.query_games.assert_called_once_with(expected_filters)
    
    @pytest.mark.asyncio
    async def test_get_games_by_date_range_no_end_date(self, query_engine, mock_storage_manager, sample_games):
        """Test querying games by date range with no end date."""
        start_date = datetime(2024, 1, 15)
        mock_storage_manager.query_games.return_value = sample_games
        
        result = await query_engine.get_games_by_date_range(start_date)
        
        assert len(result) == 3
        # Should use current time as end date
        call_args = mock_storage_manager.query_games.call_args[0][0]
        assert call_args['start_time_after'] == start_date
        assert 'start_time_before' in call_args
    
    @pytest.mark.asyncio
    async def test_get_games_by_date_range_invalid_range(self, query_engine, mock_storage_manager):
        """Test validation of invalid date ranges."""
        start_date = datetime(2024, 1, 17)
        end_date = datetime(2024, 1, 15)  # Before start date
        
        with pytest.raises(ValidationError, match="Start date cannot be after end date"):
            await query_engine.get_games_by_date_range(start_date, end_date)
    
    @pytest.mark.asyncio
    async def test_get_games_by_outcome_single(self, query_engine, mock_storage_manager, sample_games):
        """Test querying games by single outcome."""
        mock_storage_manager.query_games.return_value = sample_games
        
        result = await query_engine.get_games_by_outcome(GameResult.WHITE_WINS)
        
        # Should return only the white wins game
        assert len(result) == 1
        assert result[0].outcome.result == GameResult.WHITE_WINS
    
    @pytest.mark.asyncio
    async def test_get_games_by_outcome_multiple(self, query_engine, mock_storage_manager, sample_games):
        """Test querying games by multiple outcomes."""
        mock_storage_manager.query_games.return_value = sample_games
        
        result = await query_engine.get_games_by_outcome([GameResult.WHITE_WINS, GameResult.DRAW])
        
        # Should return white wins and draw games
        assert len(result) == 2
        outcomes = [game.outcome.result for game in result]
        assert GameResult.WHITE_WINS in outcomes
        assert GameResult.DRAW in outcomes
    
    @pytest.mark.asyncio
    async def test_get_games_by_tournament(self, query_engine, mock_storage_manager, sample_games):
        """Test querying games by tournament."""
        mock_storage_manager.query_games.return_value = sample_games[:2]  # First two games
        
        result = await query_engine.get_games_by_tournament("tournament_1")
        
        assert len(result) == 2
        mock_storage_manager.query_games.assert_called_once_with({'tournament_id': 'tournament_1'})
    
    # Advanced Query Tests
    
    @pytest.mark.asyncio
    async def test_query_games_advanced_basic_filters(self, query_engine, mock_storage_manager, sample_games):
        """Test advanced game queries with basic filters."""
        filters = GameFilters(
            player_ids=["player_black"],
            start_time_after=datetime(2024, 1, 15),
            results=[GameResult.WHITE_WINS]
        )
        mock_storage_manager.query_games.return_value = sample_games
        
        result = await query_engine.query_games_advanced(filters)
        
        # Should filter to only white wins games
        assert len(result) == 1
        assert result[0].outcome.result == GameResult.WHITE_WINS
    
    @pytest.mark.asyncio
    async def test_query_games_advanced_move_filters(self, query_engine, mock_storage_manager, sample_games):
        """Test advanced game queries with move count filters."""
        filters = GameFilters(
            min_moves=20,
            max_moves=30
        )
        mock_storage_manager.query_games.return_value = sample_games
        
        result = await query_engine.query_games_advanced(filters)
        
        # Should return only the game with 25 moves
        assert len(result) == 1
        assert result[0].total_moves == 25
    
    @pytest.mark.asyncio
    async def test_query_games_advanced_with_limit_offset(self, query_engine, mock_storage_manager, sample_games):
        """Test advanced queries with pagination."""
        filters = GameFilters()
        mock_storage_manager.query_games.return_value = sample_games
        
        result = await query_engine.query_games_advanced(filters, limit=2, offset=1)
        
        # GameFilters() has completed_only=True by default
        mock_storage_manager.query_games.assert_called_once_with({'completed_only': True}, 2, 1)
    
    @pytest.mark.asyncio
    async def test_count_games_advanced(self, query_engine, mock_storage_manager, sample_games):
        """Test counting games with advanced filters."""
        filters = GameFilters(results=[GameResult.WHITE_WINS, GameResult.BLACK_WINS])
        mock_storage_manager.query_games.return_value = sample_games
        
        count = await query_engine.count_games_advanced(filters)
        
        # Should count white wins and black wins games (2 total)
        assert count == 2
    
    # Move Query Tests
    
    @pytest.mark.asyncio
    async def test_get_moves_with_filters_basic(self, query_engine, mock_storage_manager, sample_moves):
        """Test querying moves with basic filters."""
        filters = MoveFilters(is_legal=True, player=1)
        # Mock returns all moves, but filtering should return only player 1 moves
        mock_storage_manager.get_moves_with_filters.return_value = sample_moves
        
        result = await query_engine.get_moves_with_filters("test_game_001", filters)
        
        # Should return only legal moves by player 1 (first move in sample_moves)
        assert len(result) == 1
        assert result[0].is_legal is True
        assert result[0].player == 1
    
    @pytest.mark.asyncio
    async def test_get_moves_with_filters_timing(self, query_engine, mock_storage_manager, sample_moves):
        """Test querying moves with timing filters."""
        filters = MoveFilters(
            min_thinking_time_ms=2500,
            max_api_time_ms=600
        )
        mock_storage_manager.get_moves_with_filters.return_value = sample_moves
        
        result = await query_engine.get_moves_with_filters("test_game_001", filters)
        
        # First move: 2000ms thinking (< 2500), 500ms API (< 600) - filtered out by thinking time
        # Second move: 3000ms thinking (>= 2500), 800ms API (> 600) - filtered out by API time
        # So no moves should match both criteria
        assert len(result) == 0
    
    @pytest.mark.asyncio
    async def test_get_moves_with_filters_rethink(self, query_engine, mock_storage_manager, sample_moves):
        """Test querying moves with rethink filters."""
        filters = MoveFilters(has_rethink=True)
        # The mock should return moves that will be filtered by the query engine
        # Only the second move has rethink attempts
        mock_storage_manager.get_moves_with_filters.return_value = sample_moves
        
        result = await query_engine.get_moves_with_filters("test_game_001", filters)
        
        # Should return only moves with rethink attempts (second move)
        assert len(result) == 1
        assert len(result[0].rethink_attempts) > 0
        assert result[0].move_number == 2
    
    # Search and Utility Tests
    
    @pytest.mark.asyncio
    async def test_search_games_by_player_name(self, query_engine, mock_storage_manager, sample_games):
        """Test searching games by player name."""
        mock_storage_manager.query_games.return_value = sample_games
        
        result = await query_engine.search_games("player_black")
        
        assert len(result) == 3  # All games contain this player
    
    @pytest.mark.asyncio
    async def test_search_games_by_model_name(self, query_engine, mock_storage_manager, sample_games):
        """Test searching games by model name."""
        mock_storage_manager.query_games.return_value = sample_games
        
        result = await query_engine.search_games("gpt-4")
        
        assert len(result) == 3  # All games have gpt-4 player
    
    @pytest.mark.asyncio
    async def test_search_games_by_tournament(self, query_engine, mock_storage_manager, sample_games):
        """Test searching games by tournament ID."""
        mock_storage_manager.query_games.return_value = sample_games
        
        result = await query_engine.search_games("tournament_1", ["tournament_id"])
        
        assert len(result) == 2  # Two games in tournament_1
    
    @pytest.mark.asyncio
    async def test_search_games_no_matches(self, query_engine, mock_storage_manager, sample_games):
        """Test searching games with no matches."""
        mock_storage_manager.query_games.return_value = sample_games
        
        result = await query_engine.search_games("nonexistent")
        
        assert len(result) == 0
    
    @pytest.mark.asyncio
    async def test_get_recent_games(self, query_engine, mock_storage_manager, sample_games):
        """Test getting recent games."""
        # Make one game very recent
        recent_game = sample_games[0]
        recent_game.start_time = datetime.now() - timedelta(hours=2)
        mock_storage_manager.query_games.return_value = [recent_game]
        
        result = await query_engine.get_recent_games(hours=24, limit=10)
        
        assert len(result) == 1
        # Verify the filter was applied correctly
        call_args = mock_storage_manager.query_games.call_args[0][0]
        assert 'start_time_after' in call_args
    
    @pytest.mark.asyncio
    async def test_get_recent_games_sorted(self, query_engine, mock_storage_manager):
        """Test that recent games are sorted by start time."""
        # Create games with different start times
        older_game = GameRecord(
            game_id="older",
            start_time=datetime.now() - timedelta(hours=10),
            players={0: PlayerInfo("p1", "m1", "pr1", "t1"), 1: PlayerInfo("p2", "m2", "pr2", "t2")}
        )
        newer_game = GameRecord(
            game_id="newer",
            start_time=datetime.now() - timedelta(hours=2),
            players={0: PlayerInfo("p1", "m1", "pr1", "t1"), 1: PlayerInfo("p2", "m2", "pr2", "t2")}
        )
        
        mock_storage_manager.query_games.return_value = [older_game, newer_game]
        
        result = await query_engine.get_recent_games()
        
        # Should be sorted newest first
        assert result[0].game_id == "newer"
        assert result[1].game_id == "older"
    
    # Filter Conversion Tests
    
    def test_convert_game_filters_comprehensive(self, query_engine):
        """Test comprehensive game filter conversion."""
        filters = GameFilters(
            player_ids=["p1", "p2"],
            model_names=["gpt-4"],
            model_providers=["openai"],
            agent_types=["ChessLLMAgent"],
            start_time_after=datetime(2024, 1, 1),
            start_time_before=datetime(2024, 1, 31),
            tournament_ids=["t1", "t2"],
            completed_only=True
        )
        
        result = query_engine._convert_game_filters(filters)
        
        expected = {
            'player_ids': ["p1", "p2"],
            'model_names': ["gpt-4"],
            'model_providers': ["openai"],
            'agent_types': ["ChessLLMAgent"],
            'start_time_after': datetime(2024, 1, 1),
            'start_time_before': datetime(2024, 1, 31),
            'tournament_ids': ["t1", "t2"],
            'completed_only': True
        }
        
        assert result == expected
    
    def test_convert_move_filters_comprehensive(self, query_engine):
        """Test comprehensive move filter conversion."""
        filters = MoveFilters(
            is_legal=True,
            parsing_success=False,
            has_rethink=True,
            blunder_flag=False,
            player=1,
            min_thinking_time_ms=1000,
            max_thinking_time_ms=5000
        )
        
        result = query_engine._convert_move_filters(filters)
        
        expected = {
            'is_legal': True,
            'parsing_success': False,
            'has_rethink': True,
            'blunder_flag': False,
            'player': 1,
            'min_thinking_time': 1000,
            'max_thinking_time': 5000
        }
        
        assert result == expected
    
    # Error Handling Tests
    
    @pytest.mark.asyncio
    async def test_query_games_advanced_storage_error(self, query_engine, mock_storage_manager):
        """Test handling of storage errors in advanced queries."""
        filters = GameFilters()
        mock_storage_manager.query_games.side_effect = Exception("Database error")
        
        with pytest.raises(StorageError, match="Advanced games query failed"):
            await query_engine.query_games_advanced(filters)
    
    @pytest.mark.asyncio
    async def test_get_moves_with_filters_storage_error(self, query_engine, mock_storage_manager):
        """Test handling of storage errors in move queries."""
        filters = MoveFilters()
        mock_storage_manager.get_moves_with_filters.side_effect = Exception("Database error")
        
        with pytest.raises(StorageError, match="Move query failed"):
            await query_engine.get_moves_with_filters("game_id", filters)
    
    @pytest.mark.asyncio
    async def test_search_games_storage_error(self, query_engine, mock_storage_manager):
        """Test handling of storage errors in search."""
        mock_storage_manager.query_games.side_effect = Exception("Database error")
        
        with pytest.raises(StorageError, match="Game search failed"):
            await query_engine.search_games("search_term")
    
    # Edge Cases
    
    @pytest.mark.asyncio
    async def test_empty_results(self, query_engine, mock_storage_manager):
        """Test handling of empty query results."""
        mock_storage_manager.query_games.return_value = []
        
        result = await query_engine.get_games_by_players("nonexistent_player")
        
        assert result == []
    
    def test_game_matches_filters_edge_cases(self, query_engine, sample_game):
        """Test edge cases in game filter matching."""
        # Test with None values
        filters = GameFilters(
            min_moves=None,
            max_moves=None,
            results=None
        )
        
        assert query_engine._game_matches_filters(sample_game, filters) is True
        
        # Test with game that has no outcome
        game_no_outcome = GameRecord(
            game_id="no_outcome",
            start_time=datetime.now(),
            players={0: PlayerInfo("p1", "m1", "pr1", "t1"), 1: PlayerInfo("p2", "m2", "pr2", "t2")}
        )
        
        filters_with_outcome = GameFilters(results=[GameResult.WHITE_WINS])
        assert query_engine._game_matches_filters(game_no_outcome, filters_with_outcome) is False
    
    def test_move_matches_advanced_filters_edge_cases(self, query_engine, sample_moves):
        """Test edge cases in move filter matching."""
        move = sample_moves[0]
        
        # Test with None quality score
        move.move_quality_score = None
        filters = MoveFilters(min_quality_score=0.5)
        
        assert query_engine._move_matches_advanced_filters(move, filters) is False
        
        # Test with quality score present
        move.move_quality_score = 0.8
        assert query_engine._move_matches_advanced_filters(move, filters) is True


class TestPerformanceAnalytics:
    """Test cases for performance analytics functionality."""
    
    @pytest.fixture
    def mock_storage_manager(self):
        """Create a mock storage manager."""
        return AsyncMock()
    
    @pytest.fixture
    def query_engine(self, mock_storage_manager):
        """Create a QueryEngine instance with mock storage manager."""
        return QueryEngine(mock_storage_manager)
    
    @pytest.fixture
    def sample_players(self):
        """Create sample player info."""
        return {
            0: PlayerInfo(
                player_id="player_black",
                model_name="gpt-4",
                model_provider="openai",
                agent_type="ChessLLMAgent",
                elo_rating=1500.0
            ),
            1: PlayerInfo(
                player_id="player_white",
                model_name="gemini-pro",
                model_provider="google",
                agent_type="ChessRethinkAgent",
                elo_rating=1600.0
            )
        }
    
    @pytest.fixture
    def completed_games_with_outcomes(self, sample_players):
        """Create completed games with various outcomes."""
        games = []
        
        # Game 1: White wins (player_white wins)
        games.append(GameRecord(
            game_id="game_001",
            tournament_id="tournament_1",
            start_time=datetime(2024, 1, 15, 10, 0, 0),
            end_time=datetime(2024, 1, 15, 10, 30, 0),
            players=sample_players,
            outcome=GameOutcome(GameResult.WHITE_WINS, 1, TerminationReason.CHECKMATE),
            total_moves=25,
            game_duration_seconds=1800.0
        ))
        
        # Game 2: Black wins (player_black wins)
        games.append(GameRecord(
            game_id="game_002",
            tournament_id="tournament_1",
            start_time=datetime(2024, 1, 16, 14, 0, 0),
            end_time=datetime(2024, 1, 16, 14, 45, 0),
            players=sample_players,
            outcome=GameOutcome(GameResult.BLACK_WINS, 0, TerminationReason.RESIGNATION),
            total_moves=40,
            game_duration_seconds=2700.0
        ))
        
        # Game 3: Draw
        games.append(GameRecord(
            game_id="game_003",
            tournament_id="tournament_2",
            start_time=datetime(2024, 1, 17, 9, 0, 0),
            end_time=datetime(2024, 1, 17, 9, 20, 0),
            players=sample_players,
            outcome=GameOutcome(GameResult.DRAW, None, TerminationReason.STALEMATE),
            total_moves=15,
            game_duration_seconds=1200.0
        ))
        
        # Game 4: Another white win
        games.append(GameRecord(
            game_id="game_004",
            tournament_id="tournament_1",
            start_time=datetime(2024, 1, 18, 15, 0, 0),
            end_time=datetime(2024, 1, 18, 15, 35, 0),
            players=sample_players,
            outcome=GameOutcome(GameResult.WHITE_WINS, 1, TerminationReason.CHECKMATE),
            total_moves=30,
            game_duration_seconds=2100.0
        ))
        
        return games
    
    @pytest.fixture
    def sample_moves_with_stats(self):
        """Create sample moves with various statistics."""
        moves = []
        
        # Legal move by player 1 (white)
        moves.append(MoveRecord(
            game_id="game_001",
            move_number=1,
            player=1,
            timestamp=datetime(2024, 1, 15, 10, 1, 0),
            fen_before="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
            fen_after="rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1",
            legal_moves=["e4", "d4", "Nf3"],
            move_san="e4",
            move_uci="e2e4",
            is_legal=True,
            prompt_text="Make your first move",
            raw_response="I'll play e4",
            parsing_success=True,
            thinking_time_ms=2000,
            api_call_time_ms=500,
            parsing_time_ms=100,
            move_quality_score=0.8,
            blunder_flag=False
        ))
        
        # Illegal move by player 0 (black) with rethink
        moves.append(MoveRecord(
            game_id="game_001",
            move_number=2,
            player=0,
            timestamp=datetime(2024, 1, 15, 10, 2, 0),
            fen_before="rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1",
            fen_after="rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq e6 0 2",
            legal_moves=["e5", "e6", "Nf6"],
            move_san="e5",
            move_uci="e7e5",
            is_legal=False,  # Initially illegal
            prompt_text="Respond to e4",
            raw_response="I'll play e5",
            parsing_success=False,  # Failed initially
            thinking_time_ms=3000,
            api_call_time_ms=800,
            parsing_time_ms=150,
            move_quality_score=0.6,
            blunder_flag=False,
            rethink_attempts=[
                RethinkAttempt(
                    attempt_number=1,
                    prompt_text="That move is illegal, try again",
                    raw_response="Let me play e5 instead",
                    parsed_move="e5",
                    was_legal=True,
                    timestamp=datetime(2024, 1, 15, 10, 1, 30)
                )
            ]
        ))
        
        # Blunder move by player 1
        moves.append(MoveRecord(
            game_id="game_001",
            move_number=3,
            player=1,
            timestamp=datetime(2024, 1, 15, 10, 3, 0),
            fen_before="rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq e6 0 2",
            fen_after="rnbqkbnr/pppp1ppp/8/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R b KQkq - 1 2",
            legal_moves=["Nf3", "Nc3", "d3"],
            move_san="Nf3",
            move_uci="g1f3",
            is_legal=True,
            prompt_text="Continue the game",
            raw_response="I'll play Nf3",
            parsing_success=True,
            thinking_time_ms=1500,
            api_call_time_ms=400,
            parsing_time_ms=80,
            move_quality_score=0.2,  # Low quality
            blunder_flag=True  # This is a blunder
        ))
        
        return moves
    
    # Win Rate Tests
    
    @pytest.mark.asyncio
    async def test_get_player_winrate_overall(self, query_engine, mock_storage_manager, completed_games_with_outcomes):
        """Test calculating overall win rate for a player."""
        # Mock the get_games_by_players method
        query_engine.get_games_by_players = AsyncMock(return_value=completed_games_with_outcomes)
        
        # Test win rate for player_white (should win 2 out of 4 games = 50%)
        win_rate = await query_engine.get_player_winrate("player_white")
        
        assert win_rate == 50.0
        query_engine.get_games_by_players.assert_called_once_with("player_white")
    
    @pytest.mark.asyncio
    async def test_get_player_winrate_head_to_head(self, query_engine, mock_storage_manager, completed_games_with_outcomes):
        """Test calculating head-to-head win rate."""
        # Mock the get_games_by_players method for head-to-head
        query_engine.get_games_by_players = AsyncMock(return_value=completed_games_with_outcomes)
        
        win_rate = await query_engine.get_player_winrate("player_white", "player_black")
        
        assert win_rate == 50.0  # 2 wins out of 4 games
        query_engine.get_games_by_players.assert_called_once_with("player_white", "player_black")
    
    @pytest.mark.asyncio
    async def test_get_player_winrate_no_games(self, query_engine, mock_storage_manager):
        """Test win rate calculation with no games."""
        query_engine.get_games_by_players = AsyncMock(return_value=[])
        
        win_rate = await query_engine.get_player_winrate("nonexistent_player")
        
        assert win_rate == 0.0
    
    @pytest.mark.asyncio
    async def test_get_player_winrate_no_completed_games(self, query_engine, mock_storage_manager, sample_players):
        """Test win rate calculation with no completed games."""
        # Create an ongoing game (no outcome)
        ongoing_game = GameRecord(
            game_id="ongoing",
            start_time=datetime.now(),
            players=sample_players
        )
        
        query_engine.get_games_by_players = AsyncMock(return_value=[ongoing_game])
        
        win_rate = await query_engine.get_player_winrate("player_white")
        
        assert win_rate == 0.0
    
    @pytest.mark.asyncio
    async def test_get_player_winrate_storage_error(self, query_engine, mock_storage_manager):
        """Test handling of storage errors in win rate calculation."""
        query_engine.get_games_by_players = AsyncMock(side_effect=Exception("Database error"))
        
        with pytest.raises(StorageError, match="Win rate calculation failed"):
            await query_engine.get_player_winrate("player_white")
    
    # Move Accuracy Tests
    
    @pytest.mark.asyncio
    async def test_get_move_accuracy_stats(self, query_engine, mock_storage_manager, completed_games_with_outcomes, sample_moves_with_stats):
        """Test calculating move accuracy statistics."""
        query_engine.get_games_by_players = AsyncMock(return_value=completed_games_with_outcomes)
        mock_storage_manager.get_moves.return_value = sample_moves_with_stats
        
        stats = await query_engine.get_move_accuracy_stats("player_white")
        
        # player_white is player 1, so should get moves 1 and 3 from sample_moves_with_stats
        # But the mock returns the same moves for all 4 games, so we get 4*2 = 8 moves for player 1
        assert stats.total_moves == 8  # 2 moves per game * 4 games
        assert stats.legal_moves == 8  # Moves 1 and 3 are both legal
        assert stats.illegal_moves == 0  # No illegal moves for player 1
        assert stats.parsing_failures == 0  # Both moves parsed successfully
        assert stats.total_rethink_attempts == 0  # No rethink attempts for player 1
        assert stats.blunders == 4  # Move 3 is a blunder, 1 per game * 4 games
        
        # Check calculated properties
        assert stats.accuracy_percentage == 100.0  # All moves are legal
        assert stats.blunder_rate == 50.0  # 4 blunders out of 8 moves
    
    @pytest.mark.asyncio
    async def test_get_move_accuracy_stats_with_rethink(self, query_engine, mock_storage_manager, completed_games_with_outcomes, sample_moves_with_stats):
        """Test move accuracy stats for player with rethink attempts."""
        query_engine.get_games_by_players = AsyncMock(return_value=completed_games_with_outcomes)
        mock_storage_manager.get_moves.return_value = sample_moves_with_stats
        
        stats = await query_engine.get_move_accuracy_stats("player_black")
        
        # player_black is player 0, so should get move 2 from sample_moves_with_stats
        # But the mock returns the same moves for all 4 games, so we get 4*1 = 4 moves for player 0
        assert stats.total_moves == 4  # 1 move per game * 4 games
        assert stats.legal_moves == 0  # Move 2 is marked as illegal
        assert stats.illegal_moves == 4  # All 4 instances are illegal
        assert stats.parsing_failures == 4  # Move 2 failed parsing initially
        assert stats.total_rethink_attempts == 4  # One rethink attempt per move * 4 games
        assert stats.blunders == 0
        
        # Check calculated properties
        assert stats.accuracy_percentage == 0.0  # 0 legal out of 4 total
        assert stats.average_rethink_attempts == 1.0  # 4 rethink attempts / 4 moves
    
    @pytest.mark.asyncio
    async def test_get_move_accuracy_stats_no_moves(self, query_engine, mock_storage_manager):
        """Test move accuracy stats with no moves."""
        query_engine.get_games_by_players = AsyncMock(return_value=[])
        
        stats = await query_engine.get_move_accuracy_stats("nonexistent_player")
        
        assert stats.total_moves == 0
        assert stats.accuracy_percentage == 0.0
        assert stats.parsing_success_rate == 0.0
    
    @pytest.mark.asyncio
    async def test_get_move_accuracy_stats_storage_error(self, query_engine, mock_storage_manager):
        """Test handling of storage errors in move accuracy calculation."""
        query_engine.get_games_by_players = AsyncMock(side_effect=Exception("Database error"))
        
        with pytest.raises(StorageError, match="Move accuracy calculation failed"):
            await query_engine.get_move_accuracy_stats("player_white")
    
    # Illegal Move Rate Tests
    
    @pytest.mark.asyncio
    async def test_get_illegal_move_rate(self, query_engine, mock_storage_manager, completed_games_with_outcomes, sample_moves_with_stats):
        """Test calculating illegal move rate."""
        query_engine.get_games_by_players = AsyncMock(return_value=completed_games_with_outcomes)
        mock_storage_manager.get_moves.return_value = sample_moves_with_stats
        
        # Mock get_move_accuracy_stats to return known stats
        from game_arena.storage.models import MoveAccuracyStats
        mock_stats = MoveAccuracyStats(
            total_moves=10,
            legal_moves=8,
            illegal_moves=2,
            parsing_failures=1,
            total_rethink_attempts=3,
            blunders=1
        )
        query_engine.get_move_accuracy_stats = AsyncMock(return_value=mock_stats)
        
        illegal_rate = await query_engine.get_illegal_move_rate("player_white")
        
        assert illegal_rate == 20.0  # 2 illegal out of 10 total = 20%
    
    @pytest.mark.asyncio
    async def test_get_illegal_move_rate_no_moves(self, query_engine, mock_storage_manager):
        """Test illegal move rate with no moves."""
        from game_arena.storage.models import MoveAccuracyStats
        mock_stats = MoveAccuracyStats()  # All zeros
        query_engine.get_move_accuracy_stats = AsyncMock(return_value=mock_stats)
        
        illegal_rate = await query_engine.get_illegal_move_rate("player_white")
        
        assert illegal_rate == 0.0
    
    @pytest.mark.asyncio
    async def test_get_illegal_move_rate_storage_error(self, query_engine, mock_storage_manager):
        """Test handling of storage errors in illegal move rate calculation."""
        query_engine.get_move_accuracy_stats = AsyncMock(side_effect=Exception("Database error"))
        
        with pytest.raises(StorageError, match="Illegal move rate calculation failed"):
            await query_engine.get_illegal_move_rate("player_white")
    
    # Player Comparison Tests
    
    @pytest.mark.asyncio
    async def test_get_player_comparison(self, query_engine, mock_storage_manager, completed_games_with_outcomes, sample_moves_with_stats):
        """Test comparing two players."""
        # Mock all the required methods
        query_engine.get_games_by_players = AsyncMock()
        query_engine.get_games_by_players.side_effect = [
            completed_games_with_outcomes,  # For player1 games
            completed_games_with_outcomes,  # For player2 games
            completed_games_with_outcomes   # For head-to-head games
        ]
        
        from game_arena.storage.models import MoveAccuracyStats
        player1_stats = MoveAccuracyStats(
            total_moves=20,
            legal_moves=18,
            illegal_moves=2,
            parsing_failures=1,
            total_rethink_attempts=2,
            blunders=3
        )
        player2_stats = MoveAccuracyStats(
            total_moves=15,
            legal_moves=13,
            illegal_moves=2,
            parsing_failures=2,
            total_rethink_attempts=4,
            blunders=1
        )
        
        query_engine.get_move_accuracy_stats = AsyncMock()
        query_engine.get_move_accuracy_stats.side_effect = [player1_stats, player2_stats]
        
        query_engine.get_player_winrate = AsyncMock()
        query_engine.get_player_winrate.side_effect = [60.0, 40.0]  # player1: 60%, player2: 40%
        
        query_engine._get_average_thinking_time = AsyncMock()
        query_engine._get_average_thinking_time.side_effect = [2000.0, 2500.0]  # ms
        
        comparison = await query_engine.get_player_comparison("player1", "player2")
        
        # Verify structure and some key values
        assert "player1" in comparison
        assert "player2" in comparison
        assert "head_to_head" in comparison
        
        assert comparison["player1"]["player_id"] == "player1"
        assert comparison["player1"]["win_rate"] == 60.0
        assert comparison["player1"]["accuracy"] == 90.0  # 18/20 * 100
        
        assert comparison["player2"]["player_id"] == "player2"
        assert comparison["player2"]["win_rate"] == 40.0
        assert abs(comparison["player2"]["accuracy"] - 86.67) < 0.01  # 13/15 * 100 (rounded)
        
        assert comparison["head_to_head"]["total_games"] == 4
        # The head-to-head calculation looks for actual player IDs, but we're using "player1" and "player2"
        # while the games have "player_white" and "player_black". So no matches are found.
        assert comparison["head_to_head"]["player1_wins"] == 0  # No matches found
        assert comparison["head_to_head"]["player2_wins"] == 0  # No matches found
        assert comparison["head_to_head"]["draws"] == 1  # One draw game is still counted
    
    @pytest.mark.asyncio
    async def test_get_player_comparison_storage_error(self, query_engine, mock_storage_manager):
        """Test handling of storage errors in player comparison."""
        query_engine.get_move_accuracy_stats = AsyncMock(side_effect=Exception("Database error"))
        
        with pytest.raises(StorageError, match="Player comparison failed"):
            await query_engine.get_player_comparison("player1", "player2")
    
    # Leaderboard Tests
    
    @pytest.mark.asyncio
    async def test_generate_leaderboard_by_win_rate(self, query_engine, mock_storage_manager, completed_games_with_outcomes):
        """Test generating leaderboard sorted by win rate."""
        # Mock query_games to return games with different players
        mock_storage_manager.query_games.return_value = completed_games_with_outcomes
        
        # Mock individual player methods
        query_engine.get_games_by_players = AsyncMock()
        query_engine.get_games_by_players.side_effect = [
            [completed_games_with_outcomes[0], completed_games_with_outcomes[3]],  # player_white: 2 games, 2 wins
            [completed_games_with_outcomes[1]]  # player_black: 1 game, 1 win
        ]
        
        query_engine.get_player_winrate = AsyncMock()
        query_engine.get_player_winrate.side_effect = [100.0, 100.0]  # Both have 100% win rate
        
        from game_arena.storage.models import MoveAccuracyStats
        mock_stats = MoveAccuracyStats(total_moves=10, legal_moves=9, illegal_moves=1)
        query_engine.get_move_accuracy_stats = AsyncMock(return_value=mock_stats)
        query_engine._get_average_thinking_time = AsyncMock(return_value=2000.0)
        
        leaderboard = await query_engine.generate_leaderboard("win_rate", limit=5)
        
        assert len(leaderboard) == 2  # Two unique players
        assert all("rank" in entry for entry in leaderboard)
        assert all("win_rate" in entry for entry in leaderboard)
        assert leaderboard[0]["rank"] == 1
        assert leaderboard[1]["rank"] == 2
    
    @pytest.mark.asyncio
    async def test_generate_leaderboard_invalid_criteria(self, query_engine, mock_storage_manager):
        """Test leaderboard generation with invalid criteria."""
        with pytest.raises(ValidationError, match="Invalid criteria"):
            await query_engine.generate_leaderboard("invalid_criteria")
    
    @pytest.mark.asyncio
    async def test_generate_leaderboard_storage_error(self, query_engine, mock_storage_manager):
        """Test handling of storage errors in leaderboard generation."""
        mock_storage_manager.query_games.side_effect = Exception("Database error")
        
        with pytest.raises(StorageError, match="Leaderboard generation failed"):
            await query_engine.generate_leaderboard("win_rate")
    
    # Tournament Summary Tests
    
    @pytest.mark.asyncio
    async def test_get_tournament_summary(self, query_engine, mock_storage_manager, completed_games_with_outcomes):
        """Test generating tournament summary."""
        # Filter games to only tournament_1 games
        tournament_games = [g for g in completed_games_with_outcomes if g.tournament_id == "tournament_1"]
        query_engine.get_games_by_tournament = AsyncMock(return_value=tournament_games)
        
        summary = await query_engine.get_tournament_summary("tournament_1")
        
        assert summary["tournament_id"] == "tournament_1"
        assert summary["total_games"] == 3  # 3 games in tournament_1
        assert summary["completed_games"] == 3
        assert summary["ongoing_games"] == 0
        assert summary["completion_rate"] == 100.0
        
        # Check outcomes
        assert summary["outcomes"]["white_wins"] == 2
        assert summary["outcomes"]["black_wins"] == 1
        assert summary["outcomes"]["draws"] == 0
        
        # Check participants
        assert summary["participants"] == 2  # Two unique players
        assert "player_performance" in summary
    
    @pytest.mark.asyncio
    async def test_get_tournament_summary_no_games(self, query_engine, mock_storage_manager):
        """Test tournament summary with no games."""
        query_engine.get_games_by_tournament = AsyncMock(return_value=[])
        
        summary = await query_engine.get_tournament_summary("empty_tournament")
        
        assert summary["tournament_id"] == "empty_tournament"
        assert summary["total_games"] == 0
        assert summary["completed_games"] == 0
        assert "error" in summary
    
    @pytest.mark.asyncio
    async def test_get_tournament_summary_storage_error(self, query_engine, mock_storage_manager):
        """Test handling of storage errors in tournament summary."""
        query_engine.get_games_by_tournament = AsyncMock(side_effect=Exception("Database error"))
        
        with pytest.raises(StorageError, match="Tournament summary generation failed"):
            await query_engine.get_tournament_summary("tournament_1")
    
    # Helper Method Tests
    
    @pytest.mark.asyncio
    async def test_get_average_thinking_time(self, query_engine, mock_storage_manager, completed_games_with_outcomes, sample_moves_with_stats):
        """Test calculating average thinking time."""
        query_engine.get_games_by_players = AsyncMock(return_value=completed_games_with_outcomes)
        mock_storage_manager.get_moves.return_value = sample_moves_with_stats
        
        avg_time = await query_engine._get_average_thinking_time("player_white")
        
        # player_white is player 1, gets moves 1 and 3: (2000 + 1500) / 2 = 1750
        assert avg_time == 1750.0
    
    @pytest.mark.asyncio
    async def test_get_average_thinking_time_no_moves(self, query_engine, mock_storage_manager):
        """Test average thinking time with no moves."""
        query_engine.get_games_by_players = AsyncMock(return_value=[])
        
        avg_time = await query_engine._get_average_thinking_time("nonexistent_player")
        
        assert avg_time == 0.0
    
    @pytest.mark.asyncio
    async def test_get_average_thinking_time_with_errors(self, query_engine, mock_storage_manager, completed_games_with_outcomes, sample_moves_with_stats):
        """Test average thinking time calculation with some game errors."""
        query_engine.get_games_by_players = AsyncMock(return_value=completed_games_with_outcomes)
        mock_storage_manager.get_moves.side_effect = [
            Exception("Error getting moves"),  # First game fails
            [],  # Second game has no moves
            [sample_moves_with_stats[0]]  # Third game has one move
        ]
        
        avg_time = await query_engine._get_average_thinking_time("player_white")
        
        # Should only count the successful move from the third game
        assert avg_time == 2000.0  # Only move 1's thinking time