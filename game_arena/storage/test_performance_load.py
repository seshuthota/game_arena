"""
Performance and Load Testing for the Game Arena storage system.

This module provides comprehensive performance and load tests to validate
scalability requirements, concurrent operations, query performance with
large datasets, and memory/resource consumption monitoring.

Requirements tested:
- 5.1: Performance constraints (50ms latency limit)
- 5.2: Query performance with large datasets
- 5.3: Concurrent operations without data corruption
"""

import asyncio
import gc
import logging
import os
import pytest
import pytest_asyncio
import random
import statistics
import tempfile
import time
import tracemalloc
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple
from unittest.mock import Mock, patch

# Optional dependency handling
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    psutil = None

from .backends.sqlite_backend import SQLiteBackend
from .backends.postgresql_backend import PostgreSQLBackend
from .collector import GameDataCollector
from .config import StorageConfig, CollectorConfig, DatabaseConfig, StorageBackendType
from .manager import StorageManager
from .models import (
    GameRecord, MoveRecord, PlayerInfo, GameOutcome, GameResult, 
    TerminationReason, RethinkAttempt
)
from .query_engine import QueryEngine, GameFilters, MoveFilters


logger = logging.getLogger(__name__)


# Test configuration constants
LARGE_DATASET_SIZE = 1000  # Number of games for large dataset tests
CONCURRENT_OPERATIONS = 50  # Number of concurrent operations to test
PERFORMANCE_THRESHOLD_MS = 50  # Maximum allowed latency per requirement 5.1
MEMORY_THRESHOLD_MB = 100  # Maximum memory increase allowed during tests
QUERY_PERFORMANCE_THRESHOLD_MS = 1000  # Maximum query time for large datasets


@pytest.fixture
def performance_config():
    """Create configuration optimized for performance testing."""
    from .config import DatabaseConfig, StorageBackendType, LogLevel
    
    # Create a minimal database config for testing
    db_config = DatabaseConfig(
        backend_type=StorageBackendType.SQLITE,
        database=":memory:",  # Use in-memory database for speed
        connection_pool_size=1
    )
    
    return StorageConfig(
        database=db_config,
        enable_data_validation=True,
        max_concurrent_writes=20,
        write_timeout_seconds=30,
        log_level=LogLevel.WARNING,  # Reduce logging overhead
        enable_metrics=False  # Disable metrics for consistent timing
    )


@pytest.fixture
def collector_config():
    """Create collector configuration for performance testing."""
    return CollectorConfig(
        enabled=True,
        async_processing=True,
        worker_threads=4,
        queue_size=1000,
        max_collection_latency_ms=PERFORMANCE_THRESHOLD_MS,
        max_retry_attempts=3,
        retry_delay_seconds=0.1,
        continue_on_collection_error=True,
        collect_rethink_data=True
    )


@pytest_asyncio.fixture
async def sqlite_performance_backend(performance_config):
    """Create SQLite backend optimized for performance testing."""
    db_fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(db_fd)
    
    db_config = DatabaseConfig(
        backend_type=StorageBackendType.SQLITE,
        database=db_path,  # Use 'database' not 'database_path'
        connection_pool_size=1  # SQLite should use 1
    )
    
    backend = SQLiteBackend(db_config)
    await backend.connect()
    await backend.initialize_schema()
    
    yield backend
    
    await backend.disconnect()
    try:
        os.unlink(db_path)
    except OSError:
        pass


@pytest_asyncio.fixture
async def storage_manager_perf(sqlite_performance_backend, performance_config):
    """Create storage manager for performance testing."""
    manager = StorageManager(sqlite_performance_backend, performance_config)
    await manager.initialize()
    
    yield manager
    
    await manager.shutdown()


@pytest_asyncio.fixture
async def collector_perf(storage_manager_perf, collector_config):
    """Create game data collector for performance testing."""
    collector = GameDataCollector(storage_manager_perf, collector_config)
    await collector.initialize()
    
    yield collector
    
    await collector.shutdown()


@pytest.fixture
def sample_players_perf():
    """Create sample players for performance testing."""
    return {
        0: PlayerInfo(
            player_id="perf_player_black",
            model_name="gpt-4-perf",
            model_provider="openai",
            agent_type="ChessLLMAgent",
            agent_config={"temperature": 0.7},
            elo_rating=1500.0
        ),
        1: PlayerInfo(
            player_id="perf_player_white", 
            model_name="gemini-pro-perf",
            model_provider="google",
            agent_type="ChessRethinkAgent",
            agent_config={"max_rethink": 3},
            elo_rating=1600.0
        )
    }


def _create_random_outcome() -> GameOutcome:
    """Create a random but valid game outcome."""
    result = random.choice([GameResult.WHITE_WINS, GameResult.BLACK_WINS, GameResult.DRAW])
    
    if result == GameResult.WHITE_WINS:
        winner = 1  # White is player 1
    elif result == GameResult.BLACK_WINS:
        winner = 0  # Black is player 0
    else:  # DRAW
        winner = None
    
    termination = random.choice([
        TerminationReason.CHECKMATE, TerminationReason.RESIGNATION, 
        TerminationReason.STALEMATE, TerminationReason.TIMEOUT
    ])
    
    return GameOutcome(
        result=result,
        winner=winner,
        termination=termination
    )


def create_sample_game(game_id: str, players: Dict[int, PlayerInfo], 
                      tournament_id: str = None) -> GameRecord:
    """Create a sample game record for testing."""
    return GameRecord(
        game_id=game_id,
        tournament_id=tournament_id,
        start_time=datetime.now() - timedelta(minutes=random.randint(1, 60)),
        end_time=datetime.now(),
        players=players,
        initial_fen="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
        final_fen="r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/3P1N2/PPP2PPP/RNBQK2R w KQkq - 4 4",
        outcome=_create_random_outcome(),
        total_moves=random.randint(20, 100),
        game_duration_seconds=random.uniform(300, 3600),
        metadata={"test": "performance", "batch": "load_test"}
    )


def create_sample_move(game_id: str, move_number: int, player: int) -> MoveRecord:
    """Create a sample move record for testing."""
    return MoveRecord(
        game_id=game_id,
        move_number=move_number,
        player=player,
        timestamp=datetime.now(),
        fen_before="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
        fen_after="rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1",
        legal_moves=["e4", "d4", "Nf3", "c4"],
        move_san="e4",
        move_uci="e2e4",
        is_legal=random.choice([True, True, True, False]),  # 75% legal moves
        prompt_text="What is your next move?",
        raw_response="I'll play e4 to control the center.",
        parsed_move="e4",
        parsing_success=random.choice([True, True, False]),  # 67% parsing success
        parsing_attempts=random.randint(1, 3),
        thinking_time_ms=random.randint(100, 5000),
        api_call_time_ms=random.randint(50, 1000),
        parsing_time_ms=random.randint(1, 50),
        rethink_attempts=[],
        move_quality_score=random.uniform(0.0, 1.0),
        blunder_flag=random.choice([True, False]),
        error_type=None,
        error_message=None
    )


class TestConcurrentGameDataCollection:
    """Test concurrent game data collection performance and correctness."""
    
    @pytest.mark.asyncio
    async def test_concurrent_game_creation(self, storage_manager_perf, sample_players_perf):
        """Test concurrent game creation without data corruption."""
        start_time = time.time()
        
        async def create_game(game_index: int) -> str:
            game = create_sample_game(
                f"concurrent_game_{game_index}",
                sample_players_perf,
                f"tournament_{game_index % 5}"
            )
            return await storage_manager_perf.create_game(game)
        
        # Create games concurrently
        tasks = [create_game(i) for i in range(CONCURRENT_OPERATIONS)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        creation_time = (time.time() - start_time) * 1000
        
        # Verify all operations succeeded
        successful_results = [r for r in results if isinstance(r, str)]
        failed_results = [r for r in results if isinstance(r, Exception)]
        
        assert len(successful_results) == CONCURRENT_OPERATIONS, \
            f"Expected {CONCURRENT_OPERATIONS} successful creations, got {len(successful_results)}. Failures: {failed_results}"
        
        # Verify no duplicate game IDs
        assert len(set(successful_results)) == len(successful_results), \
            "Duplicate game IDs detected in concurrent creation"
        
        # Verify performance constraint (Requirement 5.1)
        avg_time_per_game = creation_time / CONCURRENT_OPERATIONS
        assert avg_time_per_game < PERFORMANCE_THRESHOLD_MS, \
            f"Average game creation time {avg_time_per_game:.1f}ms exceeds threshold {PERFORMANCE_THRESHOLD_MS}ms"
        
        logger.info(f"Concurrent game creation: {CONCURRENT_OPERATIONS} games in {creation_time:.1f}ms "
                   f"(avg {avg_time_per_game:.1f}ms per game)")
    
    @pytest.mark.asyncio
    async def test_concurrent_move_recording(self, storage_manager_perf, sample_players_perf):
        """Test concurrent move recording for multiple games."""
        # Create a base game first
        game = create_sample_game("concurrent_moves_game", sample_players_perf)
        await storage_manager_perf.create_game(game)
        
        start_time = time.time()
        
        async def add_move(move_index: int) -> bool:
            move = create_sample_move(
                "concurrent_moves_game",
                move_index + 1,
                move_index % 2
            )
            return await storage_manager_perf.add_move(move)
        
        # Add moves concurrently
        tasks = [add_move(i) for i in range(CONCURRENT_OPERATIONS)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        recording_time = (time.time() - start_time) * 1000
        
        # Verify all operations succeeded
        successful_results = [r for r in results if r is True]
        failed_results = [r for r in results if isinstance(r, Exception)]
        
        assert len(successful_results) == CONCURRENT_OPERATIONS, \
            f"Expected {CONCURRENT_OPERATIONS} successful move recordings, got {len(successful_results)}. Failures: {failed_results}"
        
        # Verify performance constraint
        avg_time_per_move = recording_time / CONCURRENT_OPERATIONS
        assert avg_time_per_move < PERFORMANCE_THRESHOLD_MS, \
            f"Average move recording time {avg_time_per_move:.1f}ms exceeds threshold {PERFORMANCE_THRESHOLD_MS}ms"
        
        # Verify data integrity - check that all moves were stored
        stored_moves = await storage_manager_perf.get_moves("concurrent_moves_game")
        assert len(stored_moves) == CONCURRENT_OPERATIONS, \
            f"Expected {CONCURRENT_OPERATIONS} stored moves, found {len(stored_moves)}"
        
        logger.info(f"Concurrent move recording: {CONCURRENT_OPERATIONS} moves in {recording_time:.1f}ms "
                   f"(avg {avg_time_per_move:.1f}ms per move)")
    
    @pytest.mark.asyncio
    async def test_concurrent_data_collection_events(self, collector_perf, sample_players_perf):
        """Test concurrent event processing in GameDataCollector."""
        start_time = time.time()
        
        # Start multiple games concurrently
        game_start_tasks = []
        for i in range(CONCURRENT_OPERATIONS):
            game_id = f"collector_concurrent_game_{i}"
            task = asyncio.create_task(
                asyncio.to_thread(
                    collector_perf.start_game,
                    game_id,
                    sample_players_perf,
                    {"tournament_id": f"concurrent_tournament_{i % 5}"}
                )
            )
            game_start_tasks.append(task)
        
        # Wait for all game starts to complete
        start_results = await asyncio.gather(*game_start_tasks, return_exceptions=True)
        
        collection_time = (time.time() - start_time) * 1000
        
        # Verify all events were queued successfully
        successful_starts = [r for r in start_results if r is True]
        failed_starts = [r for r in start_results if isinstance(r, Exception)]
        
        assert len(successful_starts) == CONCURRENT_OPERATIONS, \
            f"Expected {CONCURRENT_OPERATIONS} successful event collections, got {len(successful_starts)}. Failures: {failed_starts}"
        
        # Wait for event processing to complete
        await asyncio.sleep(1.0)
        
        # Verify performance constraint
        avg_time_per_event = collection_time / CONCURRENT_OPERATIONS
        assert avg_time_per_event < PERFORMANCE_THRESHOLD_MS, \
            f"Average event collection time {avg_time_per_event:.1f}ms exceeds threshold {PERFORMANCE_THRESHOLD_MS}ms"
        
        # Check collector statistics
        stats = collector_perf.get_stats()
        assert stats.events_received >= CONCURRENT_OPERATIONS, \
            f"Expected at least {CONCURRENT_OPERATIONS} events received, got {stats.events_received}"
        
        logger.info(f"Concurrent event collection: {CONCURRENT_OPERATIONS} events in {collection_time:.1f}ms "
                   f"(avg {avg_time_per_event:.1f}ms per event)")


class TestLargeDatasetQueryPerformance:
    """Test query performance with large datasets."""
    
    @pytest.mark.asyncio
    async def test_setup_large_dataset(self, storage_manager_perf, sample_players_perf):
        """Set up a large dataset for query performance testing."""
        logger.info(f"Creating large dataset with {LARGE_DATASET_SIZE} games...")
        
        start_time = time.time()
        
        # Create games in batches for better performance
        batch_size = 50
        for batch_start in range(0, LARGE_DATASET_SIZE, batch_size):
            batch_end = min(batch_start + batch_size, LARGE_DATASET_SIZE)
            batch_tasks = []
            
            for i in range(batch_start, batch_end):
                game = create_sample_game(
                    f"large_dataset_game_{i}",
                    sample_players_perf,
                    f"tournament_{i % 10}"
                )
                batch_tasks.append(storage_manager_perf.create_game(game))
            
            await asyncio.gather(*batch_tasks)
            
            # Add moves for each game in the batch
            for i in range(batch_start, batch_end):
                game_id = f"large_dataset_game_{i}"
                move_tasks = []
                num_moves = random.randint(10, 50)
                
                for move_num in range(num_moves):
                    move = create_sample_move(game_id, move_num + 1, move_num % 2)
                    move_tasks.append(storage_manager_perf.add_move(move))
                
                await asyncio.gather(*move_tasks)
        
        setup_time = time.time() - start_time
        logger.info(f"Large dataset setup completed in {setup_time:.1f} seconds")
        
        # Verify dataset size
        all_games = await storage_manager_perf.query_games({})
        assert len(all_games) >= LARGE_DATASET_SIZE, \
            f"Expected at least {LARGE_DATASET_SIZE} games, found {len(all_games)}"
    
    @pytest.mark.asyncio
    async def test_query_performance_large_dataset(self, storage_manager_perf, sample_players_perf):
        """Test query performance with large dataset."""
        # First set up the large dataset
        await self.test_setup_large_dataset(storage_manager_perf, sample_players_perf)
        
        query_engine = QueryEngine(storage_manager_perf)
        
        # Test various query types and measure performance
        query_tests = [
            ("all_games", lambda: storage_manager_perf.query_games({})),
            ("games_by_player", lambda: query_engine.get_games_by_players("perf_player_black")),
            ("games_by_tournament", lambda: query_engine.get_games_by_tournament("tournament_1")),
            ("games_by_outcome", lambda: query_engine.get_games_by_outcome(GameResult.WHITE_WINS)),
            ("recent_games", lambda: query_engine.get_recent_games(hours=24, limit=100)),
        ]
        
        performance_results = {}
        
        for query_name, query_func in query_tests:
            start_time = time.time()
            results = await query_func()
            query_time = (time.time() - start_time) * 1000
            
            performance_results[query_name] = {
                'time_ms': query_time,
                'result_count': len(results)
            }
            
            # Verify performance constraint (Requirement 5.2)
            assert query_time < QUERY_PERFORMANCE_THRESHOLD_MS, \
                f"Query '{query_name}' took {query_time:.1f}ms, exceeds threshold {QUERY_PERFORMANCE_THRESHOLD_MS}ms"
            
            logger.info(f"Query '{query_name}': {query_time:.1f}ms, {len(results)} results")
        
        # Test complex filtering query
        start_time = time.time()
        filters = GameFilters(
            start_time_after=datetime.now() - timedelta(hours=2),
            results=[GameResult.WHITE_WINS, GameResult.BLACK_WINS],
            min_moves=20,
            max_moves=80
        )
        complex_results = await query_engine.query_games_advanced(filters, limit=50)
        complex_query_time = (time.time() - start_time) * 1000
        
        assert complex_query_time < QUERY_PERFORMANCE_THRESHOLD_MS, \
            f"Complex query took {complex_query_time:.1f}ms, exceeds threshold {QUERY_PERFORMANCE_THRESHOLD_MS}ms"
        
        logger.info(f"Complex query: {complex_query_time:.1f}ms, {len(complex_results)} results")
        
        return performance_results
    
    @pytest.mark.asyncio
    async def test_move_query_performance_large_dataset(self, storage_manager_perf, sample_players_perf):
        """Test move query performance with large dataset."""
        # Use existing large dataset
        all_games = await storage_manager_perf.query_games({})
        if len(all_games) < LARGE_DATASET_SIZE:
            await self.test_setup_large_dataset(storage_manager_perf, sample_players_perf)
            all_games = await storage_manager_perf.query_games({})
        
        # Test move queries on multiple games
        test_games = random.sample(all_games, min(10, len(all_games)))
        
        for game in test_games:
            start_time = time.time()
            moves = await storage_manager_perf.get_moves(game.game_id)
            query_time = (time.time() - start_time) * 1000
            
            # Verify performance constraint
            assert query_time < PERFORMANCE_THRESHOLD_MS, \
                f"Move query for game {game.game_id} took {query_time:.1f}ms, exceeds threshold {PERFORMANCE_THRESHOLD_MS}ms"
            
            # Test filtered move queries
            start_time = time.time()
            illegal_moves = await storage_manager_perf.get_moves_with_filters(
                game.game_id, {'is_legal': False}
            )
            filtered_query_time = (time.time() - start_time) * 1000
            
            assert filtered_query_time < PERFORMANCE_THRESHOLD_MS, \
                f"Filtered move query took {filtered_query_time:.1f}ms, exceeds threshold {PERFORMANCE_THRESHOLD_MS}ms"
        
        logger.info(f"Move query performance test completed for {len(test_games)} games")


class TestMemoryAndResourceConsumption:
    """Test memory usage and resource consumption during operations."""
    
    @pytest.mark.skipif(not PSUTIL_AVAILABLE, reason="psutil not available")
    @pytest.mark.asyncio
    async def test_memory_usage_during_large_operations(self, storage_manager_perf, sample_players_perf):
        """Test memory consumption during large-scale operations."""
        # Start memory tracking
        tracemalloc.start()
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        logger.info(f"Initial memory usage: {initial_memory:.1f} MB")
        
        # Perform large-scale operations
        operations_count = 500
        
        # Create games and moves
        for i in range(operations_count):
            game = create_sample_game(
                f"memory_test_game_{i}",
                sample_players_perf,
                f"memory_tournament_{i % 5}"
            )
            await storage_manager_perf.create_game(game)
            
            # Add some moves
            for move_num in range(10):
                move = create_sample_move(f"memory_test_game_{i}", move_num + 1, move_num % 2)
                await storage_manager_perf.add_move(move)
            
            # Check memory every 100 operations
            if (i + 1) % 100 == 0:
                current_memory = process.memory_info().rss / 1024 / 1024
                memory_increase = current_memory - initial_memory
                
                logger.info(f"After {i + 1} operations: {current_memory:.1f} MB "
                           f"(+{memory_increase:.1f} MB)")
                
                # Verify memory usage stays within reasonable bounds
                assert memory_increase < MEMORY_THRESHOLD_MB, \
                    f"Memory usage increased by {memory_increase:.1f} MB, exceeds threshold {MEMORY_THRESHOLD_MB} MB"
        
        # Final memory check
        final_memory = process.memory_info().rss / 1024 / 1024
        total_memory_increase = final_memory - initial_memory
        
        logger.info(f"Final memory usage: {final_memory:.1f} MB "
                   f"(total increase: {total_memory_increase:.1f} MB)")
        
        # Get memory statistics from tracemalloc
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        logger.info(f"Tracemalloc - Current: {current / 1024 / 1024:.1f} MB, "
                   f"Peak: {peak / 1024 / 1024:.1f} MB")
        
        # Force garbage collection and check if memory is released
        gc.collect()
        await asyncio.sleep(0.1)
        
        post_gc_memory = process.memory_info().rss / 1024 / 1024
        logger.info(f"Memory after GC: {post_gc_memory:.1f} MB")
    
    @pytest.mark.skipif(not PSUTIL_AVAILABLE, reason="psutil not available")
    @pytest.mark.asyncio
    async def test_resource_cleanup_after_operations(self, storage_manager_perf, sample_players_perf):
        """Test that resources are properly cleaned up after operations."""
        initial_open_files = len(psutil.Process().open_files())
        
        # Perform operations that might leave resources open
        for i in range(100):
            game = create_sample_game(f"cleanup_test_game_{i}", sample_players_perf)
            await storage_manager_perf.create_game(game)
            
            # Query the game back
            retrieved_game = await storage_manager_perf.get_game(f"cleanup_test_game_{i}")
            assert retrieved_game is not None
        
        # Check that file handles haven't leaked
        final_open_files = len(psutil.Process().open_files())
        file_handle_increase = final_open_files - initial_open_files
        
        logger.info(f"File handles - Initial: {initial_open_files}, "
                   f"Final: {final_open_files}, Increase: {file_handle_increase}")
        
        # Allow for some reasonable increase but not excessive
        assert file_handle_increase < 10, \
            f"File handle increase of {file_handle_increase} suggests resource leaks"
    
    @pytest.mark.skipif(not PSUTIL_AVAILABLE, reason="psutil not available")
    @pytest.mark.asyncio
    async def test_cpu_usage_during_concurrent_operations(self, storage_manager_perf, sample_players_perf):
        """Test CPU usage during concurrent operations."""
        process = psutil.Process()
        
        # Measure CPU usage during concurrent operations
        cpu_measurements = []
        
        async def monitor_cpu():
            """Monitor CPU usage during operations."""
            for _ in range(10):  # Monitor for 10 seconds
                cpu_percent = process.cpu_percent(interval=1.0)
                cpu_measurements.append(cpu_percent)
        
        async def perform_operations():
            """Perform concurrent operations."""
            tasks = []
            for i in range(CONCURRENT_OPERATIONS):
                game = create_sample_game(f"cpu_test_game_{i}", sample_players_perf)
                tasks.append(storage_manager_perf.create_game(game))
            
            await asyncio.gather(*tasks)
        
        # Run monitoring and operations concurrently
        await asyncio.gather(
            monitor_cpu(),
            perform_operations()
        )
        
        if cpu_measurements:
            avg_cpu = statistics.mean(cpu_measurements)
            max_cpu = max(cpu_measurements)
            
            logger.info(f"CPU usage during concurrent operations - "
                       f"Average: {avg_cpu:.1f}%, Max: {max_cpu:.1f}%")
            
            # Verify CPU usage is reasonable (not exceeding 80% on average)
            assert avg_cpu < 80.0, \
                f"Average CPU usage {avg_cpu:.1f}% is too high during concurrent operations"


class TestScalabilityRequirements:
    """Test scalability requirements validation."""
    
    @pytest.mark.asyncio
    async def test_latency_constraint_validation(self, storage_manager_perf, sample_players_perf):
        """Test that operations consistently meet the 50ms latency constraint (Requirement 5.1)."""
        latency_measurements = []
        operations_count = 100
        
        for i in range(operations_count):
            # Test game creation latency
            start_time = time.time()
            game = create_sample_game(f"latency_test_game_{i}", sample_players_perf)
            await storage_manager_perf.create_game(game)
            creation_latency = (time.time() - start_time) * 1000
            latency_measurements.append(('game_creation', creation_latency))
            
            # Test move addition latency
            start_time = time.time()
            move = create_sample_move(f"latency_test_game_{i}", 1, 0)
            await storage_manager_perf.add_move(move)
            move_latency = (time.time() - start_time) * 1000
            latency_measurements.append(('move_addition', move_latency))
            
            # Test game retrieval latency
            start_time = time.time()
            retrieved_game = await storage_manager_perf.get_game(f"latency_test_game_{i}")
            retrieval_latency = (time.time() - start_time) * 1000
            latency_measurements.append(('game_retrieval', retrieval_latency))
        
        # Analyze latency statistics
        operation_stats = {}
        for operation_type, latency in latency_measurements:
            if operation_type not in operation_stats:
                operation_stats[operation_type] = []
            operation_stats[operation_type].append(latency)
        
        for operation_type, latencies in operation_stats.items():
            avg_latency = statistics.mean(latencies)
            max_latency = max(latencies)
            p95_latency = statistics.quantiles(latencies, n=20)[18]  # 95th percentile
            
            logger.info(f"{operation_type} latency - Avg: {avg_latency:.1f}ms, "
                       f"Max: {max_latency:.1f}ms, P95: {p95_latency:.1f}ms")
            
            # Verify latency constraints
            assert avg_latency < PERFORMANCE_THRESHOLD_MS, \
                f"{operation_type} average latency {avg_latency:.1f}ms exceeds threshold {PERFORMANCE_THRESHOLD_MS}ms"
            
            assert p95_latency < PERFORMANCE_THRESHOLD_MS * 2, \
                f"{operation_type} P95 latency {p95_latency:.1f}ms exceeds threshold {PERFORMANCE_THRESHOLD_MS * 2}ms"
    
    @pytest.mark.asyncio
    async def test_concurrent_write_data_integrity(self, storage_manager_perf, sample_players_perf):
        """Test data integrity during concurrent write operations (Requirement 5.3)."""
        # Create a base game
        base_game = create_sample_game("integrity_test_game", sample_players_perf)
        await storage_manager_perf.create_game(base_game)
        
        # Perform concurrent move additions
        concurrent_moves = 100
        
        async def add_move_with_validation(move_index: int) -> Tuple[bool, str]:
            """Add a move and return success status with move ID."""
            move = create_sample_move("integrity_test_game", move_index + 1, move_index % 2)
            move.move_san = f"move_{move_index}"  # Unique identifier
            
            try:
                success = await storage_manager_perf.add_move(move)
                return success, move.move_san
            except Exception as e:
                logger.error(f"Failed to add move {move_index}: {e}")
                return False, move.move_san
        
        # Execute concurrent move additions
        tasks = [add_move_with_validation(i) for i in range(concurrent_moves)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Analyze results
        successful_moves = []
        failed_moves = []
        
        for result in results:
            if isinstance(result, Exception):
                failed_moves.append(str(result))
            else:
                success, move_id = result
                if success:
                    successful_moves.append(move_id)
                else:
                    failed_moves.append(move_id)
        
        logger.info(f"Concurrent write test - Successful: {len(successful_moves)}, "
                   f"Failed: {len(failed_moves)}")
        
        # Verify data integrity
        stored_moves = await storage_manager_perf.get_moves("integrity_test_game")
        stored_move_ids = [move.move_san for move in stored_moves]
        
        # Check that all successful moves were actually stored
        for move_id in successful_moves:
            assert move_id in stored_move_ids, \
                f"Move {move_id} was reported as successful but not found in storage"
        
        # Check for duplicate moves (data corruption)
        assert len(stored_move_ids) == len(set(stored_move_ids)), \
            "Duplicate moves detected - data corruption occurred"
        
        # Verify no data corruption in move ordering
        stored_moves.sort(key=lambda m: m.move_number)
        for i, move in enumerate(stored_moves):
            expected_player = i % 2
            assert move.player == expected_player, \
                f"Move {i} has incorrect player {move.player}, expected {expected_player}"
    
    @pytest.mark.asyncio
    async def test_system_degradation_under_load(self, storage_manager_perf, collector_perf, sample_players_perf):
        """Test graceful degradation under high load conditions."""
        # Simulate high load conditions
        high_load_operations = 200
        
        # Track performance degradation
        performance_samples = []
        error_count = 0
        
        for batch in range(10):  # 10 batches of 20 operations each
            batch_start_time = time.time()
            batch_tasks = []
            
            for i in range(20):
                operation_id = batch * 20 + i
                
                # Mix of different operations
                if operation_id % 3 == 0:
                    # Game creation
                    game = create_sample_game(f"load_test_game_{operation_id}", sample_players_perf)
                    task = storage_manager_perf.create_game(game)
                elif operation_id % 3 == 1:
                    # Event collection
                    task = asyncio.to_thread(
                        collector_perf.start_game,
                        f"collector_load_game_{operation_id}",
                        sample_players_perf,
                        {"load_test": True}
                    )
                else:
                    # Query operation
                    task = storage_manager_perf.query_games({"limit": 10})
                
                batch_tasks.append(task)
            
            # Execute batch
            try:
                batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
                batch_time = (time.time() - batch_start_time) * 1000
                
                # Count errors in this batch
                batch_errors = sum(1 for r in batch_results if isinstance(r, Exception))
                error_count += batch_errors
                
                performance_samples.append(batch_time / 20)  # Average time per operation
                
                logger.info(f"Batch {batch + 1}: {batch_time:.1f}ms total, "
                           f"{batch_time / 20:.1f}ms avg per op, {batch_errors} errors")
                
            except Exception as e:
                logger.error(f"Batch {batch + 1} failed: {e}")
                error_count += 20  # Count all operations in batch as failed
        
        # Analyze system behavior under load
        if performance_samples:
            avg_performance = statistics.mean(performance_samples)
            performance_degradation = max(performance_samples) / min(performance_samples)
            
            logger.info(f"Load test results - Average performance: {avg_performance:.1f}ms per op, "
                       f"Performance degradation ratio: {performance_degradation:.2f}, "
                       f"Error rate: {error_count / high_load_operations * 100:.1f}%")
            
            # Verify graceful degradation (performance shouldn't degrade more than 3x)
            assert performance_degradation < 3.0, \
                f"Performance degraded by {performance_degradation:.2f}x under load"
            
            # Verify error rate stays reasonable (less than 10%)
            error_rate = error_count / high_load_operations
            assert error_rate < 0.1, \
                f"Error rate {error_rate * 100:.1f}% is too high under load"


@pytest.mark.asyncio
async def test_end_to_end_performance_scenario(storage_manager_perf, collector_perf, sample_players_perf):
    """Test end-to-end performance scenario simulating real tournament usage."""
    logger.info("Starting end-to-end performance scenario...")
    
    # Simulate a tournament with multiple concurrent games
    tournament_id = "performance_tournament"
    num_games = 20
    moves_per_game = 30
    
    start_time = time.time()
    
    # Phase 1: Start all games concurrently
    game_start_tasks = []
    for i in range(num_games):
        game_id = f"e2e_game_{i}"
        task = asyncio.to_thread(
            collector_perf.start_game,
            game_id,
            sample_players_perf,
            {"tournament_id": tournament_id}
        )
        game_start_tasks.append(task)
    
    await asyncio.gather(*game_start_tasks)
    phase1_time = time.time() - start_time
    
    # Phase 2: Record moves for all games concurrently
    phase2_start = time.time()
    move_tasks = []
    
    for game_idx in range(num_games):
        game_id = f"e2e_game_{game_idx}"
        for move_num in range(moves_per_game):
            move_data = {
                'move_number': move_num + 1,
                'player': move_num % 2,
                'fen_before': "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
                'fen_after': "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1",
                'move_san': f"move_{move_num}",
                'move_uci': "e2e4",
                'is_legal': True,
                'prompt_text': "What is your move?",
                'raw_response': f"I play move {move_num}",
                'thinking_time_ms': random.randint(100, 2000)
            }
            
            task = asyncio.to_thread(collector_perf.record_move, game_id, move_data)
            move_tasks.append(task)
    
    await asyncio.gather(*move_tasks)
    phase2_time = time.time() - phase2_start
    
    # Phase 3: End all games and perform queries
    phase3_start = time.time()
    
    # End games
    game_end_tasks = []
    for i in range(num_games):
        game_id = f"e2e_game_{i}"
        outcome = _create_random_outcome()
        
        task = asyncio.to_thread(
            collector_perf.end_game,
            game_id,
            outcome,
            "final_fen_position",
            moves_per_game
        )
        game_end_tasks.append(task)
    
    await asyncio.gather(*game_end_tasks)
    
    # Wait for event processing
    await asyncio.sleep(2.0)
    
    # Perform analytical queries
    query_engine = QueryEngine(storage_manager_perf)
    
    query_tasks = [
        query_engine.get_games_by_tournament(tournament_id),
        query_engine.get_games_by_players("perf_player_black"),
        query_engine.get_games_by_outcome(GameResult.WHITE_WINS),
    ]
    
    query_results = await asyncio.gather(*query_tasks)
    phase3_time = time.time() - phase3_start
    
    total_time = time.time() - start_time
    
    # Verify results
    tournament_games = query_results[0]
    assert len(tournament_games) == num_games, \
        f"Expected {num_games} tournament games, found {len(tournament_games)}"
    
    # Performance analysis
    logger.info(f"End-to-end performance results:")
    logger.info(f"  Phase 1 (game starts): {phase1_time:.2f}s")
    logger.info(f"  Phase 2 (move recording): {phase2_time:.2f}s")
    logger.info(f"  Phase 3 (game ends + queries): {phase3_time:.2f}s")
    logger.info(f"  Total time: {total_time:.2f}s")
    logger.info(f"  Games per second: {num_games / total_time:.2f}")
    logger.info(f"  Moves per second: {(num_games * moves_per_game) / phase2_time:.2f}")
    
    # Verify performance meets requirements
    avg_game_processing_time = total_time / num_games
    assert avg_game_processing_time < 5.0, \
        f"Average game processing time {avg_game_processing_time:.2f}s is too slow"
    
    # Check collector statistics
    stats = collector_perf.get_stats()
    logger.info(f"Collector stats - Received: {stats.events_received}, "
               f"Processed: {stats.events_processed}, Failed: {stats.events_failed}")
    
    assert stats.events_failed == 0, \
        f"Event processing failures detected: {stats.events_failed}"
    
    logger.info("End-to-end performance scenario completed successfully")


if __name__ == "__main__":
    # Run performance tests with pytest
    pytest.main([__file__, "-v", "-s", "--tb=short"])