import React from 'react';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { GameDetailView } from './GameDetailView';

// Mock the API hooks
jest.mock('../hooks/useApi', () => ({
  useGame: (gameId: string) => {
    if (gameId === 'test-game-1') {
      return {
        data: {
          game: {
            game_id: 'test-game-1-full-id',
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
              result: 'white_wins',
              winner: 0,
              termination: 'checkmate',
              termination_details: null
            },
            tournament_id: 'tournament-123'
          },
          moves: [
            {
              notation: 'e4',
              action: 'e2e4',
              timestamp: '2024-01-01T10:00:30Z'
            },
            {
              notation: 'e5',
              action: 'e7e5',
              timestamp: '2024-01-01T10:01:00Z'
            },
            {
              notation: 'Nf3',
              action: 'g1f3',
              timestamp: '2024-01-01T10:01:30Z'
            }
          ]
        },
        isLoading: false,
        error: null,
        refetch: jest.fn(),
      };
    }
    
    if (gameId === 'loading-game') {
      return {
        data: null,
        isLoading: true,
        error: null,
        refetch: jest.fn(),
      };
    }
    
    if (gameId === 'error-game') {
      return {
        data: null,
        isLoading: false,
        error: new Error('Failed to fetch game'),
        refetch: jest.fn(),
      };
    }
    
    // Not found case
    return {
      data: null,
      isLoading: false,
      error: null,
      refetch: jest.fn(),
    };
  },
}));

const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

describe('GameDetailView', () => {
  test('renders loading state', () => {
    const queryClient = createTestQueryClient();
    
    render(
      <MemoryRouter initialEntries={['/games/loading-game']}>
        <QueryClientProvider client={queryClient}>
          <GameDetailView gameId="loading-game" />
        </QueryClientProvider>
      </MemoryRouter>
    );

    expect(screen.getByText('Loading game details...')).toBeInTheDocument();
  });

  test('renders error state', () => {
    const queryClient = createTestQueryClient();
    
    render(
      <MemoryRouter initialEntries={['/games/error-game']}>
        <QueryClientProvider client={queryClient}>
          <GameDetailView gameId="error-game" />
        </QueryClientProvider>
      </MemoryRouter>
    );

    expect(screen.getByText('Failed to load game')).toBeInTheDocument();
    expect(screen.getByText('Failed to fetch game')).toBeInTheDocument();
    expect(screen.getByText('Try Again')).toBeInTheDocument();
    expect(screen.getByText('← Back to Games')).toBeInTheDocument();
  });

  test('renders not found state', () => {
    const queryClient = createTestQueryClient();
    
    render(
      <MemoryRouter initialEntries={['/games/not-found-game']}>
        <QueryClientProvider client={queryClient}>
          <GameDetailView gameId="not-found-game" />
        </QueryClientProvider>
      </MemoryRouter>
    );

    expect(screen.getByText('Game not found')).toBeInTheDocument();
    expect(screen.getByText(/The requested game could not be found/)).toBeInTheDocument();
    expect(screen.getByText('← Back to Games')).toBeInTheDocument();
  });

  test('renders game details with complete data', () => {
    const queryClient = createTestQueryClient();
    
    render(
      <MemoryRouter initialEntries={['/games/test-game-1']}>
        <QueryClientProvider client={queryClient}>
          <GameDetailView gameId="test-game-1" />
        </QueryClientProvider>
      </MemoryRouter>
    );

    // Check breadcrumb
    expect(screen.getByText('Games')).toBeInTheDocument();
    expect(screen.getByText('Game Details')).toBeInTheDocument();

    // Check game header
    expect(screen.getByText(/Game test-gam/)).toBeInTheDocument(); // Truncated game ID
    expect(screen.getByText('test-game-1-full-id')).toBeInTheDocument(); // Full ID in code block

    // Check tournament info
    expect(screen.getByText('Tournament:')).toBeInTheDocument();
    expect(screen.getByText('tournament-123')).toBeInTheDocument();

    // Check game result
    expect(screen.getByText('White Wins')).toBeInTheDocument();
    expect(screen.getByText('by checkmate')).toBeInTheDocument();

    // Check player information
    expect(screen.getAllByText('White').length).toBeGreaterThanOrEqual(2); // Player card and moves
    expect(screen.getAllByText('Black').length).toBeGreaterThanOrEqual(2); // Player card and moves
    expect(screen.getByText('gpt-4')).toBeInTheDocument();
    expect(screen.getByText('claude-3')).toBeInTheDocument();
    expect(screen.getByText('openai')).toBeInTheDocument();
    expect(screen.getByText('anthropic')).toBeInTheDocument();

    // Check metadata
    expect(screen.getByText('Game Information')).toBeInTheDocument();
    expect(screen.getByText('Started:')).toBeInTheDocument();
    expect(screen.getByText('Ended:')).toBeInTheDocument();
    expect(screen.getByText('Duration:')).toBeInTheDocument();
    expect(screen.getByText('Total Moves:')).toBeInTheDocument();
    expect(screen.getByText('45')).toBeInTheDocument();
    expect(screen.getByText('Completed')).toBeInTheDocument();

    // Check move list
    expect(screen.getByText('Move History')).toBeInTheDocument();
    expect(screen.getByText('3 moves')).toBeInTheDocument();
    expect(screen.getByText('e4')).toBeInTheDocument();
    expect(screen.getByText('e5')).toBeInTheDocument();
    expect(screen.getByText('Nf3')).toBeInTheDocument();
  });

  test('displays move numbers correctly', () => {
    const queryClient = createTestQueryClient();
    
    render(
      <MemoryRouter initialEntries={['/games/test-game-1']}>
        <QueryClientProvider client={queryClient}>
          <GameDetailView gameId="test-game-1" />
        </QueryClientProvider>
      </MemoryRouter>
    );

    // Check move numbering (white moves end with '.', black moves with '...')
    expect(screen.getByText('1.')).toBeInTheDocument(); // First white move
    expect(screen.getByText('1...')).toBeInTheDocument(); // First black move  
    expect(screen.getByText('2.')).toBeInTheDocument(); // Second white move
  });

  // Skipping empty move list test for now as it requires more complex mock setup
});