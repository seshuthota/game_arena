"""
Comprehensive unit tests for CacheManager.

Tests cache coordination, warming strategies, optimization suggestions,
performance monitoring integration, and multi-cache management.
"""

import pytest
import asyncio
import time
import threading
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta

from cache_manager import (
    CacheManager,
    CacheStrategy,
    CacheType,
    CacheWarmingTask,
    CachePerformanceProfile,
    CacheOptimizationSuggestion,
    get_cache_manager
)
from statistics_cache import StatisticsCache
from batch_statistics_processor import BatchStatisticsProcessor


class MockStatisticsCache:
    """Mock statistics cache for testing."""
    
    def __init__(self):
        self._cache = {}
        self._stats = {
            'hits': 10,
            'misses': 5,
            'evictions': 2,
            'cache_size': 50,
            'total_requests': 15
        }
        self.get_calls = []
        self.set_calls = []
        self.warm_calls = []
    
    def get(self, key_parts, calculator=None, ttl=None, dependencies=None):
        self.get_calls.append({
            'key_parts': key_parts,
            'calculator': calculator,
            'ttl': ttl,
            'dependencies': dependencies
        })
        
        key = str(key_parts)
        if key in self._cache:
            return self._cache[key]
        
        if calculator:
            try:
                result = calculator()
                self._cache[key] = result
                return result
            except:
                pass
        
        return None
    
    def set(self, key_parts, value, ttl=None, dependencies=None):
        self.set_calls.append({
            'key_parts': key_parts,
            'value': value,
            'ttl': ttl,
            'dependencies': dependencies
        })
        self._cache[str(key_parts)] = value
    
    def batch_get(self, batch_requests):
        return {i: self.get(req['key_parts'], req.get('calculator')) 
                for i, req in enumerate(batch_requests)}
    
    def warm_cache(self, warming_requests):
        self.warm_calls.append(warming_requests)
    
    def get_stats(self):
        return self._stats.copy()
    
    def _generate_cache_key(self, key_parts):
        return f"key_{hash(str(key_parts))}"


class MockBatchProcessor:
    """Mock batch processor for testing."""
    
    def __init__(self):
        self.performance_metrics = {
            'total_jobs': 5,
            'successful_jobs': 4,
            'failed_jobs': 1,
            'average_processing_time': 2.5,
            'cache_efficiency': 0.75
        }
    
    def get_performance_metrics(self):
        return self.performance_metrics.copy()


class TestCacheWarmingTask:
    """Test CacheWarmingTask functionality."""
    
    def test_cache_warming_task_creation(self):
        """Test cache warming task creation."""
        calculator = lambda: "test_result"
        
        task = CacheWarmingTask(
            cache_type=CacheType.PLAYER_STATISTICS,
            priority=3,
            key_parts=['player', 'stats', '123'],
            calculator=calculator,
            ttl=600.0,
            dependencies=['player:123'],
            estimated_computation_time=1.5,
            access_frequency=10
        )
        
        assert task.cache_type == CacheType.PLAYER_STATISTICS
        assert task.priority == 3
        assert task.key_parts == ['player', 'stats', '123']
        assert task.calculator == calculator
        assert task.ttl == 600.0
        assert task.dependencies == ['player:123']
        assert task.estimated_computation_time == 1.5
        assert task.access_frequency == 10
    
    def test_cache_warming_task_comparison(self):
        """Test cache warming task priority comparison."""
        high_priority_task = CacheWarmingTask(
            cache_type=CacheType.PLAYER_STATISTICS,
            priority=5,
            key_parts=['high'],
            calculator=lambda: "high",
            ttl=300.0,
            dependencies=[]
        )
        
        low_priority_task = CacheWarmingTask(
            cache_type=CacheType.PLAYER_STATISTICS,
            priority=1,
            key_parts=['low'],
            calculator=lambda: "low",
            ttl=300.0,
            dependencies=[]
        )
        
        # Higher priority should be "less than" (comes first in sort)
        assert high_priority_task < low_priority_task


class TestCachePerformanceProfile:
    """Test CachePerformanceProfile data class."""
    
    def test_cache_performance_profile_creation(self):
        """Test cache performance profile creation."""
        profile = CachePerformanceProfile(
            cache_type=CacheType.LEADERBOARDS,
            hit_rate=0.75,
            average_response_time=150.5,
            cache_size=200,
            eviction_rate=0.05,
            warming_efficiency=0.85,
            total_requests=1000
        )
        
        assert profile.cache_type == CacheType.LEADERBOARDS
        assert profile.hit_rate == 0.75
        assert profile.average_response_time == 150.5
        assert profile.cache_size == 200
        assert profile.eviction_rate == 0.05
        assert profile.warming_efficiency == 0.85
        assert profile.total_requests == 1000
        assert isinstance(profile.last_updated, datetime)


class TestCacheOptimizationSuggestion:
    """Test CacheOptimizationSuggestion data class."""
    
    def test_cache_optimization_suggestion_creation(self):
        """Test cache optimization suggestion creation."""
        suggestion = CacheOptimizationSuggestion(
            cache_type=CacheType.AGGREGATED_STATS,
            suggestion_type="increase_ttl",
            description="Consider increasing TTL to reduce cache misses",
            expected_improvement=0.15,
            implementation_complexity="low",
            priority=2
        )
        
        assert suggestion.cache_type == CacheType.AGGREGATED_STATS
        assert suggestion.suggestion_type == "increase_ttl"
        assert "reduce cache misses" in suggestion.description
        assert suggestion.expected_improvement == 0.15
        assert suggestion.implementation_complexity == "low"
        assert suggestion.priority == 2


class TestCacheManager:
    """Test CacheManager functionality."""
    
    def setup_method(self):
        """Setup test cache manager instance."""
        self.mock_cache = MockStatisticsCache()
        self.mock_batch_processor = MockBatchProcessor()
        
        self.manager = CacheManager(
            primary_cache=self.mock_cache,
            batch_processor=self.mock_batch_processor,
            warming_strategy=CacheStrategy.MODERATE,
            max_warming_workers=2,
            warming_interval_minutes=5
        )
    
    def teardown_method(self):
        """Cleanup after tests."""
        if hasattr(self.manager, '_warming_thread') and self.manager._warming_thread:
            self.manager._shutdown_warming.set()
            if self.manager._warming_thread.is_alive():
                self.manager._warming_thread.join(timeout=1)
    
    def test_cache_manager_initialization(self):
        """Test cache manager initialization."""
        assert self.manager.primary_cache == self.mock_cache
        assert self.manager.batch_processor == self.mock_batch_processor
        assert self.manager.warming_strategy == CacheStrategy.MODERATE
        assert self.manager.max_warming_workers == 2
        assert self.manager.warming_interval == timedelta(minutes=5)
        
        # Check cache registry
        assert 'primary' in self.manager._cache_registry
        assert self.manager._cache_registry['primary'] == self.mock_cache
    
    def test_cache_registry_management(self):
        """Test cache registry operations."""
        additional_cache = MockStatisticsCache()
        
        # Register additional cache
        self.manager.register_cache('secondary', additional_cache)
        assert self.manager.get_cache('secondary') == additional_cache
        
        # Test getting primary cache
        assert self.manager.get_cache('primary') == self.mock_cache
        
        # Test getting non-existent cache
        assert self.manager.get_cache('nonexistent') is None
    
    @pytest.mark.asyncio
    async def test_get_with_warming(self):
        """Test intelligent cache retrieval with warming."""
        calculator = Mock(return_value="calculated_value")
        
        # First call should invoke calculator and store result
        result = await self.manager.get_with_warming(
            cache_type=CacheType.PLAYER_STATISTICS,
            key_parts=['player', '123'],
            calculator=calculator,
            ttl=300.0,
            dependencies=['player:123'],
            warm_related=True
        )
        
        assert result == "calculated_value"
        calculator.assert_called_once()
        
        # Verify cache get was called
        assert len(self.mock_cache.get_calls) > 0
        get_call = self.mock_cache.get_calls[0]
        assert get_call['key_parts'] == ['player', '123']
        assert get_call['calculator'] == calculator
        assert get_call['ttl'] == 300.0
        assert get_call['dependencies'] == ['player:123']
    
    @pytest.mark.asyncio
    async def test_get_with_warming_cache_name(self):
        """Test cache retrieval with specific cache name."""
        # Test with non-existent cache
        result = await self.manager.get_with_warming(
            cache_type=CacheType.PLAYER_STATISTICS,
            key_parts=['test'],
            cache_name='nonexistent'
        )
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_batch_get_with_warming(self):
        """Test batch cache retrieval with warming."""
        batch_requests = [
            {'key_parts': ['batch', '1'], 'calculator': lambda: 'value_1'},
            {'key_parts': ['batch', '2'], 'calculator': lambda: 'value_2'}
        ]
        
        results = await self.manager.batch_get_with_warming(
            cache_type=CacheType.AGGREGATED_STATS,
            batch_requests=batch_requests,
            warm_popular=True
        )
        
        # Should return results
        assert len(results) == 2
        assert 0 in results
        assert 1 in results
    
    def test_add_warming_task(self):
        """Test adding warming tasks to queue."""
        calculator = Mock(return_value="warmed_value")
        
        self.manager.add_warming_task(
            cache_type=CacheType.LEADERBOARDS,
            key_parts=['leaderboard', 'elo'],
            calculator=calculator,
            priority=3,
            ttl=600.0,
            dependencies=['leaderboard'],
            estimated_time=2.0,
            access_frequency=50
        )
        
        # Verify task was added to queue
        assert len(self.manager._warming_queue) == 1
        
        task = self.manager._warming_queue[0]
        assert task.cache_type == CacheType.LEADERBOARDS
        assert task.key_parts == ['leaderboard', 'elo']
        assert task.priority == 3
        assert task.calculator == calculator
    
    def test_warming_strategy_changes(self):
        """Test changing warming strategies."""
        # Start with moderate strategy
        assert self.manager.warming_strategy == CacheStrategy.MODERATE
        
        # Change to conservative (should stop warming thread)
        self.manager.set_warming_strategy(CacheStrategy.CONSERVATIVE)
        assert self.manager.warming_strategy == CacheStrategy.CONSERVATIVE
        
        # Change to aggressive (should start warming thread)
        self.manager.set_warming_strategy(CacheStrategy.AGGRESSIVE)
        assert self.manager.warming_strategy == CacheStrategy.AGGRESSIVE
    
    @pytest.mark.asyncio
    async def test_warm_popular_data(self):
        """Test warming cache with popular data."""
        # Mock access patterns
        popular_patterns = [
            {
                'key_parts': ['popular', '1'],
                'calculator': lambda: 'popular_value_1',
                'access_frequency': 100
            },
            {
                'key_parts': ['popular', '2'],
                'calculator': lambda: 'popular_value_2',
                'access_frequency': 50
            }
        ]
        
        # Mock identify_popular_patterns method
        with patch.object(self.manager, '_identify_popular_patterns', return_value=popular_patterns):
            warmed_count = await self.manager.warm_popular_data(top_n=2)
        
        # Should have warmed popular data
        assert warmed_count == 2
        assert len(self.mock_cache.warm_calls) > 0
    
    @pytest.mark.asyncio
    async def test_optimize_cache_performance(self):
        """Test cache performance optimization suggestions."""
        # Create mock performance profiles with different issues
        self.manager._performance_profiles = {
            CacheType.PLAYER_STATISTICS: CachePerformanceProfile(
                cache_type=CacheType.PLAYER_STATISTICS,
                hit_rate=0.3,  # Low hit rate
                average_response_time=0.2,
                cache_size=100,
                eviction_rate=0.1,
                warming_efficiency=0.8,
                total_requests=1000
            ),
            CacheType.LEADERBOARDS: CachePerformanceProfile(
                cache_type=CacheType.LEADERBOARDS,
                hit_rate=0.8,
                average_response_time=1.2,  # High response time
                cache_size=200,
                eviction_rate=0.4,  # High eviction rate
                warming_efficiency=0.9,
                total_requests=2000
            )
        }
        
        suggestions = await self.manager.optimize_cache_performance()
        
        # Should generate suggestions for detected issues
        assert len(suggestions) > 0
        
        # Check for expected suggestion types
        suggestion_types = [s.suggestion_type for s in suggestions]
        assert "add_warming" in suggestion_types  # For low hit rate
        assert "increase_ttl" in suggestion_types  # For high eviction rate
        assert "optimize_calculation" in suggestion_types  # For high response time
        
        # Should be sorted by priority
        priorities = [s.priority for s in suggestions]
        assert priorities == sorted(priorities, reverse=True)
    
    def test_performance_report_generation(self):
        """Test comprehensive performance report generation."""
        # Set up mock performance profiles
        self.manager._performance_profiles[CacheType.PLAYER_STATISTICS] = CachePerformanceProfile(
            cache_type=CacheType.PLAYER_STATISTICS,
            hit_rate=0.75,
            average_response_time=0.15,
            cache_size=150,
            eviction_rate=0.05,
            warming_efficiency=0.85,
            total_requests=500
        )
        
        # Set up mock usage stats
        self.manager._usage_stats.update({
            'total_requests': 1000,
            'cache_hits': 750,
            'warming_tasks_completed': 25,
            'optimization_actions_taken': 5
        })
        
        report = self.manager.get_performance_report()
        
        # Verify report structure
        assert 'overview' in report
        assert 'cache_profiles' in report
        assert 'cache_stats' in report
        assert 'recent_optimizations' in report
        assert 'access_patterns' in report
        
        # Check overview section
        overview = report['overview']
        assert overview['total_requests'] == 1000
        assert overview['overall_hit_rate'] == 0.75
        assert overview['warming_tasks_completed'] == 25
        
        # Check cache profiles
        profiles = report['cache_profiles']
        assert CacheType.PLAYER_STATISTICS.value in profiles
        player_profile = profiles[CacheType.PLAYER_STATISTICS.value]
        assert player_profile['hit_rate'] == 0.75
        assert player_profile['response_time'] == 0.15
    
    def test_cleanup_old_data(self):
        """Test cleanup of old cache management data."""
        # Add old access patterns
        old_time = datetime.now() - timedelta(hours=48)
        self.manager._access_patterns['old_pattern'] = {
            'last_access': old_time,
            'access_count': 10
        }
        
        # Add recent access pattern
        recent_time = datetime.now() - timedelta(minutes=30)
        self.manager._access_patterns['recent_pattern'] = {
            'last_access': recent_time,
            'access_count': 5
        }
        
        # Add old optimization suggestions
        old_suggestion = CacheOptimizationSuggestion(
            cache_type=CacheType.PLAYER_STATISTICS,
            suggestion_type="test",
            description="Old suggestion",
            expected_improvement=0.1,
            implementation_complexity="low",
            priority=1
        )
        self.manager._optimization_history.append(old_suggestion)
        
        # Perform cleanup
        cleanup_results = self.manager.cleanup_old_data(max_age_hours=24)
        
        # Verify cleanup
        assert cleanup_results['access_patterns_removed'] == 1
        assert 'old_pattern' not in self.manager._access_patterns
        assert 'recent_pattern' in self.manager._access_patterns
    
    def test_warming_thread_management(self):
        """Test warming thread lifecycle management."""
        # Start with moderate strategy (should have warming thread)
        manager_with_warming = CacheManager(
            primary_cache=self.mock_cache,
            warming_strategy=CacheStrategy.MODERATE
        )
        
        # Should start warming thread
        time.sleep(0.1)  # Give thread time to start
        assert manager_with_warming._warming_thread is not None
        
        # Change to conservative (should stop thread)
        manager_with_warming.set_warming_strategy(CacheStrategy.CONSERVATIVE)
        time.sleep(0.1)  # Give thread time to stop
        
        # Cleanup
        manager_with_warming.shutdown()
    
    def test_warming_task_execution(self):
        """Test execution of warming tasks."""
        # Mock successful calculation
        calculator = Mock(return_value="warmed_result")
        
        # Create warming task
        task = CacheWarmingTask(
            cache_type=CacheType.PLAYER_STATISTICS,
            priority=1,
            key_parts=['warm_test'],
            calculator=calculator,
            ttl=300.0,
            dependencies=['test']
        )
        
        # Execute warming task
        self.manager._execute_warming_task(task)
        
        # Verify calculator was called
        calculator.assert_called_once()
        
        # Verify result was cached
        assert len(self.mock_cache.set_calls) > 0
        set_call = self.mock_cache.set_calls[-1]
        assert set_call['value'] == "warmed_result"
    
    def test_task_key_generation(self):
        """Test warming task key generation."""
        key_parts = ['player', 'stats', 123, {'param': 'value'}]
        
        task_key1 = self.manager._generate_task_key(key_parts)
        task_key2 = self.manager._generate_task_key(key_parts)
        
        # Should generate consistent keys
        assert task_key1 == task_key2
        assert isinstance(task_key1, str)
        
        # Different key parts should generate different keys
        different_key_parts = ['player', 'stats', 456]
        task_key3 = self.manager._generate_task_key(different_key_parts)
        assert task_key1 != task_key3
    
    @patch('cache_manager.threading.Thread')
    def test_related_warming_scheduling(self, mock_thread):
        """Test scheduling of related cache warming."""
        calculator = Mock(return_value="test_result")
        
        # Should not schedule for conservative strategy
        conservative_manager = CacheManager(
            primary_cache=self.mock_cache,
            warming_strategy=CacheStrategy.CONSERVATIVE
        )
        
        # This should not schedule warming
        asyncio.run(conservative_manager._schedule_related_warming(
            cache_type=CacheType.PLAYER_STATISTICS,
            key_parts=['player', '123'],
            calculator=calculator,
            ttl=300.0,
            dependencies=['player:123']
        ))
        
        # Should not have added tasks
        assert len(conservative_manager._warming_queue) == 0
    
    def test_access_pattern_recording(self):
        """Test access pattern recording and analysis."""
        cache_type = CacheType.LEADERBOARDS
        key_parts = ['leaderboard', 'elo', 10]
        
        # Record multiple accesses
        for _ in range(5):
            self.manager._record_access_pattern(cache_type, key_parts)
        
        # Should have recorded access pattern
        assert len(self.manager._access_patterns) > 0
        
        # Find the pattern
        pattern_key = f"{cache_type}:{hash(tuple(key_parts))}"
        assert pattern_key in self.manager._access_patterns
        
        pattern = self.manager._access_patterns[pattern_key]
        assert pattern['cache_type'] == cache_type
        assert pattern['key_parts'] == key_parts
        assert pattern['access_count'] == 5
    
    def test_performance_metrics_updates(self):
        """Test performance metrics tracking."""
        cache_type = CacheType.PLAYER_STATISTICS
        
        # Update metrics with cache hit
        self.manager._update_performance_metrics(cache_type, True, 0.1)
        
        # Should create performance profile
        assert cache_type in self.manager._performance_profiles
        
        profile = self.manager._performance_profiles[cache_type]
        assert profile.total_requests == 1
        assert profile.hit_rate == 1.0
        assert profile.average_response_time == 0.1
        
        # Update with cache miss
        self.manager._update_performance_metrics(cache_type, False, 0.2)
        
        # Should update profile
        updated_profile = self.manager._performance_profiles[cache_type]
        assert updated_profile.total_requests == 2
        assert updated_profile.hit_rate == 0.5  # 1 hit out of 2 requests
    
    def test_access_pattern_summary(self):
        """Test access pattern summary generation."""
        # Record some access patterns
        self.manager._record_access_pattern(CacheType.PLAYER_STATISTICS, ['player', '1'])
        self.manager._record_access_pattern(CacheType.PLAYER_STATISTICS, ['player', '2'])
        self.manager._record_access_pattern(CacheType.LEADERBOARDS, ['leaderboard'])
        
        summary = self.manager._get_access_pattern_summary()
        
        assert 'total_accesses' in summary
        assert 'unique_patterns' in summary
        assert 'by_cache_type' in summary
        
        # Should have recorded patterns
        assert summary['unique_patterns'] >= 3
        
        # Should have cache type breakdown
        by_type = summary['by_cache_type']
        assert CacheType.PLAYER_STATISTICS in by_type
        assert CacheType.LEADERBOARDS in by_type
    
    def test_manager_shutdown(self):
        """Test cache manager shutdown."""
        # Shutdown should stop warming thread and cleanup
        self.manager.shutdown()
        
        # Warming thread should be stopped
        if self.manager._warming_thread:
            assert not self.manager._warming_thread.is_alive()


class TestCacheManagerGlobalFunction:
    """Test global cache manager function."""
    
    def test_get_cache_manager(self):
        """Test global cache manager retrieval."""
        manager1 = get_cache_manager()
        manager2 = get_cache_manager()
        
        # Should return same instance
        assert manager1 is manager2
        assert isinstance(manager1, CacheManager)
        
        # Cleanup
        manager1.shutdown()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])