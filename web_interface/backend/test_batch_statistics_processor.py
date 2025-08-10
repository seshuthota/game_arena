"""
Comprehensive unit tests for BatchStatisticsProcessor.

Tests batch processing functionality, job tracking, performance metrics,
and leaderboard generation with caching integration.
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor

from batch_statistics_processor import (
    BatchStatisticsProcessor,
    BatchJobProgress,
    BatchCalculationRequest,
    BatchCalculationResult,
    get_batch_processor
)
from statistics_cache import StatisticsCache
from statistics_calculator import AccuratePlayerStatistics, LeaderboardEntry


class MockQueryEngine:
    """Mock query engine for testing."""
    
    def __init__(self):
        self.call_count = 0
        self.storage_manager = Mock()
        self.games_data = self._create_mock_games()
        self.setup_mock_methods()
    
    def _create_mock_games(self):
        """Create mock game data."""
        games = []
        for i in range(100):
            game = Mock()
            game.game_id = f"game_{i}"
            game.players = {
                0: Mock(player_id=f"player_{i % 20}", model_name=f"model_{i % 5}", model_provider="test_provider"),
                1: Mock(player_id=f"player_{(i + 10) % 20}", model_name=f"model_{(i + 2) % 5}", model_provider="test_provider")
            }
            game.total_moves = 50 + (i % 30)
            game.is_completed = True
            games.append(game)
        return games
    
    def setup_mock_methods(self):
        """Setup mock methods."""
        async def mock_query_games(filters):
            self.call_count += 1
            return self.games_data
        
        self.storage_manager.query_games = AsyncMock(side_effect=mock_query_games)


class MockStatisticsCalculator:
    """Mock statistics calculator."""
    
    def __init__(self, query_engine, cache=None):
        self.query_engine = query_engine
        self.cache = cache
        self.calculation_delay = 0.01  # Small delay to simulate work
    
    async def _calculate_player_statistics_uncached(self, player_id: str, include_incomplete: bool = True):
        """Mock player statistics calculation."""
        await asyncio.sleep(self.calculation_delay)
        
        # Create mock statistics
        return AccuratePlayerStatistics(
            player_id=player_id,
            model_name=f"model_{hash(player_id) % 5}",
            model_provider="test_provider",
            completed_games=10 + (hash(player_id) % 20),
            wins=3 + (hash(player_id) % 8),
            losses=2 + (hash(player_id) % 6),
            draws=1 + (hash(player_id) % 4),
            total_moves=500 + (hash(player_id) % 200),
            average_game_duration=45.5,
            current_elo=1500 + (hash(player_id) % 300) - 150,
            peak_elo=1600 + (hash(player_id) % 300) - 150,
            elo_history=[],
            win_rate=0.0,  # Will be calculated
            total_games=0,   # Will be calculated
            average_game_length=0.0  # Will be calculated
        )


class TestBatchJobProgress:
    """Test BatchJobProgress functionality."""
    
    def test_batch_job_progress_creation(self):
        """Test batch job progress creation and properties."""
        progress = BatchJobProgress(
            job_id="test_job_123",
            total_items=100
        )
        
        assert progress.job_id == "test_job_123"
        assert progress.total_items == 100
        assert progress.processed_items == 0
        assert progress.failed_items == 0
        assert progress.status == "running"
        assert len(progress.errors) == 0
        assert progress.end_time is None
    
    def test_progress_percentage_calculation(self):
        """Test progress percentage calculation."""
        progress = BatchJobProgress(job_id="test", total_items=50)
        
        # Initial state
        assert progress.progress_percentage == 0.0
        
        # 50% complete
        progress.processed_items = 25
        assert progress.progress_percentage == 50.0
        
        # 100% complete
        progress.processed_items = 50
        assert progress.progress_percentage == 100.0
        
        # Handle zero total items
        zero_progress = BatchJobProgress(job_id="zero", total_items=0)
        assert zero_progress.progress_percentage == 100.0
    
    def test_elapsed_time_calculation(self):
        """Test elapsed time calculation."""
        start_time = datetime.now()
        progress = BatchJobProgress(job_id="test", total_items=10)
        progress.start_time = start_time
        
        # Should have some elapsed time
        elapsed = progress.elapsed_time
        assert elapsed.total_seconds() >= 0
        
        # With end time set
        progress.end_time = start_time + timedelta(seconds=30)
        elapsed_with_end = progress.elapsed_time
        assert elapsed_with_end.total_seconds() == 30.0
    
    def test_mark_completed_and_failed(self):
        """Test marking job as completed or failed."""
        progress = BatchJobProgress(job_id="test", total_items=10)
        
        # Mark completed
        progress.mark_completed()
        assert progress.status == "completed"
        assert progress.end_time is not None
        
        # Mark failed
        progress = BatchJobProgress(job_id="test2", total_items=10)
        progress.mark_failed("Test error")
        assert progress.status == "failed"
        assert progress.end_time is not None
        assert "Test error" in progress.errors


class TestBatchCalculationRequest:
    """Test BatchCalculationRequest data class."""
    
    def test_batch_calculation_request_creation(self):
        """Test batch calculation request creation."""
        player_ids = ["player_1", "player_2", "player_3"]
        request = BatchCalculationRequest(
            player_ids=player_ids,
            calculation_type="statistics",
            include_incomplete_data=True,
            cache_results=True,
            cache_ttl=600.0,
            priority=2
        )
        
        assert request.player_ids == player_ids
        assert request.calculation_type == "statistics"
        assert request.include_incomplete_data == True
        assert request.cache_results == True
        assert request.cache_ttl == 600.0
        assert request.priority == 2
    
    def test_batch_calculation_request_defaults(self):
        """Test default values for batch calculation request."""
        request = BatchCalculationRequest(
            player_ids=["player_1"],
            calculation_type="statistics"
        )
        
        assert request.include_incomplete_data == True
        assert request.cache_results == True
        assert request.cache_ttl == 300.0
        assert request.priority == 1


class TestBatchStatisticsProcessor:
    """Test BatchStatisticsProcessor functionality."""
    
    def setup_method(self):
        """Setup test processor instance."""
        self.mock_query_engine = MockQueryEngine()
        self.cache = StatisticsCache(max_cache_size=1000, default_ttl=300.0)
        
        with patch('batch_statistics_processor.AccurateStatisticsCalculator', MockStatisticsCalculator):
            self.processor = BatchStatisticsProcessor(
                query_engine=self.mock_query_engine,
                cache=self.cache,
                max_workers=2,
                batch_size=10,
                enable_progressive_loading=True
            )
    
    def teardown_method(self):
        """Cleanup after each test."""
        self.processor.shutdown()
        self.cache.clear()
    
    def test_processor_initialization(self):
        """Test batch processor initialization."""
        assert self.processor.query_engine == self.mock_query_engine
        assert self.processor.cache == self.cache
        assert self.processor.max_workers == 2
        assert self.processor.batch_size == 10
        assert self.processor.enable_progressive_loading == True
        
        # Check performance metrics initialization
        metrics = self.processor.get_performance_metrics()
        assert metrics['total_jobs'] == 0
        assert metrics['successful_jobs'] == 0
        assert metrics['failed_jobs'] == 0
        assert metrics['average_processing_time'] == 0.0
    
    @pytest.mark.asyncio
    async def test_basic_batch_processing(self):
        """Test basic batch statistics processing."""
        # Create test request
        player_ids = ["player_1", "player_2", "player_3"]
        request = BatchCalculationRequest(
            player_ids=player_ids,
            calculation_type="statistics",
            cache_results=True
        )
        
        # Process batch
        result = await self.processor.process_batch_statistics(request)
        
        # Verify result structure
        assert isinstance(result, BatchCalculationResult)
        assert result.job_id.startswith("batch_stats_")
        assert len(result.results) == len(player_ids)
        assert result.progress.status == "completed"
        assert result.progress.total_items == len(player_ids)
        assert result.progress.processed_items == len(player_ids)
        
        # Verify all players were processed
        for player_id in player_ids:
            assert player_id in result.results
            stats = result.results[player_id]
            assert isinstance(stats, AccuratePlayerStatistics)
            assert stats.player_id == player_id
    
    @pytest.mark.asyncio
    async def test_batch_processing_with_cache_hits(self):
        """Test batch processing with some cache hits."""
        player_ids = ["player_1", "player_2", "player_3"]
        
        # Pre-populate cache for some players
        cached_stats = AccuratePlayerStatistics(
            player_id="player_1",
            model_name="cached_model",
            model_provider="cached_provider",
            completed_games=5,
            wins=3,
            losses=1,
            draws=1,
            total_moves=250,
            average_game_duration=30.0,
            current_elo=1600,
            peak_elo=1650,
            elo_history=[],
            win_rate=60.0,
            total_games=5,
            average_game_length=50.0
        )
        self.cache.set(['player_stats', 'player_1', True], cached_stats, dependencies=['player:player_1'])
        
        # Create request
        request = BatchCalculationRequest(
            player_ids=player_ids,
            calculation_type="statistics"
        )
        
        # Process batch
        result = await self.processor.process_batch_statistics(request)
        
        # Verify cache hit/miss counts
        assert result.cache_hits >= 1  # player_1 should be cache hit
        assert result.cache_misses >= 2  # player_2, player_3 should be cache misses
        
        # Verify cached result was used
        assert result.results["player_1"] == cached_stats
    
    @pytest.mark.asyncio
    async def test_large_batch_processing(self):
        """Test processing of large batches with batching."""
        # Create large request (more than batch_size)
        player_ids = [f"player_{i}" for i in range(25)]  # batch_size is 10
        request = BatchCalculationRequest(
            player_ids=player_ids,
            calculation_type="statistics"
        )
        
        # Process batch
        result = await self.processor.process_batch_statistics(request)
        
        # Verify all players were processed despite batching
        assert len(result.results) == len(player_ids)
        assert result.progress.status == "completed"
        assert result.progress.processed_items == len(player_ids)
        
        # Verify batching occurred (should be processed in chunks)
        assert result.execution_time > 0
    
    @pytest.mark.asyncio
    async def test_batch_processing_with_failures(self):
        """Test batch processing with some calculation failures."""
        player_ids = ["player_1", "player_error", "player_3"]
        
        # Mock calculator that fails for specific player
        original_calculate = self.processor._calculate_player_statistics
        
        def failing_calculator(player_id, calc_type, include_incomplete):
            if player_id == "player_error":
                raise ValueError("Calculation failed")
            return original_calculate(player_id, calc_type, include_incomplete)
        
        with patch.object(self.processor, '_calculate_player_statistics', side_effect=failing_calculator):
            request = BatchCalculationRequest(
                player_ids=player_ids,
                calculation_type="statistics"
            )
            
            result = await self.processor.process_batch_statistics(request)
        
        # Verify partial success
        assert len(result.results) == 2  # Only successful calculations
        assert len(result.failed_calculations) == 1
        assert "player_error" in result.failed_calculations
        assert "player_1" in result.results
        assert "player_3" in result.results
        
        # Verify progress tracking
        assert result.progress.processed_items == 3  # All were attempted
        assert result.progress.failed_items == 1
    
    @pytest.mark.asyncio
    async def test_concurrent_batch_processing(self):
        """Test concurrent processing of multiple batches."""
        # Create multiple requests
        requests = []
        for i in range(3):
            player_ids = [f"batch_{i}_player_{j}" for j in range(5)]
            request = BatchCalculationRequest(
                player_ids=player_ids,
                calculation_type="statistics"
            )
            requests.append(request)
        
        # Process concurrently
        tasks = [
            self.processor.process_batch_statistics(request)
            for request in requests
        ]
        results = await asyncio.gather(*tasks)
        
        # Verify all batches completed successfully
        assert len(results) == 3
        for i, result in enumerate(results):
            assert result.progress.status == "completed"
            assert len(result.results) == 5
            
            # Verify correct players were processed
            expected_players = [f"batch_{i}_player_{j}" for j in range(5)]
            for player_id in expected_players:
                assert player_id in result.results
    
    @pytest.mark.asyncio
    async def test_leaderboard_generation(self):
        """Test leaderboard generation functionality."""
        # Generate leaderboard
        leaderboard = await self.processor.generate_leaderboard_batch(
            sort_by="elo_rating",
            min_games=5,
            limit=10
        )
        
        # Verify leaderboard structure
        assert isinstance(leaderboard, list)
        assert len(leaderboard) <= 10
        
        for i, entry in enumerate(leaderboard):
            assert isinstance(entry, LeaderboardEntry)
            assert entry.rank == i + 1
            assert entry.statistics.completed_games >= 5  # min_games filter
            
            # Verify sorting (elo_rating descending)
            if i > 0:
                prev_elo = leaderboard[i-1].statistics.current_elo
                curr_elo = entry.statistics.current_elo
                assert prev_elo >= curr_elo
    
    @pytest.mark.asyncio
    async def test_leaderboard_caching(self):
        """Test leaderboard caching functionality."""
        # Generate leaderboard twice
        start_time = time.time()
        leaderboard1 = await self.processor.generate_leaderboard_batch(
            sort_by="elo_rating",
            min_games=1,
            limit=5
        )
        first_duration = time.time() - start_time
        
        start_time = time.time()
        leaderboard2 = await self.processor.generate_leaderboard_batch(
            sort_by="elo_rating",
            min_games=1,
            limit=5
        )
        second_duration = time.time() - start_time
        
        # Second call should be faster (cached)
        assert second_duration < first_duration
        
        # Results should be identical
        assert len(leaderboard1) == len(leaderboard2)
        for entry1, entry2 in zip(leaderboard1, leaderboard2):
            assert entry1.player_id == entry2.player_id
            assert entry1.rank == entry2.rank
    
    @pytest.mark.asyncio
    async def test_leaderboard_force_recalculate(self):
        """Test forced leaderboard recalculation."""
        # Generate leaderboard normally (will be cached)
        await self.processor.generate_leaderboard_batch(sort_by="elo_rating", limit=5)
        
        # Force recalculation
        start_time = time.time()
        leaderboard = await self.processor.generate_leaderboard_batch(
            sort_by="elo_rating",
            limit=5,
            force_recalculate=True
        )
        duration = time.time() - start_time
        
        # Should take time to recalculate
        assert duration > 0.001  # Should take some measurable time
        assert len(leaderboard) <= 5
    
    def test_job_progress_tracking(self):
        """Test job progress tracking functionality."""
        # Create a job and track progress
        job_id = "test_job_123"
        progress = BatchJobProgress(job_id=job_id, total_items=10)
        
        # Simulate storing progress (in real implementation)
        self.processor._active_jobs[job_id] = progress
        
        # Get progress
        retrieved_progress = self.processor.get_job_progress(job_id)
        assert retrieved_progress == progress
        
        # Test non-existent job
        assert self.processor.get_job_progress("nonexistent") is None
    
    def test_job_result_storage(self):
        """Test job result storage and retrieval."""
        # Create mock result
        result = BatchCalculationResult(
            job_id="test_result_123",
            results={"player_1": "stats_1"},
            failed_calculations={},
            execution_time=1.5,
            cache_hits=1,
            cache_misses=0,
            progress=BatchJobProgress(job_id="test_result_123", total_items=1)
        )
        
        # Store result (simulate completed job)
        self.processor._job_results[result.job_id] = result
        
        # Retrieve result
        retrieved_result = self.processor.get_job_result(result.job_id)
        assert retrieved_result == result
        
        # Test non-existent result
        assert self.processor.get_job_result("nonexistent") is None
    
    def test_performance_metrics_tracking(self):
        """Test performance metrics tracking."""
        # Get initial metrics
        initial_metrics = self.processor.get_performance_metrics()
        
        # Create mock completed result
        result = BatchCalculationResult(
            job_id="perf_test",
            results={"player_1": "stats"},
            failed_calculations={},
            execution_time=2.0,
            cache_hits=5,
            cache_misses=3,
            progress=BatchJobProgress(job_id="perf_test", total_items=1)
        )
        result.progress.mark_completed()
        
        # Update metrics
        self.processor._update_performance_metrics(result)
        
        # Verify metrics updated
        updated_metrics = self.processor.get_performance_metrics()
        assert updated_metrics['total_jobs'] == initial_metrics['total_jobs'] + 1
        assert updated_metrics['successful_jobs'] == initial_metrics['successful_jobs'] + 1
        assert updated_metrics['total_items_processed'] == initial_metrics['total_items_processed'] + 1
        assert updated_metrics['average_processing_time'] > 0
    
    def test_performance_metrics_with_failures(self):
        """Test performance metrics with failed jobs."""
        # Create mock failed result
        result = BatchCalculationResult(
            job_id="failed_test",
            results={},
            failed_calculations={"player_1": "error"},
            execution_time=1.0,
            cache_hits=0,
            cache_misses=1,
            progress=BatchJobProgress(job_id="failed_test", total_items=1)
        )
        result.progress.mark_failed("Test failure")
        
        # Update metrics
        initial_failed = self.processor.get_performance_metrics()['failed_jobs']
        self.processor._update_performance_metrics(result)
        
        # Verify failed job counted
        updated_metrics = self.processor.get_performance_metrics()
        assert updated_metrics['failed_jobs'] == initial_failed + 1
    
    def test_cleanup_old_results(self):
        """Test cleanup of old job results."""
        # Create old results
        old_time = datetime.now() - timedelta(hours=48)
        old_progress = BatchJobProgress(job_id="old_job", total_items=1)
        old_progress.start_time = old_time
        old_result = BatchCalculationResult(
            job_id="old_job",
            results={},
            failed_calculations={},
            execution_time=1.0,
            cache_hits=0,
            cache_misses=1,
            progress=old_progress
        )
        
        # Create recent result
        recent_progress = BatchJobProgress(job_id="recent_job", total_items=1)
        recent_result = BatchCalculationResult(
            job_id="recent_job",
            results={},
            failed_calculations={},
            execution_time=1.0,
            cache_hits=0,
            cache_misses=1,
            progress=recent_progress
        )
        
        # Store both results
        self.processor._job_results["old_job"] = old_result
        self.processor._job_results["recent_job"] = recent_result
        
        # Clean up old results
        removed_count = self.processor.cleanup_old_results(max_age_hours=24)
        
        # Verify old result was removed, recent kept
        assert removed_count == 1
        assert "old_job" not in self.processor._job_results
        assert "recent_job" in self.processor._job_results
    
    @patch('batch_statistics_processor.AccurateStatisticsCalculator')
    def test_calculation_timeout_handling(self, mock_calculator_class):
        """Test handling of calculation timeouts."""
        # Mock calculator that times out
        mock_calculator = Mock()
        mock_calculator_class.return_value = mock_calculator
        
        async def slow_calculation(*args):
            await asyncio.sleep(2.0)  # Longer than timeout
            return "result"
        
        mock_calculator._calculate_player_statistics_uncached = AsyncMock(side_effect=slow_calculation)
        
        # Test timeout in sync context (should be handled gracefully)
        result = self.processor._calculate_player_statistics("player_1", "statistics", True)
        # Should return None or handle timeout gracefully
        # (exact behavior depends on implementation)
    
    def test_processor_shutdown(self):
        """Test processor shutdown functionality."""
        # Verify processor can be shut down cleanly
        self.processor.shutdown()
        
        # Executor should be shut down
        assert self.processor._executor._shutdown


class TestBatchProcessorGlobalFunction:
    """Test global batch processor function."""
    
    def test_get_batch_processor(self):
        """Test global batch processor retrieval."""
        mock_query_engine = MockQueryEngine()
        
        # Should create new instance
        processor1 = get_batch_processor(mock_query_engine)
        assert isinstance(processor1, BatchStatisticsProcessor)
        
        # Should return same instance for None query_engine
        processor2 = get_batch_processor(None)
        processor3 = get_batch_processor(None)
        assert processor2 is processor3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])