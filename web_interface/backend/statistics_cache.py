"""
Statistics caching system with TTL-based invalidation and intelligent cache management.
"""

import time
import threading
from typing import Dict, Any, Optional, List, Callable, TypeVar, Generic
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import hashlib
import json
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')

@dataclass
class CacheEntry(Generic[T]):
    """Represents a cached statistics entry with metadata."""
    data: T
    timestamp: float
    ttl: float
    access_count: int = 0
    last_accessed: float = field(default_factory=time.time)
    cache_key: str = ""
    dependencies: List[str] = field(default_factory=list)

    def is_expired(self) -> bool:
        """Check if the cache entry has expired."""
        return time.time() - self.timestamp > self.ttl

    def is_stale(self, staleness_threshold: float = 0.8) -> bool:
        """Check if the cache entry is approaching expiration."""
        age = time.time() - self.timestamp
        return age > (self.ttl * staleness_threshold)

    def touch(self) -> None:
        """Update access metadata."""
        self.access_count += 1
        self.last_accessed = time.time()


class StatisticsCache:
    """
    High-performance statistics cache with TTL-based invalidation,
    intelligent prefetching, and dependency tracking.
    """

    def __init__(
        self,
        default_ttl: float = 300.0,  # 5 minutes
        max_cache_size: int = 1000,
        cleanup_interval: float = 60.0,  # 1 minute
        staleness_threshold: float = 0.8
    ):
        self.default_ttl = default_ttl
        self.max_cache_size = max_cache_size
        self.cleanup_interval = cleanup_interval
        self.staleness_threshold = staleness_threshold
        
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = threading.RLock()
        self._last_cleanup = time.time()
        
        # Statistics tracking
        self._stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'invalidations': 0,
            'background_refreshes': 0
        }
        
        # Dependency tracking for intelligent invalidation
        self._dependencies: Dict[str, List[str]] = {}
        
        # Background refresh callbacks
        self._refresh_callbacks: Dict[str, Callable] = {}
        
        # Batch operations and cache warming
        self._warming_queue: List[Dict[str, Any]] = []
        self._warming_in_progress: bool = False
        self._warming_lock = threading.Lock()
        
        # Cache partitioning by data type
        self._partitions: Dict[str, Dict[str, CacheEntry]] = {
            'player_stats': {},
            'leaderboards': {},
            'aggregates': {},
            'time_series': {}
        }

    def _generate_cache_key(self, key_parts: List[Any]) -> str:
        """Generate a consistent cache key from multiple parts."""
        key_string = json.dumps(key_parts, sort_keys=True, default=str)
        return hashlib.md5(key_string.encode()).hexdigest()

    def _should_cleanup(self) -> bool:
        """Check if cache cleanup should be performed."""
        return time.time() - self._last_cleanup > self.cleanup_interval

    def _cleanup_expired_entries(self) -> int:
        """Remove expired entries and return count of removed entries."""
        removed_count = 0
        current_time = time.time()
        
        expired_keys = [
            key for key, entry in self._cache.items()
            if current_time - entry.timestamp > entry.ttl
        ]
        
        for key in expired_keys:
            del self._cache[key]
            removed_count += 1
            
        self._last_cleanup = current_time
        return removed_count

    def _evict_lru_entries(self, target_size: int) -> int:
        """Evict least recently used entries to reach target size."""
        if len(self._cache) <= target_size:
            return 0
            
        # Sort by last accessed time (oldest first)
        sorted_entries = sorted(
            self._cache.items(),
            key=lambda x: x[1].last_accessed
        )
        
        evicted_count = 0
        entries_to_remove = len(self._cache) - target_size
        
        for key, _ in sorted_entries[:entries_to_remove]:
            del self._cache[key]
            evicted_count += 1
            
        self._stats['evictions'] += evicted_count
        return evicted_count

    def get(
        self,
        key_parts: List[Any],
        calculator: Optional[Callable] = None,
        ttl: Optional[float] = None,
        dependencies: Optional[List[str]] = None
    ) -> Optional[Any]:
        """
        Get cached statistics or calculate if not available/expired.
        
        Args:
            key_parts: List of components to create cache key
            calculator: Function to calculate value if not cached
            ttl: Time to live for this entry (uses default if None)
            dependencies: List of dependency keys for invalidation
            
        Returns:
            Cached or calculated statistics data
        """
        cache_key = self._generate_cache_key(key_parts)
        
        with self._lock:
            # Periodic cleanup
            if self._should_cleanup():
                self._cleanup_expired_entries()
            
            # Check if we have a valid cached entry
            if cache_key in self._cache:
                entry = self._cache[cache_key]
                
                if not entry.is_expired():
                    entry.touch()
                    self._stats['hits'] += 1
                    
                    # Schedule background refresh if stale
                    if entry.is_stale(self.staleness_threshold) and calculator:
                        self._schedule_background_refresh(cache_key, calculator, ttl, dependencies)
                    
                    return entry.data
                else:
                    # Remove expired entry
                    del self._cache[cache_key]
            
            # Cache miss - calculate if calculator provided
            if calculator is None:
                self._stats['misses'] += 1
                return None
            
            # Calculate new value
            try:
                calculated_value = calculator()
                self.set(key_parts, calculated_value, ttl, dependencies)
                self._stats['misses'] += 1
                return calculated_value
            except Exception as e:
                logger.error(f"Error calculating statistics for key {cache_key}: {e}")
                self._stats['misses'] += 1
                return None

    def set(
        self,
        key_parts: List[Any],
        value: Any,
        ttl: Optional[float] = None,
        dependencies: Optional[List[str]] = None
    ) -> None:
        """
        Set a value in the cache with optional TTL and dependencies.
        
        Args:
            key_parts: List of components to create cache key
            value: Value to cache
            ttl: Time to live (uses default if None)
            dependencies: List of dependency keys for invalidation
        """
        cache_key = self._generate_cache_key(key_parts)
        effective_ttl = ttl or self.default_ttl
        
        with self._lock:
            # Ensure we don't exceed max cache size
            if len(self._cache) >= self.max_cache_size:
                self._evict_lru_entries(self.max_cache_size - 1)
            
            # Create cache entry
            entry = CacheEntry(
                data=value,
                timestamp=time.time(),
                ttl=effective_ttl,
                cache_key=cache_key,
                dependencies=dependencies or []
            )
            
            self._cache[cache_key] = entry
            
            # Update dependency tracking
            if dependencies:
                for dep in dependencies:
                    if dep not in self._dependencies:
                        self._dependencies[dep] = []
                    if cache_key not in self._dependencies[dep]:
                        self._dependencies[dep].append(cache_key)

    def invalidate(self, dependency_key: str) -> int:
        """
        Invalidate all cache entries that depend on the given key.
        
        Args:
            dependency_key: The dependency key to invalidate
            
        Returns:
            Number of entries invalidated
        """
        with self._lock:
            invalidated_count = 0
            
            if dependency_key in self._dependencies:
                cache_keys_to_invalidate = self._dependencies[dependency_key].copy()
                
                for cache_key in cache_keys_to_invalidate:
                    if cache_key in self._cache:
                        del self._cache[cache_key]
                        invalidated_count += 1
                
                # Clear dependency tracking for this key
                del self._dependencies[dependency_key]
                
                self._stats['invalidations'] += invalidated_count
                logger.info(f"Invalidated {invalidated_count} cache entries for dependency: {dependency_key}")
            
            return invalidated_count

    def invalidate_pattern(self, pattern: str) -> int:
        """
        Invalidate cache entries matching a pattern.
        
        Args:
            pattern: Pattern to match against cache keys
            
        Returns:
            Number of entries invalidated
        """
        with self._lock:
            invalidated_count = 0
            keys_to_remove = []
            
            for cache_key in self._cache.keys():
                if pattern in cache_key:
                    keys_to_remove.append(cache_key)
            
            for key in keys_to_remove:
                del self._cache[key]
                invalidated_count += 1
            
            self._stats['invalidations'] += invalidated_count
            return invalidated_count

    def _schedule_background_refresh(
        self,
        cache_key: str,
        calculator: Callable,
        ttl: Optional[float],
        dependencies: Optional[List[str]]
    ) -> None:
        """Schedule background refresh of stale cache entry."""
        def refresh_task():
            try:
                new_value = calculator()
                # Extract key_parts from cache_key (this is a simplified approach)
                # In practice, you might want to store key_parts in the cache entry
                key_parts = [cache_key]  # Simplified
                self.set(key_parts, new_value, ttl, dependencies)
                self._stats['background_refreshes'] += 1
                logger.debug(f"Background refresh completed for key: {cache_key}")
            except Exception as e:
                logger.error(f"Background refresh failed for key {cache_key}: {e}")
        
        # In a real implementation, you'd use a proper task queue
        # For now, we'll use threading (not recommended for production)
        threading.Thread(target=refresh_task, daemon=True).start()

    def get_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics."""
        with self._lock:
            total_requests = self._stats['hits'] + self._stats['misses']
            hit_rate = self._stats['hits'] / total_requests if total_requests > 0 else 0
            
            return {
                'cache_size': len(self._cache),
                'max_cache_size': self.max_cache_size,
                'hit_rate': hit_rate,
                'total_requests': total_requests,
                **self._stats,
                'dependency_count': len(self._dependencies)
            }

    def clear(self) -> None:
        """Clear all cache entries."""
        with self._lock:
            self._cache.clear()
            self._dependencies.clear()
            logger.info("Cache cleared")

    def get_cache_info(self) -> Dict[str, Any]:
        """Get detailed cache information for debugging."""
        with self._lock:
            entries_info = []
            for key, entry in self._cache.items():
                entries_info.append({
                    'key': key,
                    'age': time.time() - entry.timestamp,
                    'ttl': entry.ttl,
                    'access_count': entry.access_count,
                    'is_expired': entry.is_expired(),
                    'is_stale': entry.is_stale(self.staleness_threshold),
                    'dependencies': entry.dependencies
                })
            
            return {
                'entries': entries_info,
                'stats': self.get_stats(),
                'dependencies': dict(self._dependencies)
            }
    
    def batch_get(self, batch_requests: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Batch get operation for multiple cache keys.
        
        Args:
            batch_requests: List of dicts with keys: 'key_parts', 'calculator', 'ttl', 'dependencies'
            
        Returns:
            Dict mapping request index to cached/calculated values
        """
        results = {}
        missing_requests = []
        
        # First pass: check for cached values
        for i, request in enumerate(batch_requests):
            key_parts = request['key_parts']
            cache_key = self._generate_cache_key(key_parts)
            
            with self._lock:
                if cache_key in self._cache:
                    entry = self._cache[cache_key]
                    if not entry.is_expired():
                        entry.touch()
                        self._stats['hits'] += 1
                        results[i] = entry.data
                        continue
                    else:
                        del self._cache[cache_key]
                
                self._stats['misses'] += 1
                missing_requests.append((i, request))
        
        # Second pass: calculate missing values
        for i, request in missing_requests:
            calculator = request.get('calculator')
            if calculator:
                try:
                    calculated_value = calculator()
                    self.set(
                        request['key_parts'],
                        calculated_value,
                        request.get('ttl'),
                        request.get('dependencies')
                    )
                    results[i] = calculated_value
                except Exception as e:
                    logger.error(f"Error in batch calculation for request {i}: {e}")
                    results[i] = None
            else:
                results[i] = None
        
        return results
    
    def batch_set(self, batch_data: List[Dict[str, Any]]) -> int:
        """
        Batch set operation for multiple cache entries.
        
        Args:
            batch_data: List of dicts with keys: 'key_parts', 'value', 'ttl', 'dependencies'
            
        Returns:
            Number of entries successfully set
        """
        success_count = 0
        
        for data in batch_data:
            try:
                self.set(
                    data['key_parts'],
                    data['value'],
                    data.get('ttl'),
                    data.get('dependencies')
                )
                success_count += 1
            except Exception as e:
                logger.error(f"Error in batch set for key {data['key_parts']}: {e}")
        
        return success_count
    
    def batch_invalidate(self, dependency_patterns: List[str]) -> int:
        """
        Batch invalidation for multiple dependency patterns.
        
        Args:
            dependency_patterns: List of dependency patterns to invalidate
            
        Returns:
            Total number of entries invalidated
        """
        total_invalidated = 0
        
        for pattern in dependency_patterns:
            total_invalidated += self.invalidate(pattern)
        
        return total_invalidated
    
    def warm_cache(self, warming_requests: List[Dict[str, Any]]) -> None:
        """
        Warm cache with frequently accessed data.
        
        Args:
            warming_requests: List of requests to warm cache with
        """
        with self._warming_lock:
            if self._warming_in_progress:
                # Add to queue if warming is in progress
                self._warming_queue.extend(warming_requests)
                return
            
            self._warming_in_progress = True
        
        def warming_worker():
            try:
                # Process current requests
                for request in warming_requests:
                    try:
                        calculator = request.get('calculator')
                        if calculator:
                            key_parts = request['key_parts']
                            cache_key = self._generate_cache_key(key_parts)
                            
                            # Only warm if not already cached
                            with self._lock:
                                if cache_key not in self._cache or self._cache[cache_key].is_expired():
                                    calculated_value = calculator()
                                    self.set(
                                        key_parts,
                                        calculated_value,
                                        request.get('ttl'),
                                        request.get('dependencies')
                                    )
                                    logger.debug(f"Cache warmed for key: {cache_key}")
                    except Exception as e:
                        logger.error(f"Error warming cache for {request.get('key_parts', 'unknown')}: {e}")
                
                # Process queued requests
                with self._warming_lock:
                    while self._warming_queue:
                        queued_requests = self._warming_queue.copy()
                        self._warming_queue.clear()
                        
                        for request in queued_requests:
                            try:
                                calculator = request.get('calculator')
                                if calculator:
                                    calculated_value = calculator()
                                    self.set(
                                        request['key_parts'],
                                        calculated_value,
                                        request.get('ttl'),
                                        request.get('dependencies')
                                    )
                            except Exception as e:
                                logger.error(f"Error in queued cache warming: {e}")
            
            finally:
                with self._warming_lock:
                    self._warming_in_progress = False
        
        # Start background warming
        threading.Thread(target=warming_worker, daemon=True).start()
    
    def get_partition_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for each cache partition."""
        partition_stats = {}
        
        for partition_name, partition_cache in self._partitions.items():
            partition_stats[partition_name] = {
                'size': len(partition_cache),
                'entries': list(partition_cache.keys())
            }
        
        return partition_stats
    
    def preload_popular_data(self, popular_keys: List[Dict[str, Any]]) -> None:
        """
        Preload frequently accessed data based on usage patterns.
        
        Args:
            popular_keys: List of popular key requests to preload
        """
        logger.info(f"Preloading {len(popular_keys)} popular cache entries")
        
        # Sort by expected access frequency (if provided)
        sorted_keys = sorted(
            popular_keys,
            key=lambda x: x.get('access_frequency', 0),
            reverse=True
        )
        
        # Warm cache with popular data
        self.warm_cache(sorted_keys)


# Global cache instance
_global_cache: Optional[StatisticsCache] = None


def get_statistics_cache() -> StatisticsCache:
    """Get the global statistics cache instance."""
    global _global_cache
    if _global_cache is None:
        _global_cache = StatisticsCache()
    return _global_cache


def invalidate_player_cache(player_id: str) -> int:
    """Convenience function to invalidate all cache entries for a player."""
    cache = get_statistics_cache()
    return cache.invalidate(f"player:{player_id}")


def invalidate_game_cache(game_id: str) -> int:
    """Convenience function to invalidate cache entries related to a game."""
    cache = get_statistics_cache()
    return cache.invalidate(f"game:{game_id}")


def invalidate_leaderboard_cache() -> int:
    """Convenience function to invalidate leaderboard cache entries."""
    cache = get_statistics_cache()
    return cache.invalidate("leaderboard")