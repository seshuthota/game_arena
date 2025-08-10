import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { HeadToHeadComparison } from './HeadToHeadComparison';

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

describe('HeadToHeadComparison', () => {
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
        <HeadToHeadComparison />
      </TestWrapper>
    );

    // Check that loading skeleton is rendered
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
        <HeadToHeadComparison />
      </TestWrapper>
    );

    expect(screen.getByText('Failed to load comparison data')).toBeInTheDocument();
    expect(screen.getByText('Unable to retrieve player comparison data. Please try again later.')).toBeInTheDocument();
  });

  it('renders player selection interface', async () => {
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
        <HeadToHeadComparison />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByText('Head-to-Head Player Comparison')).toBeInTheDocument();
    });

    // Check player selectors
    expect(screen.getByLabelText('Player 1:')).toBeInTheDocument();
    expect(screen.getByLabelText('Player 2:')).toBeInTheDocument();
    expect(screen.getByText('VS')).toBeInTheDocument();

    // Check that player options are available (they appear in both selectors)
    expect(screen.getAllByText('GPT-4 (50 games)')).toHaveLength(2);
    expect(screen.getAllByText('Claude-3 (30 games)')).toHaveLength(2);
    expect(screen.getAllByText('Gemini-Pro (25 games)')).toHaveLength(2);
  });

  it('shows selection prompt when no players are selected', async () => {
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
        <HeadToHeadComparison />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByText('Select Two Players to Compare')).toBeInTheDocument();
      expect(screen.getByText('Choose two players from the dropdowns above to see their head-to-head comparison, playing styles, and performance metrics.')).toBeInTheDocument();
    });
  });

  it('allows selecting players and displays comparison', async () => {
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
        <HeadToHeadComparison />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByText('Head-to-Head Player Comparison')).toBeInTheDocument();
    });

    // Select first player
    const player1Select = screen.getByLabelText('Player 1:');
    fireEvent.change(player1Select, { target: { value: 'player1' } });

    // Select second player
    const player2Select = screen.getByLabelText('Player 2:');
    fireEvent.change(player2Select, { target: { value: 'player2' } });

    await waitFor(() => {
      // Check that comparison data is displayed
      expect(screen.getByText('Head-to-Head Record')).toBeInTheDocument();
      expect(screen.getAllByText('Total Games')).toHaveLength(3); // Appears in both player cards and h2h section
      
      // Check player names are displayed in the comparison cards
      expect(screen.getByRole('heading', { name: 'GPT-4' })).toBeInTheDocument();
      expect(screen.getByRole('heading', { name: 'Claude-3' })).toBeInTheDocument();
    });
  });

  it('allows switching between comparison modes', async () => {
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
        <HeadToHeadComparison />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByText('Head-to-Head Player Comparison')).toBeInTheDocument();
    });

    // Select players first
    const player1Select = screen.getByLabelText('Player 1:');
    fireEvent.change(player1Select, { target: { value: 'player1' } });

    const player2Select = screen.getByLabelText('Player 2:');
    fireEvent.change(player2Select, { target: { value: 'player2' } });

    // Switch to detailed mode
    const modeSelect = screen.getByLabelText('View Mode:');
    fireEvent.change(modeSelect, { target: { value: 'detailed' } });

    await waitFor(() => {
      expect(screen.getByText('Opening Preferences')).toBeInTheDocument();
      expect(screen.getByText('Game Phase Strengths')).toBeInTheDocument();
      expect(screen.getByText('Detailed Tactical Analysis')).toBeInTheDocument();
    });

    // Switch to historical mode
    fireEvent.change(modeSelect, { target: { value: 'historical' } });

    await waitFor(() => {
      expect(screen.getByText('Recent Form Comparison')).toBeInTheDocument();
      expect(screen.getByText('Historical Performance')).toBeInTheDocument();
    });
  });

  it('displays tactical comparison metrics in overview mode', async () => {
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
        <HeadToHeadComparison />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByText('Head-to-Head Player Comparison')).toBeInTheDocument();
    });

    // Select players
    const player1Select = screen.getByLabelText('Player 1:');
    fireEvent.change(player1Select, { target: { value: 'player1' } });

    const player2Select = screen.getByLabelText('Player 2:');
    fireEvent.change(player2Select, { target: { value: 'player2' } });

    await waitFor(() => {
      expect(screen.getByText('Tactical Comparison')).toBeInTheDocument();
      expect(screen.getByText('Move Accuracy')).toBeInTheDocument();
      expect(screen.getByText('Blunder Rate')).toBeInTheDocument();
    });
  });

  it('displays opening preferences in detailed mode', async () => {
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
        <HeadToHeadComparison />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByText('Head-to-Head Player Comparison')).toBeInTheDocument();
    });

    // Select players and switch to detailed mode
    const player1Select = screen.getByLabelText('Player 1:');
    fireEvent.change(player1Select, { target: { value: 'player1' } });

    const player2Select = screen.getByLabelText('Player 2:');
    fireEvent.change(player2Select, { target: { value: 'player2' } });

    const modeSelect = screen.getByLabelText('View Mode:');
    fireEvent.change(modeSelect, { target: { value: 'detailed' } });

    await waitFor(() => {
      expect(screen.getByText('Opening Preferences')).toBeInTheDocument();
      expect(screen.getByText('Sicilian Defense')).toBeInTheDocument();
      expect(screen.getByText('Queen\'s Gambit')).toBeInTheDocument();
      expect(screen.getByText('King\'s Indian Defense')).toBeInTheDocument();
    });
  });

  it('displays game phase strengths in detailed mode', async () => {
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
        <HeadToHeadComparison />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByText('Head-to-Head Player Comparison')).toBeInTheDocument();
    });

    // Select players and switch to detailed mode
    const player1Select = screen.getByLabelText('Player 1:');
    fireEvent.change(player1Select, { target: { value: 'player1' } });

    const player2Select = screen.getByLabelText('Player 2:');
    fireEvent.change(player2Select, { target: { value: 'player2' } });

    const modeSelect = screen.getByLabelText('View Mode:');
    fireEvent.change(modeSelect, { target: { value: 'detailed' } });

    await waitFor(() => {
      expect(screen.getByText('Game Phase Strengths')).toBeInTheDocument();
      expect(screen.getAllByText('Opening')).toHaveLength(2); // Appears in table header and phase strengths
      expect(screen.getByText('Middlegame')).toBeInTheDocument();
      expect(screen.getByText('Endgame')).toBeInTheDocument();
    });
  });

  it('displays historical performance in historical mode', async () => {
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
        <HeadToHeadComparison />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByText('Head-to-Head Player Comparison')).toBeInTheDocument();
    });

    // Select players and switch to historical mode
    const player1Select = screen.getByLabelText('Player 1:');
    fireEvent.change(player1Select, { target: { value: 'player1' } });

    const player2Select = screen.getByLabelText('Player 2:');
    fireEvent.change(player2Select, { target: { value: 'player2' } });

    const modeSelect = screen.getByLabelText('View Mode:');
    fireEvent.change(modeSelect, { target: { value: 'historical' } });

    await waitFor(() => {
      expect(screen.getByText('Recent Form Comparison')).toBeInTheDocument();
      expect(screen.getByText('Historical Performance')).toBeInTheDocument();
      expect(screen.getByText('Last 10 Games Won')).toBeInTheDocument();
      expect(screen.getByText('Current Win Streak')).toBeInTheDocument();
      expect(screen.getByText('Recent Trend')).toBeInTheDocument();
    });
  });

  it('displays ELO ratings for both players', async () => {
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
        <HeadToHeadComparison />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByText('Head-to-Head Player Comparison')).toBeInTheDocument();
    });

    // Select players
    const player1Select = screen.getByLabelText('Player 1:');
    fireEvent.change(player1Select, { target: { value: 'player1' } });

    const player2Select = screen.getByLabelText('Player 2:');
    fireEvent.change(player2Select, { target: { value: 'player2' } });

    await waitFor(() => {
      expect(screen.getByText('ELO: 1650')).toBeInTheDocument();
      expect(screen.getByText('ELO: 1580')).toBeInTheDocument();
    });
  });

  it('handles initial player props', async () => {
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
        <HeadToHeadComparison initialPlayer1="player1" initialPlayer2="player2" />
      </TestWrapper>
    );

    await waitFor(() => {
      // Should automatically show comparison since players are pre-selected
      expect(screen.getByText('Head-to-Head Record')).toBeInTheDocument();
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
        <HeadToHeadComparison />
      </TestWrapper>
    );

    expect(screen.getByText('Head-to-Head Player Comparison')).toBeInTheDocument();
    expect(screen.getByText('Select Player 1...')).toBeInTheDocument();
    expect(screen.getByText('Select Player 2...')).toBeInTheDocument();
  });

  it('displays win/loss/draw statistics correctly', async () => {
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
        <HeadToHeadComparison />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByText('Head-to-Head Player Comparison')).toBeInTheDocument();
    });

    // Select players
    const player1Select = screen.getByLabelText('Player 1:');
    fireEvent.change(player1Select, { target: { value: 'player1' } });

    const player2Select = screen.getByLabelText('Player 2:');
    fireEvent.change(player2Select, { target: { value: 'player2' } });

    await waitFor(() => {
      // Check that win/loss/draw stats are displayed (they contain 'W', 'D' suffixes)
      const winsDrawsElements = screen.getAllByText(/\d+[WD]/);
      expect(winsDrawsElements.length).toBeGreaterThan(0);
    });
  });
});