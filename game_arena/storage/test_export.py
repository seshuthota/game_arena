"""
Unit tests for the Game Arena storage export functionality.

Tests PGN, JSON, and CSV export formats with various scenarios
including single game export, batch export, and filtered export.
"""

import json
import pytest
from datetime import datetime, timedelta
from io import StringIO
from unittest.mock import AsyncMock, MagicMock, patch

from .export import GameExporter
from .models import (
    GameRecord, MoveRecord, PlayerInfo, GameOutcome, RethinkAttempt,
    GameResult, TerminationReason, PlayerStats
)
from .query_engine import GameFilters
from .exceptions import StorageError, ValidationError


class TestGameExporter:
    """Test cases for GameExporter class."""
    
    @pytest.fixture
    def mock_storage_manager(self):
        """Create a mock storage manager."""
        return AsyncMock()
    
    @pytest.fixture
    def mock_query_engine(self):
        """Create a mock query engine."""
        return AsyncMock()
    
    @pytest.fixture
    def exporter(self, mock_storage_manager, mock_query_engine):
        """Create a GameExporter instance with mocked dependencies."""
        return GameExporter(mock_storage_manager, mock_query_engine)
    
    @pytest.fixture
    def sample_game(self):
        """Create a sample game record for testing."""
        return GameRecord(
            game_id="test_game_001",
            tournament_id="test_tournament",
            start_time=datetime(2024, 1, 15, 10, 30, 0),
            end_time=datetime(2024, 1, 15, 11, 15, 0),
            players={
                0: PlayerInfo(
                    player_id="black_player",
                    model_name="gpt-4",
                    model_provider="openai",
                    agent_type="ChessLLMAgent",
                    elo_rating=1500.0
                ),
                1: PlayerInfo(
                    player_id="white_player",
                    model_name="gemini-pro",
                    model_provider="google",
                    agent_type="ChessRethinkAgent",
                    elo_rating=1600.0
                )
            },
            initial_fen="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
            final_fen="rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1",
            outcome=GameOutcome(
                result=GameResult.WHITE_WINS,
                winner=1,
                termination=TerminationReason.CHECKMATE
            ),
            total_moves=2,
            game_duration_seconds=2700.0
        )
    
    @pytest.fixture
    def sample_moves(self):
        """Create sample move records for testing."""
        return [
            MoveRecord(
                game_id="test_game_001",
                move_number=1,
                player=1,  # White
                timestamp=datetime(2024, 1, 15, 10, 31, 0),
                fen_before="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
                fen_after="rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1",
                legal_moves=["e4", "d4", "Nf3", "c4"],
                move_san="e4",
                move_uci="e2e4",
                is_legal=True,
                prompt_text="Make your first move as white.",
                raw_response="I'll play e4, the king's pawn opening.",
                parsed_move="e4",
                parsing_success=True,
                thinking_time_ms=2000,
                api_call_time_ms=500,
                parsing_time_ms=100
            ),
            MoveRecord(
                game_id="test_game_001",
                move_number=1,
                player=0,  # Black
                timestamp=datetime(2024, 1, 15, 10, 32, 0),
                fen_before="rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1",
                fen_after="rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq e6 0 2",
                legal_moves=["e5", "e6", "d6", "d5"],
                move_san="e5",
                move_uci="e7e5",
                is_legal=True,
                prompt_text="Respond to white's e4.",
                raw_response="I'll play e5 to control the center.",
                parsed_move="e5",
                parsing_success=True,
                thinking_time_ms=1800,
                api_call_time_ms=450,
                parsing_time_ms=80,
                rethink_attempts=[
                    RethinkAttempt(
                        attempt_number=1,
                        prompt_text="Reconsider your move.",
                        raw_response="Actually, e5 is still the best move.",
                        parsed_move="e5",
                        was_legal=True,
                        timestamp=datetime(2024, 1, 15, 10, 31, 45)
                    )
                ]
            )
        ]
    
    # PGN Export Tests
    
    @pytest.mark.asyncio
    async def test_export_game_pgn_success(self, exporter, mock_storage_manager, sample_game, sample_moves):
        """Test successful PGN export of a single game."""
        # Setup mocks
        mock_storage_manager.get_game.return_value = sample_game
        mock_storage_manager.get_moves.return_value = sample_moves
        
        # Execute
        result = await exporter.export_game_pgn("test_game_001")
        
        # Verify
        assert isinstance(result, str)
        assert '[Event "test_tournament"]' in result
        assert '[White "gemini-pro (white_player)"]' in result
        assert '[Black "gpt-4 (black_player)"]' in result
        assert '[Result "1-0"]' in result
        assert '[GameId "test_game_001"]' in result
        assert '1. e4 e5' in result
        assert '1-0' in result
        
        mock_storage_manager.get_game.assert_called_once_with("test_game_001")
        mock_storage_manager.get_moves.assert_called_once_with("test_game_001")
    
    @pytest.mark.asyncio
    async def test_export_game_pgn_no_tournament(self, exporter, mock_storage_manager, sample_game, sample_moves):
        """Test PGN export with no tournament ID."""
        # Modify sample game
        sample_game.tournament_id = None
        
        # Setup mocks
        mock_storage_manager.get_game.return_value = sample_game
        mock_storage_manager.get_moves.return_value = sample_moves
        
        # Execute
        result = await exporter.export_game_pgn("test_game_001")
        
        # Verify
        assert '[Event "Game Arena Match"]' in result
    
    @pytest.mark.asyncio
    async def test_export_game_pgn_ongoing_game(self, exporter, mock_storage_manager, sample_game, sample_moves):
        """Test PGN export of an ongoing game."""
        # Modify sample game to be ongoing
        sample_game.outcome = None
        sample_game.end_time = None
        
        # Setup mocks
        mock_storage_manager.get_game.return_value = sample_game
        mock_storage_manager.get_moves.return_value = sample_moves
        
        # Execute
        result = await exporter.export_game_pgn("test_game_001")
        
        # Verify
        assert '[Result "*"]' in result
        assert ' *' in result
    
    @pytest.mark.asyncio
    async def test_export_game_pgn_with_illegal_moves(self, exporter, mock_storage_manager, sample_game, sample_moves):
        """Test PGN export filters out illegal moves."""
        # Add an illegal move
        illegal_move = MoveRecord(
            game_id="test_game_001",
            move_number=2,
            player=1,
            timestamp=datetime(2024, 1, 15, 10, 33, 0),
            fen_before="rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq e6 0 2",
            fen_after="rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq e6 0 2",
            legal_moves=["Nf3", "Bc4", "d3"],
            move_san="Ke2",  # Illegal move
            move_uci="e1e2",
            is_legal=False,
            prompt_text="Make your second move.",
            raw_response="I'll play Ke2.",
            parsed_move="Ke2",
            parsing_success=True,
            thinking_time_ms=1500
        )
        sample_moves.append(illegal_move)
        
        # Setup mocks
        mock_storage_manager.get_game.return_value = sample_game
        mock_storage_manager.get_moves.return_value = sample_moves
        
        # Execute
        result = await exporter.export_game_pgn("test_game_001")
        
        # Verify - illegal move should not appear in PGN
        assert 'Ke2' not in result
        assert '1. e4 e5' in result
    
    @pytest.mark.asyncio
    async def test_export_games_pgn_batch(self, exporter, mock_storage_manager, sample_game, sample_moves):
        """Test batch PGN export of multiple games."""
        # Setup mocks
        mock_storage_manager.get_game.return_value = sample_game
        mock_storage_manager.get_moves.return_value = sample_moves
        
        game_ids = ["game_001", "game_002", "game_003"]
        
        # Execute
        result = await exporter.export_games_pgn_batch(game_ids)
        
        # Verify
        assert isinstance(result, dict)
        assert len(result) == 3
        for game_id in game_ids:
            assert game_id in result
            assert isinstance(result[game_id], str)
            assert '[Event "test_tournament"]' in result[game_id]
        
        assert mock_storage_manager.get_game.call_count == 3
        assert mock_storage_manager.get_moves.call_count == 3
    
    @pytest.mark.asyncio
    async def test_export_game_pgn_storage_error(self, exporter, mock_storage_manager):
        """Test PGN export handles storage errors."""
        # Setup mock to raise error
        mock_storage_manager.get_game.side_effect = Exception("Database error")
        
        # Execute and verify
        with pytest.raises(StorageError, match="PGN export failed"):
            await exporter.export_game_pgn("test_game_001")
    
    # JSON Export Tests
    
    @pytest.mark.asyncio
    async def test_export_game_json_with_moves(self, exporter, mock_storage_manager, sample_game, sample_moves):
        """Test JSON export with moves included."""
        # Setup mocks
        mock_storage_manager.get_game.return_value = sample_game
        mock_storage_manager.get_moves.return_value = sample_moves
        
        # Execute
        result = await exporter.export_game_json("test_game_001", include_moves=True)
        
        # Verify
        data = json.loads(result)
        assert data['game_id'] == "test_game_001"
        assert data['tournament_id'] == "test_tournament"
        assert 'players' in data
        assert '0' in data['players']  # Black player
        assert '1' in data['players']  # White player
        assert data['players']['1']['model_name'] == "gemini-pro"
        assert data['outcome']['result'] == "1-0"
        assert 'moves' in data
        assert len(data['moves']) == 2
        assert data['moves'][0]['move_san'] == "e4"
        assert data['moves'][1]['move_san'] == "e5"
        assert len(data['moves'][1]['rethink_attempts']) == 1
    
    @pytest.mark.asyncio
    async def test_export_game_json_without_moves(self, exporter, mock_storage_manager, sample_game):
        """Test JSON export without moves."""
        # Setup mocks
        mock_storage_manager.get_game.return_value = sample_game
        
        # Execute
        result = await exporter.export_game_json("test_game_001", include_moves=False)
        
        # Verify
        data = json.loads(result)
        assert data['game_id'] == "test_game_001"
        assert 'moves' not in data
        
        mock_storage_manager.get_moves.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_export_game_json_without_metadata(self, exporter, mock_storage_manager, sample_game, sample_moves):
        """Test JSON export without metadata."""
        # Setup mocks
        mock_storage_manager.get_game.return_value = sample_game
        mock_storage_manager.get_moves.return_value = sample_moves
        
        # Execute
        result = await exporter.export_game_json("test_game_001", include_metadata=False)
        
        # Verify
        data = json.loads(result)
        move = data['moves'][0]
        assert 'legal_moves' not in move
        assert 'prompt_text' not in move
        assert 'raw_response' not in move
        assert 'move_san' in move  # Basic fields should still be present
    
    @pytest.mark.asyncio
    async def test_export_games_json_batch(self, exporter, mock_storage_manager, sample_game, sample_moves):
        """Test batch JSON export."""
        # Setup mocks
        mock_storage_manager.get_game.return_value = sample_game
        mock_storage_manager.get_moves.return_value = sample_moves
        
        game_ids = ["game_001", "game_002"]
        
        # Execute
        result = await exporter.export_games_json_batch(game_ids)
        
        # Verify
        data = json.loads(result)
        assert isinstance(data, list)
        assert len(data) == 2
        for game_data in data:
            assert game_data['game_id'] == "test_game_001"
            assert 'moves' in game_data
    
    # CSV Export Tests
    
    @pytest.mark.asyncio
    async def test_export_games_csv(self, exporter, mock_storage_manager, sample_game):
        """Test CSV export of games."""
        # Setup mocks
        mock_storage_manager.get_game.return_value = sample_game
        
        game_ids = ["game_001", "game_002"]
        
        # Execute
        result = await exporter.export_games_csv(game_ids)
        
        # Verify
        lines = result.strip().split('\n')
        assert len(lines) == 3  # Header + 2 games
        
        # Check header
        header = lines[0]
        assert 'game_id' in header
        assert 'white_player_id' in header
        assert 'black_player_id' in header
        assert 'result' in header
        
        # Check data rows
        for i in range(1, 3):
            row = lines[i].split(',')
            assert row[0] == 'test_game_001'  # game_id
            assert row[4] == 'white_player'   # white_player_id
            assert row[9] == 'black_player'   # black_player_id
    
    @pytest.mark.asyncio
    async def test_export_games_csv_with_file(self, exporter, mock_storage_manager, sample_game):
        """Test CSV export writing to file."""
        # Setup mocks
        mock_storage_manager.get_game.return_value = sample_game
        
        output_file = StringIO()
        game_ids = ["game_001"]
        
        # Execute
        result = await exporter.export_games_csv(game_ids, output_file)
        
        # Verify
        assert "Exported 1 games" in result
        csv_content = output_file.getvalue()
        assert 'game_id' in csv_content
        assert 'test_game_001' in csv_content
    
    @pytest.mark.asyncio
    async def test_export_moves_csv(self, exporter, mock_storage_manager, sample_moves):
        """Test CSV export of moves."""
        # Setup mocks
        mock_storage_manager.get_moves.return_value = sample_moves
        
        game_ids = ["game_001"]
        
        # Execute
        result = await exporter.export_moves_csv(game_ids)
        
        # Verify
        lines = result.strip().split('\n')
        assert len(lines) == 3  # Header + 2 moves
        
        # Check header
        header = lines[0]
        assert 'game_id' in header
        assert 'move_san' in header
        assert 'thinking_time_ms' in header
        
        # Check data rows
        row1 = lines[1].split(',')
        assert row1[0] == 'test_game_001'  # game_id
        assert row1[4] == 'e4'        # move_san
        
        row2 = lines[2].split(',')
        assert row2[4] == 'e5'        # move_san
        assert row2[15] == '1'        # rethink_attempts_count
    
    # Filtered Export Tests
    
    @pytest.mark.asyncio
    async def test_export_filtered_games_json(self, exporter, mock_query_engine, mock_storage_manager, sample_game, sample_moves):
        """Test filtered export in JSON format."""
        # Setup mocks
        mock_query_engine.query_games_advanced.return_value = [sample_game]
        mock_storage_manager.get_game.return_value = sample_game
        mock_storage_manager.get_moves.return_value = sample_moves
        
        filters = GameFilters(completed_only=True)
        
        # Execute
        result = await exporter.export_filtered_games(filters, format_type='json')
        
        # Verify
        data = json.loads(result)
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]['game_id'] == "test_game_001"
        
        mock_query_engine.query_games_advanced.assert_called_once_with(filters)
    
    @pytest.mark.asyncio
    async def test_export_filtered_games_csv(self, exporter, mock_query_engine, mock_storage_manager, sample_game):
        """Test filtered export in CSV format."""
        # Setup mocks
        mock_query_engine.query_games_advanced.return_value = [sample_game]
        mock_storage_manager.get_game.return_value = sample_game
        
        filters = GameFilters(completed_only=True)
        
        # Execute
        result = await exporter.export_filtered_games(filters, format_type='csv')
        
        # Verify
        lines = result.strip().split('\n')
        assert len(lines) == 2  # Header + 1 game
        assert 'test_game_001' in result
    
    @pytest.mark.asyncio
    async def test_export_filtered_games_pgn(self, exporter, mock_query_engine, mock_storage_manager, sample_game, sample_moves):
        """Test filtered export in PGN format."""
        # Setup mocks
        mock_query_engine.query_games_advanced.return_value = [sample_game]
        mock_storage_manager.get_game.return_value = sample_game
        mock_storage_manager.get_moves.return_value = sample_moves
        
        filters = GameFilters(completed_only=True)
        
        # Execute
        result = await exporter.export_filtered_games(filters, format_type='pgn')
        
        # Verify
        assert '[Event "test_tournament"]' in result
        assert '1. e4 e5' in result
        assert '1-0' in result
    
    @pytest.mark.asyncio
    async def test_export_filtered_games_invalid_format(self, exporter, mock_query_engine):
        """Test filtered export with invalid format."""
        filters = GameFilters()
        
        # Execute and verify
        with pytest.raises(ValidationError, match="Invalid format type"):
            await exporter.export_filtered_games(filters, format_type='xml')
    
    @pytest.mark.asyncio
    async def test_export_filtered_games_no_results(self, exporter, mock_query_engine):
        """Test filtered export with no matching games."""
        # Setup mocks
        mock_query_engine.query_games_advanced.return_value = []
        
        filters = GameFilters(completed_only=True)
        
        # Execute
        result = await exporter.export_filtered_games(filters, format_type='json')
        
        # Verify
        assert result == ""
    
    # Player Stats Export Tests
    
    @pytest.mark.asyncio
    async def test_export_player_stats_csv(self, exporter, mock_storage_manager):
        """Test CSV export of player statistics."""
        # Create sample player stats
        stats = PlayerStats(
            player_id="test_player",
            games_played=10,
            wins=6,
            losses=3,
            draws=1,
            illegal_move_rate=0.05,
            average_thinking_time=2500.0,
            elo_rating=1550.0,
            last_updated=datetime(2024, 1, 15, 12, 0, 0)
        )
        
        # Setup mocks
        mock_storage_manager.get_player_stats.return_value = stats
        
        player_ids = ["test_player"]
        
        # Execute
        result = await exporter.export_player_stats_csv(player_ids)
        
        # Verify
        lines = result.strip().split('\n')
        assert len(lines) == 2  # Header + 1 player
        
        # Check header
        header = lines[0]
        assert 'player_id' in header
        assert 'win_rate' in header
        assert 'elo_rating' in header
        
        # Check data row
        row = lines[1].split(',')
        assert row[0] == 'test_player'
        assert row[1] == '10'  # games_played
        assert row[2] == '6'   # wins
    
    @pytest.mark.asyncio
    async def test_export_player_stats_csv_no_player_ids(self, exporter):
        """Test player stats export without specific player IDs."""
        # Execute and verify
        with pytest.raises(ValidationError, match="Please provide specific player_ids"):
            await exporter.export_player_stats_csv()
    
    # Utility Tests
    
    @pytest.mark.asyncio
    async def test_get_export_summary(self, exporter, mock_storage_manager, sample_game):
        """Test export summary generation."""
        # Setup mocks
        mock_storage_manager.get_game.return_value = sample_game
        
        game_ids = ["game_001", "game_002"]
        
        # Execute
        result = await exporter.get_export_summary(game_ids)
        
        # Verify
        assert result['total_games'] == 2
        assert result['completed_games'] == 2
        assert result['ongoing_games'] == 0
        assert result['total_moves'] == 4  # 2 games * 2 moves each
        assert len(result['players']) == 2
        assert len(result['models']) == 2
        assert len(result['tournaments']) == 1
        assert result['date_range']['earliest'] is not None
        assert result['date_range']['latest'] is not None
    
    def test_game_to_csv_row(self, exporter, sample_game):
        """Test conversion of game record to CSV row."""
        row = exporter._game_to_csv_row(sample_game)
        
        assert len(row) == 21  # Expected number of CSV columns
        assert row[0] == "test_game_001"  # game_id
        assert row[1] == "test_tournament"  # tournament_id
        assert row[4] == "white_player"  # white_player_id
        assert row[9] == "black_player"  # black_player_id
        assert row[14] == "1-0"  # result
        assert row[15] == "1"  # winner
        assert row[16] == "checkmate"  # termination
    
    def test_move_to_csv_row(self, exporter, sample_moves):
        """Test conversion of move record to CSV row."""
        move = sample_moves[0]  # First move (e4)
        row = exporter._move_to_csv_row(move)
        
        assert len(row) == 20  # Expected number of CSV columns
        assert row[0] == "test_game_001"  # game_id
        assert row[1] == "1"  # move_number
        assert row[2] == "1"  # player (white)
        assert row[4] == "e4"  # move_san
        assert row[5] == "e2e4"  # move_uci
        assert row[6] == "True"  # is_legal
        assert row[15] == "0"  # rethink_attempts_count
    
    def test_player_stats_to_csv_row(self, exporter):
        """Test conversion of player stats to CSV row."""
        stats = PlayerStats(
            player_id="test_player",
            games_played=10,
            wins=6,
            losses=3,
            draws=1,
            illegal_move_rate=0.05,
            average_thinking_time=2500.0,
            elo_rating=1550.0,
            last_updated=datetime(2024, 1, 15, 12, 0, 0)
        )
        
        row = exporter._player_stats_to_csv_row(stats)
        
        assert len(row) == 12  # Expected number of CSV columns
        assert row[0] == "test_player"
        assert row[1] == "10"  # games_played
        assert row[5] == "0.6000"  # win_rate
        assert row[10] == "1550.00"  # elo_rating
    
    def test_generate_pgn_moves_empty(self, exporter):
        """Test PGN move generation with empty move list."""
        result = exporter._generate_pgn_moves([])
        assert result == ""
    
    def test_generate_pgn_moves_single_white_move(self, exporter, sample_moves):
        """Test PGN move generation with single white move."""
        white_move = sample_moves[0]  # e4
        result = exporter._generate_pgn_moves([white_move])
        assert result == "1. e4"
    
    def test_json_serializer_datetime(self, exporter):
        """Test JSON serializer handles datetime objects."""
        dt = datetime(2024, 1, 15, 10, 30, 0)
        result = exporter._json_serializer(dt)
        assert result == "2024-01-15T10:30:00"
    
    def test_json_serializer_unsupported_type(self, exporter):
        """Test JSON serializer raises error for unsupported types."""
        with pytest.raises(TypeError):
            exporter._json_serializer(object())


# Integration Tests

class TestGameExporterIntegration:
    """Integration tests for GameExporter with real-like scenarios."""
    
    @pytest.fixture
    def complex_game_scenario(self):
        """Create a complex game scenario for integration testing."""
        game = GameRecord(
            game_id="complex_game_001",
            tournament_id="integration_test_tournament",
            start_time=datetime(2024, 1, 15, 14, 0, 0),
            end_time=datetime(2024, 1, 15, 15, 30, 0),
            players={
                0: PlayerInfo(
                    player_id="ai_black",
                    model_name="claude-3",
                    model_provider="anthropic",
                    agent_type="ChessRethinkAgent",
                    elo_rating=1650.0
                ),
                1: PlayerInfo(
                    player_id="ai_white",
                    model_name="gpt-4-turbo",
                    model_provider="openai",
                    agent_type="ChessLLMAgent",
                    elo_rating=1700.0
                )
            },
            initial_fen="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
            final_fen="r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/3P1N2/PPP2PPP/RNBQK2R b KQkq - 0 4",
            outcome=GameOutcome(
                result=GameResult.DRAW,
                winner=None,
                termination=TerminationReason.STALEMATE
            ),
            total_moves=8,
            game_duration_seconds=5400.0
        )
        
        moves = [
            # Move 1: e4
            MoveRecord(
                game_id="complex_game_001",
                move_number=1,
                player=1,
                timestamp=datetime(2024, 1, 15, 14, 1, 0),
                fen_before="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
                fen_after="rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1",
                legal_moves=["e4", "d4", "Nf3", "c4", "g3"],
                move_san="e4",
                move_uci="e2e4",
                is_legal=True,
                prompt_text="Play the opening move as white.",
                raw_response="I'll start with 1.e4, the King's Pawn opening.",
                parsed_move="e4",
                parsing_success=True,
                thinking_time_ms=3000,
                api_call_time_ms=800,
                parsing_time_ms=150,
                move_quality_score=0.8
            ),
            # Move 1: e5
            MoveRecord(
                game_id="complex_game_001",
                move_number=1,
                player=0,
                timestamp=datetime(2024, 1, 15, 14, 2, 30),
                fen_before="rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1",
                fen_after="rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq e6 0 2",
                legal_moves=["e5", "e6", "c5", "d6", "Nf6"],
                move_san="e5",
                move_uci="e7e5",
                is_legal=True,
                prompt_text="Respond to white's e4 opening.",
                raw_response="I'll play e5 to mirror and control the center.",
                parsed_move="e5",
                parsing_success=True,
                thinking_time_ms=2500,
                api_call_time_ms=750,
                parsing_time_ms=120,
                move_quality_score=0.85,
                rethink_attempts=[
                    RethinkAttempt(
                        attempt_number=1,
                        prompt_text="Consider alternative responses to e4.",
                        raw_response="I could play c5 for the Sicilian, but e5 is more principled.",
                        parsed_move="e5",
                        was_legal=True,
                        timestamp=datetime(2024, 1, 15, 14, 2, 15)
                    )
                ]
            ),
            # Add more moves for complexity...
        ]
        
        return game, moves
    
    @pytest.mark.asyncio
    async def test_full_export_workflow(self, complex_game_scenario):
        """Test complete export workflow with complex game data."""
        game, moves = complex_game_scenario
        
        # Create mocks
        mock_storage_manager = AsyncMock()
        mock_query_engine = AsyncMock()
        
        mock_storage_manager.get_game.return_value = game
        mock_storage_manager.get_moves.return_value = moves
        mock_query_engine.query_games_advanced.return_value = [game]
        
        exporter = GameExporter(mock_storage_manager, mock_query_engine)
        
        # Test PGN export
        pgn_result = await exporter.export_game_pgn("complex_game_001")
        assert '[Event "integration_test_tournament"]' in pgn_result
        assert '[Result "1/2-1/2"]' in pgn_result
        assert '1. e4 e5' in pgn_result
        
        # Test JSON export
        json_result = await exporter.export_game_json("complex_game_001")
        json_data = json.loads(json_result)
        assert json_data['game_id'] == "complex_game_001"
        assert json_data['outcome']['result'] == "1/2-1/2"
        assert len(json_data['moves']) == 2
        assert json_data['moves'][1]['rethink_attempts'][0]['attempt_number'] == 1
        
        # Test CSV export
        csv_result = await exporter.export_games_csv(["complex_game_001"])
        lines = csv_result.strip().split('\n')
        assert len(lines) == 2  # Header + 1 game
        assert 'complex_game_001' in csv_result
        assert '1/2-1/2' in csv_result
        
        # Test filtered export
        filters = GameFilters(completed_only=True)
        filtered_result = await exporter.export_filtered_games(filters, format_type='json')
        filtered_data = json.loads(filtered_result)
        assert len(filtered_data) == 1
        assert filtered_data[0]['game_id'] == "complex_game_001"