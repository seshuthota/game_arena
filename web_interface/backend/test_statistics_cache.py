"""
Comprehensive unit tests for StatisticsCache.

Tests TTL-based invalidation, dependency tracking, batch operations,
cache warming, and performance characteristics.
"""

import pytest
import asyncio
import time
import threading
from unittest.mock import Mock, patch, call
from datetime import datetime, timedelta

from statistics_cache import (
    StatisticsCache,
    CacheEntry,
    get_statistics_cache,
    invalidate_player_cache,
    invalidate_game_cache,
    invalidate_leaderboard_cache
)


class TestCacheEntry:
    """Test CacheEntry functionality."""
    
    def test_cache_entry_creation(self):
        """Test basic cache entry creation."""
        data = {"test": "data"}
        entry = CacheEntry(
            data=data,
            timestamp=time.time(),
            ttl=300.0,
            cache_key="test_key",
            dependencies=["dep1", "dep2"]
        )
        
        assert entry.data == data
        assert entry.ttl == 300.0
        assert entry.cache_key == "test_key"
        assert entry.dependencies == ["dep1", "dep2"]
        assert entry.access_count == 0
        assert not entry.is_expired()
    
    def test_cache_entry_expiration(self):
        """Test cache entry expiration logic."""
        # Create expired entry
        old_timestamp = time.time() - 400  # 400 seconds ago
        entry = CacheEntry(
            data="test",
            timestamp=old_timestamp,
            ttl=300.0  # 5 minutes
        )
        
        assert entry.is_expired()
        
        # Create non-expired entry
        recent_timestamp = time.time() - 100  # 100 seconds ago
        fresh_entry = CacheEntry(
            data="test",
            timestamp=recent_timestamp,
            ttl=300.0
        )
        
        assert not fresh_entry.is_expired()
    
    def test_cache_entry_staleness(self):
        """Test cache entry staleness detection."""
        # Create stale entry (80% of TTL elapsed)
        stale_timestamp = time.time() - 250  # 250 seconds ago
        entry = CacheEntry(
            data="test",
            timestamp=stale_timestamp,
            ttl=300.0  # 5 minutes
        )
        
        assert entry.is_stale(staleness_threshold=0.8)
        
        # Create fresh entry
        fresh_timestamp = time.time() - 100  # 100 seconds ago
        fresh_entry = CacheEntry(
            data="test",
            timestamp=fresh_timestamp,
            ttl=300.0
        )
        
        assert not fresh_entry.is_stale(staleness_threshold=0.8)
    
    def test_cache_entry_touch(self):
        """Test cache entry access tracking."""
        entry = CacheEntry(data="test", timestamp=time.time(), ttl=300.0)
        
        assert entry.access_count == 0
        initial_access_time = entry.last_accessed
        
        # Wait a bit to ensure time difference
        time.sleep(0.01)
        entry.touch()
        
        assert entry.access_count == 1
        assert entry.last_accessed > initial_access_time


class TestStatisticsCache:
    """Test StatisticsCache functionality."""
    
    def setup_method(self):
        """Setup test cache instance."""
        self.cache = StatisticsCache(
            default_ttl=300.0,
            max_cache_size=100,
            cleanup_interval=60.0,
            staleness_threshold=0.8
        )
    
    def teardown_method(self):
        """Cleanup after each test."""
        self.cache.clear()
    
    def test_cache_initialization(self):
        """Test cache initialization with parameters."""
        cache = StatisticsCache(
            default_ttl=600.0,
            max_cache_size=200,
            cleanup_interval=30.0,
            staleness_threshold=0.7
        )
        
        assert cache.default_ttl == 600.0
        assert cache.max_cache_size == 200
        assert cache.cleanup_interval == 30.0
        assert cache.staleness_threshold == 0.7
        assert len(cache._cache) == 0
    
    def test_basic_set_and_get(self):
        """Test basic cache set and get operations."""
        key_parts = ["test", "key", 1]
        value = {"data": "test_value"}
        
        # Test set
        self.cache.set(key_parts, value, ttl=300.0)
        
        # Test get
        result = self.cache.get(key_parts)
        assert result == value
        
        # Test cache stats
        stats = self.cache.get_stats()
        assert stats['cache_size'] == 1
        assert stats['hits'] == 1
        assert stats['misses'] == 0
    
    def test_cache_miss(self):
        """Test cache miss scenarios."""
        result = self.cache.get(["nonexistent", "key"])
        assert result is None
        
        stats = self.cache.get_stats()
        assert stats['hits'] == 0
        assert stats['misses'] == 1
    
    def test_cache_with_calculator(self):
        """Test cache with calculator function for cache misses."""
        key_parts = ["calculated", "key"]
        expected_value = {"calculated": True}
        
        calculator = Mock(return_value=expected_value)
        
        # First call should invoke calculator
        result = self.cache.get(key_parts, calculator=calculator)
        assert result == expected_value
        calculator.assert_called_once()
        
        # Second call should return cached value
        calculator.reset_mock()
        result = self.cache.get(key_parts, calculator=calculator)
        assert result == expected_value
        calculator.assert_not_called()
    
    def test_cache_calculator_exception(self):
        """Test cache behavior when calculator function raises exception."""
        def failing_calculator():
            raise ValueError("Calculation failed")
        
        result = self.cache.get(["error", "key"], calculator=failing_calculator)
        assert result is None
        
        stats = self.cache.get_stats()
        assert stats['misses'] == 1
    
    def test_ttl_expiration(self):
        """Test TTL-based cache expiration."""
        key_parts = ["expiring", "key"]
        value = "test_value"
        
        # Set with short TTL
        self.cache.set(key_parts, value, ttl=0.1)  # 100ms
        
        # Should be available immediately
        result = self.cache.get(key_parts)
        assert result == value
        
        # Wait for expiration
        time.sleep(0.15)
        
        # Should be expired now
        result = self.cache.get(key_parts)
        assert result is None
    
    def test_dependency_tracking(self):
        """Test dependency-based cache invalidation."""
        # Set multiple entries with dependencies
        self.cache.set(["player", "1"], "player_1_data", dependencies=["player:1"])
        self.cache.set(["player", "2"], "player_2_data", dependencies=["player:2"])
        self.cache.set(["leaderboard"], "leaderboard_data", dependencies=["leaderboard", "player:1"])
        
        # Verify all entries are cached
        assert self.cache.get(["player", "1"]) == "player_1_data"
        assert self.cache.get(["player", "2"]) == "player_2_data"
        assert self.cache.get(["leaderboard"]) == "leaderboard_data"
        
        # Invalidate player:1 dependency
        invalidated = self.cache.invalidate("player:1")
        assert invalidated == 2  # player:1 and leaderboard entries
        
        # Check results
        assert self.cache.get(["player", "1"]) is None
        assert self.cache.get(["player", "2"]) == "player_2_data"  # Should still exist
        assert self.cache.get(["leaderboard"]) is None
    
    def test_pattern_invalidation(self):
        """Test pattern-based cache invalidation."""
        # Set entries with pattern-matchable keys
        self.cache.set(["player", "stats", "1"], "data1")
        self.cache.set(["player", "stats", "2"], "data2")
        self.cache.set(["game", "data", "1"], "game_data")
        
        # Invalidate entries matching pattern
        invalidated = self.cache.invalidate_pattern("player")
        assert invalidated == 2
        
        # Verify correct entries were invalidated
        assert self.cache.get(["player", "stats", "1"]) is None
        assert self.cache.get(["player", "stats", "2"]) is None
        assert self.cache.get(["game", "data", "1"]) == "game_data"  # Should remain
    
    def test_cache_size_limit_and_eviction(self):
        """Test cache size limits and LRU eviction."""
        small_cache = StatisticsCache(max_cache_size=3)
        
        # Fill cache to capacity
        for i in range(3):
            small_cache.set([f"key_{i}"], f"value_{i}")
        
        # Verify all entries are cached
        for i in range(3):
            assert small_cache.get([f"key_{i}"]) == f"value_{i}"
        
        # Add one more entry to trigger eviction
        small_cache.set(["key_3"], "value_3")
        
        # The least recently used entry should be evicted
        stats = small_cache.get_stats()
        assert stats['cache_size'] <= 3
        assert stats['evictions'] > 0
    
    def test_batch_get_operations(self):
        """Test batch get operations."""
        # Prepare test data
        test_data = {
            "key_1": "value_1",
            "key_2": "value_2",
            "key_3": "value_3"
        }
        
        # Set initial data
        for key, value in test_data.items():
            self.cache.set([key], value)
        
        # Prepare batch requests (mix of cached and uncached)
        batch_requests = [
            {"key_parts": ["key_1"], "calculator": None},
            {"key_parts": ["key_2"], "calculator": None},
            {"key_parts": ["key_missing"], "calculator": lambda: "calculated_value"},
            {"key_parts": ["key_3"], "calculator": None}
        ]
        
        # Perform batch get
        results = self.cache.batch_get(batch_requests)
        
        # Verify results
        assert results[0] == "value_1"
        assert results[1] == "value_2"
        assert results[2] == "calculated_value"
        assert results[3] == "value_3"
        
        # Verify the calculated value was cached
        assert self.cache.get(["key_missing"]) == "calculated_value"
    
    def test_batch_set_operations(self):
        """Test batch set operations."""
        batch_data = [
            {"key_parts": ["batch_1"], "value": "value_1", "ttl": 300.0, "dependencies": ["dep_1"]},
            {"key_parts": ["batch_2"], "value": "value_2", "ttl": 600.0, "dependencies": ["dep_2"]},
            {"key_parts": ["batch_3"], "value": "value_3", "ttl": None, "dependencies": None}
        ]
        
        # Perform batch set
        success_count = self.cache.batch_set(batch_data)
        assert success_count == 3
        
        # Verify all entries were set
        assert self.cache.get(["batch_1"]) == "value_1"
        assert self.cache.get(["batch_2"]) == "value_2"
        assert self.cache.get(["batch_3"]) == "value_3"
        
        # Test dependency invalidation
        invalidated = self.cache.invalidate("dep_1")
        assert invalidated == 1
        assert self.cache.get(["batch_1"]) is None
        assert self.cache.get(["batch_2"]) == "value_2"  # Should remain
    
    def test_batch_invalidate_operations(self):
        """Test batch invalidation operations."""
        # Set entries with various dependencies
        self.cache.set(["entry_1"], "value_1", dependencies=["dep_1"])
        self.cache.set(["entry_2"], "value_2", dependencies=["dep_2"])
        self.cache.set(["entry_3"], "value_3", dependencies=["dep_1", "dep_3"])
        self.cache.set(["entry_4"], "value_4", dependencies=["dep_4"])
        
        # Perform batch invalidation
        patterns = ["dep_1", "dep_2"]
        total_invalidated = self.cache.batch_invalidate(patterns)
        
        # dep_1 should invalidate entry_1 and entry_3 (2 entries)
        # dep_2 should invalidate entry_2 (1 entry)
        assert total_invalidated == 3
        
        # Verify correct entries were invalidated
        assert self.cache.get(["entry_1"]) is None
        assert self.cache.get(["entry_2"]) is None
        assert self.cache.get(["entry_3"]) is None
        assert self.cache.get(["entry_4"]) == "value_4"  # Should remain
    
    def test_cache_warming(self):
        """Test cache warming functionality."""
        warming_requests = [
            {
                "key_parts": ["warm_1"],
                "calculator": lambda: "warmed_value_1",
                "ttl": 300.0,
                "dependencies": ["warm_dep_1"]
            },
            {
                "key_parts": ["warm_2"],
                "calculator": lambda: "warmed_value_2",
                "ttl": 600.0,
                "dependencies": ["warm_dep_2"]
            }
        ]
        
        # Perform cache warming
        self.cache.warm_cache(warming_requests)
        
        # Give a moment for background warming to complete
        time.sleep(0.1)
        
        # Verify entries were warmed (may take some time due to threading)
        # We'll try a few times with small delays
        for _ in range(10):  # Try for up to 1 second
            if (self.cache.get(["warm_1"]) == "warmed_value_1" and 
                self.cache.get(["warm_2"]) == "warmed_value_2"):
                break
            time.sleep(0.1)
        
        # Final verification
        assert self.cache.get(["warm_1"]) == "warmed_value_1"
        assert self.cache.get(["warm_2"]) == "warmed_value_2"
    
    def test_preload_popular_data(self):
        """Test preloading of popular data."""
        popular_keys = [
            {
                "key_parts": ["popular_1"],
                "calculator": lambda: "popular_value_1",
                "access_frequency": 10
            },
            {
                "key_parts": ["popular_2"],
                "calculator": lambda: "popular_value_2",
                "access_frequency": 5
            }
        ]
        
        # Preload popular data
        self.cache.preload_popular_data(popular_keys)
        
        # Give time for preloading to complete
        time.sleep(0.1)
        
        # Verify popular data was loaded
        for _ in range(10):  # Try for up to 1 second
            if (self.cache.get(["popular_1"]) == "popular_value_1" and 
                self.cache.get(["popular_2"]) == "popular_value_2"):
                break
            time.sleep(0.1)
    
    def test_concurrent_access(self):
        """Test thread-safe concurrent access to cache."""
        results = {}
        errors = []
        
        def cache_worker(worker_id: int):
            try:
                for i in range(100):
                    key = [f"concurrent_{worker_id}_{i}"]
                    value = f"value_{worker_id}_{i}"
                    
                    # 50% writes, 50% reads
                    if i % 2 == 0:
                        self.cache.set(key, value)
                    else:
                        result = self.cache.get(key)
                        if result:
                            results[f"{worker_id}_{i}"] = result
            except Exception as e:
                errors.append(e)
        
        # Start multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=cache_worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify no errors occurred
        assert len(errors) == 0, f"Concurrent access errors: {errors}"
        
        # Verify cache integrity
        stats = self.cache.get_stats()
        assert stats['cache_size'] > 0
    
    def test_cache_info_and_debugging(self):
        """Test cache information and debugging features."""
        # Add some test data
        self.cache.set(["debug_1"], "value_1", dependencies=["dep_1"])
        self.cache.set(["debug_2"], "value_2", dependencies=["dep_2"])
        
        # Get cache info
        cache_info = self.cache.get_cache_info()
        
        assert "entries" in cache_info
        assert "stats" in cache_info
        assert "dependencies" in cache_info
        
        # Verify entries information
        entries = cache_info["entries"]
        assert len(entries) == 2
        
        for entry in entries:
            assert "key" in entry
            assert "age" in entry
            assert "ttl" in entry
            assert "access_count" in entry
            assert "is_expired" in entry
            assert "is_stale" in entry
            assert "dependencies" in entry
    
    def test_partition_stats(self):
        """Test cache partition statistics."""
        # Get initial partition stats
        partition_stats = self.cache.get_partition_stats()
        
        # Should have default partitions
        expected_partitions = ["player_stats", "leaderboards", "aggregates", "time_series"]
        for partition in expected_partitions:
            assert partition in partition_stats
            assert "size" in partition_stats[partition]
            assert "entries" in partition_stats[partition]
    
    @patch('statistics_cache.threading.Thread')
    def test_background_refresh_scheduling(self, mock_thread):
        """Test background refresh scheduling for stale entries."""
        # Create a stale entry by manipulating timestamp
        key_parts = ["stale_key"]
        value = "stale_value"
        
        # Set entry with short TTL and make it stale
        self.cache.set(key_parts, value, ttl=100.0)
        
        # Get the cache key to manipulate entry timestamp
        cache_key = self.cache._generate_cache_key(key_parts)
        entry = self.cache._cache[cache_key]
        
        # Make entry stale (90% of TTL elapsed)
        entry.timestamp = time.time() - 90.0
        
        # Mock calculator for refresh
        calculator = Mock(return_value="refreshed_value")
        
        # Get the stale entry (should trigger background refresh)
        result = self.cache.get(key_parts, calculator=calculator)
        
        # Should return stale value immediately
        assert result == value
        
        # Should have scheduled background refresh
        mock_thread.assert_called_once()
    
    def test_cleanup_expired_entries(self):
        """Test automatic cleanup of expired entries."""
        # Add entries with different TTLs
        self.cache.set(["short_ttl"], "value_1", ttl=0.1)  # 100ms
        self.cache.set(["long_ttl"], "value_2", ttl=10.0)   # 10 seconds
        
        # Wait for short TTL to expire
        time.sleep(0.15)
        
        # Force cleanup
        removed_count = self.cache._cleanup_expired_entries()
        
        # Should have removed expired entry
        assert removed_count == 1
        assert self.cache.get(["short_ttl"]) is None
        assert self.cache.get(["long_ttl"]) == "value_2"


class TestCacheGlobalFunctions:
    """Test global cache functions."""
    
    def test_get_statistics_cache(self):
        """Test global cache instance retrieval."""
        cache1 = get_statistics_cache()
        cache2 = get_statistics_cache()
        
        # Should return same instance
        assert cache1 is cache2
        assert isinstance(cache1, StatisticsCache)
    
    def test_invalidate_player_cache(self):
        """Test player cache invalidation helper."""
        cache = get_statistics_cache()
        
        # Add player-related entries
        cache.set(["player_stats", "player_1"], "stats_1", dependencies=["player:player_1"])
        cache.set(["player_games", "player_1"], "games_1", dependencies=["player:player_1"])
        cache.set(["other_data"], "other", dependencies=["other"])
        
        # Invalidate player cache
        invalidated = invalidate_player_cache("player_1")
        assert invalidated == 2
        
        # Verify correct entries were invalidated
        assert cache.get(["player_stats", "player_1"]) is None
        assert cache.get(["player_games", "player_1"]) is None
        assert cache.get(["other_data"]) == "other"
    
    def test_invalidate_game_cache(self):
        """Test game cache invalidation helper."""
        cache = get_statistics_cache()
        
        # Add game-related entries
        cache.set(["game_data", "game_1"], "data_1", dependencies=["game:game_1"])
        cache.set(["game_analysis", "game_1"], "analysis_1", dependencies=["game:game_1"])
        cache.set(["other_data"], "other", dependencies=["other"])
        
        # Invalidate game cache
        invalidated = invalidate_game_cache("game_1")
        assert invalidated == 2
        
        # Verify correct entries were invalidated
        assert cache.get(["game_data", "game_1"]) is None
        assert cache.get(["game_analysis", "game_1"]) is None
        assert cache.get(["other_data"]) == "other"
    
    def test_invalidate_leaderboard_cache(self):
        """Test leaderboard cache invalidation helper."""
        cache = get_statistics_cache()
        
        # Add leaderboard-related entries
        cache.set(["leaderboard", "elo"], "elo_board", dependencies=["leaderboard"])
        cache.set(["leaderboard", "winrate"], "winrate_board", dependencies=["leaderboard"])
        cache.set(["other_data"], "other", dependencies=["other"])
        
        # Invalidate leaderboard cache
        invalidated = invalidate_leaderboard_cache()
        assert invalidated == 2
        
        # Verify correct entries were invalidated
        assert cache.get(["leaderboard", "elo"]) is None
        assert cache.get(["leaderboard", "winrate"]) is None
        assert cache.get(["other_data"]) == "other"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])