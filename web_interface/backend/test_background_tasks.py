"""
Comprehensive unit tests for Background Tasks system.

Tests task scheduling, execution, monitoring, error handling,
and background task management functionality.
"""

import pytest
import asyncio
import time
import threading
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta

from background_tasks import (
    BackgroundTaskManager,
    BackgroundTask,
    TaskStatus,
    TaskPriority,
    get_background_task_manager,
    start_background_tasks,
    stop_background_tasks,
    setup_background_tasks,
    shutdown_background_tasks
)


class TestBackgroundTask:
    """Test BackgroundTask data class."""
    
    def test_background_task_creation(self):
        """Test background task creation with all parameters."""
        def test_function():
            return "test_result"
        
        task = BackgroundTask(
            task_id="test_task_123",
            name="Test Task",
            description="A test background task",
            function=test_function,
            priority=TaskPriority.HIGH,
            schedule_interval=timedelta(minutes=30),
            max_retries=5,
            timeout_seconds=600,
            enabled=True
        )
        
        assert task.task_id == "test_task_123"
        assert task.name == "Test Task"
        assert task.description == "A test background task"
        assert task.function == test_function
        assert task.priority == TaskPriority.HIGH
        assert task.schedule_interval == timedelta(minutes=30)
        assert task.status == TaskStatus.PENDING
        assert task.max_retries == 5
        assert task.timeout_seconds == 600
        assert task.enabled is True
        assert task.execution_count == 0
        assert task.retry_count == 0
        assert task.error_message is None
        assert task.next_run is None
        assert task.last_run is None
    
    def test_background_task_defaults(self):
        """Test background task with default values."""
        def dummy_function():
            pass
        
        task = BackgroundTask(
            task_id="default_task",
            name="Default Task",
            description="Task with defaults",
            function=dummy_function,
            priority=TaskPriority.NORMAL
        )
        
        assert task.schedule_interval is None  # One-time task
        assert task.status == TaskStatus.PENDING
        assert task.max_retries == 3
        assert task.timeout_seconds == 300
        assert task.enabled is True


class TestBackgroundTaskManager:
    """Test BackgroundTaskManager functionality."""
    
    def setup_method(self):
        """Setup test task manager instance."""
        self.manager = BackgroundTaskManager(
            max_concurrent_tasks=2,
            task_check_interval=1  # 1 second for testing
        )
        
        # Clear any registered tasks for clean testing
        self.manager._tasks.clear()
    
    def teardown_method(self):
        """Cleanup after tests."""
        self.manager.stop_scheduler()
    
    def test_task_manager_initialization(self):
        """Test task manager initialization."""
        assert self.manager.max_concurrent_tasks == 2
        assert self.manager.task_check_interval == 1
        assert not self.manager._scheduler_active
        assert self.manager._scheduler_task is None
        assert len(self.manager._tasks) == 0
        assert len(self.manager._running_tasks) == 0
    
    def test_task_manager_with_default_tasks(self):
        """Test task manager initialization with default tasks."""
        # Create new manager to test default task registration
        manager_with_defaults = BackgroundTaskManager()
        
        # Should have registered default system tasks
        assert len(manager_with_defaults._tasks) > 0
        
        # Check for some expected default tasks
        task_ids = list(manager_with_defaults._tasks.keys())
        assert "cache_cleanup" in task_ids
        assert "cache_warming" in task_ids
        assert "performance_monitoring" in task_ids
        assert "health_check" in task_ids
        
        # Cleanup
        manager_with_defaults.stop_scheduler()
    
    def test_register_task(self):
        """Test task registration."""
        def test_function():
            return "success"
        
        task = BackgroundTask(
            task_id="register_test",
            name="Register Test",
            description="Test task registration",
            function=test_function,
            priority=TaskPriority.NORMAL,
            schedule_interval=timedelta(minutes=10)
        )
        
        # Register task
        self.manager.register_task(task)
        
        # Verify registration
        assert "register_test" in self.manager._tasks
        assert self.manager._tasks["register_test"] == task
        
        # Task should have next_run set
        assert task.next_run is not None
        assert task.next_run > datetime.now()
    
    def test_unregister_task(self):
        """Test task unregistration."""
        def test_function():
            pass
        
        task = BackgroundTask(
            task_id="unregister_test",
            name="Unregister Test",
            description="Test task unregistration",
            function=test_function,
            priority=TaskPriority.NORMAL
        )
        
        # Register then unregister
        self.manager.register_task(task)
        assert "unregister_test" in self.manager._tasks
        
        result = self.manager.unregister_task("unregister_test")
        assert result is True
        assert "unregister_test" not in self.manager._tasks
        
        # Test unregistering non-existent task
        result = self.manager.unregister_task("nonexistent")
        assert result is False
    
    def test_start_stop_scheduler(self):
        """Test scheduler lifecycle management."""
        # Start scheduler
        self.manager.start_scheduler()
        assert self.manager._scheduler_active is True
        assert self.manager._scheduler_task is not None
        
        # Give scheduler time to start
        time.sleep(0.1)
        
        # Stop scheduler
        self.manager.stop_scheduler()
        assert self.manager._scheduler_active is False
        
        # Give scheduler time to stop
        time.sleep(0.1)
    
    def test_enable_disable_task(self):
        """Test task enable/disable functionality."""
        def test_function():
            pass
        
        task = BackgroundTask(
            task_id="enable_test",
            name="Enable Test",
            description="Test task enable/disable",
            function=test_function,
            priority=TaskPriority.NORMAL
        )
        
        self.manager.register_task(task)
        
        # Task should be enabled by default
        assert task.enabled is True
        
        # Disable task
        result = self.manager.disable_task("enable_test")
        assert result is True
        assert task.enabled is False
        
        # Enable task
        result = self.manager.enable_task("enable_test")
        assert result is True
        assert task.enabled is True
        
        # Test with non-existent task
        assert self.manager.enable_task("nonexistent") is False
        assert self.manager.disable_task("nonexistent") is False
    
    @pytest.mark.asyncio
    async def test_execute_task_now(self):
        """Test immediate task execution."""
        execution_log = []
        
        def test_function():
            execution_log.append("executed")
            return "success"
        
        task = BackgroundTask(
            task_id="execute_now_test",
            name="Execute Now Test",
            description="Test immediate execution",
            function=test_function,
            priority=TaskPriority.NORMAL
        )
        
        self.manager.register_task(task)
        
        # Execute task immediately
        result = await self.manager.execute_task_now("execute_now_test")
        assert result is True
        
        # Give task time to complete
        await asyncio.sleep(0.1)
        
        # Verify execution
        assert len(execution_log) == 1
        assert execution_log[0] == "executed"
        
        # Test non-existent task
        result = await self.manager.execute_task_now("nonexistent")
        assert result is False
    
    def test_get_task_status(self):
        """Test task status retrieval."""
        def test_function():
            pass
        
        task = BackgroundTask(
            task_id="status_test",
            name="Status Test",
            description="Test status retrieval",
            function=test_function,
            priority=TaskPriority.HIGH,
            execution_count=5,
            retry_count=2
        )
        
        # Set some timestamps for testing
        task.last_run = datetime.now() - timedelta(minutes=10)
        task.next_run = datetime.now() + timedelta(minutes=5)
        task.error_message = "Test error"
        
        self.manager.register_task(task)
        
        # Get status
        status = self.manager.get_task_status("status_test")
        
        assert status is not None
        assert status['task_id'] == "status_test"
        assert status['name'] == "Status Test"
        assert status['description'] == "Test status retrieval"
        assert status['status'] == TaskStatus.PENDING.value
        assert status['priority'] == TaskPriority.HIGH.value
        assert status['enabled'] is True
        assert status['execution_count'] == 5
        assert status['retry_count'] == 2
        assert status['error_message'] == "Test error"
        assert status['last_run'] is not None
        assert status['next_run'] is not None
        assert status['is_running'] is False
        
        # Test non-existent task
        assert self.manager.get_task_status("nonexistent") is None
    
    def test_get_all_tasks_status(self):
        """Test all tasks status retrieval."""
        # Register multiple tasks
        for i in range(3):
            task = BackgroundTask(
                task_id=f"status_test_{i}",
                name=f"Status Test {i}",
                description=f"Test task {i}",
                function=lambda: None,
                priority=TaskPriority.NORMAL
            )
            self.manager.register_task(task)
        
        # Get all statuses
        all_statuses = self.manager.get_all_tasks_status()
        
        assert len(all_statuses) == 3
        for status in all_statuses:
            assert 'task_id' in status
            assert status['task_id'].startswith('status_test_')
    
    def test_get_scheduler_stats(self):
        """Test scheduler statistics retrieval."""
        stats = self.manager.get_scheduler_stats()
        
        # Verify structure
        assert 'scheduler_active' in stats
        assert 'uptime_seconds' in stats
        assert 'registered_tasks_count' in stats
        assert 'running_tasks_count' in stats
        assert 'max_concurrent_tasks' in stats
        
        # Verify values
        assert stats['scheduler_active'] is False  # Not started
        assert stats['registered_tasks_count'] == 0  # No tasks registered
        assert stats['running_tasks_count'] == 0
        assert stats['max_concurrent_tasks'] == 2
        assert isinstance(stats['uptime_seconds'], float)
    
    @pytest.mark.asyncio
    async def test_successful_task_execution(self):
        """Test successful task execution flow."""
        execution_log = []
        
        def successful_task():
            execution_log.append("success")
            return "task_completed"
        
        task = BackgroundTask(
            task_id="success_test",
            name="Success Test",
            description="Test successful execution",
            function=successful_task,
            priority=TaskPriority.NORMAL
        )
        
        # Set next run to now for immediate execution
        task.next_run = datetime.now()
        self.manager.register_task(task)
        
        # Execute task
        await self.manager._execute_task(task)
        
        # Give task time to complete
        await asyncio.sleep(0.1)
        
        # Verify execution
        assert len(execution_log) == 1
        assert task.status == TaskStatus.COMPLETED
        assert task.execution_count == 1
        assert task.retry_count == 0
        assert task.error_message is None
        assert task.last_run is not None
    
    @pytest.mark.asyncio
    async def test_failed_task_execution(self):
        """Test failed task execution and retry logic."""
        execution_count = 0
        
        def failing_task():
            nonlocal execution_count
            execution_count += 1
            raise ValueError(f"Task failed on attempt {execution_count}")
        
        task = BackgroundTask(
            task_id="fail_test",
            name="Fail Test",
            description="Test failed execution",
            function=failing_task,
            priority=TaskPriority.NORMAL,
            max_retries=2
        )
        
        task.next_run = datetime.now()
        self.manager.register_task(task)
        
        # Execute task (will fail and schedule retry)
        await self.manager._execute_task(task)
        
        # Give task time to complete
        await asyncio.sleep(0.1)
        
        # Verify failure handling
        assert task.retry_count == 1
        assert task.status == TaskStatus.SCHEDULED  # Scheduled for retry
        assert "Task failed on attempt 1" in task.error_message
        assert task.next_run is not None
        assert task.next_run > datetime.now()
    
    @pytest.mark.asyncio
    async def test_task_max_retries_exceeded(self):
        """Test task behavior when max retries are exceeded."""
        def always_failing_task():
            raise RuntimeError("Task always fails")
        
        task = BackgroundTask(
            task_id="max_fail_test",
            name="Max Fail Test",
            description="Test max retries exceeded",
            function=always_failing_task,
            priority=TaskPriority.NORMAL,
            max_retries=1
        )
        
        task.next_run = datetime.now()
        self.manager.register_task(task)
        
        # Execute task twice (initial + 1 retry)
        await self.manager._execute_task(task)
        await asyncio.sleep(0.1)
        
        # Simulate retry
        task.next_run = datetime.now()
        await self.manager._execute_task(task)
        await asyncio.sleep(0.1)
        
        # Should be permanently failed
        assert task.status == TaskStatus.FAILED
        assert task.retry_count > task.max_retries
    
    @pytest.mark.asyncio
    async def test_async_task_execution(self):
        """Test execution of async tasks."""
        execution_log = []
        
        async def async_task():
            await asyncio.sleep(0.01)
            execution_log.append("async_success")
            return "async_completed"
        
        task = BackgroundTask(
            task_id="async_test",
            name="Async Test",
            description="Test async task execution",
            function=async_task,
            priority=TaskPriority.NORMAL
        )
        
        task.next_run = datetime.now()
        self.manager.register_task(task)
        
        # Execute async task
        await self.manager._execute_task(task)
        
        # Give task time to complete
        await asyncio.sleep(0.1)
        
        # Verify execution
        assert len(execution_log) == 1
        assert execution_log[0] == "async_success"
        assert task.status == TaskStatus.COMPLETED
    
    def test_cleanup_completed_tasks(self):
        """Test cleanup of completed task references."""
        # Create mock completed tasks
        completed_task = Mock()
        completed_task.done.return_value = True
        
        running_task = Mock()
        running_task.done.return_value = False
        
        # Add to running tasks
        self.manager._running_tasks = {
            "completed_task": completed_task,
            "running_task": running_task
        }
        
        # Run cleanup
        asyncio.run(self.manager._cleanup_completed_tasks())
        
        # Completed task should be removed
        assert "completed_task" not in self.manager._running_tasks
        assert "running_task" in self.manager._running_tasks
    
    @patch('background_tasks.get_statistics_cache')
    def test_cache_cleanup_task(self, mock_get_cache):
        """Test default cache cleanup task."""
        # Mock cache with cleanup method
        mock_cache = Mock()
        mock_cache._cleanup_expired_entries.return_value = 5
        mock_cache.get_stats.return_value = {'cache_size': 100}
        mock_get_cache.return_value = mock_cache
        
        # Execute cache cleanup task
        asyncio.run(self.manager._cache_cleanup_task())
        
        # Verify cache cleanup was called
        mock_cache._cleanup_expired_entries.assert_called_once()
        mock_cache.get_stats.assert_called()
    
    @patch('background_tasks.get_cache_manager')
    async def test_cache_warming_task(self, mock_get_manager):
        """Test default cache warming task."""
        # Mock cache manager with warming method
        mock_manager = Mock()
        mock_manager.warm_popular_data = AsyncMock(return_value=10)
        mock_get_manager.return_value = mock_manager
        
        # Execute cache warming task
        await self.manager._cache_warming_task()
        
        # Verify warming was called
        mock_manager.warm_popular_data.assert_called_once_with(top_n=50)
    
    @patch('background_tasks.get_performance_monitor')
    async def test_performance_monitoring_task(self, mock_get_monitor):
        """Test default performance monitoring task."""
        # Mock performance monitor
        mock_monitor = Mock()
        mock_monitor.get_current_metrics.return_value = {
            'cache_hit_rate': 75.0,
            'response_time': 200.0
        }
        mock_get_monitor.return_value = mock_monitor
        
        # Execute monitoring task
        await self.manager._performance_monitoring_task()
        
        # Verify monitoring was called
        mock_monitor.get_current_metrics.assert_called_once()
    
    @patch('background_tasks.get_cache_manager')
    async def test_cache_optimization_task(self, mock_get_manager):
        """Test cache optimization task."""
        # Mock suggestions
        mock_suggestions = [
            Mock(priority=3, description="High priority suggestion"),
            Mock(priority=1, description="Low priority suggestion")
        ]
        
        mock_manager = Mock()
        mock_manager.optimize_cache_performance = AsyncMock(return_value=mock_suggestions)
        mock_get_manager.return_value = mock_manager
        
        # Execute optimization task
        await self.manager._cache_optimization_task()
        
        # Verify optimization was called
        mock_manager.optimize_cache_performance.assert_called_once()
    
    @patch('background_tasks.get_performance_monitor')
    async def test_system_health_check_task(self, mock_get_monitor):
        """Test system health check task."""
        from performance_monitor import AlertSeverity, SystemHealthReport
        
        # Mock health report with alerts
        mock_alerts = [
            Mock(severity=AlertSeverity.CRITICAL, message="Critical alert"),
            Mock(severity=AlertSeverity.HIGH, message="High alert")
        ]
        
        mock_report = SystemHealthReport(
            timestamp=datetime.now(),
            overall_health_score=45.0,  # Poor health
            cache_performance_score=50.0,
            system_resource_score=40.0,
            error_rate_score=45.0,
            alerts=mock_alerts,
            trends=[],
            recommendations=[],
            uptime=timedelta(hours=1)
        )
        
        mock_monitor = Mock()
        mock_monitor.generate_health_report.return_value = mock_report
        mock_get_monitor.return_value = mock_monitor
        
        # Execute health check task
        await self.manager._system_health_check_task()
        
        # Verify health report was generated
        mock_monitor.generate_health_report.assert_called_once()
    
    @patch('background_tasks.get_cache_manager')
    async def test_data_cleanup_task(self, mock_get_manager):
        """Test data cleanup task."""
        mock_manager = Mock()
        mock_manager.cleanup_old_data.return_value = {'cleaned_items': 15}
        mock_get_manager.return_value = mock_manager
        
        # Execute data cleanup task
        await self.manager._data_cleanup_task()
        
        # Verify cleanup was called
        mock_manager.cleanup_old_data.assert_called_once_with(max_age_hours=24)


class TestGlobalFunctions:
    """Test global background task functions."""
    
    def test_get_background_task_manager(self):
        """Test global task manager retrieval."""
        manager1 = get_background_task_manager()
        manager2 = get_background_task_manager()
        
        # Should return same instance
        assert manager1 is manager2
        assert isinstance(manager1, BackgroundTaskManager)
        
        # Cleanup
        manager1.stop_scheduler()
    
    def test_start_stop_background_tasks(self):
        """Test global start/stop functions."""
        # Start background tasks
        start_background_tasks()
        
        manager = get_background_task_manager()
        assert manager._scheduler_active is True
        
        # Stop background tasks
        stop_background_tasks()
        assert manager._scheduler_active is False
    
    @patch('background_tasks.get_performance_monitor')
    @patch('background_tasks.start_background_tasks')
    async def test_setup_background_tasks(self, mock_start_tasks, mock_get_monitor):
        """Test FastAPI setup function."""
        mock_monitor = Mock()
        mock_monitor.start_monitoring = Mock()
        mock_get_monitor.return_value = mock_monitor
        
        # Setup background tasks
        await setup_background_tasks()
        
        # Verify setup was called
        mock_monitor.start_monitoring.assert_called_once()
        mock_start_tasks.assert_called_once()
    
    @patch('background_tasks.get_performance_monitor')
    @patch('background_tasks.get_cache_manager')
    @patch('background_tasks.stop_background_tasks')
    async def test_shutdown_background_tasks(self, mock_stop_tasks, mock_get_manager, mock_get_monitor):
        """Test FastAPI shutdown function."""
        mock_monitor = Mock()
        mock_monitor.stop_monitoring = Mock()
        mock_get_monitor.return_value = mock_monitor
        
        mock_manager = Mock()
        mock_manager.shutdown = Mock()
        mock_get_manager.return_value = mock_manager
        
        # Shutdown background tasks
        await shutdown_background_tasks()
        
        # Verify shutdown was called
        mock_stop_tasks.assert_called_once()
        mock_monitor.stop_monitoring.assert_called_once()
        mock_manager.shutdown.assert_called_once()


class TestTaskIntegration:
    """Integration tests for task execution."""
    
    @pytest.mark.asyncio
    async def test_scheduled_task_execution(self):
        """Test scheduled task execution in real scheduler."""
        manager = BackgroundTaskManager(
            max_concurrent_tasks=1,
            task_check_interval=1
        )
        
        execution_log = []
        
        def scheduled_task():
            execution_log.append(datetime.now())
            return "completed"
        
        # Create task scheduled to run immediately
        task = BackgroundTask(
            task_id="scheduled_test",
            name="Scheduled Test",
            description="Test scheduled execution",
            function=scheduled_task,
            priority=TaskPriority.NORMAL,
            schedule_interval=timedelta(seconds=2)  # Recurring every 2 seconds
        )
        task.next_run = datetime.now() + timedelta(seconds=0.1)  # Run almost immediately
        
        try:
            manager.register_task(task)
            manager.start_scheduler()
            
            # Wait for task to execute at least once
            await asyncio.sleep(2.5)
            
            # Verify execution
            assert len(execution_log) >= 1
            assert task.status == TaskStatus.COMPLETED
            assert task.execution_count >= 1
            
        finally:
            manager.stop_scheduler()
    
    @pytest.mark.asyncio
    async def test_priority_based_execution(self):
        """Test that higher priority tasks execute first."""
        manager = BackgroundTaskManager(
            max_concurrent_tasks=1,  # Only one task at a time
            task_check_interval=1
        )
        
        execution_order = []
        
        def create_task_function(task_name):
            def task_function():
                execution_order.append(task_name)
                time.sleep(0.1)  # Small delay
                return f"{task_name}_completed"
            return task_function
        
        # Create tasks with different priorities
        low_priority_task = BackgroundTask(
            task_id="low_priority",
            name="Low Priority",
            description="Low priority task",
            function=create_task_function("low"),
            priority=TaskPriority.LOW
        )
        low_priority_task.next_run = datetime.now() + timedelta(seconds=0.1)
        
        high_priority_task = BackgroundTask(
            task_id="high_priority",
            name="High Priority", 
            description="High priority task",
            function=create_task_function("high"),
            priority=TaskPriority.HIGH
        )
        high_priority_task.next_run = datetime.now() + timedelta(seconds=0.1)
        
        try:
            # Register low priority first, then high priority
            manager.register_task(low_priority_task)
            manager.register_task(high_priority_task)
            manager.start_scheduler()
            
            # Wait for tasks to execute
            await asyncio.sleep(3)
            
            # High priority task should execute first
            assert len(execution_order) >= 1
            if len(execution_order) >= 1:
                assert execution_order[0] == "high"
        
        finally:
            manager.stop_scheduler()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])