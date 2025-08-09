import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { GameCard } from './GameCard';
import { GameSummary, GameResult, TerminationReason } from '../types/api';
import { cacheUtils } from '../hooks/useApi';

// Mock the cacheUtils
jest.mock('../hooks/useApi', () => ({
  cacheUtils: {
    prefetchGame: jest.fn()
  }
}));

const mockCacheUtils = cacheUtils as jest.Mocked<typeof cacheUtils>;

// Test wrapper component
const TestWrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false }
    }
  });

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        {children}
      </BrowserRouter>
    </QueryClientProvider>
  );
};

// Mock game data
const createMockGame = (overrides: Partial<GameSummary> = {}): GameSummary => ({
  game_id: 'test-game-123456789',
  tournament_id: null,
  start_time: '2024-01-15T10:30:00Z',
  end_time: '2024-01-15T11:15:00Z',
  players: {
    '0': {
      player_id: 'black-player',
      model_name: 'GPT-4',
      model_provider: 'OpenAI',
      agent_type: 'llm',
      elo_rating: 1650
    },
    '1': {
      player_id: 'white-player',
      model_name: 'Claude-3',
      model_provider: 'Anthropic',
      agent_type: 'llm',
      elo_rating: 1580
    }
  },
  outcome: {
    result: GameResult.WHITE_WINS,
    winner: 1,
    termination: TerminationReason.CHECKMATE,
    termination_details: null
  },
  total_moves: 42,
  duration_minutes: 45,
  is_completed: true,
  ...overrides
});

describe('GameCard', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Basic Rendering', () => {
    it('renders game card with basic information', () => {
      const game = createMockGame();
      
      render(
        <TestWrapper>
          <GameCard game={game} />
        </TestWrapper>
      );

      // Check game ID display
      expect(screen.getByText('test-gam...')).toBeInTheDocument();
      
      // Check player names
      expect(screen.getByText('Claude-3')).toBeInTheDocument();
      expect(screen.getByText('GPT-4')).toBeInTheDocument();
      
      // Check move count
      expect(screen.getByText('42 moves')).toBeInTheDocument();
      
      // Check duration
      expect(screen.getByText('45m')).toBeInTheDocument();
    });

    it('displays player ratings correctly', () => {
      const game = createMockGame();
      
      render(
        <TestWrapper>
          <GameCard game={game} />
        </TestWrapper>
      );

      expect(screen.getByText('1580')).toBeInTheDocument(); // White player rating
      expect(screen.getByText('1650')).toBeInTheDocument(); // Black player rating
    });

    it('handles players without ratings', () => {
      const game = createMockGame({
        players: {
          '0': {
            player_id: 'black-player',
            model_name: 'GPT-4',
            model_provider: 'OpenAI',
            agent_type: 'llm',
            elo_rating: null
          },
          '1': {
            player_id: 'white-player',
            model_name: 'Claude-3',
            model_provider: 'Anthropic',
            agent_type: 'llm',
            elo_rating: null
          }
        }
      });
      
      render(
        <TestWrapper>
          <GameCard game={game} />
        </TestWrapper>
      );

      expect(screen.getAllByText('Unrated')).toHaveLength(2);
    });
  });

  describe('Game Results Display', () => {
    it('displays white wins correctly', () => {
      const game = createMockGame({
        outcome: {
          result: GameResult.WHITE_WINS,
          winner: 1,
          termination: TerminationReason.CHECKMATE,
          termination_details: null
        }
      });
      
      render(
        <TestWrapper>
          <GameCard game={game} />
        </TestWrapper>
      );

      expect(screen.getByText('Claude-3 won by checkmate')).toBeInTheDocument();
      expect(screen.getByText('👑')).toBeInTheDocument(); // Winner crown
    });

    it('displays black wins correctly', () => {
      const game = createMockGame({
        outcome: {
          result: GameResult.BLACK_WINS,
          winner: 0,
          termination: TerminationReason.RESIGNATION,
          termination_details: null
        }
      });
      
      render(
        <TestWrapper>
          <GameCard game={game} />
        </TestWrapper>
      );

      expect(screen.getByText('GPT-4 won by resignation')).toBeInTheDocument();
      expect(screen.getByText('👑')).toBeInTheDocument(); // Winner crown
    });

    it('displays draw correctly', () => {
      const game = createMockGame({
        outcome: {
          result: GameResult.DRAW,
          winner: null,
          termination: TerminationReason.STALEMATE,
          termination_details: null
        }
      });
      
      render(
        <TestWrapper>
          <GameCard game={game} />
        </TestWrapper>
      );

      expect(screen.getByText('Draw by stalemate')).toBeInTheDocument();
      expect(screen.queryByText('👑')).not.toBeInTheDocument(); // No winner crown
    });

    it('displays ongoing game correctly', () => {
      const game = createMockGame({
        outcome: null,
        is_completed: false
      });
      
      render(
        <TestWrapper>
          <GameCard game={game} />
        </TestWrapper>
      );

      expect(screen.getByText('Game in progress')).toBeInTheDocument();
      expect(screen.getByText('⏳')).toBeInTheDocument(); // Ongoing status icon
    });
  });

  describe('Tournament Display', () => {
    it('shows tournament badge when game is part of tournament', () => {
      const game = createMockGame({
        tournament_id: 'tournament-123'
      });
      
      render(
        <TestWrapper>
          <GameCard game={game} />
        </TestWrapper>
      );

      expect(screen.getByText('Tournament')).toBeInTheDocument();
    });

    it('does not show tournament badge for non-tournament games', () => {
      const game = createMockGame({
        tournament_id: null
      });
      
      render(
        <TestWrapper>
          <GameCard game={game} />
        </TestWrapper>
      );

      expect(screen.queryByText('Tournament')).not.toBeInTheDocument();
    });
  });

  describe('Duration Formatting', () => {
    it('formats short durations in minutes', () => {
      const game = createMockGame({
        duration_minutes: 25
      });
      
      render(
        <TestWrapper>
          <GameCard game={game} />
        </TestWrapper>
      );

      expect(screen.getByText('25m')).toBeInTheDocument();
    });

    it('formats long durations in hours and minutes', () => {
      const game = createMockGame({
        duration_minutes: 125 // 2h 5m
      });
      
      render(
        <TestWrapper>
          <GameCard game={game} />
        </TestWrapper>
      );

      expect(screen.getByText('2h 5m')).toBeInTheDocument();
    });

    it('handles null duration', () => {
      const game = createMockGame({
        duration_minutes: null
      });
      
      render(
        <TestWrapper>
          <GameCard game={game} />
        </TestWrapper>
      );

      expect(screen.getByText('N/A')).toBeInTheDocument();
    });
  });

  describe('Date Formatting', () => {
    it('formats recent dates as relative time', () => {
      const yesterday = new Date();
      yesterday.setDate(yesterday.getDate() - 1);
      
      const game = createMockGame({
        start_time: yesterday.toISOString()
      });
      
      render(
        <TestWrapper>
          <GameCard game={game} />
        </TestWrapper>
      );

      // Use regex to match relative time formats (Yesterday, 1-2 days ago)
      expect(screen.getByText(/Yesterday|[1-2] days ago/)).toBeInTheDocument();
    });

    it('formats dates within a week as days ago', () => {
      const threeDaysAgo = new Date();
      threeDaysAgo.setDate(threeDaysAgo.getDate() - 3);
      
      const game = createMockGame({
        start_time: threeDaysAgo.toISOString()
      });
      
      render(
        <TestWrapper>
          <GameCard game={game} />
        </TestWrapper>
      );

      // Use regex to match "3 days ago" or "4 days ago" since the calculation might vary
      expect(screen.getByText(/[3-4] days ago/)).toBeInTheDocument();
    });
  });

  describe('Completion Status', () => {
    it('shows completion badge for completed games', () => {
      const game = createMockGame({
        is_completed: true
      });
      
      render(
        <TestWrapper>
          <GameCard game={game} />
        </TestWrapper>
      );

      expect(screen.getByText('Completed')).toBeInTheDocument();
    });

    it('does not show completion badge for ongoing games', () => {
      const game = createMockGame({
        is_completed: false,
        outcome: null
      });
      
      render(
        <TestWrapper>
          <GameCard game={game} />
        </TestWrapper>
      );

      expect(screen.queryByText('Completed')).not.toBeInTheDocument();
    });
  });

  describe('Interaction Behavior', () => {
    it('creates correct link to game detail page', () => {
      const game = createMockGame();
      
      render(
        <TestWrapper>
          <GameCard game={game} />
        </TestWrapper>
      );

      const link = screen.getByRole('link');
      expect(link).toHaveAttribute('href', '/games/test-game-123456789');
    });

    it('prefetches game data on hover', async () => {
      const game = createMockGame();
      mockCacheUtils.prefetchGame.mockResolvedValue(undefined);
      
      render(
        <TestWrapper>
          <GameCard game={game} />
        </TestWrapper>
      );

      const card = screen.getByRole('link');
      fireEvent.mouseEnter(card);

      await waitFor(() => {
        expect(mockCacheUtils.prefetchGame).toHaveBeenCalledWith(
          expect.any(Object),
          'test-game-123456789'
        );
      });
    });

    it('handles prefetch errors gracefully', async () => {
      const game = createMockGame();
      mockCacheUtils.prefetchGame.mockRejectedValue(new Error('Network error'));
      
      render(
        <TestWrapper>
          <GameCard game={game} />
        </TestWrapper>
      );

      const card = screen.getByRole('link');
      
      // Should not throw error
      expect(() => {
        fireEvent.mouseEnter(card);
      }).not.toThrow();
    });
  });

  describe('Visual Result Indicators', () => {
    it('shows correct status icon for white wins', () => {
      const game = createMockGame({
        outcome: {
          result: GameResult.WHITE_WINS,
          winner: 1,
          termination: TerminationReason.CHECKMATE,
          termination_details: null
        }
      });
      
      const { container } = render(
        <TestWrapper>
          <GameCard game={game} />
        </TestWrapper>
      );

      // Check for status indicator with white wins class
      const statusIndicator = container.querySelector('.status-indicator.result-white-wins');
      expect(statusIndicator).toBeInTheDocument();
      expect(statusIndicator).toHaveTextContent('⚪');
    });

    it('shows correct status icon for black wins', () => {
      const game = createMockGame({
        outcome: {
          result: GameResult.BLACK_WINS,
          winner: 0,
          termination: TerminationReason.CHECKMATE,
          termination_details: null
        }
      });
      
      const { container } = render(
        <TestWrapper>
          <GameCard game={game} />
        </TestWrapper>
      );

      // Check for status indicator with black wins class
      const statusIndicator = container.querySelector('.status-indicator.result-black-wins');
      expect(statusIndicator).toBeInTheDocument();
      expect(statusIndicator).toHaveTextContent('⚫');
    });

    it('shows correct status icon for draws', () => {
      const game = createMockGame({
        outcome: {
          result: GameResult.DRAW,
          winner: null,
          termination: TerminationReason.STALEMATE,
          termination_details: null
        }
      });
      
      const { container } = render(
        <TestWrapper>
          <GameCard game={game} />
        </TestWrapper>
      );

      // Check for status indicator with draw class
      const statusIndicator = container.querySelector('.status-indicator.result-draw');
      expect(statusIndicator).toBeInTheDocument();
      expect(statusIndicator).toHaveTextContent('🤝');
    });
  });

  describe('Responsive Behavior', () => {
    it('renders without layout issues on mobile viewport', () => {
      // Mock mobile viewport
      Object.defineProperty(window, 'innerWidth', {
        writable: true,
        configurable: true,
        value: 375,
      });

      const game = createMockGame();
      
      const { container } = render(
        <TestWrapper>
          <GameCard game={game} />
        </TestWrapper>
      );

      // Should render without throwing errors
      expect(container.firstChild).toBeInTheDocument();
    });

    it('renders without layout issues on desktop viewport', () => {
      // Mock desktop viewport
      Object.defineProperty(window, 'innerWidth', {
        writable: true,
        configurable: true,
        value: 1024,
      });

      const game = createMockGame();
      
      const { container } = render(
        <TestWrapper>
          <GameCard game={game} />
        </TestWrapper>
      );

      // Should render without throwing errors
      expect(container.firstChild).toBeInTheDocument();
    });
  });

  describe('Edge Cases', () => {
    it('handles missing player information gracefully', () => {
      const game = createMockGame({
        players: {
          '0': {
            player_id: 'black-player',
            model_name: '',
            model_provider: 'OpenAI',
            agent_type: 'llm',
            elo_rating: null
          },
          '1': {
            player_id: 'white-player',
            model_name: '',
            model_provider: 'Anthropic',
            agent_type: 'llm',
            elo_rating: null
          }
        }
      });
      
      render(
        <TestWrapper>
          <GameCard game={game} />
        </TestWrapper>
      );

      expect(screen.getAllByText('Unknown')).toHaveLength(2);
    });

    it('handles various termination reasons correctly', () => {
      const terminationReasons = [
        { termination: TerminationReason.TIME_FORFEIT, expected: 'on time' },
        { termination: TerminationReason.AGREEMENT, expected: 'by agreement' },
        { termination: TerminationReason.ABANDONED, expected: 'game abandoned' },
        { termination: TerminationReason.INSUFFICIENT_MATERIAL, expected: 'insufficient material' },
        { termination: TerminationReason.THREEFOLD_REPETITION, expected: 'threefold repetition' },
        { termination: TerminationReason.FIFTY_MOVE_RULE, expected: 'fifty-move rule' }
      ];

      terminationReasons.forEach(({ termination, expected }) => {
        const game = createMockGame({
          outcome: {
            result: GameResult.WHITE_WINS,
            winner: 1,
            termination,
            termination_details: null
          }
        });
        
        const { unmount } = render(
          <TestWrapper>
            <GameCard game={game} />
          </TestWrapper>
        );

        expect(screen.getByText(new RegExp(expected))).toBeInTheDocument();
        unmount();
      });
    });
  });
});