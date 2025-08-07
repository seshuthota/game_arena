"""
SQLite storage backend implementation.

This module provides a SQLite-based storage backend for development
and small-scale deployments of the Game Arena storage system.
"""

import sqlite3
import json
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path

from .base import StorageBackend
from ..models import GameRecord, MoveRecord, PlayerStats, PlayerInfo, GameOutcome, RethinkAttempt
from ..config import DatabaseConfig
from ..migrations import setup_migrations


class SQLiteBackend(StorageBackend):
    """SQLite implementation of the storage backend."""
    
    def __init__(self, config: DatabaseConfig):
        """Initialize SQLite backend."""
        super().__init__(config)
        self._connection: Optional[sqlite3.Connection] = None
        self._db_path = config.database or config.database_url or "game_arena.db"
        
        # Remove sqlite:// prefix if present
        if self._db_path.startswith("sqlite://"):
            self._db_path = self._db_path[9:]
    
    async def connect(self) -> None:
        """Establish connection to SQLite database."""
        # Create directory if it doesn't exist
        db_path = Path(self._db_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # SQLite connections are not truly async, but we'll use asyncio for consistency
        self._connection = sqlite3.connect(
            self._db_path,
            timeout=self.config.connection_timeout,
            check_same_thread=False
        )
        self._connection.row_factory = sqlite3.Row
        self._connected = True
    
    async def disconnect(self) -> None:
        """Close SQLite connection."""
        if self._connection:
            self._connection.close()
            self._connection = None
        self._connected = False
    
    async def initialize_schema(self) -> None:
        """Initialize SQLite database schema using migrations."""
        if not self._connection:
            raise RuntimeError("Not connected to database")
        
        # Set up migration manager and run all migrations
        migration_manager = setup_migrations(self._connection)
        applied_count = migration_manager.migrate_up()
        
        if applied_count > 0:
            print(f"Applied {applied_count} database migrations")
    
    def get_migration_manager(self):
        """Get migration manager for this backend."""
        if not self._connection:
            raise RuntimeError("Not connected to database")
        return setup_migrations(self._connection)
    
    async def create_game(self, game: GameRecord) -> str:
        """Create a new game record."""
        if not self._connection:
            raise RuntimeError("Not connected to database")
        
        cursor = self._connection.cursor()
        
        # Insert game record
        cursor.execute("""
            INSERT INTO games (
                game_id, tournament_id, start_time, end_time, initial_fen, final_fen,
                total_moves, game_duration_seconds, outcome_result, outcome_winner,
                outcome_termination, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            game.game_id,
            game.tournament_id,
            game.start_time,
            game.end_time,
            game.initial_fen,
            game.final_fen,
            game.total_moves,
            game.game_duration_seconds,
            game.outcome.result.value if game.outcome else None,
            game.outcome.winner if game.outcome else None,
            game.outcome.termination.value if game.outcome else None,
            json.dumps(game.metadata)
        ))
        
        # Insert player records
        for player_index, player_info in game.players.items():
            cursor.execute("""
                INSERT INTO players (
                    game_id, player_index, player_id, model_name, model_provider,
                    agent_type, agent_config, elo_rating
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                game.game_id,
                player_index,
                player_info.player_id,
                player_info.model_name,
                player_info.model_provider,
                player_info.agent_type,
                json.dumps(player_info.agent_config),
                player_info.elo_rating
            ))
        
        self._connection.commit()
        return game.game_id
    
    async def get_game(self, game_id: str) -> Optional[GameRecord]:
        """Retrieve a game record by ID."""
        if not self._connection:
            raise RuntimeError("Not connected to database")
        
        cursor = self._connection.cursor()
        
        # Get game data
        cursor.execute("SELECT * FROM games WHERE game_id = ?", (game_id,))
        game_row = cursor.fetchone()
        
        if not game_row:
            return None
        
        # Get player data
        cursor.execute("SELECT * FROM players WHERE game_id = ? ORDER BY player_index", (game_id,))
        player_rows = cursor.fetchall()
        
        # Build player info dict
        players = {}
        for row in player_rows:
            players[row['player_index']] = PlayerInfo(
                player_id=row['player_id'],
                model_name=row['model_name'],
                model_provider=row['model_provider'],
                agent_type=row['agent_type'],
                agent_config=json.loads(row['agent_config']) if row['agent_config'] else {},
                elo_rating=row['elo_rating']
            )
        
        # Build game outcome if present
        outcome = None
        if game_row['outcome_result']:
            from ..models import GameResult, TerminationReason
            outcome = GameOutcome(
                result=GameResult(game_row['outcome_result']),
                winner=game_row['outcome_winner'],
                termination=TerminationReason(game_row['outcome_termination'])
            )
        
        return GameRecord(
            game_id=game_row['game_id'],
            tournament_id=game_row['tournament_id'],
            start_time=datetime.fromisoformat(game_row['start_time']),
            end_time=datetime.fromisoformat(game_row['end_time']) if game_row['end_time'] else None,
            players=players,
            initial_fen=game_row['initial_fen'],
            final_fen=game_row['final_fen'],
            outcome=outcome,
            total_moves=game_row['total_moves'],
            game_duration_seconds=game_row['game_duration_seconds'],
            metadata=json.loads(game_row['metadata']) if game_row['metadata'] else {}
        )
    
    async def update_game(self, game_id: str, updates: Dict[str, Any]) -> bool:
        """Update a game record with new data."""
        if not self._connection:
            raise RuntimeError("Not connected to database")
        
        if not updates:
            return True
        
        cursor = self._connection.cursor()
        
        # Build update query dynamically
        set_clauses = []
        values = []
        
        for key, value in updates.items():
            if key == 'metadata':
                set_clauses.append("metadata = ?")
                values.append(json.dumps(value))
            elif key == 'outcome':
                if value:
                    set_clauses.extend([
                        "outcome_result = ?",
                        "outcome_winner = ?", 
                        "outcome_termination = ?"
                    ])
                    values.extend([
                        value.result.value,
                        value.winner,
                        value.termination.value
                    ])
            else:
                set_clauses.append(f"{key} = ?")
                values.append(value)
        
        if set_clauses:
            query = f"UPDATE games SET {', '.join(set_clauses)} WHERE game_id = ?"
            values.append(game_id)
            
            cursor.execute(query, values)
            self._connection.commit()
            
            return cursor.rowcount > 0
        
        return True
    
    async def delete_game(self, game_id: str) -> bool:
        """Delete a game record and all associated data."""
        if not self._connection:
            raise RuntimeError("Not connected to database")
        
        cursor = self._connection.cursor()
        cursor.execute("DELETE FROM games WHERE game_id = ?", (game_id,))
        self._connection.commit()
        
        return cursor.rowcount > 0
    
    async def add_move(self, move: MoveRecord) -> bool:
        """Add a move record to the database."""
        if not self._connection:
            raise RuntimeError("Not connected to database")
        
        cursor = self._connection.cursor()
        
        # Insert move record
        cursor.execute("""
            INSERT INTO moves (
                game_id, move_number, player, timestamp, fen_before, fen_after,
                legal_moves, move_san, move_uci, is_legal, prompt_text, raw_response,
                parsed_move, parsing_success, parsing_attempts, thinking_time_ms,
                api_call_time_ms, parsing_time_ms, move_quality_score, blunder_flag,
                error_type, error_message
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            move.game_id, move.move_number, move.player, move.timestamp,
            move.fen_before, move.fen_after, json.dumps(move.legal_moves),
            move.move_san, move.move_uci, move.is_legal, move.prompt_text,
            move.raw_response, move.parsed_move, move.parsing_success,
            move.parsing_attempts, move.thinking_time_ms, move.api_call_time_ms,
            move.parsing_time_ms, move.move_quality_score, move.blunder_flag,
            move.error_type, move.error_message
        ))
        
        move_id = cursor.lastrowid
        
        # Insert rethink attempts if any
        for attempt in move.rethink_attempts:
            cursor.execute("""
                INSERT INTO rethink_attempts (
                    move_id, attempt_number, prompt_text, raw_response,
                    parsed_move, was_legal, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                move_id, attempt.attempt_number, attempt.prompt_text,
                attempt.raw_response, attempt.parsed_move, attempt.was_legal,
                attempt.timestamp
            ))
        
        self._connection.commit()
        return True
    
    async def get_moves(self, game_id: str, limit: Optional[int] = None) -> List[MoveRecord]:
        """Get all moves for a game."""
        if not self._connection:
            raise RuntimeError("Not connected to database")
        
        cursor = self._connection.cursor()
        
        query = "SELECT * FROM moves WHERE game_id = ? ORDER BY move_number, player"
        params = [game_id]
        
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        
        cursor.execute(query, params)
        move_rows = cursor.fetchall()
        
        moves = []
        for row in move_rows:
            # Get rethink attempts for this move
            cursor.execute(
                "SELECT * FROM rethink_attempts WHERE move_id = ? ORDER BY attempt_number",
                (row['id'],)
            )
            rethink_rows = cursor.fetchall()
            
            rethink_attempts = [
                RethinkAttempt(
                    attempt_number=r['attempt_number'],
                    prompt_text=r['prompt_text'],
                    raw_response=r['raw_response'],
                    parsed_move=r['parsed_move'],
                    was_legal=r['was_legal'],
                    timestamp=datetime.fromisoformat(r['timestamp'])
                )
                for r in rethink_rows
            ]
            
            move = MoveRecord(
                game_id=row['game_id'],
                move_number=row['move_number'],
                player=row['player'],
                timestamp=datetime.fromisoformat(row['timestamp']),
                fen_before=row['fen_before'],
                fen_after=row['fen_after'],
                legal_moves=json.loads(row['legal_moves']),
                move_san=row['move_san'],
                move_uci=row['move_uci'],
                is_legal=row['is_legal'],
                prompt_text=row['prompt_text'],
                raw_response=row['raw_response'],
                parsed_move=row['parsed_move'],
                parsing_success=row['parsing_success'],
                parsing_attempts=row['parsing_attempts'],
                thinking_time_ms=row['thinking_time_ms'],
                api_call_time_ms=row['api_call_time_ms'],
                parsing_time_ms=row['parsing_time_ms'],
                rethink_attempts=rethink_attempts,
                move_quality_score=row['move_quality_score'],
                blunder_flag=row['blunder_flag'],
                error_type=row['error_type'],
                error_message=row['error_message']
            )
            moves.append(move)
        
        return moves
    
    async def get_move(self, game_id: str, move_number: int, player: int) -> Optional[MoveRecord]:
        """Get a specific move record."""
        moves = await self.get_moves(game_id)
        for move in moves:
            if move.move_number == move_number and move.player == player:
                return move
        return None
    
    async def update_player_stats(self, player_id: str, stats: PlayerStats) -> bool:
        """Update player statistics."""
        if not self._connection:
            raise RuntimeError("Not connected to database")
        
        cursor = self._connection.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO player_stats (
                player_id, games_played, wins, losses, draws, illegal_move_rate,
                average_thinking_time, elo_rating, last_updated
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            stats.player_id, stats.games_played, stats.wins, stats.losses,
            stats.draws, stats.illegal_move_rate, stats.average_thinking_time,
            stats.elo_rating, stats.last_updated
        ))
        
        self._connection.commit()
        return True
    
    async def get_player_stats(self, player_id: str) -> Optional[PlayerStats]:
        """Get player statistics."""
        if not self._connection:
            raise RuntimeError("Not connected to database")
        
        cursor = self._connection.cursor()
        cursor.execute("SELECT * FROM player_stats WHERE player_id = ?", (player_id,))
        row = cursor.fetchone()
        
        if not row:
            return None
        
        return PlayerStats(
            player_id=row['player_id'],
            games_played=row['games_played'],
            wins=row['wins'],
            losses=row['losses'],
            draws=row['draws'],
            illegal_move_rate=row['illegal_move_rate'],
            average_thinking_time=row['average_thinking_time'],
            elo_rating=row['elo_rating'],
            last_updated=datetime.fromisoformat(row['last_updated'])
        )
    
    async def query_games(self, filters: Dict[str, Any], limit: Optional[int] = None,
                         offset: Optional[int] = None) -> List[GameRecord]:
        """Query games with filters."""
        if not self._connection:
            raise RuntimeError("Not connected to database")
        
        cursor = self._connection.cursor()
        
        where_clauses = []
        params = []
        
        for key, value in filters.items():
            if key == "tournament_id":
                where_clauses.append("tournament_id = ?")
                params.append(value)
            elif key == "start_date":
                where_clauses.append("start_time >= ?")
                params.append(value)
            elif key == "end_date":
                where_clauses.append("start_time <= ?")
                params.append(value)
            elif key == "outcome_result":
                where_clauses.append("outcome_result = ?")
                params.append(value)
        
        query = "SELECT game_id FROM games"
        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)
        
        query += " ORDER BY start_time DESC"
        
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        
        if offset:
            query += " OFFSET ?"
            params.append(offset)
        
        cursor.execute(query, params)
        game_ids = [row[0] for row in cursor.fetchall()]
        
        # Fetch full game records
        games = []
        for game_id in game_ids:
            game = await self.get_game(game_id)
            if game:
                games.append(game)
        
        return games
    
    async def count_games(self, filters: Dict[str, Any]) -> int:
        """Count games matching filters."""
        if not self._connection:
            raise RuntimeError("Not connected to database")
        
        cursor = self._connection.cursor()
        
        where_clauses = []
        params = []
        
        for key, value in filters.items():
            if key == "tournament_id":
                where_clauses.append("tournament_id = ?")
                params.append(value)
            elif key == "start_date":
                where_clauses.append("start_time >= ?")
                params.append(value)
            elif key == "end_date":
                where_clauses.append("start_time <= ?")
                params.append(value)
        
        query = "SELECT COUNT(*) FROM games"
        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)
        
        cursor.execute(query, params)
        return cursor.fetchone()[0]
    
    async def cleanup_old_data(self, older_than: datetime) -> int:
        """Clean up data older than specified date."""
        if not self._connection:
            raise RuntimeError("Not connected to database")
        
        cursor = self._connection.cursor()
        cursor.execute("DELETE FROM games WHERE start_time < ?", (older_than,))
        self._connection.commit()
        
        return cursor.rowcount
    
    async def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage backend statistics."""
        if not self._connection:
            raise RuntimeError("Not connected to database")
        
        cursor = self._connection.cursor()
        
        # Get table counts
        cursor.execute("SELECT COUNT(*) FROM games")
        game_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM moves")
        move_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM player_stats")
        player_count = cursor.fetchone()[0]
        
        # Get database file size
        db_size = Path(self._db_path).stat().st_size if Path(self._db_path).exists() else 0
        
        return {
            "backend_type": "sqlite",
            "database_path": self._db_path,
            "database_size_bytes": db_size,
            "game_count": game_count,
            "move_count": move_count,
            "player_count": player_count,
            "connected": self._connected
        }
    
    async def update_move(self, move: MoveRecord) -> bool:
        """Update an existing move record."""
        if not self._connection:
            raise RuntimeError("Not connected to database")
        
        cursor = self._connection.cursor()
        
        # First, get the move ID
        cursor.execute(
            "SELECT id FROM moves WHERE game_id = ? AND move_number = ? AND player = ?",
            (move.game_id, move.move_number, move.player)
        )
        row = cursor.fetchone()
        if not row:
            return False
        
        move_id = row[0]
        
        # Update the move record (without rethink_attempts column)
        cursor.execute("""
            UPDATE moves SET
                fen_before = ?, fen_after = ?, legal_moves = ?, move_san = ?, move_uci = ?,
                is_legal = ?, prompt_text = ?, raw_response = ?, parsed_move = ?,
                parsing_success = ?, parsing_attempts = ?, thinking_time_ms = ?,
                api_call_time_ms = ?, parsing_time_ms = ?, move_quality_score = ?, 
                blunder_flag = ?, error_type = ?, error_message = ?
            WHERE id = ?
        """, (
            move.fen_before, move.fen_after, json.dumps(move.legal_moves),
            move.move_san, move.move_uci, move.is_legal, move.prompt_text,
            move.raw_response, move.parsed_move, move.parsing_success,
            move.parsing_attempts, move.thinking_time_ms, move.api_call_time_ms,
            move.parsing_time_ms, move.move_quality_score, move.blunder_flag, 
            move.error_type, move.error_message, move_id
        ))
        
        # Delete existing rethink attempts for this move
        cursor.execute("DELETE FROM rethink_attempts WHERE move_id = ?", (move_id,))
        
        # Insert updated rethink attempts
        for attempt in move.rethink_attempts:
            cursor.execute("""
                INSERT INTO rethink_attempts (
                    move_id, attempt_number, prompt_text, raw_response,
                    parsed_move, was_legal, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                move_id, attempt.attempt_number, attempt.prompt_text,
                attempt.raw_response, attempt.parsed_move, attempt.was_legal,
                attempt.timestamp
            ))
        
        self._connection.commit()
        return cursor.rowcount > 0
    
    async def add_rethink_attempt(self, game_id: str, move_number: int, 
                                 player: int, rethink_attempt: 'RethinkAttempt') -> bool:
        """Add a rethink attempt record."""
        if not self._connection:
            raise RuntimeError("Not connected to database")
        
        # First, try to get the existing move
        existing_move = await self.get_move(game_id, move_number, player)
        
        if existing_move:
            # Add to existing move's rethink attempts
            existing_move.rethink_attempts.append(rethink_attempt)
            return await self.update_move(existing_move)
        else:
            # Store as a standalone rethink attempt for later association
            # This handles the case where rethink attempts are captured before the move is finalized
            # We'll create a temporary move_id of 0 to indicate it's not yet associated
            cursor = self._connection.cursor()
            
            cursor.execute("""
                INSERT INTO rethink_attempts 
                (move_id, attempt_number, prompt_text, raw_response, 
                 parsed_move, was_legal, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                0,  # Temporary move_id for unassociated rethink attempts
                rethink_attempt.attempt_number,
                rethink_attempt.prompt_text, 
                rethink_attempt.raw_response,
                rethink_attempt.parsed_move, 
                rethink_attempt.was_legal,
                rethink_attempt.timestamp
            ))
            
            self._connection.commit()
            return cursor.rowcount > 0