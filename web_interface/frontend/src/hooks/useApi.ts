import { useQuery, UseQueryOptions } from '@tanstack/react-query';
import { useApiQuery } from './useApiWithRetry';
import { apiService } from '../services/api';
import { createCacheConfig } from '../utils/cacheConfig';
import { 
  ErrorCode, 
  createStandardizedError, 
  mapHttpStatusToErrorCode,
  StandardizedError 
} from '../utils/errorSystem';
import {
  GameListResponse,
  GameDetailResponse,
  StatisticsOverviewResponse,
  TimeSeriesResponse,
  LeaderboardResponse,
  PlayerStatisticsResponse,
  SearchResponse,
  GameListParams,
  LeaderboardParams,
  TimeSeriesParams,
  SearchFilters,
} from '../types/api';

// Error handling wrapper for API calls
const wrapApiCall = async <T>(
  apiCall: () => Promise<T>,
  errorCode: ErrorCode,
  metadata?: Record<string, any>
): Promise<T> => {
  try {
    return await apiCall();
  } catch (error) {
    // Handle HTTP errors with specific error codes
    if (error && typeof error === 'object' && 'status' in error) {
      const httpError = error as { status: number; message?: string };
      const specificErrorCode = mapHttpStatusToErrorCode(httpError.status);
      const errorMessage = httpError.message || `HTTP ${httpError.status} error`;
      const errorObj = new Error(errorMessage);
      errorObj.name = `HTTPError${httpError.status}`;
      throw createStandardizedError(specificErrorCode, errorObj, {
        ...metadata,
        httpStatus: httpError.status,
        originalError: error
      });
    }
    
    // Handle network/connection errors
    if (error instanceof Error && (
      error.message.includes('fetch') ||
      error.message.includes('network') ||
      error.message.includes('connection')
    )) {
      throw createStandardizedError(ErrorCode.NETWORK_ERROR, error, metadata);
    }
    
    // Handle timeout errors
    if (error instanceof Error && error.message.includes('timeout')) {
      throw createStandardizedError(ErrorCode.API_TIMEOUT, error, metadata);
    }
    
    // Default to the provided error code
    const errorObj = error instanceof Error ? error : new Error(String(error));
    throw createStandardizedError(errorCode, errorObj, metadata);
  }
};

// Query Keys
export const queryKeys = {
  games: (params?: GameListParams) => ['games', params],
  game: (gameId: string) => ['games', gameId],
  statistics: () => ['statistics'],
  statisticsOverview: () => ['statistics', 'overview'],
  timeSeries: (params: TimeSeriesParams) => ['statistics', 'timeSeries', params],
  leaderboard: (params?: LeaderboardParams) => ['leaderboard', params],
  playerStats: (playerId: string) => ['players', playerId, 'statistics'],
  searchGames: (params: SearchFilters) => ['search', 'games', params],
  searchPlayers: (query: string, limit?: number) => ['search', 'players', query, limit],
  health: () => ['health'],
} as const;

// Games Hooks
export const useGames = (
  params?: GameListParams,
  options?: Partial<UseQueryOptions<GameListResponse>>
) => {
  const cacheConfig = createCacheConfig('critical');
  const queryFn = () => wrapApiCall<GameListResponse>(
    () => apiService.getGames(params),
    ErrorCode.GAME_LOAD_FAILED,
    { action: 'load_games', params }
  );

  return useQuery({
    queryKey: queryKeys.games(params),
    queryFn,
    ...cacheConfig,
    ...options,
  });
};

export const useGame = (
  gameId: string,
  options?: Partial<UseQueryOptions<GameDetailResponse>>
) => {
  const cacheConfig = createCacheConfig('medium');
  const queryFn = () => wrapApiCall<GameDetailResponse>(
    () => apiService.getGame(gameId),
    ErrorCode.GAME_NOT_FOUND,
    { action: 'load_game', gameId }
  );

  return useQuery({
    queryKey: queryKeys.game(gameId),
    queryFn,
    enabled: !!gameId,
    ...cacheConfig,
    refetchOnMount: false, // Don't refetch completed games
    placeholderData: (previousData: GameDetailResponse | undefined) => previousData,
    ...options,
  });
};

// Statistics Hooks
export const useStatisticsOverview = (
  options?: Partial<UseQueryOptions<StatisticsOverviewResponse>>
) => {
  const cacheConfig = createCacheConfig('high');
  const queryFn = () => wrapApiCall<StatisticsOverviewResponse>(
    () => apiService.getStatisticsOverview(),
    ErrorCode.STATISTICS_LOAD_FAILED,
    { action: 'load_statistics_overview' }
  );

  return useQuery({
    queryKey: queryKeys.statisticsOverview(),
    queryFn,
    ...cacheConfig,
    placeholderData: (previousData: StatisticsOverviewResponse | undefined) => previousData,
    ...options,
  });
};

export const useTimeSeriesData = (
  params: TimeSeriesParams,
  options?: UseQueryOptions<TimeSeriesResponse>
) => {
  const cacheConfig = createCacheConfig('high');
  return useQuery({
    queryKey: queryKeys.timeSeries(params),
    queryFn: () => apiService.getTimeSeriesData(params),
    enabled: !!params.metric && !!params.interval,
    ...cacheConfig,
    placeholderData: (previousData) => previousData,
    ...options,
  });
};

// Leaderboard Hooks
export const useLeaderboard = (
  params?: LeaderboardParams,
  options?: UseQueryOptions<LeaderboardResponse>
) => {
  const cacheConfig = createCacheConfig('high');
  return useQuery({
    queryKey: queryKeys.leaderboard(params),
    queryFn: () => apiService.getLeaderboard(params),
    ...cacheConfig,
    placeholderData: (previousData) => previousData,
    ...options,
  });
};

export const usePlayerStatistics = (
  playerId: string,
  options?: UseQueryOptions<PlayerStatisticsResponse>
) => {
  const cacheConfig = createCacheConfig('medium');
  return useQuery({
    queryKey: queryKeys.playerStats(playerId),
    queryFn: () => apiService.getPlayerStatistics(playerId),
    enabled: !!playerId,
    ...cacheConfig,
    placeholderData: (previousData) => previousData,
    ...options,
  });
};

// Search Hooks
export const useSearchGames = (
  params: SearchFilters,
  options?: UseQueryOptions<SearchResponse>
) => {
  return useQuery({
    queryKey: queryKeys.searchGames(params),
    queryFn: () => apiService.searchGames(params),
    enabled: !!params.query && params.query.length > 0,
    staleTime: 30 * 1000, // 30 seconds - search results change frequently
    gcTime: 2 * 60 * 1000, // 2 minutes - short-lived search cache
    placeholderData: (previousData) => previousData,
    ...options,
  });
};

export const useSearchPlayers = (
  query: string,
  limit?: number,
  options?: UseQueryOptions<SearchResponse>
) => {
  return useQuery({
    queryKey: queryKeys.searchPlayers(query, limit),
    queryFn: () => apiService.searchPlayers(query, limit),
    enabled: !!query && query.length > 0,
    staleTime: 2 * 60 * 1000, // 2 minutes - player search is more stable
    gcTime: 5 * 60 * 1000, // 5 minutes garbage collection
    placeholderData: (previousData) => previousData,
    ...options,
  });
};

// Health Check Hook
export const useHealthCheck = (
  options?: UseQueryOptions<{ status: string; timestamp: string }>
) => {
  return useQuery({
    queryKey: queryKeys.health(),
    queryFn: () => apiService.healthCheck(),
    refetchInterval: 30 * 1000, // Check every 30 seconds
    refetchIntervalInBackground: false,
    staleTime: 10 * 1000, // 10 seconds
    gcTime: 1 * 60 * 1000, // 1 minute - health checks are short-lived
    retry: 1, // Only retry once for health checks
    ...options,
  });
};

// Cache Utility Functions
export const cacheUtils = {
  // Prefetch game list for faster navigation
  prefetchGames: (queryClient: any, params?: GameListParams) => {
    return queryClient.prefetchQuery({
      queryKey: queryKeys.games(params),
      queryFn: () => apiService.getGames(params),
      staleTime: 2 * 60 * 1000,
    });
  },

  // Prefetch game details when hovering over game in list
  prefetchGame: (queryClient: any, gameId: string) => {
    return queryClient.prefetchQuery({
      queryKey: queryKeys.game(gameId),
      queryFn: () => apiService.getGame(gameId),
      staleTime: 10 * 60 * 1000,
    });
  },

  // Prefetch leaderboard data
  prefetchLeaderboard: (queryClient: any, params?: LeaderboardParams) => {
    return queryClient.prefetchQuery({
      queryKey: queryKeys.leaderboard(params),
      queryFn: () => apiService.getLeaderboard(params),
      staleTime: 3 * 60 * 1000,
    });
  },

  // Prefetch statistics overview
  prefetchStatistics: (queryClient: any) => {
    return queryClient.prefetchQuery({
      queryKey: queryKeys.statisticsOverview(),
      queryFn: () => apiService.getStatisticsOverview(),
      staleTime: 3 * 60 * 1000,
    });
  },

  // Invalidate specific cache keys when new games are added
  invalidateGameCaches: (queryClient: any) => {
    queryClient.invalidateQueries({ queryKey: ['games'] });
    queryClient.invalidateQueries({ queryKey: ['statistics'] });
    queryClient.invalidateQueries({ queryKey: ['leaderboard'] });
  },

  // Optimistic update for game completion
  updateGameCache: (queryClient: any, gameId: string, updatedGame: any) => {
    queryClient.setQueryData(queryKeys.game(gameId), (oldData: any) => {
      if (oldData) {
        return {
          ...oldData,
          game: { ...oldData.game, ...updatedGame }
        };
      }
      return oldData;
    });
  },

  // Clear specific cache entries
  clearCache: (queryClient: any, patterns?: string[]) => {
    if (patterns) {
      patterns.forEach(pattern => {
        queryClient.removeQueries({ queryKey: [pattern] });
      });
    } else {
      queryClient.clear();
    }
  },

  // Get cache stats for debugging
  getCacheStats: (queryClient: any) => {
    const cache = queryClient.getQueryCache();
    return {
      queryCount: cache.getAll().length,
      queries: cache.getAll().map((query: any) => ({
        queryKey: query.queryKey,
        state: query.state.status,
        dataUpdatedAt: query.state.dataUpdatedAt,
        lastErrorUpdateCount: query.state.errorUpdateCount,
      })),
    };
  },
};