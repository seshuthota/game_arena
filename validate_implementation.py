#!/usr/bin/env python3
"""
Comprehensive validation script for Game Arena implementation.

This script validates statistics accuracy, leaderboard calculations, error handling,
and performance metrics using known datasets and test scenarios.
"""

import asyncio
import json
import time
import sqlite3
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import logging
import sys
import math

# Add backend to path for imports
sys.path.append('web_interface/backend')

from game_arena.storage import QueryEngine, create_database
from statistics_calculator import AccurateStatisticsCalculator
from elo_rating import AccurateELOCalculator
from data_validator import DataValidator
from error_handling import ErrorHandlingService
from performance_telemetry import telemetry

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class ValidationResult:
    """Result of a validation test."""
    test_name: str
    passed: bool
    expected: Any
    actual: Any
    error_message: Optional[str] = None
    performance_ms: Optional[float] = None

@dataclass  
class TestGame:
    """Test game data for validation."""
    game_id: str
    player1_id: str
    player2_id: str
    result: str  # "1-0", "0-1", "1/2-1/2"
    moves: List[str]
    opening_eco: str
    termination: str

class GameArenaValidator:
    """Comprehensive validation suite for Game Arena."""
    
    def __init__(self, database_path: str = "test_validation.db"):
        self.database_path = database_path
        self.query_engine = None
        self.statistics_calculator = None
        self.elo_calculator = None
        self.data_validator = None
        self.error_handler = None
        self.results: List[ValidationResult] = []
        
    async def initialize(self):
        """Initialize all components for testing."""
        logger.info("Initializing validation components...")
        
        # Create test database
        create_database(self.database_path)
        
        # Initialize components
        self.query_engine = await QueryEngine.create(self.database_path)
        self.statistics_calculator = AccurateStatisticsCalculator(self.query_engine)
        self.elo_calculator = AccurateELOCalculator()
        self.data_validator = DataValidator()
        self.error_handler = ErrorHandlingService(self.data_validator)
        
        logger.info("Validation components initialized")
    
    def add_result(self, result: ValidationResult):
        """Add validation result."""
        self.results.append(result)
        status = "✅ PASS" if result.passed else "❌ FAIL"
        perf = f" ({result.performance_ms:.2f}ms)" if result.performance_ms else ""
        logger.info(f"{status} {result.test_name}{perf}")
        
        if not result.passed and result.error_message:
            logger.error(f"  Error: {result.error_message}")
    
    def create_test_games(self) -> List[TestGame]:
        """Create known test games with predictable statistics."""
        return [
            TestGame(
                game_id="test_game_1",
                player1_id="gpt_4",
                player2_id="claude_3_5",
                result="1-0",  # GPT-4 wins
                moves=["e4", "e5", "Nf3", "Nc6", "Bb5", "a6", "Ba4", "Nf6", "O-O", "Be7", "Re1", "b5", "Bb3", "d6", "c3", "O-O", "h3", "Nb8", "d4", "Nbd7"],
                opening_eco="C88",  # Spanish Opening
                termination="normal"
            ),
            TestGame(
                game_id="test_game_2", 
                player1_id="claude_3_5",
                player2_id="gpt_4",
                result="0-1",  # GPT-4 wins (as Black)
                moves=["d4", "Nf6", "c4", "e6", "Nc3", "d5", "Bg5", "Be7", "e3", "O-O", "Nf3", "h6", "Bh4", "b6"],
                opening_eco="D37",  # Queen's Gambit Declined
                termination="normal"
            ),
            TestGame(
                game_id="test_game_3",
                player1_id="gpt_4", 
                player2_id="claude_3_5",
                result="1/2-1/2",  # Draw
                moves=["e4", "c5", "Nf3", "d6", "d4", "cxd4", "Nxd4", "Nf6", "Nc3", "a6"],
                opening_eco="B90",  # Sicilian Najdorf
                termination="agreement"
            ),
            TestGame(
                game_id="test_game_4",
                player1_id="gemini_pro",
                player2_id="gpt_4",
                result="1-0",  # Gemini wins
                moves=["Nf3", "d5", "d4", "Nf6", "c4", "e6", "Nc3", "Be7", "Bg5", "O-O"],
                opening_eco="D53",  # Queen's Gambit Declined
                termination="normal"
            ),
            TestGame(
                game_id="test_game_5",
                player1_id="claude_3_5",
                player2_id="gemini_pro", 
                result="0-1",  # Gemini wins (as Black)
                moves=["e4", "e6", "d4", "d5", "Nc3", "Bb4", "e5", "c5", "a3", "Bxc3+"],
                opening_eco="C02",  # French Defense
                termination="resignation"
            ),
        ]
    
    async def setup_test_data(self):
        """Set up test data in database."""
        logger.info("Setting up test data...")
        
        test_games = self.create_test_games()
        
        # Insert test games into database
        for game in test_games:
            # Convert to database format
            game_data = {
                'game_id': game.game_id,
                'players': {
                    'white': {'player_id': game.player1_id, 'model_name': game.player1_id.replace('_', '-')},
                    'black': {'player_id': game.player2_id, 'model_name': game.player2_id.replace('_', '-')}
                },
                'moves': [{'move': move, 'move_number': i//2 + 1} for i, move in enumerate(game.moves)],
                'result': game.result,
                'opening_eco': game.opening_eco,
                'termination': game.termination,
                'is_completed': True,
                'total_moves': len(game.moves)
            }
            
            # Insert into database (this would normally go through the storage layer)
            # For testing, we'll use direct SQL insertion
            await self._insert_test_game(game_data)
        
        logger.info(f"Inserted {len(test_games)} test games")
    
    async def _insert_test_game(self, game_data: Dict[str, Any]):
        """Insert test game directly into database."""
        # This is a simplified insertion for testing purposes
        # In production, this would go through the proper storage layer
        
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        
        try:
            # Insert basic game data
            cursor.execute("""
                INSERT OR REPLACE INTO games 
                (game_id, white_player_id, black_player_id, result, opening_eco, 
                 termination, is_completed, total_moves, moves_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                game_data['game_id'],
                game_data['players']['white']['player_id'],
                game_data['players']['black']['player_id'], 
                game_data['result'],
                game_data['opening_eco'],
                game_data['termination'],
                game_data['is_completed'],
                game_data['total_moves'],
                json.dumps(game_data['moves'])
            ))
            
            conn.commit()
            
        finally:
            conn.close()
    
    async def validate_statistics_accuracy(self):
        """Validate statistics calculation accuracy."""
        logger.info("Validating statistics accuracy...")
        
        start_time = time.time()
        
        try:
            # Calculate statistics
            stats = await self.statistics_calculator.calculate_leaderboard_stats()
            
            duration_ms = (time.time() - start_time) * 1000
            
            # Expected results based on our test data:
            # GPT-4: 2 wins, 1 draw, 2 losses = win rate 40%
            # Claude-3.5: 0 wins, 1 draw, 2 losses = win rate 0%  
            # Gemini-Pro: 2 wins, 0 draws, 1 loss = win rate 66.7%
            
            expected_players = {'gpt_4', 'claude_3_5', 'gemini_pro'}
            actual_players = {player['player_id'] for player in stats}
            
            self.add_result(ValidationResult(
                test_name="Statistics - Player Coverage",
                passed=expected_players.issubset(actual_players),
                expected=expected_players,
                actual=actual_players,
                performance_ms=duration_ms
            ))
            
            # Check specific player statistics
            for player_stats in stats:
                if player_stats['player_id'] == 'gpt_4':
                    # GPT-4 should have: 2 wins, 2 losses, 1 draw
                    expected_games = 5
                    expected_wins = 2
                    expected_draws = 1
                    
                    self.add_result(ValidationResult(
                        test_name="Statistics - GPT-4 Game Count",
                        passed=player_stats['games_played'] == expected_games,
                        expected=expected_games,
                        actual=player_stats['games_played']
                    ))
                    
                    self.add_result(ValidationResult(
                        test_name="Statistics - GPT-4 Win Count", 
                        passed=player_stats['wins'] == expected_wins,
                        expected=expected_wins,
                        actual=player_stats['wins']
                    ))
                    
                elif player_stats['player_id'] == 'gemini_pro':
                    # Gemini should have highest win rate
                    expected_wins = 2
                    expected_games = 3
                    
                    self.add_result(ValidationResult(
                        test_name="Statistics - Gemini Win Rate",
                        passed=player_stats['wins'] == expected_wins and player_stats['games_played'] == expected_games,
                        expected=f"{expected_wins}/{expected_games} games",
                        actual=f"{player_stats['wins']}/{player_stats['games_played']} games"
                    ))
            
        except Exception as e:
            self.add_result(ValidationResult(
                test_name="Statistics - Calculation Error",
                passed=False,
                expected="No errors",
                actual=str(e),
                error_message=str(e)
            ))
    
    async def validate_elo_calculations(self):
        """Validate ELO rating calculations."""
        logger.info("Validating ELO calculations...")
        
        start_time = time.time()
        
        try:
            # Test ELO calculation with known inputs
            initial_rating = 1400
            opponent_rating = 1400
            
            # Test win scenario
            win_change = self.elo_calculator.calculate_elo_change(
                initial_rating, opponent_rating, 1.0  # Win
            )
            
            # Expected change for equal players: ~16 points for a win
            expected_change = 16
            
            self.add_result(ValidationResult(
                test_name="ELO - Win Calculation",
                passed=abs(win_change - expected_change) <= 1,  # Allow 1 point tolerance
                expected=expected_change,
                actual=win_change
            ))
            
            # Test loss scenario
            loss_change = self.elo_calculator.calculate_elo_change(
                initial_rating, opponent_rating, 0.0  # Loss
            )
            
            expected_loss_change = -16
            
            self.add_result(ValidationResult(
                test_name="ELO - Loss Calculation",
                passed=abs(loss_change - expected_loss_change) <= 1,
                expected=expected_loss_change,
                actual=loss_change
            ))
            
            # Test draw scenario
            draw_change = self.elo_calculator.calculate_elo_change(
                initial_rating, opponent_rating, 0.5  # Draw
            )
            
            expected_draw_change = 0
            
            self.add_result(ValidationResult(
                test_name="ELO - Draw Calculation",
                passed=abs(draw_change - expected_draw_change) <= 1,
                expected=expected_draw_change,
                actual=draw_change
            ))
            
            # Test rating difference scenario
            higher_rating = 1600
            lower_rating = 1200
            
            # Higher rated player should gain less for winning
            high_win_change = self.elo_calculator.calculate_elo_change(
                higher_rating, lower_rating, 1.0
            )
            
            # Lower rated player should gain more for winning
            low_win_change = self.elo_calculator.calculate_elo_change(
                lower_rating, higher_rating, 1.0  
            )
            
            self.add_result(ValidationResult(
                test_name="ELO - Rating Difference Logic",
                passed=low_win_change > high_win_change,
                expected=f"Lower rated gain ({low_win_change}) > Higher rated gain ({high_win_change})",
                actual=f"Lower: {low_win_change}, Higher: {high_win_change}",
                performance_ms=(time.time() - start_time) * 1000
            ))
            
        except Exception as e:
            self.add_result(ValidationResult(
                test_name="ELO - Calculation Error",
                passed=False,
                expected="No errors",
                actual=str(e),
                error_message=str(e)
            ))
    
    async def validate_data_quality_handling(self):
        """Validate data validation and error handling."""
        logger.info("Validating data quality handling...")
        
        start_time = time.time()
        
        try:
            # Test FEN validation
            valid_fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
            invalid_fen = "invalid_fen_string"
            
            valid_result = self.data_validator.validate_fen(valid_fen)
            invalid_result = self.data_validator.validate_fen(invalid_fen)
            
            self.add_result(ValidationResult(
                test_name="Data Validation - Valid FEN",
                passed=valid_result.is_valid,
                expected=True,
                actual=valid_result.is_valid
            ))
            
            self.add_result(ValidationResult(
                test_name="Data Validation - Invalid FEN",
                passed=not invalid_result.is_valid,
                expected=False,
                actual=invalid_result.is_valid
            ))
            
            # Test error recovery
            corrupted_game_data = {
                'game_id': 'corrupted_game',
                'moves': ['e4', None, 'Nf3'],  # None should be handled
                'result': '1-0'
            }
            
            recovery_result = self.error_handler.recover_corrupted_game(corrupted_game_data)
            
            self.add_result(ValidationResult(
                test_name="Error Recovery - Corrupted Game",
                passed=recovery_result.can_continue,
                expected=True,
                actual=recovery_result.can_continue,
                performance_ms=(time.time() - start_time) * 1000
            ))
            
        except Exception as e:
            self.add_result(ValidationResult(
                test_name="Data Validation - Processing Error",
                passed=False,
                expected="No errors",
                actual=str(e),
                error_message=str(e)
            ))
    
    async def validate_performance_benchmarks(self):
        """Validate performance meets acceptable benchmarks."""
        logger.info("Validating performance benchmarks...")
        
        # Test statistics calculation performance
        start_time = time.time()
        
        try:
            await self.statistics_calculator.calculate_leaderboard_stats()
            stats_duration = (time.time() - start_time) * 1000
            
            # Should complete within 1 second for test data
            self.add_result(ValidationResult(
                test_name="Performance - Statistics Calculation",
                passed=stats_duration < 1000,
                expected="< 1000ms",
                actual=f"{stats_duration:.2f}ms",
                performance_ms=stats_duration
            ))
            
            # Test database query performance
            start_time = time.time()
            games = await self.query_engine.query_games()
            query_duration = (time.time() - start_time) * 1000
            
            self.add_result(ValidationResult(
                test_name="Performance - Database Query",
                passed=query_duration < 100,
                expected="< 100ms", 
                actual=f"{query_duration:.2f}ms",
                performance_ms=query_duration
            ))
            
            # Test memory usage (basic check)
            import psutil
            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024
            
            self.add_result(ValidationResult(
                test_name="Performance - Memory Usage",
                passed=memory_mb < 200,  # Should use less than 200MB for test data
                expected="< 200MB",
                actual=f"{memory_mb:.1f}MB"
            ))
            
        except Exception as e:
            self.add_result(ValidationResult(
                test_name="Performance - Benchmark Error",
                passed=False,
                expected="No errors",
                actual=str(e),
                error_message=str(e)
            ))
    
    async def validate_error_scenarios(self):
        """Test error handling with real-world scenarios."""
        logger.info("Validating error scenarios...")
        
        # Test missing move data scenario
        incomplete_game = {
            'game_id': 'incomplete_game',
            'moves': ['e4', 'e5'],  # Very short game
            'result': None,  # No result
            'players': {'white': {'player_id': 'test1'}, 'black': {'player_id': 'test2'}}
        }
        
        try:
            validation_result = self.data_validator.validate_game_data(incomplete_game)
            
            self.add_result(ValidationResult(
                test_name="Error Handling - Incomplete Game",
                passed=not validation_result.is_valid and validation_result.can_proceed,
                expected="Invalid but recoverable",
                actual=f"Valid: {validation_result.is_valid}, Can proceed: {validation_result.can_proceed}"
            ))
            
            # Test invalid player data
            invalid_player_game = {
                'game_id': 'invalid_player_game',
                'moves': ['e4', 'e5', 'Nf3', 'Nc6'],
                'result': '1-0',
                'players': None  # Invalid player data
            }
            
            validation_result = self.data_validator.validate_game_data(invalid_player_game)
            
            self.add_result(ValidationResult(
                test_name="Error Handling - Invalid Player Data",
                passed=not validation_result.is_valid,
                expected=False,
                actual=validation_result.is_valid
            ))
            
        except Exception as e:
            self.add_result(ValidationResult(
                test_name="Error Scenarios - Processing Error",
                passed=False,
                expected="Handled gracefully",
                actual=str(e),
                error_message=str(e)
            ))
    
    def generate_report(self) -> str:
        """Generate comprehensive validation report."""
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r.passed)
        failed_tests = total_tests - passed_tests
        
        success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
        
        # Calculate performance metrics
        performance_results = [r for r in self.results if r.performance_ms is not None]
        avg_performance = sum(r.performance_ms for r in performance_results) / len(performance_results) if performance_results else 0
        
        report = f"""
# Game Arena Implementation Validation Report

**Generated:** {time.strftime('%Y-%m-%d %H:%M:%S')}
**Database:** {self.database_path}

## Summary

- **Total Tests:** {total_tests}
- **Passed:** {passed_tests} ✅
- **Failed:** {failed_tests} ❌
- **Success Rate:** {success_rate:.1f}%
- **Average Performance:** {avg_performance:.2f}ms

## Test Results

"""
        
        # Group results by category
        categories = {}
        for result in self.results:
            category = result.test_name.split(' - ')[0]
            if category not in categories:
                categories[category] = []
            categories[category].append(result)
        
        for category, category_results in categories.items():
            category_passed = sum(1 for r in category_results if r.passed)
            category_total = len(category_results)
            
            report += f"\n### {category} ({category_passed}/{category_total})\n\n"
            
            for result in category_results:
                status = "✅" if result.passed else "❌"
                perf = f" `{result.performance_ms:.2f}ms`" if result.performance_ms else ""
                
                report += f"- {status} **{result.test_name.split(' - ', 1)[1]}**{perf}\n"
                
                if not result.passed:
                    report += f"  - Expected: `{result.expected}`\n"
                    report += f"  - Actual: `{result.actual}`\n"
                    if result.error_message:
                        report += f"  - Error: {result.error_message}\n"
                
                report += "\n"
        
        # Add performance analysis
        if performance_results:
            report += "\n## Performance Analysis\n\n"
            
            # Sort by performance
            performance_results.sort(key=lambda r: r.performance_ms, reverse=True)
            
            report += "| Test | Duration |\n|------|----------|\n"
            for result in performance_results:
                report += f"| {result.test_name} | {result.performance_ms:.2f}ms |\n"
        
        # Add recommendations
        report += "\n## Recommendations\n\n"
        
        if failed_tests == 0:
            report += "🎉 **All tests passed!** The implementation is ready for production deployment.\n\n"
        else:
            report += f"⚠️ **{failed_tests} tests failed.** Review the failed tests before deployment:\n\n"
            
            for result in self.results:
                if not result.passed:
                    report += f"- **{result.test_name}:** {result.error_message or 'Review expected vs actual values'}\n"
        
        if avg_performance > 500:
            report += "⚡ **Performance optimization recommended** - average test time exceeds 500ms.\n"
        
        report += "\n## Next Steps\n\n"
        report += "1. **Address Failed Tests:** Fix any issues identified in failed tests\n"
        report += "2. **Performance Testing:** Run load tests with larger datasets\n"
        report += "3. **User Testing:** Deploy to staging for user acceptance testing\n"
        report += "4. **Monitoring Setup:** Configure production monitoring and alerting\n"
        report += "5. **Documentation:** Update deployment and user documentation\n"
        
        return report
    
    async def cleanup(self):
        """Clean up test resources."""
        if self.query_engine:
            await self.query_engine.close()
        
        # Remove test database
        Path(self.database_path).unlink(missing_ok=True)

async def main():
    """Main validation function."""
    validator = GameArenaValidator()
    
    try:
        await validator.initialize()
        await validator.setup_test_data()
        
        # Run all validation tests
        await validator.validate_statistics_accuracy()
        await validator.validate_elo_calculations()
        await validator.validate_data_quality_handling()
        await validator.validate_performance_benchmarks()
        await validator.validate_error_scenarios()
        
        # Generate and save report
        report = validator.generate_report()
        
        # Save report to file
        report_file = f"validation_report_{int(time.time())}.md"
        with open(report_file, 'w') as f:
            f.write(report)
        
        print(report)
        print(f"\nReport saved to: {report_file}")
        
        # Return exit code based on results
        failed_tests = sum(1 for r in validator.results if not r.passed)
        return 0 if failed_tests == 0 else 1
        
    finally:
        await validator.cleanup()

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)