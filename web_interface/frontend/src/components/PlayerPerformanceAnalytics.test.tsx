import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { PlayerPerformanceAnalytics } from './PlayerPerformanceAnalytics';

// Mock the API hooks
jest.mock('../hooks/useApi', () => ({
  useLeaderboard: jest.fn(),
  usePlayerStatistics: jest.fn(),
}));

const { useLeaderboard, usePlayerStatistics } = require('../hooks/useApi');

// Mock data
const mockLeaderboardData = {
  players: [
    {
      player_id: 'player1',
      model_name: 'GPT-4',
      rank: 1,
      games_played: 50,
      wins: 35,
      losses: 10,
      draws: 5,
      win_rate: 70.0,
      average_game_length: 45.5,
      elo_rating: 1650.0
    },
    {
      player_id: 'player2',
      model_name: 'Claude-3',
      rank: 2,
      games_played: 30,
      wins: 18,
      losses: 8,
      draws: 4,
      win_rate: 60.0,
      average_game_length: 52.3,
      elo_rating: 1580.0
    },
    {
      player_id: 'player3',
      model_name: 'Gemini-Pro',
      rank: 3,
      games_played: 25,
      wins: 8,
      losses: 15,
      draws: 2,
      win_rate: 32.0,
      average_game_length: 38.7,
      elo_rating: 1420.0
    }
  ],
  pagination: {
    page: 1,
    limit: 50,
    total_count: 3,
    total_pages: 1,
    has_next: false,
    has_previous: false
  },
  sort_by: 'win_rate_desc',
  filters_applied: {}
};

const mockPlayerStatsData = {
  statistics: {
    player_id: 'player1',
    model_name: 'GPT-4',
    total_games: 50,
    wins: 35,
    losses: 10,
    draws: 5,
    win_rate: 70.0,
    average_game_duration: 25.5,
    total_moves: 2275,
    legal_moves: 2275,
    illegal_moves: 0,
    move_accuracy: 95.5,
    parsing_success_rate: 98.2,
    average_thinking_time: 15.3,
    blunders: 12,
    elo_rating: 1650.0
  }
};

// Test wrapper component
const TestWrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

  return (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  );
};

describe('PlayerPerformanceAnalytics', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders loading state initially', () => {
    useLeaderboard.mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
      refetch: jest.fn()
    } as any);

    usePlayerStatistics.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: null,
      refetch: jest.fn()
    } as any);

    render(
      <TestWrapper>
        <PlayerPerformanceAnalytics />
      </TestWrapper>
    );

    // Check that loading skeleton is rendered (it's a basic div with loading-skeleton class)
    const loadingElement = document.querySelector('.loading-skeleton');
    expect(loadingElement).toBeInTheDocument();
  });

  it('renders error state when leaderboard fails to load', () => {
    useLeaderboard.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error('Failed to load leaderboard'),
      refetch: jest.fn()
    } as any);

    usePlayerStatistics.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: null,
      refetch: jest.fn()
    } as any);

    render(
      <TestWrapper>
        <PlayerPerformanceAnalytics />
      </TestWrapper>
    );

    expect(screen.getByText('Failed to load player analytics')).toBeInTheDocument();
    expect(screen.getByText('Unable to retrieve player performance data. Please try again later.')).toBeInTheDocument();
  });

  it('renders overview mode with player performance cards', async () => {
    useLeaderboard.mockReturnValue({
      data: mockLeaderboardData,
      isLoading: false,
      error: null,
      refetch: jest.fn()
    } as any);

    usePlayerStatistics.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: null,
      refetch: jest.fn()
    } as any);

    render(
      <TestWrapper>
        <PlayerPerformanceAnalytics />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByText('Player Performance Analytics')).toBeInTheDocument();
    });

    // Check that player cards are rendered
    expect(screen.getByText('GPT-4')).toBeInTheDocument();
    expect(screen.getByText('Claude-3')).toBeInTheDocument();
    expect(screen.getByText('Gemini-Pro')).toBeInTheDocument();

    // Check win rates are displayed
    expect(screen.getByText('70.0%')).toBeInTheDocument();
    expect(screen.getByText('60.0%')).toBeInTheDocument();
    expect(screen.getByText('32.0%')).toBeInTheDocument();

    // Check games played are displayed
    expect(screen.getByText('50')).toBeInTheDocument();
    expect(screen.getByText('30')).toBeInTheDocument();
    expect(screen.getByText('25')).toBeInTheDocument();
  });

  it('allows switching between view modes', async () => {
    useLeaderboard.mockReturnValue({
      data: mockLeaderboardData,
      isLoading: false,
      error: null,
      refetch: jest.fn()
    } as any);

    usePlayerStatistics.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: null,
      refetch: jest.fn()
    } as any);

    render(
      <TestWrapper>
        <PlayerPerformanceAnalytics />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByText('Player Performance Analytics')).toBeInTheDocument();
    });

    // Switch to comparison mode
    const viewSelect = screen.getByLabelText('View:');
    fireEvent.change(viewSelect, { target: { value: 'comparison' } });

    await waitFor(() => {
      expect(screen.getByText('Player Comparison')).toBeInTheDocument(); // In select option
      expect(screen.getByText('Head-to-Head Player Comparison')).toBeInTheDocument(); // HeadToHeadComparison component title
    });

    // Switch back to overview
    fireEvent.change(viewSelect, { target: { value: 'overview' } });

    await waitFor(() => {
      expect(screen.getByText('GPT-4')).toBeInTheDocument();
    });
  });

  it('allows selecting a player and switching to detailed view', async () => {
    useLeaderboard.mockReturnValue({
      data: mockLeaderboardData,
      isLoading: false,
      error: null,
      refetch: jest.fn()
    } as any);

    usePlayerStatistics.mockReturnValue({
      data: mockPlayerStatsData,
      isLoading: false,
      error: null,
      refetch: jest.fn()
    } as any);

    render(
      <TestWrapper>
        <PlayerPerformanceAnalytics />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByText('Player Performance Analytics')).toBeInTheDocument();
    });

    // Select a player
    const playerSelect = screen.getByLabelText('Player:');
    fireEvent.change(playerSelect, { target: { value: 'player1' } });

    // Switch to detailed view
    const viewSelect = screen.getByLabelText('View:');
    fireEvent.change(viewSelect, { target: { value: 'detailed' } });

    await waitFor(() => {
      expect(screen.getByText('GPT-4 - Detailed Analysis')).toBeInTheDocument();
    });

    // Check that detailed metrics are displayed
    expect(screen.getByText('Overall Performance')).toBeInTheDocument();
    expect(screen.getByText('Tactical Metrics')).toBeInTheDocument();
    expect(screen.getByText('Opening Preferences')).toBeInTheDocument();
    expect(screen.getByText('Strengths')).toBeInTheDocument();
    expect(screen.getByText('Areas for Improvement')).toBeInTheDocument();
  });

  it('displays performance trends correctly', async () => {
    useLeaderboard.mockReturnValue({
      data: mockLeaderboardData,
      isLoading: false,
      error: null,
      refetch: jest.fn()
    } as any);

    usePlayerStatistics.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: null,
      refetch: jest.fn()
    } as any);

    render(
      <TestWrapper>
        <PlayerPerformanceAnalytics />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByText('Player Performance Analytics')).toBeInTheDocument();
    });

    // Check trend indicators
    const trendIndicators = screen.getAllByText('↗'); // Improving trend
    expect(trendIndicators.length).toBeGreaterThan(0);

    const decliningTrend = screen.getAllByText('↘'); // Declining trend
    expect(decliningTrend.length).toBeGreaterThan(0);
  });

  it('handles analyze player button click', async () => {
    useLeaderboard.mockReturnValue({
      data: mockLeaderboardData,
      isLoading: false,
      error: null,
      refetch: jest.fn()
    } as any);

    usePlayerStatistics.mockReturnValue({
      data: mockPlayerStatsData,
      isLoading: false,
      error: null,
      refetch: jest.fn()
    } as any);

    render(
      <TestWrapper>
        <PlayerPerformanceAnalytics />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByText('Player Performance Analytics')).toBeInTheDocument();
    });

    // Click analyze button for first player
    const analyzeButtons = screen.getAllByText('Analyze Player');
    fireEvent.click(analyzeButtons[0]);

    await waitFor(() => {
      expect(screen.getByText('GPT-4 - Detailed Analysis')).toBeInTheDocument();
    });
  });

  it('displays opening preferences in detailed view', async () => {
    useLeaderboard.mockReturnValue({
      data: mockLeaderboardData,
      isLoading: false,
      error: null,
      refetch: jest.fn()
    } as any);

    usePlayerStatistics.mockReturnValue({
      data: mockPlayerStatsData,
      isLoading: false,
      error: null,
      refetch: jest.fn()
    } as any);

    render(
      <TestWrapper>
        <PlayerPerformanceAnalytics />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByText('Player Performance Analytics')).toBeInTheDocument();
    });

    // Select player and switch to detailed view
    const playerSelect = screen.getByLabelText('Player:');
    fireEvent.change(playerSelect, { target: { value: 'player1' } });

    const viewSelect = screen.getByLabelText('View:');
    fireEvent.change(viewSelect, { target: { value: 'detailed' } });

    await waitFor(() => {
      expect(screen.getByText('Opening Preferences')).toBeInTheDocument();
      expect(screen.getByText('Sicilian Defense')).toBeInTheDocument();
      expect(screen.getByText('Queen\'s Gambit')).toBeInTheDocument();
      expect(screen.getByText('King\'s Indian Defense')).toBeInTheDocument();
    });
  });

  it('displays recent games timeline in detailed view', async () => {
    useLeaderboard.mockReturnValue({
      data: mockLeaderboardData,
      isLoading: false,
      error: null,
      refetch: jest.fn()
    } as any);

    usePlayerStatistics.mockReturnValue({
      data: mockPlayerStatsData,
      isLoading: false,
      error: null,
      refetch: jest.fn()
    } as any);

    render(
      <TestWrapper>
        <PlayerPerformanceAnalytics />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByText('Player Performance Analytics')).toBeInTheDocument();
    });

    // Select player and switch to detailed view
    const playerSelect = screen.getByLabelText('Player:');
    fireEvent.change(playerSelect, { target: { value: 'player1' } });

    const viewSelect = screen.getByLabelText('View:');
    fireEvent.change(viewSelect, { target: { value: 'detailed' } });

    await waitFor(() => {
      expect(screen.getByText('Recent Performance (Last 10 Games)')).toBeInTheDocument();
    });

    // Check that game results are displayed
    const gameResults = screen.getAllByText(/vs Player \d+/);
    expect(gameResults.length).toBe(10);
  });

  it('calculates and displays strength and weakness areas', async () => {
    useLeaderboard.mockReturnValue({
      data: mockLeaderboardData,
      isLoading: false,
      error: null,
      refetch: jest.fn()
    } as any);

    usePlayerStatistics.mockReturnValue({
      data: mockPlayerStatsData,
      isLoading: false,
      error: null,
      refetch: jest.fn()
    } as any);

    render(
      <TestWrapper>
        <PlayerPerformanceAnalytics />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByText('Player Performance Analytics')).toBeInTheDocument();
    });

    // Check that strength areas are calculated based on the logic:
    // GPT-4: win_rate=70.0 (not > 70), avg_length=45.5 (not < 30), games=50 (not > 50) - no strengths
    // Claude-3: win_rate=60.0 (not > 70), avg_length=52.3 (not < 30), games=30 (not > 50) - no strengths  
    // Gemini-Pro: win_rate=32.0 (< 40), avg_length=38.7 (not < 30), games=25 (not > 50) - weakness: Win Rate
    
    // Check that the strengths section exists even if empty
    expect(screen.getAllByText('Strengths:')).toHaveLength(3); // One for each player card

    // Select player and switch to detailed view to see more details
    const playerSelect = screen.getByLabelText('Player:');
    fireEvent.change(playerSelect, { target: { value: 'player1' } });

    const viewSelect = screen.getByLabelText('View:');
    fireEvent.change(viewSelect, { target: { value: 'detailed' } });

    await waitFor(() => {
      expect(screen.getByText('Strengths')).toBeInTheDocument();
      expect(screen.getByText('Areas for Improvement')).toBeInTheDocument();
    });
  });

  it('handles empty leaderboard data gracefully', () => {
    useLeaderboard.mockReturnValue({
      data: { players: [], pagination: { page: 1, limit: 50, total_count: 0, total_pages: 0, has_next: false, has_previous: false }, sort_by: 'win_rate_desc', filters_applied: {} },
      isLoading: false,
      error: null,
      refetch: jest.fn()
    } as any);

    usePlayerStatistics.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: null,
      refetch: jest.fn()
    } as any);

    render(
      <TestWrapper>
        <PlayerPerformanceAnalytics />
      </TestWrapper>
    );

    expect(screen.getByText('Player Performance Analytics')).toBeInTheDocument();
    expect(screen.getByText('Select a player...')).toBeInTheDocument();
  });
});