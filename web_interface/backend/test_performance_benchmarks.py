"""
Performance benchmarks for large game collections and complex statistics.

Tests system performance under load with large datasets, complex calculations,
and concurrent operations to validate scalability and efficiency.
"""

import pytest
import asyncio
import time
import random
import threading
import concurrent.futures
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from dataclasses import dataclass
from typing import List, Dict, Any
import json
import psutil
import gc

from statistics_cache import StatisticsCache
from batch_statistics_processor import BatchStatisticsProcessor
from cache_manager import CacheManager, CacheType
from performance_monitor import PerformanceMonitor
from elo_rating import ELORatingSystem
from background_tasks import BackgroundTaskManager


@dataclass
class PerformanceMetrics:
    """Performance metrics for benchmarking."""
    operation_name: str
    execution_time: float
    memory_usage_mb: float
    cache_hit_rate: float
    throughput_ops_per_second: float
    error_rate: float
    concurrent_operations: int
    dataset_size: int


class LargeDatasetGenerator:
    """Generates large datasets for performance testing."""
    
    @staticmethod
    def generate_players(count: int) -> List[Dict[str, Any]]:
        """Generate a large number of players."""
        players = []
        for i in range(count):
            players.append({
                'id': i + 1,
                'name': f'Player_{i:06d}',
                'rating': random.randint(800, 2800),
                'games_played': random.randint(0, 500),
                'wins': random.randint(0, 250),
                'losses': random.randint(0, 250),
                'draws': random.randint(0, 100),
                'country': random.choice(['USA', 'UK', 'Germany', 'Russia', 'India', 'China']),
                'title': random.choice(['GM', 'IM', 'FM', 'CM', None, None, None])  # Most players have no title
            })
        return players
    
    @staticmethod
    def generate_games(player_count: int, games_count: int) -> List[Dict[str, Any]]:
        """Generate a large number of games."""
        games = []
        openings = [
            'Sicilian Defense', 'French Defense', 'Caro-Kann Defense', 'Queen\'s Gambit',
            'King\'s Indian Defense', 'English Opening', 'Ruy Lopez', 'Italian Game',
            'Scandinavian Defense', 'Nimzo-Indian Defense'
        ]
        
        for i in range(games_count):
            white_player = random.randint(1, player_count)
            black_player = random.randint(1, player_count)
            
            # Avoid self-play
            while black_player == white_player:
                black_player = random.randint(1, player_count)
            
            games.append({
                'id': i + 1,
                'white_player_id': white_player,
                'black_player_id': black_player,
                'white_player': f'Player_{white_player:06d}',
                'black_player': f'Player_{black_player:06d}',
                'result': random.choice(['WHITE_WINS', 'BLACK_WINS', 'DRAW']),
                'opening': random.choice(openings),
                'moves_count': random.randint(20, 150),
                'duration_minutes': random.randint(5, 180),
                'date': datetime.now() - timedelta(days=random.randint(0, 365)),
                'termination': random.choice(['checkmate', 'resignation', 'time', 'draw_agreement', 'stalemate'])
            })
        
        return games
    
    @staticmethod
    def generate_complex_statistics_request(players: List[Dict], games: List[Dict]) -> Dict[str, Any]:
        """Generate complex statistics calculation request."""
        return {
            'leaderboard': {
                'top_players': 100,
                'rating_categories': ['overall', 'blitz', 'rapid', 'classical'],
                'time_periods': ['last_30_days', 'last_6_months', 'all_time']
            },
            'player_analytics': {
                'detailed_stats': True,
                'opening_analysis': True,
                'performance_trends': True,
                'head_to_head_analysis': True
            },
            'aggregate_statistics': {
                'game_outcomes_by_rating_difference': True,
                'opening_success_rates': True,
                'time_control_analysis': True,
                'country_rankings': True
            }
        }


class TestLargeDatasetPerformance:
    """Test performance with large datasets."""
    
    def setup_method(self):
        """Setup performance test environment."""
        self.cache = StatisticsCache(max_size=10000)  # Larger cache for performance tests
        self.batch_processor = BatchStatisticsProcessor(
            cache=self.cache,
            max_concurrent_jobs=10  # Higher concurrency
        )
        self.cache_manager = CacheManager(
            primary_cache=self.cache,
            batch_processor=self.batch_processor,
            max_warming_workers=5
        )
        self.performance_monitor = PerformanceMonitor(
            cache=self.cache,
            batch_processor=self.batch_processor,
            collection_interval_seconds=1
        )
        self.elo_system = ELORatingSystem()
        
        # Generate test datasets
        self.small_dataset = {
            'players': LargeDatasetGenerator.generate_players(100),
            'games': LargeDatasetGenerator.generate_games(100, 1000)
        }
        
        self.medium_dataset = {
            'players': LargeDatasetGenerator.generate_players(1000),
            'games': LargeDatasetGenerator.generate_games(1000, 10000)
        }
        
        self.large_dataset = {
            'players': LargeDatasetGenerator.generate_players(5000),
            'games': LargeDatasetGenerator.generate_games(5000, 50000)
        }
    
    def teardown_method(self):
        """Cleanup performance tests."""
        if hasattr(self.performance_monitor, 'stop_monitoring'):
            self.performance_monitor.stop_monitoring()
        if hasattr(self.cache_manager, 'shutdown'):
            self.cache_manager.shutdown()
        
        # Force garbage collection
        gc.collect()
    
    @pytest.mark.performance
    def test_elo_calculation_performance_large_dataset(self):
        """Benchmark ELO calculations with large number of games."""
        datasets = [
            ('small', self.small_dataset),
            ('medium', self.medium_dataset),
            ('large', self.large_dataset)
        ]
        
        results = []
        
        for dataset_name, dataset in datasets:
            start_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
            start_time = time.time()
            
            # Process all games for ELO updates
            processed_games = 0
            rating_updates = []
            
            # Create player rating tracking
            player_ratings = {
                player['name']: {
                    'rating': player['rating'],
                    'games_played': 0
                }
                for player in dataset['players']
            }
            
            for game in dataset['games'][:1000]:  # Limit for reasonable test time
                white_player = game['white_player']
                black_player = game['black_player']
                
                if white_player in player_ratings and black_player in player_ratings:
                    white_data = player_ratings[white_player]
                    black_data = player_ratings[black_player]
                    
                    try:
                        white_update, black_update = self.elo_system.update_ratings_for_game(
                            white_player, white_data['rating'], white_data['games_played'],
                            black_player, black_data['rating'], black_data['games_played'],
                            game['result'], True
                        )
                        
                        # Update tracking
                        player_ratings[white_player]['rating'] = white_update.new_rating
                        player_ratings[white_player]['games_played'] += 1
                        player_ratings[black_player]['rating'] = black_update.new_rating
                        player_ratings[black_player]['games_played'] += 1
                        
                        rating_updates.extend([white_update, black_update])
                        processed_games += 1
                        
                    except Exception as e:
                        print(f"Error processing game {game['id']}: {e}")
            
            end_time = time.time()
            end_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
            
            execution_time = end_time - start_time
            memory_usage = end_memory - start_memory
            throughput = processed_games / execution_time if execution_time > 0 else 0
            
            metrics = PerformanceMetrics(
                operation_name=f'ELO_calculation_{dataset_name}',
                execution_time=execution_time,
                memory_usage_mb=memory_usage,
                cache_hit_rate=0.0,  # No cache for pure ELO calculations
                throughput_ops_per_second=throughput,
                error_rate=0.0,
                concurrent_operations=1,
                dataset_size=len(dataset['games'])
            )
            
            results.append(metrics)
            
            print(f"✅ {dataset_name.upper()} dataset ELO performance:")
            print(f"   Processed {processed_games} games in {execution_time:.2f}s")
            print(f"   Throughput: {throughput:.1f} games/sec")
            print(f"   Memory usage: {memory_usage:.1f} MB")
            print(f"   Rating updates generated: {len(rating_updates)}")
        
        # Verify performance scaling
        small_throughput = results[0].throughput_ops_per_second
        medium_throughput = results[1].throughput_ops_per_second
        
        # Performance should not degrade too much with larger datasets
        degradation = (small_throughput - medium_throughput) / small_throughput
        assert degradation < 0.5, f"Performance degraded by {degradation:.1%}"
        
        print("✅ ELO calculation performance benchmark completed")
        return results
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_cache_performance_large_datasets(self):
        """Benchmark cache performance with large datasets."""
        test_scenarios = [
            ('small_frequent_access', 100, 1000),    # 100 keys, 1000 operations
            ('medium_mixed_access', 500, 5000),      # 500 keys, 5000 operations
            ('large_sparse_access', 2000, 10000)     # 2000 keys, 10000 operations
        ]
        
        results = []
        
        for scenario_name, key_count, operation_count in test_scenarios:
            start_memory = psutil.Process().memory_info().rss / 1024 / 1024
            start_time = time.time()
            
            # Pre-populate cache with some data
            for i in range(key_count // 2):
                self.cache.set(
                    key_parts=[f'benchmark_key_{i}'],
                    value={
                        'player_id': i,
                        'stats': {
                            'rating': random.randint(1200, 2200),
                            'games': random.randint(10, 100),
                            'performance_data': [random.random() for _ in range(50)]
                        }
                    },
                    ttl=300.0
                )
            
            # Perform mixed read/write operations
            cache_hits = 0
            cache_misses = 0
            cache_errors = 0
            
            for i in range(operation_count):
                try:
                    key_id = random.randint(0, key_count - 1)
                    
                    if random.random() < 0.8:  # 80% reads
                        result = self.cache.get(
                            key_parts=[f'benchmark_key_{key_id}'],
                            calculator=lambda: self._generate_complex_stats(key_id),
                            ttl=300.0
                        )
                        
                        if result:
                            cache_hits += 1
                        else:
                            cache_misses += 1
                    
                    else:  # 20% writes
                        self.cache.set(
                            key_parts=[f'benchmark_key_{key_id}'],
                            value=self._generate_complex_stats(key_id),
                            ttl=300.0
                        )
                
                except Exception:
                    cache_errors += 1
            
            end_time = time.time()
            end_memory = psutil.Process().memory_info().rss / 1024 / 1024
            
            execution_time = end_time - start_time
            memory_usage = end_memory - start_memory
            throughput = operation_count / execution_time if execution_time > 0 else 0
            hit_rate = cache_hits / (cache_hits + cache_misses) if (cache_hits + cache_misses) > 0 else 0
            error_rate = cache_errors / operation_count if operation_count > 0 else 0
            
            metrics = PerformanceMetrics(
                operation_name=f'Cache_performance_{scenario_name}',
                execution_time=execution_time,
                memory_usage_mb=memory_usage,
                cache_hit_rate=hit_rate,
                throughput_ops_per_second=throughput,
                error_rate=error_rate,
                concurrent_operations=1,
                dataset_size=operation_count
            )
            
            results.append(metrics)
            
            print(f"✅ {scenario_name.upper()} cache performance:")
            print(f"   {operation_count} operations in {execution_time:.2f}s")
            print(f"   Throughput: {throughput:.1f} ops/sec")
            print(f"   Hit rate: {hit_rate:.1%}")
            print(f"   Memory usage: {memory_usage:.1f} MB")
            print(f"   Error rate: {error_rate:.1%}")
        
        # Verify cache hit rates are reasonable
        for metrics in results:
            assert metrics.cache_hit_rate > 0.3, f"Cache hit rate too low: {metrics.cache_hit_rate:.1%}"
        
        print("✅ Cache performance benchmark completed")
        return results
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_concurrent_operations_performance(self):
        """Benchmark performance under concurrent load."""
        concurrency_levels = [1, 5, 10, 20]
        operation_count_per_worker = 100
        
        results = []
        
        for concurrency in concurrency_levels:
            start_memory = psutil.Process().memory_info().rss / 1024 / 1024
            start_time = time.time()
            
            # Track results across all workers
            total_operations = 0
            total_errors = 0
            
            async def worker_task(worker_id: int):
                nonlocal total_operations, total_errors
                
                worker_operations = 0
                worker_errors = 0
                
                for i in range(operation_count_per_worker):
                    try:
                        # Mix of different operations
                        operation_type = random.choice(['cache_get', 'cache_set', 'elo_calculation', 'batch_request'])
                        
                        if operation_type == 'cache_get':
                            result = await self.cache_manager.get_with_warming(
                                cache_type=CacheType.PLAYER_STATISTICS,
                                key_parts=[f'worker_{worker_id}_op_{i}'],
                                calculator=lambda: self._generate_player_stats(worker_id, i)
                            )
                            
                        elif operation_type == 'cache_set':
                            self.cache.set(
                                key_parts=[f'worker_{worker_id}_set_{i}'],
                                value=self._generate_player_stats(worker_id, i),
                                ttl=60.0
                            )
                            
                        elif operation_type == 'elo_calculation':
                            self.elo_system.update_ratings_for_game(
                                f'Player_{worker_id}_A', 1500.0, 10,
                                f'Player_{worker_id}_B', 1500.0, 10,
                                random.choice(['WHITE_WINS', 'BLACK_WINS', 'DRAW'])
                            )
                            
                        elif operation_type == 'batch_request':
                            batch_job = await self.batch_processor.submit_batch_job(
                                job_type=f'worker_{worker_id}_batch',
                                requests=[{
                                    'calculation_type': 'test_calc',
                                    'parameters': {'worker': worker_id, 'operation': i}
                                }],
                                priority=1
                            )
                        
                        worker_operations += 1
                        
                    except Exception as e:
                        worker_errors += 1
                
                total_operations += worker_operations
                total_errors += worker_errors
            
            # Run workers concurrently
            tasks = [worker_task(i) for i in range(concurrency)]
            await asyncio.gather(*tasks)
            
            end_time = time.time()
            end_memory = psutil.Process().memory_info().rss / 1024 / 1024
            
            execution_time = end_time - start_time
            memory_usage = end_memory - start_memory
            throughput = total_operations / execution_time if execution_time > 0 else 0
            error_rate = total_errors / (total_operations + total_errors) if (total_operations + total_errors) > 0 else 0
            
            metrics = PerformanceMetrics(
                operation_name=f'Concurrent_operations',
                execution_time=execution_time,
                memory_usage_mb=memory_usage,
                cache_hit_rate=0.5,  # Estimated
                throughput_ops_per_second=throughput,
                error_rate=error_rate,
                concurrent_operations=concurrency,
                dataset_size=total_operations
            )
            
            results.append(metrics)
            
            print(f"✅ Concurrency {concurrency} performance:")
            print(f"   {total_operations} operations in {execution_time:.2f}s")
            print(f"   Throughput: {throughput:.1f} ops/sec")
            print(f"   Memory usage: {memory_usage:.1f} MB")
            print(f"   Error rate: {error_rate:.1%}")
        
        # Verify throughput scales reasonably with concurrency
        single_thread_throughput = results[0].throughput_ops_per_second
        max_concurrent_throughput = max(r.throughput_ops_per_second for r in results)
        
        # Should see some improvement with concurrency
        improvement = max_concurrent_throughput / single_thread_throughput
        assert improvement > 1.2, f"Concurrency improvement too low: {improvement:.1f}x"
        
        print("✅ Concurrent operations performance benchmark completed")
        return results
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_batch_processing_scalability(self):
        """Benchmark batch processing scalability."""
        batch_sizes = [10, 50, 100, 500]
        
        results = []
        
        for batch_size in batch_sizes:
            start_memory = psutil.Process().memory_info().rss / 1024 / 1024
            start_time = time.time()
            
            # Create batch requests
            batch_requests = []
            for i in range(batch_size):
                batch_requests.append({
                    'calculation_type': 'player_statistics',
                    'parameters': {
                        'player_id': f'player_{i}',
                        'include_recent_games': True,
                        'include_opening_analysis': True
                    },
                    'priority': 1
                })
            
            # Submit batch job
            batch_job = await self.batch_processor.submit_batch_job(
                job_type=f'scalability_test_batch_{batch_size}',
                requests=batch_requests,
                priority=1
            )
            
            # Wait for completion (with timeout)
            wait_time = 0
            max_wait = 30.0  # 30 seconds max wait
            
            while not batch_job.completed and wait_time < max_wait:
                await asyncio.sleep(0.1)
                wait_time += 0.1
            
            end_time = time.time()
            end_memory = psutil.Process().memory_info().rss / 1024 / 1024
            
            execution_time = end_time - start_time
            memory_usage = end_memory - start_memory
            throughput = batch_size / execution_time if execution_time > 0 else 0
            
            # Get batch processing metrics
            batch_metrics = self.batch_processor.get_performance_metrics()
            
            metrics = PerformanceMetrics(
                operation_name=f'Batch_processing_size_{batch_size}',
                execution_time=execution_time,
                memory_usage_mb=memory_usage,
                cache_hit_rate=batch_metrics.get('cache_efficiency', 0.0),
                throughput_ops_per_second=throughput,
                error_rate=0.0,  # Would need to track from batch results
                concurrent_operations=batch_size,
                dataset_size=batch_size
            )
            
            results.append(metrics)
            
            print(f"✅ Batch size {batch_size} performance:")
            print(f"   Processed in {execution_time:.2f}s")
            print(f"   Throughput: {throughput:.1f} items/sec")
            print(f"   Memory usage: {memory_usage:.1f} MB")
            print(f"   Batch metrics: {batch_metrics}")
        
        # Verify batch processing efficiency
        for i in range(1, len(results)):
            prev_efficiency = results[i-1].throughput_ops_per_second
            curr_efficiency = results[i].throughput_ops_per_second
            
            # Throughput should not degrade significantly
            if prev_efficiency > 0:
                degradation = (prev_efficiency - curr_efficiency) / prev_efficiency
                assert degradation < 0.7, f"Batch processing degraded too much: {degradation:.1%}"
        
        print("✅ Batch processing scalability benchmark completed")
        return results
    
    def _generate_complex_stats(self, key_id: int) -> Dict[str, Any]:
        """Generate complex statistics data for benchmarking."""
        return {
            'player_id': key_id,
            'rating': random.randint(1200, 2200),
            'games_played': random.randint(50, 500),
            'recent_performance': [random.random() for _ in range(20)],
            'opening_repertoire': {
                f'opening_{i}': {
                    'games': random.randint(5, 50),
                    'win_rate': random.random(),
                    'avg_rating_opponent': random.randint(1200, 2000)
                }
                for i in range(10)
            },
            'head_to_head': {
                f'opponent_{i}': {
                    'games': random.randint(1, 10),
                    'score': random.random() * random.randint(1, 10)
                }
                for i in range(20)
            },
            'time_controls': {
                'blitz': {'rating': random.randint(1200, 2200), 'games': random.randint(0, 200)},
                'rapid': {'rating': random.randint(1200, 2200), 'games': random.randint(0, 200)},
                'classical': {'rating': random.randint(1200, 2200), 'games': random.randint(0, 100)}
            },
            'calculated_at': datetime.now().isoformat()
        }
    
    def _generate_player_stats(self, worker_id: int, operation_id: int) -> Dict[str, Any]:
        """Generate player statistics for concurrent testing."""
        return {
            'worker_id': worker_id,
            'operation_id': operation_id,
            'rating': 1500 + random.randint(-300, 300),
            'games_played': random.randint(10, 100),
            'performance_trend': [random.random() for _ in range(10)],
            'generated_at': datetime.now().isoformat()
        }


class TestMemoryAndResourceUsage:
    """Test memory usage and resource consumption."""
    
    def setup_method(self):
        """Setup resource usage tests."""
        self.cache = StatisticsCache()
    
    def teardown_method(self):
        """Cleanup resource tests."""
        gc.collect()
    
    @pytest.mark.performance
    def test_memory_usage_large_cache(self):
        """Test memory usage with large cache datasets."""
        initial_memory = psutil.Process().memory_info().rss / 1024 / 1024
        
        # Fill cache with increasing amounts of data
        memory_usage_points = []
        
        for data_size in [100, 500, 1000, 2000, 5000]:
            # Add data to cache
            for i in range(data_size):
                large_data = {
                    'id': i,
                    'large_array': [random.random() for _ in range(1000)],  # ~8KB per entry
                    'metadata': {f'key_{j}': f'value_{j}_{"x" * 100}' for j in range(10)}  # ~1KB
                }
                
                self.cache.set(
                    key_parts=[f'memory_test_{data_size}_{i}'],
                    value=large_data,
                    ttl=300.0
                )
            
            current_memory = psutil.Process().memory_info().rss / 1024 / 1024
            memory_increase = current_memory - initial_memory
            
            memory_usage_points.append({
                'data_size': data_size,
                'memory_mb': memory_increase,
                'memory_per_item': memory_increase / data_size if data_size > 0 else 0
            })
            
            print(f"Cache size {data_size}: {memory_increase:.1f} MB ({memory_increase/data_size:.2f} MB per item)")
        
        # Verify memory usage is reasonable
        final_memory_usage = memory_usage_points[-1]['memory_mb']
        assert final_memory_usage < 2000, f"Memory usage too high: {final_memory_usage:.1f} MB"
        
        # Verify memory usage scales predictably
        memory_per_item_avg = sum(p['memory_per_item'] for p in memory_usage_points) / len(memory_usage_points)
        print(f"✅ Average memory per cache item: {memory_per_item_avg:.2f} MB")
        
        return memory_usage_points
    
    @pytest.mark.performance
    def test_cache_eviction_performance(self):
        """Test cache eviction performance under memory pressure."""
        # Set small cache size to force evictions
        small_cache = StatisticsCache(max_size=100)
        
        start_time = time.time()
        eviction_count = 0
        
        # Add more items than cache can hold
        for i in range(500):
            old_stats = small_cache.get_stats()
            
            small_cache.set(
                key_parts=[f'eviction_test_{i}'],
                value={'data': f'test_data_{i}', 'size': 'x' * 1000},
                ttl=300.0
            )
            
            new_stats = small_cache.get_stats()
            if new_stats.get('evictions', 0) > old_stats.get('evictions', 0):
                eviction_count += 1
        
        eviction_time = time.time() - start_time
        
        final_stats = small_cache.get_stats()
        
        print(f"✅ Cache eviction performance:")
        print(f"   Evictions triggered: {eviction_count}")
        print(f"   Total eviction time: {eviction_time:.2f}s")
        print(f"   Final cache stats: {final_stats}")
        
        # Eviction should be reasonably fast
        assert eviction_time < 5.0, f"Eviction too slow: {eviction_time:.2f}s"
        assert eviction_count > 0, "No evictions occurred"


class TestRealWorldScenarioPerformance:
    """Test performance in realistic usage scenarios."""
    
    def setup_method(self):
        """Setup realistic scenario tests."""
        self.cache = StatisticsCache()
        self.batch_processor = BatchStatisticsProcessor(cache=self.cache)
        self.cache_manager = CacheManager(primary_cache=self.cache)
        self.elo_system = ELORatingSystem()
    
    def teardown_method(self):
        """Cleanup scenario tests."""
        if hasattr(self.cache_manager, 'shutdown'):
            self.cache_manager.shutdown()
        gc.collect()
    
    @pytest.mark.performance 
    @pytest.mark.asyncio
    async def test_tournament_processing_scenario(self):
        """Simulate processing a large tournament with thousands of games."""
        # Generate tournament data
        tournament_players = 200
        rounds = 9  # Swiss system tournament
        games_per_round = tournament_players // 2
        total_games = rounds * games_per_round
        
        players = LargeDatasetGenerator.generate_players(tournament_players)
        games = LargeDatasetGenerator.generate_games(tournament_players, total_games)
        
        print(f"🏆 Simulating tournament: {tournament_players} players, {total_games} games")
        
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024
        
        # Phase 1: Process all game results and update ratings
        rating_updates = []
        player_ratings = {p['name']: {'rating': p['rating'], 'games': 0} for p in players}
        
        for game in games:
            white_player = game['white_player']
            black_player = game['black_player']
            
            if white_player in player_ratings and black_player in player_ratings:
                white_data = player_ratings[white_player]
                black_data = player_ratings[black_player]
                
                white_update, black_update = self.elo_system.update_ratings_for_game(
                    white_player, white_data['rating'], white_data['games'],
                    black_player, black_data['rating'], black_data['games'],
                    game['result'], True
                )
                
                player_ratings[white_player]['rating'] = white_update.new_rating
                player_ratings[white_player]['games'] += 1
                player_ratings[black_player]['rating'] = black_update.new_rating
                player_ratings[black_player]['games'] += 1
                
                rating_updates.extend([white_update, black_update])
        
        phase1_time = time.time() - start_time
        
        # Phase 2: Generate tournament statistics and leaderboards
        phase2_start = time.time()
        
        # Calculate leaderboards
        leaderboard = await self.cache_manager.get_with_warming(
            cache_type=CacheType.LEADERBOARDS,
            key_parts=['tournament_leaderboard'],
            calculator=lambda: self._generate_tournament_leaderboard(player_ratings),
            ttl=3600.0
        )
        
        # Calculate tournament statistics
        tournament_stats = await self.cache_manager.get_with_warming(
            cache_type=CacheType.AGGREGATED_STATS,
            key_parts=['tournament_stats'],
            calculator=lambda: self._calculate_tournament_stats(games, players),
            ttl=3600.0
        )
        
        phase2_time = time.time() - phase2_start
        
        total_time = time.time() - start_time
        final_memory = psutil.Process().memory_info().rss / 1024 / 1024
        memory_usage = final_memory - start_memory
        
        print(f"✅ Tournament processing completed:")
        print(f"   Phase 1 (ELO updates): {phase1_time:.2f}s")
        print(f"   Phase 2 (Statistics): {phase2_time:.2f}s")
        print(f"   Total time: {total_time:.2f}s")
        print(f"   Memory usage: {memory_usage:.1f} MB")
        print(f"   Games processed: {len(rating_updates) // 2}")
        print(f"   Final leaderboard size: {len(leaderboard)}")
        print(f"   Tournament stats calculated: {len(tournament_stats)}")
        
        # Performance assertions
        assert total_time < 60.0, f"Tournament processing too slow: {total_time:.2f}s"
        assert memory_usage < 500.0, f"Memory usage too high: {memory_usage:.1f} MB"
        assert len(leaderboard) == tournament_players
        
        return {
            'total_time': total_time,
            'memory_usage': memory_usage,
            'games_processed': len(rating_updates) // 2,
            'players_processed': tournament_players
        }
    
    def _generate_tournament_leaderboard(self, player_ratings: Dict) -> List[Dict]:
        """Generate tournament leaderboard from player ratings."""
        leaderboard = []
        
        for player_name, data in player_ratings.items():
            leaderboard.append({
                'rank': 0,  # Will be set after sorting
                'player_name': player_name,
                'rating': data['rating'],
                'games_played': data['games'],
                'score': data['games'] * 0.6  # Approximate tournament score
            })
        
        # Sort by rating
        leaderboard.sort(key=lambda x: x['rating'], reverse=True)
        
        # Set ranks
        for i, player in enumerate(leaderboard):
            player['rank'] = i + 1
        
        return leaderboard
    
    def _calculate_tournament_stats(self, games: List[Dict], players: List[Dict]) -> Dict:
        """Calculate comprehensive tournament statistics."""
        total_games = len(games)
        total_players = len(players)
        
        # Result distribution
        white_wins = sum(1 for g in games if g['result'] == 'WHITE_WINS')
        black_wins = sum(1 for g in games if g['result'] == 'BLACK_WINS')
        draws = sum(1 for g in games if g['result'] == 'DRAW')
        
        # Opening analysis
        opening_counts = {}
        for game in games:
            opening = game['opening']
            opening_counts[opening] = opening_counts.get(opening, 0) + 1
        
        # Average game length
        avg_moves = sum(g['moves_count'] for g in games) / len(games)
        avg_duration = sum(g['duration_minutes'] for g in games) / len(games)
        
        return {
            'total_games': total_games,
            'total_players': total_players,
            'result_distribution': {
                'white_wins': white_wins,
                'black_wins': black_wins,
                'draws': draws,
                'white_win_percentage': (white_wins / total_games) * 100,
                'draw_percentage': (draws / total_games) * 100
            },
            'popular_openings': sorted(opening_counts.items(), key=lambda x: x[1], reverse=True)[:10],
            'average_game_length': avg_moves,
            'average_duration_minutes': avg_duration,
            'calculated_at': datetime.now().isoformat()
        }


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "performance"])