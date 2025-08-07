"""
Unit tests for the configuration management system.
"""

import json
import os
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from .config import (
    StorageBackendType, LogLevel, DatabaseConfig, StorageConfig, CollectorConfig,
    ConfigurationError, ConfigurationValidator, ConfigurationManager,
    load_config_from_env, load_collector_config_from_env
)


class TestDatabaseConfig:
    """Test database configuration functionality."""
    
    def test_sqlite_default(self):
        """Test SQLite default configuration."""
        config = DatabaseConfig.sqlite_default("test.db")
        
        assert config.backend_type == StorageBackendType.SQLITE
        assert config.database == "test.db"
        assert config.connection_pool_size == 1
    
    def test_postgresql_default(self):
        """Test PostgreSQL default configuration."""
        config = DatabaseConfig.postgresql_default(
            host="localhost",
            database="test_db",
            username="test_user",
            password="test_pass"
        )
        
        assert config.backend_type == StorageBackendType.POSTGRESQL
        assert config.host == "localhost"
        assert config.database == "test_db"
        assert config.username == "test_user"
        assert config.password == "test_pass"
        assert config.port == 5432
    
    def test_from_url_sqlite(self):
        """Test creating config from SQLite URL."""
        config = DatabaseConfig.from_url("sqlite:///test.db")
        
        assert config.backend_type == StorageBackendType.SQLITE
        assert config.database_url == "sqlite:///test.db"
        assert config.connection_pool_size == 1
    
    def test_from_url_postgresql(self):
        """Test creating config from PostgreSQL URL."""
        config = DatabaseConfig.from_url("postgresql://user:pass@localhost:5432/db")
        
        assert config.backend_type == StorageBackendType.POSTGRESQL
        assert config.database_url == "postgresql://user:pass@localhost:5432/db"
    
    def test_from_url_unsupported(self):
        """Test creating config from unsupported URL."""
        with pytest.raises(ValueError, match="Unsupported database URL"):
            DatabaseConfig.from_url("mysql://localhost/db")
    
    def test_sqlite_validation_missing_database(self):
        """Test SQLite validation with missing database."""
        with pytest.raises(ValueError, match="SQLite requires database_url or database path"):
            DatabaseConfig(
                backend_type=StorageBackendType.SQLITE
            )
    
    def test_postgresql_validation_missing_required(self):
        """Test PostgreSQL validation with missing required fields."""
        with pytest.raises(ValueError, match="PostgreSQL requires database_url or host/database/username"):
            DatabaseConfig(
                backend_type=StorageBackendType.POSTGRESQL
            )
    
    def test_invalid_connection_pool_size(self):
        """Test validation with invalid connection pool size."""
        with pytest.raises(ValueError, match="connection_pool_size must be positive"):
            DatabaseConfig(
                backend_type=StorageBackendType.SQLITE,
                database="test.db",
                connection_pool_size=0
            )
    
    def test_invalid_timeouts(self):
        """Test validation with invalid timeout values."""
        with pytest.raises(ValueError, match="connection_timeout must be positive"):
            DatabaseConfig(
                backend_type=StorageBackendType.SQLITE,
                database="test.db",
                connection_timeout=0
            )
        
        with pytest.raises(ValueError, match="query_timeout must be positive"):
            DatabaseConfig(
                backend_type=StorageBackendType.SQLITE,
                database="test.db",
                query_timeout=0
            )


class TestStorageConfig:
    """Test storage configuration functionality."""
    
    def test_development_default(self):
        """Test development default configuration."""
        config = StorageConfig.development_default()
        
        assert config.database.backend_type == StorageBackendType.SQLITE
        assert config.enable_auto_backup is False
        assert config.enable_metrics is False
        assert config.log_level == LogLevel.DEBUG
    
    def test_production_default(self):
        """Test production default configuration."""
        config = StorageConfig.production_default()
        
        assert config.database.backend_type == StorageBackendType.POSTGRESQL
        assert config.enable_auto_backup is True
        assert config.enable_metrics is True
        assert config.log_level == LogLevel.INFO
        assert config.enable_data_validation is True
    
    def test_validation_positive_values(self):
        """Test validation of positive values."""
        db_config = DatabaseConfig.sqlite_default()
        
        with pytest.raises(ValueError, match="batch_size must be positive"):
            StorageConfig(database=db_config, batch_size=0)
        
        with pytest.raises(ValueError, match="max_concurrent_writes must be positive"):
            StorageConfig(database=db_config, max_concurrent_writes=0)
        
        with pytest.raises(ValueError, match="write_timeout_seconds must be positive"):
            StorageConfig(database=db_config, write_timeout_seconds=0)
    
    def test_validation_optional_positive_values(self):
        """Test validation of optional positive values."""
        db_config = DatabaseConfig.sqlite_default()
        
        with pytest.raises(ValueError, match="max_game_age_days must be positive"):
            StorageConfig(database=db_config, max_game_age_days=0)
        
        with pytest.raises(ValueError, match="max_games_per_player must be positive"):
            StorageConfig(database=db_config, max_games_per_player=0)
    
    def test_validation_intervals(self):
        """Test validation of interval values."""
        db_config = DatabaseConfig.sqlite_default()
        
        with pytest.raises(ValueError, match="cleanup_interval_hours must be positive"):
            StorageConfig(database=db_config, cleanup_interval_hours=0)
        
        with pytest.raises(ValueError, match="backup_interval_hours must be positive"):
            StorageConfig(database=db_config, backup_interval_hours=0)
        
        with pytest.raises(ValueError, match="metrics_interval_seconds must be positive"):
            StorageConfig(database=db_config, metrics_interval_seconds=0)


class TestCollectorConfig:
    """Test collector configuration functionality."""
    
    def test_minimal_config(self):
        """Test minimal collector configuration."""
        config = CollectorConfig.minimal()
        
        assert config.collect_rethink_data is False
        assert config.collect_timing_data is False
        assert config.collect_llm_responses is False
        assert config.async_processing is False
        assert config.worker_threads == 1
    
    def test_comprehensive_config(self):
        """Test comprehensive collector configuration."""
        config = CollectorConfig.comprehensive()
        
        assert config.collect_move_data is True
        assert config.collect_rethink_data is True
        assert config.collect_timing_data is True
        assert config.collect_llm_responses is True
        assert config.async_processing is True
        assert config.worker_threads == 4
    
    def test_validation_positive_values(self):
        """Test validation of positive values."""
        with pytest.raises(ValueError, match="max_collection_latency_ms must be positive"):
            CollectorConfig(max_collection_latency_ms=0)
        
        with pytest.raises(ValueError, match="queue_size must be positive"):
            CollectorConfig(queue_size=0)
        
        with pytest.raises(ValueError, match="worker_threads must be positive"):
            CollectorConfig(worker_threads=0)
        
        with pytest.raises(ValueError, match="min_game_length must be positive"):
            CollectorConfig(min_game_length=0)
    
    def test_validation_game_length_consistency(self):
        """Test validation of game length consistency."""
        with pytest.raises(ValueError, match="max_game_length must be >= min_game_length"):
            CollectorConfig(min_game_length=10, max_game_length=5)
    
    def test_validation_retry_settings(self):
        """Test validation of retry settings."""
        with pytest.raises(ValueError, match="max_retry_attempts cannot be negative"):
            CollectorConfig(max_retry_attempts=-1)
        
        with pytest.raises(ValueError, match="retry_delay_seconds cannot be negative"):
            CollectorConfig(retry_delay_seconds=-1.0)
    
    def test_validation_sample_rates(self):
        """Test validation of sample rates."""
        with pytest.raises(ValueError, match="sample_rate must be between 0 and 1"):
            CollectorConfig(sample_rate=1.5)
        
        with pytest.raises(ValueError, match="sample_rate must be between 0 and 1"):
            CollectorConfig(sample_rate=-0.1)
        
        with pytest.raises(ValueError, match="move_sample_rate must be between 0 and 1"):
            CollectorConfig(move_sample_rate=1.5)


class TestEnvironmentConfiguration:
    """Test environment-based configuration loading."""
    
    def test_load_config_from_env_defaults(self):
        """Test loading config from environment with defaults."""
        with patch.dict(os.environ, {}, clear=True):
            config = load_config_from_env()
            
            assert config.database.backend_type == StorageBackendType.SQLITE
            assert config.batch_size == 100
            assert config.max_concurrent_writes == 10
            assert config.enable_auto_backup is False
            assert config.log_level == LogLevel.INFO
    
    def test_load_config_from_env_custom(self):
        """Test loading config from environment with custom values."""
        env_vars = {
            "GAME_ARENA_DATABASE_URL": "postgresql://user:pass@localhost/db",
            "GAME_ARENA_BATCH_SIZE": "200",
            "GAME_ARENA_MAX_CONCURRENT_WRITES": "20",
            "GAME_ARENA_ENABLE_BACKUP": "true",
            "GAME_ARENA_BACKUP_PATH": "custom_backups",
            "GAME_ARENA_LOG_LEVEL": "DEBUG"
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            config = load_config_from_env()
            
            assert config.database.backend_type == StorageBackendType.POSTGRESQL
            assert config.batch_size == 200
            assert config.max_concurrent_writes == 20
            assert config.enable_auto_backup is True
            assert config.backup_path == "custom_backups"
            assert config.log_level == LogLevel.DEBUG
    
    def test_load_collector_config_from_env_defaults(self):
        """Test loading collector config from environment with defaults."""
        with patch.dict(os.environ, {}, clear=True):
            config = load_collector_config_from_env()
            
            assert config.enabled is True
            assert config.collect_rethink_data is True
            assert config.max_collection_latency_ms == 50
            assert config.sample_rate == 1.0
    
    def test_load_collector_config_from_env_custom(self):
        """Test loading collector config from environment with custom values."""
        env_vars = {
            "GAME_ARENA_COLLECTION_ENABLED": "false",
            "GAME_ARENA_COLLECT_RETHINK": "false",
            "GAME_ARENA_MAX_LATENCY_MS": "100",
            "GAME_ARENA_SAMPLE_RATE": "0.5"
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            config = load_collector_config_from_env()
            
            assert config.enabled is False
            assert config.collect_rethink_data is False
            assert config.max_collection_latency_ms == 100
            assert config.sample_rate == 0.5


class TestConfigurationValidator:
    """Test configuration validator functionality."""
    
    @pytest.fixture
    def validator(self):
        """Create a configuration validator for testing."""
        return ConfigurationValidator()
    
    def test_validate_database_config_sqlite_warnings(self, validator):
        """Test database config validation with SQLite warnings."""
        config = DatabaseConfig(
            backend_type=StorageBackendType.SQLITE,
            database="test",  # Missing .db extension
            connection_pool_size=5  # Should be 1 for SQLite
        )
        
        errors = validator.validate_database_config(config)
        
        assert len(errors) == 2
        assert "should have .db extension" in errors[0]
        assert "SQLite should use connection_pool_size=1" in errors[1]
    
    def test_validate_database_config_postgresql_warnings(self, validator):
        """Test database config validation with PostgreSQL warnings."""
        config = DatabaseConfig(
            backend_type=StorageBackendType.POSTGRESQL,
            database_url="postgresql://user:pass@localhost/db",
            port=70000,  # Invalid port
            connection_pool_size=150  # Too large
        )
        
        errors = validator.validate_database_config(config)
        
        assert len(errors) == 2
        assert "port must be between 1 and 65535" in errors[0]
        assert "Connection pool size seems too large" in errors[1]
    
    def test_validate_storage_config_warnings(self, validator):
        """Test storage config validation with warnings."""
        db_config = DatabaseConfig.sqlite_default()
        config = StorageConfig(
            database=db_config,
            batch_size=20000,  # Too large
            max_concurrent_writes=100,  # Too high
            max_file_size_mb=2000,  # Too large
            backup_retention_days=400  # Too long
        )
        
        errors = validator.validate_storage_config(config)
        
        assert len(errors) >= 4
        assert any("Batch size seems too large" in error for error in errors)
        assert any("Max concurrent writes seems too high" in error for error in errors)
        assert any("Max file size seems too large" in error for error in errors)
        assert any("Backup retention seems too long" in error for error in errors)
    
    def test_validate_collector_config_warnings(self, validator):
        """Test collector config validation with warnings."""
        config = CollectorConfig(
            max_collection_latency_ms=2000,  # Too high
            queue_size=200000,  # Too large
            worker_threads=50,  # Too many
            sample_rate=0.005  # Too low
        )
        
        errors = validator.validate_collector_config(config)
        
        assert len(errors) >= 4
        assert any("Collection latency limit seems too high" in error for error in errors)
        assert any("Queue size seems too large" in error for error in errors)
        assert any("Too many worker threads" in error for error in errors)
        assert any("Sample rate seems too low" in error for error in errors)
    
    def test_validate_collector_config_logic_error(self, validator):
        """Test collector config validation with logic errors."""
        config = CollectorConfig(
            enabled=False,
            collect_move_data=True,  # Inconsistent with enabled=False
            collect_rethink_data=True
        )
        
        errors = validator.validate_collector_config(config)
        
        assert len(errors) >= 1
        assert any("Collection is disabled but specific collection flags are enabled" in error for error in errors)
    
    def test_validate_all(self, validator):
        """Test validating all configurations."""
        storage_config = StorageConfig.development_default()
        collector_config = CollectorConfig()
        
        validation_results = validator.validate_all(storage_config, collector_config)
        
        assert 'storage' in validation_results
        assert 'collector' in validation_results
        assert isinstance(validation_results['storage'], list)
        assert isinstance(validation_results['collector'], list)


class TestConfigurationManager:
    """Test configuration manager functionality."""
    
    @pytest.fixture
    def config_manager(self):
        """Create a configuration manager for testing."""
        return ConfigurationManager()
    
    def test_load_from_file_json(self, config_manager):
        """Test loading configuration from JSON file."""
        config_data = {
            'storage': {
                'database': {
                    'backend_type': 'sqlite',
                    'database': 'test.db'
                },
                'batch_size': 200
            },
            'collector': {
                'enabled': True,
                'worker_threads': 4
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            temp_path = f.name
        
        try:
            loaded_data = config_manager.load_from_file(temp_path)
            
            assert loaded_data == config_data
            assert loaded_data['storage']['batch_size'] == 200
            assert loaded_data['collector']['worker_threads'] == 4
        finally:
            os.unlink(temp_path)
    
    def test_load_from_file_not_found(self, config_manager):
        """Test loading from non-existent file."""
        with pytest.raises(ConfigurationError, match="Configuration file not found"):
            config_manager.load_from_file("nonexistent.json")
    
    def test_load_from_file_unsupported_format(self, config_manager):
        """Test loading from unsupported file format."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("some content")
            temp_path = f.name
        
        try:
            with pytest.raises(ConfigurationError, match="Unsupported configuration file format"):
                config_manager.load_from_file(temp_path)
        finally:
            os.unlink(temp_path)
    
    def test_save_to_file_json(self, config_manager):
        """Test saving configuration to JSON file."""
        config_data = {
            'storage': {'batch_size': 200},
            'collector': {'worker_threads': 4}
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name
        
        try:
            config_manager.save_to_file(config_data, temp_path)
            
            # Verify file was created and contains correct data
            with open(temp_path, 'r') as f:
                loaded_data = json.load(f)
            
            assert loaded_data == config_data
        finally:
            os.unlink(temp_path)
    
    def test_create_storage_config(self, config_manager):
        """Test creating storage config from dictionary."""
        config_data = {
            'database': {
                'backend_type': 'sqlite',
                'database': 'test.db'
            },
            'batch_size': 200,
            'log_level': 'debug'
        }
        
        storage_config = config_manager.create_storage_config(config_data)
        
        assert storage_config.database.backend_type == StorageBackendType.SQLITE
        assert storage_config.database.database == 'test.db'
        assert storage_config.batch_size == 200
        assert storage_config.log_level == LogLevel.DEBUG
    
    def test_create_collector_config(self, config_manager):
        """Test creating collector config from dictionary."""
        config_data = {
            'enabled': False,
            'worker_threads': 8,
            'sample_rate': 0.5
        }
        
        collector_config = config_manager.create_collector_config(config_data)
        
        assert collector_config.enabled is False
        assert collector_config.worker_threads == 8
        assert collector_config.sample_rate == 0.5
    
    def test_load_configuration_defaults(self, config_manager):
        """Test loading configuration with defaults."""
        with patch.dict(os.environ, {}, clear=True):
            config = config_manager.load_configuration(use_environment=False, validate=False)
            
            assert 'storage' in config
            assert 'collector' in config
            assert 'loaded_from' in config
            assert isinstance(config['storage'], StorageConfig)
            assert isinstance(config['collector'], CollectorConfig)
    
    def test_load_configuration_with_file(self, config_manager):
        """Test loading configuration with file override."""
        config_data = {
            'storage': {
                'database': {
                    'backend_type': 'sqlite',
                    'database': 'custom.db'
                },
                'batch_size': 300
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            temp_path = f.name
        
        try:
            with patch.dict(os.environ, {}, clear=True):
                config = config_manager.load_configuration(
                    config_file=temp_path,
                    use_environment=False,
                    validate=False
                )
                
                assert config['storage'].database.database == 'custom.db'
                assert config['storage'].batch_size == 300
        finally:
            os.unlink(temp_path)
    
    def test_load_configuration_validation_error(self, config_manager):
        """Test loading configuration with validation errors."""
        config_data = {
            'storage': {
                'database': {
                    'backend_type': 'sqlite',
                    'database': 'test.db'
                },
                'batch_size': 0  # Invalid value
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            temp_path = f.name
        
        try:
            with pytest.raises(ConfigurationError, match="Failed to create storage configuration"):
                config_manager.load_configuration(
                    config_file=temp_path,
                    use_environment=False,
                    validate=True
                )
        finally:
            os.unlink(temp_path)
    
    def test_export_configuration(self, config_manager):
        """Test exporting configuration to file."""
        storage_config = StorageConfig.development_default()
        collector_config = CollectorConfig()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name
        
        try:
            config_manager.export_configuration(storage_config, collector_config, temp_path)
            
            # Verify exported file
            with open(temp_path, 'r') as f:
                exported_data = json.load(f)
            
            assert 'storage' in exported_data
            assert 'collector' in exported_data
            assert 'metadata' in exported_data
            assert exported_data['storage']['database']['backend_type'] == 'sqlite'
        finally:
            os.unlink(temp_path)
    
    def test_get_configuration_template(self, config_manager):
        """Test getting configuration template."""
        template = config_manager.get_configuration_template()
        
        assert 'storage' in template
        assert 'collector' in template
        assert 'database' in template['storage']
        assert 'backend_type' in template['storage']['database']
        assert 'enabled' in template['collector']
    
    def test_config_to_dict(self, config_manager):
        """Test converting configuration object to dictionary."""
        storage_config = StorageConfig.development_default()
        
        config_dict = config_manager._config_to_dict(storage_config)
        
        assert isinstance(config_dict, dict)
        assert 'database' in config_dict
        assert 'batch_size' in config_dict
        assert config_dict['log_level'] == 'DEBUG'  # Enum converted to value


if __name__ == "__main__":
    pytest.main([__file__])