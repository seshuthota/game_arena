"""
Accurate Statistics Calculator for Chess Game Analysis.

This module provides comprehensive and accurate statistics calculation
with proper handling of incomplete data, data validation, and error recovery.
Enhanced with intelligent caching for improved performance.
"""

import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict

from game_arena.storage import QueryEngine
from game_arena.storage.models import GameRecord, GameResult, PlayerInfo
from elo_rating import ELORatingSystem, GameOutcome
from statistics_cache import StatisticsCache, get_statistics_cache

logger = logging.getLogger(__name__)


@dataclass
class DataQualityMetrics:
    """Metrics about data quality and completeness."""
    total_games: int = 0
    complete_games: int = 0
    games_with_outcome: int = 0
    games_with_timing: int = 0
    games_with_moves: int = 0
    completeness_percentage: float = 0.0
    excluded_games: int = 0
    exclusion_reasons: Dict[str, int] = field(default_factory=dict)
    confidence_level: float = 0.0
    
    def calculate_metrics(self):
        """Calculate derived metrics."""
        if self.total_games > 0:
            self.completeness_percentage = (self.complete_games / self.total_games) * 100.0
            self.confidence_level = min(
                self.completeness_percentage / 100.0,
                (self.games_with_outcome / self.total_games) if self.total_games > 0 else 0.0
            )
        else:
            self.completeness_percentage = 0.0
            self.confidence_level = 0.0


@dataclass
class AccuratePlayerStatistics:
    """Comprehensive and accurate player statistics."""
    player_id: str
    model_name: str
    model_provider: str = ""
    
    # Game counts
    total_games: int = 0
    completed_games: int = 0
    wins: int = 0
    losses: int = 0
    draws: int = 0
    
    # Calculated percentages
    win_rate: float = 0.0
    draw_rate: float = 0.0
    loss_rate: float = 0.0
    
    # ELO rating
    current_elo: float = 1500.0
    peak_elo: float = 1500.0
    elo_history: List[Tuple[datetime, float]] = field(default_factory=list)
    
    # Performance metrics
    average_game_length: float = 0.0
    average_game_duration: float = 0.0
    total_moves: int = 0
    
    # Recent performance
    recent_games: List[str] = field(default_factory=list)  # Last 10 game results
    current_streak: int = 0
    streak_type: str = "none"  # "win", "loss", "draw", "none"
    longest_win_streak: int = 0
    
    # Opponent analysis
    average_opponent_elo: float = 0.0
    strongest_opponent_elo: float = 0.0
    weakest_opponent_elo: float = 0.0
    
    # Data quality
    data_quality: DataQualityMetrics = field(default_factory=DataQualityMetrics)
    last_updated: datetime = field(default_factory=datetime.now)
    
    def calculate_derived_stats(self):
        """Calculate derived statistics from base data."""
        if self.completed_games > 0:
            self.win_rate = (self.wins / self.completed_games) * 100.0
            self.draw_rate = (self.draws / self.completed_games) * 100.0
            self.loss_rate = (self.losses / self.completed_games) * 100.0
        else:
            self.win_rate = self.draw_rate = self.loss_rate = 0.0
        
        if self.total_games > 0:
            self.average_game_length = self.total_moves / self.total_games
        else:
            self.average_game_length = 0.0


@dataclass
class LeaderboardEntry:
    """Entry in the leaderboard with accurate statistics."""
    rank: int
    player_id: str
    model_name: str
    model_provider: str
    statistics: AccuratePlayerStatistics
    
    # Ranking metrics
    ranking_score: float = 0.0
    trend_direction: str = "stable"  # "up", "down", "stable"
    recent_form: str = "average"  # "excellent", "good", "average", "poor"


class DataValidator:
    """Validates game data and identifies quality issues."""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def validate_game_for_statistics(self, game: GameRecord) -> Tuple[bool, List[str]]:
        """
        Validate if a game can be used for statistics calculation.
        
        Args:
            game: Game record to validate
            
        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []
        
        # Check basic game data
        if not game.game_id:
            issues.append("Missing game ID")
        
        if not game.players or len(game.players) != 2:
            issues.append("Invalid player data")
        
        if not game.start_time:
            issues.append("Missing start time")
        
        # Check completion status
        if not game.is_completed:
            issues.append("Game not completed")
        
        # Check outcome data
        if game.is_completed and not game.outcome:
            issues.append("Completed game missing outcome")
        
        if game.outcome and not game.outcome.result:
            issues.append("Outcome missing result")
        
        # Check player information
        for position, player_info in game.players.items():
            if not player_info.player_id:
                issues.append(f"Player {position} missing ID")
            if not player_info.model_name:
                issues.append(f"Player {position} missing model name")
        
        # Check move count
        if game.total_moves < 0:
            issues.append("Invalid move count")
        
        is_valid = len(issues) == 0
        return is_valid, issues
    
    def validate_player_info(self, player_info: PlayerInfo) -> Tuple[bool, List[str]]:
        """
        Validate player information.
        
        Args:
            player_info: Player information to validate
            
        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []
        
        if not player_info.player_id:
            issues.append("Missing player ID")
        
        if not player_info.model_name:
            issues.append("Missing model name")
        
        if not player_info.model_provider:
            issues.append("Missing model provider")
        
        if player_info.elo_rating is not None:
            if not isinstance(player_info.elo_rating, (int, float)):
                issues.append("Invalid ELO rating type")
            elif player_info.elo_rating < 0 or player_info.elo_rating > 4000:
                issues.append("ELO rating out of reasonable range")
        
        is_valid = len(issues) == 0
        return is_valid, issues


class AccurateStatisticsCalculator:
    """
    Calculates accurate player statistics with proper error handling,
    data validation, and intelligent caching for improved performance.
    """
    
    def __init__(self, query_engine: QueryEngine, cache: Optional[StatisticsCache] = None):
        """Initialize the statistics calculator."""
        self.query_engine = query_engine
        self.elo_system = ELORatingSystem()
        self.validator = DataValidator()
        self.cache = cache or get_statistics_cache()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    async def calculate_player_statistics(
        self, 
        player_id: str,
        include_incomplete_data: bool = True,
        use_cache: bool = True
    ) -> Optional[AccuratePlayerStatistics]:
        """
        Calculate comprehensive and accurate statistics for a player with caching.
        
        Args:
            player_id: ID of the player to analyze
            include_incomplete_data: Whether to include games with incomplete data
            use_cache: Whether to use cached results if available
            
        Returns:
            AccuratePlayerStatistics object or None if player not found
        """
        # Create cache key
        cache_key_parts = ["player_stats", player_id, include_incomplete_data]
        
        if use_cache:
            # Try to get from cache first
            cached_stats = self.cache.get(
                cache_key_parts,
                dependencies=[f"player:{player_id}"]
            )
            
            if cached_stats is not None:
                self.logger.debug(f"Retrieved cached statistics for player {player_id}")
                return cached_stats
        
        try:
            # Calculate statistics (not cached or cache miss)
            stats = await self._calculate_player_statistics_uncached(player_id, include_incomplete_data)
            
            if stats and use_cache:
                # Cache the results with dependencies
                self.cache.set(
                    cache_key_parts,
                    stats,
                    ttl=300.0,  # 5 minutes
                    dependencies=[f"player:{player_id}"]
                )
                self.logger.debug(f"Cached statistics for player {player_id}")
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to calculate statistics for player {player_id}: {e}")
            return None

    async def _calculate_player_statistics_uncached(
        self, 
        player_id: str,
        include_incomplete_data: bool = True
    ) -> Optional[AccuratePlayerStatistics]:
        """
        Calculate comprehensive and accurate statistics for a player (uncached version).
        
        Args:
            player_id: ID of the player to analyze
            include_incomplete_data: Whether to include games with incomplete data
            
        Returns:
            AccuratePlayerStatistics object or None if player not found
        """
        # Get all games for this player
        all_games = await self.query_engine.get_games_by_players(player_id)
        
        if not all_games:
            self.logger.warning(f"No games found for player {player_id}")
            return None
        
        # Get player info from first valid game
        player_info = self._extract_player_info(all_games, player_id)
        if not player_info:
            self.logger.error(f"Could not extract player info for {player_id}")
            return None
        
        # Initialize statistics object
        stats = AccuratePlayerStatistics(
            player_id=player_id,
            model_name=player_info.model_name,
            model_provider=player_info.model_provider or "unknown"
        )
        
        # Validate and categorize games
        valid_games, data_quality = self._validate_and_categorize_games(all_games)
        stats.data_quality = data_quality
        
        # Use valid games or all games based on parameter
        games_to_analyze = valid_games if not include_incomplete_data else all_games
        
        if not games_to_analyze:
            self.logger.warning(f"No valid games to analyze for player {player_id}")
            return stats
        
        # Calculate basic game statistics
        await self._calculate_basic_game_stats(stats, games_to_analyze, player_id)
        
        # Calculate ELO rating and history
        await self._calculate_elo_statistics(stats, games_to_analyze, player_id)
        
        # Calculate performance metrics
        await self._calculate_performance_metrics(stats, games_to_analyze, player_id)
        
        # Calculate recent performance and streaks
        await self._calculate_recent_performance(stats, games_to_analyze, player_id)
        
        # Calculate opponent analysis
        await self._calculate_opponent_analysis(stats, games_to_analyze, player_id)
        
        # Calculate derived statistics
        stats.calculate_derived_stats()
        
        self.logger.info(f"Calculated statistics for {player_id}: {stats.wins}W-{stats.losses}L-{stats.draws}D, "
                       f"ELO: {stats.current_elo:.1f}, Win Rate: {stats.win_rate:.1f}%")
        
        return stats
    
    def _extract_player_info(self, games: List[GameRecord], player_id: str) -> Optional[PlayerInfo]:
        """Extract player information from games."""
        for game in games:
            for player_info in game.players.values():
                if player_info.player_id == player_id:
                    return player_info
        return None
    
    def _validate_and_categorize_games(self, games: List[GameRecord]) -> Tuple[List[GameRecord], DataQualityMetrics]:
        """Validate games and calculate data quality metrics."""
        valid_games = []
        data_quality = DataQualityMetrics()
        data_quality.total_games = len(games)
        
        for game in games:
            is_valid, issues = self.validator.validate_game_for_statistics(game)
            
            if is_valid:
                valid_games.append(game)
                data_quality.complete_games += 1
            else:
                data_quality.excluded_games += 1
                for issue in issues:
                    data_quality.exclusion_reasons[issue] = data_quality.exclusion_reasons.get(issue, 0) + 1
            
            # Track specific data availability
            if game.outcome and game.outcome.result:
                data_quality.games_with_outcome += 1
            
            if game.start_time and game.end_time:
                data_quality.games_with_timing += 1
            
            if game.total_moves > 0:
                data_quality.games_with_moves += 1
        
        data_quality.calculate_metrics()
        return valid_games, data_quality
    
    async def _calculate_basic_game_stats(
        self, 
        stats: AccuratePlayerStatistics, 
        games: List[GameRecord], 
        player_id: str
    ):
        """Calculate basic game statistics (wins, losses, draws)."""
        stats.total_games = len(games)
        
        for game in games:
            if not game.is_completed or not game.outcome:
                continue
            
            stats.completed_games += 1
            
            # Find player position in this game
            player_position = None
            for position, player_info in game.players.items():
                if player_info.player_id == player_id:
                    player_position = position
                    break
            
            if player_position is None:
                continue
            
            # Count wins, losses, draws based on game result
            result = game.outcome.result
            if result == GameResult.DRAW:
                stats.draws += 1
            elif result == GameResult.WHITE_WINS:
                if player_position == 1:  # Player was white
                    stats.wins += 1
                else:  # Player was black
                    stats.losses += 1
            elif result == GameResult.BLACK_WINS:
                if player_position == 0:  # Player was black
                    stats.wins += 1
                else:  # Player was white
                    stats.losses += 1
    
    async def _calculate_elo_statistics(
        self, 
        stats: AccuratePlayerStatistics, 
        games: List[GameRecord], 
        player_id: str
    ):
        """Calculate ELO rating and history."""
        # Sort games by start time for chronological ELO calculation
        sorted_games = sorted([g for g in games if g.start_time], key=lambda x: x.start_time)
        
        current_elo = self.elo_system.default_rating
        peak_elo = current_elo
        elo_history = [(datetime.now(), current_elo)]
        
        games_played = 0
        
        for game in sorted_games:
            if not game.is_completed or not game.outcome:
                continue
            
            # Find player and opponent info
            player_position = None
            opponent_info = None
            
            for position, player_info in game.players.items():
                if player_info.player_id == player_id:
                    player_position = position
                else:
                    opponent_info = player_info
            
            if player_position is None or opponent_info is None:
                continue
            
            # Get opponent ELO (use default if not available)
            opponent_elo = getattr(opponent_info, 'elo_rating', None) or self.elo_system.default_rating
            
            # Determine game outcome from player's perspective
            result = game.outcome.result
            if result == GameResult.DRAW:
                outcome = GameOutcome.DRAW
            elif result == GameResult.WHITE_WINS:
                outcome = GameOutcome.WIN if player_position == 1 else GameOutcome.LOSS
            elif result == GameResult.BLACK_WINS:
                outcome = GameOutcome.WIN if player_position == 0 else GameOutcome.LOSS
            else:
                continue
            
            # Calculate new ELO
            new_elo = self.elo_system.calculate_new_rating(
                current_elo, opponent_elo, outcome, games_played=games_played
            )
            
            current_elo = new_elo
            peak_elo = max(peak_elo, current_elo)
            games_played += 1
            
            # Add to history
            if game.start_time:
                elo_history.append((game.start_time, current_elo))
        
        stats.current_elo = current_elo
        stats.peak_elo = peak_elo
        stats.elo_history = elo_history
    
    async def _calculate_performance_metrics(
        self, 
        stats: AccuratePlayerStatistics, 
        games: List[GameRecord], 
        player_id: str
    ):
        """Calculate performance metrics like average game length and duration."""
        total_moves = 0
        total_duration = 0.0
        games_with_duration = 0
        
        for game in games:
            # Count moves (approximate for this player)
            if game.total_moves > 0:
                # Assume roughly equal moves per player
                player_moves = game.total_moves // 2
                total_moves += player_moves
            
            # Calculate duration
            if game.start_time and game.end_time:
                duration_minutes = (game.end_time - game.start_time).total_seconds() / 60.0
                total_duration += duration_minutes
                games_with_duration += 1
        
        stats.total_moves = total_moves
        
        if games_with_duration > 0:
            stats.average_game_duration = total_duration / games_with_duration
    
    async def _calculate_recent_performance(
        self, 
        stats: AccuratePlayerStatistics, 
        games: List[GameRecord], 
        player_id: str
    ):
        """Calculate recent performance and streaks."""
        # Sort games by start time (most recent first)
        completed_games = [g for g in games if g.is_completed and g.outcome and g.start_time]
        sorted_games = sorted(completed_games, key=lambda x: x.start_time, reverse=True)
        
        # Get last 10 games
        recent_games = sorted_games[:10]
        recent_results = []
        
        for game in recent_games:
            # Find player position
            player_position = None
            for position, player_info in game.players.items():
                if player_info.player_id == player_id:
                    player_position = position
                    break
            
            if player_position is None:
                continue
            
            # Determine result
            result = game.outcome.result
            if result == GameResult.DRAW:
                recent_results.append("D")
            elif result == GameResult.WHITE_WINS:
                recent_results.append("W" if player_position == 1 else "L")
            elif result == GameResult.BLACK_WINS:
                recent_results.append("W" if player_position == 0 else "L")
        
        stats.recent_games = recent_results
        
        # Calculate current streak
        if recent_results:
            current_result = recent_results[0]
            current_streak = 1
            
            for result in recent_results[1:]:
                if result == current_result:
                    current_streak += 1
                else:
                    break
            
            stats.current_streak = current_streak
            stats.streak_type = {"W": "win", "L": "loss", "D": "draw"}.get(current_result, "none")
        
        # Calculate longest win streak
        longest_win_streak = 0
        current_win_streak = 0
        
        # Reverse to go chronologically
        for result in reversed(recent_results):
            if result == "W":
                current_win_streak += 1
                longest_win_streak = max(longest_win_streak, current_win_streak)
            else:
                current_win_streak = 0
        
        stats.longest_win_streak = longest_win_streak
    
    async def _calculate_opponent_analysis(
        self, 
        stats: AccuratePlayerStatistics, 
        games: List[GameRecord], 
        player_id: str
    ):
        """Calculate opponent analysis metrics."""
        opponent_elos = []
        
        for game in games:
            if not game.is_completed:
                continue
            
            # Find opponent info
            for position, player_info in game.players.items():
                if player_info.player_id != player_id:
                    opponent_elo = getattr(player_info, 'elo_rating', None)
                    if opponent_elo:
                        opponent_elos.append(opponent_elo)
                    break
        
        if opponent_elos:
            stats.average_opponent_elo = sum(opponent_elos) / len(opponent_elos)
            stats.strongest_opponent_elo = max(opponent_elos)
            stats.weakest_opponent_elo = min(opponent_elos)
        else:
            stats.average_opponent_elo = self.elo_system.default_rating
            stats.strongest_opponent_elo = self.elo_system.default_rating
            stats.weakest_opponent_elo = self.elo_system.default_rating
    
    async def generate_accurate_leaderboard(
        self,
        sort_by: str = "elo_rating",
        min_games: int = 5,
        limit: int = 100,
        use_cache: bool = True
    ) -> List[LeaderboardEntry]:
        """
        Generate an accurate leaderboard with proper statistics and caching.
        
        Args:
            sort_by: Sorting criteria ("elo_rating", "win_rate", "games_played")
            min_games: Minimum games required to be included
            limit: Maximum number of entries to return
            use_cache: Whether to use cached results if available
            
        Returns:
            List of leaderboard entries
        """
        # Create cache key
        cache_key_parts = ["leaderboard", sort_by, min_games, limit]
        
        if use_cache:
            # Try to get from cache first
            cached_leaderboard = self.cache.get(
                cache_key_parts,
                dependencies=["leaderboard"]
            )
            
            if cached_leaderboard is not None:
                self.logger.debug(f"Retrieved cached leaderboard (sort_by={sort_by}, limit={limit})")
                return cached_leaderboard
        
        try:
            # Calculate leaderboard (not cached or cache miss)
            leaderboard_entries = await self._generate_leaderboard_uncached(sort_by, min_games, limit)
            
            if leaderboard_entries and use_cache:
                # Cache the results with longer TTL for leaderboards
                self.cache.set(
                    cache_key_parts,
                    leaderboard_entries,
                    ttl=600.0,  # 10 minutes
                    dependencies=["leaderboard"]
                )
                self.logger.debug(f"Cached leaderboard (sort_by={sort_by}, limit={limit})")
            
            return leaderboard_entries
            
        except Exception as e:
            self.logger.error(f"Failed to generate leaderboard: {e}")
            return []

    async def _generate_leaderboard_uncached(
        self,
        sort_by: str = "elo_rating",
        min_games: int = 5,
        limit: int = 100
    ) -> List[LeaderboardEntry]:
        """
        Generate an accurate leaderboard with proper statistics (uncached version).
        
        Args:
            sort_by: Sorting criteria ("elo_rating", "win_rate", "games_played")
            min_games: Minimum games required to be included
            limit: Maximum number of entries to return
            
        Returns:
            List of leaderboard entries
        """
        # Get all unique players
        all_games = await self.query_engine.storage_manager.query_games({})
        player_ids = set()
        
        for game in all_games:
            for player_info in game.players.values():
                player_ids.add(player_info.player_id)
        
        # Calculate statistics for each player (using cache for individual players)
        leaderboard_entries = []
        
        for player_id in player_ids:
            stats = await self.calculate_player_statistics(player_id, use_cache=True)
            
            if not stats or stats.completed_games < min_games:
                continue
            
            # Calculate ranking score based on sort criteria
            if sort_by == "elo_rating":
                ranking_score = stats.current_elo
            elif sort_by == "win_rate":
                ranking_score = stats.win_rate
            elif sort_by == "games_played":
                ranking_score = stats.completed_games
            else:
                ranking_score = stats.current_elo
            
            entry = LeaderboardEntry(
                rank=0,  # Will be set after sorting
                player_id=player_id,
                model_name=stats.model_name,
                model_provider=stats.model_provider,
                statistics=stats,
                ranking_score=ranking_score
            )
            
            leaderboard_entries.append(entry)
        
        # Sort by ranking score (descending)
        leaderboard_entries.sort(key=lambda x: x.ranking_score, reverse=True)
        
        # Assign ranks and limit results
        for i, entry in enumerate(leaderboard_entries[:limit]):
            entry.rank = i + 1
        
        self.logger.info(f"Generated leaderboard with {len(leaderboard_entries[:limit])} entries, "
                       f"sorted by {sort_by}")
        
        return leaderboard_entries[:limit]

    def invalidate_player_cache(self, player_id: str) -> int:
        """
        Invalidate cache entries for a specific player.
        
        Args:
            player_id: ID of the player whose cache should be invalidated
            
        Returns:
            Number of cache entries invalidated
        """
        return self.cache.invalidate(f"player:{player_id}")

    def invalidate_leaderboard_cache(self) -> int:
        """
        Invalidate all leaderboard cache entries.
        
        Returns:
            Number of cache entries invalidated
        """
        return self.cache.invalidate("leaderboard")

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache performance statistics.
        
        Returns:
            Dictionary containing cache statistics
        """
        return self.cache.get_stats()