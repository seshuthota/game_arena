// Application constants and configuration values

export const APP_CONFIG = {
  name: 'Game Analysis Dashboard',
  version: '1.0.0',
  description: 'Comprehensive analytics for LLM vs LLM chess games',
} as const;

export const API_CONFIG = {
  baseURL: process.env.REACT_APP_API_BASE_URL || '/api',
  timeout: 30000,
  retryAttempts: 3,
  retryDelay: 1000,
} as const;

export const UI_CONFIG = {
  defaultPageSize: 50,
  maxPageSize: 1000,
  debounceDelay: 300,
  animationDuration: 200,
} as const;

export const ROUTES = {
  HOME: '/',
  GAMES: '/games',
  GAME_DETAIL: '/games/:gameId',
  STATISTICS: '/statistics',
  LEADERBOARD: '/leaderboard',
  PLAYER_DETAIL: '/players/:playerId',
} as const;

export const QUERY_KEYS = {
  GAMES: 'games',
  GAME: 'game',
  STATISTICS: 'statistics',
  LEADERBOARD: 'leaderboard',
  PLAYER_STATS: 'playerStats',
  SEARCH: 'search',
  HEALTH: 'health',
} as const;

export const ERROR_MESSAGES = {
  NETWORK_ERROR: 'Network error. Please check your connection and try again.',
  SERVER_ERROR: 'Server error. Please try again later.',
  NOT_FOUND: 'The requested resource was not found.',
  UNAUTHORIZED: 'You are not authorized to access this resource.',
  VALIDATION_ERROR: 'Please check your input and try again.',
  GENERIC_ERROR: 'Something went wrong. Please try again.',
} as const;