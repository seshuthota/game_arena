"""
Unit tests for the monitoring and health check system.
"""

import asyncio
import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from .monitoring import (
    HealthStatus, HealthCheckResult, PerformanceMetrics, DataQualityMetrics,
    PerformanceMonitor, DataQualityValidator, HealthChecker, StorageMonitor,
    PSUTIL_AVAILABLE
)
from .models import GameRecord, MoveRecord, PlayerInfo, PlayerStats, GameOutcome, GameResult, TerminationReason
from .exceptions import StorageError


@pytest.fixture
def mock_storage_manager():
    """Create a mock storage manager for testing."""
    manager = AsyncMock()
    
    # Sample game data
    sample_game = GameRecord(
        game_id="test_game_001",
        start_time=datetime.now() - timedelta(hours=2),
        end_time=datetime.now() - timedelta(hours=1),
        players={
            0: PlayerInfo("player_black", "gpt-4", "openai", "ChessLLMAgent"),
            1: PlayerInfo("player_white", "gemini-pro", "google", "ChessRethinkAgent")
        },
        outcome=GameOutcome(GameResult.WHITE_WINS, 1, TerminationReason.CHECKMATE),
        total_moves=25
    )
    
    # Sample move data
    sample_move = MoveRecord(
        game_id="test_game_001",
        move_number=1,
        player=1,
        timestamp=datetime.now() - timedelta(hours=2),
        fen_before="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
        fen_after="rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1",
        legal_moves=["e4", "d4", "Nf3"],
        move_san="e4",
        move_uci="e2e4",
        is_legal=True,
        prompt_text="Make your first move",
        raw_response="I'll play e4",
        thinking_time_ms=1500
    )
    
    # Configure mock methods
    manager.query_games.return_value = [sample_game]
    manager.get_moves.return_value = [sample_move]
    manager.get_game.return_value = sample_game
    manager.backend.is_connected = True
    
    return manager


class TestHealthCheckResult:
    """Test health check result functionality."""
    
    def test_health_check_result_creation(self):
        """Test creating a health check result."""
        result = HealthCheckResult(
            name="test_check",
            status=HealthStatus.HEALTHY,
            message="All good",
            details={"value": 100}
        )
        
        assert result.name == "test_check"
        assert result.status == HealthStatus.HEALTHY
        assert result.message == "All good"
        assert result.details["value"] == 100
        assert isinstance(result.timestamp, datetime)
        assert result.duration_ms == 0.0


class TestPerformanceMetrics:
    """Test performance metrics functionality."""
    
    def test_performance_metrics_creation(self):
        """Test creating performance metrics."""
        metrics = PerformanceMetrics("test_operation")
        
        assert metrics.operation_name == "test_operation"
        assert metrics.total_calls == 0
        assert metrics.total_duration_ms == 0.0
        assert metrics.error_count == 0
        assert metrics.average_duration_ms == 0.0
        assert metrics.error_rate == 0.0
    
    def test_performance_metrics_calculations(self):
        """Test performance metrics calculations."""
        metrics = PerformanceMetrics(
            operation_name="test_op",
            total_calls=10,
            total_duration_ms=1000.0,
            error_count=2
        )
        
        assert metrics.average_duration_ms == 100.0
        assert metrics.error_rate == 0.2
    
    def test_performance_metrics_calls_per_minute(self):
        """Test calls per minute calculation."""
        metrics = PerformanceMetrics(
            operation_name="test_op",
            total_calls=60,
            last_call_timestamp=datetime.now() - timedelta(minutes=2)
        )
        
        # Should be approximately 30 calls per minute
        assert 25 <= metrics.calls_per_minute <= 35


class TestDataQualityMetrics:
    """Test data quality metrics functionality."""
    
    def test_data_quality_metrics_creation(self):
        """Test creating data quality metrics."""
        metrics = DataQualityMetrics()
        
        assert metrics.total_games == 0
        assert metrics.completed_games == 0
        assert metrics.total_moves == 0
        assert metrics.game_completion_rate == 0.0
        assert metrics.move_accuracy_rate == 0.0
        assert metrics.parsing_success_rate == 0.0
    
    def test_data_quality_metrics_calculations(self):
        """Test data quality metrics calculations."""
        metrics = DataQualityMetrics(
            total_games=100,
            completed_games=80,
            total_moves=1000,
            illegal_moves=50,
            parsing_failures=20
        )
        
        assert metrics.game_completion_rate == 0.8
        assert metrics.move_accuracy_rate == 0.95
        assert metrics.parsing_success_rate == 0.98


class TestPerformanceMonitor:
    """Test performance monitor functionality."""
    
    def test_performance_monitor_creation(self):
        """Test creating a performance monitor."""
        monitor = PerformanceMonitor()
        
        assert len(monitor.metrics) == 0
    
    def test_record_operation(self):
        """Test recording operations."""
        monitor = PerformanceMonitor()
        
        # Record successful operation
        monitor.record_operation("test_op", 100.0, success=True)
        
        metrics = monitor.get_metrics("test_op")
        assert "test_op" in metrics
        
        metric = metrics["test_op"]
        assert metric.total_calls == 1
        assert metric.total_duration_ms == 100.0
        assert metric.error_count == 0
        assert metric.average_duration_ms == 100.0
        assert metric.error_rate == 0.0
    
    def test_record_operation_with_error(self):
        """Test recording operations with errors."""
        monitor = PerformanceMonitor()
        
        # Record failed operation
        monitor.record_operation("test_op", 200.0, success=False)
        
        metrics = monitor.get_metrics("test_op")
        metric = metrics["test_op"]
        
        assert metric.total_calls == 1
        assert metric.error_count == 1
        assert metric.error_rate == 1.0
    
    def test_multiple_operations(self):
        """Test recording multiple operations."""
        monitor = PerformanceMonitor()
        
        # Record multiple operations
        monitor.record_operation("test_op", 100.0, success=True)
        monitor.record_operation("test_op", 200.0, success=True)
        monitor.record_operation("test_op", 150.0, success=False)
        
        metrics = monitor.get_metrics("test_op")
        metric = metrics["test_op"]
        
        assert metric.total_calls == 3
        assert metric.total_duration_ms == 450.0
        assert metric.average_duration_ms == 150.0
        assert metric.error_count == 1
        assert metric.error_rate == 1/3
        assert metric.min_duration_ms == 100.0
        assert metric.max_duration_ms == 200.0
    
    def test_get_summary(self):
        """Test getting performance summary."""
        monitor = PerformanceMonitor()
        
        # Record operations for multiple operation types
        monitor.record_operation("fast_op", 50.0, success=True)
        monitor.record_operation("slow_op", 500.0, success=True)
        monitor.record_operation("error_op", 100.0, success=False)
        
        summary = monitor.get_summary()
        
        assert summary['total_operations'] == 3
        assert summary['overall_stats']['total_calls'] == 3
        assert summary['overall_stats']['total_errors'] == 1
        assert 'operations' in summary
        assert 'fast_op' in summary['operations']
        assert 'slow_op' in summary['operations']
        assert 'error_op' in summary['operations']
        
        # Check slowest and fastest operations
        assert summary['overall_stats']['slowest_operation']['name'] == 'slow_op'
        assert summary['overall_stats']['fastest_operation']['name'] == 'fast_op'
    
    def test_reset_metrics(self):
        """Test resetting metrics."""
        monitor = PerformanceMonitor()
        
        # Record some operations
        monitor.record_operation("test_op", 100.0)
        assert len(monitor.get_metrics()) == 1
        
        # Reset all metrics
        monitor.reset_metrics()
        assert len(monitor.get_metrics()) == 0
        
        # Record operations again
        monitor.record_operation("test_op", 100.0)
        monitor.record_operation("other_op", 200.0)
        assert len(monitor.get_metrics()) == 2
        
        # Reset specific metric
        monitor.reset_metrics("test_op")
        metrics = monitor.get_metrics()
        assert "test_op" not in metrics
        assert "other_op" in metrics


class TestDataQualityValidator:
    """Test data quality validator functionality."""
    
    @pytest.mark.asyncio
    async def test_validate_data_quality(self, mock_storage_manager):
        """Test data quality validation."""
        validator = DataQualityValidator(mock_storage_manager)
        
        # Configure mock to return test data
        completed_game = GameRecord(
            game_id="completed_game",
            start_time=datetime.now() - timedelta(hours=2),
            end_time=datetime.now() - timedelta(hours=1),
            players={
                0: PlayerInfo("p1", "model1", "provider1", "agent1"),
                1: PlayerInfo("p2", "model2", "provider2", "agent2")
            },
            outcome=GameOutcome(GameResult.WHITE_WINS, 1, TerminationReason.CHECKMATE)
        )
        
        incomplete_game = GameRecord(
            game_id="incomplete_game",
            start_time=datetime.now() - timedelta(hours=1),
            players={
                0: PlayerInfo("p1", "model1", "provider1", "agent1"),
                1: PlayerInfo("p2", "model2", "provider2", "agent2")
            }
        )
        
        mock_storage_manager.query_games.return_value = [completed_game, incomplete_game]
        
        # Mock moves with some illegal moves and parsing failures
        legal_move = MoveRecord(
            game_id="completed_game",
            move_number=1,
            player=1,
            timestamp=datetime.now(),
            fen_before="start",
            fen_after="after",
            legal_moves=["e4"],
            move_san="e4",
            move_uci="e2e4",
            is_legal=True,
            prompt_text="prompt",
            raw_response="response",
            parsing_success=True
        )
        
        illegal_move = MoveRecord(
            game_id="completed_game",
            move_number=2,
            player=0,
            timestamp=datetime.now(),
            fen_before="start",
            fen_after="after",
            legal_moves=["d4"],
            move_san="invalid",
            move_uci="invalid",
            is_legal=False,
            prompt_text="prompt",
            raw_response="response",
            parsing_success=False
        )
        
        mock_storage_manager.get_moves.return_value = [legal_move, illegal_move]
        
        # Run validation
        metrics = await validator.validate_data_quality()
        
        assert metrics.total_games == 2
        assert metrics.completed_games == 1
        assert metrics.total_moves == 4  # 2 moves per game
        assert metrics.illegal_moves == 2  # 1 illegal move per game
        assert metrics.parsing_failures == 2  # 1 parsing failure per game
        assert metrics.game_completion_rate == 0.5
        assert metrics.move_accuracy_rate == 0.5
        assert metrics.parsing_success_rate == 0.5
    
    @pytest.mark.asyncio
    async def test_validate_game_integrity(self, mock_storage_manager):
        """Test game integrity validation."""
        validator = DataQualityValidator(mock_storage_manager)
        
        # Configure mock for valid game
        valid_game = GameRecord(
            game_id="valid_game",
            start_time=datetime.now() - timedelta(hours=2),
            end_time=datetime.now() - timedelta(hours=1),
            players={
                0: PlayerInfo("p1", "model1", "provider1", "agent1"),
                1: PlayerInfo("p2", "model2", "provider2", "agent2")
            },
            total_moves=2
        )
        
        valid_moves = [
            MoveRecord(
                game_id="valid_game",
                move_number=1,
                player=1,
                timestamp=datetime.now(),
                fen_before="start",
                fen_after="after",
                legal_moves=["e4"],
                move_san="e4",
                move_uci="e2e4",
                is_legal=True,
                prompt_text="prompt",
                raw_response="response"
            ),
            MoveRecord(
                game_id="valid_game",
                move_number=1,
                player=0,
                timestamp=datetime.now(),
                fen_before="start",
                fen_after="after",
                legal_moves=["e5"],
                move_san="e5",
                move_uci="e7e5",
                is_legal=True,
                prompt_text="prompt",
                raw_response="response"
            )
        ]
        
        mock_storage_manager.get_game.return_value = valid_game
        mock_storage_manager.get_moves.return_value = valid_moves
        
        # Run validation
        result = await validator.validate_game_integrity("valid_game")
        
        assert result['game_id'] == "valid_game"
        assert result['is_valid'] is True
        assert len(result['errors']) == 0
        assert result['move_count'] == 2
        assert result['illegal_moves'] == 0
        assert result['parsing_failures'] == 0
    
    @pytest.mark.asyncio
    async def test_validate_game_integrity_invalid_game(self, mock_storage_manager):
        """Test game integrity validation with invalid game."""
        validator = DataQualityValidator(mock_storage_manager)
        
        # Create a valid game but with inconsistent move data
        valid_game = GameRecord(
            game_id="invalid_game",
            start_time=datetime.now(),
            players={
                0: PlayerInfo("p1", "model1", "provider1", "agent1"),
                1: PlayerInfo("p2", "model2", "provider2", "agent2")
            },
            total_moves=2,  # Says 2 moves (expects 4 individual moves)
            end_time=datetime.now(),  # Completed game
            outcome=GameOutcome(GameResult.WHITE_WINS, 1, TerminationReason.CHECKMATE)
        )
        
        # But provide no moves (inconsistent)
        mock_storage_manager.get_game.return_value = valid_game
        mock_storage_manager.get_moves.return_value = []  # No moves despite total_moves=2
        
        # Run validation
        result = await validator.validate_game_integrity("invalid_game")
        
        assert result['game_id'] == "invalid_game"
        assert result['is_valid'] is True  # Basic validation passes
        assert len(result['warnings']) > 0  # But warnings about move count mismatch
        assert "Move count mismatch" in result['warnings'][0]
    
    @pytest.mark.asyncio
    async def test_validate_data_quality_storage_error(self, mock_storage_manager):
        """Test data quality validation with storage error."""
        validator = DataQualityValidator(mock_storage_manager)
        
        # Configure mock to raise exception
        mock_storage_manager.query_games.side_effect = Exception("Storage error")
        
        # Should raise StorageError
        with pytest.raises(StorageError, match="Data quality validation failed"):
            await validator.validate_data_quality()


class TestHealthChecker:
    """Test health checker functionality."""
    
    @pytest.fixture
    def health_checker(self, mock_storage_manager):
        """Create a health checker for testing."""
        performance_monitor = PerformanceMonitor()
        return HealthChecker(mock_storage_manager, performance_monitor)
    
    @pytest.mark.asyncio
    async def test_run_all_health_checks(self, health_checker):
        """Test running all health checks."""
        if PSUTIL_AVAILABLE:
            with patch('game_arena.storage.monitoring.psutil.virtual_memory') as mock_memory, \
                 patch('game_arena.storage.monitoring.psutil.cpu_percent') as mock_cpu, \
                 patch('game_arena.storage.monitoring.psutil.disk_usage') as mock_disk:
                
                # Mock system resource calls
                mock_memory.return_value = MagicMock(percent=50.0, available=2048*1024*1024)
                mock_cpu.return_value = 25.0
                mock_disk.return_value = MagicMock(
                    free=5000*1024*1024,
                    used=1000*1024*1024,
                    total=6000*1024*1024
                )
                
                results = await health_checker.run_all_health_checks()
        else:
            # Run without psutil mocking
            results = await health_checker.run_all_health_checks()
        
        # Check that all expected health checks are present
        expected_checks = [
            'database_connectivity',
            'storage_performance',
            'data_quality',
            'system_resources',
            'storage_capacity',
            'overall'
        ]
        
        for check in expected_checks:
            assert check in results
            assert isinstance(results[check], HealthCheckResult)
            assert results[check].duration_ms >= 0
    
    @pytest.mark.asyncio
    async def test_database_connectivity_check_healthy(self, health_checker, mock_storage_manager):
        """Test database connectivity check when healthy."""
        mock_storage_manager.backend.is_connected = True
        mock_storage_manager.query_games.return_value = []
        
        result = await health_checker._check_database_connectivity()
        
        assert result.name == 'database_connectivity'
        assert result.status == HealthStatus.HEALTHY
        assert result.details['connected'] is True
    
    @pytest.mark.asyncio
    async def test_database_connectivity_check_disconnected(self, health_checker, mock_storage_manager):
        """Test database connectivity check when disconnected."""
        mock_storage_manager.backend.is_connected = False
        
        result = await health_checker._check_database_connectivity()
        
        assert result.name == 'database_connectivity'
        assert result.status == HealthStatus.CRITICAL
        assert result.details['connected'] is False
    
    @pytest.mark.asyncio
    async def test_storage_performance_check(self, health_checker):
        """Test storage performance check."""
        # Add some performance metrics
        health_checker.performance_monitor.record_operation("test_op", 100.0, success=True)
        health_checker.performance_monitor.record_operation("test_op", 200.0, success=True)
        
        result = await health_checker._check_storage_performance()
        
        assert result.name == 'storage_performance'
        assert result.status == HealthStatus.HEALTHY
        assert 'overall_stats' in result.details
    
    @pytest.mark.asyncio
    async def test_storage_performance_check_high_error_rate(self, health_checker):
        """Test storage performance check with high error rate."""
        # Add operations with high error rate
        for _ in range(10):
            health_checker.performance_monitor.record_operation("error_op", 100.0, success=False)
        
        result = await health_checker._check_storage_performance()
        
        assert result.name == 'storage_performance'
        assert result.status == HealthStatus.WARNING
        assert "High error rate" in result.message
    
    @pytest.mark.asyncio
    async def test_system_resources_check_healthy(self, health_checker):
        """Test system resources check when healthy."""
        if PSUTIL_AVAILABLE:
            with patch('game_arena.storage.monitoring.psutil.virtual_memory') as mock_memory, \
                 patch('game_arena.storage.monitoring.psutil.cpu_percent') as mock_cpu:
                
                mock_memory.return_value = MagicMock(percent=50.0, available=2048*1024*1024)
                mock_cpu.return_value = 25.0
                
                result = await health_checker._check_system_resources()
                
                assert result.name == 'system_resources'
                assert result.status == HealthStatus.HEALTHY
                assert result.details['memory_percent'] == 50.0
                assert result.details['cpu_percent'] == 25.0
        else:
            result = await health_checker._check_system_resources()
            
            assert result.name == 'system_resources'
            assert result.status == HealthStatus.UNKNOWN
            assert result.details['psutil_available'] is False
    
    @pytest.mark.asyncio
    async def test_system_resources_check_high_memory(self, health_checker):
        """Test system resources check with high memory usage."""
        if PSUTIL_AVAILABLE:
            with patch('game_arena.storage.monitoring.psutil.virtual_memory') as mock_memory, \
                 patch('game_arena.storage.monitoring.psutil.cpu_percent') as mock_cpu:
                
                mock_memory.return_value = MagicMock(percent=95.0, available=100*1024*1024)
                mock_cpu.return_value = 25.0
                
                result = await health_checker._check_system_resources()
                
                assert result.name == 'system_resources'
                assert result.status == HealthStatus.WARNING
                assert "High memory usage" in result.message
        else:
            result = await health_checker._check_system_resources()
            
            assert result.name == 'system_resources'
            assert result.status == HealthStatus.UNKNOWN
    
    @pytest.mark.asyncio
    async def test_storage_capacity_check_healthy(self, health_checker):
        """Test storage capacity check when healthy."""
        if PSUTIL_AVAILABLE:
            with patch('game_arena.storage.monitoring.psutil.disk_usage') as mock_disk:
                mock_disk.return_value = MagicMock(
                    free=5000*1024*1024,  # 5GB free
                    used=1000*1024*1024,  # 1GB used
                    total=6000*1024*1024  # 6GB total
                )
                
                result = await health_checker._check_storage_capacity()
                
                assert result.name == 'storage_capacity'
                assert result.status == HealthStatus.HEALTHY
                assert result.details['free_space_mb'] > 1000
        else:
            result = await health_checker._check_storage_capacity()
            
            assert result.name == 'storage_capacity'
            assert result.status == HealthStatus.UNKNOWN
            assert result.details['psutil_available'] is False
    
    @pytest.mark.asyncio
    async def test_storage_capacity_check_low_space(self, health_checker):
        """Test storage capacity check with low disk space."""
        if PSUTIL_AVAILABLE:
            with patch('game_arena.storage.monitoring.psutil.disk_usage') as mock_disk:
                mock_disk.return_value = MagicMock(
                    free=500*1024*1024,   # 500MB free (below threshold)
                    used=5500*1024*1024,  # 5.5GB used
                    total=6000*1024*1024  # 6GB total
                )
                
                result = await health_checker._check_storage_capacity()
                
                assert result.name == 'storage_capacity'
                assert result.status == HealthStatus.CRITICAL
                assert "Low disk space" in result.message
        else:
            result = await health_checker._check_storage_capacity()
            
            assert result.name == 'storage_capacity'
            assert result.status == HealthStatus.UNKNOWN
    
    def test_update_thresholds(self, health_checker):
        """Test updating health check thresholds."""
        new_thresholds = {
            'max_response_time_ms': 10000,
            'max_error_rate': 0.1
        }
        
        health_checker.update_thresholds(new_thresholds)
        
        assert health_checker.thresholds['max_response_time_ms'] == 10000
        assert health_checker.thresholds['max_error_rate'] == 0.1


class TestStorageMonitor:
    """Test storage monitor functionality."""
    
    @pytest.fixture
    def storage_monitor(self, mock_storage_manager):
        """Create a storage monitor for testing."""
        return StorageMonitor(mock_storage_manager)
    
    @pytest.mark.asyncio
    async def test_storage_monitor_creation(self, storage_monitor):
        """Test creating a storage monitor."""
        assert storage_monitor.storage_manager is not None
        assert storage_monitor.performance_monitor is not None
        assert storage_monitor.health_checker is not None
        assert storage_monitor.data_quality_validator is not None
        assert storage_monitor._monitoring_active is False
    
    @pytest.mark.asyncio
    async def test_start_stop_monitoring(self, storage_monitor):
        """Test starting and stopping monitoring."""
        # Start monitoring
        await storage_monitor.start_monitoring(interval_seconds=1)
        assert storage_monitor._monitoring_active is True
        assert storage_monitor._monitoring_task is not None
        
        # Give it a moment to start
        await asyncio.sleep(0.1)
        
        # Stop monitoring
        await storage_monitor.stop_monitoring()
        assert storage_monitor._monitoring_active is False
    
    @pytest.mark.asyncio
    async def test_start_monitoring_already_active(self, storage_monitor):
        """Test starting monitoring when already active."""
        # Start monitoring first time
        await storage_monitor.start_monitoring(interval_seconds=1)
        
        # Try to start again - should not create new task
        old_task = storage_monitor._monitoring_task
        await storage_monitor.start_monitoring(interval_seconds=1)
        
        # Should be the same task
        assert storage_monitor._monitoring_task == old_task
        
        # Cleanup
        await storage_monitor.stop_monitoring()
    
    @pytest.mark.asyncio
    async def test_get_monitoring_status(self, storage_monitor):
        """Test getting monitoring status."""
        if PSUTIL_AVAILABLE:
            with patch('game_arena.storage.monitoring.psutil.virtual_memory') as mock_memory, \
                 patch('game_arena.storage.monitoring.psutil.cpu_percent') as mock_cpu, \
                 patch('game_arena.storage.monitoring.psutil.disk_usage') as mock_disk:
                
                # Mock system resource calls
                mock_memory.return_value = MagicMock(percent=50.0, available=2048*1024*1024)
                mock_cpu.return_value = 25.0
                mock_disk.return_value = MagicMock(
                    free=5000*1024*1024,
                    used=1000*1024*1024,
                    total=6000*1024*1024
                )
                
                status = await storage_monitor.get_monitoring_status()
        else:
            # Run without psutil mocking
            status = await storage_monitor.get_monitoring_status()
        
        assert 'monitoring_active' in status
        assert 'monitoring_interval_seconds' in status
        assert 'timestamp' in status
        assert 'health_checks' in status
        assert 'performance_metrics' in status
        assert 'data_quality' in status
        
        # Check health checks structure
        assert 'overall' in status['health_checks']
        assert 'database_connectivity' in status['health_checks']
        
        # Check that each health check has required fields
        for check_name, check_data in status['health_checks'].items():
            assert 'status' in check_data
            assert 'message' in check_data
            assert 'duration_ms' in check_data
    
    def test_record_operation(self, storage_monitor):
        """Test recording operations."""
        storage_monitor.record_operation("test_op", 100.0, success=True)
        
        metrics = storage_monitor.performance_monitor.get_metrics("test_op")
        assert "test_op" in metrics
        assert metrics["test_op"].total_calls == 1
    
    @pytest.mark.asyncio
    async def test_run_health_check_specific(self, storage_monitor):
        """Test running a specific health check."""
        if PSUTIL_AVAILABLE:
            with patch('game_arena.storage.monitoring.psutil.virtual_memory') as mock_memory, \
                 patch('game_arena.storage.monitoring.psutil.cpu_percent') as mock_cpu, \
                 patch('game_arena.storage.monitoring.psutil.disk_usage') as mock_disk:
                
                # Mock system resource calls
                mock_memory.return_value = MagicMock(percent=50.0, available=2048*1024*1024)
                mock_cpu.return_value = 25.0
                mock_disk.return_value = MagicMock(
                    free=5000*1024*1024,
                    used=1000*1024*1024,
                    total=6000*1024*1024
                )
                
                # Run specific health check
                results = await storage_monitor.run_health_check("database_connectivity")
        else:
            # Run without psutil mocking
            results = await storage_monitor.run_health_check("database_connectivity")
        
        assert len(results) == 1
        assert "database_connectivity" in results
        assert isinstance(results["database_connectivity"], HealthCheckResult)
    
    @pytest.mark.asyncio
    async def test_run_health_check_unknown(self, storage_monitor):
        """Test running an unknown health check."""
        with pytest.raises(ValueError, match="Unknown health check"):
            await storage_monitor.run_health_check("unknown_check")
    
    @pytest.mark.asyncio
    async def test_get_monitoring_status_error(self, storage_monitor, mock_storage_manager):
        """Test getting monitoring status with error."""
        # Configure mock to raise exception
        mock_storage_manager.query_games.side_effect = Exception("Storage error")
        
        with pytest.raises(StorageError, match="Monitoring status retrieval failed"):
            await storage_monitor.get_monitoring_status()


if __name__ == "__main__":
    pytest.main([__file__])