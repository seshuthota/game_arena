"""
Cache Manager for coordinated cache management and optimization.

This module provides centralized cache management capabilities including
cache coordination, intelligent warming strategies, performance monitoring,
and cross-system cache synchronization.
"""

import asyncio
import logging
import threading
import time
from typing import Dict, List, Optional, Any, Callable, Set, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import json

from statistics_cache import StatisticsCache, get_statistics_cache
from batch_statistics_processor import BatchStatisticsProcessor, BatchCalculationRequest

logger = logging.getLogger(__name__)


class CacheStrategy(str, Enum):
    """Cache warming and management strategies."""
    AGGRESSIVE = "aggressive"    # Preload everything possible
    MODERATE = "moderate"       # Preload frequently accessed data
    CONSERVATIVE = "conservative"  # Only cache on demand
    CUSTOM = "custom"           # User-defined strategy


class CacheType(str, Enum):
    """Types of cached data."""
    PLAYER_STATISTICS = "player_statistics"
    LEADERBOARDS = "leaderboards"
    GAME_ANALYSIS = "game_analysis"
    AGGREGATED_STATS = "aggregated_stats"
    TIME_SERIES = "time_series"


@dataclass
class CacheWarmingTask:
    """Task for cache warming."""
    cache_type: CacheType
    priority: int
    key_parts: List[Any]
    calculator: Callable
    ttl: float
    dependencies: List[str]
    estimated_computation_time: float = 0.0
    access_frequency: int = 1
    last_accessed: Optional[datetime] = None
    
    def __lt__(self, other):
        """Comparison for priority queue."""
        return self.priority > other.priority  # Higher priority first


@dataclass
class CachePerformanceProfile:
    """Performance profile for cache analysis."""
    cache_type: CacheType
    hit_rate: float
    average_response_time: float
    cache_size: int
    eviction_rate: float
    warming_efficiency: float
    total_requests: int
    last_updated: datetime = field(default_factory=datetime.now)


@dataclass
class CacheOptimizationSuggestion:
    """Optimization suggestion for cache performance."""
    cache_type: CacheType
    suggestion_type: str  # "increase_ttl", "add_warming", "adjust_strategy"
    description: str
    expected_improvement: float
    implementation_complexity: str  # "low", "medium", "high"
    priority: int


class CacheManager:
    """
    Centralized cache manager for coordinating multiple caches and optimization.
    
    Provides:
    - Multi-cache coordination and synchronization
    - Intelligent cache warming based on usage patterns
    - Performance monitoring and optimization suggestions
    - Automatic cache maintenance and cleanup
    - Custom warming strategies
    """
    
    def __init__(
        self,
        primary_cache: Optional[StatisticsCache] = None,
        batch_processor: Optional[BatchStatisticsProcessor] = None,
        warming_strategy: CacheStrategy = CacheStrategy.MODERATE,
        max_warming_workers: int = 2,
        warming_interval_minutes: int = 15
    ):
        """Initialize the cache manager."""
        self.primary_cache = primary_cache or get_statistics_cache()
        self.batch_processor = batch_processor
        self.warming_strategy = warming_strategy
        self.max_warming_workers = max_warming_workers
        self.warming_interval = timedelta(minutes=warming_interval_minutes)
        
        # Cache registry for multiple cache instances
        self._cache_registry: Dict[str, StatisticsCache] = {
            'primary': self.primary_cache
        }
        
        # Warming task management
        self._warming_queue: List[CacheWarmingTask] = []
        self._warming_in_progress: Set[str] = set()
        self._warming_lock = threading.RLock()
        self._warming_thread: Optional[threading.Thread] = None
        self._shutdown_warming = threading.Event()
        
        # Performance tracking
        self._performance_profiles: Dict[CacheType, CachePerformanceProfile] = {}
        self._access_patterns: Dict[str, Dict[str, Any]] = {}
        self._optimization_history: List[CacheOptimizationSuggestion] = []
        
        # Usage analytics
        self._usage_stats = {
            'total_requests': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'warming_tasks_completed': 0,
            'optimization_actions_taken': 0,
            'last_maintenance': datetime.now()
        }
        
        # Start background warming if strategy allows
        if warming_strategy != CacheStrategy.CONSERVATIVE:
            self._start_warming_thread()
        
        logger.info(f"CacheManager initialized with strategy: {warming_strategy}")
    
    def register_cache(self, name: str, cache: StatisticsCache) -> None:
        """Register an additional cache instance."""
        self._cache_registry[name] = cache
        logger.info(f"Registered cache: {name}")
    
    def get_cache(self, name: str = 'primary') -> Optional[StatisticsCache]:
        """Get a registered cache by name."""
        return self._cache_registry.get(name)
    
    async def get_with_warming(
        self,
        cache_type: CacheType,
        key_parts: List[Any],
        calculator: Optional[Callable] = None,
        ttl: Optional[float] = None,
        dependencies: Optional[List[str]] = None,
        cache_name: str = 'primary',
        warm_related: bool = True
    ) -> Any:
        """
        Get cached data with intelligent warming of related data.
        
        Args:
            cache_type: Type of cached data
            key_parts: Cache key components
            calculator: Function to calculate value if not cached
            ttl: Time to live for cache entry
            dependencies: Cache dependencies
            cache_name: Name of cache to use
            warm_related: Whether to warm related cache entries
            
        Returns:
            Cached or calculated value
        """
        cache = self.get_cache(cache_name)
        if cache is None:
            logger.error(f"Cache '{cache_name}' not found")
            return None
        
        start_time = time.time()
        
        # Record access pattern
        self._record_access_pattern(cache_type, key_parts)
        
        # Get the value
        result = cache.get(key_parts, calculator, ttl, dependencies)
        
        # Update performance metrics
        response_time = time.time() - start_time
        self._update_performance_metrics(cache_type, result is not None, response_time)
        
        # Schedule related cache warming if enabled
        if warm_related and result is not None:
            await self._schedule_related_warming(cache_type, key_parts, calculator, ttl, dependencies)
        
        return result
    
    async def batch_get_with_warming(
        self,
        cache_type: CacheType,
        batch_requests: List[Dict[str, Any]],
        cache_name: str = 'primary',
        warm_popular: bool = True
    ) -> Dict[str, Any]:
        """
        Batch get with intelligent warming of popular data.
        
        Args:
            cache_type: Type of cached data
            batch_requests: List of batch requests
            cache_name: Name of cache to use
            warm_popular: Whether to warm popular related data
            
        Returns:
            Batch results
        """
        cache = self.get_cache(cache_name)
        if cache is None:
            logger.error(f"Cache '{cache_name}' not found")
            return {}
        
        start_time = time.time()
        
        # Record batch access patterns
        for request in batch_requests:
            self._record_access_pattern(cache_type, request.get('key_parts', []))
        
        # Perform batch get
        results = cache.batch_get(batch_requests)
        
        # Update performance metrics
        response_time = time.time() - start_time
        hit_count = sum(1 for v in results.values() if v is not None)
        miss_count = len(results) - hit_count
        
        for _ in range(hit_count):
            self._update_performance_metrics(cache_type, True, response_time / len(results))
        for _ in range(miss_count):
            self._update_performance_metrics(cache_type, False, response_time / len(results))
        
        # Schedule warming for popular patterns if enabled
        if warm_popular:
            await self._schedule_popular_warming(cache_type, batch_requests)
        
        return results
    
    def add_warming_task(
        self,
        cache_type: CacheType,
        key_parts: List[Any],
        calculator: Callable,
        priority: int = 1,
        ttl: float = 300.0,
        dependencies: Optional[List[str]] = None,
        estimated_time: float = 0.0,
        access_frequency: int = 1
    ) -> None:
        """Add a task to the cache warming queue."""
        task = CacheWarmingTask(
            cache_type=cache_type,
            priority=priority,
            key_parts=key_parts,
            calculator=calculator,
            ttl=ttl,
            dependencies=dependencies or [],
            estimated_computation_time=estimated_time,
            access_frequency=access_frequency
        )
        
        with self._warming_lock:
            # Check if similar task already exists
            task_key = self._generate_task_key(key_parts)
            if task_key not in self._warming_in_progress:
                self._warming_queue.append(task)
                self._warming_queue.sort()  # Sort by priority
                logger.debug(f"Added warming task for {cache_type}: {key_parts}")
    
    def set_warming_strategy(self, strategy: CacheStrategy) -> None:
        """Change the cache warming strategy."""
        old_strategy = self.warming_strategy
        self.warming_strategy = strategy
        
        if strategy == CacheStrategy.CONSERVATIVE and self._warming_thread:
            # Stop warming thread for conservative strategy
            self._shutdown_warming.set()
            self._warming_thread.join(timeout=5)
            self._warming_thread = None
        elif strategy != CacheStrategy.CONSERVATIVE and not self._warming_thread:
            # Start warming thread for active strategies
            self._start_warming_thread()
        
        logger.info(f"Changed warming strategy from {old_strategy} to {strategy}")
    
    async def warm_popular_data(self, top_n: int = 50) -> int:
        """Warm cache with the most popular data based on access patterns."""
        logger.info(f"Warming {top_n} most popular cache entries")
        
        # Analyze access patterns to identify popular data
        popular_patterns = self._identify_popular_patterns(top_n)
        
        warming_tasks = []
        for pattern in popular_patterns:
            if pattern.get('calculator'):
                warming_tasks.append({
                    'key_parts': pattern['key_parts'],
                    'calculator': pattern['calculator'],
                    'ttl': pattern.get('ttl', 300.0),
                    'dependencies': pattern.get('dependencies', []),
                    'access_frequency': pattern.get('access_frequency', 1)
                })
        
        if warming_tasks:
            self.primary_cache.warm_cache(warming_tasks)
            return len(warming_tasks)
        
        return 0
    
    async def optimize_cache_performance(self) -> List[CacheOptimizationSuggestion]:
        """Analyze cache performance and generate optimization suggestions."""
        suggestions = []
        
        for cache_type, profile in self._performance_profiles.items():
            # Low hit rate suggestion
            if profile.hit_rate < 0.5:
                suggestions.append(CacheOptimizationSuggestion(
                    cache_type=cache_type,
                    suggestion_type="add_warming",
                    description=f"Hit rate is low ({profile.hit_rate:.1%}). Consider adding cache warming.",
                    expected_improvement=0.2,
                    implementation_complexity="medium",
                    priority=3
                ))
            
            # High eviction rate suggestion
            if profile.eviction_rate > 0.3:
                suggestions.append(CacheOptimizationSuggestion(
                    cache_type=cache_type,
                    suggestion_type="increase_ttl",
                    description=f"High eviction rate ({profile.eviction_rate:.1%}). Consider increasing TTL.",
                    expected_improvement=0.15,
                    implementation_complexity="low",
                    priority=2
                ))
            
            # Slow response time suggestion
            if profile.average_response_time > 0.5:
                suggestions.append(CacheOptimizationSuggestion(
                    cache_type=cache_type,
                    suggestion_type="optimize_calculation",
                    description=f"Slow response time ({profile.average_response_time:.2f}s). Optimize calculations.",
                    expected_improvement=0.3,
                    implementation_complexity="high",
                    priority=1
                ))
        
        # Sort by priority
        suggestions.sort(key=lambda x: x.priority, reverse=True)
        
        self._optimization_history.extend(suggestions)
        logger.info(f"Generated {len(suggestions)} optimization suggestions")
        
        return suggestions
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report."""
        total_requests = self._usage_stats['total_requests']
        overall_hit_rate = 0.0
        if total_requests > 0:
            overall_hit_rate = self._usage_stats['cache_hits'] / total_requests
        
        return {
            'overview': {
                'total_requests': total_requests,
                'overall_hit_rate': overall_hit_rate,
                'warming_tasks_completed': self._usage_stats['warming_tasks_completed'],
                'optimization_actions': self._usage_stats['optimization_actions_taken'],
                'uptime': datetime.now() - self._usage_stats['last_maintenance']
            },
            'cache_profiles': {
                cache_type.value: {
                    'hit_rate': profile.hit_rate,
                    'response_time': profile.average_response_time,
                    'cache_size': profile.cache_size,
                    'eviction_rate': profile.eviction_rate,
                    'warming_efficiency': profile.warming_efficiency,
                    'total_requests': profile.total_requests
                }
                for cache_type, profile in self._performance_profiles.items()
            },
            'cache_stats': {
                name: cache.get_stats()
                for name, cache in self._cache_registry.items()
            },
            'recent_optimizations': self._optimization_history[-10:],  # Last 10
            'access_patterns': self._get_access_pattern_summary()
        }
    
    def cleanup_old_data(self, max_age_hours: int = 24) -> Dict[str, int]:
        """Clean up old cache data and tracking information."""
        cleanup_results = {}
        
        # Clean up access patterns
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        old_patterns = []
        
        for key, pattern in self._access_patterns.items():
            if pattern.get('last_access', datetime.min) < cutoff_time:
                old_patterns.append(key)
        
        for key in old_patterns:
            del self._access_patterns[key]
        
        cleanup_results['access_patterns_removed'] = len(old_patterns)
        
        # Clean up optimization history
        old_optimizations = [
            opt for opt in self._optimization_history
            if datetime.now() - timedelta(hours=max_age_hours) > datetime.now()
        ]
        self._optimization_history = [
            opt for opt in self._optimization_history
            if opt not in old_optimizations
        ]
        
        cleanup_results['old_optimizations_removed'] = len(old_optimizations)
        
        logger.info(f"Cleaned up {sum(cleanup_results.values())} old cache management items")
        return cleanup_results
    
    def _start_warming_thread(self) -> None:
        """Start the background cache warming thread."""
        if self._warming_thread and self._warming_thread.is_alive():
            return
        
        self._shutdown_warming.clear()
        self._warming_thread = threading.Thread(target=self._warming_worker, daemon=True)
        self._warming_thread.start()
        logger.info("Started cache warming background thread")
    
    def _warming_worker(self) -> None:
        """Background worker for cache warming tasks."""
        while not self._shutdown_warming.wait(timeout=60):  # Check every minute
            try:
                self._process_warming_queue()
            except Exception as e:
                logger.error(f"Error in warming worker: {e}")
    
    def _process_warming_queue(self) -> None:
        """Process pending warming tasks."""
        tasks_to_process = []
        
        with self._warming_lock:
            # Get tasks to process (up to max_warming_workers)
            while len(tasks_to_process) < self.max_warming_workers and self._warming_queue:
                task = self._warming_queue.pop(0)
                task_key = self._generate_task_key(task.key_parts)
                
                if task_key not in self._warming_in_progress:
                    tasks_to_process.append(task)
                    self._warming_in_progress.add(task_key)
        
        # Process tasks
        for task in tasks_to_process:
            try:
                self._execute_warming_task(task)
            finally:
                task_key = self._generate_task_key(task.key_parts)
                with self._warming_lock:
                    self._warming_in_progress.discard(task_key)
    
    def _execute_warming_task(self, task: CacheWarmingTask) -> None:
        """Execute a single warming task."""
        try:
            start_time = time.time()
            
            # Check if already cached and not expired
            cache_key = self.primary_cache._generate_cache_key(task.key_parts)
            if cache_key in self.primary_cache._cache:
                entry = self.primary_cache._cache[cache_key]
                if not entry.is_expired():
                    return  # Already cached
            
            # Calculate and cache
            result = task.calculator()
            if result is not None:
                self.primary_cache.set(task.key_parts, result, task.ttl, task.dependencies)
                
                execution_time = time.time() - start_time
                self._usage_stats['warming_tasks_completed'] += 1
                
                logger.debug(f"Warming task completed in {execution_time:.2f}s: {task.cache_type}")
            
        except Exception as e:
            logger.error(f"Failed to execute warming task for {task.cache_type}: {e}")
    
    def _record_access_pattern(self, cache_type: CacheType, key_parts: List[Any]) -> None:
        """Record access pattern for analytics."""
        pattern_key = f"{cache_type}:{hash(tuple(key_parts))}"
        current_time = datetime.now()
        
        if pattern_key in self._access_patterns:
            pattern = self._access_patterns[pattern_key]
            pattern['access_count'] += 1
            pattern['last_access'] = current_time
        else:
            self._access_patterns[pattern_key] = {
                'cache_type': cache_type,
                'key_parts': key_parts,
                'access_count': 1,
                'first_access': current_time,
                'last_access': current_time
            }
        
        self._usage_stats['total_requests'] += 1
    
    def _update_performance_metrics(self, cache_type: CacheType, cache_hit: bool, response_time: float) -> None:
        """Update performance metrics for a cache operation."""
        if cache_hit:
            self._usage_stats['cache_hits'] += 1
        else:
            self._usage_stats['cache_misses'] += 1
        
        # Update cache type specific metrics
        if cache_type not in self._performance_profiles:
            self._performance_profiles[cache_type] = CachePerformanceProfile(
                cache_type=cache_type,
                hit_rate=0.0,
                average_response_time=0.0,
                cache_size=0,
                eviction_rate=0.0,
                warming_efficiency=0.0,
                total_requests=0
            )
        
        profile = self._performance_profiles[cache_type]
        profile.total_requests += 1
        
        # Update hit rate
        if cache_hit:
            hits = profile.hit_rate * (profile.total_requests - 1) + 1
        else:
            hits = profile.hit_rate * (profile.total_requests - 1)
        profile.hit_rate = hits / profile.total_requests
        
        # Update response time (moving average)
        profile.average_response_time = (
            profile.average_response_time * (profile.total_requests - 1) + response_time
        ) / profile.total_requests
        
        profile.last_updated = datetime.now()
    
    async def _schedule_related_warming(
        self,
        cache_type: CacheType,
        key_parts: List[Any],
        calculator: Optional[Callable],
        ttl: Optional[float],
        dependencies: Optional[List[str]]
    ) -> None:
        """Schedule warming of related cache entries."""
        if self.warming_strategy == CacheStrategy.CONSERVATIVE or not calculator:
            return
        
        # Generate related warming tasks based on cache type and current data
        related_tasks = self._generate_related_warming_tasks(cache_type, key_parts, calculator, ttl, dependencies)
        
        for task in related_tasks:
            self.add_warming_task(**task)
    
    async def _schedule_popular_warming(
        self,
        cache_type: CacheType,
        batch_requests: List[Dict[str, Any]]
    ) -> None:
        """Schedule warming for popular data patterns."""
        if self.warming_strategy == CacheStrategy.CONSERVATIVE:
            return
        
        # Identify popular patterns from batch requests
        popular_patterns = self._identify_popular_patterns_from_batch(batch_requests)
        
        for pattern in popular_patterns:
            if pattern.get('calculator'):
                self.add_warming_task(
                    cache_type=cache_type,
                    key_parts=pattern['key_parts'],
                    calculator=pattern['calculator'],
                    priority=pattern.get('priority', 1),
                    ttl=pattern.get('ttl', 300.0),
                    dependencies=pattern.get('dependencies', [])
                )
    
    def _generate_related_warming_tasks(
        self,
        cache_type: CacheType,
        key_parts: List[Any],
        calculator: Optional[Callable],
        ttl: Optional[float],
        dependencies: Optional[List[str]]
    ) -> List[Dict[str, Any]]:
        """Generate related warming tasks based on access patterns."""
        tasks = []
        
        # This is a simplified implementation
        # In practice, you'd analyze access patterns to predict related data
        
        if cache_type == CacheType.PLAYER_STATISTICS:
            # For player stats, might warm leaderboard data
            tasks.append({
                'cache_type': CacheType.LEADERBOARDS,
                'key_parts': ['leaderboard', 'elo_rating', 5, 100],
                'calculator': lambda: None,  # Would be actual calculator
                'priority': 1,
                'ttl': ttl or 300.0,
                'dependencies': ['leaderboard']
            })
        
        return tasks
    
    def _identify_popular_patterns(self, top_n: int) -> List[Dict[str, Any]]:
        """Identify the most popular access patterns."""
        # Sort patterns by access count
        sorted_patterns = sorted(
            self._access_patterns.items(),
            key=lambda x: x[1]['access_count'],
            reverse=True
        )
        
        popular = []
        for _, pattern in sorted_patterns[:top_n]:
            if 'calculator' in pattern:  # Only include patterns with calculators
                popular.append({
                    'key_parts': pattern['key_parts'],
                    'calculator': pattern['calculator'],
                    'access_frequency': pattern['access_count']
                })
        
        return popular
    
    def _identify_popular_patterns_from_batch(self, batch_requests: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify popular patterns from batch requests."""
        # Simplified implementation
        return batch_requests[:5]  # Just take first 5 as "popular"
    
    def _generate_task_key(self, key_parts: List[Any]) -> str:
        """Generate a unique key for a warming task."""
        return json.dumps(key_parts, sort_keys=True, default=str)
    
    def _get_access_pattern_summary(self) -> Dict[str, Any]:
        """Get summary of access patterns."""
        total_accesses = sum(pattern['access_count'] for pattern in self._access_patterns.values())
        
        cache_type_stats = {}
        for pattern in self._access_patterns.values():
            cache_type = pattern['cache_type']
            if cache_type not in cache_type_stats:
                cache_type_stats[cache_type] = {'accesses': 0, 'unique_keys': 0}
            cache_type_stats[cache_type]['accesses'] += pattern['access_count']
            cache_type_stats[cache_type]['unique_keys'] += 1
        
        return {
            'total_accesses': total_accesses,
            'unique_patterns': len(self._access_patterns),
            'by_cache_type': cache_type_stats
        }
    
    def shutdown(self) -> None:
        """Shutdown the cache manager."""
        logger.info("Shutting down CacheManager")
        
        if self._warming_thread:
            self._shutdown_warming.set()
            self._warming_thread.join(timeout=5)
        
        # Final cleanup
        self.cleanup_old_data(max_age_hours=0)  # Clean everything


# Global cache manager instance
_global_cache_manager: Optional[CacheManager] = None


def get_cache_manager() -> CacheManager:
    """Get the global cache manager instance."""
    global _global_cache_manager
    if _global_cache_manager is None:
        _global_cache_manager = CacheManager()
    return _global_cache_manager