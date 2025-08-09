import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
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
  useStableCallback: jest.fn((callback, deps) => {
    // Return the callback function directly for testing
    return callback;
  }),
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

describe('GameListView with Advanced Filters Integration', () => {
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

  describe('Filter Panel Integration', () => {
    test('renders FilterPanel component', () => {
      const queryClient = createTestQueryClient();
      
      render(
        <MemoryRouter>
          <QueryClientProvider client={queryClient}>
            <GameListView />
          </QueryClientProvider>
        </MemoryRouter>
      );

      // Should have search input from FilterPanel
      expect(screen.getByPlaceholderText(/Search games by player names/)).toBeInTheDocument();
      
      // Should have filter toggle button
      expect(screen.getByText('Filters')).toBeInTheDocument();
    });

    test('filter panel shows advanced filtering options when expanded', () => {
      const queryClient = createTestQueryClient();
      
      render(
        <MemoryRouter>
          <QueryClientProvider client={queryClient}>
            <GameListView />
          </QueryClientProvider>
        </MemoryRouter>
      );

      // Expand filters
      const filterToggle = screen.getByText('Filters');
      fireEvent.click(filterToggle);

      // Should show all advanced filter sections
      expect(screen.getByText('Opening Analysis')).toBeInTheDocument();
      expect(screen.getByText('Player Matchups')).toBeInTheDocument();
      expect(screen.getByText('Game Length Analysis')).toBeInTheDocument();
      expect(screen.getByText('Game Results')).toBeInTheDocument();
      expect(screen.getByText('Termination Reasons')).toBeInTheDocument();
    });

    test('opening type filtering options are available', () => {
      const queryClient = createTestQueryClient();
      
      render(
        <MemoryRouter>
          <QueryClientProvider client={queryClient}>
            <GameListView />
          </QueryClientProvider>
        </MemoryRouter>
      );

      // Expand filters
      const filterToggle = screen.getByText('Filters');
      fireEvent.click(filterToggle);

      // Check ECO codes filter
      expect(screen.getByLabelText('ECO Codes')).toBeInTheDocument();
      expect(screen.getByPlaceholderText('A00, B01, C20 (comma-separated)')).toBeInTheDocument();
      expect(screen.getByText('Filter by Encyclopedia of Chess Openings codes')).toBeInTheDocument();

      // Check opening names filter
      expect(screen.getByLabelText('Opening Names')).toBeInTheDocument();
      expect(screen.getByPlaceholderText('Sicilian Defense, Queen\'s Gambit (comma-separated)')).toBeInTheDocument();
      expect(screen.getByText('Filter by opening names or variations')).toBeInTheDocument();
    });

    test('game length filtering with duration ranges and move count criteria', () => {
      const queryClient = createTestQueryClient();
      
      render(
        <MemoryRouter>
          <QueryClientProvider client={queryClient}>
            <GameListView />
          </QueryClientProvider>
        </MemoryRouter>
      );

      // Expand filters
      const filterToggle = screen.getByText('Filters');
      fireEvent.click(filterToggle);

      // Check duration range filter
      expect(screen.getByLabelText('Duration Range')).toBeInTheDocument();
      expect(screen.getByText('Filter by game duration categories')).toBeInTheDocument();
      
      const durationSelect = screen.getByLabelText('Duration Range');
      fireEvent.click(durationSelect);
      expect(screen.getByText('Blitz (≤ 10 min)')).toBeInTheDocument();
      expect(screen.getByText('Rapid (10-30 min)')).toBeInTheDocument();
      expect(screen.getByText('Classical (30-90 min)')).toBeInTheDocument();
      expect(screen.getByText('Correspondence (> 90 min)')).toBeInTheDocument();

      // Check move count range filter
      expect(screen.getByLabelText('Move Count Range')).toBeInTheDocument();
      expect(screen.getByText('Filter by total number of moves played')).toBeInTheDocument();
      
      const moveCountSelect = screen.getByLabelText('Move Count Range');
      fireEvent.click(moveCountSelect);
      expect(screen.getByText('Short games (≤ 20 moves)')).toBeInTheDocument();
      expect(screen.getByText('Medium games (21-40 moves)')).toBeInTheDocument();
      expect(screen.getByText('Long games (41-60 moves)')).toBeInTheDocument();
      expect(screen.getByText('Very long games (> 60 moves)')).toBeInTheDocument();
    });

    test('player matchup filtering for head-to-head analysis', () => {
      const queryClient = createTestQueryClient();
      
      render(
        <MemoryRouter>
          <QueryClientProvider client={queryClient}>
            <GameListView />
          </QueryClientProvider>
        </MemoryRouter>
      );

      // Expand filters
      const filterToggle = screen.getByText('Filters');
      fireEvent.click(filterToggle);

      // Check player matchup filter
      expect(screen.getByText('Player Matchups')).toBeInTheDocument();
      expect(screen.getByLabelText('Head-to-Head Analysis')).toBeInTheDocument();
      expect(screen.getByPlaceholderText('player1 vs player2')).toBeInTheDocument();
      expect(screen.getByText('Find games between specific players (e.g., "gpt-4 vs claude-3")')).toBeInTheDocument();
    });

    test('result-based filtering with win/loss/draw options and termination reasons', () => {
      const queryClient = createTestQueryClient();
      
      render(
        <MemoryRouter>
          <QueryClientProvider client={queryClient}>
            <GameListView />
          </QueryClientProvider>
        </MemoryRouter>
      );

      // Expand filters
      const filterToggle = screen.getByText('Filters');
      fireEvent.click(filterToggle);

      // Check game results section
      expect(screen.getByText('Game Results')).toBeInTheDocument();
      expect(screen.getByText('White Wins')).toBeInTheDocument();
      expect(screen.getByText('Black Wins')).toBeInTheDocument();
      expect(screen.getByText('Draw')).toBeInTheDocument();
      expect(screen.getByText('Ongoing')).toBeInTheDocument();

      // Check termination reasons section
      expect(screen.getByText('Termination Reasons')).toBeInTheDocument();
      expect(screen.getByText('Checkmate')).toBeInTheDocument();
      expect(screen.getByText('Resignation')).toBeInTheDocument();
      expect(screen.getByText('Stalemate')).toBeInTheDocument();
      expect(screen.getByText('Time Forfeit')).toBeInTheDocument();
      expect(screen.getByText('Agreement')).toBeInTheDocument();
      expect(screen.getByText('Abandoned')).toBeInTheDocument();
    });
  });

  describe('Filter Functionality', () => {
    test('filter changes trigger onFilterChange callback', () => {
      const mockOnFilterChange = jest.fn();
      const queryClient = createTestQueryClient();
      
      render(
        <MemoryRouter>
          <QueryClientProvider client={queryClient}>
            <GameListView onFilterChange={mockOnFilterChange} />
          </QueryClientProvider>
        </MemoryRouter>
      );

      // Expand filters
      const filterToggle = screen.getByText('Filters');
      fireEvent.click(filterToggle);

      // Set some filter values
      const ecoInput = screen.getByLabelText('ECO Codes');
      fireEvent.change(ecoInput, { target: { value: 'A00, B01' } });

      const matchupInput = screen.getByLabelText('Head-to-Head Analysis');
      fireEvent.change(matchupInput, { target: { value: 'gpt-4 vs claude-3' } });

      // Apply filters
      const applyButton = screen.getByText('Apply Filters');
      fireEvent.click(applyButton);

      // Should call onFilterChange with the new filters
      expect(mockOnFilterChange).toHaveBeenCalledWith(
        expect.objectContaining({
          page: 1,
          opening_eco_codes: ['A00', 'B01'],
          player_matchup: 'gpt-4 vs claude-3'
        })
      );
    });

    test('clear filters resets page to 1 and calls onFilterChange', () => {
      const mockOnFilterChange = jest.fn();
      const queryClient = createTestQueryClient();
      
      render(
        <MemoryRouter>
          <QueryClientProvider client={queryClient}>
            <GameListView 
              filters={{ page: 3, limit: 50, opening_eco_codes: ['A00'] } as any}
              onFilterChange={mockOnFilterChange} 
            />
          </QueryClientProvider>
        </MemoryRouter>
      );

      // Clear filters
      const clearButton = screen.getByText('Clear All');
      fireEvent.click(clearButton);

      // Should reset to page 1
      expect(mockOnFilterChange).toHaveBeenCalledWith(
        expect.objectContaining({
          page: 1,
          limit: 50
        })
      );
    });

    test('search functionality works with debouncing', async () => {
      const mockOnFilterChange = jest.fn();
      const queryClient = createTestQueryClient();
      
      render(
        <MemoryRouter>
          <QueryClientProvider client={queryClient}>
            <GameListView onFilterChange={mockOnFilterChange} />
          </QueryClientProvider>
        </MemoryRouter>
      );

      // Type in search input
      const searchInput = screen.getByPlaceholderText(/Search games by player names/);
      fireEvent.change(searchInput, { target: { value: 'gpt-4' } });

      // Wait for debounced search to trigger
      await waitFor(() => {
        expect(mockOnFilterChange).toHaveBeenCalledWith(
          expect.objectContaining({
            search: 'gpt-4',
            page: 1
          })
        );
      }, { timeout: 500 });
    });
  });

  describe('Filter Performance and Search', () => {
    test('handles complex filter combinations', () => {
      const mockOnFilterChange = jest.fn();
      const queryClient = createTestQueryClient();
      
      render(
        <MemoryRouter>
          <QueryClientProvider client={queryClient}>
            <GameListView onFilterChange={mockOnFilterChange} />
          </QueryClientProvider>
        </MemoryRouter>
      );

      // Expand filters
      const filterToggle = screen.getByText('Filters');
      fireEvent.click(filterToggle);

      // Set multiple filter types
      const ecoInput = screen.getByLabelText('ECO Codes');
      fireEvent.change(ecoInput, { target: { value: 'A00, B01, C20' } });

      const openingInput = screen.getByLabelText('Opening Names');
      fireEvent.change(openingInput, { target: { value: 'Sicilian Defense, Queen\'s Gambit' } });

      const matchupInput = screen.getByLabelText('Head-to-Head Analysis');
      fireEvent.change(matchupInput, { target: { value: 'gpt-4 vs claude-3' } });

      const durationSelect = screen.getByLabelText('Duration Range');
      fireEvent.change(durationSelect, { target: { value: 'blitz' } });

      const moveCountSelect = screen.getByLabelText('Move Count Range');
      fireEvent.change(moveCountSelect, { target: { value: 'short' } });

      // Select some checkboxes
      const whiteWinsCheckbox = screen.getByRole('checkbox', { name: /White Wins/ });
      fireEvent.click(whiteWinsCheckbox);

      const checkmateCheckbox = screen.getByRole('checkbox', { name: /Checkmate/ });
      fireEvent.click(checkmateCheckbox);

      // Apply filters
      const applyButton = screen.getByText('Apply Filters');
      fireEvent.click(applyButton);

      // Should handle all filter types correctly
      expect(mockOnFilterChange).toHaveBeenCalledWith(
        expect.objectContaining({
          page: 1,
          opening_eco_codes: ['A00', 'B01', 'C20'],
          opening_names: ['Sicilian Defense', 'Queen\'s Gambit'],
          player_matchup: 'gpt-4 vs claude-3',
          duration_range: 'blitz',
          move_count_range: 'short',
          results: [GameResult.WHITE_WINS],
          termination_reasons: [TerminationReason.CHECKMATE]
        })
      );
    });

    test('filters work alongside existing controls', () => {
      const mockOnFilterChange = jest.fn();
      const queryClient = createTestQueryClient();
      
      render(
        <MemoryRouter>
          <QueryClientProvider client={queryClient}>
            <GameListView onFilterChange={mockOnFilterChange} />
          </QueryClientProvider>
        </MemoryRouter>
      );

      // Should still have existing sort and limit controls
      expect(screen.getByLabelText('Sort by:')).toBeInTheDocument();
      expect(screen.getByLabelText('Show:')).toBeInTheDocument();
      
      // Should show results count
      expect(screen.getByText(/Showing 1-1 of 1 games/)).toBeInTheDocument();
    });
  });
});