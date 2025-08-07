"""
Core data models for the Game Arena storage system.

This module defines the data structures used to represent games, moves,
players, and analytics data throughout the storage system.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum


class GameResult(Enum):
    """Standard chess game results."""
    WHITE_WINS = "1-0"
    BLACK_WINS = "0-1"
    DRAW = "1/2-1/2"
    ONGOING = "*"


class TerminationReason(Enum):
    """Reasons for game termination."""
    CHECKMATE = "checkmate"
    STALEMATE = "stalemate"
    RESIGNATION = "resignation"
    TIMEOUT = "timeout"
    ERROR = "error"
    INSUFFICIENT_MATERIAL = "insufficient_material"
    THREEFOLD_REPETITION = "threefold_repetition"
    FIFTY_MOVE_RULE = "fifty_move_rule"


@dataclass
class PlayerInfo:
    """Information about a player in a game."""
    player_id: str
    model_name: str
    model_provider: str
    agent_type: str  # "ChessLLMAgent", "ChessRethinkAgent"
    agent_config: Dict[str, Any] = field(default_factory=dict)
    elo_rating: Optional[float] = None
    
    def __post_init__(self):
        """Validate player information."""
        if not self.player_id:
            raise ValueError("player_id cannot be empty")
        if not self.model_name:
            raise ValueError("model_name cannot be empty")
        if not self.model_provider:
            raise ValueError("model_provider cannot be empty")
        if not self.agent_type:
            raise ValueError("agent_type cannot be empty")


@dataclass
class GameOutcome:
    """Represents the outcome of a completed game."""
    result: GameResult
    winner: Optional[int] = None  # 0 for black, 1 for white, None for draw
    termination: TerminationReason = TerminationReason.CHECKMATE
    
    def __post_init__(self):
        """Validate game outcome consistency."""
        if self.result == GameResult.WHITE_WINS and self.winner != 1:
            raise ValueError("White wins but winner is not 1")
        if self.result == GameResult.BLACK_WINS and self.winner != 0:
            raise ValueError("Black wins but winner is not 0")
        if self.result == GameResult.DRAW and self.winner is not None:
            raise ValueError("Draw game cannot have a winner")


@dataclass
class GameRecord:
    """Complete record of a chess game."""
    game_id: str
    start_time: datetime
    players: Dict[int, PlayerInfo]  # 0: Black, 1: White
    initial_fen: str = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    tournament_id: Optional[str] = None
    end_time: Optional[datetime] = None
    final_fen: Optional[str] = None
    outcome: Optional[GameOutcome] = None
    total_moves: int = 0
    game_duration_seconds: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate game record."""
        if not self.game_id:
            raise ValueError("game_id cannot be empty")
        if not self.players or len(self.players) != 2:
            raise ValueError("Must have exactly 2 players")
        if 0 not in self.players or 1 not in self.players:
            raise ValueError("Players must be indexed as 0 (black) and 1 (white)")
        if not self.initial_fen:
            raise ValueError("initial_fen cannot be empty")
        if self.total_moves < 0:
            raise ValueError("total_moves cannot be negative")
    
    @property
    def is_completed(self) -> bool:
        """Check if the game is completed."""
        return self.outcome is not None and self.end_time is not None
    
    @property
    def duration_minutes(self) -> Optional[float]:
        """Get game duration in minutes."""
        if self.game_duration_seconds is not None:
            return self.game_duration_seconds / 60.0
        return None


@dataclass
class RethinkAttempt:
    """Represents a single rethink attempt during move generation."""
    attempt_number: int
    prompt_text: str
    raw_response: str
    parsed_move: Optional[str]
    was_legal: bool
    timestamp: datetime
    
    def __post_init__(self):
        """Validate rethink attempt."""
        if self.attempt_number < 1:
            raise ValueError("attempt_number must be positive")
        if not self.prompt_text:
            raise ValueError("prompt_text cannot be empty")
        if not self.raw_response:
            raise ValueError("raw_response cannot be empty")


@dataclass
class MoveRecord:
    """Complete record of a single move in a game."""
    game_id: str
    move_number: int
    player: int  # 0 or 1
    timestamp: datetime
    
    # Game state
    fen_before: str
    fen_after: str
    legal_moves: List[str]
    
    # Move information
    move_san: str  # Standard Algebraic Notation
    move_uci: str  # Universal Chess Interface notation
    is_legal: bool
    
    # LLM interaction data
    prompt_text: str
    raw_response: str
    parsed_move: Optional[str] = None
    parsing_success: bool = True
    parsing_attempts: int = 1
    
    # Timing data
    thinking_time_ms: int = 0
    api_call_time_ms: int = 0
    parsing_time_ms: int = 0
    
    # Rethink data (if applicable)
    rethink_attempts: List[RethinkAttempt] = field(default_factory=list)
    
    # Quality metrics
    move_quality_score: Optional[float] = None
    blunder_flag: bool = False
    
    # Error information
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    
    def __post_init__(self):
        """Validate move record."""
        if not self.game_id:
            raise ValueError("game_id cannot be empty")
        if self.move_number < 1:
            raise ValueError("move_number must be positive")
        if self.player not in [0, 1]:
            raise ValueError("player must be 0 or 1")
        if not self.fen_before:
            raise ValueError("fen_before cannot be empty")
        if not self.fen_after:
            raise ValueError("fen_after cannot be empty")
        if not self.move_san:
            raise ValueError("move_san cannot be empty")
        if not self.move_uci:
            raise ValueError("move_uci cannot be empty")
        if not self.prompt_text:
            raise ValueError("prompt_text cannot be empty")
        if not self.raw_response:
            raise ValueError("raw_response cannot be empty")
        if self.parsing_attempts < 1:
            raise ValueError("parsing_attempts must be positive")
        if any(t < 0 for t in [self.thinking_time_ms, self.api_call_time_ms, self.parsing_time_ms]):
            raise ValueError("Timing values cannot be negative")
    
    @property
    def total_time_ms(self) -> int:
        """Get total time spent on this move."""
        return self.thinking_time_ms + self.api_call_time_ms + self.parsing_time_ms
    
    @property
    def had_rethink(self) -> bool:
        """Check if this move involved rethinking."""
        return len(self.rethink_attempts) > 0


@dataclass
class PlayerStats:
    """Aggregated statistics for a player."""
    player_id: str
    games_played: int = 0
    wins: int = 0
    losses: int = 0
    draws: int = 0
    illegal_move_rate: float = 0.0
    average_thinking_time: float = 0.0
    elo_rating: float = 1200.0  # Default ELO rating
    last_updated: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        """Validate player stats."""
        if not self.player_id:
            raise ValueError("player_id cannot be empty")
        if any(v < 0 for v in [self.games_played, self.wins, self.losses, self.draws]):
            raise ValueError("Game counts cannot be negative")
        if self.wins + self.losses + self.draws > self.games_played:
            raise ValueError("Sum of outcomes cannot exceed games played")
        if not 0.0 <= self.illegal_move_rate <= 1.0:
            raise ValueError("illegal_move_rate must be between 0 and 1")
        if self.average_thinking_time < 0:
            raise ValueError("average_thinking_time cannot be negative")
    
    @property
    def win_rate(self) -> float:
        """Calculate win rate."""
        if self.games_played == 0:
            return 0.0
        return self.wins / self.games_played
    
    @property
    def draw_rate(self) -> float:
        """Calculate draw rate."""
        if self.games_played == 0:
            return 0.0
        return self.draws / self.games_played
    
    @property
    def loss_rate(self) -> float:
        """Calculate loss rate."""
        if self.games_played == 0:
            return 0.0
        return self.losses / self.games_played


@dataclass
class MoveAccuracyStats:
    """Statistics about move accuracy and parsing success."""
    total_moves: int = 0
    legal_moves: int = 0
    illegal_moves: int = 0
    parsing_failures: int = 0
    total_rethink_attempts: int = 0
    blunders: int = 0
    
    def __post_init__(self):
        """Validate move accuracy stats."""
        if any(v < 0 for v in [self.total_moves, self.legal_moves, self.illegal_moves, 
                               self.parsing_failures, self.total_rethink_attempts, self.blunders]):
            raise ValueError("All counts must be non-negative")
        if self.legal_moves + self.illegal_moves > self.total_moves:
            raise ValueError("Legal + illegal moves cannot exceed total moves")
    
    @property
    def accuracy_percentage(self) -> float:
        """Calculate move accuracy percentage."""
        if self.total_moves == 0:
            return 0.0
        return (self.legal_moves / self.total_moves) * 100.0
    
    @property
    def parsing_success_rate(self) -> float:
        """Calculate parsing success rate."""
        if self.total_moves == 0:
            return 0.0
        successful_parses = self.total_moves - self.parsing_failures
        return (successful_parses / self.total_moves) * 100.0
    
    @property
    def average_rethink_attempts(self) -> float:
        """Calculate average rethink attempts per move."""
        if self.total_moves == 0:
            return 0.0
        return self.total_rethink_attempts / self.total_moves
    
    @property
    def blunder_rate(self) -> float:
        """Calculate blunder rate."""
        if self.total_moves == 0:
            return 0.0
        return (self.blunders / self.total_moves) * 100.0