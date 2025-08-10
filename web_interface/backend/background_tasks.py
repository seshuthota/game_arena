"""
Background processing tasks for cache maintenance, optimization, and system management.

This module provides background task management for automatic cache maintenance,
performance optimization, data cleanup, and system health monitoring.
"""

import asyncio
import logging
import time
import threading
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import json

from statistics_cache import get_statistics_cache
from batch_statistics_processor import get_batch_processor
from cache_manager import get_cache_manager
from performance_monitor import get_performance_monitor, AlertSeverity

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    """Background task status."""
    PENDING = "pending"
    RUNNING = "running" 
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SCHEDULED = "scheduled"


class TaskPriority(int, Enum):
    """Background task priority levels."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class BackgroundTask:
    """Background task definition."""
    task_id: str
    name: str
    description: str
    function: Callable
    priority: TaskPriority
    schedule_interval: Optional[timedelta] = None  # None for one-time tasks
    next_run: Optional[datetime] = None
    last_run: Optional[datetime] = None
    status: TaskStatus = TaskStatus.PENDING
    error_message: Optional[str] = None
    execution_count: int = 0
    max_retries: int = 3
    retry_count: int = 0
    timeout_seconds: int = 300  # 5 minutes default
    enabled: bool = True


class BackgroundTaskManager:
    """
    Manager for background processing tasks.
    
    Handles scheduling, execution, monitoring, and maintenance of background tasks
    including cache optimization, data cleanup, and system monitoring.
    """
    
    def __init__(
        self,
        max_concurrent_tasks: int = 3,
        task_check_interval: int = 30  # seconds
    ):
        self.max_concurrent_tasks = max_concurrent_tasks
        self.task_check_interval = task_check_interval
        
        # Task management
        self._tasks: Dict[str, BackgroundTask] = {}
        self._running_tasks: Dict[str, asyncio.Task] = {}
        self._task_lock = threading.RLock()
        
        # Scheduler state
        self._scheduler_active = False
        self._scheduler_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()
        
        # Performance tracking
        self._task_stats = {
            'total_tasks_executed': 0,
            'successful_executions': 0,
            'failed_executions': 0,
            'total_execution_time': 0.0,
            'average_execution_time': 0.0,
            'scheduler_uptime': 0.0
        }
        
        self._start_time = datetime.now()
        
        # Register default tasks
        self._register_default_tasks()
        
        logger.info(f"BackgroundTaskManager initialized with {max_concurrent_tasks} concurrent task limit")
    
    def _register_default_tasks(self) -> None:
        """Register default system tasks."""
        
        # Cache cleanup task - runs every 5 minutes
        self.register_task(BackgroundTask(
            task_id="cache_cleanup",
            name="Cache Cleanup",
            description="Clean up expired cache entries and optimize memory usage",
            function=self._cache_cleanup_task,
            priority=TaskPriority.NORMAL,
            schedule_interval=timedelta(minutes=5),
            timeout_seconds=120
        ))
        
        # Cache warming task - runs every 15 minutes
        self.register_task(BackgroundTask(
            task_id="cache_warming",
            name="Cache Warming",
            description="Pre-warm cache with frequently accessed data",
            function=self._cache_warming_task,
            priority=TaskPriority.LOW,
            schedule_interval=timedelta(minutes=15),
            timeout_seconds=300
        ))
        
        # Performance monitoring task - runs every 30 seconds
        self.register_task(BackgroundTask(
            task_id="performance_monitoring",
            name="Performance Monitoring",
            description="Collect and analyze system performance metrics",
            function=self._performance_monitoring_task,
            priority=TaskPriority.HIGH,
            schedule_interval=timedelta(seconds=30),
            timeout_seconds=60
        ))
        
        # Cache optimization task - runs every hour
        self.register_task(BackgroundTask(
            task_id="cache_optimization",
            name="Cache Optimization",
            description="Analyze and optimize cache performance",
            function=self._cache_optimization_task,
            priority=TaskPriority.NORMAL,
            schedule_interval=timedelta(hours=1),
            timeout_seconds=300
        ))
        
        # System health check - runs every 2 minutes
        self.register_task(BackgroundTask(
            task_id="health_check",
            name="System Health Check",
            description="Monitor system health and generate alerts",
            function=self._system_health_check_task,
            priority=TaskPriority.HIGH,
            schedule_interval=timedelta(minutes=2),
            timeout_seconds=60
        ))
        
        # Data cleanup task - runs daily at 2 AM
        self.register_task(BackgroundTask(
            task_id="data_cleanup",
            name="Data Cleanup",
            description="Clean up old logs, metrics, and temporary data",
            function=self._data_cleanup_task,
            priority=TaskPriority.LOW,
            schedule_interval=timedelta(days=1),
            timeout_seconds=600
        ))
        
        # Batch processing optimization - runs every 30 minutes
        self.register_task(BackgroundTask(
            task_id="batch_processing_optimization",
            name="Batch Processing Optimization",
            description="Optimize batch processing performance and clean up old jobs",
            function=self._batch_processing_optimization_task,
            priority=TaskPriority.NORMAL,
            schedule_interval=timedelta(minutes=30),
            timeout_seconds=180
        ))
    
    def register_task(self, task: BackgroundTask) -> None:
        """Register a background task."""
        with self._task_lock:
            if task.next_run is None and task.schedule_interval:
                task.next_run = datetime.now() + task.schedule_interval
            
            self._tasks[task.task_id] = task
            logger.info(f"Registered background task: {task.name} ({task.task_id})")
    
    def unregister_task(self, task_id: str) -> bool:
        """Unregister a background task."""
        with self._task_lock:
            if task_id in self._tasks:
                # Cancel if currently running
                if task_id in self._running_tasks:
                    self._running_tasks[task_id].cancel()
                    del self._running_tasks[task_id]
                
                del self._tasks[task_id]
                logger.info(f"Unregistered background task: {task_id}")
                return True
            return False
    
    def start_scheduler(self) -> None:
        """Start the background task scheduler."""
        if self._scheduler_active:
            logger.warning("Background task scheduler already active")
            return
        
        self._scheduler_active = True
        self._shutdown_event.clear()
        
        # Start scheduler in asyncio event loop
        loop = asyncio.get_event_loop()
        self._scheduler_task = loop.create_task(self._scheduler_loop())
        
        logger.info("Background task scheduler started")
    
    def stop_scheduler(self) -> None:
        """Stop the background task scheduler."""
        if not self._scheduler_active:
            return
        
        self._scheduler_active = False
        self._shutdown_event.set()
        
        # Cancel all running tasks
        with self._task_lock:
            for task_id, running_task in self._running_tasks.items():
                running_task.cancel()
                logger.info(f"Cancelled running task: {task_id}")
            self._running_tasks.clear()
        
        # Cancel scheduler task
        if self._scheduler_task:
            self._scheduler_task.cancel()
        
        logger.info("Background task scheduler stopped")
    
    async def _scheduler_loop(self) -> None:
        """Main scheduler loop."""
        logger.info("Background task scheduler loop started")
        
        while self._scheduler_active:
            try:
                current_time = datetime.now()
                
                # Check for tasks that need to run
                tasks_to_run = []
                
                with self._task_lock:
                    for task_id, task in self._tasks.items():
                        if (task.enabled and 
                            task.status != TaskStatus.RUNNING and
                            task_id not in self._running_tasks and
                            task.next_run and
                            current_time >= task.next_run):
                            tasks_to_run.append(task)
                
                # Sort by priority (highest first)
                tasks_to_run.sort(key=lambda t: t.priority.value, reverse=True)
                
                # Execute tasks up to concurrent limit
                for task in tasks_to_run[:self.max_concurrent_tasks - len(self._running_tasks)]:
                    await self._execute_task(task)
                
                # Clean up completed tasks
                await self._cleanup_completed_tasks()
                
                # Wait before next check
                await asyncio.sleep(self.task_check_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                await asyncio.sleep(self.task_check_interval)
        
        logger.info("Background task scheduler loop stopped")
    
    async def _execute_task(self, task: BackgroundTask) -> None:
        """Execute a background task."""
        with self._task_lock:
            if task.task_id in self._running_tasks:
                return  # Already running
            
            task.status = TaskStatus.RUNNING
            task.execution_count += 1
        
        logger.debug(f"Starting background task: {task.name}")
        
        async def task_wrapper():
            start_time = time.time()
            try:
                # Execute the task function
                if asyncio.iscoroutinefunction(task.function):
                    await task.function()
                else:
                    # Run sync function in thread pool
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(None, task.function)
                
                # Task completed successfully
                execution_time = time.time() - start_time
                
                with self._task_lock:
                    task.status = TaskStatus.COMPLETED
                    task.last_run = datetime.now()
                    task.error_message = None
                    task.retry_count = 0
                    
                    # Schedule next run if recurring
                    if task.schedule_interval:
                        task.next_run = datetime.now() + task.schedule_interval
                    
                    # Update stats
                    self._task_stats['total_tasks_executed'] += 1
                    self._task_stats['successful_executions'] += 1
                    self._task_stats['total_execution_time'] += execution_time
                    self._task_stats['average_execution_time'] = (
                        self._task_stats['total_execution_time'] / 
                        self._task_stats['total_tasks_executed']
                    )
                
                logger.debug(f"Completed background task: {task.name} in {execution_time:.2f}s")
                
            except Exception as e:
                execution_time = time.time() - start_time
                
                with self._task_lock:
                    task.retry_count += 1
                    task.error_message = str(e)
                    
                    if task.retry_count <= task.max_retries:
                        # Retry with exponential backoff
                        retry_delay = min(300, 30 * (2 ** (task.retry_count - 1)))  # Max 5 minutes
                        task.next_run = datetime.now() + timedelta(seconds=retry_delay)
                        task.status = TaskStatus.SCHEDULED
                        logger.warning(f"Task {task.name} failed (attempt {task.retry_count}/{task.max_retries}), "
                                     f"retrying in {retry_delay}s: {e}")
                    else:
                        # Max retries exceeded
                        task.status = TaskStatus.FAILED
                        logger.error(f"Task {task.name} failed permanently after {task.retry_count} attempts: {e}")
                    
                    # Update stats
                    self._task_stats['total_tasks_executed'] += 1
                    self._task_stats['failed_executions'] += 1
                    self._task_stats['total_execution_time'] += execution_time
                    self._task_stats['average_execution_time'] = (
                        self._task_stats['total_execution_time'] / 
                        self._task_stats['total_tasks_executed']
                    )
        
        # Start the task with timeout
        running_task = asyncio.create_task(asyncio.wait_for(task_wrapper(), timeout=task.timeout_seconds))
        
        with self._task_lock:
            self._running_tasks[task.task_id] = running_task
    
    async def _cleanup_completed_tasks(self) -> None:
        """Clean up completed or failed task references."""
        completed_task_ids = []
        
        with self._task_lock:
            for task_id, running_task in self._running_tasks.items():
                if running_task.done():
                    completed_task_ids.append(task_id)
            
            for task_id in completed_task_ids:
                del self._running_tasks[task_id]
    
    # Default task implementations
    
    async def _cache_cleanup_task(self) -> None:
        """Clean up expired cache entries."""
        cache = get_statistics_cache()
        
        # Get initial stats
        initial_stats = cache.get_stats()
        initial_size = initial_stats['cache_size']
        
        # Trigger cleanup (this is normally done automatically, but we can force it)
        cleaned_count = cache._cleanup_expired_entries()
        
        # Get final stats
        final_stats = cache.get_stats()
        final_size = final_stats['cache_size']
        
        logger.info(f"Cache cleanup: removed {cleaned_count} expired entries, "
                   f"cache size: {initial_size} -> {final_size}")
    
    async def _cache_warming_task(self) -> None:
        """Warm cache with frequently accessed data."""
        cache_manager = get_cache_manager()
        
        # Warm popular data
        warmed_count = await cache_manager.warm_popular_data(top_n=50)
        
        logger.info(f"Cache warming: warmed {warmed_count} popular entries")
    
    async def _performance_monitoring_task(self) -> None:
        """Collect performance metrics."""
        performance_monitor = get_performance_monitor()
        
        # The performance monitor automatically collects metrics in its own thread
        # This task can perform additional analysis or trigger actions based on metrics
        
        current_metrics = performance_monitor.get_current_metrics()
        
        # Check for performance issues and log warnings
        if hasattr(performance_monitor, 'MetricType'):
            cache_hit_rate = current_metrics.get(performance_monitor.MetricType.CACHE_HIT_RATE)
            if cache_hit_rate is not None and cache_hit_rate < 50:
                logger.warning(f"Low cache hit rate detected: {cache_hit_rate:.1f}%")
            
            response_time = current_metrics.get(performance_monitor.MetricType.RESPONSE_TIME)
            if response_time is not None and response_time > 1000:  # > 1 second
                logger.warning(f"High response time detected: {response_time:.0f}ms")
    
    async def _cache_optimization_task(self) -> None:
        """Analyze and optimize cache performance."""
        cache_manager = get_cache_manager()
        
        # Generate optimization suggestions
        suggestions = await cache_manager.optimize_cache_performance()
        
        if suggestions:
            high_priority_suggestions = [s for s in suggestions if s.priority >= 3]
            if high_priority_suggestions:
                logger.warning(f"High-priority cache optimization needed: {len(high_priority_suggestions)} suggestions")
                for suggestion in high_priority_suggestions[:3]:  # Log top 3
                    logger.warning(f"  - {suggestion.description}")
        
        logger.info(f"Cache optimization: generated {len(suggestions)} suggestions")
    
    async def _system_health_check_task(self) -> None:
        """Monitor system health and generate alerts."""
        performance_monitor = get_performance_monitor()
        
        # Generate health report
        health_report = performance_monitor.generate_health_report()
        
        # Check for critical alerts
        critical_alerts = [a for a in health_report.alerts if a.severity == AlertSeverity.CRITICAL]
        high_alerts = [a for a in health_report.alerts if a.severity == AlertSeverity.HIGH]
        
        if critical_alerts:
            logger.critical(f"CRITICAL system alerts detected: {len(critical_alerts)}")
            for alert in critical_alerts:
                logger.critical(f"  - {alert.message}")
        
        if high_alerts:
            logger.error(f"HIGH severity alerts detected: {len(high_alerts)}")
            for alert in high_alerts[:3]:  # Log top 3
                logger.error(f"  - {alert.message}")
        
        # Log overall health
        if health_report.overall_health_score < 60:
            logger.error(f"System health critical: {health_report.overall_health_score:.1f}/100")
        elif health_report.overall_health_score < 80:
            logger.warning(f"System health degraded: {health_report.overall_health_score:.1f}/100")
    
    async def _data_cleanup_task(self) -> None:
        """Clean up old data and logs."""
        # Clean up cache manager data
        cache_manager = get_cache_manager()
        cleanup_results = cache_manager.cleanup_old_data(max_age_hours=24)
        
        # Clean up batch processor results
        try:
            batch_processor = get_batch_processor(None)  # Will use global instance
            if batch_processor:
                cleaned_jobs = batch_processor.cleanup_old_results(max_age_hours=48)
                logger.info(f"Data cleanup: removed {cleaned_jobs} old batch job results")
        except Exception as e:
            logger.warning(f"Could not clean up batch processor data: {e}")
        
        # Clean up performance monitor data
        performance_monitor = get_performance_monitor()
        performance_stats = performance_monitor.get_performance_stats()
        
        total_cleaned = sum(cleanup_results.values()) if cleanup_results else 0
        logger.info(f"Data cleanup: removed {total_cleaned} old cache management items")
    
    async def _batch_processing_optimization_task(self) -> None:
        """Optimize batch processing performance."""
        try:
            batch_processor = get_batch_processor(None)
            if not batch_processor:
                return
            
            # Get performance metrics
            metrics = batch_processor.get_performance_metrics()
            
            # Log performance summary
            logger.info(f"Batch processing stats: "
                       f"{metrics.get('total_jobs', 0)} jobs, "
                       f"{metrics.get('successful_jobs', 0)} successful, "
                       f"{metrics.get('average_processing_time', 0):.2f}s avg time")
            
            # Clean up old results
            cleaned_count = batch_processor.cleanup_old_results(max_age_hours=24)
            if cleaned_count > 0:
                logger.info(f"Cleaned up {cleaned_count} old batch job results")
        
        except Exception as e:
            logger.warning(f"Batch processing optimization failed: {e}")
    
    # Public API methods
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get status information for a specific task."""
        with self._task_lock:
            if task_id in self._tasks:
                task = self._tasks[task_id]
                return {
                    'task_id': task.task_id,
                    'name': task.name,
                    'description': task.description,
                    'status': task.status.value,
                    'priority': task.priority.value,
                    'enabled': task.enabled,
                    'execution_count': task.execution_count,
                    'retry_count': task.retry_count,
                    'last_run': task.last_run.isoformat() if task.last_run else None,
                    'next_run': task.next_run.isoformat() if task.next_run else None,
                    'error_message': task.error_message,
                    'is_running': task_id in self._running_tasks
                }
            return None
    
    def get_all_tasks_status(self) -> List[Dict[str, Any]]:
        """Get status information for all tasks."""
        with self._task_lock:
            return [
                self.get_task_status(task_id)
                for task_id in self._tasks.keys()
            ]
    
    def get_scheduler_stats(self) -> Dict[str, Any]:
        """Get scheduler performance statistics."""
        uptime = datetime.now() - self._start_time
        
        with self._task_lock:
            return {
                'scheduler_active': self._scheduler_active,
                'uptime_seconds': uptime.total_seconds(),
                'registered_tasks_count': len(self._tasks),
                'running_tasks_count': len(self._running_tasks),
                'max_concurrent_tasks': self.max_concurrent_tasks,
                **self._task_stats
            }
    
    def enable_task(self, task_id: str) -> bool:
        """Enable a background task."""
        with self._task_lock:
            if task_id in self._tasks:
                self._tasks[task_id].enabled = True
                logger.info(f"Enabled background task: {task_id}")
                return True
            return False
    
    def disable_task(self, task_id: str) -> bool:
        """Disable a background task."""
        with self._task_lock:
            if task_id in self._tasks:
                self._tasks[task_id].enabled = False
                
                # Cancel if currently running
                if task_id in self._running_tasks:
                    self._running_tasks[task_id].cancel()
                    del self._running_tasks[task_id]
                
                logger.info(f"Disabled background task: {task_id}")
                return True
            return False
    
    async def execute_task_now(self, task_id: str) -> bool:
        """Execute a task immediately (one-time execution)."""
        with self._task_lock:
            if task_id not in self._tasks:
                return False
            
            task = self._tasks[task_id]
            if task_id in self._running_tasks:
                return False  # Already running
        
        await self._execute_task(task)
        return True


# Global task manager instance
_global_task_manager: Optional[BackgroundTaskManager] = None


def get_background_task_manager() -> BackgroundTaskManager:
    """Get the global background task manager instance."""
    global _global_task_manager
    if _global_task_manager is None:
        _global_task_manager = BackgroundTaskManager()
    return _global_task_manager


def start_background_tasks():
    """Start the background task system."""
    task_manager = get_background_task_manager()
    task_manager.start_scheduler()
    logger.info("Background task system started")


def stop_background_tasks():
    """Stop the background task system."""
    task_manager = get_background_task_manager()
    task_manager.stop_scheduler()
    logger.info("Background task system stopped")


# FastAPI integration
async def setup_background_tasks():
    """Setup background tasks for FastAPI application."""
    # Start performance monitoring
    performance_monitor = get_performance_monitor()
    performance_monitor.start_monitoring()
    
    # Start background task scheduler
    start_background_tasks()
    
    logger.info("Background task system initialized for FastAPI")


async def shutdown_background_tasks():
    """Shutdown background tasks for FastAPI application."""
    # Stop background tasks
    stop_background_tasks()
    
    # Stop performance monitoring
    performance_monitor = get_performance_monitor()
    performance_monitor.stop_monitoring()
    
    # Shutdown other components
    cache_manager = get_cache_manager()
    cache_manager.shutdown()
    
    try:
        batch_processor = get_batch_processor(None)
        if batch_processor:
            batch_processor.shutdown()
    except Exception as e:
        logger.warning(f"Error shutting down batch processor: {e}")
    
    logger.info("Background task system shutdown complete")