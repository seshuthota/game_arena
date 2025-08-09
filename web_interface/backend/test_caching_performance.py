"""
Comprehensive performance tests for the caching and optimization system.

This module provides extensive testing for cache performance, batch processing,
cache management, and overall system performance under various load conditions.
"""

import asyncio
import pytest
import time
import threading
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
import random
import statistics as stats
from unittest.mock import Mock, AsyncMock, patch

from statistics_cache import StatisticsCache
from batch_statistics_processor import BatchStatisticsProcessor, BatchCalculationRequest
from cache_manager import CacheManager, CacheStrategy, CacheType
from performance_monitor import PerformanceMonitor, MetricType
from caching_middleware import ResponseCachingMiddleware, CacheConfig


class MockQueryEngine:
    """Mock query engine for testing."""
    
    def __init__(self, delay: float = 0.1):
        self.delay = delay
        self.call_count = 0
        self.games_data = self._generate_mock_games()
        self.players_data = self._generate_mock_players()
    
    def _generate_mock_games(self):
        """Generate mock game data."""
        games = []
        for i in range(1000):
            games.append({
                'game_id': f'game_{i}',
                'players': {
                    '0': {'player_id': f'player_{i % 100}', 'model_name': f'model_{i % 10}'},
                    '1': {'player_id': f'player_{(i + 50) % 100}', 'model_name': f'model_{(i + 5) % 10}'}
                },
                'total_moves': random.randint(20, 100),
                'is_completed': True
            })
        return games
    
    def _generate_mock_players(self):
        """Generate mock player data."""
        players = {}
        for i in range(100):
            players[f'player_{i}'] = {
                'player_id': f'player_{i}',
                'model_name': f'model_{i % 10}',
                'games_played': random.randint(5, 50),
                'wins': random.randint(0, 25),
                'losses': random.randint(0, 25),
                'draws': random.randint(0, 10),
                'elo_rating': random.randint(1200, 1800)
            }
        return players
    
    async def query_games(self, filters=None):
        """Mock game query with artificial delay."""
        await asyncio.sleep(self.delay)
        self.call_count += 1
        return self.games_data
    
    async def get_player_statistics(self, player_id: str):
        """Mock player statistics with artificial delay."""
        await asyncio.sleep(self.delay)
        self.call_count += 1
        return self.players_data.get(player_id)


class PerformanceTestSuite:
    """Comprehensive performance test suite."""
    
    def __init__(self):
        self.mock_query_engine = MockQueryEngine()
        self.cache = StatisticsCache(
            default_ttl=300.0,
            max_cache_size=1000,
            cleanup_interval=60.0
        )
        self.batch_processor = BatchStatisticsProcessor(
            query_engine=self.mock_query_engine,
            cache=self.cache,
            max_workers=4,
            batch_size=50
        )
        self.cache_manager = CacheManager(
            primary_cache=self.cache,
            batch_processor=self.batch_processor,
            warming_strategy=CacheStrategy.MODERATE
        )
        self.performance_monitor = PerformanceMonitor(
            cache=self.cache,
            batch_processor=self.batch_processor,
            cache_manager=self.cache_manager
        )
    
    async def test_cache_basic_performance(self) -> Dict[str, float]:
        """Test basic cache operations performance."""
        print("Testing basic cache performance...")
        
        results = {}
        test_data = [(f"key_{i}", f"value_{i}") for i in range(1000)]
        
        # Test SET operations
        start_time = time.time()
        for key, value in test_data:
            self.cache.set([key], value, ttl=300.0)
        set_time = time.time() - start_time
        results['set_ops_per_second'] = len(test_data) / set_time
        
        # Test GET operations (cache hits)
        start_time = time.time()
        for key, _ in test_data:
            result = self.cache.get([key])
            assert result is not None
        get_time = time.time() - start_time
        results['get_ops_per_second'] = len(test_data) / get_time
        
        # Test cache miss performance
        start_time = time.time()
        for i in range(100):
            result = self.cache.get([f"nonexistent_key_{i}"])
            assert result is None
        miss_time = time.time() - start_time
        results['miss_ops_per_second'] = 100 / miss_time
        
        print(f"Cache SET: {results['set_ops_per_second']:.0f} ops/sec")
        print(f"Cache GET (hits): {results['get_ops_per_second']:.0f} ops/sec")
        print(f"Cache GET (misses): {results['miss_ops_per_second']:.0f} ops/sec")
        
        return results
    
    async def test_batch_operations_performance(self) -> Dict[str, float]:
        """Test batch cache operations performance."""
        print("Testing batch operations performance...")
        
        results = {}
        
        # Test batch_set
        batch_data = [
            {
                'key_parts': [f'batch_key_{i}'],
                'value': f'batch_value_{i}',
                'ttl': 300.0,
                'dependencies': [f'dep_{i % 10}']
            }
            for i in range(1000)
        ]
        
        start_time = time.time()
        success_count = self.cache.batch_set(batch_data)
        batch_set_time = time.time() - start_time
        results['batch_set_ops_per_second'] = success_count / batch_set_time
        
        # Test batch_get
        batch_requests = [
            {
                'key_parts': [f'batch_key_{i}'],
                'calculator': None,
                'ttl': 300.0,
                'dependencies': [f'dep_{i % 10}']
            }
            for i in range(1000)
        ]
        
        start_time = time.time()
        batch_results = self.cache.batch_get(batch_requests)
        batch_get_time = time.time() - start_time
        results['batch_get_ops_per_second'] = len(batch_results) / batch_get_time
        
        print(f"Batch SET: {results['batch_set_ops_per_second']:.0f} ops/sec")
        print(f"Batch GET: {results['batch_get_ops_per_second']:.0f} ops/sec")
        
        return results
    
    async def test_concurrent_access_performance(self) -> Dict[str, Any]:
        """Test cache performance under concurrent access."""
        print("Testing concurrent access performance...")
        
        results = {}
        num_threads = 10
        operations_per_thread = 100
        
        def cache_worker(thread_id: int) -> Dict[str, float]:
            """Worker function for concurrent testing."""
            start_time = time.time()
            operations = 0
            
            for i in range(operations_per_thread):
                key = f"concurrent_{thread_id}_{i}"
                
                # 70% reads, 30% writes
                if random.random() < 0.7:
                    self.cache.get([key])
                else:
                    self.cache.set([key], f"value_{thread_id}_{i}", ttl=300.0)
                
                operations += 1
            
            duration = time.time() - start_time
            return {
                'thread_id': thread_id,
                'operations': operations,
                'duration': duration,
                'ops_per_second': operations / duration
            }
        
        # Run concurrent operations
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [
                executor.submit(cache_worker, thread_id)
                for thread_id in range(num_threads)
            ]
            
            thread_results = []
            for future in as_completed(futures):
                thread_results.append(future.result())
        
        # Calculate aggregate statistics
        all_ops_per_second = [r['ops_per_second'] for r in thread_results]
        results['total_operations'] = sum(r['operations'] for r in thread_results)
        results['total_duration'] = max(r['duration'] for r in thread_results)
        results['average_ops_per_second'] = stats.mean(all_ops_per_second)
        results['total_throughput'] = results['total_operations'] / results['total_duration']
        results['ops_per_second_stddev'] = stats.stdev(all_ops_per_second)
        
        print(f"Concurrent throughput: {results['total_throughput']:.0f} ops/sec")
        print(f"Average per-thread: {results['average_ops_per_second']:.0f} ops/sec")
        print(f"Std deviation: {results['ops_per_second_stddev']:.0f} ops/sec")
        
        return results
    
    async def test_batch_processor_performance(self) -> Dict[str, Any]:
        """Test batch statistics processor performance."""
        print("Testing batch processor performance...")
        
        results = {}
        
        # Test small batch
        small_player_ids = [f"player_{i}" for i in range(10)]
        small_request = BatchCalculationRequest(
            player_ids=small_player_ids,
            calculation_type="statistics",
            include_incomplete_data=True,
            cache_results=True
        )
        
        start_time = time.time()
        small_result = await self.batch_processor.process_batch_statistics(small_request)
        small_duration = time.time() - start_time
        
        results['small_batch'] = {
            'player_count': len(small_player_ids),
            'duration': small_duration,
            'players_per_second': len(small_player_ids) / small_duration,
            'cache_hit_rate': small_result.cache_hits / (small_result.cache_hits + small_result.cache_misses) * 100,
            'success_rate': len(small_result.results) / len(small_player_ids) * 100
        }
        
        # Test medium batch
        medium_player_ids = [f"player_{i}" for i in range(50)]
        medium_request = BatchCalculationRequest(
            player_ids=medium_player_ids,
            calculation_type="statistics",
            include_incomplete_data=True,
            cache_results=True
        )
        
        start_time = time.time()
        medium_result = await self.batch_processor.process_batch_statistics(medium_request)
        medium_duration = time.time() - start_time
        
        results['medium_batch'] = {
            'player_count': len(medium_player_ids),
            'duration': medium_duration,
            'players_per_second': len(medium_player_ids) / medium_duration,
            'cache_hit_rate': medium_result.cache_hits / (medium_result.cache_hits + medium_result.cache_misses) * 100,
            'success_rate': len(medium_result.results) / len(medium_player_ids) * 100
        }
        
        # Test large batch
        large_player_ids = [f"player_{i}" for i in range(100)]
        large_request = BatchCalculationRequest(
            player_ids=large_player_ids,
            calculation_type="statistics",
            include_incomplete_data=True,
            cache_results=True
        )
        
        start_time = time.time()
        large_result = await self.batch_processor.process_batch_statistics(large_request)
        large_duration = time.time() - start_time
        
        results['large_batch'] = {
            'player_count': len(large_player_ids),
            'duration': large_duration,
            'players_per_second': len(large_player_ids) / large_duration,
            'cache_hit_rate': large_result.cache_hits / (large_result.cache_hits + large_result.cache_misses) * 100,
            'success_rate': len(large_result.results) / len(large_player_ids) * 100
        }
        
        # Print results
        for batch_size, metrics in results.items():
            print(f"{batch_size.title()} ({metrics['player_count']} players):")
            print(f"  Duration: {metrics['duration']:.2f}s")
            print(f"  Throughput: {metrics['players_per_second']:.1f} players/sec")
            print(f"  Cache hit rate: {metrics['cache_hit_rate']:.1f}%")
            print(f"  Success rate: {metrics['success_rate']:.1f}%")
        
        return results
    
    async def test_cache_manager_performance(self) -> Dict[str, Any]:
        """Test cache manager performance and optimization."""
        print("Testing cache manager performance...")
        
        results = {}
        
        # Test cache warming performance
        warming_requests = [
            {
                'key_parts': ['warm', f'key_{i}'],
                'calculator': lambda i=i: f"calculated_value_{i}",
                'ttl': 300.0,
                'dependencies': [f'dep_{i % 5}'],
                'access_frequency': random.randint(1, 10)
            }
            for i in range(100)
        ]
        
        start_time = time.time()
        warmed_count = await self.cache_manager.warm_popular_data(top_n=50)
        warming_duration = time.time() - start_time
        
        results['cache_warming'] = {
            'requests_count': len(warming_requests),
            'warmed_count': warmed_count,
            'duration': warming_duration,
            'warming_rate': warmed_count / warming_duration if warming_duration > 0 else 0
        }
        
        # Test intelligent cache retrieval
        cache_retrieval_times = []
        
        for i in range(100):
            start_time = time.time()
            result = await self.cache_manager.get_with_warming(
                cache_type=CacheType.PLAYER_STATISTICS,
                key_parts=['player_stats', f'player_{i % 10}'],
                calculator=lambda: f"calculated_stats_{i}",
                ttl=300.0,
                dependencies=[f'player:{i % 10}']
            )
            retrieval_time = time.time() - start_time
            cache_retrieval_times.append(retrieval_time)
        
        results['intelligent_retrieval'] = {
            'requests_count': len(cache_retrieval_times),
            'average_time': stats.mean(cache_retrieval_times),
            'min_time': min(cache_retrieval_times),
            'max_time': max(cache_retrieval_times),
            'time_stddev': stats.stdev(cache_retrieval_times)
        }
        
        # Test optimization suggestions
        start_time = time.time()
        optimization_suggestions = await self.cache_manager.optimize_cache_performance()
        optimization_time = time.time() - start_time
        
        results['optimization'] = {
            'suggestions_count': len(optimization_suggestions),
            'analysis_time': optimization_time,
            'high_priority_suggestions': len([s for s in optimization_suggestions if s.priority >= 3])
        }
        
        # Print results
        print(f"Cache warming: {results['cache_warming']['warmed_count']} entries in {results['cache_warming']['duration']:.2f}s")
        print(f"Intelligent retrieval: {results['intelligent_retrieval']['average_time']*1000:.1f}ms average")
        print(f"Optimization analysis: {results['optimization']['suggestions_count']} suggestions in {results['optimization']['analysis_time']*1000:.1f}ms")
        
        return results
    
    async def test_performance_monitor(self) -> Dict[str, Any]:
        """Test performance monitoring system."""
        print("Testing performance monitor...")
        
        results = {}
        
        # Start monitoring
        self.performance_monitor.start_monitoring()
        
        # Wait for some metrics collection
        await asyncio.sleep(2)
        
        # Generate some load to create metrics
        for i in range(50):
            self.cache.set([f'monitor_test_{i}'], f'value_{i}', ttl=300.0)
            self.cache.get([f'monitor_test_{i}'])
        
        # Wait for metrics collection
        await asyncio.sleep(3)
        
        # Get current metrics
        current_metrics = self.performance_monitor.get_current_metrics()
        
        # Generate health report
        health_report = self.performance_monitor.generate_health_report()
        
        # Stop monitoring
        self.performance_monitor.stop_monitoring()
        
        results = {
            'metrics_collected': len(current_metrics),
            'health_score': health_report.overall_health_score,
            'cache_performance_score': health_report.cache_performance_score,
            'active_alerts': len(health_report.alerts),
            'trends_detected': len(health_report.trends),
            'recommendations': len(health_report.recommendations),
            'uptime_seconds': health_report.uptime.total_seconds()
        }
        
        print(f"Performance monitoring:")
        print(f"  Health score: {results['health_score']:.1f}/100")
        print(f"  Metrics collected: {results['metrics_collected']}")
        print(f"  Trends detected: {results['trends_detected']}")
        print(f"  Recommendations: {results['recommendations']}")
        
        return results
    
    async def test_memory_usage(self) -> Dict[str, Any]:
        """Test memory usage under load."""
        print("Testing memory usage...")
        
        import psutil
        import gc
        
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Load test data
        large_data_set = []
        for i in range(10000):
            key = f'memory_test_{i}'
            value = {'large_data': 'x' * 1000, 'index': i, 'timestamp': time.time()}
            self.cache.set([key], value, ttl=300.0)
            large_data_set.append((key, value))
        
        after_load_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Access data multiple times
        for _ in range(5):
            for key, _ in random.sample(large_data_set, 1000):
                result = self.cache.get([key])
        
        after_access_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Clear cache and force garbage collection
        self.cache.clear()
        gc.collect()
        
        after_clear_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        results = {
            'initial_memory_mb': initial_memory,
            'after_load_memory_mb': after_load_memory,
            'after_access_memory_mb': after_access_memory,
            'after_clear_memory_mb': after_clear_memory,
            'memory_growth_mb': after_load_memory - initial_memory,
            'memory_recovered_mb': after_access_memory - after_clear_memory,
            'cache_entries_loaded': len(large_data_set)
        }
        
        print(f"Memory usage:")
        print(f"  Initial: {results['initial_memory_mb']:.1f} MB")
        print(f"  After loading {results['cache_entries_loaded']} entries: {results['after_load_memory_mb']:.1f} MB (+{results['memory_growth_mb']:.1f} MB)")
        print(f"  After clear: {results['after_clear_memory_mb']:.1f} MB")
        print(f"  Memory recovered: {results['memory_recovered_mb']:.1f} MB")
        
        return results


async def run_comprehensive_performance_tests():
    """Run all performance tests and generate report."""
    print("=" * 80)
    print("COMPREHENSIVE CACHING PERFORMANCE TEST SUITE")
    print("=" * 80)
    
    test_suite = PerformanceTestSuite()
    
    try:
        # Run all tests
        test_results = {}
        
        test_results['basic_cache'] = await test_suite.test_cache_basic_performance()
        test_results['batch_operations'] = await test_suite.test_batch_operations_performance()
        test_results['concurrent_access'] = await test_suite.test_concurrent_access_performance()
        test_results['batch_processor'] = await test_suite.test_batch_processor_performance()
        test_results['cache_manager'] = await test_suite.test_cache_manager_performance()
        test_results['performance_monitor'] = await test_suite.test_performance_monitor()
        test_results['memory_usage'] = await test_suite.test_memory_usage()
        
        # Generate summary
        print("\n" + "=" * 80)
        print("PERFORMANCE TEST SUMMARY")
        print("=" * 80)
        
        # Cache performance summary
        basic_results = test_results['basic_cache']
        print(f"Cache Operations:")
        print(f"  SET throughput: {basic_results['set_ops_per_second']:.0f} ops/sec")
        print(f"  GET throughput: {basic_results['get_ops_per_second']:.0f} ops/sec")
        print(f"  MISS throughput: {basic_results['miss_ops_per_second']:.0f} ops/sec")
        
        # Batch performance summary
        batch_results = test_results['batch_operations']
        print(f"Batch Operations:")
        print(f"  Batch SET: {batch_results['batch_set_ops_per_second']:.0f} ops/sec")
        print(f"  Batch GET: {batch_results['batch_get_ops_per_second']:.0f} ops/sec")
        
        # Concurrent performance summary
        concurrent_results = test_results['concurrent_access']
        print(f"Concurrent Access:")
        print(f"  Total throughput: {concurrent_results['total_throughput']:.0f} ops/sec")
        print(f"  Average per-thread: {concurrent_results['average_ops_per_second']:.0f} ops/sec")
        
        # Health summary
        monitor_results = test_results['performance_monitor']
        print(f"System Health:")
        print(f"  Overall health score: {monitor_results['health_score']:.1f}/100")
        print(f"  Optimization recommendations: {monitor_results['recommendations']}")
        
        # Memory summary
        memory_results = test_results['memory_usage']
        print(f"Memory Usage:")
        print(f"  Peak memory usage: {memory_results['after_access_memory_mb']:.1f} MB")
        print(f"  Memory recovered: {memory_results['memory_recovered_mb']:.1f} MB")
        
        print("\n" + "=" * 80)
        print("PERFORMANCE TESTS COMPLETED SUCCESSFULLY")
        print("=" * 80)
        
        return test_results
    
    except Exception as e:
        print(f"Performance test failed: {e}")
        raise
    
    finally:
        # Cleanup
        try:
            test_suite.performance_monitor.shutdown()
            test_suite.batch_processor.shutdown()
            test_suite.cache_manager.shutdown()
        except:
            pass


# Pytest integration
@pytest.mark.asyncio
async def test_cache_performance_suite():
    """Main pytest entry point for performance tests."""
    results = await run_comprehensive_performance_tests()
    
    # Assert minimum performance requirements
    assert results['basic_cache']['set_ops_per_second'] > 1000, "Cache SET performance too low"
    assert results['basic_cache']['get_ops_per_second'] > 5000, "Cache GET performance too low"
    assert results['concurrent_access']['total_throughput'] > 2000, "Concurrent throughput too low"
    assert results['performance_monitor']['health_score'] > 70, "System health score too low"
    
    # Assert memory usage is reasonable
    assert results['memory_usage']['memory_recovered_mb'] > 0, "Memory not properly recovered after cache clear"


if __name__ == "__main__":
    # Run performance tests directly
    asyncio.run(run_comprehensive_performance_tests())