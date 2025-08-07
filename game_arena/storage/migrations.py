"""
Database schema migration system for the Game Arena storage system.

This module provides a migration framework to handle database schema
changes and upgrades in a controlled and versioned manner.
"""

import sqlite3
import logging
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
from pathlib import Path


logger = logging.getLogger(__name__)


class Migration:
    """Represents a single database migration."""
    
    def __init__(self, version: int, name: str, up_sql: str, down_sql: str = ""):
        """Initialize a migration.
        
        Args:
            version: Migration version number (must be unique and sequential)
            name: Descriptive name for the migration
            up_sql: SQL to apply the migration
            down_sql: SQL to rollback the migration (optional)
        """
        self.version = version
        self.name = name
        self.up_sql = up_sql
        self.down_sql = down_sql
        self.applied_at: Optional[datetime] = None
    
    def __str__(self) -> str:
        return f"Migration {self.version}: {self.name}"


class MigrationManager:
    """Manages database schema migrations."""
    
    def __init__(self, connection: sqlite3.Connection):
        """Initialize migration manager with database connection."""
        self.connection = connection
        self.migrations: List[Migration] = []
        self._ensure_migration_table()
    
    def _ensure_migration_table(self) -> None:
        """Create migrations table if it doesn't exist."""
        cursor = self.connection.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.connection.commit()
    
    def add_migration(self, migration: Migration) -> None:
        """Add a migration to the manager."""
        # Check for duplicate versions
        for existing in self.migrations:
            if existing.version == migration.version:
                raise ValueError(f"Migration version {migration.version} already exists")
        
        self.migrations.append(migration)
        # Keep migrations sorted by version
        self.migrations.sort(key=lambda m: m.version)
    
    def get_applied_migrations(self) -> List[int]:
        """Get list of applied migration versions."""
        cursor = self.connection.cursor()
        cursor.execute("SELECT version FROM schema_migrations ORDER BY version")
        return [row[0] for row in cursor.fetchall()]
    
    def get_pending_migrations(self) -> List[Migration]:
        """Get list of pending migrations."""
        applied_versions = set(self.get_applied_migrations())
        return [m for m in self.migrations if m.version not in applied_versions]
    
    def apply_migration(self, migration: Migration) -> None:
        """Apply a single migration."""
        logger.info(f"Applying {migration}")
        
        cursor = self.connection.cursor()
        
        try:
            # Execute migration SQL
            cursor.executescript(migration.up_sql)
            
            # Record migration as applied
            cursor.execute("""
                INSERT INTO schema_migrations (version, name, applied_at)
                VALUES (?, ?, ?)
            """, (migration.version, migration.name, datetime.now()))
            
            self.connection.commit()
            migration.applied_at = datetime.now()
            
            logger.info(f"Successfully applied {migration}")
            
        except Exception as e:
            self.connection.rollback()
            logger.error(f"Failed to apply {migration}: {e}")
            raise
    
    def rollback_migration(self, migration: Migration) -> None:
        """Rollback a single migration."""
        if not migration.down_sql:
            raise ValueError(f"Migration {migration.version} has no rollback SQL")
        
        logger.info(f"Rolling back {migration}")
        
        cursor = self.connection.cursor()
        
        try:
            # Execute rollback SQL
            cursor.executescript(migration.down_sql)
            
            # Remove migration record
            cursor.execute(
                "DELETE FROM schema_migrations WHERE version = ?",
                (migration.version,)
            )
            
            self.connection.commit()
            migration.applied_at = None
            
            logger.info(f"Successfully rolled back {migration}")
            
        except Exception as e:
            self.connection.rollback()
            logger.error(f"Failed to rollback {migration}: {e}")
            raise    

    def migrate_up(self, target_version: Optional[int] = None) -> int:
        """Apply all pending migrations up to target version.
        
        Args:
            target_version: Stop at this version (None = apply all)
            
        Returns:
            Number of migrations applied
        """
        pending = self.get_pending_migrations()
        
        if target_version is not None:
            pending = [m for m in pending if m.version <= target_version]
        
        applied_count = 0
        for migration in pending:
            self.apply_migration(migration)
            applied_count += 1
        
        return applied_count
    
    def migrate_down(self, target_version: int) -> int:
        """Rollback migrations down to target version.
        
        Args:
            target_version: Rollback to this version (exclusive)
            
        Returns:
            Number of migrations rolled back
        """
        applied_versions = self.get_applied_migrations()
        to_rollback = [v for v in applied_versions if v > target_version]
        to_rollback.sort(reverse=True)  # Rollback in reverse order
        
        rollback_count = 0
        for version in to_rollback:
            migration = next((m for m in self.migrations if m.version == version), None)
            if migration:
                self.rollback_migration(migration)
                rollback_count += 1
            else:
                logger.warning(f"No migration found for version {version}")
        
        return rollback_count
    
    def get_current_version(self) -> int:
        """Get the current schema version."""
        applied = self.get_applied_migrations()
        return max(applied) if applied else 0
    
    def get_latest_version(self) -> int:
        """Get the latest available migration version."""
        return max((m.version for m in self.migrations), default=0)
    
    def is_up_to_date(self) -> bool:
        """Check if database is up to date with latest migrations."""
        return self.get_current_version() == self.get_latest_version()


def get_default_migrations() -> List[Migration]:
    """Get the default set of migrations for the Game Arena storage system."""
    migrations = []
    
    # Migration 1: Initial schema
    migrations.append(Migration(
        version=1,
        name="initial_schema",
        up_sql="""
            -- Games table
            CREATE TABLE IF NOT EXISTS games (
                game_id TEXT PRIMARY KEY,
                tournament_id TEXT,
                start_time TIMESTAMP NOT NULL,
                end_time TIMESTAMP,
                initial_fen TEXT NOT NULL,
                final_fen TEXT,
                total_moves INTEGER DEFAULT 0,
                game_duration_seconds REAL,
                outcome_result TEXT,
                outcome_winner INTEGER,
                outcome_termination TEXT,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            -- Players table
            CREATE TABLE IF NOT EXISTS players (
                game_id TEXT,
                player_index INTEGER,
                player_id TEXT NOT NULL,
                model_name TEXT NOT NULL,
                model_provider TEXT NOT NULL,
                agent_type TEXT NOT NULL,
                agent_config TEXT,
                elo_rating REAL,
                PRIMARY KEY (game_id, player_index),
                FOREIGN KEY (game_id) REFERENCES games (game_id) ON DELETE CASCADE
            );
            
            -- Moves table
            CREATE TABLE IF NOT EXISTS moves (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_id TEXT NOT NULL,
                move_number INTEGER NOT NULL,
                player INTEGER NOT NULL,
                timestamp TIMESTAMP NOT NULL,
                fen_before TEXT NOT NULL,
                fen_after TEXT NOT NULL,
                legal_moves TEXT NOT NULL,
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
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                move_id INTEGER NOT NULL,
                attempt_number INTEGER NOT NULL,
                prompt_text TEXT NOT NULL,
                raw_response TEXT NOT NULL,
                parsed_move TEXT,
                was_legal BOOLEAN NOT NULL,
                timestamp TIMESTAMP NOT NULL,
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
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """,
        down_sql="""
            DROP TABLE IF EXISTS rethink_attempts;
            DROP TABLE IF EXISTS moves;
            DROP TABLE IF EXISTS players;
            DROP TABLE IF EXISTS player_stats;
            DROP TABLE IF EXISTS games;
        """
    ))
    
    # Migration 2: Add indexes for performance
    migrations.append(Migration(
        version=2,
        name="add_performance_indexes",
        up_sql="""
            CREATE INDEX IF NOT EXISTS idx_games_tournament ON games (tournament_id);
            CREATE INDEX IF NOT EXISTS idx_games_start_time ON games (start_time);
            CREATE INDEX IF NOT EXISTS idx_games_outcome ON games (outcome_result);
            CREATE INDEX IF NOT EXISTS idx_moves_game_id ON moves (game_id);
            CREATE INDEX IF NOT EXISTS idx_moves_timestamp ON moves (timestamp);
            CREATE INDEX IF NOT EXISTS idx_moves_player ON moves (player);
            CREATE INDEX IF NOT EXISTS idx_players_player_id ON players (player_id);
            CREATE INDEX IF NOT EXISTS idx_rethink_move_id ON rethink_attempts (move_id);
        """,
        down_sql="""
            DROP INDEX IF EXISTS idx_games_tournament;
            DROP INDEX IF EXISTS idx_games_start_time;
            DROP INDEX IF EXISTS idx_games_outcome;
            DROP INDEX IF EXISTS idx_moves_game_id;
            DROP INDEX IF EXISTS idx_moves_timestamp;
            DROP INDEX IF EXISTS idx_moves_player;
            DROP INDEX IF EXISTS idx_players_player_id;
            DROP INDEX IF EXISTS idx_rethink_move_id;
        """
    ))
    
    return migrations


def setup_migrations(connection: sqlite3.Connection) -> MigrationManager:
    """Set up migration manager with default migrations."""
    manager = MigrationManager(connection)
    
    for migration in get_default_migrations():
        manager.add_migration(migration)
    
    return manager