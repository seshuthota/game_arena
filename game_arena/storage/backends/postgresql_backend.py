"""
PostgreSQL storage backend implementation.

This module provides a PostgreSQL-based storage backend for production
deployments of the Game Arena storage system with connection pooling,
transaction management, and database-specific optimizations.
"""

import asyncio
import json
import logging
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from contextlib import asynccontextmanager

try:
    import asyncpg
    import asyncpg.pool
except ImportError:
    asyncpg = None

from .base import StorageBackend
from ..models import GameRecord, MoveRecord, PlayerStats, PlayerInfo, GameOutcome, RethinkAttempt
from ..config import DatabaseConfig


logger = logging.getLogger(__name__)


class PostgreSQLBackend(StorageBackend):
    """PostgreSQL implementation of the storage backend with connection pooling."""
    
    def __init__(self, config: DatabaseConfig):
        """Initialize PostgreSQL backend."""
        if asyncpg is None:
            raise ImportError(
                "asyncpg is required for PostgreSQL backend. "
                "Install with: pip install asyncpg"
            )
        
        super().__init__(config)
        self._pool: Optional[asyncpg.pool.Pool] = None
        self._connection_string = self._build_connection_string()
    
    def _build_connection_string(self) -> str:
        """Build PostgreSQL connection string from config."""
        if self.config.database_url:
            return self.config.database_url
        
        # Build connection string from individual components
        parts = []
        if self.config.host:
            parts.append(f"host={self.config.host}")
        if self.config.port:
            parts.append(f"port={self.config.port}")
        if self.config.database:
            parts.append(f"database={self.config.database}")
        if self.config.username:
            parts.append(f"user={self.config.username}")
        if self.config.password:
            parts.append(f"password={self.config.password}")
        
        if self.config.enable_ssl:
            parts.append("sslmode=require")
            if self.config.ssl_cert_path:
                parts.append(f"sslcert={self.config.ssl_cert_path}")
        else:
            parts.append("sslmode=prefer")
        
        return " ".join(parts)
    
    async def connect(self) -> None:
        """Establish connection pool to PostgreSQL database."""
        try:
            self._pool = await asyncpg.create_pool(
                self._connection_string,
                min_size=1,
                max_size=self.config.connection_pool_size,
                command_timeout=self.config.query_timeout,
                server_settings={
                    'application_name': 'game_arena_storage',
                    'timezone': 'UTC'
                }
            )
            self._connected = True
            logger.info("Connected to PostgreSQL database")
            
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            raise
    
    async def disconnect(self) -> None:
        """Close PostgreSQL connection pool."""
        if self._pool:
            await self._pool.close()
            self._pool = None
        self._connected = False
        logger.info("Disconnected from PostgreSQL database")
    
    @asynccontextmanager
    async def _get_connection(self):
        """Get a connection from the pool."""
        if not self._pool:
            raise RuntimeError("Not connected to database")
        
        async with self._pool.acquire() as connection:
            yield connection
    
    @asynccontextmanager
    async def _get_transaction(self):
        """Get a connection with transaction context."""
        async with self._get_connection() as conn:
            async with conn.transaction():
                yield conn
    
    async def initialize_schema(self) -> None:
        """Initialize PostgreSQL database schema."""
        if not self._pool:
            raise RuntimeError("Not connected to database")
        
        # Create schema migration table
        async with self._get_connection() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    applied_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """)
            
            # Check if we need to run migrations
            applied_versions = await conn.fetch(
                "SELECT version FROM schema_migrations ORDER BY version"
            )
            applied_versions = [row['version'] for row in applied_versions]
            
            # Apply migrations if needed
            await self._apply_migrations(conn, applied_versions)
    
    async def _apply_migrations(self, conn, applied_versions: List[int]) -> None:
        """Apply database migrations."""
        migrations = self._get_postgresql_migrations()
        
        for migration in migrations:
            if migration['version'] not in applied_versions:
                logger.info(f"Applying migration {migration['version']}: {migration['name']}")
                
                async with conn.transaction():
                    await conn.execute(migration['sql'])
                    await conn.execute("""
                        INSERT INTO schema_migrations (version, name)
                        VALUES ($1, $2)
                    """, migration['version'], migration['name'])
                
                logger.info(f"Applied migration {migration['version']}")
    
    def _get_postgresql_migrations(self) -> List[Dict[str, Any]]:
        """Get PostgreSQL-specific migrations."""
        return [
            {
                'version': 1,
                'name': 'initial_schema',
                'sql': """
                    -- Games table
                    CREATE TABLE IF NOT EXISTS games (
                        game_id TEXT PRIMARY KEY,
                        tournament_id TEXT,
                        start_time TIMESTAMP WITH TIME ZONE NOT NULL,
                        end_time TIMESTAMP WITH TIME ZONE,
                        initial_fen TEXT NOT NULL,
                        final_fen TEXT,
                        total_moves INTEGER DEFAULT 0,
                        game_duration_seconds REAL,
                        outcome_result TEXT,
                        outcome_winner INTEGER,
                        outcome_termination TEXT,
                        metadata JSONB,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                    );
                    
                    -- Players table
                    CREATE TABLE IF NOT EXISTS players (
                        game_id TEXT,
                        player_index INTEGER,
                        player_id TEXT NOT NULL,
                        model_name TEXT NOT NULL,
                        model_provider TEXT NOT NULL,
                        agent_type TEXT NOT NULL,
                        agent_config JSONB,
                        elo_rating REAL,
                        PRIMARY KEY (game_id, player_index),
                        FOREIGN KEY (game_id) REFERENCES games (game_id) ON DELETE CASCADE
                    );
                    
                    -- Moves table
                    CREATE TABLE IF NOT EXISTS moves (
                        id SERIAL PRIMARY KEY,
                        game_id TEXT NOT NULL,
                        move_number INTEGER NOT NULL,
                        player INTEGER NOT NULL,
                        timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
                        fen_before TEXT NOT NULL,
                        fen_after TEXT NOT NULL,
                        legal_moves JSONB NOT NULL,
                        move_san TEXT NOT NULL,
                        move_uci TEXT NOT NULL,
                        is_legal BOOLEAN NOT NULL,
                        prompt_text TEXT NOT NULL,
                        raw_response TEXT NOT NULL,
                        parsed_move TEXT,
                        parsing_success BOOLEAN DEFAULT TRUE,
                        parsing_attempts INTEGER DEFAULT 1,
                        thinking_time_ms INTEGER DEFAULT 0,
                        api_call_time_ms INTEGER DEFAULT 0,
                        parsing_time_ms INTEGER DEFAULT 0,
                        move_quality_score REAL,
                        blunder_flag BOOLEAN DEFAULT FALSE,
                        error_type TEXT,
                        error_message TEXT,
                        FOREIGN KEY (game_id) REFERENCES games (game_id) ON DELETE CASCADE,
                        UNIQUE (game_id, move_number, player)
                    );
                    
                    -- Rethink attempts table
                    CREATE TABLE IF NOT EXISTS rethink_attempts (
                        id SERIAL PRIMARY KEY,
                        move_id INTEGER NOT NULL,
                        attempt_number INTEGER NOT NULL,
                        prompt_text TEXT NOT NULL,
                        raw_response TEXT NOT NULL,
                        parsed_move TEXT,
                        was_legal BOOLEAN NOT NULL,
                        timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
                        FOREIGN KEY (move_id) REFERENCES moves (id) ON DELETE CASCADE
                    );
                    
                    -- Player statistics table
                    CREATE TABLE IF NOT EXISTS player_stats (
                        player_id TEXT PRIMARY KEY,
                        games_played INTEGER DEFAULT 0,
                        wins INTEGER DEFAULT 0,
                        losses INTEGER DEFAULT 0,
                        draws INTEGER DEFAULT 0,
                        illegal_move_rate REAL DEFAULT 0.0,
                        average_thinking_time REAL DEFAULT 0.0,
                        elo_rating REAL DEFAULT 1200.0,
                        last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                    );
                """
            },
            {
                'version': 2,
                'name': 'add_performance_indexes',
                'sql': """
                    CREATE INDEX IF NOT EXISTS idx_games_tournament ON games (tournament_id);
                    CREATE INDEX IF NOT EXISTS idx_games_start_time ON games (start_time);
                    CREATE INDEX IF NOT EXISTS idx_games_outcome ON games (outcome_result);
                    CREATE INDEX IF NOT EXISTS idx_games_metadata ON games USING GIN (metadata);
                    CREATE INDEX IF NOT EXISTS idx_moves_game_id ON moves (game_id);
                    CREATE INDEX IF NOT EXISTS idx_moves_timestamp ON moves (timestamp);
                    CREATE INDEX IF NOT EXISTS idx_moves_player ON moves (player);
                    CREATE INDEX IF NOT EXISTS idx_moves_legal_moves ON moves USING GIN (legal_moves);
                    CREATE INDEX IF NOT EXISTS idx_players_player_id ON players (player_id);
                    CREATE INDEX IF NOT EXISTS idx_players_config ON players USING GIN (agent_config);
                    CREATE INDEX IF NOT EXISTS idx_rethink_move_id ON rethink_attempts (move_id);
                """
            },
            {
                'version': 3,
                'name': 'add_partitioning_support',
                'sql': """
                    -- Add partitioning support for large datasets
                    -- This migration prepares tables for future partitioning
                    ALTER TABLE games ADD COLUMN IF NOT EXISTS partition_key DATE GENERATED ALWAYS AS (start_time::DATE) STORED;
                    CREATE INDEX IF NOT EXISTS idx_games_partition_key ON games (partition_key);
                """
            }
        ]
    
    async def create_game(self, game: GameRecord) -> str:
        """Create a new game record."""
        async with self._get_transaction() as conn:
            # Insert game record
            await conn.execute("""
                INSERT INTO games (
                    game_id, tournament_id, start_time, end_time, initial_fen, final_fen,
                    total_moves, game_duration_seconds, outcome_result, outcome_winner,
                    outcome_termination, metadata
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
            """, 
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
            )
            
            # Insert player records
            for player_index, player_info in game.players.items():
                await conn.execute("""
                    INSERT INTO players (
                        game_id, player_index, player_id, model_name, model_provider,
                        agent_type, agent_config, elo_rating
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """,
                    game.game_id,
                    player_index,
                    player_info.player_id,
                    player_info.model_name,
                    player_info.model_provider,
                    player_info.agent_type,
                    json.dumps(player_info.agent_config),
                    player_info.elo_rating
                )
        
        return game.game_id
    
    async def get_game(self, game_id: str) -> Optional[GameRecord]:
        """Retrieve a game record by ID."""
        async with self._get_connection() as conn:
            # Get game data
            game_row = await conn.fetchrow(
                "SELECT * FROM games WHERE game_id = $1", game_id
            )
            
            if not game_row:
                return None
            
            # Get player data
            player_rows = await conn.fetch(
                "SELECT * FROM players WHERE game_id = $1 ORDER BY player_index",
                game_id
            )
            
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
                start_time=game_row['start_time'],
                end_time=game_row['end_time'],
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
        if not updates:
            return True
        
        async with self._get_connection() as conn:
            # Build update query dynamically
            set_clauses = []
            values = []
            param_count = 1
            
            for key, value in updates.items():
                if key == 'metadata':
                    set_clauses.append(f"metadata = ${param_count}")
                    values.append(json.dumps(value))
                elif key == 'outcome':
                    if value:
                        set_clauses.extend([
                            f"outcome_result = ${param_count}",
                            f"outcome_winner = ${param_count + 1}",
                            f"outcome_termination = ${param_count + 2}"
                        ])
                        values.extend([
                            value.result.value,
                            value.winner,
                            value.termination.value
                        ])
                        param_count += 2
                else:
                    set_clauses.append(f"{key} = ${param_count}")
                    values.append(value)
                param_count += 1
            
            if set_clauses:
                query = f"UPDATE games SET {', '.join(set_clauses)} WHERE game_id = ${param_count}"
                values.append(game_id)
                
                result = await conn.execute(query, *values)
                return result.split()[-1] != '0'  # Check if rows were affected
        
        return True
    
    async def delete_game(self, game_id: str) -> bool:
        """Delete a game record and all associated data."""
        async with self._get_connection() as conn:
            result = await conn.execute("DELETE FROM games WHERE game_id = $1", game_id)
            return result.split()[-1] != '0'  # Check if rows were affected
    
    async def add_move(self, move: MoveRecord) -> bool:
        """Add a move record to the database."""
        async with self._get_transaction() as conn:
            # Insert move record
            move_id = await conn.fetchval("""
                INSERT INTO moves (
                    game_id, move_number, player, timestamp, fen_before, fen_after,
                    legal_moves, move_san, move_uci, is_legal, prompt_text, raw_response,
                    parsed_move, parsing_success, parsing_attempts, thinking_time_ms,
                    api_call_time_ms, parsing_time_ms, move_quality_score, blunder_flag,
                    error_type, error_message
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21, $22)
                RETURNING id
            """,
                move.game_id, move.move_number, move.player, move.timestamp,
                move.fen_before, move.fen_after, json.dumps(move.legal_moves),
                move.move_san, move.move_uci, move.is_legal, move.prompt_text,
                move.raw_response, move.parsed_move, move.parsing_success,
                move.parsing_attempts, move.thinking_time_ms, move.api_call_time_ms,
                move.parsing_time_ms, move.move_quality_score, move.blunder_flag,
                move.error_type, move.error_message
            )
            
            # Insert rethink attempts if any
            for attempt in move.rethink_attempts:
                await conn.execute("""
                    INSERT INTO rethink_attempts (
                        move_id, attempt_number, prompt_text, raw_response,
                        parsed_move, was_legal, timestamp
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                """,
                    move_id, attempt.attempt_number, attempt.prompt_text,
                    attempt.raw_response, attempt.parsed_move, attempt.was_legal,
                    attempt.timestamp
                )
        
        return True
    
    async def get_moves(self, game_id: str, limit: Optional[int] = None) -> List[MoveRecord]:
        """Get all moves for a game."""
        async with self._get_connection() as conn:
            query = "SELECT * FROM moves WHERE game_id = $1 ORDER BY move_number, player"
            params = [game_id]
            
            if limit:
                query += f" LIMIT ${len(params) + 1}"
                params.append(limit)
            
            move_rows = await conn.fetch(query, *params)
            
            moves = []
            for row in move_rows:
                # Get rethink attempts for this move
                rethink_rows = await conn.fetch(
                    "SELECT * FROM rethink_attempts WHERE move_id = $1 ORDER BY attempt_number",
                    row['id']
                )
                
                rethink_attempts = [
                    RethinkAttempt(
                        attempt_number=r['attempt_number'],
                        prompt_text=r['prompt_text'],
                        raw_response=r['raw_response'],
                        parsed_move=r['parsed_move'],
                        was_legal=r['was_legal'],
                        timestamp=r['timestamp']
                    )
                    for r in rethink_rows
                ]
                
                move = MoveRecord(
                    game_id=row['game_id'],
                    move_number=row['move_number'],
                    player=row['player'],
                    timestamp=row['timestamp'],
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
        async with self._get_connection() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM moves WHERE game_id = $1 AND move_number = $2 AND player = $3",
                game_id, move_number, player
            )
            
            if not row:
                return None
            
            # Get rethink attempts for this move
            rethink_rows = await conn.fetch(
                "SELECT * FROM rethink_attempts WHERE move_id = $1 ORDER BY attempt_number",
                row['id']
            )
            
            rethink_attempts = [
                RethinkAttempt(
                    attempt_number=r['attempt_number'],
                    prompt_text=r['prompt_text'],
                    raw_response=r['raw_response'],
                    parsed_move=r['parsed_move'],
                    was_legal=r['was_legal'],
                    timestamp=r['timestamp']
                )
                for r in rethink_rows
            ]
            
            return MoveRecord(
                game_id=row['game_id'],
                move_number=row['move_number'],
                player=row['player'],
                timestamp=row['timestamp'],
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
    
    async def update_player_stats(self, player_id: str, stats: PlayerStats) -> bool:
        """Update player statistics."""
        async with self._get_connection() as conn:
            result = await conn.execute("""
                INSERT INTO player_stats (
                    player_id, games_played, wins, losses, draws, illegal_move_rate,
                    average_thinking_time, elo_rating, last_updated
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                ON CONFLICT (player_id) DO UPDATE SET
                    games_played = EXCLUDED.games_played,
                    wins = EXCLUDED.wins,
                    losses = EXCLUDED.losses,
                    draws = EXCLUDED.draws,
                    illegal_move_rate = EXCLUDED.illegal_move_rate,
                    average_thinking_time = EXCLUDED.average_thinking_time,
                    elo_rating = EXCLUDED.elo_rating,
                    last_updated = EXCLUDED.last_updated
            """,
                stats.player_id, stats.games_played, stats.wins, stats.losses,
                stats.draws, stats.illegal_move_rate, stats.average_thinking_time,
                stats.elo_rating, stats.last_updated
            )
            return True
    
    async def get_player_stats(self, player_id: str) -> Optional[PlayerStats]:
        """Get player statistics."""
        async with self._get_connection() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM player_stats WHERE player_id = $1", player_id
            )
            
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
                last_updated=row['last_updated']
            )
    
    async def query_games(self, filters: Dict[str, Any], limit: Optional[int] = None,
                         offset: Optional[int] = None) -> List[GameRecord]:
        """Query games with filters."""
        async with self._get_connection() as conn:
            where_clauses = []
            params = []
            param_count = 1
            
            for key, value in filters.items():
                if key == "tournament_id":
                    where_clauses.append(f"tournament_id = ${param_count}")
                    params.append(value)
                elif key == "start_date":
                    where_clauses.append(f"start_time >= ${param_count}")
                    params.append(value)
                elif key == "end_date":
                    where_clauses.append(f"start_time <= ${param_count}")
                    params.append(value)
                elif key == "outcome_result":
                    where_clauses.append(f"outcome_result = ${param_count}")
                    params.append(value)
                elif key == "player_id":
                    where_clauses.append(f"game_id IN (SELECT game_id FROM players WHERE player_id = ${param_count})")
                    params.append(value)
                param_count += 1
            
            query = "SELECT game_id FROM games"
            if where_clauses:
                query += " WHERE " + " AND ".join(where_clauses)
            
            query += " ORDER BY start_time DESC"
            
            if limit:
                query += f" LIMIT ${param_count}"
                params.append(limit)
                param_count += 1
            
            if offset:
                query += f" OFFSET ${param_count}"
                params.append(offset)
            
            game_rows = await conn.fetch(query, *params)
            game_ids = [row['game_id'] for row in game_rows]
            
            # Fetch full game records
            games = []
            for game_id in game_ids:
                game = await self.get_game(game_id)
                if game:
                    games.append(game)
            
            return games
    
    async def count_games(self, filters: Dict[str, Any]) -> int:
        """Count games matching filters."""
        async with self._get_connection() as conn:
            where_clauses = []
            params = []
            param_count = 1
            
            for key, value in filters.items():
                if key == "tournament_id":
                    where_clauses.append(f"tournament_id = ${param_count}")
                    params.append(value)
                elif key == "start_date":
                    where_clauses.append(f"start_time >= ${param_count}")
                    params.append(value)
                elif key == "end_date":
                    where_clauses.append(f"start_time <= ${param_count}")
                    params.append(value)
                elif key == "player_id":
                    where_clauses.append(f"game_id IN (SELECT game_id FROM players WHERE player_id = ${param_count})")
                    params.append(value)
                param_count += 1
            
            query = "SELECT COUNT(*) FROM games"
            if where_clauses:
                query += " WHERE " + " AND ".join(where_clauses)
            
            result = await conn.fetchval(query, *params)
            return result
    
    async def cleanup_old_data(self, older_than: datetime) -> int:
        """Clean up data older than specified date."""
        async with self._get_connection() as conn:
            result = await conn.execute(
                "DELETE FROM games WHERE start_time < $1", older_than
            )
            return int(result.split()[-1])
    
    async def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage backend statistics."""
        async with self._get_connection() as conn:
            # Get table counts
            game_count = await conn.fetchval("SELECT COUNT(*) FROM games")
            move_count = await conn.fetchval("SELECT COUNT(*) FROM moves")
            player_count = await conn.fetchval("SELECT COUNT(*) FROM player_stats")
            
            # Get database size
            db_size = await conn.fetchval("""
                SELECT pg_size_pretty(pg_database_size(current_database()))
            """)
            
            # Get connection pool stats
            pool_stats = {
                "pool_size": self._pool.get_size() if self._pool else 0,
                "pool_max_size": self.config.connection_pool_size,
                "pool_idle_connections": self._pool.get_idle_size() if self._pool else 0,
            }
            
            return {
                "backend_type": "postgresql",
                "database_size": db_size,
                "game_count": game_count,
                "move_count": move_count,
                "player_count": player_count,
                "connected": self._connected,
                "connection_pool": pool_stats
            }
    
    async def execute_raw_query(self, query: str, params: Optional[List[Any]] = None) -> List[Dict[str, Any]]:
        """Execute a raw SQL query (for advanced analytics)."""
        async with self._get_connection() as conn:
            if params:
                rows = await conn.fetch(query, *params)
            else:
                rows = await conn.fetch(query)
            
            return [dict(row) for row in rows]
    
    async def bulk_insert_moves(self, moves: List[MoveRecord]) -> bool:
        """Bulk insert moves for better performance."""
        if not moves:
            return True
        
        async with self._get_transaction() as conn:
            # Prepare move data
            move_data = []
            rethink_data = []
            
            for move in moves:
                move_data.append((
                    move.game_id, move.move_number, move.player, move.timestamp,
                    move.fen_before, move.fen_after, json.dumps(move.legal_moves),
                    move.move_san, move.move_uci, move.is_legal, move.prompt_text,
                    move.raw_response, move.parsed_move, move.parsing_success,
                    move.parsing_attempts, move.thinking_time_ms, move.api_call_time_ms,
                    move.parsing_time_ms, move.move_quality_score, move.blunder_flag,
                    move.error_type, move.error_message
                ))
            
            # Bulk insert moves
            move_ids = await conn.fetch("""
                INSERT INTO moves (
                    game_id, move_number, player, timestamp, fen_before, fen_after,
                    legal_moves, move_san, move_uci, is_legal, prompt_text, raw_response,
                    parsed_move, parsing_success, parsing_attempts, thinking_time_ms,
                    api_call_time_ms, parsing_time_ms, move_quality_score, blunder_flag,
                    error_type, error_message
                ) SELECT * FROM UNNEST($1::text[], $2::int[], $3::int[], $4::timestamptz[],
                                     $5::text[], $6::text[], $7::jsonb[], $8::text[], $9::text[],
                                     $10::boolean[], $11::text[], $12::text[], $13::text[],
                                     $14::boolean[], $15::int[], $16::int[], $17::int[], $18::int[],
                                     $19::real[], $20::boolean[], $21::text[], $22::text[])
                RETURNING id
            """, *zip(*move_data))
            
            # Prepare rethink data with move IDs
            for i, move in enumerate(moves):
                move_id = move_ids[i]['id']
                for attempt in move.rethink_attempts:
                    rethink_data.append((
                        move_id, attempt.attempt_number, attempt.prompt_text,
                        attempt.raw_response, attempt.parsed_move, attempt.was_legal,
                        attempt.timestamp
                    ))
            
            # Bulk insert rethink attempts if any
            if rethink_data:
                await conn.executemany("""
                    INSERT INTO rethink_attempts (
                        move_id, attempt_number, prompt_text, raw_response,
                        parsed_move, was_legal, timestamp
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                """, rethink_data)
        
        return True
    
    async def update_move(self, move: MoveRecord) -> bool:
        """Update an existing move record."""
        async with self._get_transaction() as conn:
            # First, get the move ID
            move_id = await conn.fetchval(
                "SELECT id FROM moves WHERE game_id = $1 AND move_number = $2 AND player = $3",
                move.game_id, move.move_number, move.player
            )
            
            if not move_id:
                return False
            
            # Update the move record
            await conn.execute("""
                UPDATE moves SET
                    fen_before = $1, fen_after = $2, legal_moves = $3, move_san = $4, move_uci = $5,
                    is_legal = $6, prompt_text = $7, raw_response = $8, parsed_move = $9,
                    parsing_success = $10, parsing_attempts = $11, thinking_time_ms = $12,
                    api_call_time_ms = $13, parsing_time_ms = $14, move_quality_score = $15,
                    blunder_flag = $16, error_type = $17, error_message = $18
                WHERE id = $19
            """,
                move.fen_before, move.fen_after, json.dumps(move.legal_moves),
                move.move_san, move.move_uci, move.is_legal, move.prompt_text,
                move.raw_response, move.parsed_move, move.parsing_success,
                move.parsing_attempts, move.thinking_time_ms, move.api_call_time_ms,
                move.parsing_time_ms, move.move_quality_score, move.blunder_flag,
                move.error_type, move.error_message, move_id
            )
            
            # Delete existing rethink attempts for this move
            await conn.execute("DELETE FROM rethink_attempts WHERE move_id = $1", move_id)
            
            # Insert updated rethink attempts
            for attempt in move.rethink_attempts:
                await conn.execute("""
                    INSERT INTO rethink_attempts (
                        move_id, attempt_number, prompt_text, raw_response,
                        parsed_move, was_legal, timestamp
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                """,
                    move_id, attempt.attempt_number, attempt.prompt_text,
                    attempt.raw_response, attempt.parsed_move, attempt.was_legal,
                    attempt.timestamp
                )
        
        return True
    
    async def add_rethink_attempt(self, game_id: str, move_number: int, 
                                 player: int, rethink_attempt: 'RethinkAttempt') -> bool:
        """Add a rethink attempt record."""
        async with self._get_connection() as conn:
            # First, try to get the existing move
            existing_move = await self.get_move(game_id, move_number, player)
            
            if existing_move:
                # Add to existing move's rethink attempts
                existing_move.rethink_attempts.append(rethink_attempt)
                return await self.update_move(existing_move)
            else:
                # Store as a standalone rethink attempt for later association
                # This handles the case where rethink attempts are captured before the move is finalized
                # We'll use move_id = 0 to indicate it's not yet associated
                await conn.execute("""
                    INSERT INTO rethink_attempts 
                    (move_id, attempt_number, prompt_text, raw_response, 
                     parsed_move, was_legal, timestamp)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                """,
                    0,  # Temporary move_id for unassociated rethink attempts
                    rethink_attempt.attempt_number,
                    rethink_attempt.prompt_text, 
                    rethink_attempt.raw_response,
                    rethink_attempt.parsed_move, 
                    rethink_attempt.was_legal,
                    rethink_attempt.timestamp
                )
                
                return True