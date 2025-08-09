import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { GameListView } from './GameListView';
import { GameResult, TerminationReason } from '../types/api';

// Mock the API hooks
jest.mock('../hooks/useApi', () => ({
  useGames: jest.fn(),
  cacheUtils: {
    prefetchGame: jest.fn(),
    prefetchGames: jest.fn()
  }
}));

// Mock performance optimizations
jest.mock('../utils/performanceOptimizations', () => ({
  usePerformanceMonitor: jest.fn(),
  useStableCallback: jest.fn((callback) => callback),
  useIntersectionObserver: jest.fn()
}));

import { useGames } from '../hooks/useApi';
const mockUseGames = useGames as jest.MockedFunction<typeof useGames>;

const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

const mockGameData = {
  games: [
    {
      game_id: 'test-game-123456789',
      tournament_id: null,
      start_time: '2024-01-01T10:00:00Z',
      end_time: '2024-01-01T11:30:00Z',
      duration_minutes: 90,
      total_moves: 45,
      is_completed: true,
      players: {
        '0': {
          player_id: 'alice_gpt4',
          model_name: 'gpt-4',
          model_provider: 'openai',
          agent_type: 'basic',
          elo_rating: 1600
        },
        '1': {
          player_id: 'bob_claude',
          model_name: 'claude-3',
          model_provider: 'anthropic',
          agent_type: 'basic',
          elo_rating: 1550
        }
      },
      outcome: {
        result: GameResult.WHITE_WINS,
        winner: 1,
        termination: TerminationReason.CHECKMATE,
        termination_details: null
      }
    }
  ],
  pagination: {
    page: 1,
    limit: 50,
    total_count: 1,
    total_pages: 1,
    has_next: false,
    has_previous: false
  },
  filters_applied: {}
};

describe('GameListView', () => {
  beforeEach(() => {
    mockUseGames.mockReturnValue({
      data: mockGameData,
      isLoading: false,
      error: null,
      refetch: jest.fn(),
    } as any);
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  describe('Card-based Layout', () => {
    test('renders games in card layout instead of table', () => {
      const queryClient = createTestQueryClient();
      
      render(
        <MemoryRouter>
          <QueryClientProvider client={queryClient}>
            <GameListView />
          </QueryClientProvider>
        </MemoryRouter>
      );

      // Should not have table elements
      expect(screen.queryByRole('table')).not.toBeInTheDocument();
      expect(screen.queryByRole('columnheader')).not.toBeInTheDocument();
      
      // Should have card elements
      expect(screen.getByText('test-gam...')).toBeInTheDocument(); // Game ID
      expect(screen.getByText('gpt-4')).toBeInTheDocument();
      expect(screen.getByText('claude-3')).toBeInTheDocument();
    });

    test('displays game cards with visual result indicators', () => {
      const queryClient = createTestQueryClient();
      
      render(
        <MemoryRouter>
          <QueryClientProvider client={queryClient}>
            <GameListView />
          </QueryClientProvider>
        </MemoryRouter>
      );

      // Check for result text with proper formatting
      expect(screen.getByText('claude-3 won by checkmate')).toBeInTheDocument();
      
      // Check for player ratings
      expect(screen.getByText('1550')).toBeInTheDocument(); // White player rating
      expect(screen.getByText('1600')).toBeInTheDocument(); // Black player rating
      
      // Check for game metadata
      expect(screen.getByText('45 moves')).toBeInTheDocument();
      expect(screen.getByText('1h 30m')).toBeInTheDocument(); // Duration formatting
    });

    test('shows player-specific result display with actual names', () => {
      const queryClient = createTestQueryClient();
      
      render(
        <MemoryRouter>
          <QueryClientProvider client={queryClient}>
            <GameListView />
          </QueryClientProvider>
        </MemoryRouter>
      );

      // Should show actual player names in result
      expect(screen.getByText('claude-3 won by checkmate')).toBeInTheDocument();
      
      // Should show winner crown
      expect(screen.getByText('👑')).toBeInTheDocument();
    });

    test('displays game metadata with opening moves and key statistics', () => {
      const queryClient = createTestQueryClient();
      
      render(
        <MemoryRouter>
          <QueryClientProvider client={queryClient}>
            <GameListView />
          </QueryClientProvider>
        </MemoryRouter>
      );

      // Check metadata icons and values
      expect(screen.getByText('🕐')).toBeInTheDocument(); // Duration icon
      expect(screen.getByText('♟️')).toBeInTheDocument(); // Moves icon
      expect(screen.getByText('📅')).toBeInTheDocument(); // Date icon
      
      // Check completion badge
      expect(screen.getByText('Completed')).toBeInTheDocument();
    });
  });

  describe('Responsive Grid Layout', () => {
    test('renders games in responsive grid', () => {
      const queryClient = createTestQueryClient();
      
      const { container } = render(
        <MemoryRouter>
          <QueryClientProvider client={queryClient}>
            <GameListView />
          </QueryClientProvider>
        </MemoryRouter>
      );

      // Check for grid container class
      const gridContainer = container.querySelector('.games-grid');
      expect(gridContainer).toBeInTheDocument();
    });

    test('handles multiple games in grid layout', () => {
      const multipleGamesData = {
        ...mockGameData,
        games: [
          mockGameData.games[0],
          {
            ...mockGameData.games[0],
            game_id: 'test-game-987654321',
            outcome: {
              result: GameResult.BLACK_WINS,
              winner: 0,
              termination: TerminationReason.RESIGNATION,
              termination_details: null
            }
          }
        ],
        pagination: {
          ...mockGameData.pagination,
          total_count: 2
        }
      };

      mockUseGames.mockReturnValue({
        data: multipleGamesData,
        isLoading: false,
        error: null,
        refetch: jest.fn(),
      } as any);

      const queryClient = createTestQueryClient();
      
      render(
        <MemoryRouter>
          <QueryClientProvider client={queryClient}>
            <GameListView />
          </QueryClientProvider>
        </MemoryRouter>
      );

      // Should show both games
      expect(screen.getAllByText('test-gam...')).toHaveLength(2);
      
      // Should show different results
      expect(screen.getByText('claude-3 won by checkmate')).toBeInTheDocument();
      expect(screen.getByText('gpt-4 won by resignation')).toBeInTheDocument();
    });
  });

  describe('Visual Result Indicators', () => {
    test('shows correct colors and icons for different game outcomes', () => {
      const drawGameData = {
        ...mockGameData,
        games: [{
          ...mockGameData.games[0],
          outcome: {
            result: GameResult.DRAW,
            winner: null,
            termination: TerminationReason.STALEMATE,
            termination_details: null
          }
        }]
      };

      mockUseGames.mockReturnValue({
        data: drawGameData,
        isLoading: false,
        error: null,
        refetch: jest.fn(),
      } as any);

      const queryClient = createTestQueryClient();
      
      render(
        <MemoryRouter>
          <QueryClientProvider client={queryClient}>
            <GameListView />
          </QueryClientProvider>
        </MemoryRouter>
      );

      // Should show draw result
      expect(screen.getByText('Draw by stalemate')).toBeInTheDocument();
      expect(screen.getByText('🤝')).toBeInTheDocument(); // Draw icon
    });

    test('shows ongoing game status correctly', () => {
      const ongoingGameData = {
        ...mockGameData,
        games: [{
          ...mockGameData.games[0],
          outcome: null,
          is_completed: false
        }]
      };

      mockUseGames.mockReturnValue({
        data: ongoingGameData,
        isLoading: false,
        error: null,
        refetch: jest.fn(),
      } as any);

      const queryClient = createTestQueryClient();
      
      render(
        <MemoryRouter>
          <QueryClientProvider client={queryClient}>
            <GameListView />
          </QueryClientProvider>
        </MemoryRouter>
      );

      // Should show ongoing status
      expect(screen.getByText('Game in progress')).toBeInTheDocument();
      expect(screen.getByText('⏳')).toBeInTheDocument(); // Ongoing icon
      expect(screen.queryByText('Completed')).not.toBeInTheDocument();
    });
  });

  describe('Controls and Pagination', () => {
    test('displays results count', () => {
      const queryClient = createTestQueryClient();
      
      render(
        <MemoryRouter>
          <QueryClientProvider client={queryClient}>
            <GameListView />
          </QueryClientProvider>
        </MemoryRouter>
      );

      expect(screen.getByText(/Showing 1-1 of 1 games/)).toBeInTheDocument();
    });

    test('shows sort controls', () => {
      const queryClient = createTestQueryClient();
      
      render(
        <MemoryRouter>
          <QueryClientProvider client={queryClient}>
            <GameListView />
          </QueryClientProvider>
        </MemoryRouter>
      );

      expect(screen.getByLabelText('Sort by:')).toBeInTheDocument();
      expect(screen.getByDisplayValue('Newest First')).toBeInTheDocument();
    });

    test('shows items per page control', () => {
      const queryClient = createTestQueryClient();
      
      render(
        <MemoryRouter>
          <QueryClientProvider client={queryClient}>
            <GameListView />
          </QueryClientProvider>
        </MemoryRouter>
      );

      expect(screen.getByLabelText('Show:')).toBeInTheDocument();
      expect(screen.getByDisplayValue('50')).toBeInTheDocument();
    });
  });

  describe('Error and Loading States', () => {
    test('shows loading skeleton when loading', () => {
      mockUseGames.mockReturnValue({
        data: null,
        isLoading: true,
        error: null,
        refetch: jest.fn(),
      } as any);

      const queryClient = createTestQueryClient();
      
      render(
        <MemoryRouter>
          <QueryClientProvider client={queryClient}>
            <GameListView />
          </QueryClientProvider>
        </MemoryRouter>
      );

      // Should show loading state (GameListSkeleton is mocked)
      expect(screen.queryByText('test-gam...')).not.toBeInTheDocument();
    });

    test('shows error state when there is an error', () => {
      mockUseGames.mockReturnValue({
        data: null,
        isLoading: false,
        error: new Error('Network error'),
        refetch: jest.fn(),
      } as any);

      const queryClient = createTestQueryClient();
      
      render(
        <MemoryRouter>
          <QueryClientProvider client={queryClient}>
            <GameListView />
          </QueryClientProvider>
        </MemoryRouter>
      );

      expect(screen.getByText('Failed to load games')).toBeInTheDocument();
      expect(screen.getByText('Network error')).toBeInTheDocument();
      expect(screen.getByText('Try Again')).toBeInTheDocument();
    });

    test('shows empty state when no games found', () => {
      mockUseGames.mockReturnValue({
        data: {
          ...mockGameData,
          games: []
        },
        isLoading: false,
        error: null,
        refetch: jest.fn(),
      } as any);

      const queryClient = createTestQueryClient();
      
      render(
        <MemoryRouter>
          <QueryClientProvider client={queryClient}>
            <GameListView />
          </QueryClientProvider>
        </MemoryRouter>
      );

      expect(screen.getByText('No games found')).toBeInTheDocument();
    });
  });

  describe('Tournament Display', () => {
    test('shows tournament badge for tournament games', () => {
      const tournamentGameData = {
        ...mockGameData,
        games: [{
          ...mockGameData.games[0],
          tournament_id: 'tournament-123'
        }]
      };

      mockUseGames.mockReturnValue({
        data: tournamentGameData,
        isLoading: false,
        error: null,
        refetch: jest.fn(),
      } as any);

      const queryClient = createTestQueryClient();
      
      render(
        <MemoryRouter>
          <QueryClientProvider client={queryClient}>
            <GameListView />
          </QueryClientProvider>
        </MemoryRouter>
      );

      expect(screen.getByText('Tournament')).toBeInTheDocument();
    });
  });
});