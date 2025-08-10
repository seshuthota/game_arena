"""
ELO Rating System for Chess Game Analysis.

This module implements a proper ELO rating calculation system with K-factor support,
handling various game outcomes and providing accurate rating updates.
"""

import logging
import math
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class GameOutcome(Enum):
    """Game outcome from a player's perspective."""
    WIN = 1.0
    DRAW = 0.5
    LOSS = 0.0


@dataclass
class ELORatingUpdate:
    """Represents an ELO rating update for a player."""
    player_id: str
    old_rating: float
    new_rating: float
    rating_change: float
    opponent_id: str
    opponent_rating: float
    game_outcome: GameOutcome
    k_factor: float
    expected_score: float
    actual_score: float


class ELORatingSystem:
    """
    Implements the ELO rating system for chess games.
    
    The ELO rating system calculates the relative skill levels of players
    based on their game results. This implementation supports:
    - Configurable K-factors based on player rating and experience
    - Proper handling of draws (0.5 points each)
    - Rating floor to prevent ratings from going too low
    - Comprehensive logging and validation
    """
    
    def __init__(
        self,
        default_rating: float = 1500.0,
        rating_floor: float = 100.0,
        k_factor_high: float = 32.0,  # For new players (< 30 games or rating < 2100)
        k_factor_medium: float = 24.0,  # For intermediate players
        k_factor_low: float = 16.0,  # For experienced players (> 30 games and rating > 2400)
        provisional_games_threshold: int = 30
    ):
        """
        Initialize the ELO rating system.
        
        Args:
            default_rating: Starting rating for new players
            rating_floor: Minimum possible rating
            k_factor_high: K-factor for new/lower-rated players
            k_factor_medium: K-factor for intermediate players  
            k_factor_low: K-factor for experienced/high-rated players
            provisional_games_threshold: Games needed to exit provisional status
        """
        self.default_rating = default_rating
        self.rating_floor = rating_floor
        self.k_factor_high = k_factor_high
        self.k_factor_medium = k_factor_medium
        self.k_factor_low = k_factor_low
        self.provisional_games_threshold = provisional_games_threshold
        
        logger.info(f"Initialized ELO rating system with default rating {default_rating}")
    
    def get_k_factor(self, player_rating: float, games_played: int) -> float:
        """
        Determine the appropriate K-factor for a player.
        
        K-factor determines how much ratings change after each game:
        - Higher K-factor = more volatile ratings (for new players)
        - Lower K-factor = more stable ratings (for experienced players)
        
        Args:
            player_rating: Current rating of the player
            games_played: Number of games the player has played
            
        Returns:
            Appropriate K-factor for the player
        """
        # New players get high K-factor for faster rating adjustment
        if games_played < self.provisional_games_threshold:
            return self.k_factor_high
        
        # Experienced high-rated players get low K-factor for stability
        if player_rating >= 2400:
            return self.k_factor_low
        
        # Intermediate players get medium K-factor
        if player_rating >= 2100:
            return self.k_factor_medium
        
        # Lower-rated experienced players still get high K-factor
        return self.k_factor_high
    
    def calculate_expected_score(self, player_rating: float, opponent_rating: float) -> float:
        """
        Calculate the expected score for a player against an opponent.
        
        Uses the standard ELO formula: E = 1 / (1 + 10^((opponent_rating - player_rating) / 400))
        
        Args:
            player_rating: Rating of the player
            opponent_rating: Rating of the opponent
            
        Returns:
            Expected score (0.0 to 1.0)
        """
        rating_difference = opponent_rating - player_rating
        expected_score = 1.0 / (1.0 + math.pow(10, rating_difference / 400.0))
        
        logger.debug(f"Expected score: {expected_score:.3f} (player: {player_rating}, opponent: {opponent_rating})")
        return expected_score
    
    def calculate_rating_change(
        self,
        player_rating: float,
        opponent_rating: float,
        actual_score: float,
        k_factor: Optional[float] = None,
        games_played: int = 0
    ) -> float:
        """
        Calculate the rating change for a player after a game.
        
        Uses the ELO formula: ΔR = K × (S - E)
        Where:
        - ΔR = rating change
        - K = K-factor
        - S = actual score (1 for win, 0.5 for draw, 0 for loss)
        - E = expected score
        
        Args:
            player_rating: Current rating of the player
            opponent_rating: Rating of the opponent
            actual_score: Actual game result (1.0 = win, 0.5 = draw, 0.0 = loss)
            k_factor: Override K-factor (if None, calculated automatically)
            games_played: Number of games played (for K-factor calculation)
            
        Returns:
            Rating change (positive for rating increase, negative for decrease)
        """
        if k_factor is None:
            k_factor = self.get_k_factor(player_rating, games_played)
        
        expected_score = self.calculate_expected_score(player_rating, opponent_rating)
        rating_change = k_factor * (actual_score - expected_score)
        
        logger.debug(f"Rating change: {rating_change:.2f} (K={k_factor}, actual={actual_score}, expected={expected_score:.3f})")
        return rating_change
    
    def calculate_new_rating(
        self,
        player_rating: float,
        opponent_rating: float,
        game_outcome: GameOutcome,
        k_factor: Optional[float] = None,
        games_played: int = 0
    ) -> float:
        """
        Calculate the new rating for a player after a game.
        
        Args:
            player_rating: Current rating of the player
            opponent_rating: Rating of the opponent
            game_outcome: Result of the game from player's perspective
            k_factor: Override K-factor (if None, calculated automatically)
            games_played: Number of games played (for K-factor calculation)
            
        Returns:
            New rating for the player
        """
        actual_score = game_outcome.value
        rating_change = self.calculate_rating_change(
            player_rating, opponent_rating, actual_score, k_factor, games_played
        )
        
        new_rating = player_rating + rating_change
        
        # Apply rating floor
        new_rating = max(new_rating, self.rating_floor)
        
        logger.debug(f"New rating: {new_rating:.2f} (was {player_rating:.2f}, change: {rating_change:+.2f})")
        return new_rating
    
    def update_ratings_for_game(
        self,
        player1_id: str,
        player1_rating: float,
        player1_games: int,
        player2_id: str,
        player2_rating: float,
        player2_games: int,
        game_result: str,  # "WHITE_WINS", "BLACK_WINS", "DRAW"
        player1_is_white: bool = True
    ) -> Tuple[ELORatingUpdate, ELORatingUpdate]:
        """
        Update ratings for both players after a game.
        
        Args:
            player1_id: ID of the first player
            player1_rating: Current rating of the first player
            player1_games: Number of games played by the first player
            player2_id: ID of the second player
            player2_rating: Current rating of the second player
            player2_games: Number of games played by the second player
            game_result: Game result ("WHITE_WINS", "BLACK_WINS", "DRAW")
            player1_is_white: Whether player1 played as white
            
        Returns:
            Tuple of (player1_update, player2_update)
        """
        # Determine outcomes for each player
        if game_result == "DRAW":
            player1_outcome = GameOutcome.DRAW
            player2_outcome = GameOutcome.DRAW
        elif game_result == "WHITE_WINS":
            if player1_is_white:
                player1_outcome = GameOutcome.WIN
                player2_outcome = GameOutcome.LOSS
            else:
                player1_outcome = GameOutcome.LOSS
                player2_outcome = GameOutcome.WIN
        elif game_result == "BLACK_WINS":
            if player1_is_white:
                player1_outcome = GameOutcome.LOSS
                player2_outcome = GameOutcome.WIN
            else:
                player1_outcome = GameOutcome.WIN
                player2_outcome = GameOutcome.LOSS
        else:
            raise ValueError(f"Invalid game result: {game_result}")
        
        # Calculate K-factors
        player1_k_factor = self.get_k_factor(player1_rating, player1_games)
        player2_k_factor = self.get_k_factor(player2_rating, player2_games)
        
        # Calculate expected scores
        player1_expected = self.calculate_expected_score(player1_rating, player2_rating)
        player2_expected = self.calculate_expected_score(player2_rating, player1_rating)
        
        # Calculate new ratings
        player1_new_rating = self.calculate_new_rating(
            player1_rating, player2_rating, player1_outcome, player1_k_factor, player1_games
        )
        player2_new_rating = self.calculate_new_rating(
            player2_rating, player1_rating, player2_outcome, player2_k_factor, player2_games
        )
        
        # Create update objects
        player1_update = ELORatingUpdate(
            player_id=player1_id,
            old_rating=player1_rating,
            new_rating=player1_new_rating,
            rating_change=player1_new_rating - player1_rating,
            opponent_id=player2_id,
            opponent_rating=player2_rating,
            game_outcome=player1_outcome,
            k_factor=player1_k_factor,
            expected_score=player1_expected,
            actual_score=player1_outcome.value
        )
        
        player2_update = ELORatingUpdate(
            player_id=player2_id,
            old_rating=player2_rating,
            new_rating=player2_new_rating,
            rating_change=player2_new_rating - player2_rating,
            opponent_id=player1_id,
            opponent_rating=player1_rating,
            game_outcome=player2_outcome,
            k_factor=player2_k_factor,
            expected_score=player2_expected,
            actual_score=player2_outcome.value
        )
        
        logger.info(f"ELO updates - {player1_id}: {player1_rating:.1f} → {player1_new_rating:.1f} ({player1_new_rating - player1_rating:+.1f}), "
                   f"{player2_id}: {player2_rating:.1f} → {player2_new_rating:.1f} ({player2_new_rating - player2_rating:+.1f})")
        
        return player1_update, player2_update
    
    def validate_rating(self, rating: float) -> bool:
        """
        Validate that a rating is within acceptable bounds.
        
        Args:
            rating: Rating to validate
            
        Returns:
            True if rating is valid, False otherwise
        """
        return (
            isinstance(rating, (int, float)) and
            not math.isnan(rating) and
            not math.isinf(rating) and
            rating >= self.rating_floor and
            rating <= 4000.0  # Reasonable upper bound
        )
    
    def get_rating_category(self, rating: float) -> str:
        """
        Get the rating category for a player.
        
        Args:
            rating: Player's rating
            
        Returns:
            Rating category string
        """
        if rating >= 2400:
            return "Master"
        elif rating >= 2200:
            return "Expert"
        elif rating >= 2000:
            return "Class A"
        elif rating >= 1800:
            return "Class B"
        elif rating >= 1600:
            return "Class C"
        elif rating >= 1400:
            return "Class D"
        elif rating >= 1200:
            return "Class E"
        else:
            return "Beginner"