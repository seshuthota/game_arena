import axios, { AxiosInstance, AxiosResponse } from 'axios';
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

// Create axios instance with base configuration
const createApiClient = (): AxiosInstance => {
  const baseURL = process.env.REACT_APP_API_BASE_URL || '/api';
  
  const client = axios.create({
    baseURL,
    timeout: 30000, // 30 second timeout
    headers: {
      'Content-Type': 'application/json',
    },
  });

  // Request interceptor
  client.interceptors.request.use(
    (config) => {
      console.log(`API Request: ${config.method?.toUpperCase()} ${config.url}`);
      return config;
    },
    (error) => {
      console.error('API Request Error:', error);
      return Promise.reject(error);
    }
  );

  // Response interceptor
  client.interceptors.response.use(
    (response) => {
      console.log(`API Response: ${response.status} ${response.config.url}`);
      return response;
    },
    (error) => {
      console.error('API Response Error:', error.response?.status, error.message);
      
      // Handle common HTTP errors
      if (error.response?.status === 401) {
        // Handle unauthorized access
        console.error('Unauthorized access');
      } else if (error.response?.status === 404) {
        console.error('Resource not found');
      } else if (error.response?.status >= 500) {
        console.error('Server error');
      }
      
      return Promise.reject(error);
    }
  );

  return client;
};

// Create the API client instance
const apiClient = createApiClient();

// API Service class
class ApiService {
  private client: AxiosInstance;

  constructor(client: AxiosInstance) {
    this.client = client;
  }

  // Games API
  async getGames(params?: GameListParams): Promise<GameListResponse> {
    const response: AxiosResponse<GameListResponse> = await this.client.get('/games', {
      params: this.cleanParams(params),
    });
    return response.data;
  }

  async getGame(gameId: string): Promise<GameDetailResponse> {
    const response: AxiosResponse<GameDetailResponse> = await this.client.get(`/games/${gameId}`);
    return response.data;
  }

  // Statistics API
  async getStatisticsOverview(): Promise<StatisticsOverviewResponse> {
    const response: AxiosResponse<StatisticsOverviewResponse> = await this.client.get('/statistics/overview');
    return response.data;
  }

  async getTimeSeriesData(params: TimeSeriesParams): Promise<TimeSeriesResponse> {
    const response: AxiosResponse<TimeSeriesResponse> = await this.client.get('/statistics/time-series', {
      params: this.cleanParams(params),
    });
    return response.data;
  }

  // Leaderboard API
  async getLeaderboard(params?: LeaderboardParams): Promise<LeaderboardResponse> {
    const response: AxiosResponse<LeaderboardResponse> = await this.client.get('/leaderboard', {
      params: this.cleanParams(params),
    });
    return response.data;
  }

  async getPlayerStatistics(playerId: string): Promise<PlayerStatisticsResponse> {
    const response: AxiosResponse<PlayerStatisticsResponse> = await this.client.get(`/players/${playerId}/statistics`);
    return response.data;
  }

  // Search API
  async searchGames(params: SearchFilters): Promise<SearchResponse> {
    const response: AxiosResponse<SearchResponse> = await this.client.get('/search/games', {
      params: this.cleanParams({
        query: params.query,
        limit: params.limit,
        search_fields: params.search_fields?.join(','),
      }),
    });
    return response.data;
  }

  async searchPlayers(query: string, limit?: number): Promise<SearchResponse> {
    const response: AxiosResponse<SearchResponse> = await this.client.get('/search/players', {
      params: this.cleanParams({ query, limit }),
    });
    return response.data;
  }

  // Health check - uses root endpoint, not /api prefix
  async healthCheck(): Promise<{ status: string; timestamp: string }> {
    try {
      // Create a separate client for health check that doesn't use /api prefix
      // Since we have a proxy to localhost:8000, use relative URL
      const healthClient = axios.create({
        timeout: 5000, // Shorter timeout for health checks
        headers: {
          'Content-Type': 'application/json',
        },
      });
      const response = await healthClient.get('/health');
      return response.data;
    } catch (error) {
      throw new Error('API health check failed');
    }
  }

  // Utility method to clean undefined/null parameters
  private cleanParams(params?: Record<string, any>): Record<string, any> {
    if (!params) return {};
    
    const cleaned: Record<string, any> = {};
    
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        // Convert arrays to comma-separated strings for query parameters
        if (Array.isArray(value)) {
          cleaned[key] = value.join(',');
        } else {
          cleaned[key] = value;
        }
      }
    });
    
    return cleaned;
  }
}

// Export the API service instance
export const apiService = new ApiService(apiClient);
export default apiService;