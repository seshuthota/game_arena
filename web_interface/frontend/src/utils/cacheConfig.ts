import { QueryClient, UseQueryOptions } from '@tanstack/react-query';

// Cache duration constants (in milliseconds)
export const CACHE_DURATIONS = {
  // Fast-changing data
  GAME_LIST: 2 * 60 * 1000, // 2 minutes
  LEADERBOARD: 3 * 60 * 1000, // 3 minutes
  STATISTICS_OVERVIEW: 3 * 60 * 1000, // 3 minutes
  
  // Moderately changing data
  GAME_DETAILS: 10 * 60 * 1000, // 10 minutes (completed games rarely change)
  PLAYER_STATS: 5 * 60 * 1000, // 5 minutes
  TIME_SERIES: 5 * 60 * 1000, // 5 minutes
  
  // Slow-changing data
  USER_PROFILE: 15 * 60 * 1000, // 15 minutes
  APP_CONFIG: 30 * 60 * 1000, // 30 minutes
  
  // Garbage collection times (how long to keep in memory)
  GC_SHORT: 5 * 60 * 1000, // 5 minutes
  GC_MEDIUM: 15 * 60 * 1000, // 15 minutes
  GC_LONG: 30 * 60 * 1000, // 30 minutes
  GC_EXTENDED: 60 * 60 * 1000, // 1 hour
} as const;

// Auto-refresh intervals for background updates
export const REFRESH_INTERVALS = {
  LIVE_STATS: 30 * 1000, // 30 seconds for live stats
  LEADERBOARD: 5 * 60 * 1000, // 5 minutes for leaderboard
  GAME_LIST: 2 * 60 * 1000, // 2 minutes for game list
  DISABLED: false, // No auto-refresh
} as const;

// Network-aware caching strategies
export const getNetworkAwareCacheConfig = () => {
  // Detect connection speed (if available)
  const connection = (navigator as any).connection || (navigator as any).mozConnection || (navigator as any).webkitConnection;
  const isSlowConnection = connection && (
    connection.effectiveType === 'slow-2g' || 
    connection.effectiveType === '2g' ||
    connection.saveData
  );
  
  return {
    isSlowConnection,
    // Adjust cache times for slow connections
    staleTimeMultiplier: isSlowConnection ? 2 : 1,
    gcTimeMultiplier: isSlowConnection ? 3 : 1,
    // Disable background refetching on slow connections
    refetchOnWindowFocus: !isSlowConnection,
    refetchOnReconnect: true,
    // More aggressive retry delays on slow connections
    retryDelay: (attemptIndex: number) => Math.min(1000 * 2 ** attemptIndex * (isSlowConnection ? 2 : 1), 30000),
  };
};

// Priority-based caching configurations
export const createCacheConfig = (
  priority: 'critical' | 'high' | 'medium' | 'low' = 'medium'
): Partial<UseQueryOptions> => {
  const networkConfig = getNetworkAwareCacheConfig();
  
  const configs = {
    critical: {
      staleTime: CACHE_DURATIONS.GAME_LIST * networkConfig.staleTimeMultiplier,
      gcTime: CACHE_DURATIONS.GC_SHORT * networkConfig.gcTimeMultiplier,
      refetchInterval: REFRESH_INTERVALS.LIVE_STATS,
      refetchIntervalInBackground: false,
      refetchOnWindowFocus: networkConfig.refetchOnWindowFocus,
      refetchOnReconnect: networkConfig.refetchOnReconnect,
      retry: 3,
      retryDelay: networkConfig.retryDelay,
    },
    high: {
      staleTime: CACHE_DURATIONS.STATISTICS_OVERVIEW * networkConfig.staleTimeMultiplier,
      gcTime: CACHE_DURATIONS.GC_MEDIUM * networkConfig.gcTimeMultiplier,
      refetchInterval: REFRESH_INTERVALS.LEADERBOARD,
      refetchIntervalInBackground: false,
      refetchOnWindowFocus: networkConfig.refetchOnWindowFocus,
      refetchOnReconnect: networkConfig.refetchOnReconnect,
      retry: 2,
      retryDelay: networkConfig.retryDelay,
    },
    medium: {
      staleTime: CACHE_DURATIONS.GAME_DETAILS * networkConfig.staleTimeMultiplier,
      gcTime: CACHE_DURATIONS.GC_LONG * networkConfig.gcTimeMultiplier,
      refetchInterval: REFRESH_INTERVALS.DISABLED,
      refetchOnWindowFocus: networkConfig.refetchOnWindowFocus,
      refetchOnReconnect: networkConfig.refetchOnReconnect,
      retry: 1,
      retryDelay: networkConfig.retryDelay,
    },
    low: {
      staleTime: CACHE_DURATIONS.USER_PROFILE * networkConfig.staleTimeMultiplier,
      gcTime: CACHE_DURATIONS.GC_EXTENDED * networkConfig.gcTimeMultiplier,
      refetchInterval: REFRESH_INTERVALS.DISABLED,
      refetchOnWindowFocus: false,
      refetchOnReconnect: networkConfig.refetchOnReconnect,
      retry: 1,
      retryDelay: networkConfig.retryDelay,
    },
  };
  
  return configs[priority];
};

// Smart prefetching utilities
export const createPrefetchStrategies = (queryClient: QueryClient) => {
  return {
    // Prefetch next page of games when user scrolls to 80% of current page
    prefetchNextGames: async (currentParams: any) => {
      const nextPageParams = { ...currentParams, page: (currentParams.page || 1) + 1 };
      await queryClient.prefetchQuery({
        queryKey: ['games', nextPageParams],
        // Use a shorter stale time for prefetched data
        staleTime: CACHE_DURATIONS.GAME_LIST / 2,
      });
    },
    
    // Prefetch game details on hover
    prefetchGameOnHover: async (gameId: string) => {
      await queryClient.prefetchQuery({
        queryKey: ['games', gameId],
        staleTime: CACHE_DURATIONS.GAME_DETAILS,
      });
    },
    
    // Prefetch related statistics when viewing a game
    prefetchRelatedStats: async (gameId: string) => {
      // Prefetch player stats for both players
      const gameData = queryClient.getQueryData(['games', gameId]) as any;
      if (gameData?.game) {
        const { white_player, black_player } = gameData.game;
        if (white_player?.id) {
          queryClient.prefetchQuery({
            queryKey: ['players', white_player.id, 'statistics'],
            staleTime: CACHE_DURATIONS.PLAYER_STATS,
          });
        }
        if (black_player?.id) {
          queryClient.prefetchQuery({
            queryKey: ['players', black_player.id, 'statistics'],
            staleTime: CACHE_DURATIONS.PLAYER_STATS,
          });
        }
      }
    },
    
    // Batch prefetch for visible items
    batchPrefetch: async (items: any[], type: 'games' | 'players') => {
      const promises = items.slice(0, 10).map((item) => { // Limit to first 10 items
        const queryKey = type === 'games' ? ['games', item.id] : ['players', item.id, 'statistics'];
        return queryClient.prefetchQuery({
          queryKey,
          staleTime: type === 'games' ? CACHE_DURATIONS.GAME_DETAILS : CACHE_DURATIONS.PLAYER_STATS,
        });
      });
      
      await Promise.allSettled(promises);
    },
  };
};

// Cache invalidation strategies
export const createInvalidationStrategies = (queryClient: QueryClient) => {
  return {
    // Invalidate all game-related caches when a new game is added
    invalidateGameCaches: () => {
      queryClient.invalidateQueries({ queryKey: ['games'] });
      queryClient.invalidateQueries({ queryKey: ['statistics'] });
      queryClient.invalidateQueries({ queryKey: ['leaderboard'] });
      queryClient.invalidateQueries({ queryKey: ['players'] });
    },
    
    // Selective invalidation for specific player
    invalidatePlayerCaches: (playerId: string) => {
      queryClient.invalidateQueries({ queryKey: ['players', playerId] });
      queryClient.invalidateQueries({ queryKey: ['leaderboard'] });
      // Also invalidate games that include this player
      queryClient.invalidateQueries({ 
        queryKey: ['games'], 
        predicate: (query) => {
          const data = query.state.data as any;
          return data?.games?.some((game: any) => 
            game.white_player?.id === playerId || game.black_player?.id === playerId
          );
        }
      });
    },
    
    // Time-based cache cleanup
    cleanupStaleCaches: () => {
      const now = Date.now();
      const queries = queryClient.getQueryCache().getAll();
      
      queries.forEach((query) => {
        const lastUpdated = query.state.dataUpdatedAt;
        const maxAge = CACHE_DURATIONS.GC_EXTENDED;
        
        if (now - lastUpdated > maxAge) {
          queryClient.removeQueries({ queryKey: query.queryKey });
        }
      });
    },
    
    // Optimistic updates for game completions
    optimisticGameUpdate: (gameId: string, updates: any) => {
      queryClient.setQueryData(['games', gameId], (oldData: any) => {
        if (oldData?.game) {
          return {
            ...oldData,
            game: { ...oldData.game, ...updates }
          };
        }
        return oldData;
      });
      
      // Also update the game in lists
      queryClient.setQueriesData(
        { queryKey: ['games'] },
        (oldData: any) => {
          if (oldData?.games) {
            return {
              ...oldData,
              games: oldData.games.map((game: any) =>
                game.id === gameId ? { ...game, ...updates } : game
              )
            };
          }
          return oldData;
        }
      );
    },
  };
};

// Performance monitoring for cache effectiveness
export const createCachePerformanceMonitor = (queryClient: QueryClient) => {
  return {
    getCacheStats: () => {
      const cache = queryClient.getQueryCache();
      const queries = cache.getAll();
      
      const stats = {
        totalQueries: queries.length,
        activeQueries: queries.filter(q => q.getObserversCount() > 0).length,
        staleQueries: queries.filter(q => q.isStale()).length,
        errorQueries: queries.filter(q => q.state.status === 'error').length,
        memoryUsage: queries.reduce((acc, q) => {
          return acc + (JSON.stringify(q.state.data || '').length || 0);
        }, 0),
        cacheHitRatio: this.calculateHitRatio?.(queries) || 0,
      };
      
      return stats;
    },
    
    calculateHitRatio: (queries: any[]) => {
      let hits = 0;
      let total = 0;
      
      queries.forEach(query => {
        if (query?.state?.data && query?.state?.dataUpdatedAt) {
          total++;
          if (query?.state?.fetchStatus === 'idle') {
            hits++;
          }
        }
      });
      
      return total > 0 ? (hits / total) * 100 : 0;
    },
    
    logCachePerformance: (monitor: any) => {
      if (process.env.NODE_ENV === 'development') {
        const stats = monitor.getCacheStats();
        console.group('🚀 Cache Performance Stats');
        console.table(stats);
        console.groupEnd();
      }
    },
  };
};

// Default query client configuration with optimizations
export const createOptimizedQueryClient = () => {
  const networkConfig = getNetworkAwareCacheConfig();
  
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: CACHE_DURATIONS.GAME_DETAILS,
        gcTime: CACHE_DURATIONS.GC_MEDIUM,
        refetchOnWindowFocus: networkConfig.refetchOnWindowFocus,
        refetchOnReconnect: networkConfig.refetchOnReconnect,
        retry: networkConfig.isSlowConnection ? 1 : 2,
        retryDelay: networkConfig.retryDelay,
        // Enable placeholderData for better UX
        placeholderData: (previousData: any) => previousData,
      },
      mutations: {
        retry: 1,
        retryDelay: networkConfig.retryDelay,
      },
    },
  });
};