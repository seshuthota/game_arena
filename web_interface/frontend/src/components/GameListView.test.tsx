import React from 'react';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { GameListView } from './GameListView';

// Mock the API hooks
jest.mock('../hooks/useApi', () => ({
  useGames: () => ({
    data: {
      games: [
        {
          game_id: 'test-game-1',
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
    },
    isLoading: false,
    error: null,
    refetch: jest.fn(),
  }),
}));

const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

describe('GameListView', () => {
  test('renders game list with data', () => {
    const queryClient = createTestQueryClient();
    
    render(
      <MemoryRouter>
        <QueryClientProvider client={queryClient}>
          <GameListView />
        </QueryClientProvider>
      </MemoryRouter>
    );

    // Check if games are displayed
    expect(screen.getByText('test-gam...')).toBeInTheDocument(); // First 8 chars + ...
    expect(screen.getByText('gpt-4')).toBeInTheDocument();
    expect(screen.getByText('claude-3')).toBeInTheDocument();
    expect(screen.getByText('White Wins')).toBeInTheDocument();
  });

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
});