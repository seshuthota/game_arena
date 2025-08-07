"""
Configuration management for the Game Arena storage system.

This module provides configuration classes and utilities for managing
storage system settings, database connections, and data collection options.
Enhanced with comprehensive configuration validation, environment-based configuration,
and configuration file support.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Union
from enum import Enum
import os
import json
import yaml
import logging
from pathlib import Path
from datetime import datetime


class StorageBackendType(Enum):
    """Supported storage backend types."""
    SQLITE = "sqlite"
    POSTGRESQL = "postgresql"


class LogLevel(Enum):
    """Logging levels for the storage system."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class DatabaseConfig:
    """Database connection configuration."""
    backend_type: StorageBackendType
    database_url: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    database: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    connection_pool_size: int = 10
    connection_timeout: int = 30
    query_timeout: int = 60
    enable_ssl: bool = False
    ssl_cert_path: Optional[str] = None
    
    def __post_init__(self):
        """Validate database configuration."""
        if self.backend_type == StorageBackendType.SQLITE:
            if not self.database_url and not self.database:
                raise ValueError("SQLite requires database_url or database path")
        elif self.backend_type == StorageBackendType.POSTGRESQL:
            if not self.database_url:
                if not all([self.host, self.database, self.username]):
                    raise ValueError("PostgreSQL requires database_url or host/database/username")
        
        if self.connection_pool_size < 1:
            raise ValueError("connection_pool_size must be positive")
        if self.connection_timeout < 1:
            raise ValueError("connection_timeout must be positive")
        if self.query_timeout < 1:
            raise ValueError("query_timeout must be positive")
    
    @classmethod
    def sqlite_default(cls, db_path: str = "game_arena.db") -> "DatabaseConfig":
        """Create default SQLite configuration."""
        return cls(
            backend_type=StorageBackendType.SQLITE,
            database=db_path,
            connection_pool_size=1,  # SQLite doesn't need pooling
        )
    
    @classmethod
    def postgresql_default(cls, host: str = "localhost", database: str = "game_arena",
                          username: str = "postgres", password: str = "") -> "DatabaseConfig":
        """Create default PostgreSQL configuration."""
        return cls(
            backend_type=StorageBackendType.POSTGRESQL,
            host=host,
            port=5432,
            database=database,
            username=username,
            password=password,
        )
    
    @classmethod
    def from_url(cls, database_url: str) -> "DatabaseConfig":
        """Create configuration from database URL."""
        if database_url.startswith("sqlite"):
            return cls(
                backend_type=StorageBackendType.SQLITE,
                database_url=database_url,
                connection_pool_size=1,
            )
        elif database_url.startswith("postgresql"):
            return cls(
                backend_type=StorageBackendType.POSTGRESQL,
                database_url=database_url,
            )
        else:
            raise ValueError(f"Unsupported database URL: {database_url}")


@dataclass
class StorageConfig:
    """Main storage system configuration."""
    database: DatabaseConfig
    
    # Performance settings
    batch_size: int = 100
    max_concurrent_writes: int = 10
    write_timeout_seconds: int = 30
    enable_write_batching: bool = True
    
    # Data retention settings
    max_game_age_days: Optional[int] = None
    max_games_per_player: Optional[int] = None
    enable_auto_cleanup: bool = False
    cleanup_interval_hours: int = 24
    
    # File storage settings
    file_storage_path: str = "game_data"
    max_file_size_mb: int = 100
    compress_files: bool = True
    
    # Backup settings
    enable_auto_backup: bool = False
    backup_interval_hours: int = 24
    backup_retention_days: int = 30
    backup_path: str = "backups"
    
    # Monitoring settings
    enable_metrics: bool = True
    metrics_interval_seconds: int = 60
    log_level: LogLevel = LogLevel.INFO
    log_file_path: Optional[str] = None
    
    # Feature flags
    enable_move_quality_analysis: bool = False
    enable_real_time_analytics: bool = True
    enable_data_validation: bool = True
    
    def __post_init__(self):
        """Validate storage configuration."""
        if self.batch_size < 1:
            raise ValueError("batch_size must be positive")
        if self.max_concurrent_writes < 1:
            raise ValueError("max_concurrent_writes must be positive")
        if self.write_timeout_seconds < 1:
            raise ValueError("write_timeout_seconds must be positive")
        if self.max_game_age_days is not None and self.max_game_age_days < 1:
            raise ValueError("max_game_age_days must be positive")
        if self.max_games_per_player is not None and self.max_games_per_player < 1:
            raise ValueError("max_games_per_player must be positive")
        if self.cleanup_interval_hours < 1:
            raise ValueError("cleanup_interval_hours must be positive")
        if self.max_file_size_mb < 1:
            raise ValueError("max_file_size_mb must be positive")
        if self.backup_interval_hours < 1:
            raise ValueError("backup_interval_hours must be positive")
        if self.backup_retention_days < 1:
            raise ValueError("backup_retention_days must be positive")
        if self.metrics_interval_seconds < 1:
            raise ValueError("metrics_interval_seconds must be positive")
    
    @classmethod
    def development_default(cls) -> "StorageConfig":
        """Create default configuration for development."""
        return cls(
            database=DatabaseConfig.sqlite_default("dev_game_arena.db"),
            enable_auto_backup=False,
            enable_metrics=False,
            log_level=LogLevel.DEBUG,
        )
    
    @classmethod
    def production_default(cls) -> "StorageConfig":
        """Create default configuration for production."""
        return cls(
            database=DatabaseConfig.postgresql_default(),
            enable_auto_backup=True,
            enable_metrics=True,
            log_level=LogLevel.INFO,
            enable_data_validation=True,
        )


@dataclass
class CollectorConfig:
    """Configuration for game data collection."""
    
    # Collection settings
    enabled: bool = True
    collect_move_data: bool = True
    collect_rethink_data: bool = True
    collect_timing_data: bool = True
    collect_llm_responses: bool = True
    
    # Performance settings
    max_collection_latency_ms: int = 50
    async_processing: bool = True
    queue_size: int = 1000
    worker_threads: int = 2
    
    # Data filtering
    min_game_length: int = 1
    max_game_length: Optional[int] = None
    collect_incomplete_games: bool = True
    
    # Agent integration
    wrap_agents_automatically: bool = True
    agent_types_to_wrap: List[str] = field(default_factory=lambda: ["ChessLLMAgent", "ChessRethinkAgent"])
    preserve_agent_behavior: bool = True
    
    # Error handling
    continue_on_collection_error: bool = True
    max_retry_attempts: int = 3
    retry_delay_seconds: float = 1.0
    
    # Sampling settings
    sample_rate: float = 1.0  # Collect all games by default
    sample_moves: bool = False
    move_sample_rate: float = 1.0
    
    def __post_init__(self):
        """Validate collector configuration."""
        if self.max_collection_latency_ms < 1:
            raise ValueError("max_collection_latency_ms must be positive")
        if self.queue_size < 1:
            raise ValueError("queue_size must be positive")
        if self.worker_threads < 1:
            raise ValueError("worker_threads must be positive")
        if self.min_game_length < 1:
            raise ValueError("min_game_length must be positive")
        if self.max_game_length is not None and self.max_game_length < self.min_game_length:
            raise ValueError("max_game_length must be >= min_game_length")
        if self.max_retry_attempts < 0:
            raise ValueError("max_retry_attempts cannot be negative")
        if self.retry_delay_seconds < 0:
            raise ValueError("retry_delay_seconds cannot be negative")
        if not 0.0 <= self.sample_rate <= 1.0:
            raise ValueError("sample_rate must be between 0 and 1")
        if not 0.0 <= self.move_sample_rate <= 1.0:
            raise ValueError("move_sample_rate must be between 0 and 1")
    
    @classmethod
    def minimal(cls) -> "CollectorConfig":
        """Create minimal collection configuration."""
        return cls(
            collect_rethink_data=False,
            collect_timing_data=False,
            collect_llm_responses=False,
            async_processing=False,
            worker_threads=1,
        )
    
    @classmethod
    def comprehensive(cls) -> "CollectorConfig":
        """Create comprehensive collection configuration."""
        return cls(
            collect_move_data=True,
            collect_rethink_data=True,
            collect_timing_data=True,
            collect_llm_responses=True,
            async_processing=True,
            worker_threads=4,
        )


def load_config_from_env() -> StorageConfig:
    """Load storage configuration from environment variables."""
    # Database configuration
    db_url = os.getenv("GAME_ARENA_DATABASE_URL")
    if db_url:
        db_config = DatabaseConfig.from_url(db_url)
    else:
        # Default to SQLite
        db_path = os.getenv("GAME_ARENA_DB_PATH", "game_arena.db")
        db_config = DatabaseConfig.sqlite_default(db_path)
    
    # Storage configuration
    config = StorageConfig(
        database=db_config,
        batch_size=int(os.getenv("GAME_ARENA_BATCH_SIZE", "100")),
        max_concurrent_writes=int(os.getenv("GAME_ARENA_MAX_CONCURRENT_WRITES", "10")),
        enable_auto_backup=os.getenv("GAME_ARENA_ENABLE_BACKUP", "false").lower() == "true",
        backup_path=os.getenv("GAME_ARENA_BACKUP_PATH", "backups"),
        file_storage_path=os.getenv("GAME_ARENA_FILE_STORAGE_PATH", "game_data"),
        log_level=LogLevel(os.getenv("GAME_ARENA_LOG_LEVEL", "INFO")),
        log_file_path=os.getenv("GAME_ARENA_LOG_FILE"),
    )
    
    return config


def load_collector_config_from_env() -> CollectorConfig:
    """Load collector configuration from environment variables."""
    return CollectorConfig(
        enabled=os.getenv("GAME_ARENA_COLLECTION_ENABLED", "true").lower() == "true",
        collect_rethink_data=os.getenv("GAME_ARENA_COLLECT_RETHINK", "true").lower() == "true",
        collect_timing_data=os.getenv("GAME_ARENA_COLLECT_TIMING", "true").lower() == "true",
        collect_llm_responses=os.getenv("GAME_ARENA_COLLECT_LLM", "true").lower() == "true",
        max_collection_latency_ms=int(os.getenv("GAME_ARENA_MAX_LATENCY_MS", "50")),
        async_processing=os.getenv("GAME_ARENA_ASYNC_PROCESSING", "true").lower() == "true",
        sample_rate=float(os.getenv("GAME_ARENA_SAMPLE_RATE", "1.0")),
    )


class ConfigurationError(Exception):
    """Exception raised for configuration-related errors."""
    pass


class ConfigurationValidator:
    """
    Validates configuration settings and provides detailed error reporting.
    
    Provides comprehensive validation for all configuration classes with
    detailed error messages and suggestions for fixing configuration issues.
    """
    
    def __init__(self):
        """Initialize the configuration validator."""
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def validate_database_config(self, config: DatabaseConfig) -> List[str]:
        """
        Validate database configuration.
        
        Args:
            config: Database configuration to validate
            
        Returns:
            List of validation error messages
        """
        errors = []
        
        try:
            # Basic validation is done in __post_init__, but we can add more here
            if config.backend_type == StorageBackendType.SQLITE:
                if config.database and not config.database.endswith('.db'):
                    errors.append("SQLite database file should have .db extension")
                
                if config.connection_pool_size > 1:
                    errors.append("SQLite should use connection_pool_size=1")
            
            elif config.backend_type == StorageBackendType.POSTGRESQL:
                if config.port and not (1 <= config.port <= 65535):
                    errors.append("PostgreSQL port must be between 1 and 65535")
                
                if config.connection_pool_size > 100:
                    errors.append("Connection pool size seems too large (>100)")
            
            # General validations
            if config.connection_timeout > 300:
                errors.append("Connection timeout seems too long (>300 seconds)")
            
            if config.query_timeout > 3600:
                errors.append("Query timeout seems too long (>1 hour)")
            
        except Exception as e:
            errors.append(f"Database configuration validation failed: {e}")
        
        return errors
    
    def validate_storage_config(self, config: StorageConfig) -> List[str]:
        """
        Validate storage configuration.
        
        Args:
            config: Storage configuration to validate
            
        Returns:
            List of validation error messages
        """
        errors = []
        
        try:
            # Validate database config
            db_errors = self.validate_database_config(config.database)
            errors.extend([f"Database: {error}" for error in db_errors])
            
            # Performance validations
            if config.batch_size > 10000:
                errors.append("Batch size seems too large (>10000)")
            
            if config.max_concurrent_writes > 50:
                errors.append("Max concurrent writes seems too high (>50)")
            
            if config.write_timeout_seconds > 300:
                errors.append("Write timeout seems too long (>300 seconds)")
            
            # File storage validations
            if config.max_file_size_mb > 1000:
                errors.append("Max file size seems too large (>1GB)")
            
            # Path validations
            try:
                Path(config.file_storage_path).resolve()
            except Exception:
                errors.append(f"Invalid file storage path: {config.file_storage_path}")
            
            try:
                Path(config.backup_path).resolve()
            except Exception:
                errors.append(f"Invalid backup path: {config.backup_path}")
            
            # Backup validations
            if config.backup_interval_hours < 1:
                errors.append("Backup interval too frequent (<1 hour)")
            
            if config.backup_retention_days > 365:
                errors.append("Backup retention seems too long (>1 year)")
            
            # Monitoring validations
            if config.metrics_interval_seconds < 10:
                errors.append("Metrics interval too frequent (<10 seconds)")
            
        except Exception as e:
            errors.append(f"Storage configuration validation failed: {e}")
        
        return errors
    
    def validate_collector_config(self, config: CollectorConfig) -> List[str]:
        """
        Validate collector configuration.
        
        Args:
            config: Collector configuration to validate
            
        Returns:
            List of validation error messages
        """
        errors = []
        
        try:
            # Performance validations
            if config.max_collection_latency_ms > 1000:
                errors.append("Collection latency limit seems too high (>1000ms)")
            
            if config.queue_size > 100000:
                errors.append("Queue size seems too large (>100000)")
            
            if config.worker_threads > 20:
                errors.append("Too many worker threads (>20)")
            
            # Sampling validations
            if config.sample_rate < 0.01 and config.sample_rate > 0:
                errors.append("Sample rate seems too low (<1%)")
            
            if config.move_sample_rate < 0.01 and config.move_sample_rate > 0:
                errors.append("Move sample rate seems too low (<1%)")
            
            # Logic validations
            if not config.enabled and any([
                config.collect_move_data,
                config.collect_rethink_data,
                config.collect_timing_data,
                config.collect_llm_responses
            ]):
                errors.append("Collection is disabled but specific collection flags are enabled")
            
        except Exception as e:
            errors.append(f"Collector configuration validation failed: {e}")
        
        return errors
    
    def validate_all(self, storage_config: StorageConfig, 
                    collector_config: CollectorConfig) -> Dict[str, List[str]]:
        """
        Validate all configuration objects.
        
        Args:
            storage_config: Storage configuration to validate
            collector_config: Collector configuration to validate
            
        Returns:
            Dictionary mapping config type to list of errors
        """
        return {
            'storage': self.validate_storage_config(storage_config),
            'collector': self.validate_collector_config(collector_config)
        }


class ConfigurationManager:
    """
    Comprehensive configuration management system.
    
    Provides loading, saving, validation, and environment-based configuration
    management with support for multiple configuration sources and formats.
    """
    
    def __init__(self):
        """Initialize the configuration manager."""
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.validator = ConfigurationValidator()
        self._config_cache: Dict[str, Any] = {}
    
    def load_from_file(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Load configuration from a file.
        
        Args:
            file_path: Path to configuration file (JSON or YAML)
            
        Returns:
            Configuration dictionary
            
        Raises:
            ConfigurationError: If file cannot be loaded or parsed
        """
        try:
            file_path = Path(file_path)
            
            if not file_path.exists():
                raise ConfigurationError(f"Configuration file not found: {file_path}")
            
            with open(file_path, 'r', encoding='utf-8') as f:
                if file_path.suffix.lower() in ['.yml', '.yaml']:
                    try:
                        import yaml
                        config_data = yaml.safe_load(f)
                    except ImportError:
                        raise ConfigurationError("PyYAML is required for YAML configuration files")
                elif file_path.suffix.lower() == '.json':
                    config_data = json.load(f)
                else:
                    raise ConfigurationError(f"Unsupported configuration file format: {file_path.suffix}")
            
            self.logger.info(f"Loaded configuration from {file_path}")
            return config_data
            
        except Exception as e:
            raise ConfigurationError(f"Failed to load configuration from {file_path}: {e}") from e
    
    def save_to_file(self, config_data: Dict[str, Any], file_path: Union[str, Path]) -> None:
        """
        Save configuration to a file.
        
        Args:
            config_data: Configuration dictionary to save
            file_path: Path to save configuration file
            
        Raises:
            ConfigurationError: If file cannot be saved
        """
        try:
            file_path = Path(file_path)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                if file_path.suffix.lower() in ['.yml', '.yaml']:
                    try:
                        import yaml
                        yaml.safe_dump(config_data, f, default_flow_style=False, indent=2)
                    except ImportError:
                        raise ConfigurationError("PyYAML is required for YAML configuration files")
                elif file_path.suffix.lower() == '.json':
                    json.dump(config_data, f, indent=2, default=str)
                else:
                    raise ConfigurationError(f"Unsupported configuration file format: {file_path.suffix}")
            
            self.logger.info(f"Saved configuration to {file_path}")
            
        except Exception as e:
            raise ConfigurationError(f"Failed to save configuration to {file_path}: {e}") from e
    
    def create_storage_config(self, config_data: Dict[str, Any]) -> StorageConfig:
        """
        Create StorageConfig from configuration data.
        
        Args:
            config_data: Configuration dictionary
            
        Returns:
            StorageConfig instance
            
        Raises:
            ConfigurationError: If configuration is invalid
        """
        try:
            # Extract database configuration
            db_data = config_data.get('database', {})
            
            # Handle backend type
            backend_type_str = db_data.get('backend_type', 'sqlite')
            if isinstance(backend_type_str, str):
                backend_type = StorageBackendType(backend_type_str.lower())
            else:
                backend_type = backend_type_str
            
            # Create database config
            db_config = DatabaseConfig(
                backend_type=backend_type,
                database_url=db_data.get('database_url'),
                host=db_data.get('host'),
                port=db_data.get('port'),
                database=db_data.get('database'),
                username=db_data.get('username'),
                password=db_data.get('password'),
                connection_pool_size=db_data.get('connection_pool_size', 10),
                connection_timeout=db_data.get('connection_timeout', 30),
                query_timeout=db_data.get('query_timeout', 60),
                enable_ssl=db_data.get('enable_ssl', False),
                ssl_cert_path=db_data.get('ssl_cert_path')
            )
            
            # Handle log level
            log_level_str = config_data.get('log_level', 'INFO')
            if isinstance(log_level_str, str):
                log_level = LogLevel(log_level_str.upper())
            else:
                log_level = log_level_str
            
            # Create storage config
            storage_config = StorageConfig(
                database=db_config,
                batch_size=config_data.get('batch_size', 100),
                max_concurrent_writes=config_data.get('max_concurrent_writes', 10),
                write_timeout_seconds=config_data.get('write_timeout_seconds', 30),
                enable_write_batching=config_data.get('enable_write_batching', True),
                max_game_age_days=config_data.get('max_game_age_days'),
                max_games_per_player=config_data.get('max_games_per_player'),
                enable_auto_cleanup=config_data.get('enable_auto_cleanup', False),
                cleanup_interval_hours=config_data.get('cleanup_interval_hours', 24),
                file_storage_path=config_data.get('file_storage_path', 'game_data'),
                max_file_size_mb=config_data.get('max_file_size_mb', 100),
                compress_files=config_data.get('compress_files', True),
                enable_auto_backup=config_data.get('enable_auto_backup', False),
                backup_interval_hours=config_data.get('backup_interval_hours', 24),
                backup_retention_days=config_data.get('backup_retention_days', 30),
                backup_path=config_data.get('backup_path', 'backups'),
                enable_metrics=config_data.get('enable_metrics', True),
                metrics_interval_seconds=config_data.get('metrics_interval_seconds', 60),
                log_level=log_level,
                log_file_path=config_data.get('log_file_path'),
                enable_move_quality_analysis=config_data.get('enable_move_quality_analysis', False),
                enable_real_time_analytics=config_data.get('enable_real_time_analytics', True),
                enable_data_validation=config_data.get('enable_data_validation', True)
            )
            
            return storage_config
            
        except Exception as e:
            raise ConfigurationError(f"Failed to create storage configuration: {e}") from e
    
    def create_collector_config(self, config_data: Dict[str, Any]) -> CollectorConfig:
        """
        Create CollectorConfig from configuration data.
        
        Args:
            config_data: Configuration dictionary
            
        Returns:
            CollectorConfig instance
            
        Raises:
            ConfigurationError: If configuration is invalid
        """
        try:
            collector_config = CollectorConfig(
                enabled=config_data.get('enabled', True),
                collect_move_data=config_data.get('collect_move_data', True),
                collect_rethink_data=config_data.get('collect_rethink_data', True),
                collect_timing_data=config_data.get('collect_timing_data', True),
                collect_llm_responses=config_data.get('collect_llm_responses', True),
                max_collection_latency_ms=config_data.get('max_collection_latency_ms', 50),
                async_processing=config_data.get('async_processing', True),
                queue_size=config_data.get('queue_size', 1000),
                worker_threads=config_data.get('worker_threads', 2),
                min_game_length=config_data.get('min_game_length', 1),
                max_game_length=config_data.get('max_game_length'),
                collect_incomplete_games=config_data.get('collect_incomplete_games', True),
                wrap_agents_automatically=config_data.get('wrap_agents_automatically', True),
                agent_types_to_wrap=config_data.get('agent_types_to_wrap', ["ChessLLMAgent", "ChessRethinkAgent"]),
                preserve_agent_behavior=config_data.get('preserve_agent_behavior', True),
                continue_on_collection_error=config_data.get('continue_on_collection_error', True),
                max_retry_attempts=config_data.get('max_retry_attempts', 3),
                retry_delay_seconds=config_data.get('retry_delay_seconds', 1.0),
                sample_rate=config_data.get('sample_rate', 1.0),
                sample_moves=config_data.get('sample_moves', False),
                move_sample_rate=config_data.get('move_sample_rate', 1.0)
            )
            
            return collector_config
            
        except Exception as e:
            raise ConfigurationError(f"Failed to create collector configuration: {e}") from e
    
    def load_configuration(self, 
                          config_file: Optional[Union[str, Path]] = None,
                          use_environment: bool = True,
                          validate: bool = True) -> Dict[str, Any]:
        """
        Load complete configuration from multiple sources.
        
        Args:
            config_file: Optional configuration file path
            use_environment: Whether to use environment variables
            validate: Whether to validate configuration
            
        Returns:
            Dictionary containing storage and collector configurations
            
        Raises:
            ConfigurationError: If configuration loading or validation fails
        """
        try:
            # Start with default configurations
            if use_environment:
                # Check environment for configuration type
                env_type = os.getenv("GAME_ARENA_ENV", "development").lower()
                if env_type == "production":
                    storage_config = StorageConfig.production_default()
                else:
                    storage_config = StorageConfig.development_default()
                
                collector_config = CollectorConfig()
                
                # Override with environment variables
                storage_config = load_config_from_env()
                collector_config = load_collector_config_from_env()
            else:
                # Use defaults
                storage_config = StorageConfig.development_default()
                collector_config = CollectorConfig()
            
            # Override with file configuration if provided
            if config_file:
                file_config = self.load_from_file(config_file)
                
                if 'storage' in file_config:
                    storage_config = self.create_storage_config(file_config['storage'])
                
                if 'collector' in file_config:
                    collector_config = self.create_collector_config(file_config['collector'])
            
            # Validate configuration if requested
            if validate:
                validation_errors = self.validator.validate_all(storage_config, collector_config)
                
                all_errors = []
                for config_type, errors in validation_errors.items():
                    if errors:
                        all_errors.extend([f"{config_type}: {error}" for error in errors])
                
                if all_errors:
                    error_msg = "Configuration validation failed:\n" + "\n".join(all_errors)
                    raise ConfigurationError(error_msg)
            
            result = {
                'storage': storage_config,
                'collector': collector_config,
                'loaded_from': {
                    'file': str(config_file) if config_file else None,
                    'environment': use_environment,
                    'timestamp': datetime.now().isoformat()
                }
            }
            
            self.logger.info("Configuration loaded successfully")
            return result
            
        except Exception as e:
            if isinstance(e, ConfigurationError):
                raise
            raise ConfigurationError(f"Failed to load configuration: {e}") from e
    
    def export_configuration(self, 
                           storage_config: StorageConfig,
                           collector_config: CollectorConfig,
                           output_file: Union[str, Path]) -> None:
        """
        Export configuration to a file.
        
        Args:
            storage_config: Storage configuration to export
            collector_config: Collector configuration to export
            output_file: Output file path
            
        Raises:
            ConfigurationError: If export fails
        """
        try:
            # Convert configurations to dictionaries
            config_data = {
                'storage': self._config_to_dict(storage_config),
                'collector': self._config_to_dict(collector_config),
                'metadata': {
                    'exported_at': datetime.now().isoformat(),
                    'version': '1.0'
                }
            }
            
            self.save_to_file(config_data, output_file)
            
        except Exception as e:
            raise ConfigurationError(f"Failed to export configuration: {e}") from e
    
    def _config_to_dict(self, config: Any) -> Dict[str, Any]:
        """Convert a configuration object to a dictionary."""
        if hasattr(config, '__dict__'):
            result = {}
            for key, value in config.__dict__.items():
                if isinstance(value, Enum):
                    result[key] = value.value
                elif hasattr(value, '__dict__') and not isinstance(value, (str, int, float, bool, type(None))):
                    result[key] = self._config_to_dict(value)
                elif isinstance(value, list):
                    result[key] = [self._config_to_dict(item) if hasattr(item, '__dict__') else item for item in value]
                else:
                    result[key] = value
            return result
        else:
            return config
    
    def get_configuration_template(self) -> Dict[str, Any]:
        """
        Get a configuration template with all available options.
        
        Returns:
            Configuration template dictionary
        """
        return {
            'storage': {
                'database': {
                    'backend_type': 'sqlite',  # or 'postgresql'
                    'database_url': None,
                    'host': 'localhost',
                    'port': 5432,
                    'database': 'game_arena',
                    'username': 'postgres',
                    'password': '',
                    'connection_pool_size': 10,
                    'connection_timeout': 30,
                    'query_timeout': 60,
                    'enable_ssl': False,
                    'ssl_cert_path': None
                },
                'batch_size': 100,
                'max_concurrent_writes': 10,
                'write_timeout_seconds': 30,
                'enable_write_batching': True,
                'max_game_age_days': None,
                'max_games_per_player': None,
                'enable_auto_cleanup': False,
                'cleanup_interval_hours': 24,
                'file_storage_path': 'game_data',
                'max_file_size_mb': 100,
                'compress_files': True,
                'enable_auto_backup': False,
                'backup_interval_hours': 24,
                'backup_retention_days': 30,
                'backup_path': 'backups',
                'enable_metrics': True,
                'metrics_interval_seconds': 60,
                'log_level': 'INFO',
                'log_file_path': None,
                'enable_move_quality_analysis': False,
                'enable_real_time_analytics': True,
                'enable_data_validation': True
            },
            'collector': {
                'enabled': True,
                'collect_move_data': True,
                'collect_rethink_data': True,
                'collect_timing_data': True,
                'collect_llm_responses': True,
                'max_collection_latency_ms': 50,
                'async_processing': True,
                'queue_size': 1000,
                'worker_threads': 2,
                'min_game_length': 1,
                'max_game_length': None,
                'collect_incomplete_games': True,
                'wrap_agents_automatically': True,
                'agent_types_to_wrap': ['ChessLLMAgent', 'ChessRethinkAgent'],
                'preserve_agent_behavior': True,
                'continue_on_collection_error': True,
                'max_retry_attempts': 3,
                'retry_delay_seconds': 1.0,
                'sample_rate': 1.0,
                'sample_moves': False,
                'move_sample_rate': 1.0
            }
        }