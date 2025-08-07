"""
Export functionality for the Game Arena storage system.

This module provides export capabilities for game data in various formats
including PGN (Portable Game Notation), JSON, and CSV formats.
Supports both single game and batch export operations.
"""

import csv
import json
import logging
from datetime import datetime
from io import StringIO
from typing import Dict, List, Optional, Any, Union, TextIO
from dataclasses import asdict

from .models import GameRecord, MoveRecord, PlayerStats, GameResult, TerminationReason
from .manager import StorageManager
from .query_engine import QueryEngine, GameFilters
from .exceptions import StorageError, ValidationError


logger = logging.getLogger(__name__)


class GameExporter:
    """
    Handles export of game data in various formats.
    
    Supports PGN, JSON, and CSV export formats with batch processing
    capabilities for large datasets.
    """
    
    def __init__(self, storage_manager: StorageManager, query_engine: QueryEngine):
        """Initialize the game exporter."""
        self.storage_manager = storage_manager
        self.query_engine = query_engine
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    # PGN Export (Requirement 3.4)
    
    async def export_game_pgn(self, game_id: str) -> str:
        """
        Export a single game in PGN format.
        
        Args:
            game_id: ID of the game to export
            
        Returns:
            PGN formatted string
            
        Raises:
            StorageError: If game retrieval fails
            ValidationError: If game data is incomplete
        """
        try:
            # Get game record
            game = await self.storage_manager.get_game(game_id)
            
            # Get moves for the game
            moves = await self.storage_manager.get_moves(game_id)
            
            # Generate PGN
            pgn = self._generate_pgn(game, moves)
            
            self.logger.info(f"Exported game {game_id} to PGN format")
            return pgn
            
        except Exception as e:
            self.logger.error(f"Failed to export game {game_id} to PGN: {e}")
            raise StorageError(f"PGN export failed: {e}") from e
    
    def _generate_pgn(self, game: GameRecord, moves: List[MoveRecord]) -> str:
        """Generate PGN format string from game and moves data."""
        pgn_lines = []
        
        # PGN Header tags
        pgn_lines.append(f'[Event "{game.tournament_id or "Game Arena Match"}"]')
        pgn_lines.append(f'[Site "Game Arena"]')
        pgn_lines.append(f'[Date "{game.start_time.strftime("%Y.%m.%d")}"]')
        pgn_lines.append(f'[Round "-"]')
        
        # Player information
        white_player = game.players.get(1)
        black_player = game.players.get(0)
        
        if white_player:
            pgn_lines.append(f'[White "{white_player.model_name} ({white_player.player_id})"]')
        else:
            pgn_lines.append('[White "Unknown"]')
            
        if black_player:
            pgn_lines.append(f'[Black "{black_player.model_name} ({black_player.player_id})"]')
        else:
            pgn_lines.append('[Black "Unknown"]')
        
        # Game result
        if game.outcome:
            pgn_lines.append(f'[Result "{game.outcome.result.value}"]')
        else:
            pgn_lines.append('[Result "*"]')
        
        # Additional metadata
        if game.initial_fen != "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1":
            pgn_lines.append(f'[FEN "{game.initial_fen}"]')
        
        pgn_lines.append(f'[GameId "{game.game_id}"]')
        
        if game.end_time:
            pgn_lines.append(f'[EndTime "{game.end_time.strftime("%Y.%m.%d %H:%M:%S")}"]')
        
        if game.game_duration_seconds:
            pgn_lines.append(f'[TimeControl "{int(game.game_duration_seconds)}s"]')
        
        if game.outcome and game.outcome.termination:
            pgn_lines.append(f'[Termination "{game.outcome.termination.value}"]')
        
        # Add empty line before moves
        pgn_lines.append('')
        
        # Generate move text
        move_text = self._generate_pgn_moves(moves)
        pgn_lines.append(move_text)
        
        # Add result at the end
        if game.outcome:
            pgn_lines.append(f' {game.outcome.result.value}')
        else:
            pgn_lines.append(' *')
        
        return '\n'.join(pgn_lines)
    
    def _generate_pgn_moves(self, moves: List[MoveRecord]) -> str:
        """Generate PGN move notation from move records."""
        if not moves:
            return ""
        
        # Sort moves by move number and player (white=1 first, then black=0)
        sorted_moves = sorted(moves, key=lambda m: (m.move_number, -m.player))
        
        # Filter out illegal moves
        legal_moves = [move for move in sorted_moves if move.is_legal]
        
        if not legal_moves:
            return ""
        
        move_pairs = []
        current_move_num = 0
        white_move = None
        
        for move in legal_moves:
            if move.move_number != current_move_num:
                # New move number - handle any pending white move
                if white_move is not None:
                    move_pairs.append(f"{current_move_num}. {white_move}")
                    white_move = None
                
                current_move_num = move.move_number
            
            if move.player == 1:  # White
                white_move = move.move_san
            else:  # Black
                if white_move is not None:
                    # We have both white and black moves for this move number
                    move_pairs.append(f"{current_move_num}. {white_move} {move.move_san}")
                    white_move = None
                else:
                    # Black move without white move (shouldn't happen in normal games)
                    move_pairs.append(f"{current_move_num}... {move.move_san}")
        
        # Handle final white move if exists
        if white_move is not None:
            move_pairs.append(f"{current_move_num}. {white_move}")
        
        return ' '.join(move_pairs)
    
    async def export_games_pgn_batch(self, game_ids: List[str]) -> Dict[str, str]:
        """
        Export multiple games in PGN format.
        
        Args:
            game_ids: List of game IDs to export
            
        Returns:
            Dictionary mapping game IDs to PGN strings
            
        Raises:
            StorageError: If any export operation fails
        """
        try:
            pgn_exports = {}
            failed_exports = []
            
            for game_id in game_ids:
                try:
                    pgn = await self.export_game_pgn(game_id)
                    pgn_exports[game_id] = pgn
                except Exception as e:
                    self.logger.error(f"Failed to export game {game_id} to PGN: {e}")
                    failed_exports.append(game_id)
            
            if failed_exports:
                self.logger.warning(f"Failed to export {len(failed_exports)} games: {failed_exports}")
            
            self.logger.info(f"Exported {len(pgn_exports)}/{len(game_ids)} games to PGN format")
            return pgn_exports
            
        except Exception as e:
            self.logger.error(f"Failed to export games batch to PGN: {e}")
            raise StorageError(f"Batch PGN export failed: {e}") from e
    
    # JSON Export (Requirement 3.4)
    
    async def export_game_json(self, game_id: str, include_moves: bool = True,
                              include_metadata: bool = True) -> str:
        """
        Export a single game in JSON format.
        
        Args:
            game_id: ID of the game to export
            include_moves: Whether to include move data
            include_metadata: Whether to include additional metadata
            
        Returns:
            JSON formatted string
            
        Raises:
            StorageError: If game retrieval fails
        """
        try:
            # Get game record
            game = await self.storage_manager.get_game(game_id)
            
            # Convert to dictionary
            game_dict = self._game_to_dict(game, include_metadata)
            
            if include_moves:
                # Get moves for the game
                moves = await self.storage_manager.get_moves(game_id)
                game_dict['moves'] = [self._move_to_dict(move, include_metadata) for move in moves]
            
            # Convert to JSON
            json_str = json.dumps(game_dict, indent=2, default=self._json_serializer)
            
            self.logger.info(f"Exported game {game_id} to JSON format")
            return json_str
            
        except Exception as e:
            self.logger.error(f"Failed to export game {game_id} to JSON: {e}")
            raise StorageError(f"JSON export failed: {e}") from e
    
    def _game_to_dict(self, game: GameRecord, include_metadata: bool = True) -> Dict[str, Any]:
        """Convert GameRecord to dictionary for JSON export."""
        game_dict = {
            'game_id': game.game_id,
            'start_time': game.start_time.isoformat(),
            'players': {
                str(k): {
                    'player_id': v.player_id,
                    'model_name': v.model_name,
                    'model_provider': v.model_provider,
                    'agent_type': v.agent_type,
                    'elo_rating': v.elo_rating
                } for k, v in game.players.items()
            },
            'initial_fen': game.initial_fen,
            'total_moves': game.total_moves
        }
        
        # Optional fields
        if game.tournament_id:
            game_dict['tournament_id'] = game.tournament_id
        if game.end_time:
            game_dict['end_time'] = game.end_time.isoformat()
        if game.final_fen:
            game_dict['final_fen'] = game.final_fen
        if game.outcome:
            game_dict['outcome'] = {
                'result': game.outcome.result.value,
                'winner': game.outcome.winner,
                'termination': game.outcome.termination.value
            }
        if game.game_duration_seconds:
            game_dict['game_duration_seconds'] = game.game_duration_seconds
        
        if include_metadata and game.metadata:
            game_dict['metadata'] = game.metadata
        
        return game_dict
    
    def _move_to_dict(self, move: MoveRecord, include_metadata: bool = True) -> Dict[str, Any]:
        """Convert MoveRecord to dictionary for JSON export."""
        move_dict = {
            'move_number': move.move_number,
            'player': move.player,
            'timestamp': move.timestamp.isoformat(),
            'fen_before': move.fen_before,
            'fen_after': move.fen_after,
            'move_san': move.move_san,
            'move_uci': move.move_uci,
            'is_legal': move.is_legal,
            'parsing_success': move.parsing_success,
            'thinking_time_ms': move.thinking_time_ms
        }
        
        if include_metadata:
            move_dict.update({
                'legal_moves': move.legal_moves,
                'prompt_text': move.prompt_text,
                'raw_response': move.raw_response,
                'parsed_move': move.parsed_move,
                'parsing_attempts': move.parsing_attempts,
                'api_call_time_ms': move.api_call_time_ms,
                'parsing_time_ms': move.parsing_time_ms,
                'move_quality_score': move.move_quality_score,
                'blunder_flag': move.blunder_flag
            })
            
            if move.rethink_attempts:
                move_dict['rethink_attempts'] = [
                    {
                        'attempt_number': attempt.attempt_number,
                        'prompt_text': attempt.prompt_text,
                        'raw_response': attempt.raw_response,
                        'parsed_move': attempt.parsed_move,
                        'was_legal': attempt.was_legal,
                        'timestamp': attempt.timestamp.isoformat()
                    } for attempt in move.rethink_attempts
                ]
            
            if move.error_type:
                move_dict['error_type'] = move.error_type
            if move.error_message:
                move_dict['error_message'] = move.error_message
        
        return move_dict
    
    def _json_serializer(self, obj):
        """Custom JSON serializer for datetime and other objects."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
    
    async def export_games_json_batch(self, game_ids: List[str], 
                                     include_moves: bool = True,
                                     include_metadata: bool = True) -> str:
        """
        Export multiple games in JSON format as an array.
        
        Args:
            game_ids: List of game IDs to export
            include_moves: Whether to include move data
            include_metadata: Whether to include additional metadata
            
        Returns:
            JSON formatted string containing array of games
            
        Raises:
            StorageError: If any export operation fails
        """
        try:
            games_data = []
            failed_exports = []
            
            for game_id in game_ids:
                try:
                    # Get game record
                    game = await self.storage_manager.get_game(game_id)
                    game_dict = self._game_to_dict(game, include_metadata)
                    
                    if include_moves:
                        moves = await self.storage_manager.get_moves(game_id)
                        game_dict['moves'] = [self._move_to_dict(move, include_metadata) for move in moves]
                    
                    games_data.append(game_dict)
                    
                except Exception as e:
                    self.logger.error(f"Failed to export game {game_id} to JSON: {e}")
                    failed_exports.append(game_id)
            
            if failed_exports:
                self.logger.warning(f"Failed to export {len(failed_exports)} games: {failed_exports}")
            
            # Convert to JSON
            json_str = json.dumps(games_data, indent=2, default=self._json_serializer)
            
            self.logger.info(f"Exported {len(games_data)}/{len(game_ids)} games to JSON format")
            return json_str
            
        except Exception as e:
            self.logger.error(f"Failed to export games batch to JSON: {e}")
            raise StorageError(f"Batch JSON export failed: {e}") from e  
  
    # CSV Export (Requirement 3.4)
    
    async def export_games_csv(self, game_ids: List[str], output_file: Optional[TextIO] = None) -> str:
        """
        Export games in CSV format.
        
        Args:
            game_ids: List of game IDs to export
            output_file: Optional file object to write to
            
        Returns:
            CSV formatted string if no output_file provided
            
        Raises:
            StorageError: If export operation fails
        """
        try:
            # Define CSV headers for games
            headers = [
                'game_id', 'tournament_id', 'start_time', 'end_time',
                'white_player_id', 'white_model', 'white_provider', 'white_agent_type', 'white_elo',
                'black_player_id', 'black_model', 'black_provider', 'black_agent_type', 'black_elo',
                'result', 'winner', 'termination', 'total_moves', 'duration_seconds',
                'initial_fen', 'final_fen'
            ]
            
            # Use StringIO if no output file provided
            if output_file is None:
                output_file = StringIO()
                return_string = True
            else:
                return_string = False
            
            writer = csv.writer(output_file)
            writer.writerow(headers)
            
            exported_count = 0
            failed_exports = []
            
            for game_id in game_ids:
                try:
                    game = await self.storage_manager.get_game(game_id)
                    row = self._game_to_csv_row(game)
                    writer.writerow(row)
                    exported_count += 1
                    
                except Exception as e:
                    self.logger.error(f"Failed to export game {game_id} to CSV: {e}")
                    failed_exports.append(game_id)
            
            if failed_exports:
                self.logger.warning(f"Failed to export {len(failed_exports)} games: {failed_exports}")
            
            self.logger.info(f"Exported {exported_count}/{len(game_ids)} games to CSV format")
            
            if return_string:
                return output_file.getvalue()
            else:
                return f"Exported {exported_count} games"
                
        except Exception as e:
            self.logger.error(f"Failed to export games to CSV: {e}")
            raise StorageError(f"CSV export failed: {e}") from e
    
    def _game_to_csv_row(self, game: GameRecord) -> List[str]:
        """Convert GameRecord to CSV row."""
        white_player = game.players.get(1)
        black_player = game.players.get(0)
        
        row = [
            game.game_id,
            game.tournament_id or '',
            game.start_time.isoformat() if game.start_time else '',
            game.end_time.isoformat() if game.end_time else '',
            
            # White player info
            white_player.player_id if white_player else '',
            white_player.model_name if white_player else '',
            white_player.model_provider if white_player else '',
            white_player.agent_type if white_player else '',
            str(white_player.elo_rating) if white_player and white_player.elo_rating else '',
            
            # Black player info
            black_player.player_id if black_player else '',
            black_player.model_name if black_player else '',
            black_player.model_provider if black_player else '',
            black_player.agent_type if black_player else '',
            str(black_player.elo_rating) if black_player and black_player.elo_rating else '',
            
            # Game outcome
            game.outcome.result.value if game.outcome else '',
            str(game.outcome.winner) if game.outcome and game.outcome.winner is not None else '',
            game.outcome.termination.value if game.outcome else '',
            
            # Game stats
            str(game.total_moves),
            str(game.game_duration_seconds) if game.game_duration_seconds else '',
            game.initial_fen,
            game.final_fen or ''
        ]
        
        return row
    
    async def export_moves_csv(self, game_ids: List[str], output_file: Optional[TextIO] = None) -> str:
        """
        Export moves in CSV format.
        
        Args:
            game_ids: List of game IDs to export moves for
            output_file: Optional file object to write to
            
        Returns:
            CSV formatted string if no output_file provided
            
        Raises:
            StorageError: If export operation fails
        """
        try:
            # Define CSV headers for moves
            headers = [
                'game_id', 'move_number', 'player', 'timestamp',
                'move_san', 'move_uci', 'is_legal', 'parsing_success',
                'thinking_time_ms', 'api_call_time_ms', 'parsing_time_ms',
                'fen_before', 'fen_after', 'parsed_move', 'parsing_attempts',
                'rethink_attempts_count', 'move_quality_score', 'blunder_flag',
                'error_type', 'error_message'
            ]
            
            # Use StringIO if no output file provided
            if output_file is None:
                output_file = StringIO()
                return_string = True
            else:
                return_string = False
            
            writer = csv.writer(output_file)
            writer.writerow(headers)
            
            exported_moves = 0
            failed_games = []
            
            for game_id in game_ids:
                try:
                    moves = await self.storage_manager.get_moves(game_id)
                    
                    for move in moves:
                        row = self._move_to_csv_row(move)
                        writer.writerow(row)
                        exported_moves += 1
                        
                except Exception as e:
                    self.logger.error(f"Failed to export moves for game {game_id} to CSV: {e}")
                    failed_games.append(game_id)
            
            if failed_games:
                self.logger.warning(f"Failed to export moves for {len(failed_games)} games: {failed_games}")
            
            self.logger.info(f"Exported {exported_moves} moves from {len(game_ids)} games to CSV format")
            
            if return_string:
                return output_file.getvalue()
            else:
                return f"Exported {exported_moves} moves"
                
        except Exception as e:
            self.logger.error(f"Failed to export moves to CSV: {e}")
            raise StorageError(f"Move CSV export failed: {e}") from e
    
    def _move_to_csv_row(self, move: MoveRecord) -> List[str]:
        """Convert MoveRecord to CSV row."""
        row = [
            move.game_id,
            str(move.move_number),
            str(move.player),
            move.timestamp.isoformat(),
            move.move_san,
            move.move_uci,
            str(move.is_legal),
            str(move.parsing_success),
            str(move.thinking_time_ms),
            str(move.api_call_time_ms),
            str(move.parsing_time_ms),
            move.fen_before,
            move.fen_after,
            move.parsed_move or '',
            str(move.parsing_attempts),
            str(len(move.rethink_attempts)),
            str(move.move_quality_score) if move.move_quality_score is not None else '',
            str(move.blunder_flag),
            move.error_type or '',
            move.error_message or ''
        ]
        
        return row
    
    # Batch Export with Filtering (Requirement 3.4)
    
    async def export_filtered_games(self, filters: GameFilters, 
                                   format_type: str = 'json',
                                   include_moves: bool = True,
                                   include_metadata: bool = True,
                                   output_file: Optional[TextIO] = None) -> str:
        """
        Export games matching filters in specified format.
        
        Args:
            filters: GameFilters object with query criteria
            format_type: Export format ('json', 'csv', 'pgn')
            include_moves: Whether to include move data (JSON only)
            include_metadata: Whether to include metadata
            output_file: Optional file object to write to
            
        Returns:
            Formatted string if no output_file provided
            
        Raises:
            StorageError: If export operation fails
            ValidationError: If format_type is invalid
        """
        try:
            if format_type not in ['json', 'csv', 'pgn']:
                raise ValidationError(f"Invalid format type: {format_type}")
            
            # Query games with filters
            games = await self.query_engine.query_games_advanced(filters)
            game_ids = [game.game_id for game in games]
            
            if not game_ids:
                self.logger.info("No games found matching filters")
                return "" if output_file is None else "No games found"
            
            self.logger.info(f"Exporting {len(game_ids)} games in {format_type} format")
            
            # Export based on format
            if format_type == 'json':
                if output_file:
                    result = await self.export_games_json_batch(game_ids, include_moves, include_metadata)
                    output_file.write(result)
                    return f"Exported {len(game_ids)} games"
                else:
                    return await self.export_games_json_batch(game_ids, include_moves, include_metadata)
                    
            elif format_type == 'csv':
                return await self.export_games_csv(game_ids, output_file)
                
            elif format_type == 'pgn':
                if output_file:
                    pgn_exports = await self.export_games_pgn_batch(game_ids)
                    for game_id, pgn in pgn_exports.items():
                        output_file.write(pgn)
                        output_file.write('\n\n')  # Separate games with blank lines
                    return f"Exported {len(pgn_exports)} games"
                else:
                    pgn_exports = await self.export_games_pgn_batch(game_ids)
                    return '\n\n'.join(pgn_exports.values())
            
        except (ValidationError, StorageError):
            raise
        except Exception as e:
            self.logger.error(f"Failed to export filtered games: {e}")
            raise StorageError(f"Filtered export failed: {e}") from e
    
    async def export_player_stats_csv(self, player_ids: Optional[List[str]] = None,
                                     output_file: Optional[TextIO] = None) -> str:
        """
        Export player statistics in CSV format.
        
        Args:
            player_ids: Optional list of specific player IDs to export
            output_file: Optional file object to write to
            
        Returns:
            CSV formatted string if no output_file provided
            
        Raises:
            StorageError: If export operation fails
        """
        try:
            # Define CSV headers for player stats
            headers = [
                'player_id', 'games_played', 'wins', 'losses', 'draws',
                'win_rate', 'draw_rate', 'loss_rate', 'illegal_move_rate',
                'average_thinking_time', 'elo_rating', 'last_updated'
            ]
            
            # Use StringIO if no output file provided
            if output_file is None:
                output_file = StringIO()
                return_string = True
            else:
                return_string = False
            
            writer = csv.writer(output_file)
            writer.writerow(headers)
            
            exported_count = 0
            
            if player_ids:
                # Export specific players
                for player_id in player_ids:
                    try:
                        stats = await self.storage_manager.get_player_stats(player_id)
                        if stats:
                            row = self._player_stats_to_csv_row(stats)
                            writer.writerow(row)
                            exported_count += 1
                    except Exception as e:
                        self.logger.error(f"Failed to export stats for player {player_id}: {e}")
            else:
                # Export all players - this would need to be implemented in storage manager
                # For now, we'll raise an error suggesting to provide specific player IDs
                raise ValidationError("Please provide specific player_ids for stats export")
            
            self.logger.info(f"Exported stats for {exported_count} players to CSV format")
            
            if return_string:
                return output_file.getvalue()
            else:
                return f"Exported {exported_count} player stats"
                
        except (ValidationError, StorageError):
            raise
        except Exception as e:
            self.logger.error(f"Failed to export player stats to CSV: {e}")
            raise StorageError(f"Player stats CSV export failed: {e}") from e
    
    def _player_stats_to_csv_row(self, stats: PlayerStats) -> List[str]:
        """Convert PlayerStats to CSV row."""
        row = [
            stats.player_id,
            str(stats.games_played),
            str(stats.wins),
            str(stats.losses),
            str(stats.draws),
            f"{stats.win_rate:.4f}",
            f"{stats.draw_rate:.4f}",
            f"{stats.loss_rate:.4f}",
            f"{stats.illegal_move_rate:.4f}",
            f"{stats.average_thinking_time:.2f}",
            f"{stats.elo_rating:.2f}",
            stats.last_updated.isoformat()
        ]
        
        return row
    
    # Utility Methods
    
    async def get_export_summary(self, game_ids: List[str]) -> Dict[str, Any]:
        """
        Get summary information about games to be exported.
        
        Args:
            game_ids: List of game IDs
            
        Returns:
            Dictionary with export summary information
            
        Raises:
            StorageError: If summary generation fails
        """
        try:
            summary = {
                'total_games': len(game_ids),
                'completed_games': 0,
                'ongoing_games': 0,
                'total_moves': 0,
                'date_range': {'earliest': None, 'latest': None},
                'players': set(),
                'tournaments': set(),
                'models': set()
            }
            
            for game_id in game_ids:
                try:
                    game = await self.storage_manager.get_game(game_id)
                    
                    if game.is_completed:
                        summary['completed_games'] += 1
                    else:
                        summary['ongoing_games'] += 1
                    
                    summary['total_moves'] += game.total_moves
                    
                    # Track date range
                    if summary['date_range']['earliest'] is None or game.start_time < summary['date_range']['earliest']:
                        summary['date_range']['earliest'] = game.start_time
                    if summary['date_range']['latest'] is None or game.start_time > summary['date_range']['latest']:
                        summary['date_range']['latest'] = game.start_time
                    
                    # Track players, tournaments, models
                    for player_info in game.players.values():
                        summary['players'].add(player_info.player_id)
                        summary['models'].add(f"{player_info.model_provider}/{player_info.model_name}")
                    
                    if game.tournament_id:
                        summary['tournaments'].add(game.tournament_id)
                        
                except Exception as e:
                    self.logger.error(f"Failed to process game {game_id} for summary: {e}")
            
            # Convert sets to lists for JSON serialization
            summary['players'] = list(summary['players'])
            summary['tournaments'] = list(summary['tournaments'])
            summary['models'] = list(summary['models'])
            
            # Convert dates to ISO format
            if summary['date_range']['earliest']:
                summary['date_range']['earliest'] = summary['date_range']['earliest'].isoformat()
            if summary['date_range']['latest']:
                summary['date_range']['latest'] = summary['date_range']['latest'].isoformat()
            
            self.logger.info(f"Generated export summary for {len(game_ids)} games")
            return summary
            
        except Exception as e:
            self.logger.error(f"Failed to generate export summary: {e}")
            raise StorageError(f"Export summary generation failed: {e}") from e