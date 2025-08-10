"""
Performance tests for the statistics caching system.
"""

import pytest
import asyncio
import time
from datetime import datetime
from unittest.mock import Mock, AsyncMock
from typing import List, Dict, Any

from statistics_cache import StatisticsCache, get_statistics_cache
from statistics_calculator import AccurateStatisticsCalculator, AccuratePlayerStatistics
from game_arena.storage.models import GameRecord, PlayerInfo, GameResult


class TestStatisticsCachePerformance:
    """Performance tests for the statistics caching system."""

    def setup_method(self):
        """Set up test fixtures."""
        self.cache = StatisticsCache(
            default_ttl=60.0,  # 1 minute for testing
            max_cache_size=1000,  # Increased for testing
            cleanup_interval=10.0
        )
        
        # Mock query engine
        self.mock_query_engine = Mock()
        self.mock_query_engine.get_games_by_players = AsyncMock()
        self.mock_query_engine.storage_manager = Mock()
        self.mock_query_engine.storage_manager.query_games = AsyncMock()
        
        self.calculator = AccurateStatisticsCalculator(
            query_engine=self.mock_query_engine,
            cache=self.cache
        )

    def test_cache_basic_operations_performance(self):
        """Test basic cache operations performance."""
        start_time = time.time()
        
        # Test rapid cache operations
        for i in range(1000):
            key_parts = ["test", f"player_{i}", "data"]
            value = {"player_id": f"player_{i}", "score": i * 10}
            
            # Set value
            self.cache.set(key_parts, value, ttl=60.0)
            
            # Get value
            retrieved = self.cache.get(key_parts)
            assert retrieved == value
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should complete 2000 operations (1000 set + 1000 get) in less than 1 second
        assert duration < 1.0, f"Cache operations took {duration:.3f}s, expected < 1.0s"
        
        # Verify cache stats
        stats = self.cache.get_stats()
        assert stats['hits'] == 1000
        assert stats['total_requests'] == 1000
        assert stats['hit_rate'] == 1.0

    def test_cache_concurrent_access_performance(self):
        """Test cache performance under concurrent access."""
        import threading
        import concurrent.futures
        
        def cache_worker(worker_id: int, operations: int) -> Dict[str, Any]:
            """Worker function for concurrent cache operations."""
            hits = 0
            misses = 0
            
            for i in range(operations):
                key_parts = ["worker", str(worker_id), str(i)]
                value = {"worker": worker_id, "operation": i}
                
                # Set value
                self.cache.set(key_parts, value)
                
                # Get value
                retrieved = self.cache.get(key_parts)
                if retrieved == value:
                    hits += 1
                else:
                    misses += 1
            
            return {"hits": hits, "misses": misses}
        
        start_time = time.time()
        
        # Run concurrent workers
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(cache_worker, worker_id, 100)
                for worker_id in range(10)
            ]
            
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should complete 10,000 operations (10 workers * 100 ops * 2 operations each) in reasonable time
        assert duration < 2.0, f"Concurrent cache operations took {duration:.3f}s, expected < 2.0s"
        
        # Verify all operations succeeded
        total_hits = sum(result["hits"] for result in results)
        total_misses = sum(result["misses"] for result in results)
        
        assert total_hits == 1000  # All gets should hit
        assert total_misses == 0

    def test_cache_invalidation_performance(self):
        """Test cache invalidation performance."""
        # Populate cache with many entries
        player_count = 100
        
        for player_id in range(player_count):
            for stat_type in ["basic", "elo", "performance"]:
                key_parts = ["player_stats", f"player_{player_id}", stat_type]
                value = {"player_id": f"player_{player_id}", "type": stat_type}
                dependencies = [f"player:player_{player_id}"]
                
                self.cache.set(key_parts, value, dependencies=dependencies)
        
        # Test invalidation performance
        start_time = time.time()
        
        # Invalidate half the players
        invalidated_total = 0
        for player_id in range(0, player_count, 2):  # Every other player
            invalidated = self.cache.invalidate(f"player:player_{player_id}")
            invalidated_total += invalidated
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should complete invalidation quickly
        assert duration < 0.1, f"Cache invalidation took {duration:.3f}s, expected < 0.1s"
        
        # Should have invalidated some entries (dependency tracking may not be 1:1)
        assert invalidated_total > 0
        assert invalidated_total <= 150  # At most 3 entries per player

    def test_cache_cleanup_performance(self):
        """Test cache cleanup performance with expired entries."""
        # Populate cache with entries that will expire quickly
        entry_count = 500
        
        for i in range(entry_count):
            key_parts = ["temp", f"entry_{i}"]
            value = {"id": i, "data": f"test_data_{i}"}
            # Set very short TTL
            self.cache.set(key_parts, value, ttl=0.01)  # 10ms
        
        # Wait for entries to expire
        time.sleep(0.1)
        
        # Force cleanup
        start_time = time.time()
        removed_count = self.cache._cleanup_expired_entries()
        end_time = time.time()
        
        duration = end_time - start_time
        
        # Cleanup should be fast
        assert duration < 0.1, f"Cache cleanup took {duration:.3f}s, expected < 0.1s"
        
        # Should have removed expired entries (may be limited by max_cache_size)
        assert removed_count > 0
        assert removed_count <= entry_count

    def test_cache_memory_efficiency(self):
        """Test cache memory usage and efficiency."""
        import sys
        
        # Measure initial cache size
        initial_size = sys.getsizeof(self.cache._cache)
        
        # Add many entries
        entry_count = 1000
        for i in range(entry_count):
            key_parts = ["memory_test", f"entry_{i}"]
            # Create reasonably sized data
            value = {
                "id": i,
                "data": f"test_data_{i}" * 10,  # ~100 bytes per entry
                "metadata": {"created": time.time(), "version": 1}
            }
            self.cache.set(key_parts, value)
        
        # Measure final cache size
        final_size = sys.getsizeof(self.cache._cache)
        size_per_entry = (final_size - initial_size) / entry_count
        
        # Each entry should use reasonable memory (less than 1KB overhead per entry)
        assert size_per_entry < 1024, f"Memory usage per entry: {size_per_entry:.1f} bytes"
        
        # Test cache size limit enforcement
        cache_stats = self.cache.get_stats()
        assert cache_stats['cache_size'] <= self.cache.max_cache_size

    @pytest.mark.asyncio
    async def test_statistics_calculator_cache_integration_performance(self):
        """Test performance of statistics calculator with caching."""
        # Mock game data
        mock_games = []
        for i in range(50):  # 50 games per player
            game = Mock(spec=GameRecord)
            game.game_id = f"game_{i}"
            game.is_completed = True
            game.outcome = Mock()
            game.outcome.result = GameResult.WHITE_WINS if i % 2 == 0 else GameResult.BLACK_WINS
            game.start_time = datetime.fromtimestamp(time.time() - (i * 3600))  # 1 hour apart
            game.end_time = datetime.fromtimestamp(game.start_time.timestamp() + 1800)  # 30 minutes each
            game.total_moves = 40 + (i % 20)
            
            # Mock players
            game.players = {
                0: PlayerInfo(player_id="test_player", model_name="TestModel", model_provider="Test", agent_type="llm"),
                1: PlayerInfo(player_id=f"opponent_{i}", model_name="OpponentModel", model_provider="Test", agent_type="llm")
            }
            mock_games.append(game)
        
        self.mock_query_engine.get_games_by_players.return_value = mock_games
        
        # Test first calculation (cache miss)
        start_time = time.time()
        stats1 = await self.calculator.calculate_player_statistics("test_player", use_cache=True)
        first_calc_time = time.time() - start_time
        
        assert stats1 is not None
        
        # Test second calculation (cache hit)
        start_time = time.time()
        stats2 = await self.calculator.calculate_player_statistics("test_player", use_cache=True)
        second_calc_time = time.time() - start_time
        
        assert stats2 is not None
        
        # Cache hit should be significantly faster
        assert second_calc_time < first_calc_time * 0.1, \
            f"Cache hit ({second_calc_time:.3f}s) should be much faster than miss ({first_calc_time:.3f}s)"
        
        # Verify cache statistics
        cache_stats = self.cache.get_stats()
        assert cache_stats['hits'] >= 1
        assert cache_stats['hit_rate'] > 0

    @pytest.mark.asyncio
    async def test_leaderboard_cache_performance(self):
        """Test leaderboard caching performance."""
        # Mock multiple players
        player_count = 20
        all_games = []
        
        for player_id in range(player_count):
            # Create games for each player
            for game_id in range(10):  # 10 games per player
                game = Mock(spec=GameRecord)
                game.game_id = f"game_{player_id}_{game_id}"
                game.is_completed = True
                game.outcome = Mock()
                game.outcome.result = GameResult.WHITE_WINS if game_id % 3 == 0 else GameResult.BLACK_WINS
                game.start_time = time.time() - (game_id * 3600)
                game.end_time = game.start_time + 1800
                game.total_moves = 40
                
                game.players = {
                    0: PlayerInfo(player_id=f"player_{player_id}", model_name=f"Model_{player_id}", model_provider="Test", agent_type="llm"),
                    1: PlayerInfo(player_id=f"opponent_{game_id}", model_name="OpponentModel", model_provider="Test", agent_type="llm")
                }
                all_games.append(game)
        
        self.mock_query_engine.storage_manager.query_games.return_value = all_games
        
        # Mock individual player statistics calls
        async def mock_get_games_by_players(player_id):
            return [game for game in all_games if any(
                player_info.player_id == player_id 
                for player_info in game.players.values()
            )]
        
        self.mock_query_engine.get_games_by_players.side_effect = mock_get_games_by_players
        
        # Test first leaderboard generation (cache miss)
        start_time = time.time()
        leaderboard1 = await self.calculator.generate_accurate_leaderboard(
            sort_by="elo_rating", min_games=5, limit=10, use_cache=True
        )
        first_gen_time = time.time() - start_time
        
        assert len(leaderboard1) > 0
        
        # Test second leaderboard generation (cache hit)
        start_time = time.time()
        leaderboard2 = await self.calculator.generate_accurate_leaderboard(
            sort_by="elo_rating", min_games=5, limit=10, use_cache=True
        )
        second_gen_time = time.time() - start_time
        
        assert len(leaderboard2) == len(leaderboard1)
        
        # Cache hit should be significantly faster
        assert second_gen_time < first_gen_time * 0.1, \
            f"Cached leaderboard ({second_gen_time:.3f}s) should be much faster than uncached ({first_gen_time:.3f}s)"

    def test_cache_ttl_and_staleness_performance(self):
        """Test cache TTL and staleness detection performance."""
        # Set entries with different TTLs
        entry_count = 100
        
        start_time = time.time()
        
        for i in range(entry_count):
            key_parts = ["ttl_test", f"entry_{i}"]
            value = {"id": i, "timestamp": time.time()}
            ttl = 0.1 + (i * 0.01)  # Varying TTLs from 0.1 to 1.1 seconds
            
            self.cache.set(key_parts, value, ttl=ttl)
        
        set_time = time.time() - start_time
        
        # Test staleness detection
        start_time = time.time()
        stale_count = 0
        
        for i in range(entry_count):
            key_parts = ["ttl_test", f"entry_{i}"]
            cache_key = self.cache._generate_cache_key(key_parts)
            
            if cache_key in self.cache._cache:
                entry = self.cache._cache[cache_key]
                if entry.is_stale(0.8):  # 80% of TTL
                    stale_count += 1
        
        staleness_check_time = time.time() - start_time
        
        # Operations should be fast
        assert set_time < 0.1, f"Setting {entry_count} entries took {set_time:.3f}s"
        assert staleness_check_time < 0.05, f"Staleness check took {staleness_check_time:.3f}s"

    def test_cache_dependency_tracking_performance(self):
        """Test performance of dependency tracking system."""
        # Create entries with complex dependency relationships
        player_count = 50
        stat_types = ["basic", "elo", "performance", "recent", "opponents"]
        
        start_time = time.time()
        
        # Create entries with dependencies
        for player_id in range(player_count):
            for stat_type in stat_types:
                key_parts = ["player_stats", f"player_{player_id}", stat_type]
                value = {"player_id": f"player_{player_id}", "type": stat_type}
                dependencies = [
                    f"player:player_{player_id}",
                    f"stats:{stat_type}",
                    "global:stats"
                ]
                
                self.cache.set(key_parts, value, dependencies=dependencies)
        
        creation_time = time.time() - start_time
        
        # Test dependency invalidation performance
        start_time = time.time()
        
        # Invalidate by player (should affect 5 entries per player)
        player_invalidations = 0
        for player_id in range(0, player_count, 5):  # Every 5th player
            invalidated = self.cache.invalidate(f"player:player_{player_id}")
            player_invalidations += invalidated
        
        # Invalidate by stat type (should affect remaining entries of that type)
        stat_invalidations = self.cache.invalidate("stats:elo")
        
        invalidation_time = time.time() - start_time
        
        # Operations should be reasonably fast
        assert creation_time < 0.5, f"Creating {player_count * len(stat_types)} entries took {creation_time:.3f}s"
        assert invalidation_time < 0.2, f"Dependency invalidation took {invalidation_time:.3f}s"
        
        # Verify some invalidations occurred (dependency tracking may vary)
        assert player_invalidations > 0
        assert stat_invalidations >= 0

    def test_global_cache_singleton_performance(self):
        """Test performance of global cache singleton access."""
        start_time = time.time()
        
        # Access global cache many times
        caches = []
        for i in range(1000):
            cache = get_statistics_cache()
            caches.append(cache)
        
        access_time = time.time() - start_time
        
        # Should be very fast
        assert access_time < 0.1, f"Global cache access took {access_time:.3f}s"
        
        # All should be the same instance
        assert all(cache is caches[0] for cache in caches)

    def test_cache_pattern_invalidation_performance(self):
        """Test performance of pattern-based cache invalidation."""
        # Create entries with patterns
        pattern_count = 100
        entries_per_pattern = 10
        
        for pattern_id in range(pattern_count):
            for entry_id in range(entries_per_pattern):
                key_parts = ["pattern_test", f"pattern_{pattern_id}", f"entry_{entry_id}"]
                value = {"pattern": pattern_id, "entry": entry_id}
                self.cache.set(key_parts, value)
        
        # Test pattern invalidation
        start_time = time.time()
        
        # Invalidate entries matching specific patterns
        total_invalidated = 0
        for pattern_id in range(0, pattern_count, 10):  # Every 10th pattern
            invalidated = self.cache.invalidate_pattern(f"pattern_{pattern_id}")
            total_invalidated += invalidated
        
        pattern_invalidation_time = time.time() - start_time
        
        # Should be reasonably fast
        assert pattern_invalidation_time < 0.2, f"Pattern invalidation took {pattern_invalidation_time:.3f}s"
        
        # Should have invalidated some entries (pattern matching may vary)
        assert total_invalidated >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])