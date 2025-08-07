"""
Backup and archiving system for Game Arena storage.

This module provides automated backup scheduling, data archiving for old games,
data compression and cleanup utilities for the storage system.
"""

import asyncio
import gzip
import json
import logging
import os
import shutil
import tarfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import asdict
import tempfile

from .models import GameRecord, MoveRecord, PlayerStats
from .manager import StorageManager
from .config import StorageConfig
from .exceptions import StorageError


logger = logging.getLogger(__name__)


class BackupConfig:
    """Configuration for backup operations."""
    
    def __init__(
        self,
        backup_directory: str = "./backups",
        archive_directory: str = "./archives", 
        compression_enabled: bool = True,
        backup_retention_days: int = 30,
        archive_retention_days: int = 365,
        auto_backup_interval_hours: int = 24,
        max_backup_size_mb: int = 1000,
        include_move_data: bool = True,
        include_player_stats: bool = True
    ):
        self.backup_directory = Path(backup_directory)
        self.archive_directory = Path(archive_directory)
        self.compression_enabled = compression_enabled
        self.backup_retention_days = backup_retention_days
        self.archive_retention_days = archive_retention_days
        self.auto_backup_interval_hours = auto_backup_interval_hours
        self.max_backup_size_mb = max_backup_size_mb
        self.include_move_data = include_move_data
        self.include_player_stats = include_player_stats
        
        # Ensure directories exist
        self.backup_directory.mkdir(parents=True, exist_ok=True)
        self.archive_directory.mkdir(parents=True, exist_ok=True)


class BackupManager:
    """
    Manages backup and archiving operations for game data.
    
    Provides automated backup scheduling, data archiving for old games,
    and data compression and cleanup utilities.
    """
    
    def __init__(self, storage_manager: StorageManager, config: BackupConfig):
        """Initialize the backup manager."""
        self.storage_manager = storage_manager
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._backup_task: Optional[asyncio.Task] = None
        self._running = False
    
    async def start_automated_backup(self) -> None:
        """Start the automated backup scheduler."""
        if self._backup_task and not self._backup_task.done():
            self.logger.warning("Automated backup already running")
            return
        
        self._running = True
        self._backup_task = asyncio.create_task(self._backup_scheduler())
        self.logger.info(f"Started automated backup with {self.config.auto_backup_interval_hours}h interval")
    
    async def stop_automated_backup(self) -> None:
        """Stop the automated backup scheduler."""
        self._running = False
        if self._backup_task:
            self._backup_task.cancel()
            try:
                await self._backup_task
            except asyncio.CancelledError:
                pass
        self.logger.info("Stopped automated backup scheduler")
    
    async def _backup_scheduler(self) -> None:
        """Internal scheduler for automated backups."""
        while self._running:
            try:
                await self.create_backup()
                await self.cleanup_old_backups()
                
                # Wait for next backup interval
                await asyncio.sleep(self.config.auto_backup_interval_hours * 3600)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in backup scheduler: {e}")
                # Wait a shorter time before retrying on error
                await asyncio.sleep(300)  # 5 minutes
    
    async def create_backup(self, backup_name: Optional[str] = None) -> str:
        """
        Create a complete backup of game data.
        
        Args:
            backup_name: Optional custom name for the backup
            
        Returns:
            Path to the created backup file
            
        Raises:
            StorageError: If backup creation fails
        """
        try:
            if backup_name is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_name = f"game_data_backup_{timestamp}"
            
            backup_path = self.config.backup_directory / f"{backup_name}.json"
            if self.config.compression_enabled:
                backup_path = backup_path.with_suffix(".json.gz")
            
            self.logger.info(f"Creating backup: {backup_path}")
            
            # Collect all data
            backup_data = await self._collect_backup_data()
            
            # Write backup file
            if self.config.compression_enabled:
                with gzip.open(backup_path, 'wt', encoding='utf-8') as f:
                    json.dump(backup_data, f, indent=2, default=self._json_serializer)
            else:
                with open(backup_path, 'w', encoding='utf-8') as f:
                    json.dump(backup_data, f, indent=2, default=self._json_serializer)
            
            # Check backup size
            backup_size_mb = backup_path.stat().st_size / (1024 * 1024)
            if backup_size_mb > self.config.max_backup_size_mb:
                self.logger.warning(f"Backup size ({backup_size_mb:.1f}MB) exceeds limit ({self.config.max_backup_size_mb}MB)")
            
            self.logger.info(f"Backup created successfully: {backup_path} ({backup_size_mb:.1f}MB)")
            return str(backup_path)
            
        except Exception as e:
            self.logger.error(f"Failed to create backup: {e}")
            raise StorageError(f"Backup creation failed: {e}") from e
    
    async def _collect_backup_data(self) -> Dict[str, Any]:
        """Collect all data for backup."""
        backup_data = {
            'metadata': {
                'backup_timestamp': datetime.now().isoformat(),
                'version': '1.0',
                'includes_move_data': self.config.include_move_data,
                'includes_player_stats': self.config.include_player_stats
            },
            'games': [],
            'moves': {},
            'player_stats': []
        }
        
        # Get all games
        all_games = await self.storage_manager.query_games({})
        self.logger.info(f"Backing up {len(all_games)} games")
        
        for game in all_games:
            backup_data['games'].append(asdict(game))
            
            # Get moves for each game if enabled
            if self.config.include_move_data:
                moves = await self.storage_manager.get_moves(game.game_id)
                backup_data['moves'][game.game_id] = [asdict(move) for move in moves]
        
        # Get player statistics if enabled
        if self.config.include_player_stats:
            # Get unique player IDs from games
            player_ids = set()
            for game in all_games:
                for player_info in game.players.values():
                    player_ids.add(player_info.player_id)
            
            for player_id in player_ids:
                try:
                    stats = await self.storage_manager.get_player_stats(player_id)
                    if stats:
                        backup_data['player_stats'].append(asdict(stats))
                except Exception as e:
                    self.logger.warning(f"Failed to backup stats for player {player_id}: {e}")
                    # Continue with other players
        
        return backup_data
    
    def _json_serializer(self, obj: Any) -> Any:
        """Custom JSON serializer for datetime and other objects."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif hasattr(obj, 'value') and hasattr(obj, '_name_'):  # Handle Enum objects more specifically
            return obj.value
        elif hasattr(obj, '__dict__'):
            return obj.__dict__
        else:
            return str(obj)
    
    async def restore_backup(self, backup_path: str, overwrite_existing: bool = False) -> bool:
        """
        Restore data from a backup file.
        
        Args:
            backup_path: Path to the backup file
            overwrite_existing: Whether to overwrite existing data
            
        Returns:
            True if restore was successful
            
        Raises:
            StorageError: If restore operation fails
        """
        try:
            backup_file = Path(backup_path)
            if not backup_file.exists():
                raise StorageError(f"Backup file not found: {backup_path}")
            
            self.logger.info(f"Restoring backup from: {backup_path}")
            
            # Load backup data
            if backup_path.endswith('.gz'):
                with gzip.open(backup_file, 'rt', encoding='utf-8') as f:
                    backup_data = json.load(f)
            else:
                with open(backup_file, 'r', encoding='utf-8') as f:
                    backup_data = json.load(f)
            
            # Validate backup format
            if 'metadata' not in backup_data:
                raise StorageError("Invalid backup format: missing metadata")
            
            metadata = backup_data['metadata']
            self.logger.info(f"Restoring backup from {metadata.get('backup_timestamp', 'unknown time')}")
            
            # Restore games
            games_restored = 0
            if 'games' in backup_data:
                for game_data in backup_data['games']:
                    try:
                        game = self._deserialize_game(game_data)
                        
                        # Check if game exists
                        existing_game = None
                        try:
                            existing_game = await self.storage_manager.get_game(game.game_id)
                        except:
                            pass  # Game doesn't exist
                        
                        if existing_game and not overwrite_existing:
                            self.logger.debug(f"Skipping existing game {game.game_id}")
                            continue
                        
                        if existing_game and overwrite_existing:
                            await self.storage_manager.delete_game(game.game_id)
                        
                        await self.storage_manager.create_game(game)
                        games_restored += 1
                        
                    except Exception as e:
                        self.logger.error(f"Failed to restore game {game_data.get('game_id', 'unknown')}: {e}")
                        # Continue with other games
            
            # Restore moves
            moves_restored = 0
            if 'moves' in backup_data and metadata.get('includes_move_data', False):
                for game_id, moves_data in backup_data['moves'].items():
                    for move_data in moves_data:
                        try:
                            move = self._deserialize_move(move_data)
                            await self.storage_manager.add_move(move)
                            moves_restored += 1
                        except Exception as e:
                            self.logger.error(f"Failed to restore move for game {game_id}: {e}")
            
            # Restore player stats
            stats_restored = 0
            if 'player_stats' in backup_data and metadata.get('includes_player_stats', False):
                for stats_data in backup_data['player_stats']:
                    try:
                        stats = self._deserialize_player_stats(stats_data)
                        await self.storage_manager.update_player_stats(stats.player_id, stats)
                        stats_restored += 1
                    except Exception as e:
                        self.logger.error(f"Failed to restore stats for player {stats_data.get('player_id', 'unknown')}: {e}")
            
            self.logger.info(f"Backup restore completed: {games_restored} games, {moves_restored} moves, {stats_restored} player stats")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to restore backup: {e}")
            raise StorageError(f"Backup restore failed: {e}") from e
    
    def _deserialize_game(self, game_data: Dict[str, Any]) -> GameRecord:
        """Deserialize game data from backup."""
        # Convert datetime strings back to datetime objects
        if 'start_time' in game_data and isinstance(game_data['start_time'], str):
            game_data['start_time'] = datetime.fromisoformat(game_data['start_time'])
        if 'end_time' in game_data and isinstance(game_data['end_time'], str):
            game_data['end_time'] = datetime.fromisoformat(game_data['end_time'])
        
        # Convert players dict
        if 'players' in game_data:
            from .models import PlayerInfo
            players = {}
            for key, player_data in game_data['players'].items():
                players[int(key)] = PlayerInfo(**player_data)
            game_data['players'] = players
        
        # Convert outcome
        if 'outcome' in game_data and game_data['outcome']:
            from .models import GameOutcome, GameResult, TerminationReason
            outcome_data = game_data['outcome']
            # Handle both string values and dict representations
            if isinstance(outcome_data, dict):
                game_data['outcome'] = GameOutcome(
                    result=GameResult(outcome_data['result']),
                    winner=outcome_data.get('winner'),
                    termination=TerminationReason(outcome_data['termination'])
                )
            else:
                # If it's already an object, leave it as is
                pass
        
        return GameRecord(**game_data)
    
    def _deserialize_move(self, move_data: Dict[str, Any]) -> MoveRecord:
        """Deserialize move data from backup."""
        # Convert datetime strings
        if 'timestamp' in move_data and isinstance(move_data['timestamp'], str):
            move_data['timestamp'] = datetime.fromisoformat(move_data['timestamp'])
        
        # Convert rethink attempts
        if 'rethink_attempts' in move_data:
            from .models import RethinkAttempt
            attempts = []
            for attempt_data in move_data['rethink_attempts']:
                if 'timestamp' in attempt_data and isinstance(attempt_data['timestamp'], str):
                    attempt_data['timestamp'] = datetime.fromisoformat(attempt_data['timestamp'])
                attempts.append(RethinkAttempt(**attempt_data))
            move_data['rethink_attempts'] = attempts
        
        return MoveRecord(**move_data)
    
    def _deserialize_player_stats(self, stats_data: Dict[str, Any]) -> PlayerStats:
        """Deserialize player stats data from backup."""
        if 'last_updated' in stats_data and isinstance(stats_data['last_updated'], str):
            stats_data['last_updated'] = datetime.fromisoformat(stats_data['last_updated'])
        
        return PlayerStats(**stats_data)
    
    async def archive_old_games(self, older_than_days: int = 90) -> str:
        """
        Archive games older than specified days to reduce database size.
        
        Args:
            older_than_days: Archive games older than this many days
            
        Returns:
            Path to the created archive file
            
        Raises:
            StorageError: If archiving fails
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=older_than_days)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            archive_name = f"archived_games_{timestamp}"
            
            self.logger.info(f"Archiving games older than {cutoff_date}")
            
            # Find old games
            old_games = await self.storage_manager.query_games({
                'end_time_before': cutoff_date
            })
            
            if not old_games:
                self.logger.info("No games found for archiving")
                return ""
            
            # Create archive data
            archive_data = {
                'metadata': {
                    'archive_timestamp': datetime.now().isoformat(),
                    'cutoff_date': cutoff_date.isoformat(),
                    'games_count': len(old_games),
                    'version': '1.0'
                },
                'games': [],
                'moves': {}
            }
            
            # Collect games and moves
            for game in old_games:
                archive_data['games'].append(asdict(game))
                moves = await self.storage_manager.get_moves(game.game_id)
                archive_data['moves'][game.game_id] = [asdict(move) for move in moves]
            
            # Create archive file
            archive_path = self.config.archive_directory / f"{archive_name}.tar.gz"
            
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir) / f"{archive_name}.json"
                
                # Write JSON data
                with open(temp_path, 'w', encoding='utf-8') as f:
                    json.dump(archive_data, f, indent=2, default=self._json_serializer)
                
                # Create compressed archive
                with tarfile.open(archive_path, 'w:gz') as tar:
                    tar.add(temp_path, arcname=f"{archive_name}.json")
            
            # Remove archived games from database
            archived_count = 0
            for game in old_games:
                try:
                    await self.storage_manager.delete_game(game.game_id)
                    archived_count += 1
                except Exception as e:
                    self.logger.error(f"Failed to delete archived game {game.game_id}: {e}")
            
            archive_size_mb = archive_path.stat().st_size / (1024 * 1024)
            self.logger.info(f"Archived {archived_count} games to {archive_path} ({archive_size_mb:.1f}MB)")
            
            return str(archive_path)
            
        except Exception as e:
            self.logger.error(f"Failed to archive old games: {e}")
            raise StorageError(f"Game archiving failed: {e}") from e
    
    async def cleanup_old_backups(self) -> int:
        """
        Clean up old backup files based on retention policy.
        
        Returns:
            Number of backup files deleted
            
        Raises:
            StorageError: If cleanup fails
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=self.config.backup_retention_days)
            deleted_count = 0
            
            # Clean up backup files
            for backup_file in self.config.backup_directory.glob("*.json*"):
                try:
                    file_time = datetime.fromtimestamp(backup_file.stat().st_mtime)
                    if file_time < cutoff_date:
                        backup_file.unlink()
                        deleted_count += 1
                        self.logger.debug(f"Deleted old backup: {backup_file}")
                except Exception as e:
                    self.logger.error(f"Failed to delete backup file {backup_file}: {e}")
            
            if deleted_count > 0:
                self.logger.info(f"Cleaned up {deleted_count} old backup files")
            
            return deleted_count
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup old backups: {e}")
            raise StorageError(f"Backup cleanup failed: {e}") from e
    
    async def cleanup_old_archives(self) -> int:
        """
        Clean up old archive files based on retention policy.
        
        Returns:
            Number of archive files deleted
            
        Raises:
            StorageError: If cleanup fails
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=self.config.archive_retention_days)
            deleted_count = 0
            
            # Clean up archive files
            for archive_file in self.config.archive_directory.glob("*.tar.gz"):
                try:
                    file_time = datetime.fromtimestamp(archive_file.stat().st_mtime)
                    if file_time < cutoff_date:
                        archive_file.unlink()
                        deleted_count += 1
                        self.logger.debug(f"Deleted old archive: {archive_file}")
                except Exception as e:
                    self.logger.error(f"Failed to delete archive file {archive_file}: {e}")
            
            if deleted_count > 0:
                self.logger.info(f"Cleaned up {deleted_count} old archive files")
            
            return deleted_count
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup old archives: {e}")
            raise StorageError(f"Archive cleanup failed: {e}") from e
    
    async def get_backup_info(self) -> Dict[str, Any]:
        """
        Get information about existing backups and archives.
        
        Returns:
            Dictionary containing backup and archive information
        """
        try:
            backup_info = {
                'backup_directory': str(self.config.backup_directory),
                'archive_directory': str(self.config.archive_directory),
                'backups': [],
                'archives': [],
                'total_backup_size_mb': 0,
                'total_archive_size_mb': 0
            }
            
            # Get backup file info
            for backup_file in self.config.backup_directory.glob("*.json*"):
                size_mb = backup_file.stat().st_size / (1024 * 1024)
                backup_info['backups'].append({
                    'name': backup_file.name,
                    'path': str(backup_file),
                    'size_mb': round(size_mb, 2),
                    'created': datetime.fromtimestamp(backup_file.stat().st_mtime).isoformat()
                })
                backup_info['total_backup_size_mb'] += size_mb
            
            # Get archive file info
            for archive_file in self.config.archive_directory.glob("*.tar.gz"):
                size_mb = archive_file.stat().st_size / (1024 * 1024)
                backup_info['archives'].append({
                    'name': archive_file.name,
                    'path': str(archive_file),
                    'size_mb': round(size_mb, 2),
                    'created': datetime.fromtimestamp(archive_file.stat().st_mtime).isoformat()
                })
                backup_info['total_archive_size_mb'] += size_mb
            
            # Sort by creation time (newest first)
            backup_info['backups'].sort(key=lambda x: x['created'], reverse=True)
            backup_info['archives'].sort(key=lambda x: x['created'], reverse=True)
            
            backup_info['total_backup_size_mb'] = round(backup_info['total_backup_size_mb'], 2)
            backup_info['total_archive_size_mb'] = round(backup_info['total_archive_size_mb'], 2)
            
            return backup_info
            
        except Exception as e:
            self.logger.error(f"Failed to get backup info: {e}")
            raise StorageError(f"Backup info retrieval failed: {e}") from e
    
    async def verify_backup(self, backup_path: str) -> Dict[str, Any]:
        """
        Verify the integrity of a backup file.
        
        Args:
            backup_path: Path to the backup file to verify
            
        Returns:
            Dictionary containing verification results
            
        Raises:
            StorageError: If verification fails
        """
        try:
            backup_file = Path(backup_path)
            if not backup_file.exists():
                raise StorageError(f"Backup file not found: {backup_path}")
            
            verification_result = {
                'file_path': backup_path,
                'file_exists': True,
                'file_size_mb': round(backup_file.stat().st_size / (1024 * 1024), 2),
                'is_readable': False,
                'has_valid_format': False,
                'games_count': 0,
                'moves_count': 0,
                'player_stats_count': 0,
                'errors': []
            }
            
            # Try to read and parse the backup
            try:
                if backup_path.endswith('.gz'):
                    with gzip.open(backup_file, 'rt', encoding='utf-8') as f:
                        backup_data = json.load(f)
                else:
                    with open(backup_file, 'r', encoding='utf-8') as f:
                        backup_data = json.load(f)
                
                verification_result['is_readable'] = True
                
                # Check format
                if 'metadata' in backup_data:
                    verification_result['has_valid_format'] = True
                    verification_result['backup_timestamp'] = backup_data['metadata'].get('backup_timestamp')
                    verification_result['version'] = backup_data['metadata'].get('version')
                else:
                    verification_result['errors'].append("Missing metadata section")
                
                # Count data
                if 'games' in backup_data:
                    verification_result['games_count'] = len(backup_data['games'])
                
                if 'moves' in backup_data:
                    total_moves = sum(len(moves) for moves in backup_data['moves'].values())
                    verification_result['moves_count'] = total_moves
                
                if 'player_stats' in backup_data:
                    verification_result['player_stats_count'] = len(backup_data['player_stats'])
                
            except json.JSONDecodeError as e:
                verification_result['errors'].append(f"Invalid JSON format: {e}")
            except Exception as e:
                verification_result['errors'].append(f"Failed to read backup: {e}")
            
            verification_result['is_valid'] = len(verification_result['errors']) == 0
            
            return verification_result
            
        except Exception as e:
            self.logger.error(f"Failed to verify backup: {e}")
            raise StorageError(f"Backup verification failed: {e}") from e