import React, { ReactElement } from 'react';
import { render, RenderOptions } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ErrorBoundary } from '../components/ErrorBoundary';
import { ToastProvider } from '../components/Toast';

// Create a custom render function that includes providers
const AllTheProviders: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        staleTime: Infinity,
      },
    },
  });

  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <ToastProvider>
          <BrowserRouter>
            {children}
          </BrowserRouter>
        </ToastProvider>
      </QueryClientProvider>
    </ErrorBoundary>
  );
};

const customRender = (
  ui: ReactElement,
  options?: Omit<RenderOptions, 'wrapper'>
) => render(ui, { wrapper: AllTheProviders, ...options });

// Re-export everything
export * from '@testing-library/react';
export { customRender as render };

// Mock data generators
export const createMockGameSummary = (overrides = {}) => ({
  game_id: 'test-game-123',
  tournament_id: null,
  start_time: '2024-01-15T10:00:00Z',
  end_time: '2024-01-15T10:45:00Z',
  players: {
    '0': {
      player_id: 'player-white',
      model_name: 'gpt-4',
      model_provider: 'openai',
      agent_type: 'chess',
      elo_rating: 1500
    },
    '1': {
      player_id: 'player-black',
      model_name: 'claude-3',
      model_provider: 'anthropic',
      agent_type: 'chess',
      elo_rating: 1450
    }
  },
  outcome: {
    result: 'white_wins',
    winner: 0,
    termination: 'checkmate',
    termination_details: 'White checkmated black'
  },
  total_moves: 45,
  duration_minutes: 45,
  is_completed: true,
  ...overrides
});

export const createMockGameDetail = (overrides = {}) => ({
  game: createMockGameSummary(overrides),
  moves: [
    {
      move_number: 1,
      player: 0,
      action: 'e4',
      notation: 'e4',
      fen_before: 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1',
      fen_after: 'rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1',
      thinking_time: 2.5,
      timestamp: '2024-01-15T10:00:30Z',
      llm_response: 'I will open with the King\'s pawn.',
      is_legal: true,
      parsing_success: true
    },
    {
      move_number: 1,
      player: 1,
      action: 'e5',
      notation: 'e5',
      fen_before: 'rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1',
      fen_after: 'rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq e6 0 2',
      thinking_time: 1.8,
      timestamp: '2024-01-15T10:01:00Z',
      llm_response: 'I will respond symmetrically with e5.',
      is_legal: true,
      parsing_success: true
    }
  ],
  ...overrides
});

export const createMockLeaderboardEntry = (overrides = {}) => ({
  player_id: 'test-player-1',
  model_name: 'gpt-4',
  rank: 1,
  games_played: 50,
  wins: 30,
  losses: 15,
  draws: 5,
  win_rate: 0.6,
  average_game_length: 45.5,
  elo_rating: 1650,
  ...overrides
});

export const createMockStatistics = (overrides = {}) => ({
  total_games: 150,
  completed_games: 145,
  ongoing_games: 5,
  unique_players: 25,
  unique_tournaments: 3,
  total_moves: 6750,
  average_game_duration_minutes: 42.3,
  games_by_result: {
    white_wins: 65,
    black_wins: 58,
    draws: 22,
    ongoing: 5
  },
  games_by_termination: {
    checkmate: 85,
    resignation: 35,
    draw_agreement: 15,
    stalemate: 5,
    time_forfeit: 5,
    ongoing: 5
  },
  most_active_players: [
    { player_id: 'player-1', games_count: 12 },
    { player_id: 'player-2', games_count: 10 }
  ],
  average_moves_per_game: 45.0,
  shortest_game_moves: 12,
  longest_game_moves: 120,
  ...overrides
});

// Mock hooks
export const createMockResponsive = (overrides = {}) => ({
  windowSize: { width: 1024, height: 768 },
  deviceType: 'desktop' as const,
  orientation: 'landscape' as const,
  isMobile: false,
  isTablet: false,
  isDesktop: true,
  isPortrait: false,
  isLandscape: true,
  isBreakpoint: jest.fn(() => true),
  isBetweenBreakpoints: jest.fn(() => false),
  isTouchDevice: false,
  hasHover: true,
  aspectRatio: 1.33,
  ...overrides
});

// Mock API responses
export const mockApiSuccess = (data: any) => ({
  success: true,
  data,
  message: 'Success',
  timestamp: new Date().toISOString()
});

export const mockApiError = (message = 'Test error', status = 500) => ({
  success: false,
  error: {
    message,
    status,
    timestamp: new Date().toISOString()
  }
});

// Test helpers
export const waitForLoadingToFinish = () => {
  return new Promise(resolve => setTimeout(resolve, 100));
};

export const mockIntersectionObserver = () => {
  const mockIntersectionObserver = jest.fn();
  mockIntersectionObserver.mockReturnValue({
    observe: () => null,
    unobserve: () => null,
    disconnect: () => null
  });
  window.IntersectionObserver = mockIntersectionObserver;
};

export const mockResizeObserver = () => {
  const mockResizeObserver = jest.fn();
  mockResizeObserver.mockReturnValue({
    observe: () => null,
    unobserve: () => null,
    disconnect: () => null
  });
  window.ResizeObserver = mockResizeObserver;
};

// Setup common mocks
export const setupCommonMocks = () => {
  mockIntersectionObserver();
  mockResizeObserver();
  
  // Mock window.matchMedia
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: jest.fn().mockImplementation(query => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: jest.fn(), // deprecated
      removeListener: jest.fn(), // deprecated
      addEventListener: jest.fn(),
      removeEventListener: jest.fn(),
      dispatchEvent: jest.fn(),
    })),
  });

  // Mock window.scrollTo
  window.scrollTo = jest.fn();
  
  // Mock performance.now
  global.performance.now = jest.fn(() => Date.now());
};