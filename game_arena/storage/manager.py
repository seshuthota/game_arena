"""
Storage Manager for the Game Arena storage system.

This module provides the main StorageManager class that coordinates
data operations across different storage backends with transaction
handling, error recovery, and data validation.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, AsyncGenerator
from uuid import uuid4

from .backends.base import StorageBackend
from .models import GameRecord, MoveRecord, PlayerStats, GameOutcome
from .config import StorageConfig
from .exceptions import (
    StorageError,
    ValidationError,
    TransactionError,
    GameNotFoundError,
    DuplicateGameError,
)


logger = logging.getLogger(__name__)


class StorageManager:
    """
    Main storage manager that provides high-level operations for game data.
    
    Handles transaction management, error recovery, data validation,
    and coordinates operations across storage backends.
    """
    
    def __init__(self, backend: StorageBackend, config: StorageConfig):
        """Initialize the storage manager."""
        self.backend = backend
        self.config = config
        self._transaction_lock = asyncio.Lock()
        self._active_transactions: Dict[str, Any] = {}
        
        # Setup logging
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.logger.setLevel(getattr(logging, config.log_level.value))
    
    async def initialize(self) -> None:
        """Initialize the storage manager and backend."""
        try:
            await self.backend.connect()
            await self.backend.initialize_schema()
            self.logger.info("Storage manager initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize storage manager: {e}")
            raise StorageError(f"Storage initialization failed: {e}") from e
    
    async def shutdown(self) -> None:
        """Shutdown the storage manager and close connections."""
        try:
            # Wait for any active transactions to complete
            if self._active_transactions:
                self.logger.warning(f"Waiting for {len(self._active_transactions)} active transactions")
                await asyncio.sleep(1)  # Give transactions time to complete
            
            await self.backend.disconnect()
            self.logger.info("Storage manager shutdown complete")
        except Exception as e:
            self.logger.error(f"Error during storage manager shutdown: {e}")
            raise StorageError(f"Storage shutdown failed: {e}") from e
    
    @asynccontextmanager
    async def transaction(self) -> AsyncGenerator[str, None]:
        """
        Create a transaction context for atomic operations.
        
        Returns:
            Transaction ID for tracking
        """
        transaction_id = str(uuid4())
        
        async with self._transaction_lock:
            try:
                self._active_transactions[transaction_id] = {
                    'start_time': datetime.now(),
                    'operations': []
                }
                self.logger.debug(f"Started transaction {transaction_id}")
                yield transaction_id
                
                # Transaction completed successfully
                self.logger.debug(f"Committed transaction {transaction_id}")
                
            except Exception as e:
                self.logger.error(f"Transaction {transaction_id} failed: {e}")
                # Attempt rollback if backend supports it
                try:
                    await self._rollback_transaction(transaction_id)
                except Exception as rollback_error:
                    self.logger.error(f"Rollback failed for transaction {transaction_id}: {rollback_error}")
                raise TransactionError(f"Transaction failed: {e}") from e
            
            finally:
                # Clean up transaction tracking
                self._active_transactions.pop(transaction_id, None)
    
    async def _rollback_transaction(self, transaction_id: str) -> None:
        """Attempt to rollback a failed transaction."""
        # This is a placeholder for transaction rollback logic
        # Actual implementation would depend on backend capabilities
        self.logger.warning(f"Rollback requested for transaction {transaction_id}")
    
    def _validate_game_data(self, game: GameRecord) -> None:
        """
        Validate game data before storage operations.
        
        Args:
            game: Game record to validate
            
        Raises:
            ValidationError: If validation fails
        """
        if not self.config.enable_data_validation:
            return
        
        try:
            # Basic validation is handled by the dataclass __post_init__
            # Additional business logic validation here
            
            if game.end_time and game.start_time and game.end_time < game.start_time:
                raise ValidationError("Game end time cannot be before start time")
            
            if game.outcome and not game.end_time:
                raise ValidationError("Game with outcome must have end time")
            
            if game.total_moves < 0:
                raise ValidationError("Total moves cannot be negative")
            
            # Validate player information
            for player_id, player_info in game.players.items():
                if not player_info.player_id:
                    raise ValidationError(f"Player {player_id} missing player_id")
                if not player_info.model_name:
                    raise ValidationError(f"Player {player_id} missing model_name")
            
            self.logger.debug(f"Game data validation passed for game {game.game_id}")
            
        except Exception as e:
            self.logger.error(f"Game data validation failed: {e}")
            raise ValidationError(f"Game validation failed: {e}") from e
    
    def _validate_move_data(self, move: MoveRecord) -> None:
        """
        Validate move data before storage operations.
        
        Args:
            move: Move record to validate
            
        Raises:
            ValidationError: If validation fails
        """
        if not self.config.enable_data_validation:
            return
        
        try:
            # Basic validation is handled by the dataclass __post_init__
            # Additional business logic validation here
            
            if move.thinking_time_ms < 0:
                raise ValidationError("Thinking time cannot be negative")
            
            if move.parsing_attempts < 1:
                raise ValidationError("Must have at least one parsing attempt")
            
            if move.rethink_attempts:
                for i, attempt in enumerate(move.rethink_attempts):
                    if attempt.attempt_number != i + 1:
                        raise ValidationError(f"Rethink attempt {i} has incorrect attempt number")
            
            self.logger.debug(f"Move data validation passed for move {move.move_number} in game {move.game_id}")
            
        except Exception as e:
            self.logger.error(f"Move data validation failed: {e}")
            raise ValidationError(f"Move validation failed: {e}") from e
    
    # Game Operations
    
    async def create_game(self, game: GameRecord) -> str:
        """
        Create a new game record.
        
        Args:
            game: Game record to create
            
        Returns:
            Game ID of the created game
            
        Raises:
            ValidationError: If game data is invalid
            DuplicateGameError: If game ID already exists
            StorageError: If storage operation fails
        """
        try:
            self._validate_game_data(game)
            
            # Check if game already exists
            existing_game = await self.backend.get_game(game.game_id)
            if existing_game:
                raise DuplicateGameError(f"Game {game.game_id} already exists")
            
            game_id = await self.backend.create_game(game)
            self.logger.info(f"Created game {game_id}")
            return game_id
                
        except (ValidationError, DuplicateGameError):
            raise
        except Exception as e:
            self.logger.error(f"Failed to create game {game.game_id}: {e}")
            raise StorageError(f"Game creation failed: {e}") from e
    
    async def get_game(self, game_id: str) -> GameRecord:
        """
        Retrieve a game record by ID.
        
        Args:
            game_id: ID of the game to retrieve
            
        Returns:
            Game record
            
        Raises:
            GameNotFoundError: If game doesn't exist
            StorageError: If storage operation fails
        """
        try:
            game = await self.backend.get_game(game_id)
            if not game:
                raise GameNotFoundError(f"Game {game_id} not found")
            
            self.logger.debug(f"Retrieved game {game_id}")
            return game
            
        except GameNotFoundError:
            raise
        except Exception as e:
            self.logger.error(f"Failed to retrieve game {game_id}: {e}")
            raise StorageError(f"Game retrieval failed: {e}") from e
    
    async def update_game(self, game_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update a game record with new data.
        
        Args:
            game_id: ID of the game to update
            updates: Dictionary of fields to update
            
        Returns:
            True if update was successful
            
        Raises:
            GameNotFoundError: If game doesn't exist
            ValidationError: If update data is invalid
            StorageError: If storage operation fails
        """
        try:
            # Verify game exists
            existing_game = await self.get_game(game_id)
            
            # Validate updates
            if self.config.enable_data_validation:
                self._validate_game_updates(updates)
            
            success = await self.backend.update_game(game_id, updates)
            if success:
                self.logger.info(f"Updated game {game_id}")
            else:
                raise StorageError(f"Backend reported update failure for game {game_id}")
            return success
                
        except (GameNotFoundError, ValidationError):
            raise
        except Exception as e:
            self.logger.error(f"Failed to update game {game_id}: {e}")
            raise StorageError(f"Game update failed: {e}") from e
    
    def _validate_game_updates(self, updates: Dict[str, Any]) -> None:
        """Validate game update data."""
        # Validate specific update fields
        if 'end_time' in updates and 'start_time' in updates:
            if updates['end_time'] < updates['start_time']:
                raise ValidationError("End time cannot be before start time")
        
        if 'total_moves' in updates and updates['total_moves'] < 0:
            raise ValidationError("Total moves cannot be negative")
        
        if 'outcome' in updates and updates['outcome'] is not None:
            if not isinstance(updates['outcome'], GameOutcome):
                raise ValidationError("Outcome must be a GameOutcome instance")
    
    async def complete_game(self, game_id: str, outcome: GameOutcome, 
                           final_fen: str, total_moves: int) -> bool:
        """
        Mark a game as completed with final outcome and update player statistics.
        
        Args:
            game_id: ID of the game to complete
            outcome: Final game outcome
            final_fen: Final board position in FEN notation
            total_moves: Total number of moves played
            
        Returns:
            True if completion was successful
            
        Raises:
            GameNotFoundError: If game doesn't exist
            ValidationError: If completion data is invalid
            StorageError: If storage operation fails
        """
        try:
            # Get existing game to calculate duration
            game = await self.get_game(game_id)
            
            end_time = datetime.now()
            duration_seconds = (end_time - game.start_time).total_seconds()
            
            updates = {
                'end_time': end_time,
                'outcome': outcome,
                'final_fen': final_fen,
                'total_moves': total_moves,
                'game_duration_seconds': duration_seconds
            }
            
            async with self.transaction() as transaction_id:
                # Update game record
                success = await self.update_game(game_id, updates)
                if not success:
                    raise StorageError(f"Failed to update game {game_id}")
                
                # Get updated game record for player stats update
                completed_game = await self.get_game(game_id)
                
                # Update ELO ratings for both players (Requirement 4.1)
                try:
                    new_ratings = await self.update_elo_ratings(completed_game)
                    self.logger.info(f"Updated ELO ratings for game {game_id}: {new_ratings}")
                except Exception as e:
                    self.logger.error(f"Failed to update ELO ratings for game {game_id}: {e}")
                    # Continue even if ELO update fails
                
                # Update comprehensive player statistics (Requirements 4.1, 4.2)
                for player_info in completed_game.players.values():
                    try:
                        await self.calculate_and_update_player_stats(player_info.player_id)
                    except Exception as e:
                        self.logger.error(f"Failed to update stats for player {player_info.player_id}: {e}")
                        # Continue even if individual player stats update fails
                
                self.logger.info(f"Completed game {game_id} with outcome {outcome.result.value} "
                               f"and updated player statistics")
                
                return success
            
        except Exception as e:
            self.logger.error(f"Failed to complete game {game_id}: {e}")
            raise StorageError(f"Game completion failed: {e}") from e
    
    async def delete_game(self, game_id: str) -> bool:
        """
        Delete a game record and all associated data.
        
        Args:
            game_id: ID of the game to delete
            
        Returns:
            True if deletion was successful
            
        Raises:
            GameNotFoundError: If game doesn't exist
            StorageError: If storage operation fails
        """
        try:
            # Verify game exists
            await self.get_game(game_id)
            
            success = await self.backend.delete_game(game_id)
            if success:
                self.logger.info(f"Deleted game {game_id}")
            else:
                raise StorageError(f"Backend reported deletion failure for game {game_id}")
            return success
                
        except GameNotFoundError:
            raise
        except Exception as e:
            self.logger.error(f"Failed to delete game {game_id}: {e}")
            raise StorageError(f"Game deletion failed: {e}") from e
    
    async def query_games(self, filters: Dict[str, Any], limit: Optional[int] = None,
                         offset: Optional[int] = None) -> List[GameRecord]:
        """
        Query games with filters.
        
        Args:
            filters: Dictionary of filter criteria
            limit: Maximum number of results to return
            offset: Number of results to skip
            
        Returns:
            List of matching game records
            
        Raises:
            StorageError: If query operation fails
        """
        try:
            games = await self.backend.query_games(filters, limit, offset)
            self.logger.debug(f"Queried games with filters {filters}, returned {len(games)} results")
            return games
            
        except Exception as e:
            self.logger.error(f"Failed to query games: {e}")
            raise StorageError(f"Game query failed: {e}") from e
    
    async def count_games(self, filters: Dict[str, Any]) -> int:
        """
        Count games matching filters.
        
        Args:
            filters: Dictionary of filter criteria
            
        Returns:
            Number of matching games
            
        Raises:
            StorageError: If count operation fails
        """
        try:
            count = await self.backend.count_games(filters)
            self.logger.debug(f"Counted {count} games with filters {filters}")
            return count
            
        except Exception as e:
            self.logger.error(f"Failed to count games: {e}")
            raise StorageError(f"Game count failed: {e}") from e
    
    # Move Operations
    
    async def add_move(self, move: MoveRecord) -> bool:
        """
        Add a move record to the database.
        
        Args:
            move: Move record to add
            
        Returns:
            True if move was added successfully
            
        Raises:
            ValidationError: If move data is invalid
            StorageError: If storage operation fails
        """
        try:
            self._validate_move_data(move)
            
            success = await self.backend.add_move(move)
            if success:
                self.logger.info(f"Added move {move.move_number} for game {move.game_id}")
            else:
                raise StorageError(f"Backend reported failure adding move {move.move_number} for game {move.game_id}")
            return success
                
        except ValidationError:
            raise
        except Exception as e:
            self.logger.error(f"Failed to add move {move.move_number} for game {move.game_id}: {e}")
            raise StorageError(f"Move addition failed: {e}") from e
    
    async def add_moves_batch(self, moves: List[MoveRecord]) -> int:
        """
        Add multiple move records in a batch operation for performance.
        
        Args:
            moves: List of move records to add
            
        Returns:
            Number of moves successfully added
            
        Raises:
            ValidationError: If any move data is invalid
            StorageError: If storage operation fails
        """
        if not moves:
            return 0
        
        try:
            # Validate all moves first
            for move in moves:
                self._validate_move_data(move)
            
            async with self.transaction() as transaction_id:
                success_count = 0
                
                for move in moves:
                    try:
                        success = await self.backend.add_move(move)
                        if success:
                            success_count += 1
                        else:
                            self.logger.warning(f"Failed to add move {move.move_number} for game {move.game_id}")
                    except Exception as e:
                        self.logger.error(f"Error adding move {move.move_number} for game {move.game_id}: {e}")
                        # Continue with other moves in batch
                
                self.logger.info(f"Added {success_count}/{len(moves)} moves in batch transaction {transaction_id}")
                return success_count
                
        except ValidationError:
            raise
        except Exception as e:
            self.logger.error(f"Failed to add moves batch: {e}")
            raise StorageError(f"Batch move addition failed: {e}") from e
    
    async def get_moves(self, game_id: str, limit: Optional[int] = None) -> List[MoveRecord]:
        """
        Get all moves for a game.
        
        Args:
            game_id: ID of the game to get moves for
            limit: Maximum number of moves to return
            
        Returns:
            List of move records ordered by move number and player
            
        Raises:
            StorageError: If storage operation fails
        """
        try:
            moves = await self.backend.get_moves(game_id, limit)
            self.logger.debug(f"Retrieved {len(moves)} moves for game {game_id}")
            return moves
            
        except Exception as e:
            self.logger.error(f"Failed to get moves for game {game_id}: {e}")
            raise StorageError(f"Move retrieval failed: {e}") from e
    
    async def get_move(self, game_id: str, move_number: int, player: int) -> Optional[MoveRecord]:
        """
        Get a specific move record.
        
        Args:
            game_id: ID of the game
            move_number: Move number (1-based)
            player: Player index (0 for black, 1 for white)
            
        Returns:
            Move record if found, None otherwise
            
        Raises:
            StorageError: If storage operation fails
        """
        try:
            move = await self.backend.get_move(game_id, move_number, player)
            if move:
                self.logger.debug(f"Retrieved move {move_number} by player {player} for game {game_id}")
            else:
                self.logger.debug(f"Move {move_number} by player {player} not found for game {game_id}")
            return move
            
        except Exception as e:
            self.logger.error(f"Failed to get move {move_number} by player {player} for game {game_id}: {e}")
            raise StorageError(f"Move retrieval failed: {e}") from e
    
    async def get_moves_with_filters(self, game_id: str, filters: Dict[str, Any]) -> List[MoveRecord]:
        """
        Get moves for a game with additional filtering.
        
        Args:
            game_id: ID of the game
            filters: Dictionary of filter criteria
                - is_legal: Filter by move legality (bool)
                - parsing_success: Filter by parsing success (bool)
                - has_rethink: Filter moves that had rethink attempts (bool)
                - blunder_flag: Filter moves marked as blunders (bool)
                - min_thinking_time: Minimum thinking time in ms (int)
                - max_thinking_time: Maximum thinking time in ms (int)
                - player: Filter by player (0 or 1)
            
        Returns:
            List of filtered move records
            
        Raises:
            StorageError: If storage operation fails
        """
        try:
            # Get all moves first
            all_moves = await self.get_moves(game_id)
            
            # Apply filters
            filtered_moves = []
            for move in all_moves:
                if self._move_matches_filters(move, filters):
                    filtered_moves.append(move)
            
            self.logger.debug(f"Filtered {len(all_moves)} moves to {len(filtered_moves)} for game {game_id}")
            return filtered_moves
            
        except Exception as e:
            self.logger.error(f"Failed to get filtered moves for game {game_id}: {e}")
            raise StorageError(f"Filtered move retrieval failed: {e}") from e
    
    def _move_matches_filters(self, move: MoveRecord, filters: Dict[str, Any]) -> bool:
        """Check if a move matches the given filters."""
        for key, value in filters.items():
            if key == 'is_legal' and move.is_legal != value:
                return False
            elif key == 'parsing_success' and move.parsing_success != value:
                return False
            elif key == 'has_rethink' and move.had_rethink != value:
                return False
            elif key == 'blunder_flag' and move.blunder_flag != value:
                return False
            elif key == 'min_thinking_time' and move.thinking_time_ms < value:
                return False
            elif key == 'max_thinking_time' and move.thinking_time_ms > value:
                return False
            elif key == 'player' and move.player != value:
                return False
        return True
    
    async def get_move_statistics(self, game_id: str) -> Dict[str, Any]:
        """
        Get statistics about moves in a game.
        
        Args:
            game_id: ID of the game
            
        Returns:
            Dictionary containing move statistics
            
        Raises:
            StorageError: If storage operation fails
        """
        try:
            moves = await self.get_moves(game_id)
            
            if not moves:
                return {
                    'total_moves': 0,
                    'legal_moves': 0,
                    'illegal_moves': 0,
                    'parsing_failures': 0,
                    'rethink_attempts': 0,
                    'blunders': 0,
                    'average_thinking_time_ms': 0.0,
                    'total_game_time_ms': 0
                }
            
            stats = {
                'total_moves': len(moves),
                'legal_moves': sum(1 for m in moves if m.is_legal),
                'illegal_moves': sum(1 for m in moves if not m.is_legal),
                'parsing_failures': sum(1 for m in moves if not m.parsing_success),
                'rethink_attempts': sum(len(m.rethink_attempts) for m in moves),
                'blunders': sum(1 for m in moves if m.blunder_flag),
                'average_thinking_time_ms': sum(m.thinking_time_ms for m in moves) / len(moves),
                'total_game_time_ms': sum(m.total_time_ms for m in moves)
            }
            
            # Add per-player statistics
            player_stats = {}
            for player in [0, 1]:
                player_moves = [m for m in moves if m.player == player]
                if player_moves:
                    player_stats[f'player_{player}'] = {
                        'moves': len(player_moves),
                        'legal_moves': sum(1 for m in player_moves if m.is_legal),
                        'illegal_moves': sum(1 for m in player_moves if not m.is_legal),
                        'average_thinking_time_ms': sum(m.thinking_time_ms for m in player_moves) / len(player_moves),
                        'blunders': sum(1 for m in player_moves if m.blunder_flag)
                    }
            
            stats.update(player_stats)
            
            self.logger.debug(f"Calculated move statistics for game {game_id}")
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to get move statistics for game {game_id}: {e}")
            raise StorageError(f"Move statistics calculation failed: {e}") from e
    
    async def add_rethink_attempt(self, game_id: str, move_number: int, 
                                 player: int, rethink_attempt: 'RethinkAttempt') -> bool:
        """
        Add a rethink attempt to an existing move record.
        
        Args:
            game_id: ID of the game
            move_number: Move number the rethink attempt is for
            player: Player making the rethink attempt
            rethink_attempt: RethinkAttempt record to add
            
        Returns:
            True if rethink attempt was added successfully
            
        Raises:
            ValidationError: If rethink attempt data is invalid
            StorageError: If storage operation fails
        """
        try:
            # Validate rethink attempt data
            if not rethink_attempt.prompt_text:
                raise ValidationError("Rethink attempt prompt_text cannot be empty")
            if not rethink_attempt.raw_response:
                raise ValidationError("Rethink attempt raw_response cannot be empty")
            if rethink_attempt.attempt_number < 1:
                raise ValidationError("Rethink attempt number must be positive")
            
            # Get the existing move record
            move = await self.get_move(game_id, move_number, player)
            if not move:
                # If move doesn't exist yet, we'll store the rethink attempt for later association
                # This can happen if rethink attempts are captured before the final move is recorded
                self.logger.warning(
                    f"Move {move_number} by player {player} not found for game {game_id}, "
                    f"storing rethink attempt for later association"
                )
                # For now, we'll use the backend's rethink storage if available
                success = await self.backend.add_rethink_attempt(
                    game_id, move_number, player, rethink_attempt
                )
            else:
                # Add to existing move's rethink attempts
                move.rethink_attempts.append(rethink_attempt)
                # Update the move record
                success = await self.backend.update_move(move)
            
            if success:
                self.logger.info(
                    f"Added rethink attempt {rethink_attempt.attempt_number} "
                    f"for move {move_number} by player {player} in game {game_id}"
                )
            else:
                raise StorageError(
                    f"Backend reported failure adding rethink attempt for "
                    f"move {move_number} by player {player} in game {game_id}"
                )
            
            return success
                
        except ValidationError:
            raise
        except Exception as e:
            self.logger.error(
                f"Failed to add rethink attempt for move {move_number} "
                f"by player {player} in game {game_id}: {e}"
            )
            raise StorageError(f"Rethink attempt addition failed: {e}") from e

    async def validate_move_integrity(self, game_id: str) -> Dict[str, Any]:
        """
        Validate the integrity of move data for a game.
        
        Args:
            game_id: ID of the game to validate
            
        Returns:
            Dictionary containing validation results
            
        Raises:
            StorageError: If storage operation fails
        """
        try:
            moves = await self.get_moves(game_id)
            game = await self.get_game(game_id)
            
            validation_results = {
                'is_valid': True,
                'errors': [],
                'warnings': [],
                'move_count': len(moves),
                'expected_moves': game.total_moves if game else None
            }
            
            if not moves:
                validation_results['warnings'].append("No moves found for game")
                return validation_results
            
            # Check move sequence integrity
            expected_move_number = 1
            for i, move in enumerate(moves):
                # Check move number sequence
                if move.move_number != expected_move_number:
                    validation_results['errors'].append(
                        f"Move {i}: Expected move number {expected_move_number}, got {move.move_number}"
                    )
                    validation_results['is_valid'] = False
                
                # Check player alternation (simplified - assumes standard chess)
                expected_player = (expected_move_number - 1) % 2
                if move.player != expected_player:
                    validation_results['errors'].append(
                        f"Move {i}: Expected player {expected_player}, got {move.player}"
                    )
                    validation_results['is_valid'] = False
                
                # Check FEN consistency (basic validation)
                if not move.fen_before or not move.fen_after:
                    validation_results['errors'].append(
                        f"Move {i}: Missing FEN data"
                    )
                    validation_results['is_valid'] = False
                
                # Check for required fields
                if not move.move_san or not move.move_uci:
                    validation_results['errors'].append(
                        f"Move {i}: Missing move notation"
                    )
                    validation_results['is_valid'] = False
                
                # Check rethink attempt consistency
                for j, attempt in enumerate(move.rethink_attempts):
                    if attempt.attempt_number != j + 1:
                        validation_results['warnings'].append(
                            f"Move {i}: Rethink attempt {j} has incorrect attempt number"
                        )
                
                expected_move_number += 1
            
            # Check total move count consistency
            if game and len(moves) != game.total_moves:
                validation_results['warnings'].append(
                    f"Move count mismatch: found {len(moves)}, expected {game.total_moves}"
                )
            
            self.logger.debug(f"Validated move integrity for game {game_id}: {validation_results['is_valid']}")
            return validation_results
            
        except Exception as e:
            self.logger.error(f"Failed to validate move integrity for game {game_id}: {e}")
            raise StorageError(f"Move integrity validation failed: {e}") from e
    
    # Player Statistics Operations
    
    async def update_player_stats(self, player_id: str, stats: PlayerStats) -> bool:
        """
        Update player statistics.
        
        Args:
            player_id: ID of the player to update
            stats: Updated player statistics
            
        Returns:
            True if update was successful
            
        Raises:
            ValidationError: If stats data is invalid
            StorageError: If storage operation fails
        """
        try:
            # Validate stats data
            if self.config.enable_data_validation:
                self._validate_player_stats(stats)
            
            success = await self.backend.update_player_stats(player_id, stats)
            if success:
                self.logger.info(f"Updated player stats for {player_id}")
            else:
                raise StorageError(f"Backend reported failure updating stats for player {player_id}")
            return success
                
        except ValidationError:
            raise
        except Exception as e:
            self.logger.error(f"Failed to update player stats for {player_id}: {e}")
            raise StorageError(f"Player stats update failed: {e}") from e
    
    def _validate_player_stats(self, stats: PlayerStats) -> None:
        """Validate player statistics data."""
        if not stats.player_id:
            raise ValidationError("Player ID cannot be empty")
        if stats.games_played < 0:
            raise ValidationError("Games played cannot be negative")
        if stats.wins < 0 or stats.losses < 0 or stats.draws < 0:
            raise ValidationError("Win/loss/draw counts cannot be negative")
        if stats.wins + stats.losses + stats.draws > stats.games_played:
            raise ValidationError("Sum of outcomes cannot exceed games played")
        if not 0.0 <= stats.illegal_move_rate <= 1.0:
            raise ValidationError("Illegal move rate must be between 0 and 1")
        if stats.average_thinking_time < 0:
            raise ValidationError("Average thinking time cannot be negative")
        if stats.elo_rating < 0:
            raise ValidationError("ELO rating cannot be negative")
    
    async def get_player_stats(self, player_id: str) -> Optional[PlayerStats]:
        """
        Get player statistics.
        
        Args:
            player_id: ID of the player to get stats for
            
        Returns:
            Player statistics if found, None otherwise
            
        Raises:
            StorageError: If storage operation fails
        """
        try:
            stats = await self.backend.get_player_stats(player_id)
            if stats:
                self.logger.debug(f"Retrieved player stats for {player_id}")
            else:
                self.logger.debug(f"No stats found for player {player_id}")
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to get player stats for {player_id}: {e}")
            raise StorageError(f"Player stats retrieval failed: {e}") from e
    
    async def calculate_and_update_player_stats(self, player_id: str) -> PlayerStats:
        """
        Calculate comprehensive player statistics from game and move data.
        
        Args:
            player_id: ID of the player to calculate stats for
            
        Returns:
            Updated player statistics
            
        Raises:
            StorageError: If calculation or storage operation fails
        """
        try:
            # Get all games for this player
            games = await self.query_games({'player_id': player_id})
            
            if not games:
                # Create default stats for new player
                stats = PlayerStats(
                    player_id=player_id,
                    games_played=0,
                    wins=0,
                    losses=0,
                    draws=0,
                    illegal_move_rate=0.0,
                    average_thinking_time=0.0,
                    elo_rating=1200.0,  # Default ELO
                    last_updated=datetime.now()
                )
                await self.update_player_stats(player_id, stats)
                return stats
            
            # Calculate basic game statistics
            wins = 0
            losses = 0
            draws = 0
            completed_games = 0
            
            for game in games:
                if game.is_completed and game.outcome:
                    completed_games += 1
                    # Determine player color and outcome
                    player_color = None
                    for color, player_info in game.players.items():
                        if player_info.player_id == player_id:
                            player_color = color
                            break
                    
                    if player_color is not None:
                        if game.outcome.winner == player_color:
                            wins += 1
                        elif game.outcome.winner is None:
                            draws += 1
                        else:
                            losses += 1
            
            # Calculate move-based statistics
            total_moves = 0
            illegal_moves = 0
            total_thinking_time = 0
            
            for game in games:
                moves = await self.get_moves(game.game_id)
                player_moves = [m for m in moves if self._is_player_move(m, player_id, game)]
                
                for move in player_moves:
                    total_moves += 1
                    if not move.is_legal:
                        illegal_moves += 1
                    total_thinking_time += move.thinking_time_ms
            
            # Calculate rates and averages
            illegal_move_rate = illegal_moves / total_moves if total_moves > 0 else 0.0
            average_thinking_time = total_thinking_time / total_moves if total_moves > 0 else 0.0
            
            # Get current ELO rating (preserve existing rating if available)
            current_stats = await self.get_player_stats(player_id)
            current_elo = current_stats.elo_rating if current_stats else 1200.0
            
            # Create updated stats
            stats = PlayerStats(
                player_id=player_id,
                games_played=completed_games,
                wins=wins,
                losses=losses,
                draws=draws,
                illegal_move_rate=illegal_move_rate,
                average_thinking_time=average_thinking_time,
                elo_rating=current_elo,
                last_updated=datetime.now()
            )
            
            # Update in database
            await self.update_player_stats(player_id, stats)
            
            self.logger.info(f"Calculated and updated stats for player {player_id}: "
                           f"{wins}W-{losses}L-{draws}D, ELO: {current_elo:.0f}")
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to calculate player stats for {player_id}: {e}")
            raise StorageError(f"Player stats calculation failed: {e}") from e
    
    def _is_player_move(self, move: MoveRecord, player_id: str, game: GameRecord) -> bool:
        """Check if a move belongs to the specified player."""
        player_info = game.players.get(move.player)
        return player_info is not None and player_info.player_id == player_id
    
    async def update_elo_ratings(self, game: GameRecord) -> Dict[str, float]:
        """
        Update ELO ratings for players after a completed game.
        
        Args:
            game: Completed game record
            
        Returns:
            Dictionary mapping player IDs to their new ELO ratings
            
        Raises:
            StorageError: If ELO calculation or update fails
        """
        try:
            if not game.is_completed or not game.outcome:
                raise ValueError("Game must be completed to update ELO ratings")
            
            # Get current player stats
            player_ids = [info.player_id for info in game.players.values()]
            current_stats = {}
            
            for player_id in player_ids:
                stats = await self.get_player_stats(player_id)
                if not stats:
                    # Create default stats for new player
                    stats = PlayerStats(
                        player_id=player_id,
                        elo_rating=1200.0,
                        last_updated=datetime.now()
                    )
                    await self.update_player_stats(player_id, stats)
                current_stats[player_id] = stats
            
            # Calculate ELO changes
            black_player_id = game.players[0].player_id
            white_player_id = game.players[1].player_id
            
            black_elo = current_stats[black_player_id].elo_rating
            white_elo = current_stats[white_player_id].elo_rating
            
            # Determine game result from black's perspective
            if game.outcome.winner == 0:  # Black wins
                black_score = 1.0
                white_score = 0.0
            elif game.outcome.winner == 1:  # White wins
                black_score = 0.0
                white_score = 1.0
            else:  # Draw
                black_score = 0.5
                white_score = 0.5
            
            # Calculate new ELO ratings
            new_black_elo, new_white_elo = self._calculate_elo_change(
                black_elo, white_elo, black_score, white_score
            )
            
            # Update player stats with new ELO ratings
            new_ratings = {}
            
            # Update black player
            black_stats = current_stats[black_player_id]
            black_stats.elo_rating = new_black_elo
            black_stats.last_updated = datetime.now()
            await self.update_player_stats(black_player_id, black_stats)
            new_ratings[black_player_id] = new_black_elo
            
            # Update white player
            white_stats = current_stats[white_player_id]
            white_stats.elo_rating = new_white_elo
            white_stats.last_updated = datetime.now()
            await self.update_player_stats(white_player_id, white_stats)
            new_ratings[white_player_id] = new_white_elo
            
            self.logger.info(f"Updated ELO ratings for game {game.game_id}: "
                           f"{black_player_id}: {black_elo:.0f} -> {new_black_elo:.0f}, "
                           f"{white_player_id}: {white_elo:.0f} -> {new_white_elo:.0f}")
            
            return new_ratings
            
        except Exception as e:
            self.logger.error(f"Failed to update ELO ratings for game {game.game_id}: {e}")
            raise StorageError(f"ELO rating update failed: {e}") from e
    
    def _calculate_elo_change(self, rating_a: float, rating_b: float, 
                             score_a: float, score_b: float, k_factor: int = 32) -> tuple[float, float]:
        """
        Calculate new ELO ratings using the standard ELO formula.
        
        Args:
            rating_a: Current ELO rating of player A
            rating_b: Current ELO rating of player B
            score_a: Score for player A (1.0 = win, 0.5 = draw, 0.0 = loss)
            score_b: Score for player B (1.0 = win, 0.5 = draw, 0.0 = loss)
            k_factor: K-factor for ELO calculation (default 32)
            
        Returns:
            Tuple of (new_rating_a, new_rating_b)
        """
        # Calculate expected scores
        expected_a = 1 / (1 + 10 ** ((rating_b - rating_a) / 400))
        expected_b = 1 / (1 + 10 ** ((rating_a - rating_b) / 400))
        
        # Calculate new ratings
        new_rating_a = rating_a + k_factor * (score_a - expected_a)
        new_rating_b = rating_b + k_factor * (score_b - expected_b)
        
        return new_rating_a, new_rating_b
    
    async def get_head_to_head_stats(self, player1_id: str, player2_id: str) -> Dict[str, Any]:
        """
        Get head-to-head statistics between two players.
        
        Args:
            player1_id: ID of the first player
            player2_id: ID of the second player
            
        Returns:
            Dictionary containing head-to-head statistics
            
        Raises:
            StorageError: If query operation fails
        """
        try:
            # Query games between these two players
            games = await self.query_games({
                'players': [player1_id, player2_id]
            })
            
            # Filter to only games with both players
            h2h_games = []
            for game in games:
                player_ids = [info.player_id for info in game.players.values()]
                if player1_id in player_ids and player2_id in player_ids:
                    h2h_games.append(game)
            
            if not h2h_games:
                return {
                    'total_games': 0,
                    'player1_wins': 0,
                    'player2_wins': 0,
                    'draws': 0,
                    'player1_win_rate': 0.0,
                    'player2_win_rate': 0.0,
                    'draw_rate': 0.0,
                    'games': []
                }
            
            # Calculate statistics
            player1_wins = 0
            player2_wins = 0
            draws = 0
            
            game_summaries = []
            
            for game in h2h_games:
                if not game.is_completed or not game.outcome:
                    continue
                
                # Determine which player is which color
                player1_color = None
                player2_color = None
                
                for color, player_info in game.players.items():
                    if player_info.player_id == player1_id:
                        player1_color = color
                    elif player_info.player_id == player2_id:
                        player2_color = color
                
                # Count outcomes
                if game.outcome.winner == player1_color:
                    player1_wins += 1
                elif game.outcome.winner == player2_color:
                    player2_wins += 1
                else:
                    draws += 1
                
                # Add game summary
                game_summaries.append({
                    'game_id': game.game_id,
                    'date': game.start_time.isoformat(),
                    'result': game.outcome.result.value,
                    'winner': game.outcome.winner,
                    'player1_color': player1_color,
                    'player2_color': player2_color,
                    'total_moves': game.total_moves,
                    'duration_minutes': game.duration_minutes
                })
            
            total_completed = player1_wins + player2_wins + draws
            
            stats = {
                'total_games': len(h2h_games),
                'completed_games': total_completed,
                'player1_wins': player1_wins,
                'player2_wins': player2_wins,
                'draws': draws,
                'player1_win_rate': player1_wins / total_completed if total_completed > 0 else 0.0,
                'player2_win_rate': player2_wins / total_completed if total_completed > 0 else 0.0,
                'draw_rate': draws / total_completed if total_completed > 0 else 0.0,
                'games': game_summaries
            }
            
            self.logger.debug(f"Calculated head-to-head stats between {player1_id} and {player2_id}: "
                            f"{player1_wins}-{player2_wins}-{draws}")
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to get head-to-head stats between {player1_id} and {player2_id}: {e}")
            raise StorageError(f"Head-to-head stats calculation failed: {e}") from e
    
    async def get_player_performance_trends(self, player_id: str, 
                                          days: int = 30) -> Dict[str, Any]:
        """
        Get player performance trends over a specified time period.
        
        Args:
            player_id: ID of the player
            days: Number of days to analyze (default 30)
            
        Returns:
            Dictionary containing performance trend data
            
        Raises:
            StorageError: If query operation fails
        """
        try:
            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            # Get games in date range
            games = await self.query_games({
                'player_id': player_id,
                'start_date': start_date,
                'end_date': end_date
            })
            
            if not games:
                return {
                    'period_days': days,
                    'total_games': 0,
                    'wins': 0,
                    'losses': 0,
                    'draws': 0,
                    'win_rate': 0.0,
                    'average_game_length': 0.0,
                    'elo_change': 0.0,
                    'daily_performance': []
                }
            
            # Group games by day
            daily_games = {}
            for game in games:
                if game.is_completed:
                    day_key = game.start_time.date().isoformat()
                    if day_key not in daily_games:
                        daily_games[day_key] = []
                    daily_games[day_key].append(game)
            
            # Calculate daily performance
            daily_performance = []
            total_wins = 0
            total_losses = 0
            total_draws = 0
            total_game_length = 0
            completed_games = 0
            
            for day, day_games in sorted(daily_games.items()):
                day_wins = 0
                day_losses = 0
                day_draws = 0
                day_game_length = 0
                
                for game in day_games:
                    if game.outcome:
                        completed_games += 1
                        
                        # Determine player color and outcome
                        player_color = None
                        for color, player_info in game.players.items():
                            if player_info.player_id == player_id:
                                player_color = color
                                break
                        
                        if player_color is not None:
                            if game.outcome.winner == player_color:
                                day_wins += 1
                                total_wins += 1
                            elif game.outcome.winner is None:
                                day_draws += 1
                                total_draws += 1
                            else:
                                day_losses += 1
                                total_losses += 1
                        
                        if game.duration_minutes:
                            day_game_length += game.duration_minutes
                            total_game_length += game.duration_minutes
                
                daily_performance.append({
                    'date': day,
                    'games': len(day_games),
                    'wins': day_wins,
                    'losses': day_losses,
                    'draws': day_draws,
                    'win_rate': day_wins / len(day_games) if day_games else 0.0,
                    'average_game_length': day_game_length / len(day_games) if day_games else 0.0
                })
            
            # Calculate ELO change over period
            elo_change = 0.0
            if len(games) >= 2:
                # Get ELO from first and last game (simplified)
                first_game = min(games, key=lambda g: g.start_time)
                last_game = max(games, key=lambda g: g.start_time)
                
                # This is a simplified calculation - in practice you'd track ELO history
                current_stats = await self.get_player_stats(player_id)
                if current_stats:
                    # Estimate ELO change based on win rate vs expected
                    expected_win_rate = 0.5  # Simplified assumption
                    actual_win_rate = total_wins / completed_games if completed_games > 0 else 0.0
                    elo_change = (actual_win_rate - expected_win_rate) * 100  # Rough estimate
            
            trends = {
                'period_days': days,
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'total_games': len(games),
                'completed_games': completed_games,
                'wins': total_wins,
                'losses': total_losses,
                'draws': total_draws,
                'win_rate': total_wins / completed_games if completed_games > 0 else 0.0,
                'average_game_length': total_game_length / completed_games if completed_games > 0 else 0.0,
                'elo_change': elo_change,
                'daily_performance': daily_performance
            }
            
            self.logger.debug(f"Calculated performance trends for player {player_id} over {days} days")
            
            return trends
            
        except Exception as e:
            self.logger.error(f"Failed to get performance trends for player {player_id}: {e}")
            raise StorageError(f"Performance trends calculation failed: {e}") from e
    
    async def update_all_player_stats(self) -> Dict[str, PlayerStats]:
        """
        Update statistics for all players in the system.
        
        Returns:
            Dictionary mapping player IDs to their updated statistics
            
        Raises:
            StorageError: If update operation fails
        """
        try:
            # Get all unique player IDs from games
            all_games = await self.query_games({})
            player_ids = set()
            
            for game in all_games:
                for player_info in game.players.values():
                    player_ids.add(player_info.player_id)
            
            updated_stats = {}
            
            async with self.transaction() as transaction_id:
                for player_id in player_ids:
                    try:
                        stats = await self.calculate_and_update_player_stats(player_id)
                        updated_stats[player_id] = stats
                    except Exception as e:
                        self.logger.error(f"Failed to update stats for player {player_id}: {e}")
                        # Continue with other players
            
            self.logger.info(f"Updated stats for {len(updated_stats)}/{len(player_ids)} players")
            
            return updated_stats
            
        except Exception as e:
            self.logger.error(f"Failed to update all player stats: {e}")
            raise StorageError(f"Bulk player stats update failed: {e}") from e

    # Health and Maintenance Operations
    
    async def get_health_status(self) -> Dict[str, Any]:
        """
        Get storage system health status.
        
        Returns:
            Dictionary containing health metrics
        """
        try:
            backend_stats = await self.backend.get_storage_stats()
            
            health_status = {
                'status': 'healthy',
                'backend_connected': self.backend.is_connected,
                'active_transactions': len(self._active_transactions),
                'backend_stats': backend_stats,
                'timestamp': datetime.now().isoformat()
            }
            
            # Check for any warning conditions
            if len(self._active_transactions) > 10:
                health_status['warnings'] = ['High number of active transactions']
            
            if not self.backend.is_connected:
                health_status['status'] = 'unhealthy'
                health_status['errors'] = ['Backend not connected']
            
            return health_status
            
        except Exception as e:
            self.logger.error(f"Failed to get health status: {e}")
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    async def cleanup_old_data(self, older_than: datetime) -> int:
        """
        Clean up data older than specified date.
        
        Args:
            older_than: Delete data older than this date
            
        Returns:
            Number of records cleaned up
            
        Raises:
            StorageError: If cleanup operation fails
        """
        try:
            cleaned_count = await self.backend.cleanup_old_data(older_than)
            self.logger.info(f"Cleaned up {cleaned_count} old records")
            return cleaned_count
                
        except Exception as e:
            self.logger.error(f"Failed to cleanup old data: {e}")
            raise StorageError(f"Data cleanup failed: {e}") from e