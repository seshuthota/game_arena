"""
Tests for the DataValidator class.

This module contains comprehensive tests for FEN validation, move notation validation,
player information validation, and game data validation.
"""

import pytest
from datetime import datetime

from data_validator import (
    DataValidator, ValidationResult, ValidationError, ValidationSeverity, DataQualityMetrics
)


class TestDataValidator:
    """Test cases for DataValidator class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.validator = DataValidator()
    
    def test_validate_fen_valid_starting_position(self):
        """Test validation of valid starting position FEN."""
        fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        result = self.validator.validate_fen(fen)
        
        assert result.is_valid
        assert result.can_proceed
        assert result.confidence_level == 1.0
        assert len(result.errors) == 0
        assert len(result.warnings) == 0
    
    def test_validate_fen_valid_mid_game_position(self):
        """Test validation of valid mid-game FEN."""
        fen = "rnbqkb1r/pppp1ppp/5n2/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 4 3"
        result = self.validator.validate_fen(fen)
        
        assert result.is_valid
        assert result.can_proceed
        assert result.confidence_level == 1.0
        assert len(result.errors) == 0
    
    def test_validate_fen_empty_string(self):
        """Test validation of empty FEN string."""
        result = self.validator.validate_fen("")
        
        assert not result.is_valid
        assert not result.can_proceed
        assert result.confidence_level == 0.0
        assert len(result.errors) == 1
        assert result.errors[0].error_code == "FEN_MISSING"
    
    def test_validate_fen_none_value(self):
        """Test validation of None FEN value."""
        result = self.validator.validate_fen(None)
        
        assert not result.is_valid
        assert not result.can_proceed
        assert result.confidence_level == 0.0
        assert len(result.errors) == 1
        assert result.errors[0].error_code == "FEN_MISSING"
    
    def test_validate_fen_invalid_format(self):
        """Test validation of invalid FEN format."""
        fen = "invalid-fen-string"
        result = self.validator.validate_fen(fen)
        
        assert not result.is_valid
        assert not result.can_proceed
        assert result.confidence_level == 0.0
        assert len(result.errors) == 1
        assert result.errors[0].error_code == "FEN_INVALID_PARTS"  # This is what actually gets triggered first
    
    def test_validate_fen_wrong_number_of_parts(self):
        """Test validation of FEN with wrong number of parts."""
        fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq"  # Missing parts
        result = self.validator.validate_fen(fen)
        
        assert not result.is_valid
        assert not result.can_proceed
        assert result.confidence_level == 0.0
        assert len(result.errors) == 1
        assert result.errors[0].error_code == "FEN_INVALID_PARTS"
    
    def test_validate_fen_invalid_side_to_move(self):
        """Test validation of FEN with invalid side to move."""
        fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR x KQkq - 0 1"
        result = self.validator.validate_fen(fen)
        
        assert not result.is_valid
        assert result.can_proceed  # Not critical error
        assert len(result.errors) == 1
        assert result.errors[0].error_code == "FEN_INVALID_SIDE"
        assert result.errors[0].severity == ValidationSeverity.MAJOR
    
    def test_validate_fen_invalid_castling_rights(self):
        """Test validation of FEN with invalid castling rights."""
        fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w XYZ - 0 1"
        result = self.validator.validate_fen(fen)
        
        assert result.is_valid  # Minor error only - still valid
        assert result.can_proceed  # Minor error
        assert len(result.errors) == 1
        assert result.errors[0].error_code == "FEN_INVALID_CASTLING"
        assert result.errors[0].severity == ValidationSeverity.MINOR
    
    def test_validate_fen_invalid_en_passant(self):
        """Test validation of FEN with invalid en passant square."""
        fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq z9 0 1"
        result = self.validator.validate_fen(fen)
        
        assert not result.is_valid
        assert result.can_proceed  # Minor error
        assert len(result.errors) == 1
        assert result.errors[0].error_code == "FEN_INVALID_EN_PASSANT"
        assert result.errors[0].severity == ValidationSeverity.MINOR
    
    def test_validate_fen_invalid_halfmove_counter(self):
        """Test validation of FEN with invalid halfmove counter."""
        fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - abc 1"
        result = self.validator.validate_fen(fen)
        
        assert not result.is_valid
        assert result.can_proceed  # Minor error
        assert len(result.errors) == 1
        assert result.errors[0].error_code == "FEN_INVALID_HALFMOVE"
        assert result.errors[0].severity == ValidationSeverity.MINOR
    
    def test_validate_fen_negative_halfmove_counter(self):
        """Test validation of FEN with negative halfmove counter."""
        fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - -5 1"
        result = self.validator.validate_fen(fen)
        
        assert result.is_valid  # Warning, not error
        assert result.can_proceed
        assert len(result.warnings) == 1
        assert result.warnings[0].error_code == "FEN_NEGATIVE_HALFMOVE"
    
    def test_validate_fen_invalid_fullmove_counter(self):
        """Test validation of FEN with invalid fullmove counter."""
        fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 xyz"
        result = self.validator.validate_fen(fen)
        
        assert not result.is_valid
        assert result.can_proceed  # Minor error
        assert len(result.errors) == 1
        assert result.errors[0].error_code == "FEN_INVALID_FULLMOVE"
    
    def test_validate_fen_zero_fullmove_counter(self):
        """Test validation of FEN with zero fullmove counter."""
        fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 0"
        result = self.validator.validate_fen(fen)
        
        assert not result.is_valid
        assert result.can_proceed  # Minor error
        assert len(result.errors) == 1
        assert result.errors[0].error_code == "FEN_INVALID_FULLMOVE"
    
    def test_validate_fen_position_wrong_rank_count(self):
        """Test validation of FEN position with wrong number of ranks."""
        fen = "rnbqkbnr/pppppppp/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"  # Missing rank
        result = self.validator.validate_fen(fen)
        
        assert not result.is_valid
        assert not result.can_proceed
        assert len(result.errors) >= 1
        assert any(e.error_code == "FEN_INVALID_RANKS" for e in result.errors)
    
    def test_validate_fen_position_no_white_king(self):
        """Test validation of FEN position with no white king."""
        fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQ1BNR w KQkq - 0 1"  # No white king
        result = self.validator.validate_fen(fen)
        
        assert not result.is_valid
        assert not result.can_proceed
        assert any(e.error_code == "FEN_INVALID_WHITE_KING_COUNT" for e in result.errors)
    
    def test_validate_fen_position_multiple_black_kings(self):
        """Test validation of FEN position with multiple black kings."""
        fen = "rnbqkknr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"  # Two black kings
        result = self.validator.validate_fen(fen)
        
        assert not result.is_valid
        assert not result.can_proceed
        assert any(e.error_code == "FEN_INVALID_BLACK_KING_COUNT" for e in result.errors)
    
    def test_validate_fen_position_invalid_character(self):
        """Test validation of FEN position with invalid character."""
        fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQxBNR w KQkq - 0 1"  # Invalid 'x'
        result = self.validator.validate_fen(fen)
        
        assert not result.is_valid
        assert result.can_proceed  # Major error, not critical
        assert any(e.error_code == "FEN_INVALID_CHARACTER" for e in result.errors)
    
    def test_validate_fen_position_wrong_rank_length(self):
        """Test validation of FEN position with wrong rank length."""
        fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBN w KQkq - 0 1"  # Last rank too short
        result = self.validator.validate_fen(fen)
        
        assert not result.is_valid
        assert result.can_proceed  # Major error
        assert any(e.error_code == "FEN_INVALID_RANK_LENGTH" for e in result.errors)
    
    def test_validate_fen_excessive_pawns_warning(self):
        """Test validation of FEN with excessive pawns (promotion scenario)."""
        fen = "rnbqkbnr/PPPPPPPP/8/8/8/8/pppppppp/RNBQKBNR w KQkq - 0 1"  # 8 white pawns on 7th rank
        result = self.validator.validate_fen(fen)
        
        # This should be valid but generate warnings
        assert result.is_valid
        assert result.can_proceed
        assert len(result.warnings) >= 1
        assert any(w.error_code in ["FEN_EXCESSIVE_WHITE_PAWNS", "FEN_EXCESSIVE_BLACK_PAWNS"] for w in result.warnings)


class TestMoveNotationValidation:
    """Test cases for move notation validation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.validator = DataValidator()
    
    def test_validate_move_notation_valid_pawn_move(self):
        """Test validation of valid pawn move."""
        result = self.validator.validate_move_notation("e4")
        
        assert result.is_valid
        assert result.can_proceed
        assert result.confidence_level == 1.0
        assert len(result.errors) == 0
    
    def test_validate_move_notation_valid_piece_move(self):
        """Test validation of valid piece move."""
        result = self.validator.validate_move_notation("Nf3")
        
        assert result.is_valid
        assert result.can_proceed
        assert result.confidence_level == 1.0
        assert len(result.errors) == 0
    
    def test_validate_move_notation_valid_capture(self):
        """Test validation of valid capture move."""
        result = self.validator.validate_move_notation("exd5")
        
        assert result.is_valid
        assert result.can_proceed
        assert result.confidence_level == 1.0
        assert len(result.errors) == 0
    
    def test_validate_move_notation_valid_castling_kingside(self):
        """Test validation of valid kingside castling."""
        result = self.validator.validate_move_notation("O-O")
        
        assert result.is_valid
        assert result.can_proceed
        assert result.confidence_level == 1.0
        assert len(result.errors) == 0
    
    def test_validate_move_notation_valid_castling_queenside(self):
        """Test validation of valid queenside castling."""
        result = self.validator.validate_move_notation("O-O-O")
        
        assert result.is_valid
        assert result.can_proceed
        assert result.confidence_level == 1.0
        assert len(result.errors) == 0
    
    def test_validate_move_notation_valid_promotion(self):
        """Test validation of valid pawn promotion."""
        result = self.validator.validate_move_notation("e8=Q")
        
        assert result.is_valid
        assert result.can_proceed
        assert result.confidence_level == 1.0
        assert len(result.errors) == 0
    
    def test_validate_move_notation_valid_check(self):
        """Test validation of valid move with check."""
        result = self.validator.validate_move_notation("Qh5+")
        
        assert result.is_valid
        assert result.can_proceed
        assert result.confidence_level == 1.0
        assert len(result.errors) == 0
    
    def test_validate_move_notation_valid_checkmate(self):
        """Test validation of valid move with checkmate."""
        result = self.validator.validate_move_notation("Qf7#")
        
        assert result.is_valid
        assert result.can_proceed
        assert result.confidence_level == 1.0
        assert len(result.errors) == 0
    
    def test_validate_move_notation_empty_string(self):
        """Test validation of empty move notation."""
        result = self.validator.validate_move_notation("")
        
        assert not result.is_valid
        assert not result.can_proceed
        assert result.confidence_level == 0.0
        assert len(result.errors) == 1
        assert result.errors[0].error_code == "MOVE_MISSING"
    
    def test_validate_move_notation_none_value(self):
        """Test validation of None move notation."""
        result = self.validator.validate_move_notation(None)
        
        assert not result.is_valid
        assert not result.can_proceed
        assert result.confidence_level == 0.0
        assert len(result.errors) == 1
        assert result.errors[0].error_code == "MOVE_MISSING"
    
    def test_validate_move_notation_invalid_format(self):
        """Test validation of invalid move notation format."""
        result = self.validator.validate_move_notation("invalid-move")
        
        assert not result.is_valid
        assert result.can_proceed  # Major error, not critical
        assert len(result.errors) == 1
        assert result.errors[0].error_code == "MOVE_INVALID_FORMAT"
        assert result.errors[0].severity == ValidationSeverity.MAJOR
    
    def test_validate_move_notation_lowercase_castling_warning(self):
        """Test validation of lowercase castling notation."""
        result = self.validator.validate_move_notation("o-o")
        
        assert result.is_valid  # Warning, not error
        assert result.can_proceed
        assert len(result.warnings) == 1
        assert result.warnings[0].error_code == "MOVE_CASTLING_NOTATION"
    
    def test_validate_move_notation_zero_castling_warning(self):
        """Test validation of zero-based castling notation."""
        result = self.validator.validate_move_notation("0-0-0")
        
        assert result.is_valid  # Warning, not error
        assert result.can_proceed
        assert len(result.warnings) == 1
        assert result.warnings[0].error_code == "MOVE_CASTLING_NOTATION"
    
    def test_validate_move_notation_very_long_move(self):
        """Test validation of unusually long move notation."""
        result = self.validator.validate_move_notation("Nf3+++++++")
        
        assert result.is_valid  # Warning about length
        assert result.can_proceed
        assert len(result.warnings) == 1
        assert result.warnings[0].error_code == "MOVE_LONG_NOTATION"


class TestPlayerInfoValidation:
    """Test cases for player information validation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.validator = DataValidator()
    
    def test_validate_player_info_valid_complete(self):
        """Test validation of valid complete player info."""
        player_data = {
            'player_id': 'test_player_123',
            'model_name': 'GPT-4',
            'model_provider': 'OpenAI',
            'agent_type': 'chess_agent',
            'elo_rating': 1500.0
        }
        
        result = self.validator.validate_player_info(player_data)
        
        assert result.is_valid
        assert result.can_proceed
        assert result.confidence_level == 1.0
        assert len(result.errors) == 0
    
    def test_validate_player_info_valid_minimal(self):
        """Test validation of valid minimal player info."""
        player_data = {
            'player_id': 'test_player',
            'model_name': 'Test Model'
        }
        
        result = self.validator.validate_player_info(player_data)
        
        assert result.is_valid
        assert result.can_proceed
        assert result.confidence_level == 1.0
        assert len(result.errors) == 0
    
    def test_validate_player_info_missing_player_id(self):
        """Test validation of player info missing player_id."""
        player_data = {
            'model_name': 'Test Model'
        }
        
        result = self.validator.validate_player_info(player_data)
        
        assert not result.is_valid
        assert not result.can_proceed
        assert len(result.errors) == 1
        assert result.errors[0].error_code == "PLAYER_MISSING_REQUIRED_FIELD"
        assert result.errors[0].field == "player_id"
    
    def test_validate_player_info_missing_model_name(self):
        """Test validation of player info missing model_name."""
        player_data = {
            'player_id': 'test_player'
        }
        
        result = self.validator.validate_player_info(player_data)
        
        assert not result.is_valid
        assert not result.can_proceed
        assert len(result.errors) == 1
        assert result.errors[0].error_code == "PLAYER_MISSING_REQUIRED_FIELD"
        assert result.errors[0].field == "model_name"
    
    def test_validate_player_info_empty_player_id(self):
        """Test validation of player info with empty player_id."""
        player_data = {
            'player_id': '',
            'model_name': 'Test Model'
        }
        
        result = self.validator.validate_player_info(player_data)
        
        assert not result.is_valid
        assert not result.can_proceed
        assert len(result.errors) == 1
        assert result.errors[0].error_code == "PLAYER_MISSING_REQUIRED_FIELD"
    
    def test_validate_player_info_invalid_player_id_characters(self):
        """Test validation of player info with invalid player_id characters."""
        player_data = {
            'player_id': 'test@player!',
            'model_name': 'Test Model'
        }
        
        result = self.validator.validate_player_info(player_data)
        
        assert not result.is_valid
        assert result.can_proceed  # Major error, not critical
        assert len(result.errors) == 1
        assert result.errors[0].error_code == "PLAYER_INVALID_ID_FORMAT"
        assert result.errors[0].severity == ValidationSeverity.MAJOR
    
    def test_validate_player_info_very_long_player_id(self):
        """Test validation of player info with very long player_id."""
        player_data = {
            'player_id': 'a' * 150,  # Very long ID
            'model_name': 'Test Model'
        }
        
        result = self.validator.validate_player_info(player_data)
        
        assert result.is_valid  # Warning, not error
        assert result.can_proceed
        assert len(result.warnings) == 1
        assert result.warnings[0].error_code == "PLAYER_LONG_ID"
    
    def test_validate_player_info_very_long_model_name(self):
        """Test validation of player info with very long model_name."""
        player_data = {
            'player_id': 'test_player',
            'model_name': 'a' * 250  # Very long model name
        }
        
        result = self.validator.validate_player_info(player_data)
        
        assert result.is_valid  # Warning, not error
        assert result.can_proceed
        assert len(result.warnings) == 1
        assert result.warnings[0].error_code == "PLAYER_LONG_MODEL_NAME"
    
    def test_validate_player_info_negative_elo(self):
        """Test validation of player info with negative ELO rating."""
        player_data = {
            'player_id': 'test_player',
            'model_name': 'Test Model',
            'elo_rating': -100
        }
        
        result = self.validator.validate_player_info(player_data)
        
        assert result.is_valid  # Warning, not error
        assert result.can_proceed
        assert len(result.warnings) == 1
        assert result.warnings[0].error_code == "PLAYER_NEGATIVE_ELO"
    
    def test_validate_player_info_very_high_elo(self):
        """Test validation of player info with very high ELO rating."""
        player_data = {
            'player_id': 'test_player',
            'model_name': 'Test Model',
            'elo_rating': 5000
        }
        
        result = self.validator.validate_player_info(player_data)
        
        assert result.is_valid  # Warning, not error
        assert result.can_proceed
        assert len(result.warnings) == 1
        assert result.warnings[0].error_code == "PLAYER_HIGH_ELO"
    
    def test_validate_player_info_invalid_elo_type(self):
        """Test validation of player info with invalid ELO type."""
        player_data = {
            'player_id': 'test_player',
            'model_name': 'Test Model',
            'elo_rating': 'not_a_number'
        }
        
        result = self.validator.validate_player_info(player_data)
        
        assert not result.is_valid
        assert result.can_proceed  # Minor error
        assert len(result.errors) == 1
        assert result.errors[0].error_code == "PLAYER_INVALID_ELO_TYPE"
        assert result.errors[0].severity == ValidationSeverity.MINOR


class TestGameDataValidation:
    """Test cases for game data validation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.validator = DataValidator()
    
    def test_validate_game_data_valid_complete(self):
        """Test validation of valid complete game data."""
        game_data = {
            'game_id': 'test_game_123',
            'players': {
                '0': {
                    'player_id': 'player_1',
                    'model_name': 'Model A'
                },
                '1': {
                    'player_id': 'player_2',
                    'model_name': 'Model B'
                }
            },
            'start_time': '2024-01-01T10:00:00Z',
            'end_time': '2024-01-01T11:00:00Z',
            'total_moves': 50,
            'outcome': {
                'result': 'white_wins'
            }
        }
        
        result = self.validator.validate_game_data(game_data)
        
        assert result.is_valid
        assert result.can_proceed
        assert len(result.errors) == 0
    
    def test_validate_game_data_missing_game_id(self):
        """Test validation of game data missing game_id."""
        game_data = {
            'players': {
                '0': {'player_id': 'player_1', 'model_name': 'Model A'},
                '1': {'player_id': 'player_2', 'model_name': 'Model B'}
            },
            'start_time': '2024-01-01T10:00:00Z'
        }
        
        result = self.validator.validate_game_data(game_data)
        
        assert not result.is_valid
        assert not result.can_proceed
        assert len(result.errors) == 1
        assert result.errors[0].error_code == "GAME_MISSING_REQUIRED_FIELD"
        assert result.errors[0].field == "game_id"
    
    def test_validate_game_data_missing_players(self):
        """Test validation of game data missing players."""
        game_data = {
            'game_id': 'test_game',
            'start_time': '2024-01-01T10:00:00Z'
        }
        
        result = self.validator.validate_game_data(game_data)
        
        assert not result.is_valid
        assert not result.can_proceed
        assert len(result.errors) == 1
        assert result.errors[0].error_code == "GAME_MISSING_REQUIRED_FIELD"
        assert result.errors[0].field == "players"
    
    def test_validate_game_data_insufficient_players(self):
        """Test validation of game data with insufficient players."""
        game_data = {
            'game_id': 'test_game',
            'players': {
                '0': {'player_id': 'player_1', 'model_name': 'Model A'}
            },
            'start_time': '2024-01-01T10:00:00Z'
        }
        
        result = self.validator.validate_game_data(game_data)
        
        assert not result.is_valid
        assert not result.can_proceed
        assert len(result.errors) == 1
        assert result.errors[0].error_code == "GAME_INSUFFICIENT_PLAYERS"
    
    def test_validate_game_data_invalid_players_type(self):
        """Test validation of game data with invalid players type."""
        game_data = {
            'game_id': 'test_game',
            'players': ['player1', 'player2'],  # Should be dict, not list
            'start_time': '2024-01-01T10:00:00Z'
        }
        
        result = self.validator.validate_game_data(game_data)
        
        assert not result.is_valid
        assert not result.can_proceed
        assert len(result.errors) == 1
        assert result.errors[0].error_code == "GAME_INVALID_PLAYERS_TYPE"
    
    def test_validate_game_data_invalid_timestamp(self):
        """Test validation of game data with invalid timestamp."""
        game_data = {
            'game_id': 'test_game',
            'players': {
                '0': {'player_id': 'player_1', 'model_name': 'Model A'},
                '1': {'player_id': 'player_2', 'model_name': 'Model B'}
            },
            'start_time': 'invalid-timestamp'
        }
        
        result = self.validator.validate_game_data(game_data)
        
        assert not result.is_valid
        assert result.can_proceed  # Minor error
        assert len(result.errors) == 1
        assert result.errors[0].error_code == "GAME_INVALID_TIMESTAMP"
        assert result.errors[0].severity == ValidationSeverity.MINOR
    
    def test_validate_game_data_negative_total_moves(self):
        """Test validation of game data with negative total moves."""
        game_data = {
            'game_id': 'test_game',
            'players': {
                '0': {'player_id': 'player_1', 'model_name': 'Model A'},
                '1': {'player_id': 'player_2', 'model_name': 'Model B'}
            },
            'start_time': '2024-01-01T10:00:00Z',
            'total_moves': -5
        }
        
        result = self.validator.validate_game_data(game_data)
        
        assert not result.is_valid
        assert result.can_proceed  # Major error, not critical
        assert len(result.errors) == 1
        assert result.errors[0].error_code == "GAME_NEGATIVE_MOVES"
        assert result.errors[0].severity == ValidationSeverity.MAJOR
    
    def test_validate_game_data_many_moves_warning(self):
        """Test validation of game data with unusually many moves."""
        game_data = {
            'game_id': 'test_game',
            'players': {
                '0': {'player_id': 'player_1', 'model_name': 'Model A'},
                '1': {'player_id': 'player_2', 'model_name': 'Model B'}
            },
            'start_time': '2024-01-01T10:00:00Z',
            'total_moves': 1500
        }
        
        result = self.validator.validate_game_data(game_data)
        
        assert result.is_valid  # Warning, not error
        assert result.can_proceed
        assert len(result.warnings) == 1
        assert result.warnings[0].error_code == "GAME_MANY_MOVES"
    
    def test_validate_game_data_invalid_total_moves_type(self):
        """Test validation of game data with invalid total moves type."""
        game_data = {
            'game_id': 'test_game',
            'players': {
                '0': {'player_id': 'player_1', 'model_name': 'Model A'},
                '1': {'player_id': 'player_2', 'model_name': 'Model B'}
            },
            'start_time': '2024-01-01T10:00:00Z',
            'total_moves': 'fifty'
        }
        
        result = self.validator.validate_game_data(game_data)
        
        assert not result.is_valid
        assert result.can_proceed  # Minor error
        assert len(result.errors) == 1
        assert result.errors[0].error_code == "GAME_INVALID_MOVES_TYPE"
        assert result.errors[0].severity == ValidationSeverity.MINOR


class TestDataQualityMetrics:
    """Test cases for data quality metrics calculation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.validator = DataValidator()
    
    def test_calculate_data_quality_metrics_complete_data(self):
        """Test calculation of data quality metrics for complete data."""
        data = {
            'field1': 'value1',
            'field2': 'value2',
            'field3': 'value3',
            'optional1': 'optional_value'
        }
        required_fields = ['field1', 'field2', 'field3']
        optional_fields = ['optional1', 'optional2']
        
        metrics = self.validator.calculate_data_quality_metrics(data, required_fields, optional_fields)
        
        assert metrics.completeness == 0.8  # 4 out of 5 fields present
        assert metrics.accuracy == 1.0  # No validation errors
        assert metrics.consistency == 1.0
        assert metrics.confidence_level > 0.9
        assert len(metrics.missing_fields) == 0
        assert metrics.valid_fields == 4
        assert metrics.total_fields_checked == 5
    
    def test_calculate_data_quality_metrics_missing_required_fields(self):
        """Test calculation of data quality metrics with missing required fields."""
        data = {
            'field1': 'value1',
            'optional1': 'optional_value'
        }
        required_fields = ['field1', 'field2', 'field3']
        optional_fields = ['optional1', 'optional2']
        
        metrics = self.validator.calculate_data_quality_metrics(data, required_fields, optional_fields)
        
        assert metrics.completeness == 0.4  # 2 out of 5 fields present
        assert 'field2' in metrics.missing_fields
        assert 'field3' in metrics.missing_fields
        assert metrics.valid_fields == 2
        assert metrics.confidence_level < 0.7
    
    def test_calculate_data_quality_metrics_empty_data(self):
        """Test calculation of data quality metrics for empty data."""
        data = {}
        required_fields = ['field1', 'field2']
        optional_fields = ['optional1']
        
        metrics = self.validator.calculate_data_quality_metrics(data, required_fields, optional_fields)
        
        assert metrics.completeness == 0.0
        assert len(metrics.missing_fields) == 2
        assert metrics.valid_fields == 0
        assert metrics.confidence_level == 0.0
    
    def test_calculate_data_quality_metrics_no_fields(self):
        """Test calculation of data quality metrics with no fields to check."""
        data = {'some_field': 'some_value'}
        required_fields = []
        optional_fields = []
        
        metrics = self.validator.calculate_data_quality_metrics(data, required_fields, optional_fields)
        
        assert metrics.completeness == 1.0  # No fields to check
        assert metrics.total_fields_checked == 0
        assert metrics.valid_fields == 0
        assert metrics.confidence_level == 1.0


if __name__ == '__main__':
    pytest.main([__file__])