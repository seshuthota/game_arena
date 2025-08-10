# Performance Optimization and Caching Strategies

## Overview

The Game Arena performance optimization system implements a multi-layered caching architecture with intelligent warming, real-time monitoring, and automated optimization. This document covers the comprehensive performance strategies, caching mechanisms, and optimization techniques implemented throughout the system.

## Architecture Overview

The performance optimization system consists of several interconnected components:

1. **StatisticsCache**: Core caching layer for player and game statistics
2. **CacheManager**: Coordinated cache management and warming strategies
3. **BatchStatisticsProcessor**: Optimized batch processing for heavy computations
4. **PerformanceMonitor**: Real-time monitoring and alerting system
5. **CachingMiddleware**: HTTP response caching middleware

## Core Caching System

### StatisticsCache

The primary caching layer that handles all statistical data with TTL-based invalidation.

#### Configuration

```python
class CacheConfig:
    DEFAULT_TTL = 600.0          # 10 minutes default TTL
    MAX_CACHE_SIZE = 10000       # Maximum number of cached entries
    CLEANUP_INTERVAL = 300.0     # Cache cleanup every 5 minutes
    HIT_RATIO_TARGET = 0.85      # Target cache hit ratio
    MEMORY_LIMIT_MB = 512        # Memory limit for cache
    
    # Cache warming settings
    WARMING_ENABLED = True
    WARMING_BATCH_SIZE = 50
    WARMING_INTERVAL = 180.0     # Warm cache every 3 minutes
    PRELOAD_THRESHOLD = 0.7      # Preload when TTL < 70%
```

#### Implementation

```python
class StatisticsCache:
    def __init__(self, max_size: int = 10000, default_ttl: float = 600.0):
        """Initialize cache with size and TTL limits."""
        self._cache: Dict[str, CacheEntry] = {}
        self._access_times: Dict[str, datetime] = {}
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._lock = threading.RLock()
        self._stats = CacheStats()
        
    async def get(self, key: str) -> Optional[CacheEntry]:
        """Retrieve item from cache with hit/miss tracking."""
        
    async def set(self, key: str, value: Any, ttl: Optional[float] = None):
        """Store item in cache with automatic cleanup."""
        
    async def invalidate_pattern(self, pattern: str):
        """Invalidate all keys matching pattern."""
        
    async def warm_cache(self, warming_tasks: List[CacheWarmingTask]):
        """Proactively warm cache with high-priority data."""
```

### Cache Strategies

#### 1. Tiered Caching Strategy

```python
class TieredCacheStrategy:
    """Multi-level caching with different TTL values based on data volatility."""
    
    CACHE_TIERS = {
        # Tier 1: Hot data (frequently accessed, short TTL)
        "hot": {
            "ttl": 300,      # 5 minutes
            "size_limit": 1000,
            "priority": 1
        },
        
        # Tier 2: Warm data (moderate access, medium TTL)
        "warm": {
            "ttl": 1800,     # 30 minutes
            "size_limit": 5000,
            "priority": 2
        },
        
        # Tier 3: Cold data (infrequent access, long TTL)
        "cold": {
            "ttl": 7200,     # 2 hours
            "size_limit": 10000,
            "priority": 3
        }
    }
```

#### 2. Intelligent Cache Warming

```python
class CacheWarmingStrategy:
    """Intelligent cache warming based on access patterns and predictions."""
    
    def __init__(self):
        self.access_patterns = defaultdict(list)
        self.warming_queue = PriorityQueue()
        
    def predict_access_needs(self) -> List[CacheWarmingTask]:
        """Predict which data should be preloaded."""
        tasks = []
        
        # Analyze historical access patterns
        for key, accesses in self.access_patterns.items():
            frequency = len(accesses)
            recent_accesses = [a for a in accesses if a > datetime.now() - timedelta(hours=1)]
            
            if frequency > 10 and len(recent_accesses) > 2:
                task = CacheWarmingTask(
                    cache_type=self._infer_cache_type(key),
                    priority=frequency,
                    key_parts=key.split(":"),
                    calculator=self._get_calculator(key),
                    ttl=self._calculate_optimal_ttl(accesses),
                    access_frequency=frequency
                )
                tasks.append(task)
        
        return sorted(tasks, key=lambda x: x.priority, reverse=True)
```

#### 3. Adaptive TTL Calculation

```python
def calculate_adaptive_ttl(key: str, access_history: List[datetime]) -> float:
    """Calculate optimal TTL based on access patterns."""
    if not access_history:
        return DEFAULT_TTL
    
    # Calculate access frequency
    now = datetime.now()
    recent_accesses = [a for a in access_history if a > now - timedelta(hours=24)]
    
    if not recent_accesses:
        return DEFAULT_TTL * 2  # Increase TTL for rarely accessed data
    
    # Calculate average time between accesses
    intervals = []
    for i in range(1, len(recent_accesses)):
        interval = (recent_accesses[i] - recent_accesses[i-1]).total_seconds()
        intervals.append(interval)
    
    if intervals:
        avg_interval = statistics.mean(intervals)
        # Set TTL to 50% of average access interval
        adaptive_ttl = max(MIN_TTL, min(MAX_TTL, avg_interval * 0.5))
        return adaptive_ttl
    
    return DEFAULT_TTL
```

## Batch Processing Optimization

### BatchStatisticsProcessor

Optimizes heavy statistical calculations through intelligent batching and parallel processing.

#### Configuration

```python
class BatchProcessingConfig:
    BATCH_SIZE = 100             # Items per batch
    MAX_CONCURRENT_BATCHES = 4   # Parallel batch limit
    PROCESSING_TIMEOUT = 300.0   # 5 minute timeout per batch
    QUEUE_SIZE_LIMIT = 1000      # Maximum queued requests
    PRIORITY_QUEUE_ENABLED = True
    
    # Performance thresholds
    CPU_USAGE_THRESHOLD = 0.8    # Pause if CPU > 80%
    MEMORY_USAGE_THRESHOLD = 0.9 # Pause if memory > 90%
```

#### Implementation

```python
class BatchStatisticsProcessor:
    def __init__(self, query_engine, statistics_cache):
        self.processing_queue = asyncio.PriorityQueue()
        self.active_batches = {}
        self.performance_monitor = PerformanceMonitor()
        
    async def process_batch_request(self, request: BatchCalculationRequest):
        """Process batch calculation with performance monitoring."""
        batch_id = self._generate_batch_id()
        
        try:
            # Check system resources before processing
            if not self._check_system_resources():
                await self._wait_for_resources()
            
            # Split into optimal batch sizes
            batches = self._optimize_batch_size(request)
            
            # Process batches in parallel
            results = await asyncio.gather(
                *[self._process_single_batch(batch) for batch in batches],
                return_exceptions=True
            )
            
            # Combine results and cache
            combined_result = self._combine_batch_results(results)
            await self._cache_batch_results(combined_result)
            
            return combined_result
            
        except Exception as e:
            logger.error(f"Batch processing failed: {e}")
            raise
        finally:
            self._cleanup_batch(batch_id)
```

#### Intelligent Batch Sizing

```python
def optimize_batch_size(self, request: BatchCalculationRequest) -> List[Dict]:
    """Dynamically optimize batch size based on system performance."""
    base_size = self.config.BATCH_SIZE
    
    # Adjust based on system resources
    cpu_usage = psutil.cpu_percent()
    memory_usage = psutil.virtual_memory().percent
    
    if cpu_usage > 70:
        batch_size = max(10, base_size // 2)  # Reduce batch size under load
    elif cpu_usage < 30:
        batch_size = min(200, base_size * 2)  # Increase batch size when idle
    else:
        batch_size = base_size
    
    # Adjust based on data complexity
    complexity_factor = self._calculate_complexity_factor(request)
    batch_size = int(batch_size / complexity_factor)
    
    return self._split_into_batches(request.items, batch_size)

def _calculate_complexity_factor(self, request: BatchCalculationRequest) -> float:
    """Calculate processing complexity factor."""
    factor = 1.0
    
    if request.include_opening_analysis:
        factor *= 1.5
    if request.include_head_to_head:
        factor *= 2.0
    if request.calculate_trends:
        factor *= 1.3
    
    return factor
```

## Performance Monitoring

### Real-time Metrics Collection

```python
class PerformanceMonitor:
    def __init__(self):
        self.metrics = defaultdict(deque)
        self.alerts = []
        self.thresholds = {
            MetricType.CACHE_HIT_RATE: 0.8,
            MetricType.RESPONSE_TIME: 1000,  # ms
            MetricType.ERROR_RATE: 0.01,     # 1%
            MetricType.MEMORY_USAGE: 0.9,    # 90%
        }
        
    def record_metric(self, metric_type: MetricType, value: float):
        """Record performance metric with automatic alerting."""
        timestamp = datetime.now()
        self.metrics[metric_type].append((timestamp, value))
        
        # Keep only recent metrics (last hour)
        cutoff = timestamp - timedelta(hours=1)
        while (self.metrics[metric_type] and 
               self.metrics[metric_type][0][0] < cutoff):
            self.metrics[metric_type].popleft()
        
        # Check thresholds and generate alerts
        self._check_alert_conditions(metric_type, value)
```

### Performance Optimization Recommendations

```python
class PerformanceOptimizer:
    def __init__(self, monitor: PerformanceMonitor):
        self.monitor = monitor
        
    def generate_recommendations(self) -> List[OptimizationRecommendation]:
        """Generate optimization recommendations based on performance data."""
        recommendations = []
        
        # Analyze cache performance
        hit_rate = self._calculate_average_hit_rate()
        if hit_rate < 0.8:
            recommendations.append(
                OptimizationRecommendation(
                    type="cache_tuning",
                    priority="high",
                    description="Cache hit rate below target (80%)",
                    suggested_actions=[
                        "Increase cache size limit",
                        "Implement more aggressive warming",
                        "Review TTL settings for frequently accessed data"
                    ],
                    expected_improvement="15-25% hit rate increase"
                )
            )
        
        # Analyze response times
        avg_response_time = self._calculate_average_response_time()
        if avg_response_time > 500:  # ms
            recommendations.append(
                OptimizationRecommendation(
                    type="performance_tuning",
                    priority="medium",
                    description=f"Average response time high ({avg_response_time}ms)",
                    suggested_actions=[
                        "Enable more aggressive caching",
                        "Optimize database queries",
                        "Implement connection pooling"
                    ],
                    expected_improvement="30-50% response time reduction"
                )
            )
        
        # Analyze batch processing efficiency
        batch_efficiency = self._calculate_batch_efficiency()
        if batch_efficiency < 0.7:
            recommendations.append(
                OptimizationRecommendation(
                    type="batch_optimization",
                    priority="medium",
                    description="Batch processing efficiency below optimal",
                    suggested_actions=[
                        "Adjust batch sizes based on system load",
                        "Implement parallel processing",
                        "Review batch priority algorithms"
                    ],
                    expected_improvement="20-40% throughput increase"
                )
            )
        
        return recommendations
```

## Frontend Performance Optimizations

### React Component Optimizations

#### 1. ChessBoardComponent Optimization

```typescript
// Memoized chess board component with optimized re-rendering
export const ChessBoardComponent = React.memo<ChessBoardComponentProps>(
  ({ position, orientation, disabled, lastMove, ...props }) => {
    // Position cache for efficient navigation
    const positionCache = useRef(new PositionCache(100));
    
    // Memoized board configuration
    const boardConfig = useMemo(() => ({
      position,
      orientation,
      showNotation: props.showCoordinates,
      draggable: !disabled,
      animationSpeed: props.animationSpeed,
      pieceTheme: 'https://chessboardjs.com/img/chesspieces/wikipedia/{piece}.png',
      onDrop: handleMove,
      onSnapEnd: updatePosition
    }), [position, orientation, disabled, props.showCoordinates, props.animationSpeed]);
    
    // Debounced position updates
    const debouncedPositionUpdate = useMemo(
      () => debounce((newPosition: string) => {
        props.onPositionChange?.(newPosition);
      }, 50),
      [props.onPositionChange]
    );
    
    return (
      <div className="chess-board-container">
        <div ref={boardRef} className="chess-board" />
      </div>
    );
  },
  // Custom comparison function for optimized re-rendering
  (prevProps, nextProps) => {
    return (
      prevProps.position === nextProps.position &&
      prevProps.orientation === nextProps.orientation &&
      prevProps.disabled === nextProps.disabled &&
      prevProps.showCoordinates === nextProps.showCoordinates &&
      isEqual(prevProps.lastMove, nextProps.lastMove)
    );
  }
);
```

#### 2. Virtualized Lists for Large Datasets

```typescript
import { FixedSizeList as List } from 'react-window';

const VirtualizedGameList: React.FC<GameListProps> = ({ games, onGameSelect }) => {
  const ItemRenderer = useCallback(({ index, style }) => {
    const game = games[index];
    
    return (
      <div style={style}>
        <GameCard 
          game={game} 
          onClick={() => onGameSelect(game.id)}
        />
      </div>
    );
  }, [games, onGameSelect]);
  
  return (
    <List
      height={600}
      itemCount={games.length}
      itemSize={120}
      overscanCount={5}
      itemData={games}
    >
      {ItemRenderer}
    </List>
  );
};
```

### Data Fetching Optimizations

#### 1. SWR with Optimistic Updates

```typescript
import useSWR, { mutate } from 'swr';

export function usePlayerStatistics(playerId: string) {
  const { data, error, isLoading } = useSWR(
    playerId ? `/api/v1/players/${playerId}/statistics` : null,
    fetcher,
    {
      revalidateOnFocus: false,
      revalidateOnReconnect: true,
      refreshInterval: 300000, // Refresh every 5 minutes
      dedupingInterval: 60000,  // Dedupe requests within 1 minute
    }
  );
  
  const updateStatistics = useCallback(async (updates: Partial<PlayerStats>) => {
    // Optimistic update
    mutate(
      `/api/v1/players/${playerId}/statistics`,
      { ...data, ...updates },
      false
    );
    
    // Actual API call
    try {
      await updatePlayerStatsAPI(playerId, updates);
      mutate(`/api/v1/players/${playerId}/statistics`);
    } catch (error) {
      // Revert on error
      mutate(`/api/v1/players/${playerId}/statistics`);
      throw error;
    }
  }, [playerId, data]);
  
  return {
    statistics: data,
    isLoading,
    error,
    updateStatistics
  };
}
```

#### 2. Request Batching and Deduplication

```typescript
class RequestBatcher {
  private batches = new Map<string, {
    requests: Array<{ resolve: Function; reject: Function; params: any }>;
    timeoutId: NodeJS.Timeout;
  }>();
  
  async batchRequest<T>(
    batchKey: string,
    request: any,
    batchProcessor: (requests: any[]) => Promise<T[]>,
    delay: number = 100
  ): Promise<T> {
    return new Promise((resolve, reject) => {
      const batch = this.batches.get(batchKey) || {
        requests: [],
        timeoutId: setTimeout(() => this.processBatch(batchKey, batchProcessor), delay)
      };
      
      batch.requests.push({ resolve, reject, params: request });
      this.batches.set(batchKey, batch);
    });
  }
  
  private async processBatch(batchKey: string, processor: Function) {
    const batch = this.batches.get(batchKey);
    if (!batch) return;
    
    this.batches.delete(batchKey);
    
    try {
      const results = await processor(batch.requests.map(r => r.params));
      batch.requests.forEach((req, index) => {
        req.resolve(results[index]);
      });
    } catch (error) {
      batch.requests.forEach(req => req.reject(error));
    }
  }
}

// Usage
const batcher = new RequestBatcher();

export async function getPlayerStatistics(playerId: string) {
  return batcher.batchRequest(
    'player-statistics',
    { playerId },
    async (requests) => {
      const playerIds = requests.map(r => r.playerId);
      const response = await fetch('/api/v1/batch/player-statistics', {
        method: 'POST',
        body: JSON.stringify({ player_ids: playerIds })
      });
      return response.json();
    }
  );
}
```

## Database Optimization

### Query Optimization Strategies

#### 1. Index Strategy

```sql
-- Optimized indexes for common queries
CREATE INDEX idx_games_players ON games USING GIN (players);
CREATE INDEX idx_games_start_time ON games (start_time DESC);
CREATE INDEX idx_games_result ON games (result) WHERE result IS NOT NULL;
CREATE INDEX idx_games_composite ON games (start_time DESC, result) 
  WHERE is_completed = true;

-- Partial indexes for better performance
CREATE INDEX idx_games_ongoing ON games (game_id) 
  WHERE is_completed = false;
CREATE INDEX idx_games_recent ON games (start_time DESC) 
  WHERE start_time > NOW() - INTERVAL '7 days';
```

#### 2. Query Pattern Optimization

```python
class OptimizedQueryEngine:
    def __init__(self):
        self.query_cache = {}
        self.connection_pool = self._create_connection_pool()
    
    async def get_leaderboard_optimized(self, 
                                      page: int, 
                                      limit: int, 
                                      filters: Dict) -> List[Dict]:
        """Optimized leaderboard query with minimal data transfer."""
        
        # Use prepared statements for better performance
        query = """
        SELECT 
            p.player_id,
            p.model_name,
            p.model_provider,
            p.elo_rating,
            p.games_played,
            p.wins,
            p.draws,
            p.losses,
            ROW_NUMBER() OVER (ORDER BY p.elo_rating DESC) as ranking
        FROM player_statistics p
        WHERE ($1::text IS NULL OR p.model_provider = ANY($1::text[]))
          AND ($2::int IS NULL OR p.games_played >= $2)
        ORDER BY p.elo_rating DESC
        LIMIT $3 OFFSET $4
        """
        
        params = [
            filters.get('model_providers'),
            filters.get('min_games'),
            limit,
            (page - 1) * limit
        ]
        
        async with self.connection_pool.acquire() as conn:
            return await conn.fetch(query, *params)
```

## Memory Management

### Memory-Efficient Data Structures

```python
class MemoryEfficientCache:
    """Cache implementation optimized for memory usage."""
    
    def __init__(self, max_memory_mb: int = 512):
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.cache = {}
        self.access_times = {}
        self.memory_usage = 0
        self._lock = threading.RLock()
        
    def _estimate_memory_usage(self, obj: Any) -> int:
        """Estimate memory usage of cached object."""
        if isinstance(obj, str):
            return len(obj.encode('utf-8'))
        elif isinstance(obj, (int, float)):
            return 8  # 64-bit numbers
        elif isinstance(obj, dict):
            return sum(
                self._estimate_memory_usage(k) + self._estimate_memory_usage(v)
                for k, v in obj.items()
            ) + 64  # Dict overhead
        elif isinstance(obj, list):
            return sum(self._estimate_memory_usage(item) for item in obj) + 56
        else:
            # Fallback to sys.getsizeof for complex objects
            return sys.getsizeof(obj)
    
    def set(self, key: str, value: Any, ttl: Optional[float] = None):
        """Set cache value with memory limit enforcement."""
        estimated_size = self._estimate_memory_usage(value)
        
        # Check if adding this item would exceed memory limit
        if self.memory_usage + estimated_size > self.max_memory_bytes:
            self._evict_to_fit(estimated_size)
        
        with self._lock:
            # Remove old entry if exists
            if key in self.cache:
                old_size = self._estimate_memory_usage(self.cache[key])
                self.memory_usage -= old_size
            
            self.cache[key] = value
            self.access_times[key] = time.time()
            self.memory_usage += estimated_size
    
    def _evict_to_fit(self, required_space: int):
        """Evict least recently used items to free memory."""
        target_usage = self.max_memory_bytes - required_space
        
        # Sort by access time (LRU first)
        sorted_keys = sorted(
            self.access_times.keys(),
            key=lambda k: self.access_times[k]
        )
        
        for key in sorted_keys:
            if self.memory_usage <= target_usage:
                break
                
            value_size = self._estimate_memory_usage(self.cache[key])
            del self.cache[key]
            del self.access_times[key]
            self.memory_usage -= value_size
```

## Monitoring and Alerting

### Performance Metrics Dashboard

```python
class PerformanceDashboard:
    def __init__(self, monitor: PerformanceMonitor):
        self.monitor = monitor
        
    def get_dashboard_metrics(self) -> Dict[str, Any]:
        """Generate comprehensive performance dashboard data."""
        return {
            "cache_performance": {
                "hit_rate": self._calculate_hit_rate(),
                "miss_rate": self._calculate_miss_rate(),
                "eviction_rate": self._calculate_eviction_rate(),
                "memory_usage": self._get_memory_usage(),
                "size": self._get_cache_size()
            },
            "system_performance": {
                "avg_response_time_ms": self._calculate_avg_response_time(),
                "p95_response_time_ms": self._calculate_p95_response_time(),
                "throughput_rps": self._calculate_throughput(),
                "error_rate": self._calculate_error_rate()
            },
            "batch_processing": {
                "queue_length": self._get_queue_length(),
                "processing_rate": self._calculate_processing_rate(),
                "avg_batch_time": self._calculate_avg_batch_time(),
                "efficiency": self._calculate_batch_efficiency()
            },
            "resource_utilization": {
                "cpu_usage": psutil.cpu_percent(),
                "memory_usage": psutil.virtual_memory().percent,
                "disk_io": self._get_disk_io_stats(),
                "network_io": self._get_network_io_stats()
            },
            "recommendations": self._get_optimization_recommendations()
        }
```

### Automated Optimization

```python
class AutoOptimizer:
    def __init__(self, cache_manager, performance_monitor):
        self.cache_manager = cache_manager
        self.monitor = performance_monitor
        self.optimization_history = []
        
    async def run_optimization_cycle(self):
        """Run automated optimization based on performance metrics."""
        current_metrics = self.monitor.get_current_metrics()
        
        optimizations = []
        
        # Optimize cache settings
        if current_metrics.cache_hit_rate < 0.8:
            optimizations.append(await self._optimize_cache_settings())
            
        # Optimize batch processing
        if current_metrics.batch_efficiency < 0.7:
            optimizations.append(await self._optimize_batch_settings())
            
        # Optimize TTL values
        if current_metrics.eviction_rate > 0.1:
            optimizations.append(await self._optimize_ttl_values())
        
        # Apply optimizations
        for optimization in optimizations:
            if optimization.expected_improvement > 0.1:  # 10% improvement threshold
                await self._apply_optimization(optimization)
                self.optimization_history.append(optimization)
        
        return optimizations
```

This comprehensive performance optimization system provides intelligent caching, automated tuning, and continuous monitoring to ensure optimal system performance under varying loads and usage patterns.