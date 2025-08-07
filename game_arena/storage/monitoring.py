"""
Monitoring and health check system for Game Arena storage.

This module provides storage performance monitoring, data quality validation checks,
health check endpoints, and comprehensive monitoring features for the storage system.
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum
import threading

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    psutil = None

from .models import GameRecord, MoveRecord, PlayerStats
from .manager import StorageManager
from .exceptions import StorageError


logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health check status levels."""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass
class HealthCheckResult:
    """Result of a health check."""
    name: str
    status: HealthStatus
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    duration_ms: float = 0.0


@dataclass
class PerformanceMetrics:
    """Performance metrics for storage operations."""
    operation_name: str
    total_calls: int = 0
    total_duration_ms: float = 0.0
    min_duration_ms: float = float('inf')
    max_duration_ms: float = 0.0
    error_count: int = 0
    last_call_timestamp: Optional[datetime] = None
    
    @property
    def average_duration_ms(self) -> float:
        """Calculate average duration."""
        if self.total_calls == 0:
            return 0.0
        return self.total_duration_ms / self.total_calls
    
    @property
    def error_rate(self) -> float:
        """Calculate error rate."""
        if self.total_calls == 0:
            return 0.0
        return self.error_count / self.total_calls
    
    @property
    def calls_per_minute(self) -> float:
        """Calculate calls per minute (last hour)."""
        if not self.last_call_timestamp:
            return 0.0
        
        time_diff = datetime.now() - self.last_call_timestamp
        if time_diff.total_seconds() < 60:
            return self.total_calls  # Less than a minute, return total
        
        minutes = time_diff.total_seconds() / 60
        return self.total_calls / minutes


@dataclass
class DataQualityMetrics:
    """Data quality metrics."""
    total_games: int = 0
    completed_games: int = 0
    games_with_errors: int = 0
    total_moves: int = 0
    illegal_moves: int = 0
    parsing_failures: int = 0
    orphaned_moves: int = 0  # Moves without corresponding games
    duplicate_games: int = 0
    last_updated: datetime = field(default_factory=datetime.now)
    
    @property
    def game_completion_rate(self) -> float:
        """Calculate game completion rate."""
        if self.total_games == 0:
            return 0.0
        return self.completed_games / self.total_games
    
    @property
    def move_accuracy_rate(self) -> float:
        """Calculate move accuracy rate."""
        if self.total_moves == 0:
            return 0.0
        return (self.total_moves - self.illegal_moves) / self.total_moves
    
    @property
    def parsing_success_rate(self) -> float:
        """Calculate parsing success rate."""
        if self.total_moves == 0:
            return 0.0
        return (self.total_moves - self.parsing_failures) / self.total_moves


class PerformanceMonitor:
    """
    Monitors storage performance and tracks metrics.
    
    Provides performance monitoring, timing measurements, and
    performance analytics for storage operations.
    """
    
    def __init__(self):
        """Initialize the performance monitor."""
        self.metrics: Dict[str, PerformanceMetrics] = {}
        self._lock = threading.Lock()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def record_operation(self, operation_name: str, duration_ms: float, success: bool = True) -> None:
        """
        Record a storage operation for performance tracking.
        
        Args:
            operation_name: Name of the operation
            duration_ms: Duration in milliseconds
            success: Whether the operation was successful
        """
        with self._lock:
            if operation_name not in self.metrics:
                self.metrics[operation_name] = PerformanceMetrics(operation_name)
            
            metric = self.metrics[operation_name]
            metric.total_calls += 1
            metric.total_duration_ms += duration_ms
            metric.min_duration_ms = min(metric.min_duration_ms, duration_ms)
            metric.max_duration_ms = max(metric.max_duration_ms, duration_ms)
            metric.last_call_timestamp = datetime.now()
            
            if not success:
                metric.error_count += 1
    
    def get_metrics(self, operation_name: Optional[str] = None) -> Dict[str, PerformanceMetrics]:
        """
        Get performance metrics.
        
        Args:
            operation_name: Specific operation to get metrics for, or None for all
            
        Returns:
            Dictionary of performance metrics
        """
        with self._lock:
            if operation_name:
                return {operation_name: self.metrics.get(operation_name, PerformanceMetrics(operation_name))}
            return self.metrics.copy()
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get a summary of all performance metrics.
        
        Returns:
            Dictionary containing performance summary
        """
        with self._lock:
            summary = {
                'total_operations': len(self.metrics),
                'operations': {},
                'overall_stats': {
                    'total_calls': 0,
                    'total_errors': 0,
                    'average_duration_ms': 0.0,
                    'slowest_operation': None,
                    'fastest_operation': None
                }
            }
            
            if not self.metrics:
                return summary
            
            total_calls = sum(m.total_calls for m in self.metrics.values())
            total_errors = sum(m.error_count for m in self.metrics.values())
            total_duration = sum(m.total_duration_ms for m in self.metrics.values())
            
            summary['overall_stats']['total_calls'] = total_calls
            summary['overall_stats']['total_errors'] = total_errors
            summary['overall_stats']['average_duration_ms'] = total_duration / total_calls if total_calls > 0 else 0.0
            
            # Find slowest and fastest operations
            slowest = max(self.metrics.values(), key=lambda m: m.average_duration_ms)
            fastest = min(self.metrics.values(), key=lambda m: m.average_duration_ms)
            
            summary['overall_stats']['slowest_operation'] = {
                'name': slowest.operation_name,
                'average_duration_ms': slowest.average_duration_ms
            }
            summary['overall_stats']['fastest_operation'] = {
                'name': fastest.operation_name,
                'average_duration_ms': fastest.average_duration_ms
            }
            
            # Add individual operation summaries
            for name, metric in self.metrics.items():
                summary['operations'][name] = {
                    'total_calls': metric.total_calls,
                    'average_duration_ms': metric.average_duration_ms,
                    'error_rate': metric.error_rate,
                    'calls_per_minute': metric.calls_per_minute
                }
            
            return summary
    
    def reset_metrics(self, operation_name: Optional[str] = None) -> None:
        """
        Reset performance metrics.
        
        Args:
            operation_name: Specific operation to reset, or None for all
        """
        with self._lock:
            if operation_name:
                if operation_name in self.metrics:
                    del self.metrics[operation_name]
            else:
                self.metrics.clear()
        
        self.logger.info(f"Reset performance metrics for {operation_name or 'all operations'}")


class DataQualityValidator:
    """
    Validates data quality and integrity in the storage system.
    
    Provides data quality validation checks, integrity verification,
    and data consistency monitoring.
    """
    
    def __init__(self, storage_manager: StorageManager):
        """Initialize the data quality validator."""
        self.storage_manager = storage_manager
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    async def validate_data_quality(self) -> DataQualityMetrics:
        """
        Perform comprehensive data quality validation.
        
        Returns:
            Data quality metrics
            
        Raises:
            StorageError: If validation fails
        """
        try:
            self.logger.info("Starting data quality validation")
            
            metrics = DataQualityMetrics()
            
            # Get all games
            all_games = await self.storage_manager.query_games({})
            metrics.total_games = len(all_games)
            
            # Analyze games
            for game in all_games:
                if game.is_completed:
                    metrics.completed_games += 1
                
                # Check for games with errors (basic validation)
                try:
                    # Validate game data integrity
                    if not game.game_id or not game.players:
                        metrics.games_with_errors += 1
                        continue
                    
                    # Get moves for this game
                    moves = await self.storage_manager.get_moves(game.game_id)
                    
                    for move in moves:
                        metrics.total_moves += 1
                        
                        if not move.is_legal:
                            metrics.illegal_moves += 1
                        
                        if not move.parsing_success:
                            metrics.parsing_failures += 1
                
                except Exception as e:
                    self.logger.warning(f"Error analyzing game {game.game_id}: {e}")
                    metrics.games_with_errors += 1
            
            # Check for orphaned moves (moves without corresponding games)
            metrics.orphaned_moves = await self._count_orphaned_moves(all_games)
            
            # Check for duplicate games
            metrics.duplicate_games = await self._count_duplicate_games(all_games)
            
            metrics.last_updated = datetime.now()
            
            self.logger.info(f"Data quality validation completed: {metrics.total_games} games, "
                           f"{metrics.total_moves} moves, {metrics.games_with_errors} games with errors")
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Data quality validation failed: {e}")
            raise StorageError(f"Data quality validation failed: {e}") from e
    
    async def _count_orphaned_moves(self, games: List[GameRecord]) -> int:
        """Count moves that don't have corresponding games."""
        # This is a simplified implementation
        # In a real system, you might query the database directly for better performance
        game_ids = {game.game_id for game in games}
        orphaned_count = 0
        
        # This would need to be implemented based on the specific backend
        # For now, we'll return 0 as a placeholder
        return orphaned_count
    
    async def _count_duplicate_games(self, games: List[GameRecord]) -> int:
        """Count duplicate games based on game_id."""
        game_ids = [game.game_id for game in games]
        unique_ids = set(game_ids)
        return len(game_ids) - len(unique_ids)
    
    async def validate_game_integrity(self, game_id: str) -> Dict[str, Any]:
        """
        Validate the integrity of a specific game.
        
        Args:
            game_id: ID of the game to validate
            
        Returns:
            Dictionary containing validation results
            
        Raises:
            StorageError: If validation fails
        """
        try:
            validation_result = {
                'game_id': game_id,
                'is_valid': True,
                'errors': [],
                'warnings': [],
                'move_count': 0,
                'illegal_moves': 0,
                'parsing_failures': 0
            }
            
            # Get game record
            try:
                game = await self.storage_manager.get_game(game_id)
            except Exception as e:
                validation_result['is_valid'] = False
                validation_result['errors'].append(f"Game not found: {e}")
                return validation_result
            
            # Validate game data
            if not game.players or len(game.players) != 2:
                validation_result['errors'].append("Game must have exactly 2 players")
                validation_result['is_valid'] = False
            
            if game.total_moves < 0:
                validation_result['errors'].append("Total moves cannot be negative")
                validation_result['is_valid'] = False
            
            # Get and validate moves
            moves = await self.storage_manager.get_moves(game_id)
            validation_result['move_count'] = len(moves)
            
            # Check move consistency
            expected_moves = game.total_moves * 2 if game.is_completed else None
            if expected_moves and len(moves) != expected_moves:
                validation_result['warnings'].append(
                    f"Move count mismatch: expected {expected_moves}, found {len(moves)}"
                )
            
            # Validate individual moves
            for i, move in enumerate(moves):
                if not move.is_legal:
                    validation_result['illegal_moves'] += 1
                
                if not move.parsing_success:
                    validation_result['parsing_failures'] += 1
                
                # Check move sequence
                if move.move_number != (i // 2) + 1:
                    validation_result['warnings'].append(
                        f"Move sequence issue at index {i}: expected move {(i // 2) + 1}, got {move.move_number}"
                    )
            
            return validation_result
            
        except Exception as e:
            self.logger.error(f"Game integrity validation failed for {game_id}: {e}")
            raise StorageError(f"Game integrity validation failed: {e}") from e


class HealthChecker:
    """
    Provides health check functionality for the storage system.
    
    Implements various health checks including database connectivity,
    performance thresholds, data integrity, and system resources.
    """
    
    def __init__(self, storage_manager: StorageManager, performance_monitor: PerformanceMonitor):
        """Initialize the health checker."""
        self.storage_manager = storage_manager
        self.performance_monitor = performance_monitor
        self.data_quality_validator = DataQualityValidator(storage_manager)
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Health check thresholds
        self.thresholds = {
            'max_response_time_ms': 5000,
            'max_error_rate': 0.05,  # 5%
            'min_disk_space_mb': 1000,
            'max_memory_usage_percent': 80,
            'min_game_completion_rate': 0.8,  # 80%
            'max_illegal_move_rate': 0.1  # 10%
        }
    
    async def run_all_health_checks(self) -> Dict[str, HealthCheckResult]:
        """
        Run all health checks and return results.
        
        Returns:
            Dictionary of health check results
        """
        self.logger.info("Running comprehensive health checks")
        
        health_checks = {
            'database_connectivity': self._check_database_connectivity,
            'storage_performance': self._check_storage_performance,
            'data_quality': self._check_data_quality,
            'system_resources': self._check_system_resources,
            'storage_capacity': self._check_storage_capacity
        }
        
        results = {}
        
        for check_name, check_func in health_checks.items():
            try:
                start_time = time.time()
                result = await check_func()
                duration_ms = (time.time() - start_time) * 1000
                result.duration_ms = duration_ms
                results[check_name] = result
            except Exception as e:
                self.logger.error(f"Health check {check_name} failed: {e}")
                results[check_name] = HealthCheckResult(
                    name=check_name,
                    status=HealthStatus.CRITICAL,
                    message=f"Health check failed: {e}",
                    details={'error': str(e)}
                )
        
        # Determine overall health status
        overall_status = self._determine_overall_status(results)
        results['overall'] = HealthCheckResult(
            name='overall',
            status=overall_status,
            message=f"Overall system status: {overall_status.value}",
            details={'individual_checks': len(results)}
        )
        
        self.logger.info(f"Health checks completed with overall status: {overall_status.value}")
        return results
    
    async def _check_database_connectivity(self) -> HealthCheckResult:
        """Check database connectivity and basic operations."""
        try:
            # Test basic connectivity
            if not self.storage_manager.backend.is_connected:
                return HealthCheckResult(
                    name='database_connectivity',
                    status=HealthStatus.CRITICAL,
                    message="Database is not connected",
                    details={'connected': False}
                )
            
            # Test basic query operation
            start_time = time.time()
            games = await self.storage_manager.query_games({}, limit=1)
            query_time_ms = (time.time() - start_time) * 1000
            
            status = HealthStatus.HEALTHY
            message = "Database connectivity is healthy"
            
            if query_time_ms > self.thresholds['max_response_time_ms']:
                status = HealthStatus.WARNING
                message = f"Database response time is slow: {query_time_ms:.1f}ms"
            
            return HealthCheckResult(
                name='database_connectivity',
                status=status,
                message=message,
                details={
                    'connected': True,
                    'query_time_ms': query_time_ms,
                    'test_query_results': len(games)
                }
            )
            
        except Exception as e:
            return HealthCheckResult(
                name='database_connectivity',
                status=HealthStatus.CRITICAL,
                message=f"Database connectivity check failed: {e}",
                details={'error': str(e)}
            )
    
    async def _check_storage_performance(self) -> HealthCheckResult:
        """Check storage performance metrics."""
        try:
            metrics_summary = self.performance_monitor.get_summary()
            
            status = HealthStatus.HEALTHY
            message = "Storage performance is healthy"
            issues = []
            
            # Check overall error rate
            total_calls = metrics_summary['overall_stats']['total_calls']
            total_errors = metrics_summary['overall_stats']['total_errors']
            
            if total_calls > 0:
                error_rate = total_errors / total_calls
                if error_rate > self.thresholds['max_error_rate']:
                    status = HealthStatus.WARNING
                    issues.append(f"High error rate: {error_rate:.2%}")
            
            # Check average response time
            avg_duration = metrics_summary['overall_stats']['average_duration_ms']
            if avg_duration > self.thresholds['max_response_time_ms']:
                status = HealthStatus.WARNING
                issues.append(f"High average response time: {avg_duration:.1f}ms")
            
            # Check for operations with high error rates
            for op_name, op_metrics in metrics_summary['operations'].items():
                if op_metrics['error_rate'] > self.thresholds['max_error_rate']:
                    status = HealthStatus.WARNING
                    issues.append(f"High error rate for {op_name}: {op_metrics['error_rate']:.2%}")
            
            if issues:
                message = f"Storage performance issues detected: {'; '.join(issues)}"
            
            return HealthCheckResult(
                name='storage_performance',
                status=status,
                message=message,
                details=metrics_summary
            )
            
        except Exception as e:
            return HealthCheckResult(
                name='storage_performance',
                status=HealthStatus.CRITICAL,
                message=f"Performance check failed: {e}",
                details={'error': str(e)}
            )
    
    async def _check_data_quality(self) -> HealthCheckResult:
        """Check data quality metrics."""
        try:
            quality_metrics = await self.data_quality_validator.validate_data_quality()
            
            status = HealthStatus.HEALTHY
            message = "Data quality is healthy"
            issues = []
            
            # Check game completion rate
            if quality_metrics.game_completion_rate < self.thresholds['min_game_completion_rate']:
                status = HealthStatus.WARNING
                issues.append(f"Low game completion rate: {quality_metrics.game_completion_rate:.2%}")
            
            # Check illegal move rate
            illegal_move_rate = 1.0 - quality_metrics.move_accuracy_rate
            if illegal_move_rate > self.thresholds['max_illegal_move_rate']:
                status = HealthStatus.WARNING
                issues.append(f"High illegal move rate: {illegal_move_rate:.2%}")
            
            # Check for orphaned moves
            if quality_metrics.orphaned_moves > 0:
                status = HealthStatus.WARNING
                issues.append(f"Found {quality_metrics.orphaned_moves} orphaned moves")
            
            # Check for duplicate games
            if quality_metrics.duplicate_games > 0:
                status = HealthStatus.WARNING
                issues.append(f"Found {quality_metrics.duplicate_games} duplicate games")
            
            if issues:
                message = f"Data quality issues detected: {'; '.join(issues)}"
            
            return HealthCheckResult(
                name='data_quality',
                status=status,
                message=message,
                details={
                    'total_games': quality_metrics.total_games,
                    'completed_games': quality_metrics.completed_games,
                    'completion_rate': quality_metrics.game_completion_rate,
                    'total_moves': quality_metrics.total_moves,
                    'illegal_moves': quality_metrics.illegal_moves,
                    'move_accuracy_rate': quality_metrics.move_accuracy_rate,
                    'parsing_success_rate': quality_metrics.parsing_success_rate,
                    'orphaned_moves': quality_metrics.orphaned_moves,
                    'duplicate_games': quality_metrics.duplicate_games
                }
            )
            
        except Exception as e:
            return HealthCheckResult(
                name='data_quality',
                status=HealthStatus.CRITICAL,
                message=f"Data quality check failed: {e}",
                details={'error': str(e)}
            )
    
    async def _check_system_resources(self) -> HealthCheckResult:
        """Check system resource usage."""
        try:
            if not PSUTIL_AVAILABLE:
                return HealthCheckResult(
                    name='system_resources',
                    status=HealthStatus.UNKNOWN,
                    message="System resource monitoring unavailable (psutil not installed)",
                    details={'psutil_available': False}
                )
            
            # Get memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # Get CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            status = HealthStatus.HEALTHY
            message = "System resources are healthy"
            issues = []
            
            # Check memory usage
            if memory_percent > self.thresholds['max_memory_usage_percent']:
                status = HealthStatus.WARNING
                issues.append(f"High memory usage: {memory_percent:.1f}%")
            
            # Check CPU usage (warning if consistently high)
            if cpu_percent > 90:
                status = HealthStatus.WARNING
                issues.append(f"High CPU usage: {cpu_percent:.1f}%")
            
            if issues:
                message = f"System resource issues detected: {'; '.join(issues)}"
            
            return HealthCheckResult(
                name='system_resources',
                status=status,
                message=message,
                details={
                    'memory_percent': memory_percent,
                    'memory_available_mb': memory.available / (1024 * 1024),
                    'cpu_percent': cpu_percent,
                    'psutil_available': True
                }
            )
            
        except Exception as e:
            return HealthCheckResult(
                name='system_resources',
                status=HealthStatus.CRITICAL,
                message=f"System resource check failed: {e}",
                details={'error': str(e)}
            )
    
    async def _check_storage_capacity(self) -> HealthCheckResult:
        """Check storage disk capacity."""
        try:
            if not PSUTIL_AVAILABLE:
                return HealthCheckResult(
                    name='storage_capacity',
                    status=HealthStatus.UNKNOWN,
                    message="Storage capacity monitoring unavailable (psutil not installed)",
                    details={'psutil_available': False}
                )
            
            # Get disk usage for current directory
            disk_usage = psutil.disk_usage('.')
            free_space_mb = disk_usage.free / (1024 * 1024)
            used_percent = (disk_usage.used / disk_usage.total) * 100
            
            status = HealthStatus.HEALTHY
            message = "Storage capacity is healthy"
            
            if free_space_mb < self.thresholds['min_disk_space_mb']:
                status = HealthStatus.CRITICAL
                message = f"Low disk space: {free_space_mb:.1f}MB remaining"
            elif used_percent > 90:
                status = HealthStatus.WARNING
                message = f"High disk usage: {used_percent:.1f}% used"
            
            return HealthCheckResult(
                name='storage_capacity',
                status=status,
                message=message,
                details={
                    'free_space_mb': free_space_mb,
                    'used_percent': used_percent,
                    'total_space_mb': disk_usage.total / (1024 * 1024),
                    'psutil_available': True
                }
            )
            
        except Exception as e:
            return HealthCheckResult(
                name='storage_capacity',
                status=HealthStatus.CRITICAL,
                message=f"Storage capacity check failed: {e}",
                details={'error': str(e)}
            )
    
    def _determine_overall_status(self, results: Dict[str, HealthCheckResult]) -> HealthStatus:
        """Determine overall health status from individual check results."""
        if not results:
            return HealthStatus.UNKNOWN
        
        statuses = [result.status for result in results.values()]
        
        if HealthStatus.CRITICAL in statuses:
            return HealthStatus.CRITICAL
        elif HealthStatus.WARNING in statuses:
            return HealthStatus.WARNING
        elif all(status == HealthStatus.HEALTHY for status in statuses):
            return HealthStatus.HEALTHY
        else:
            return HealthStatus.UNKNOWN
    
    def update_thresholds(self, new_thresholds: Dict[str, Any]) -> None:
        """
        Update health check thresholds.
        
        Args:
            new_thresholds: Dictionary of new threshold values
        """
        self.thresholds.update(new_thresholds)
        self.logger.info(f"Updated health check thresholds: {new_thresholds}")


class StorageMonitor:
    """
    Main monitoring system that coordinates all monitoring components.
    
    Provides a unified interface for storage monitoring, health checks,
    performance tracking, and data quality validation.
    """
    
    def __init__(self, storage_manager: StorageManager):
        """Initialize the storage monitor."""
        self.storage_manager = storage_manager
        self.performance_monitor = PerformanceMonitor()
        self.health_checker = HealthChecker(storage_manager, self.performance_monitor)
        self.data_quality_validator = DataQualityValidator(storage_manager)
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Monitoring state
        self._monitoring_active = False
        self._monitoring_task: Optional[asyncio.Task] = None
        self._monitoring_interval = 300  # 5 minutes
    
    async def start_monitoring(self, interval_seconds: int = 300) -> None:
        """
        Start continuous monitoring.
        
        Args:
            interval_seconds: Monitoring interval in seconds
        """
        if self._monitoring_active:
            self.logger.warning("Monitoring is already active")
            return
        
        self._monitoring_interval = interval_seconds
        self._monitoring_active = True
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        
        self.logger.info(f"Started storage monitoring with {interval_seconds}s interval")
    
    async def stop_monitoring(self) -> None:
        """Stop continuous monitoring."""
        self._monitoring_active = False
        
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("Stopped storage monitoring")
    
    async def _monitoring_loop(self) -> None:
        """Internal monitoring loop."""
        while self._monitoring_active:
            try:
                # Run health checks
                health_results = await self.health_checker.run_all_health_checks()
                
                # Log critical issues
                for check_name, result in health_results.items():
                    if result.status == HealthStatus.CRITICAL:
                        self.logger.error(f"Critical health issue in {check_name}: {result.message}")
                    elif result.status == HealthStatus.WARNING:
                        self.logger.warning(f"Health warning in {check_name}: {result.message}")
                
                # Wait for next monitoring cycle
                await asyncio.sleep(self._monitoring_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying
    
    async def get_monitoring_status(self) -> Dict[str, Any]:
        """
        Get current monitoring status and metrics.
        
        Returns:
            Dictionary containing monitoring status and metrics
        """
        try:
            # Get health check results
            health_results = await self.health_checker.run_all_health_checks()
            
            # Get performance metrics
            performance_summary = self.performance_monitor.get_summary()
            
            # Get data quality metrics
            data_quality = await self.data_quality_validator.validate_data_quality()
            
            return {
                'monitoring_active': self._monitoring_active,
                'monitoring_interval_seconds': self._monitoring_interval,
                'timestamp': datetime.now().isoformat(),
                'health_checks': {
                    name: {
                        'status': result.status.value,
                        'message': result.message,
                        'duration_ms': result.duration_ms
                    }
                    for name, result in health_results.items()
                },
                'performance_metrics': performance_summary,
                'data_quality': {
                    'total_games': data_quality.total_games,
                    'completed_games': data_quality.completed_games,
                    'completion_rate': data_quality.game_completion_rate,
                    'total_moves': data_quality.total_moves,
                    'move_accuracy_rate': data_quality.move_accuracy_rate,
                    'parsing_success_rate': data_quality.parsing_success_rate
                }
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get monitoring status: {e}")
            raise StorageError(f"Monitoring status retrieval failed: {e}") from e
    
    def record_operation(self, operation_name: str, duration_ms: float, success: bool = True) -> None:
        """
        Record a storage operation for monitoring.
        
        Args:
            operation_name: Name of the operation
            duration_ms: Duration in milliseconds
            success: Whether the operation was successful
        """
        self.performance_monitor.record_operation(operation_name, duration_ms, success)
    
    async def run_health_check(self, check_name: Optional[str] = None) -> Dict[str, HealthCheckResult]:
        """
        Run health checks on demand.
        
        Args:
            check_name: Specific check to run, or None for all checks
            
        Returns:
            Dictionary of health check results
        """
        if check_name:
            # Run specific health check
            all_results = await self.health_checker.run_all_health_checks()
            if check_name in all_results:
                return {check_name: all_results[check_name]}
            else:
                raise ValueError(f"Unknown health check: {check_name}")
        else:
            # Run all health checks
            return await self.health_checker.run_all_health_checks()