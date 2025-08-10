"""
Batch Statistics Processor for efficient bulk calculations and leaderboard generation.

This module provides high-performance batch processing capabilities for calculating
multiple player statistics simultaneously, generating leaderboards efficiently,
and handling large-scale statistical operations.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Tuple, Any, Callable, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from collections import defaultdict

from game_arena.storage import QueryEngine
from game_arena.storage.models import GameRecord, GameResult, PlayerInfo
from statistics_calculator import AccurateStatisticsCalculator, AccuratePlayerStatistics, LeaderboardEntry
from statistics_cache import StatisticsCache, get_statistics_cache
from elo_rating import ELORatingSystem, GameOutcome

logger = logging.getLogger(__name__)


@dataclass
class BatchJobProgress:
    """Progress tracking for batch processing jobs."""
    job_id: str
    total_items: int
    processed_items: int = 0
    failed_items: int = 0
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    status: str = "running"  # running, completed, failed, cancelled
    errors: List[str] = field(default_factory=list)
    
    @property
    def progress_percentage(self) -> float:
        """Calculate progress percentage."""
        if self.total_items == 0:
            return 100.0
        return (self.processed_items / self.total_items) * 100.0
    
    @property
    def elapsed_time(self) -> timedelta:
        """Calculate elapsed time."""
        end_time = self.end_time or datetime.now()
        return end_time - self.start_time
    
    def mark_completed(self) -> None:
        """Mark job as completed."""
        self.end_time = datetime.now()
        self.status = "completed"
    
    def mark_failed(self, error: str) -> None:
        """Mark job as failed."""
        self.end_time = datetime.now()
        self.status = "failed"
        self.errors.append(error)


@dataclass
class BatchCalculationRequest:
    """Request for batch calculation."""
    player_ids: List[str]
    calculation_type: str  # "statistics", "leaderboard", "elo_history"
    include_incomplete_data: bool = True
    cache_results: bool = True
    cache_ttl: float = 300.0
    priority: int = 1  # Higher number = higher priority


@dataclass
class BatchCalculationResult:
    """Result of batch calculation."""
    job_id: str
    results: Dict[str, Any]
    failed_calculations: Dict[str, str]
    execution_time: float
    cache_hits: int
    cache_misses: int
    progress: BatchJobProgress


class BatchStatisticsProcessor:
    """
    High-performance batch processor for statistics calculations.
    
    Provides efficient bulk processing capabilities for:
    - Multiple player statistics calculation
    - Leaderboard generation and updates
    - ELO rating batch calculations
    - Progressive data loading
    """
    
    def __init__(
        self,
        query_engine: QueryEngine,
        cache: Optional[StatisticsCache] = None,
        max_workers: int = 4,
        batch_size: int = 50,
        enable_progressive_loading: bool = True
    ):
        """Initialize the batch processor."""
        self.query_engine = query_engine
        self.cache = cache or get_statistics_cache()
        self.max_workers = max_workers
        self.batch_size = batch_size
        self.enable_progressive_loading = enable_progressive_loading
        
        # Create statistics calculator
        self.stats_calculator = AccurateStatisticsCalculator(query_engine, cache)
        self.elo_system = ELORatingSystem()
        
        # Job tracking
        self._active_jobs: Dict[str, BatchJobProgress] = {}
        self._job_results: Dict[str, BatchCalculationResult] = {}
        
        # Performance metrics
        self._performance_metrics = {
            'total_jobs': 0,
            'successful_jobs': 0,
            'failed_jobs': 0,
            'average_processing_time': 0.0,
            'total_items_processed': 0,
            'cache_efficiency': 0.0
        }
        
        # Thread pool for concurrent processing
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        
        logger.info(f"BatchStatisticsProcessor initialized with {max_workers} workers, batch size {batch_size}")
    
    async def process_batch_statistics(
        self,
        request: BatchCalculationRequest
    ) -> BatchCalculationResult:
        """
        Process batch statistics calculation request.
        
        Args:
            request: Batch calculation request
            
        Returns:
            BatchCalculationResult with processing results
        """
        job_id = f"batch_stats_{int(time.time() * 1000)}"
        start_time = time.time()
        
        # Initialize progress tracking
        progress = BatchJobProgress(
            job_id=job_id,
            total_items=len(request.player_ids)
        )
        self._active_jobs[job_id] = progress
        
        logger.info(f"Starting batch statistics processing job {job_id} for {len(request.player_ids)} players")
        
        try:
            results = {}
            failed_calculations = {}
            cache_hits = 0
            cache_misses = 0
            
            # Process in batches for memory efficiency
            player_batches = [
                request.player_ids[i:i + self.batch_size]
                for i in range(0, len(request.player_ids), self.batch_size)
            ]
            
            for batch_index, player_batch in enumerate(player_batches):
                logger.debug(f"Processing batch {batch_index + 1}/{len(player_batches)} with {len(player_batch)} players")
                
                # Process batch concurrently
                batch_results = await self._process_player_batch(
                    player_batch,
                    request,
                    progress
                )
                
                # Merge results
                results.update(batch_results['results'])
                failed_calculations.update(batch_results['failed'])
                cache_hits += batch_results['cache_hits']
                cache_misses += batch_results['cache_misses']
                
                # Update progress
                progress.processed_items += len(player_batch)
                progress.failed_items += len(batch_results['failed'])
                
                logger.debug(f"Batch {batch_index + 1} completed: {len(batch_results['results'])} successful, {len(batch_results['failed'])} failed")
            
            # Mark job as completed
            progress.mark_completed()
            execution_time = time.time() - start_time
            
            # Create result
            result = BatchCalculationResult(
                job_id=job_id,
                results=results,
                failed_calculations=failed_calculations,
                execution_time=execution_time,
                cache_hits=cache_hits,
                cache_misses=cache_misses,
                progress=progress
            )
            
            # Store result and update metrics
            self._job_results[job_id] = result
            self._update_performance_metrics(result)
            
            logger.info(f"Batch job {job_id} completed in {execution_time:.2f}s: "
                       f"{len(results)} successful, {len(failed_calculations)} failed, "
                       f"cache hit rate: {cache_hits/(cache_hits+cache_misses)*100:.1f}%")
            
            return result
            
        except Exception as e:
            progress.mark_failed(str(e))
            logger.error(f"Batch job {job_id} failed: {e}")
            raise
        finally:
            # Clean up active job tracking
            if job_id in self._active_jobs:
                del self._active_jobs[job_id]
    
    async def _process_player_batch(
        self,
        player_ids: List[str],
        request: BatchCalculationRequest,
        progress: BatchJobProgress
    ) -> Dict[str, Any]:
        """Process a batch of players concurrently."""
        
        # First, try to get cached results
        cache_requests = []
        for player_id in player_ids:
            cache_requests.append({
                'key_parts': ['player_stats', player_id, request.include_incomplete_data],
                'calculator': None,  # Will be set later if needed
                'ttl': request.cache_ttl,
                'dependencies': [f'player:{player_id}']
            })
        
        # Batch cache lookup
        cached_results = self.cache.batch_get(cache_requests)
        
        results = {}
        failed = {}
        cache_hits = 0
        cache_misses = 0
        players_to_calculate = []
        
        # Identify cache hits and misses
        for i, player_id in enumerate(player_ids):
            if i in cached_results and cached_results[i] is not None:
                results[player_id] = cached_results[i]
                cache_hits += 1
            else:
                players_to_calculate.append(player_id)
                cache_misses += 1
        
        # Calculate statistics for cache misses
        if players_to_calculate:
            calculation_futures = []
            
            # Submit calculation tasks
            for player_id in players_to_calculate:
                future = self._executor.submit(
                    self._calculate_player_statistics,
                    player_id,
                    request.calculation_type,
                    request.include_incomplete_data
                )
                calculation_futures.append((player_id, future))
            
            # Collect results as they complete
            for player_id, future in calculation_futures:
                try:
                    result = future.result(timeout=30)  # 30 second timeout per calculation
                    if result is not None:
                        results[player_id] = result
                        
                        # Cache the result if requested
                        if request.cache_results:
                            self.cache.set(
                                ['player_stats', player_id, request.include_incomplete_data],
                                result,
                                request.cache_ttl,
                                [f'player:{player_id}']
                            )
                    else:
                        failed[player_id] = "Calculation returned None"
                        
                except Exception as e:
                    failed[player_id] = str(e)
                    logger.error(f"Failed to calculate statistics for player {player_id}: {e}")
        
        return {
            'results': results,
            'failed': failed,
            'cache_hits': cache_hits,
            'cache_misses': cache_misses
        }
    
    def _calculate_player_statistics(
        self,
        player_id: str,
        calculation_type: str,
        include_incomplete_data: bool
    ) -> Optional[Any]:
        """Calculate statistics for a single player (synchronous)."""
        try:
            if calculation_type == "statistics":
                # Use asyncio.run for async function in sync context
                loop = None
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                return loop.run_until_complete(
                    self.stats_calculator._calculate_player_statistics_uncached(
                        player_id, include_incomplete_data
                    )
                )
            else:
                logger.warning(f"Unknown calculation type: {calculation_type}")
                return None
                
        except Exception as e:
            logger.error(f"Error calculating {calculation_type} for player {player_id}: {e}")
            return None
    
    async def generate_leaderboard_batch(
        self,
        sort_by: str = "elo_rating",
        min_games: int = 5,
        limit: int = 100,
        force_recalculate: bool = False
    ) -> List[LeaderboardEntry]:
        """
        Generate leaderboard using batch processing for optimal performance.
        
        Args:
            sort_by: Sorting criteria
            min_games: Minimum games required
            limit: Maximum number of entries
            force_recalculate: Force recalculation instead of using cache
            
        Returns:
            List of leaderboard entries
        """
        logger.info(f"Generating leaderboard (sort_by={sort_by}, limit={limit}, force={force_recalculate})")
        
        # Check cache first unless force recalculation is requested
        if not force_recalculate:
            cached_leaderboard = self.cache.get(
                ['leaderboard', sort_by, min_games, limit],
                dependencies=['leaderboard']
            )
            if cached_leaderboard is not None:
                logger.debug("Returning cached leaderboard")
                return cached_leaderboard
        
        start_time = time.time()
        
        try:
            # Get all unique players
            all_games = await self.query_engine.storage_manager.query_games({})
            player_ids = set()
            
            for game in all_games:
                for player_info in game.players.values():
                    player_ids.add(player_info.player_id)
            
            # Create batch request for all players
            batch_request = BatchCalculationRequest(
                player_ids=list(player_ids),
                calculation_type="statistics",
                include_incomplete_data=True,
                cache_results=True,
                cache_ttl=600.0  # 10 minutes for leaderboard data
            )
            
            # Process batch statistics
            batch_result = await self.process_batch_statistics(batch_request)
            
            # Filter and sort results
            leaderboard_entries = []
            
            for player_id, stats in batch_result.results.items():
                if isinstance(stats, AccuratePlayerStatistics) and stats.completed_games >= min_games:
                    # Calculate ranking score
                    if sort_by == "elo_rating":
                        ranking_score = stats.current_elo
                    elif sort_by == "win_rate":
                        ranking_score = stats.win_rate
                    elif sort_by == "games_played":
                        ranking_score = stats.completed_games
                    else:
                        ranking_score = stats.current_elo
                    
                    entry = LeaderboardEntry(
                        rank=0,  # Will be set after sorting
                        player_id=player_id,
                        model_name=stats.model_name,
                        model_provider=stats.model_provider,
                        statistics=stats,
                        ranking_score=ranking_score
                    )
                    leaderboard_entries.append(entry)
            
            # Sort by ranking score (descending)
            leaderboard_entries.sort(key=lambda x: x.ranking_score, reverse=True)
            
            # Assign ranks and limit results
            final_entries = []
            for i, entry in enumerate(leaderboard_entries[:limit]):
                entry.rank = i + 1
                final_entries.append(entry)
            
            # Cache the result
            self.cache.set(
                ['leaderboard', sort_by, min_games, limit],
                final_entries,
                ttl=600.0,  # 10 minutes
                dependencies=['leaderboard']
            )
            
            execution_time = time.time() - start_time
            logger.info(f"Generated leaderboard with {len(final_entries)} entries in {execution_time:.2f}s "
                       f"(cache hit rate: {batch_result.cache_hits/(batch_result.cache_hits+batch_result.cache_misses)*100:.1f}%)")
            
            return final_entries
            
        except Exception as e:
            logger.error(f"Failed to generate leaderboard: {e}")
            return []
    
    def get_job_progress(self, job_id: str) -> Optional[BatchJobProgress]:
        """Get progress information for a batch job."""
        return self._active_jobs.get(job_id)
    
    def get_job_result(self, job_id: str) -> Optional[BatchCalculationResult]:
        """Get result for a completed batch job."""
        return self._job_results.get(job_id)
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for batch processing."""
        return self._performance_metrics.copy()
    
    def _update_performance_metrics(self, result: BatchCalculationResult) -> None:
        """Update performance metrics with job result."""
        self._performance_metrics['total_jobs'] += 1
        
        if result.progress.status == 'completed':
            self._performance_metrics['successful_jobs'] += 1
        else:
            self._performance_metrics['failed_jobs'] += 1
        
        # Update average processing time
        total_time = self._performance_metrics['average_processing_time'] * (self._performance_metrics['total_jobs'] - 1)
        total_time += result.execution_time
        self._performance_metrics['average_processing_time'] = total_time / self._performance_metrics['total_jobs']
        
        # Update items processed
        self._performance_metrics['total_items_processed'] += result.progress.total_items
        
        # Update cache efficiency
        if result.cache_hits + result.cache_misses > 0:
            cache_efficiency = result.cache_hits / (result.cache_hits + result.cache_misses)
            total_cache_ops = self._performance_metrics.get('total_cache_operations', 0)
            current_efficiency = self._performance_metrics['cache_efficiency']
            
            # Weighted average
            new_ops = result.cache_hits + result.cache_misses
            new_efficiency = (current_efficiency * total_cache_ops + cache_efficiency * new_ops) / (total_cache_ops + new_ops)
            
            self._performance_metrics['cache_efficiency'] = new_efficiency
            self._performance_metrics['total_cache_operations'] = total_cache_ops + new_ops
    
    def cleanup_old_results(self, max_age_hours: int = 24) -> int:
        """Clean up old job results."""
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        removed_count = 0
        
        job_ids_to_remove = []
        for job_id, result in self._job_results.items():
            if result.progress.start_time < cutoff_time:
                job_ids_to_remove.append(job_id)
        
        for job_id in job_ids_to_remove:
            del self._job_results[job_id]
            removed_count += 1
        
        logger.info(f"Cleaned up {removed_count} old job results")
        return removed_count
    
    def shutdown(self) -> None:
        """Shutdown the batch processor and clean up resources."""
        logger.info("Shutting down BatchStatisticsProcessor")
        self._executor.shutdown(wait=True)


# Global batch processor instance
_global_batch_processor: Optional[BatchStatisticsProcessor] = None


def get_batch_processor(query_engine: QueryEngine) -> BatchStatisticsProcessor:
    """Get the global batch processor instance."""
    global _global_batch_processor
    if _global_batch_processor is None:
        _global_batch_processor = BatchStatisticsProcessor(query_engine)
    return _global_batch_processor