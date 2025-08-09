"""
Comprehensive tests for the ELO rating system.

This module tests the ELO rating calculation accuracy, K-factor logic,
and various game outcome scenarios to ensure statistical accuracy.
"""

import pytest
import math
from datetime import datetime

from elo_rating import ELORatingSystem, GameOutcome, ELORatingUpdate


class TestELORatingSystem:
    """Test cases for the ELO rating system."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.elo_system = ELORatingSystem()
    
    def test_initialization(self):
        """Test ELO system initialization with default values."""
        assert self.elo_system.default_rating == 1500.0
        assert self.elo_system.rating_floor == 100.0
        assert self.elo_system.k_factor_high == 32.0
        assert self.elo_system.k_factor_medium == 24.0
        assert self.elo_system.k_factor_low == 16.0
        assert self.elo_system.provisional_games_threshold == 30
    
    def test_custom_initialization(self):
        """Test ELO system initialization with custom values."""
        custom_elo = ELORatingSystem(
            default_rating=1200.0,
            rating_floor=200.0,
            k_factor_high=40.0,
            k_factor_medium=20.0,
            k_factor_low=10.0,
            provisional_games_threshold=20
        )
        
        assert custom_elo.default_rating == 1200.0
        assert custom_elo.rating_floor == 200.0
        assert custom_elo.k_factor_high == 40.0
        assert custom_elo.k_factor_medium == 20.0
        assert custom_elo.k_factor_low == 10.0
        assert custom_elo.provisional_games_threshold == 20
    
    def test_k_factor_calculation(self):
        """Test K-factor calculation based on rating and games played."""
        # New player (< 30 games) should get high K-factor
        assert self.elo_system.get_k_factor(1500.0, 10) == 32.0
        assert self.elo_system.get_k_factor(2000.0, 25) == 32.0
        
        # Experienced high-rated player should get low K-factor
        assert self.elo_system.get_k_factor(2500.0, 50) == 16.0
        assert self.elo_system.get_k_factor(2400.0, 100) == 16.0
        
        # Intermediate player should get medium K-factor
        assert self.elo_system.get_k_factor(2200.0, 50) == 24.0
        assert self.elo_system.get_k_factor(2300.0, 40) == 24.0
        
        # Lower-rated experienced player should get high K-factor
        assert self.elo_system.get_k_factor(1800.0, 50) == 32.0
        assert self.elo_system.get_k_factor(2000.0, 100) == 32.0
    
    def test_expected_score_calculation(self):
        """Test expected score calculation using ELO formula."""
        # Equal ratings should give 0.5 expected score
        expected = self.elo_system.calculate_expected_score(1500.0, 1500.0)
        assert abs(expected - 0.5) < 0.001
        
        # Higher rated player should have higher expected score
        expected_higher = self.elo_system.calculate_expected_score(1600.0, 1500.0)
        assert expected_higher > 0.5
        assert expected_higher < 1.0
        
        # Lower rated player should have lower expected score
        expected_lower = self.elo_system.calculate_expected_score(1400.0, 1500.0)
        assert expected_lower < 0.5
        assert expected_lower > 0.0
        
        # Test specific known values
        # 400 point difference should give approximately 0.909 expected score
        expected_400_diff = self.elo_system.calculate_expected_score(1900.0, 1500.0)
        assert abs(expected_400_diff - 0.909) < 0.01
    
    def test_rating_change_calculation(self):
        """Test rating change calculation."""
        # Win against equal opponent with default K-factor
        change = self.elo_system.calculate_rating_change(1500.0, 1500.0, 1.0, k_factor=32.0)
        expected_change = 32.0 * (1.0 - 0.5)  # K * (actual - expected)
        assert abs(change - expected_change) < 0.001
        assert change == 16.0
        
        # Loss against equal opponent
        change = self.elo_system.calculate_rating_change(1500.0, 1500.0, 0.0, k_factor=32.0)
        expected_change = 32.0 * (0.0 - 0.5)
        assert abs(change - expected_change) < 0.001
        assert change == -16.0
        
        # Draw against equal opponent
        change = self.elo_system.calculate_rating_change(1500.0, 1500.0, 0.5, k_factor=32.0)
        assert abs(change) < 0.001  # Should be approximately 0
        
        # Win against higher rated opponent (upset)
        change = self.elo_system.calculate_rating_change(1400.0, 1600.0, 1.0, k_factor=32.0)
        assert change > 16.0  # Should gain more than against equal opponent
        
        # Loss against lower rated opponent (upset)
        change = self.elo_system.calculate_rating_change(1600.0, 1400.0, 0.0, k_factor=32.0)
        assert change < -16.0  # Should lose more than against equal opponent
    
    def test_new_rating_calculation(self):
        """Test new rating calculation."""
        # Win against equal opponent
        new_rating = self.elo_system.calculate_new_rating(1500.0, 1500.0, GameOutcome.WIN, k_factor=32.0)
        assert new_rating == 1516.0
        
        # Loss against equal opponent
        new_rating = self.elo_system.calculate_new_rating(1500.0, 1500.0, GameOutcome.LOSS, k_factor=32.0)
        assert new_rating == 1484.0
        
        # Draw against equal opponent
        new_rating = self.elo_system.calculate_new_rating(1500.0, 1500.0, GameOutcome.DRAW, k_factor=32.0)
        assert abs(new_rating - 1500.0) < 0.001
        
        # Test rating floor
        new_rating = self.elo_system.calculate_new_rating(150.0, 2000.0, GameOutcome.LOSS, k_factor=32.0)
        assert new_rating >= self.elo_system.rating_floor
    
    def test_game_outcome_enum_values(self):
        """Test that GameOutcome enum has correct values."""
        assert GameOutcome.WIN.value == 1.0
        assert GameOutcome.DRAW.value == 0.5
        assert GameOutcome.LOSS.value == 0.0
    
    def test_update_ratings_for_game_white_wins(self):
        """Test rating updates when white wins."""
        player1_update, player2_update = self.elo_system.update_ratings_for_game(
            player1_id="player1",
            player1_rating=1500.0,
            player1_games=10,
            player2_id="player2", 
            player2_rating=1500.0,
            player2_games=10,
            game_result="WHITE_WINS",
            player1_is_white=True
        )
        
        # Player1 (white) should gain rating
        assert player1_update.new_rating > player1_update.old_rating
        assert player1_update.game_outcome == GameOutcome.WIN
        assert player1_update.rating_change > 0
        
        # Player2 (black) should lose rating
        assert player2_update.new_rating < player2_update.old_rating
        assert player2_update.game_outcome == GameOutcome.LOSS
        assert player2_update.rating_change < 0
        
        # Rating changes should be equal and opposite (approximately)
        assert abs(player1_update.rating_change + player2_update.rating_change) < 0.1
    
    def test_update_ratings_for_game_black_wins(self):
        """Test rating updates when black wins."""
        player1_update, player2_update = self.elo_system.update_ratings_for_game(
            player1_id="player1",
            player1_rating=1500.0,
            player1_games=10,
            player2_id="player2",
            player2_rating=1500.0,
            player2_games=10,
            game_result="BLACK_WINS",
            player1_is_white=True
        )
        
        # Player1 (white) should lose rating
        assert player1_update.new_rating < player1_update.old_rating
        assert player1_update.game_outcome == GameOutcome.LOSS
        
        # Player2 (black) should gain rating
        assert player2_update.new_rating > player2_update.old_rating
        assert player2_update.game_outcome == GameOutcome.WIN
    
    def test_update_ratings_for_game_draw(self):
        """Test rating updates for a draw."""
        player1_update, player2_update = self.elo_system.update_ratings_for_game(
            player1_id="player1",
            player1_rating=1500.0,
            player1_games=10,
            player2_id="player2",
            player2_rating=1500.0,
            player2_games=10,
            game_result="DRAW",
            player1_is_white=True
        )
        
        # Both players should have minimal rating change for equal ratings
        assert abs(player1_update.rating_change) < 0.1
        assert abs(player2_update.rating_change) < 0.1
        assert player1_update.game_outcome == GameOutcome.DRAW
        assert player2_update.game_outcome == GameOutcome.DRAW
    
    def test_update_ratings_different_k_factors(self):
        """Test that different K-factors are applied correctly."""
        # New player vs experienced player
        player1_update, player2_update = self.elo_system.update_ratings_for_game(
            player1_id="new_player",
            player1_rating=1500.0,
            player1_games=5,  # New player
            player2_id="experienced_player",
            player2_rating=2500.0,
            player2_games=100,  # Experienced high-rated player
            game_result="WHITE_WINS",
            player1_is_white=True
        )
        
        # New player should have higher K-factor (32) vs experienced player's lower K-factor (16)
        assert player1_update.k_factor == 32.0
        assert player2_update.k_factor == 16.0
        
        # New player should gain more rating than experienced player loses
        assert abs(player1_update.rating_change) > abs(player2_update.rating_change)
    
    def test_rating_validation(self):
        """Test rating validation."""
        assert self.elo_system.validate_rating(1500.0) is True
        assert self.elo_system.validate_rating(100.0) is True  # At floor
        assert self.elo_system.validate_rating(4000.0) is True  # At ceiling
        
        assert self.elo_system.validate_rating(50.0) is False  # Below floor
        assert self.elo_system.validate_rating(5000.0) is False  # Above ceiling
        assert self.elo_system.validate_rating(float('nan')) is False  # NaN
        assert self.elo_system.validate_rating(float('inf')) is False  # Infinity
        assert self.elo_system.validate_rating("1500") is False  # Wrong type
    
    def test_rating_categories(self):
        """Test rating category classification."""
        assert self.elo_system.get_rating_category(2500) == "Master"
        assert self.elo_system.get_rating_category(2300) == "Expert"
        assert self.elo_system.get_rating_category(2100) == "Class A"
        assert self.elo_system.get_rating_category(1900) == "Class B"
        assert self.elo_system.get_rating_category(1700) == "Class C"
        assert self.elo_system.get_rating_category(1500) == "Class D"
        assert self.elo_system.get_rating_category(1300) == "Class E"
        assert self.elo_system.get_rating_category(1000) == "Beginner"
    
    def test_invalid_game_result(self):
        """Test handling of invalid game results."""
        with pytest.raises(ValueError, match="Invalid game result"):
            self.elo_system.update_ratings_for_game(
                "player1", 1500.0, 10, "player2", 1500.0, 10, "INVALID_RESULT"
            )
    
    def test_elo_rating_update_object(self):
        """Test ELORatingUpdate object creation and properties."""
        update = ELORatingUpdate(
            player_id="test_player",
            old_rating=1500.0,
            new_rating=1516.0,
            rating_change=16.0,
            opponent_id="opponent",
            opponent_rating=1500.0,
            game_outcome=GameOutcome.WIN,
            k_factor=32.0,
            expected_score=0.5,
            actual_score=1.0
        )
        
        assert update.player_id == "test_player"
        assert update.old_rating == 1500.0
        assert update.new_rating == 1516.0
        assert update.rating_change == 16.0
        assert update.opponent_id == "opponent"
        assert update.opponent_rating == 1500.0
        assert update.game_outcome == GameOutcome.WIN
        assert update.k_factor == 32.0
        assert update.expected_score == 0.5
        assert update.actual_score == 1.0
    
    def test_extreme_rating_differences(self):
        """Test ELO calculations with extreme rating differences."""
        # Very high rated player vs very low rated player
        expected = self.elo_system.calculate_expected_score(2800.0, 800.0)
        assert expected > 0.99  # Should be almost certain to win
        
        # Very low rated player vs very high rated player
        expected = self.elo_system.calculate_expected_score(800.0, 2800.0)
        assert expected < 0.01  # Should be almost certain to lose
        
        # Upset: low rated player beats high rated player
        new_rating = self.elo_system.calculate_new_rating(
            800.0, 2800.0, GameOutcome.WIN, k_factor=32.0
        )
        assert new_rating > 830.0  # Should gain significant rating
    
    def test_rating_conservation(self):
        """Test that total rating points are approximately conserved."""
        # Multiple games between players should conserve total rating
        player1_rating = 1500.0
        player2_rating = 1500.0
        
        total_rating_before = player1_rating + player2_rating
        
        # Simulate several games
        for game_result in ["WHITE_WINS", "BLACK_WINS", "DRAW", "WHITE_WINS", "DRAW"]:
            p1_update, p2_update = self.elo_system.update_ratings_for_game(
                "p1", player1_rating, 50, "p2", player2_rating, 50, game_result, True
            )
            player1_rating = p1_update.new_rating
            player2_rating = p2_update.new_rating
        
        total_rating_after = player1_rating + player2_rating
        
        # Total rating should be approximately conserved (small differences due to rounding)
        assert abs(total_rating_after - total_rating_before) < 1.0


if __name__ == "__main__":
    pytest.main([__file__])