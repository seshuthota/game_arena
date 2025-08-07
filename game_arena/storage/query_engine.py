"""
Query Engine for the Game Arena storage system.

This module provides high-level query interface for data analysis and reporting,
implementing filtering, search, and analytics capabilities for game data.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass

from .models import GameRecord, MoveRecord, PlayerStats, GameResult, TerminationReason
from .manager import StorageManager
from .exceptions import StorageError, ValidationError


logger = logging.getLogger(__name__)


@dataclass
class GameFilters:
    """Filters for game queries."""
    # Player filters
    player_ids: Optional[List[str]] = None
    player1_id: Optional[str] = None  # Specific player 1 (white)
    player2_id: Optional[str] = None  # Specific player 2 (black)
    model_names: Optional[List[str]] = None
    model_providers: Optional[List[str]] = None
    agent_types: Optional[List[str]] = None
    
    # Time filters
    start_time_after: Optional[datetime] = None
    start_time_before: Optional[datetime] = None
    end_time_after: Optional[datetime] = None
    end_time_before: Optional[datetime] = None
    
    # Game outcome filters
    results: Optional[List[GameResult]] = None
    winners: Optional[List[int]] = None  # 0, 1, or None for draws
    termination_reasons: Optional[List[TerminationReason]] = None
    
    # Tournament filters
    tournament_ids: Optional[List[str]] = None
    
    # Game characteristics
    min_moves: Optional[int] = None
    max_moves: Optional[int] = None
    min_duration_minutes: Optional[float] = None
    max_duration_minutes: Optional[float] = None
    
    # Status filters
    completed_only: bool = True
    ongoing_only: bool = False


@dataclass
class MoveFilters:
    """Filters for move queries."""
    # Basic filters
    is_legal: Optional[bool] = None
    parsing_success: Optional[bool] = None
    has_rethink: Optional[bool] = None
    blunder_flag: Optional[bool] = None
    
    # Player filters
    player: Optional[int] = None  # 0 or 1
    
    # Timing filters
    min_thinking_time_ms: Optional[int] = None
    max_thinking_time_ms: Optional[int] = None
    min_api_time_ms: Optional[int] = None
    max_api_time_ms: Optional[int] = None
    
    # Move range filters
    min_move_number: Optional[int] = None
    max_move_number: Optional[int] = None
    
    # Quality filters
    min_quality_score: Optional[float] = None
    max_quality_score: Optional[float] = None


class QueryEngine:
    """
    High-level query interface for game data analysis and reporting.
    
    Provides methods for filtering games and moves, calculating statistics,
    and generating reports based on various criteria.
    """
    
    def __init__(self, storage_manager: StorageManager):
        """Initialize the query engine."""
        self.storage_manager = storage_manager
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    # Basic Game Queries (Requirement 3.1)
    
    async def get_games_by_players(self, player1: str, player2: str = None) -> List[GameRecord]:
        """
        Get games involving specific players.
        
        Args:
            player1: First player ID (required)
            player2: Second player ID (optional, if None returns all games with player1)
            
        Returns:
            List of matching game records
            
        Raises:
            StorageError: If query operation fails
        """
        try:
            if player2:
                # Head-to-head games between two specific players
                filters = {
                    'players': [player1, player2]
                }
                self.logger.debug(f"Querying head-to-head games between {player1} and {player2}")
            else:
                # All games involving player1
                filters = {
                    'player_ids': [player1]
                }
                self.logger.debug(f"Querying all games involving {player1}")
            
            games = await self.storage_manager.query_games(filters)
            
            # Additional filtering for head-to-head if needed
            if player2:
                filtered_games = []
                for game in games:
                    player_ids = [info.player_id for info in game.players.values()]
                    if player1 in player_ids and player2 in player_ids:
                        filtered_games.append(game)
                games = filtered_games
            
            self.logger.info(f"Found {len(games)} games for players query")
            return games
            
        except Exception as e:
            self.logger.error(f"Failed to query games by players: {e}")
            raise StorageError(f"Player games query failed: {e}") from e
    
    async def get_games_by_date_range(self, start_date: datetime, 
                                     end_date: datetime = None) -> List[GameRecord]:
        """
        Get games within a specific date range.
        
        Args:
            start_date: Start of date range (inclusive)
            end_date: End of date range (inclusive), defaults to now
            
        Returns:
            List of matching game records
            
        Raises:
            StorageError: If query operation fails
            ValidationError: If date range is invalid
        """
        try:
            if end_date is None:
                end_date = datetime.now()
            
            if start_date > end_date:
                raise ValidationError("Start date cannot be after end date")
            
            filters = {
                'start_time_after': start_date,
                'start_time_before': end_date
            }
            
            games = await self.storage_manager.query_games(filters)
            
            self.logger.info(f"Found {len(games)} games between {start_date} and {end_date}")
            return games
            
        except ValidationError:
            raise
        except Exception as e:
            self.logger.error(f"Failed to query games by date range: {e}")
            raise StorageError(f"Date range games query failed: {e}") from e
    
    async def get_games_by_outcome(self, outcome: Union[GameResult, List[GameResult]]) -> List[GameRecord]:
        """
        Get games with specific outcomes.
        
        Args:
            outcome: Game result(s) to filter by
            
        Returns:
            List of matching game records
            
        Raises:
            StorageError: If query operation fails
        """
        try:
            if isinstance(outcome, GameResult):
                outcomes = [outcome]
            else:
                outcomes = outcome
            
            filters = {
                'results': outcomes,
                'completed_only': True
            }
            
            games = await self.storage_manager.query_games(filters)
            
            # Additional filtering by outcome since backend might not support this directly
            filtered_games = []
            for game in games:
                if game.outcome and game.outcome.result in outcomes:
                    filtered_games.append(game)
            
            self.logger.info(f"Found {len(filtered_games)} games with outcomes {[o.value for o in outcomes]}")
            return filtered_games
            
        except Exception as e:
            self.logger.error(f"Failed to query games by outcome: {e}")
            raise StorageError(f"Outcome games query failed: {e}") from e
    
    async def get_games_by_tournament(self, tournament_id: str) -> List[GameRecord]:
        """
        Get all games from a specific tournament.
        
        Args:
            tournament_id: Tournament identifier
            
        Returns:
            List of matching game records
            
        Raises:
            StorageError: If query operation fails
        """
        try:
            filters = {
                'tournament_id': tournament_id
            }
            
            games = await self.storage_manager.query_games(filters)
            
            self.logger.info(f"Found {len(games)} games for tournament {tournament_id}")
            return games
            
        except Exception as e:
            self.logger.error(f"Failed to query games by tournament: {e}")
            raise StorageError(f"Tournament games query failed: {e}") from e
    
    # Advanced Game Queries (Requirement 3.2)
    
    async def query_games_advanced(self, filters: GameFilters, 
                                  limit: Optional[int] = None,
                                  offset: Optional[int] = None) -> List[GameRecord]:
        """
        Query games with advanced filtering options.
        
        Args:
            filters: GameFilters object with query criteria
            limit: Maximum number of results to return
            offset: Number of results to skip
            
        Returns:
            List of matching game records
            
        Raises:
            StorageError: If query operation fails
            ValidationError: If filters are invalid
        """
        try:
            # Convert GameFilters to backend filter format
            backend_filters = self._convert_game_filters(filters)
            
            games = await self.storage_manager.query_games(backend_filters, limit, offset)
            
            # Apply additional filtering that backend might not support
            filtered_games = self._apply_additional_game_filters(games, filters)
            
            self.logger.info(f"Advanced query returned {len(filtered_games)} games")
            return filtered_games
            
        except ValidationError:
            raise
        except Exception as e:
            self.logger.error(f"Failed to execute advanced games query: {e}")
            raise StorageError(f"Advanced games query failed: {e}") from e
    
    def _convert_game_filters(self, filters: GameFilters) -> Dict[str, Any]:
        """Convert GameFilters to backend filter format."""
        backend_filters = {}
        
        # Player filters
        if filters.player_ids:
            backend_filters['player_ids'] = filters.player_ids
        if filters.model_names:
            backend_filters['model_names'] = filters.model_names
        if filters.model_providers:
            backend_filters['model_providers'] = filters.model_providers
        if filters.agent_types:
            backend_filters['agent_types'] = filters.agent_types
        
        # Time filters
        if filters.start_time_after:
            backend_filters['start_time_after'] = filters.start_time_after
        if filters.start_time_before:
            backend_filters['start_time_before'] = filters.start_time_before
        if filters.end_time_after:
            backend_filters['end_time_after'] = filters.end_time_after
        if filters.end_time_before:
            backend_filters['end_time_before'] = filters.end_time_before
        
        # Tournament filters
        if filters.tournament_ids:
            backend_filters['tournament_ids'] = filters.tournament_ids
        
        # Status filters
        if filters.completed_only:
            backend_filters['completed_only'] = True
        if filters.ongoing_only:
            backend_filters['ongoing_only'] = True
        
        return backend_filters
    
    def _apply_additional_game_filters(self, games: List[GameRecord], 
                                     filters: GameFilters) -> List[GameRecord]:
        """Apply filters that the backend might not support directly."""
        filtered_games = []
        
        for game in games:
            if self._game_matches_filters(game, filters):
                filtered_games.append(game)
        
        return filtered_games
    
    def _game_matches_filters(self, game: GameRecord, filters: GameFilters) -> bool:
        """Check if a game matches the given filters."""
        # Specific player position filters
        if filters.player1_id:
            white_player = game.players.get(1)
            if not white_player or white_player.player_id != filters.player1_id:
                return False
        
        if filters.player2_id:
            black_player = game.players.get(0)
            if not black_player or black_player.player_id != filters.player2_id:
                return False
        
        # Outcome filters - only check if game has outcome
        if filters.results:
            if not game.outcome:
                return False
            if game.outcome.result not in filters.results:
                return False
        
        if filters.winners is not None:
            if not game.outcome:
                return False
            if game.outcome.winner not in filters.winners:
                return False
        
        if filters.termination_reasons:
            if not game.outcome:
                return False
            if game.outcome.termination not in filters.termination_reasons:
                return False
        
        # Game characteristics
        if filters.min_moves is not None and game.total_moves < filters.min_moves:
            return False
        
        if filters.max_moves is not None and game.total_moves > filters.max_moves:
            return False
        
        if filters.min_duration_minutes is not None and game.duration_minutes:
            if game.duration_minutes < filters.min_duration_minutes:
                return False
        
        if filters.max_duration_minutes is not None and game.duration_minutes:
            if game.duration_minutes > filters.max_duration_minutes:
                return False
        
        return True
    
    async def count_games_advanced(self, filters: GameFilters) -> int:
        """
        Count games matching advanced filters.
        
        Args:
            filters: GameFilters object with query criteria
            
        Returns:
            Number of matching games
            
        Raises:
            StorageError: If count operation fails
        """
        try:
            # For accurate count with complex filters, we need to query and count
            # This could be optimized in the backend for better performance
            games = await self.query_games_advanced(filters)
            count = len(games)
            
            self.logger.debug(f"Counted {count} games matching advanced filters")
            return count
            
        except Exception as e:
            self.logger.error(f"Failed to count games with advanced filters: {e}")
            raise StorageError(f"Advanced games count failed: {e}") from e
    
    # Move Queries
    
    async def get_moves_with_filters(self, game_id: str, filters: MoveFilters) -> List[MoveRecord]:
        """
        Get moves for a game with filtering.
        
        Args:
            game_id: ID of the game
            filters: MoveFilters object with query criteria
            
        Returns:
            List of filtered move records
            
        Raises:
            StorageError: If query operation fails
        """
        try:
            # Convert MoveFilters to backend filter format
            backend_filters = self._convert_move_filters(filters)
            
            moves = await self.storage_manager.get_moves_with_filters(game_id, backend_filters)
            
            # Apply additional filtering
            filtered_moves = self._apply_additional_move_filters(moves, filters)
            
            self.logger.debug(f"Move query returned {len(filtered_moves)} moves for game {game_id}")
            return filtered_moves
            
        except Exception as e:
            self.logger.error(f"Failed to query moves with filters for game {game_id}: {e}")
            raise StorageError(f"Move query failed: {e}") from e
    
    def _convert_move_filters(self, filters: MoveFilters) -> Dict[str, Any]:
        """Convert MoveFilters to backend filter format."""
        backend_filters = {}
        
        if filters.is_legal is not None:
            backend_filters['is_legal'] = filters.is_legal
        if filters.parsing_success is not None:
            backend_filters['parsing_success'] = filters.parsing_success
        if filters.has_rethink is not None:
            backend_filters['has_rethink'] = filters.has_rethink
        if filters.blunder_flag is not None:
            backend_filters['blunder_flag'] = filters.blunder_flag
        if filters.player is not None:
            backend_filters['player'] = filters.player
        if filters.min_thinking_time_ms is not None:
            backend_filters['min_thinking_time'] = filters.min_thinking_time_ms
        if filters.max_thinking_time_ms is not None:
            backend_filters['max_thinking_time'] = filters.max_thinking_time_ms
        
        return backend_filters
    
    def _apply_additional_move_filters(self, moves: List[MoveRecord], 
                                     filters: MoveFilters) -> List[MoveRecord]:
        """Apply filters that the backend might not support directly."""
        filtered_moves = []
        
        for move in moves:
            if self._move_matches_all_filters(move, filters):
                filtered_moves.append(move)
        
        return filtered_moves
    
    def _move_matches_all_filters(self, move: MoveRecord, filters: MoveFilters) -> bool:
        """Check if a move matches all filters (both basic and advanced)."""
        # Basic filters (these might be handled by backend, but we apply them here too for completeness)
        if filters.is_legal is not None and move.is_legal != filters.is_legal:
            return False
        if filters.parsing_success is not None and move.parsing_success != filters.parsing_success:
            return False
        if filters.has_rethink is not None and move.had_rethink != filters.has_rethink:
            return False
        if filters.blunder_flag is not None and move.blunder_flag != filters.blunder_flag:
            return False
        if filters.player is not None and move.player != filters.player:
            return False
        if filters.min_thinking_time_ms is not None and move.thinking_time_ms < filters.min_thinking_time_ms:
            return False
        if filters.max_thinking_time_ms is not None and move.thinking_time_ms > filters.max_thinking_time_ms:
            return False
        
        # Advanced filters
        return self._move_matches_advanced_filters(move, filters)
    
    def _move_matches_advanced_filters(self, move: MoveRecord, filters: MoveFilters) -> bool:
        """Check if a move matches advanced filters."""
        # API timing filters
        if filters.min_api_time_ms is not None and move.api_call_time_ms < filters.min_api_time_ms:
            return False
        if filters.max_api_time_ms is not None and move.api_call_time_ms > filters.max_api_time_ms:
            return False
        
        # Move range filters
        if filters.min_move_number is not None and move.move_number < filters.min_move_number:
            return False
        if filters.max_move_number is not None and move.move_number > filters.max_move_number:
            return False
        
        # Quality filters - only check if move has quality score
        if filters.min_quality_score is not None:
            if move.move_quality_score is None:
                return False
            if move.move_quality_score < filters.min_quality_score:
                return False
        if filters.max_quality_score is not None:
            if move.move_quality_score is None:
                return False
            if move.move_quality_score > filters.max_quality_score:
                return False
        
        return True
    
    # Utility Methods
    
    async def search_games(self, search_term: str, search_fields: List[str] = None) -> List[GameRecord]:
        """
        Search games by text in specified fields.
        
        Args:
            search_term: Text to search for
            search_fields: Fields to search in (defaults to player names and tournament ID)
            
        Returns:
            List of matching game records
            
        Raises:
            StorageError: If search operation fails
        """
        try:
            if search_fields is None:
                search_fields = ['player_names', 'tournament_id']
            
            # Get all games and filter by search term
            # This is a simple implementation - could be optimized with database text search
            all_games = await self.storage_manager.query_games({})
            
            matching_games = []
            search_term_lower = search_term.lower()
            
            for game in all_games:
                if self._game_matches_search(game, search_term_lower, search_fields):
                    matching_games.append(game)
            
            self.logger.info(f"Search for '{search_term}' returned {len(matching_games)} games")
            return matching_games
            
        except Exception as e:
            self.logger.error(f"Failed to search games: {e}")
            raise StorageError(f"Game search failed: {e}") from e
    
    def _game_matches_search(self, game: GameRecord, search_term: str, 
                           search_fields: List[str]) -> bool:
        """Check if a game matches the search term in specified fields."""
        for field in search_fields:
            if field == 'player_names':
                for player_info in game.players.values():
                    if (search_term in player_info.player_id.lower() or
                        search_term in player_info.model_name.lower()):
                        return True
            elif field == 'tournament_id' and game.tournament_id:
                if search_term in game.tournament_id.lower():
                    return True
            elif field == 'game_id':
                if search_term in game.game_id.lower():
                    return True
        
        return False
    
    async def get_recent_games(self, hours: int = 24, limit: int = 100) -> List[GameRecord]:
        """
        Get recent games within the specified time window.
        
        Args:
            hours: Number of hours to look back (default 24)
            limit: Maximum number of games to return
            
        Returns:
            List of recent game records, ordered by start time (newest first)
            
        Raises:
            StorageError: If query operation fails
        """
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            
            filters = {
                'start_time_after': cutoff_time
            }
            
            games = await self.storage_manager.query_games(filters, limit=limit)
            
            # Sort by start time, newest first
            games.sort(key=lambda g: g.start_time, reverse=True)
            
            self.logger.info(f"Found {len(games)} recent games in last {hours} hours")
            return games
            
        except Exception as e:
            self.logger.error(f"Failed to get recent games: {e}")
            raise StorageError(f"Recent games query failed: {e}") from e
    
    # Performance Analytics (Requirement 3.3, 4.2, 4.3)
    
    async def get_player_winrate(self, player_id: str, opponent: str = None) -> float:
        """
        Calculate win rate for a player, optionally against a specific opponent.
        
        Args:
            player_id: ID of the player to calculate win rate for
            opponent: Optional opponent ID for head-to-head win rate
            
        Returns:
            Win rate as a percentage (0.0 to 100.0)
            
        Raises:
            StorageError: If calculation fails
        """
        try:
            if opponent:
                games = await self.get_games_by_players(player_id, opponent)
                self.logger.debug(f"Calculating head-to-head win rate for {player_id} vs {opponent}")
            else:
                games = await self.get_games_by_players(player_id)
                self.logger.debug(f"Calculating overall win rate for {player_id}")
            
            if not games:
                return 0.0
            
            # Only count completed games
            completed_games = [g for g in games if g.is_completed]
            if not completed_games:
                return 0.0
            
            wins = 0
            for game in completed_games:
                if game.outcome and game.outcome.winner is not None:
                    # Find which player position this player_id is in
                    for position, player_info in game.players.items():
                        if player_info.player_id == player_id:
                            if game.outcome.winner == position:
                                wins += 1
                            break
            
            win_rate = (wins / len(completed_games)) * 100.0
            self.logger.info(f"Win rate for {player_id}: {win_rate:.2f}% ({wins}/{len(completed_games)})")
            return win_rate
            
        except Exception as e:
            self.logger.error(f"Failed to calculate win rate for {player_id}: {e}")
            raise StorageError(f"Win rate calculation failed: {e}") from e
    
    async def get_move_accuracy_stats(self, player_id: str) -> 'MoveAccuracyStats':
        """
        Calculate move accuracy statistics for a player.
        
        Args:
            player_id: ID of the player to analyze
            
        Returns:
            MoveAccuracyStats object with detailed accuracy metrics
            
        Raises:
            StorageError: If calculation fails
        """
        try:
            # Get all games for this player
            games = await self.get_games_by_players(player_id)
            
            total_moves = 0
            legal_moves = 0
            illegal_moves = 0
            parsing_failures = 0
            total_rethink_attempts = 0
            blunders = 0
            
            for game in games:
                try:
                    # Get moves for this game
                    all_moves = await self.storage_manager.get_moves(game.game_id)
                    
                    # Filter moves by this player
                    player_moves = []
                    for move in all_moves:
                        # Find which position this player is in for this game
                        for position, player_info in game.players.items():
                            if player_info.player_id == player_id and move.player == position:
                                player_moves.append(move)
                                break
                    
                    # Analyze moves
                    for move in player_moves:
                        total_moves += 1
                        
                        if move.is_legal:
                            legal_moves += 1
                        else:
                            illegal_moves += 1
                        
                        if not move.parsing_success:
                            parsing_failures += 1
                        
                        total_rethink_attempts += len(move.rethink_attempts)
                        
                        if move.blunder_flag:
                            blunders += 1
                            
                except Exception as e:
                    self.logger.warning(f"Failed to analyze moves for game {game.game_id}: {e}")
                    continue
            
            from .models import MoveAccuracyStats
            stats = MoveAccuracyStats(
                total_moves=total_moves,
                legal_moves=legal_moves,
                illegal_moves=illegal_moves,
                parsing_failures=parsing_failures,
                total_rethink_attempts=total_rethink_attempts,
                blunders=blunders
            )
            
            self.logger.info(f"Move accuracy stats for {player_id}: "
                           f"{stats.accuracy_percentage:.1f}% accuracy, "
                           f"{stats.parsing_success_rate:.1f}% parsing success")
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to calculate move accuracy stats for {player_id}: {e}")
            raise StorageError(f"Move accuracy calculation failed: {e}") from e
    
    async def get_illegal_move_rate(self, player_id: str) -> float:
        """
        Calculate the illegal move rate for a player.
        
        Args:
            player_id: ID of the player to analyze
            
        Returns:
            Illegal move rate as a percentage (0.0 to 100.0)
            
        Raises:
            StorageError: If calculation fails
        """
        try:
            stats = await self.get_move_accuracy_stats(player_id)
            
            if stats.total_moves == 0:
                return 0.0
            
            illegal_rate = (stats.illegal_moves / stats.total_moves) * 100.0
            self.logger.info(f"Illegal move rate for {player_id}: {illegal_rate:.2f}%")
            return illegal_rate
            
        except Exception as e:
            self.logger.error(f"Failed to calculate illegal move rate for {player_id}: {e}")
            raise StorageError(f"Illegal move rate calculation failed: {e}") from e
    
    async def get_player_comparison(self, player1_id: str, player2_id: str) -> Dict[str, Any]:
        """
        Compare performance statistics between two players.
        
        Args:
            player1_id: ID of the first player
            player2_id: ID of the second player
            
        Returns:
            Dictionary containing comparison metrics
            
        Raises:
            StorageError: If comparison calculation fails
        """
        try:
            # Get individual stats for both players
            player1_stats = await self.get_move_accuracy_stats(player1_id)
            player2_stats = await self.get_move_accuracy_stats(player2_id)
            
            # Get win rates
            player1_winrate = await self.get_player_winrate(player1_id)
            player2_winrate = await self.get_player_winrate(player2_id)
            
            # Get head-to-head record
            h2h_games = await self.get_games_by_players(player1_id, player2_id)
            completed_h2h = [g for g in h2h_games if g.is_completed]
            
            player1_h2h_wins = 0
            player2_h2h_wins = 0
            h2h_draws = 0
            
            for game in completed_h2h:
                if game.outcome:
                    if game.outcome.winner is None:
                        h2h_draws += 1
                    else:
                        # Find which position each player is in
                        for position, player_info in game.players.items():
                            if player_info.player_id == player1_id and game.outcome.winner == position:
                                player1_h2h_wins += 1
                                break
                            elif player_info.player_id == player2_id and game.outcome.winner == position:
                                player2_h2h_wins += 1
                                break
            
            # Calculate average thinking times
            player1_avg_thinking = await self._get_average_thinking_time(player1_id)
            player2_avg_thinking = await self._get_average_thinking_time(player2_id)
            
            comparison = {
                'player1': {
                    'player_id': player1_id,
                    'win_rate': player1_winrate,
                    'accuracy': player1_stats.accuracy_percentage,
                    'illegal_move_rate': (player1_stats.illegal_moves / max(player1_stats.total_moves, 1)) * 100,
                    'parsing_success_rate': player1_stats.parsing_success_rate,
                    'blunder_rate': player1_stats.blunder_rate,
                    'average_rethink_attempts': player1_stats.average_rethink_attempts,
                    'average_thinking_time_ms': player1_avg_thinking,
                    'total_games': len(await self.get_games_by_players(player1_id)),
                    'total_moves': player1_stats.total_moves
                },
                'player2': {
                    'player_id': player2_id,
                    'win_rate': player2_winrate,
                    'accuracy': player2_stats.accuracy_percentage,
                    'illegal_move_rate': (player2_stats.illegal_moves / max(player2_stats.total_moves, 1)) * 100,
                    'parsing_success_rate': player2_stats.parsing_success_rate,
                    'blunder_rate': player2_stats.blunder_rate,
                    'average_rethink_attempts': player2_stats.average_rethink_attempts,
                    'average_thinking_time_ms': player2_avg_thinking,
                    'total_games': len(await self.get_games_by_players(player2_id)),
                    'total_moves': player2_stats.total_moves
                },
                'head_to_head': {
                    'total_games': len(completed_h2h),
                    'player1_wins': player1_h2h_wins,
                    'player2_wins': player2_h2h_wins,
                    'draws': h2h_draws,
                    'player1_h2h_winrate': (player1_h2h_wins / max(len(completed_h2h), 1)) * 100,
                    'player2_h2h_winrate': (player2_h2h_wins / max(len(completed_h2h), 1)) * 100
                }
            }
            
            self.logger.info(f"Generated comparison between {player1_id} and {player2_id}")
            return comparison
            
        except Exception as e:
            self.logger.error(f"Failed to compare players {player1_id} and {player2_id}: {e}")
            raise StorageError(f"Player comparison failed: {e}") from e
    
    async def _get_average_thinking_time(self, player_id: str) -> float:
        """Calculate average thinking time for a player."""
        try:
            games = await self.get_games_by_players(player_id)
            total_thinking_time = 0
            total_moves = 0
            
            for game in games:
                try:
                    all_moves = await self.storage_manager.get_moves(game.game_id)
                    
                    for move in all_moves:
                        # Find which position this player is in for this game
                        for position, player_info in game.players.items():
                            if player_info.player_id == player_id and move.player == position:
                                total_thinking_time += move.thinking_time_ms
                                total_moves += 1
                                break
                                
                except Exception as e:
                    self.logger.warning(f"Failed to get moves for game {game.game_id}: {e}")
                    continue
            
            if total_moves == 0:
                return 0.0
            
            return total_thinking_time / total_moves
            
        except Exception as e:
            self.logger.warning(f"Failed to calculate average thinking time for {player_id}: {e}")
            return 0.0
    
    async def generate_leaderboard(self, criteria: str = 'win_rate', limit: int = 10) -> List[Dict[str, Any]]:
        """
        Generate a leaderboard of players based on specified criteria.
        
        Args:
            criteria: Ranking criteria ('win_rate', 'accuracy', 'games_played')
            limit: Maximum number of players to include
            
        Returns:
            List of player rankings with statistics
            
        Raises:
            StorageError: If leaderboard generation fails
            ValidationError: If criteria is invalid
        """
        try:
            valid_criteria = ['win_rate', 'accuracy', 'games_played', 'illegal_move_rate']
            if criteria not in valid_criteria:
                raise ValidationError(f"Invalid criteria '{criteria}'. Must be one of: {valid_criteria}")
            
            # Get all unique players from games
            all_games = await self.storage_manager.query_games({})
            player_ids = set()
            
            for game in all_games:
                for player_info in game.players.values():
                    player_ids.add(player_info.player_id)
            
            # Calculate stats for each player
            player_rankings = []
            
            for player_id in player_ids:
                try:
                    # Get basic stats
                    games = await self.get_games_by_players(player_id)
                    completed_games = [g for g in games if g.is_completed]
                    
                    if not completed_games:
                        continue  # Skip players with no completed games
                    
                    win_rate = await self.get_player_winrate(player_id)
                    accuracy_stats = await self.get_move_accuracy_stats(player_id)
                    avg_thinking_time = await self._get_average_thinking_time(player_id)
                    
                    # Calculate wins, losses, draws
                    wins = losses = draws = 0
                    for game in completed_games:
                        if game.outcome:
                            if game.outcome.winner is None:
                                draws += 1
                            else:
                                for position, player_info in game.players.items():
                                    if player_info.player_id == player_id:
                                        if game.outcome.winner == position:
                                            wins += 1
                                        else:
                                            losses += 1
                                        break
                    
                    player_ranking = {
                        'player_id': player_id,
                        'rank': 0,  # Will be set after sorting
                        'win_rate': win_rate,
                        'accuracy': accuracy_stats.accuracy_percentage,
                        'games_played': len(completed_games),
                        'wins': wins,
                        'losses': losses,
                        'draws': draws,
                        'illegal_move_rate': (accuracy_stats.illegal_moves / max(accuracy_stats.total_moves, 1)) * 100,
                        'parsing_success_rate': accuracy_stats.parsing_success_rate,
                        'blunder_rate': accuracy_stats.blunder_rate,
                        'average_rethink_attempts': accuracy_stats.average_rethink_attempts,
                        'average_thinking_time_ms': avg_thinking_time,
                        'total_moves': accuracy_stats.total_moves
                    }
                    
                    player_rankings.append(player_ranking)
                    
                except Exception as e:
                    self.logger.warning(f"Failed to calculate stats for player {player_id}: {e}")
                    continue
            
            # Sort by criteria
            if criteria == 'win_rate':
                player_rankings.sort(key=lambda x: x['win_rate'], reverse=True)
            elif criteria == 'accuracy':
                player_rankings.sort(key=lambda x: x['accuracy'], reverse=True)
            elif criteria == 'games_played':
                player_rankings.sort(key=lambda x: x['games_played'], reverse=True)
            elif criteria == 'illegal_move_rate':
                player_rankings.sort(key=lambda x: x['illegal_move_rate'])  # Lower is better
            
            # Assign ranks and limit results
            for i, ranking in enumerate(player_rankings[:limit]):
                ranking['rank'] = i + 1
            
            leaderboard = player_rankings[:limit]
            
            self.logger.info(f"Generated leaderboard with {len(leaderboard)} players, sorted by {criteria}")
            return leaderboard
            
        except ValidationError:
            raise
        except Exception as e:
            self.logger.error(f"Failed to generate leaderboard: {e}")
            raise StorageError(f"Leaderboard generation failed: {e}") from e
    
    async def get_tournament_summary(self, tournament_id: str) -> Dict[str, Any]:
        """
        Generate a comprehensive summary of a tournament.
        
        Args:
            tournament_id: ID of the tournament to summarize
            
        Returns:
            Dictionary containing tournament statistics and analytics
            
        Raises:
            StorageError: If summary generation fails
        """
        try:
            # Get all games from the tournament
            games = await self.get_games_by_tournament(tournament_id)
            completed_games = [g for g in games if g.is_completed]
            
            if not games:
                return {
                    'tournament_id': tournament_id,
                    'total_games': 0,
                    'completed_games': 0,
                    'error': 'No games found for tournament'
                }
            
            # Basic tournament stats
            total_games = len(games)
            completed_games_count = len(completed_games)
            ongoing_games = total_games - completed_games_count
            
            # Game outcome distribution
            white_wins = black_wins = draws = 0
            termination_counts = {}
            
            for game in completed_games:
                if game.outcome:
                    if game.outcome.result == GameResult.WHITE_WINS:
                        white_wins += 1
                    elif game.outcome.result == GameResult.BLACK_WINS:
                        black_wins += 1
                    elif game.outcome.result == GameResult.DRAW:
                        draws += 1
                    
                    termination = game.outcome.termination.value
                    termination_counts[termination] = termination_counts.get(termination, 0) + 1
            
            # Player participation and performance
            player_stats = {}
            for game in games:
                for player_info in game.players.values():
                    player_id = player_info.player_id
                    if player_id not in player_stats:
                        player_stats[player_id] = {
                            'games_played': 0,
                            'wins': 0,
                            'losses': 0,
                            'draws': 0,
                            'model_name': player_info.model_name,
                            'agent_type': player_info.agent_type
                        }
                    
                    player_stats[player_id]['games_played'] += 1
                    
                    if game.is_completed and game.outcome:
                        if game.outcome.winner is None:
                            player_stats[player_id]['draws'] += 1
                        else:
                            # Find which position this player is in
                            for position, p_info in game.players.items():
                                if p_info.player_id == player_id:
                                    if game.outcome.winner == position:
                                        player_stats[player_id]['wins'] += 1
                                    else:
                                        player_stats[player_id]['losses'] += 1
                                    break
            
            # Calculate average game length and duration
            total_moves = sum(g.total_moves for g in completed_games)
            avg_moves = total_moves / max(completed_games_count, 1)
            
            total_duration = sum(g.game_duration_seconds or 0 for g in completed_games if g.game_duration_seconds)
            games_with_duration = len([g for g in completed_games if g.game_duration_seconds])
            avg_duration_minutes = (total_duration / 60) / max(games_with_duration, 1) if games_with_duration > 0 else 0
            
            # Tournament date range
            start_times = [g.start_time for g in games]
            tournament_start = min(start_times) if start_times else None
            tournament_end = max([g.end_time for g in completed_games if g.end_time]) if completed_games else None
            
            summary = {
                'tournament_id': tournament_id,
                'total_games': total_games,
                'completed_games': completed_games_count,
                'ongoing_games': ongoing_games,
                'completion_rate': (completed_games_count / total_games) * 100 if total_games > 0 else 0,
                
                'outcomes': {
                    'white_wins': white_wins,
                    'black_wins': black_wins,
                    'draws': draws,
                    'white_win_rate': (white_wins / max(completed_games_count, 1)) * 100,
                    'black_win_rate': (black_wins / max(completed_games_count, 1)) * 100,
                    'draw_rate': (draws / max(completed_games_count, 1)) * 100
                },
                
                'terminations': termination_counts,
                
                'game_characteristics': {
                    'average_moves': avg_moves,
                    'total_moves': total_moves,
                    'average_duration_minutes': avg_duration_minutes,
                    'shortest_game_moves': min([g.total_moves for g in completed_games]) if completed_games else 0,
                    'longest_game_moves': max([g.total_moves for g in completed_games]) if completed_games else 0
                },
                
                'timeline': {
                    'tournament_start': tournament_start.isoformat() if tournament_start else None,
                    'tournament_end': tournament_end.isoformat() if tournament_end else None,
                    'duration_hours': ((tournament_end - tournament_start).total_seconds() / 3600) if tournament_start and tournament_end else None
                },
                
                'participants': len(player_stats),
                'player_performance': player_stats
            }
            
            self.logger.info(f"Generated tournament summary for {tournament_id}: "
                           f"{total_games} games, {len(player_stats)} players")
            return summary
            
        except Exception as e:
            self.logger.error(f"Failed to generate tournament summary for {tournament_id}: {e}")
            raise StorageError(f"Tournament summary generation failed: {e}") from e