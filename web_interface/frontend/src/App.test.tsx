import React from 'react';
import { render, screen } from '@testing-library/react';
import App from './App';

// Mock the API hooks to prevent actual API calls during tests
jest.mock('./hooks/useApi', () => ({
  useHealthCheck: () => ({
    data: { status: 'healthy', timestamp: '2024-01-01T00:00:00Z' },
    isError: false,
  }),
  useStatisticsOverview: () => ({
    data: {
      statistics: {
        total_games: 100,
        completed_games: 95,
        total_players: 10,
        average_game_duration: 45,
      },
    },
    isLoading: false,
    error: null,
  }),
}));

test('renders game analysis dashboard', () => {
  render(<App />);
  const titleElement = screen.getByRole('heading', { name: /Game Analysis Dashboard/i });
  expect(titleElement).toBeInTheDocument();
});

test('renders navigation links', () => {
  render(<App />);
  
  // Check that key navigation links are present
  const allGamesLinks = screen.getAllByText('Games');
  const allStatisticsLinks = screen.getAllByText('Statistics');
  const allLeaderboardLinks = screen.getAllByText('Leaderboard');
  
  // Should appear at least once (header and/or footer)
  expect(allGamesLinks.length).toBeGreaterThan(0);
  expect(allStatisticsLinks.length).toBeGreaterThan(0); 
  expect(allLeaderboardLinks.length).toBeGreaterThan(0);
});

test('renders system status indicator', () => {
  render(<App />);
  
  const statusIndicator = screen.getByText('Online');
  expect(statusIndicator).toBeInTheDocument();
});