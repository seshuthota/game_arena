"""
Tests for the Game Arena storage models.

This module contains unit tests to verify the data models work correctly
with validation and basic functionality.
"""

import pytest
from datetime import datetime
from game_arena.storage.models import (
    GameRecord, PlayerInfo, GameOutcome, MoveRecord, RethinkAttempt,
    PlayerStats, MoveAccuracyStats, GameResult, TerminationReason
)


def test_player_info_creation():
    """Test PlayerInfo creation and validation."""
    player = PlayerInfo(
        player_id="test_player",
        model_name="gpt-4",
        model_provider="openai",
        agent_type="ChessLLMAgent"
    )
    
    assert player.player_id == "test_player"
    assert player.model_name == "gpt-4"
    assert player.elo_rating is None


def test_player_info_validation():
    """Test PlayerInfo validation errors."""
    with pytest.raises(ValueError, match="player_id cannot be empty"):
        PlayerInfo(
            player_id="",
            model_name="gpt-4",
            model_provider="openai",
            agent_type="ChessLLMAgent"
        )


def test_game_outcome_creation():
    """Test GameOutcome creation and validation."""
    outcome = GameOutcome(
        result=GameResult.WHITE_WINS,
        winner=1,
        termination=TerminationReason.CHECKMATE
    )
    
    assert outcome.result == GameResult.WHITE_WINS
    assert outcome.winner == 1
    assert outcome.termination == TerminationReason.CHECKMATE


def test_game_outcome_validation():
    """Test GameOutcome validation errors."""
    with pytest.raises(ValueError, match="White wins but winner is not 1"):
        GameOutcome(
            result=GameResult.WHITE_WINS,
            winner=0,
            termination=TerminationReason.CHECKMATE
        )


def test_game_record_creation():
    """Test GameRecord creation and validation."""
    players = {
        0: PlayerInfo("black_player", "gpt-4", "openai", "ChessLLMAgent"),
        1: PlayerInfo("white_player", "gemini", "google", "ChessLLMAgent")
    }
    
    game = GameRecord(
        game_id="test_game_001",
        start_time=datetime.now(),
        players=players
    )
    
    assert game.game_id == "test_game_001"
    assert len(game.players) == 2
    assert not game.is_completed
    assert game.total_moves == 0


def test_game_record_validation():
    """Test GameRecord validation errors."""
    with pytest.raises(ValueError, match="game_id cannot be empty"):
        GameRecord(
            game_id="",
            start_time=datetime.now(),
            players={}
        )


def test_rethink_attempt_creation():
    """Test RethinkAttempt creation and validation."""
    attempt = RethinkAttempt(
        attempt_number=1,
        prompt_text="Please reconsider your move",
        raw_response="e4",
        parsed_move="e4",
        was_legal=True,
        timestamp=datetime.now()
    )
    
    assert attempt.attempt_number == 1
    assert attempt.was_legal


def test_move_record_creation():
    """Test MoveRecord creation and validation."""
    move = MoveRecord(
        game_id="test_game_001",
        move_number=1,
        player=1,
        timestamp=datetime.now(),
        fen_before="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
        fen_after="rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1",
        legal_moves=["e4", "d4", "Nf3"],
        move_san="e4",
        move_uci="e2e4",
        is_legal=True,
        prompt_text="Make your move",
        raw_response="I'll play e4"
    )
    
    assert move.game_id == "test_game_001"
    assert move.is_legal
    assert not move.had_rethink
    assert move.total_time_ms == 0


def test_player_stats_creation():
    """Test PlayerStats creation and properties."""
    stats = PlayerStats(
        player_id="test_player",
        games_played=10,
        wins=6,
        losses=3,
        draws=1
    )
    
    assert stats.win_rate == 0.6
    assert stats.draw_rate == 0.1
    assert stats.loss_rate == 0.3


def test_move_accuracy_stats():
    """Test MoveAccuracyStats creation and properties."""
    stats = MoveAccuracyStats(
        total_moves=100,
        legal_moves=95,
        illegal_moves=5,
        parsing_failures=2,
        blunders=3
    )
    
    assert stats.accuracy_percentage == 95.0
    assert stats.parsing_success_rate == 98.0
    assert stats.blunder_rate == 3.0


if __name__ == "__main__":
    pytest.main([__file__])