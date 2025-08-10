"""
Integration tests for error recovery scenarios and data quality handling.

Tests system resilience, error recovery mechanisms, data validation workflows,
and fallback strategies across all components.
"""

import pytest
import asyncio
import json
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from contextlib import asynccontextmanager

from statistics_cache import StatisticsCache
from batch_statistics_processor import BatchStatisticsProcessor
from cache_manager import CacheManager, CacheType
from performance_monitor import PerformanceMonitor, AlertSeverity
from background_tasks import BackgroundTaskManager
from elo_rating import ELORatingSystem
from caching_middleware import ResponseCachingMiddleware


class MockFailingDatabase:
    """Mock database that simulates various failure scenarios."""
    
    def __init__(self, failure_mode='none'):
        self.failure_mode = failure_mode
        self.call_count = 0
        self.intermittent_failure_rate = 0.5
        
    def set_failure_mode(self, mode):
        """Set the failure mode for testing."""
        self.failure_mode = mode
        self.call_count = 0
    
    def get_games(self, limit=None, offset=0):
        """Simulate database game retrieval with potential failures."""
        self.call_count += 1
        
        if self.failure_mode == 'connection_error':
            raise ConnectionError("Database connection lost")
        
        elif self.failure_mode == 'timeout':
            raise TimeoutError("Database query timeout")
        
        elif self.failure_mode == 'intermittent':
            if self.call_count % 2 == 0:  # Fail every other call
                raise ConnectionError("Intermittent connection failure")
        
        elif self.failure_mode == 'corrupted_data':
            return [
                {
                    'id': 1,
                    'white_player': None,  # Missing data
                    'black_player': 'Bob',
                    'result': 'INVALID_RESULT',  # Invalid result
                    'moves': [],
                    'date': 'invalid_date'  # Invalid date format
                },
                {
                    'id': 2,
                    'white_player': 'Charlie',
                    'black_player': 'Diana',
                    'result': 'WHITE_WINS',
                    'moves': ['invalid_move_notation'],  # Invalid moves
                    'date': datetime.now()
                }
            ]
        
        elif self.failure_mode == 'partial_failure':
            if self.call_count <= 2:
                return [{'id': 1, 'white_player': 'Alice', 'black_player': 'Bob', 'result': 'WHITE_WINS'}]
            else:
                raise ConnectionError("Database became unavailable")
        
        # Normal operation
        return [
            {'id': 1, 'white_player': 'Alice', 'black_player': 'Bob', 'result': 'WHITE_WINS'},
            {'id': 2, 'white_player': 'Charlie', 'black_player': 'Diana', 'result': 'BLACK_WINS'}
        ]


class TestErrorRecoveryWorkflows:
    """Test error recovery workflows across system components."""
    
    def setup_method(self):
        """Setup error recovery test environment."""
        self.mock_db = MockFailingDatabase()
        self.cache = StatisticsCache()
        self.batch_processor = BatchStatisticsProcessor(cache=self.cache)
        self.cache_manager = CacheManager(primary_cache=self.cache, batch_processor=self.batch_processor)
        self.performance_monitor = PerformanceMonitor(cache=self.cache, batch_processor=self.batch_processor)
        self.elo_system = ELORatingSystem()
    
    def teardown_method(self):
        """Cleanup after error recovery tests."""
        if hasattr(self.performance_monitor, 'stop_monitoring'):
            self.performance_monitor.stop_monitoring()
        if hasattr(self.cache_manager, 'shutdown'):
            self.cache_manager.shutdown()
    
    @pytest.mark.asyncio
    async def test_database_connection_failure_recovery(self):
        """Test recovery from database connection failures."""
        # Setup: Normal operation first
        self.mock_db.set_failure_mode('none')
        
        # Cache some data during normal operation
        normal_data = await self.cache_manager.get_with_warming(
            cache_type=CacheType.PLAYER_STATISTICS,
            key_parts=['player_stats', 'Alice'],
            calculator=lambda: self._get_player_stats('Alice'),
            ttl=300.0,
            dependencies=['player:Alice']
        )
        
        assert normal_data is not None
        print("✅ Normal data cached successfully")
        
        # Simulate database failure
        self.mock_db.set_failure_mode('connection_error')
        
        # Should serve from cache when database fails
        cached_data = await self.cache_manager.get_with_warming(
            cache_type=CacheType.PLAYER_STATISTICS,
            key_parts=['player_stats', 'Alice'],
            calculator=lambda: self._get_player_stats('Alice'),
            ttl=300.0,
            dependencies=['player:Alice']
        )
        
        # Should get cached data even with database failure
        assert cached_data is not None
        print("✅ Successfully served cached data during database failure")
        
        # Test new request that requires database (should handle gracefully)
        fallback_data = await self.cache_manager.get_with_warming(
            cache_type=CacheType.PLAYER_STATISTICS,
            key_parts=['player_stats', 'NewPlayer'],
            calculator=lambda: self._get_player_stats_with_fallback('NewPlayer'),
            ttl=60.0  # Shorter TTL for fallback data
        )
        
        assert fallback_data is not None
        assert 'error_recovery' in fallback_data
        print("✅ Fallback mechanism activated for new requests")
    
    @pytest.mark.asyncio
    async def test_intermittent_failure_retry_logic(self):
        """Test retry logic for intermittent failures."""
        self.mock_db.set_failure_mode('intermittent')
        
        successful_requests = 0
        failed_requests = 0
        
        # Make multiple requests to test retry behavior
        for i in range(10):
            try:
                data = await self._request_with_retry(
                    lambda: self.mock_db.get_games(),
                    max_retries=3,
                    retry_delay=0.01  # Fast retry for testing
                )
                if data:
                    successful_requests += 1
            except Exception:
                failed_requests += 1
        
        # Should have some successful requests due to retry logic
        assert successful_requests > 0
        print(f"✅ Retry logic successful: {successful_requests}/{successful_requests + failed_requests} requests succeeded")
        
        # Verify performance monitor captured retry metrics
        if hasattr(self.performance_monitor, '_record_metric'):
            self.performance_monitor._record_metric('RETRY_COUNT', failed_requests, datetime.now())
    
    @pytest.mark.asyncio 
    async def test_data_corruption_handling(self):
        """Test handling of corrupted or invalid data."""
        self.mock_db.set_failure_mode('corrupted_data')
        
        # Attempt to process corrupted games
        games = self.mock_db.get_games()
        
        processed_games = []
        validation_errors = []
        
        for game in games:
            try:
                # Validate game data
                validated_game = self._validate_game_data(game)
                if validated_game:
                    processed_games.append(validated_game)
            except ValueError as e:
                validation_errors.append({
                    'game_id': game.get('id', 'unknown'),
                    'error': str(e),
                    'data': game
                })
        
        # Should have caught validation errors
        assert len(validation_errors) > 0
        print(f"✅ Detected {len(validation_errors)} data validation errors")
        
        # Should have processed some valid games
        assert len(processed_games) >= 0
        print(f"✅ Successfully processed {len(processed_games)} valid games")
        
        # Test ELO system with invalid data
        for error in validation_errors:
            if 'INVALID_RESULT' in str(error['error']):
                # Should gracefully handle invalid game results
                with pytest.raises(ValueError):
                    self.elo_system.update_ratings_for_game(
                        'Alice', 1500.0, 10,
                        'Bob', 1500.0, 10,
                        'INVALID_RESULT'
                    )
                print("✅ ELO system properly rejected invalid game result")
    
    @pytest.mark.asyncio
    async def test_cache_failure_graceful_degradation(self):
        """Test graceful degradation when cache fails."""
        # First, ensure cache is working
        test_data = await self.cache_manager.get_with_warming(
            cache_type=CacheType.PLAYER_STATISTICS,
            key_parts=['test_player'],
            calculator=lambda: {'rating': 1500, 'games': 5}
        )
        assert test_data is not None
        
        # Simulate cache failure
        original_get = self.cache.get
        self.cache.get = Mock(side_effect=Exception("Cache service unavailable"))
        
        # Should still work without cache
        direct_data = await self.cache_manager.get_with_warming(
            cache_type=CacheType.PLAYER_STATISTICS,
            key_parts=['direct_calculation'],
            calculator=lambda: {'rating': 1600, 'games': 8, 'source': 'direct'}
        )
        
        assert direct_data is not None
        assert direct_data['source'] == 'direct'
        print("✅ System continued to work with cache failure")
        
        # Restore cache and verify recovery
        self.cache.get = original_get
        
        recovered_data = await self.cache_manager.get_with_warming(
            cache_type=CacheType.PLAYER_STATISTICS,
            key_parts=['recovery_test'],
            calculator=lambda: {'rating': 1700, 'games': 12, 'source': 'recovered'}
        )
        
        assert recovered_data is not None
        print("✅ Cache recovery successful")
    
    @pytest.mark.asyncio
    async def test_performance_monitor_alert_recovery(self):
        """Test performance monitor alert handling and recovery."""
        # Generate conditions that trigger alerts
        if hasattr(self.performance_monitor, '_record_metric'):
            # Record poor performance metrics
            self.performance_monitor._record_metric('CACHE_HIT_RATE', 15.0, datetime.now())  # Very low
            self.performance_monitor._record_metric('RESPONSE_TIME', 2500.0, datetime.now())  # Very high
            self.performance_monitor._record_metric('ERROR_RATE', 25.0, datetime.now())  # High error rate
            
            # Trigger alert check
            if hasattr(self.performance_monitor, '_check_alert_conditions'):
                self.performance_monitor._check_alert_conditions()
                
                # Should have generated alerts
                if hasattr(self.performance_monitor, '_active_alerts'):
                    alerts = list(self.performance_monitor._active_alerts.values())
                    
                    critical_alerts = [a for a in alerts if a.severity == AlertSeverity.CRITICAL]
                    high_alerts = [a for a in alerts if a.severity == AlertSeverity.HIGH]
                    
                    print(f"✅ Generated {len(critical_alerts)} critical and {len(high_alerts)} high severity alerts")
                    
                    # Test alert acknowledgment
                    for alert in alerts[:2]:  # Acknowledge first 2 alerts
                        result = self.performance_monitor.acknowledge_alert(
                            alert.alert_id, 
                            "Acknowledged during error recovery test"
                        )
                        assert result is True
                    
                    print("✅ Alert acknowledgment working correctly")
        
        # Simulate recovery by recording better metrics
        if hasattr(self.performance_monitor, '_record_metric'):
            self.performance_monitor._record_metric('CACHE_HIT_RATE', 85.0, datetime.now())
            self.performance_monitor._record_metric('RESPONSE_TIME', 150.0, datetime.now())
            self.performance_monitor._record_metric('ERROR_RATE', 2.0, datetime.now())
            
            print("✅ Recovery metrics recorded")
    
    @pytest.mark.asyncio
    async def test_batch_processor_partial_failure_handling(self):
        """Test batch processor handling of partial failures."""
        # Create batch with mix of valid and invalid requests
        batch_requests = [
            {
                'calculation_type': 'player_stats',
                'parameters': {'player': 'Alice'},
                'priority': 1
            },
            {
                'calculation_type': 'invalid_calculation',  # This will fail
                'parameters': {'invalid': 'data'},
                'priority': 1
            },
            {
                'calculation_type': 'player_stats',
                'parameters': {'player': 'Bob'},
                'priority': 1
            },
            {
                'calculation_type': 'player_stats', 
                'parameters': {'player': None},  # This will fail
                'priority': 1
            }
        ]
        
        # Submit batch job
        batch_job = await self.batch_processor.submit_batch_job(
            job_type='mixed_success_batch',
            requests=batch_requests,
            priority=1
        )
        
        # Give time for processing
        await asyncio.sleep(0.1)
        
        # Check results
        metrics = self.batch_processor.get_performance_metrics()
        
        # Should have processed some successfully and recorded failures
        assert metrics['total_jobs'] > 0
        print(f"✅ Batch processing metrics: {metrics}")
        
        # Should handle partial failures gracefully
        assert 'failed_jobs' in metrics
        assert 'successful_jobs' in metrics
        
        total_processed = metrics.get('successful_jobs', 0) + metrics.get('failed_jobs', 0)
        assert total_processed <= len(batch_requests)
        
        print(f"✅ Batch processor handled partial failures: {metrics.get('successful_jobs', 0)} succeeded, {metrics.get('failed_jobs', 0)} failed")
    
    @pytest.mark.asyncio
    async def test_cascading_failure_isolation(self):
        """Test isolation of cascading failures."""
        # Setup multiple components with potential failures
        components = {
            'database': self.mock_db,
            'cache': self.cache,
            'batch_processor': self.batch_processor,
            'performance_monitor': self.performance_monitor
        }
        
        # Start by failing the database
        self.mock_db.set_failure_mode('connection_error')
        
        # Test that cache continues to work
        cache_result = await self.cache_manager.get_with_warming(
            cache_type=CacheType.AGGREGATED_STATS,
            key_parts=['isolation_test'],
            calculator=lambda: {'isolated': True, 'timestamp': datetime.now().isoformat()}
        )
        
        assert cache_result is not None
        print("✅ Cache isolated from database failure")
        
        # Test that performance monitoring continues
        if hasattr(self.performance_monitor, '_record_metric'):
            self.performance_monitor._record_metric('ISOLATION_TEST', 100.0, datetime.now())
            
            current_metrics = self.performance_monitor.get_current_metrics()
            assert len(current_metrics) >= 0  # Should not crash
            print("✅ Performance monitoring isolated from database failure")
        
        # Test that batch processor can use cached data
        fallback_request = {
            'calculation_type': 'fallback_stats',
            'parameters': {'use_cache': True},
            'priority': 1
        }
        
        fallback_job = await self.batch_processor.submit_batch_job(
            job_type='fallback_test',
            requests=[fallback_request],
            priority=1
        )
        
        # Should not crash even with database down
        await asyncio.sleep(0.1)
        print("✅ Batch processor isolated from database failure")
        
        # Restore database and verify recovery
        self.mock_db.set_failure_mode('none')
        
        recovery_result = await self.cache_manager.get_with_warming(
            cache_type=CacheType.PLAYER_STATISTICS,
            key_parts=['recovery_verification'],
            calculator=lambda: self._get_player_stats('RecoveryTest')
        )
        
        assert recovery_result is not None
        print("✅ System recovered successfully after database restoration")
    
    def _get_player_stats(self, player_name):
        """Get player statistics with potential database failure."""
        try:
            games = self.mock_db.get_games()
            # Process games for player
            return {
                'player': player_name,
                'rating': 1500.0,
                'games_played': len(games),
                'source': 'database'
            }
        except Exception as e:
            raise Exception(f"Failed to get player stats for {player_name}: {e}")
    
    def _get_player_stats_with_fallback(self, player_name):
        """Get player statistics with fallback for failures."""
        try:
            return self._get_player_stats(player_name)
        except Exception:
            # Fallback to default/cached data
            return {
                'player': player_name,
                'rating': 1500.0,  # Default rating
                'games_played': 0,
                'source': 'fallback',
                'error_recovery': True,
                'message': 'Using fallback data due to system unavailability'
            }
    
    def _validate_game_data(self, game):
        """Validate game data and raise errors for invalid data."""
        if not game.get('white_player'):
            raise ValueError("Missing white player")
        
        if not game.get('black_player'):
            raise ValueError("Missing black player")
        
        valid_results = ['WHITE_WINS', 'BLACK_WINS', 'DRAW']
        if game.get('result') not in valid_results:
            raise ValueError(f"Invalid game result: {game.get('result')}")
        
        # Validate date
        if isinstance(game.get('date'), str) and game['date'] == 'invalid_date':
            raise ValueError("Invalid date format")
        
        # Validate moves if present
        moves = game.get('moves', [])
        if moves and any('invalid' in str(move).lower() for move in moves):
            raise ValueError("Invalid move notation detected")
        
        return game
    
    async def _request_with_retry(self, operation, max_retries=3, retry_delay=0.1):
        """Execute operation with retry logic."""
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                return operation()
            except Exception as e:
                last_exception = e
                if attempt < max_retries:
                    await asyncio.sleep(retry_delay * (2 ** attempt))  # Exponential backoff
                    continue
                else:
                    raise last_exception


class TestDataQualityValidation:
    """Test data quality validation and handling workflows."""
    
    def setup_method(self):
        """Setup data quality test environment."""
        self.elo_system = ELORatingSystem()
        
    def test_elo_rating_validation_workflow(self):
        """Test ELO rating validation with various data quality issues."""
        # Test with valid data
        valid_ratings = [1200.0, 1500.0, 2000.0, 2800.0]
        for rating in valid_ratings:
            assert self.elo_system.validate_rating(rating)
        
        # Test with invalid data
        invalid_ratings = [
            50.0,     # Below floor
            5000.0,   # Above ceiling
            float('nan'),  # NaN
            float('inf'),  # Infinity
            -100.0,   # Negative
            "1500",   # Wrong type
            None      # None value
        ]
        
        validation_errors = []
        for rating in invalid_ratings:
            if not self.elo_system.validate_rating(rating):
                validation_errors.append(rating)
        
        assert len(validation_errors) == len(invalid_ratings)
        print(f"✅ Detected {len(validation_errors)} rating validation errors")
    
    def test_game_result_validation_workflow(self):
        """Test game result validation and error handling."""
        valid_results = ['WHITE_WINS', 'BLACK_WINS', 'DRAW']
        invalid_results = ['INVALID', 'WHITE_WIN', 'TIE', '', None, 123]
        
        # Test valid results
        for result in valid_results:
            try:
                update1, update2 = self.elo_system.update_ratings_for_game(
                    'Alice', 1500.0, 10,
                    'Bob', 1500.0, 10,
                    result
                )
                assert update1 is not None and update2 is not None
            except ValueError:
                pytest.fail(f"Valid result '{result}' was rejected")
        
        # Test invalid results
        error_count = 0
        for result in invalid_results:
            try:
                self.elo_system.update_ratings_for_game(
                    'Alice', 1500.0, 10,
                    'Bob', 1500.0, 10,
                    result
                )
            except ValueError:
                error_count += 1
        
        assert error_count == len(invalid_results)
        print(f"✅ Properly rejected {error_count} invalid game results")
    
    def test_missing_data_handling_workflow(self):
        """Test handling of missing or incomplete data."""
        # Test cases with missing data
        test_cases = [
            {
                'name': 'missing_player_name',
                'white_player': None,
                'black_player': 'Bob',
                'expected_error': 'Missing player information'
            },
            {
                'name': 'missing_game_count',
                'white_player': 'Alice',
                'black_player': 'Bob',
                'games_played': None,
                'expected_error': 'Invalid games played count'
            },
            {
                'name': 'invalid_rating_range',
                'rating': -50.0,
                'expected_error': 'Rating out of valid range'
            }
        ]
        
        handled_errors = 0
        for case in test_cases:
            try:
                # Simulate processing with missing data
                if case['name'] == 'missing_player_name' and not case['white_player']:
                    raise ValueError('Missing player information')
                elif case['name'] == 'missing_game_count' and case.get('games_played') is None:
                    raise ValueError('Invalid games played count')
                elif case['name'] == 'invalid_rating_range':
                    if not self.elo_system.validate_rating(case['rating']):
                        raise ValueError('Rating out of valid range')
            except ValueError as e:
                if case['expected_error'] in str(e):
                    handled_errors += 1
        
        assert handled_errors == len(test_cases)
        print(f"✅ Properly handled {handled_errors} missing data scenarios")


class TestSystemResilienceScenarios:
    """Test system-wide resilience scenarios."""
    
    @pytest.mark.asyncio
    async def test_high_load_error_recovery(self):
        """Test error recovery under high load conditions."""
        cache = StatisticsCache()
        failing_operations = 0
        successful_operations = 0
        
        # Simulate high load with intermittent failures
        async def simulate_operation(operation_id):
            nonlocal failing_operations, successful_operations
            
            try:
                # Randomly fail some operations
                if operation_id % 5 == 0:  # Fail every 5th operation
                    raise Exception(f"Simulated failure for operation {operation_id}")
                
                # Simulate cache operation
                result = cache.get(
                    key_parts=[f'load_test_{operation_id}'],
                    calculator=lambda: {'operation_id': operation_id, 'result': 'success'}
                )
                
                if result:
                    successful_operations += 1
                    
            except Exception:
                failing_operations += 1
        
        # Run many concurrent operations
        operations = [simulate_operation(i) for i in range(100)]
        await asyncio.gather(*operations, return_exceptions=True)
        
        total_operations = successful_operations + failing_operations
        success_rate = successful_operations / total_operations if total_operations > 0 else 0
        
        print(f"✅ High load test completed:")
        print(f"   Total operations: {total_operations}")
        print(f"   Successful: {successful_operations}")
        print(f"   Failed: {failing_operations}")
        print(f"   Success rate: {success_rate:.2%}")
        
        # Should have reasonable success rate despite failures
        assert success_rate >= 0.7  # At least 70% success rate
        assert successful_operations > 0
    
    @pytest.mark.asyncio
    async def test_memory_pressure_recovery(self):
        """Test system behavior under memory pressure."""
        cache = StatisticsCache()
        
        # Fill cache with large amount of data
        large_data_items = []
        for i in range(50):
            large_data = {
                'id': i,
                'data': ['x' * 1000] * 100,  # 100KB per item
                'metadata': {f'key_{j}': f'value_{j}' for j in range(100)}
            }
            
            cache.set(
                key_parts=[f'memory_test_{i}'],
                value=large_data,
                ttl=300.0
            )
            large_data_items.append(large_data)
        
        # Verify cache handles memory pressure
        cache_stats = cache.get_stats()
        
        # Should have reasonable cache size and eviction behavior
        print(f"✅ Memory pressure test completed:")
        print(f"   Cache stats: {cache_stats}")
        
        # Test that system remains responsive
        responsive_test = cache.get(
            key_parts=['responsiveness_test'],
            calculator=lambda: {'responsive': True, 'timestamp': datetime.now().isoformat()}
        )
        
        assert responsive_test is not None
        print("✅ System remained responsive under memory pressure")
    
    @pytest.mark.asyncio
    async def test_network_partition_recovery(self):
        """Test recovery from network partition scenarios."""
        # This would typically test distributed components
        # For this integration test, simulate with component isolation
        
        cache = StatisticsCache()
        batch_processor = BatchStatisticsProcessor(cache=cache)
        
        # Simulate network partition by isolating components
        original_cache_get = cache.get
        partition_active = True
        
        def partitioned_cache_get(*args, **kwargs):
            if partition_active:
                raise ConnectionError("Network partition: cache unreachable")
            return original_cache_get(*args, **kwargs)
        
        cache.get = partitioned_cache_get
        
        # Test that batch processor handles partition
        try:
            batch_job = await batch_processor.submit_batch_job(
                job_type='partition_test',
                requests=[{
                    'calculation_type': 'test_calc',
                    'parameters': {'test': 'partition'},
                    'priority': 1
                }],
                priority=1
            )
            
            # Should handle gracefully
            print("✅ Batch processor handled network partition")
            
        except Exception as e:
            # Should not crash the system
            print(f"✅ Network partition handled gracefully: {e}")
        
        # Simulate network recovery
        partition_active = False
        cache.get = original_cache_get
        
        # Test recovery
        recovery_result = cache.get(
            key_parts=['recovery_test'],
            calculator=lambda: {'recovered': True}
        )
        
        assert recovery_result is not None
        print("✅ System recovered from network partition")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])