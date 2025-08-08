"""
Comprehensive performance tests for the Game Analysis Web Interface.

This module tests performance requirements including 2-second load times,
response times under load, memory usage, and scalability.
"""

import asyncio
import time
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any
from datetime import datetime, timezone
import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock
import psutil
import threading

from .main import create_app
from game_arena.storage.models import GameRecord


class PerformanceMetrics:
    """Class to track and analyze performance metrics."""
    
    def __init__(self):
        self.response_times: List[float] = []
        self.memory_usage: List[float] = []
        self.cpu_usage: List[float] = []
        self.concurrent_requests: List[Dict[str, Any]] = []
    
    def add_response_time(self, response_time: float):
        self.response_times.append(response_time)
    
    def add_memory_usage(self, memory_mb: float):
        self.memory_usage.append(memory_mb)
    
    def add_cpu_usage(self, cpu_percent: float):
        self.cpu_usage.append(cpu_percent)
    
    def add_concurrent_request(self, endpoint: str, response_time: float, status_code: int):
        self.concurrent_requests.append({
            'endpoint': endpoint,
            'response_time': response_time,
            'status_code': status_code,
            'timestamp': time.time()
        })
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive performance statistics."""
        stats = {}
        
        if self.response_times:
            stats['response_times'] = {
                'mean': statistics.mean(self.response_times),
                'median': statistics.median(self.response_times),
                'p95': self._percentile(self.response_times, 95),
                'p99': self._percentile(self.response_times, 99),
                'max': max(self.response_times),
                'min': min(self.response_times),
                'count': len(self.response_times)
            }
        
        if self.memory_usage:
            stats['memory'] = {
                'mean': statistics.mean(self.memory_usage),
                'max': max(self.memory_usage),
                'min': min(self.memory_usage)
            }
        
        if self.cpu_usage:
            stats['cpu'] = {
                'mean': statistics.mean(self.cpu_usage),
                'max': max(self.cpu_usage)
            }
        
        if self.concurrent_requests:
            successful_requests = [r for r in self.concurrent_requests if r['status_code'] < 400]
            stats['concurrent'] = {
                'total_requests': len(self.concurrent_requests),
                'successful_requests': len(successful_requests),
                'success_rate': len(successful_requests) / len(self.concurrent_requests) if self.concurrent_requests else 0,
                'avg_response_time': statistics.mean([r['response_time'] for r in successful_requests]) if successful_requests else 0
            }
        
        return stats
    
    @staticmethod
    def _percentile(data: List[float], percentile: int) -> float:
        """Calculate percentile of a dataset."""
        sorted_data = sorted(data)
        index = (percentile / 100) * (len(sorted_data) - 1)
        if index.is_integer():
            return sorted_data[int(index)]
        else:
            lower = sorted_data[int(index)]
            upper = sorted_data[int(index) + 1]
            return lower + (upper - lower) * (index - int(index))


@pytest.fixture
def performance_metrics():
    """Create a performance metrics tracker."""
    return PerformanceMetrics()


@pytest.fixture
def large_dataset():
    """Create a large dataset for performance testing."""
    games = []
    for i in range(1000):  # Generate 1000 mock games
        game = MagicMock(spec=GameRecord)
        game.game_id = f"perf_game_{i}"
        game.tournament_id = f"tournament_{i % 10}"
        base_time = datetime.now(timezone.utc)
        game.start_time = base_time.replace(hour=10 + (i % 12))
        game.end_time = game.start_time.replace(hour=game.start_time.hour + 1)  # 1 hour games
        game.total_moves = 40 + (i % 60)  # Varying game lengths
        game.is_completed = True
        
        # Mock players
        game.players = {
            "0": MagicMock(
                player_id=f"player_{i}_white",
                model_name=f"model_{i % 5}",
                model_provider=f"provider_{i % 3}",
                agent_type="ChessLLMAgent",
                elo_rating=1200 + (i % 400),
            ),
            "1": MagicMock(
                player_id=f"player_{i}_black",
                model_name=f"model_{(i + 1) % 5}",
                model_provider=f"provider_{(i + 1) % 3}",
                agent_type="ChessLLMAgent",
                elo_rating=1200 + ((i + 1) % 400),
            ),
        }
        
        # Mock outcome
        game.outcome = MagicMock()
        game.outcome.result = MagicMock()
        game.outcome.result.value = ["WHITE_WINS", "BLACK_WINS", "DRAW"][i % 3]
        game.outcome.winner = None if i % 3 == 2 else (i % 2)
        game.outcome.termination = MagicMock()
        game.outcome.termination.value = ["CHECKMATE", "RESIGNATION", "DRAW_BY_REPETITION"][i % 3]
        game.outcome.termination_details = None
        
        games.append(game)
    
    return games


@pytest.fixture
def performance_test_app(large_dataset):
    """Create a test app with performance-oriented mocks."""
    app = create_app()
    
    # Create fast mock dependencies
    mock_storage_manager = AsyncMock()
    mock_query_engine = AsyncMock()
    
    # Mock query engine with large dataset
    mock_query_engine.query_games_advanced.return_value = large_dataset[:20]  # Return first 20 for pagination
    mock_query_engine.count_games_advanced.return_value = len(large_dataset)
    mock_query_engine.storage_manager = mock_storage_manager
    
    # Set up app state
    app.state.storage_manager = mock_storage_manager
    app.state.query_engine = mock_query_engine
    
    return app


@pytest.fixture
def performance_client(performance_test_app):
    """Create a test client for performance testing."""
    return TestClient(performance_test_app)


class TestAPIPerformance:
    """Test API performance requirements."""
    
    def test_games_list_response_time(self, performance_client, performance_metrics):
        """Test that games list API responds within 2 seconds."""
        start_time = time.time()
        
        response = performance_client.get("/api/games")
        
        response_time = time.time() - start_time
        performance_metrics.add_response_time(response_time)
        
        assert response.status_code == 200
        assert response_time < 2.0, f"Response time {response_time:.2f}s exceeds 2s requirement"
    
    def test_game_detail_response_time(self, performance_client, performance_metrics):
        """Test that game detail API responds within 2 seconds."""
        # First, ensure the mock returns a game
        start_time = time.time()
        
        response = performance_client.get("/api/games/perf_game_1")
        
        response_time = time.time() - start_time
        performance_metrics.add_response_time(response_time)
        
        assert response.status_code == 200
        assert response_time < 2.0, f"Response time {response_time:.2f}s exceeds 2s requirement"
    
    def test_statistics_response_time(self, performance_client, performance_metrics):
        """Test that statistics API responds within 2 seconds."""
        start_time = time.time()
        
        response = performance_client.get("/api/statistics/overview")
        
        response_time = time.time() - start_time
        performance_metrics.add_response_time(response_time)
        
        assert response.status_code == 200
        assert response_time < 2.0, f"Response time {response_time:.2f}s exceeds 2s requirement"
    
    def test_leaderboard_response_time(self, performance_client, performance_metrics):
        """Test that leaderboard API responds within 2 seconds."""
        start_time = time.time()
        
        response = performance_client.get("/api/leaderboard")
        
        response_time = time.time() - start_time
        performance_metrics.add_response_time(response_time)
        
        assert response.status_code == 200
        assert response_time < 2.0, f"Response time {response_time:.2f}s exceeds 2s requirement"
    
    def test_filtered_games_response_time(self, performance_client, performance_metrics):
        """Test filtered games API performance."""
        params = {
            'player_id': 'player_1_white',
            'model_provider': 'provider_1',
            'start_date': '2024-01-01T00:00:00Z',
            'end_date': '2024-12-31T23:59:59Z',
            'result': 'white_wins',
            'page': '1',
            'limit': '50'
        }
        
        start_time = time.time()
        
        response = performance_client.get("/api/games", params=params)
        
        response_time = time.time() - start_time
        performance_metrics.add_response_time(response_time)
        
        assert response.status_code == 200
        assert response_time < 2.0, f"Filtered response time {response_time:.2f}s exceeds 2s requirement"


class TestConcurrentPerformance:
    """Test performance under concurrent load."""
    
    def test_concurrent_games_requests(self, performance_test_app, performance_metrics):
        """Test concurrent requests to games API."""
        num_concurrent = 20
        
        def make_request(client_id: int) -> Dict[str, Any]:
            """Make a single request and return metrics."""
            client = TestClient(performance_test_app)
            start_time = time.time()
            
            try:
                response = client.get(f"/api/games?page={client_id % 5 + 1}")
                response_time = time.time() - start_time
                
                return {
                    'client_id': client_id,
                    'response_time': response_time,
                    'status_code': response.status_code,
                    'success': response.status_code == 200
                }
            except Exception as e:
                return {
                    'client_id': client_id,
                    'response_time': time.time() - start_time,
                    'status_code': 500,
                    'success': False,
                    'error': str(e)
                }
        
        # Execute concurrent requests
        with ThreadPoolExecutor(max_workers=num_concurrent) as executor:
            futures = [executor.submit(make_request, i) for i in range(num_concurrent)]
            results = [future.result() for future in as_completed(futures)]
        
        # Analyze results
        successful_requests = [r for r in results if r['success']]
        response_times = [r['response_time'] for r in successful_requests]
        
        # Record metrics
        for result in results:
            performance_metrics.add_concurrent_request(
                '/api/games', 
                result['response_time'], 
                result['status_code']
            )
        
        # Assertions
        assert len(successful_requests) >= num_concurrent * 0.95, "Success rate should be at least 95%"
        assert all(rt < 5.0 for rt in response_times), "All concurrent requests should complete within 5 seconds"
        
        avg_response_time = statistics.mean(response_times)
        assert avg_response_time < 2.0, f"Average concurrent response time {avg_response_time:.2f}s exceeds 2s requirement"
    
    def test_mixed_endpoint_load(self, performance_test_app, performance_metrics):
        """Test performance with mixed endpoint load."""
        endpoints = [
            "/api/games",
            "/api/statistics/overview", 
            "/api/leaderboard",
            "/api/games/perf_game_1"
        ]
        
        requests_per_endpoint = 5
        total_requests = len(endpoints) * requests_per_endpoint
        
        def make_mixed_request(endpoint: str, request_id: int) -> Dict[str, Any]:
            """Make a request to a specific endpoint."""
            client = TestClient(performance_test_app)
            start_time = time.time()
            
            try:
                response = client.get(endpoint)
                response_time = time.time() - start_time
                
                return {
                    'endpoint': endpoint,
                    'request_id': request_id,
                    'response_time': response_time,
                    'status_code': response.status_code,
                    'success': response.status_code == 200
                }
            except Exception as e:
                return {
                    'endpoint': endpoint,
                    'request_id': request_id,
                    'response_time': time.time() - start_time,
                    'status_code': 500,
                    'success': False,
                    'error': str(e)
                }
        
        # Create mixed workload
        tasks = []
        for endpoint in endpoints:
            for i in range(requests_per_endpoint):
                tasks.append((endpoint, len(tasks)))
        
        # Execute mixed concurrent requests
        with ThreadPoolExecutor(max_workers=15) as executor:
            futures = [executor.submit(make_mixed_request, endpoint, req_id) 
                      for endpoint, req_id in tasks]
            results = [future.result() for future in as_completed(futures)]
        
        # Analyze results by endpoint
        endpoint_results = {}
        for result in results:
            endpoint = result['endpoint']
            if endpoint not in endpoint_results:
                endpoint_results[endpoint] = []
            endpoint_results[endpoint].append(result)
            
            # Record metrics
            performance_metrics.add_concurrent_request(
                endpoint, 
                result['response_time'], 
                result['status_code']
            )
        
        # Verify each endpoint performs well
        for endpoint, endpoint_data in endpoint_results.items():
            successful = [r for r in endpoint_data if r['success']]
            success_rate = len(successful) / len(endpoint_data)
            
            assert success_rate >= 0.95, f"Endpoint {endpoint} success rate {success_rate:.2%} < 95%"
            
            if successful:
                avg_time = statistics.mean([r['response_time'] for r in successful])
                assert avg_time < 2.0, f"Endpoint {endpoint} avg response time {avg_time:.2f}s > 2s"


class TestMemoryPerformance:
    """Test memory usage and efficiency."""
    
    def test_memory_usage_stability(self, performance_client, performance_metrics):
        """Test that memory usage remains stable under repeated requests."""
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Make repeated requests to stress test memory
        for i in range(50):
            response = performance_client.get(f"/api/games?page={i % 10 + 1}")
            assert response.status_code == 200
            
            # Record memory usage every 10 requests
            if i % 10 == 0:
                current_memory = process.memory_info().rss / 1024 / 1024
                performance_metrics.add_memory_usage(current_memory)
        
        final_memory = process.memory_info().rss / 1024 / 1024
        memory_growth = final_memory - initial_memory
        
        # Memory growth should be reasonable (less than 50MB for 50 requests)
        assert memory_growth < 50, f"Memory grew by {memory_growth:.2f}MB, which may indicate a memory leak"
    
    def test_large_response_memory_efficiency(self, performance_client, performance_metrics):
        """Test memory efficiency with large response payloads."""
        process = psutil.Process()
        
        # Request large page sizes
        large_page_sizes = [100, 200, 500]
        
        for page_size in large_page_sizes:
            memory_before = process.memory_info().rss / 1024 / 1024
            
            response = performance_client.get(f"/api/games?limit={page_size}")
            assert response.status_code == 200
            
            memory_after = process.memory_info().rss / 1024 / 1024
            memory_delta = memory_after - memory_before
            
            performance_metrics.add_memory_usage(memory_after)
            
            # Memory increase should be proportional to page size, not excessive
            max_expected_increase = page_size * 0.1  # 0.1MB per game record max
            assert memory_delta < max_expected_increase, \
                f"Memory increase {memory_delta:.2f}MB for {page_size} games exceeds expected {max_expected_increase:.2f}MB"


class TestScalabilityPerformance:
    """Test performance scalability with increasing data size."""
    
    def test_pagination_performance_scaling(self, performance_test_app, performance_metrics):
        """Test that pagination performance scales well with data size."""
        client = TestClient(performance_test_app)
        
        # Test different page sizes
        page_sizes = [10, 50, 100, 500]
        
        for page_size in page_sizes:
            start_time = time.time()
            
            response = client.get(f"/api/games?limit={page_size}")
            
            response_time = time.time() - start_time
            performance_metrics.add_response_time(response_time)
            
            assert response.status_code == 200
            
            # Response time should scale reasonably with page size
            # Larger pages should not be dramatically slower
            max_expected_time = 0.5 + (page_size / 1000)  # Base time + scaling factor
            assert response_time < max_expected_time, \
                f"Page size {page_size} took {response_time:.2f}s, exceeds expected {max_expected_time:.2f}s"
    
    def test_filtering_performance_scaling(self, performance_test_app, performance_metrics):
        """Test that filtering performance doesn't degrade significantly with complex filters."""
        client = TestClient(performance_test_app)
        
        # Test increasingly complex filter combinations
        filter_combinations = [
            {},  # No filters
            {'player_id': 'player_1_white'},  # Single filter
            {'player_id': 'player_1_white', 'model_provider': 'provider_1'},  # Two filters
            {  # Multiple filters
                'player_id': 'player_1_white',
                'model_provider': 'provider_1',
                'result': 'white_wins',
                'min_moves': '20'
            },
            {  # Complex filters with date range
                'model_provider': 'provider_1',
                'result': 'white_wins',
                'min_moves': '20',
                'max_moves': '100',
                'start_date': '2024-01-01T00:00:00Z',
                'end_date': '2024-12-31T23:59:59Z'
            }
        ]
        
        for i, filters in enumerate(filter_combinations):
            start_time = time.time()
            
            response = client.get("/api/games", params=filters)
            
            response_time = time.time() - start_time
            performance_metrics.add_response_time(response_time)
            
            assert response.status_code == 200
            
            # Even complex filters should respond within 2 seconds
            assert response_time < 2.0, \
                f"Filter combination {i} took {response_time:.2f}s, exceeds 2s requirement"


@pytest.mark.performance
class TestPerformanceReporting:
    """Generate comprehensive performance reports."""
    
    def test_comprehensive_performance_suite(
        self, 
        performance_test_app, 
        performance_metrics,
        large_dataset
    ):
        """Run a comprehensive performance test suite and generate report."""
        client = TestClient(performance_test_app)
        
        print(f"\n{'='*50}")
        print("COMPREHENSIVE PERFORMANCE TEST REPORT")
        print(f"{'='*50}")
        print(f"Dataset Size: {len(large_dataset)} mock games")
        
        # Test various scenarios
        scenarios = [
            ("Basic Games List", "/api/games"),
            ("Large Page Size", "/api/games?limit=100"),
            ("Filtered Games", "/api/games?model_provider=provider_1&result=white_wins"),
            ("Statistics Overview", "/api/statistics/overview"),
            ("Leaderboard", "/api/leaderboard"),
            ("Game Detail", "/api/games/perf_game_1"),
        ]
        
        scenario_results = {}
        
        for scenario_name, endpoint in scenarios:
            times = []
            
            # Run each scenario multiple times
            for _ in range(10):
                start_time = time.time()
                response = client.get(endpoint)
                end_time = time.time()
                
                assert response.status_code == 200
                times.append(end_time - start_time)
                performance_metrics.add_response_time(end_time - start_time)
            
            scenario_results[scenario_name] = {
                'mean': statistics.mean(times),
                'median': statistics.median(times),
                'max': max(times),
                'min': min(times),
                'p95': performance_metrics._percentile(times, 95),
                'meets_requirement': all(t < 2.0 for t in times)
            }
        
        # Print detailed results
        print(f"\n{'Scenario':<20} {'Mean':<8} {'Median':<8} {'Max':<8} {'Min':<8} {'P95':<8} {'2s Req':<8}")
        print("-" * 80)
        
        all_meet_requirements = True
        for scenario, results in scenario_results.items():
            meets_req = "✓" if results['meets_requirement'] else "✗"
            if not results['meets_requirement']:
                all_meet_requirements = False
                
            print(f"{scenario:<20} {results['mean']:<8.3f} {results['median']:<8.3f} "
                  f"{results['max']:<8.3f} {results['min']:<8.3f} {results['p95']:<8.3f} "
                  f"{meets_req:<8}")
        
        # Overall statistics
        overall_stats = performance_metrics.get_statistics()
        if 'response_times' in overall_stats:
            rt_stats = overall_stats['response_times']
            print(f"\nOVERALL STATISTICS:")
            print(f"Total Requests: {rt_stats['count']}")
            print(f"Mean Response Time: {rt_stats['mean']:.3f}s")
            print(f"95th Percentile: {rt_stats['p95']:.3f}s")
            print(f"99th Percentile: {rt_stats['p99']:.3f}s")
            print(f"Max Response Time: {rt_stats['max']:.3f}s")
        
        print(f"\n{'='*50}")
        print(f"PERFORMANCE REQUIREMENTS: {'PASSED' if all_meet_requirements else 'FAILED'}")
        print(f"{'='*50}\n")
        
        # Final assertion
        assert all_meet_requirements, "Some endpoints failed to meet 2-second response time requirement"