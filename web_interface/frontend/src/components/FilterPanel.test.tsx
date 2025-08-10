import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { FilterPanel } from './FilterPanel';
import { GameResult, TerminationReason } from '../types/api';

const mockFilters = {
  page: 1,
  limit: 50,
};

const mockOnFiltersChange = jest.fn();
const mockOnClearFilters = jest.fn();

// Mock timers for debounced search
jest.useFakeTimers();

describe('FilterPanel', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  afterEach(() => {
    jest.runOnlyPendingTimers();
    jest.useRealTimers();
  });

  describe('Basic Functionality', () => {
    test('renders search input', () => {
      render(
        <FilterPanel
          filters={mockFilters}
          onFiltersChange={mockOnFiltersChange}
          onClearFilters={mockOnClearFilters}
        />
      );

      const searchInput = screen.getByPlaceholderText(/Search games by player names/);
      expect(searchInput).toBeInTheDocument();
    });

    test('search input calls debounced function', async () => {
      jest.useRealTimers(); // Use real timers for this test
      
      render(
        <FilterPanel
          filters={mockFilters}
          onFiltersChange={mockOnFiltersChange}
          onClearFilters={mockOnClearFilters}
        />
      );

      const searchInput = screen.getByPlaceholderText(/Search games by player names/);
      fireEvent.change(searchInput, { target: { value: 'test search' } });

      expect(searchInput).toHaveValue('test search');
      
      // Wait for debounced function to be called
      await waitFor(() => {
        expect(mockOnFiltersChange).toHaveBeenCalledWith(
          expect.objectContaining({
            search: 'test search',
            page: 1
          })
        );
      }, { timeout: 500 });
    });

    test('filter toggle shows and hides filters', () => {
      render(
        <FilterPanel
          filters={mockFilters}
          onFiltersChange={mockOnFiltersChange}
          onClearFilters={mockOnClearFilters}
        />
      );

      const filterToggle = screen.getByText('Filters');
      
      // Filter content should not be visible initially
      expect(screen.queryByText('Players')).not.toBeInTheDocument();
      
      // Click to expand filters
      fireEvent.click(filterToggle);
      
      // Filter content should be visible after click
      expect(screen.getByText('Players')).toBeInTheDocument();
      expect(screen.getByText('Date Range')).toBeInTheDocument();
      expect(screen.getByText('Game Results')).toBeInTheDocument();
    });

    test('clear filters button calls onClearFilters', () => {
      const filtersWithData = {
        ...mockFilters,
        search: 'test search',
      };

      render(
        <FilterPanel
          filters={filtersWithData}
          onFiltersChange={mockOnFiltersChange}
          onClearFilters={mockOnClearFilters}
        />
      );

      const clearButton = screen.getByText('Clear All');
      fireEvent.click(clearButton);

      expect(mockOnClearFilters).toHaveBeenCalledTimes(1);
    });
  });

  describe('Advanced Filtering Features', () => {
    beforeEach(() => {
      render(
        <FilterPanel
          filters={mockFilters}
          onFiltersChange={mockOnFiltersChange}
          onClearFilters={mockOnClearFilters}
        />
      );

      // Expand filters to access advanced options
      const filterToggle = screen.getByText('Filters');
      fireEvent.click(filterToggle);
    });

    describe('Opening Type Filtering', () => {
      test('renders ECO codes filter input', () => {
        expect(screen.getByLabelText('ECO Codes')).toBeInTheDocument();
        expect(screen.getByPlaceholderText('A00, B01, C20 (comma-separated)')).toBeInTheDocument();
        expect(screen.getByText('Filter by Encyclopedia of Chess Openings codes')).toBeInTheDocument();
      });

      test('renders opening names filter input', () => {
        expect(screen.getByLabelText('Opening Names')).toBeInTheDocument();
        expect(screen.getByPlaceholderText('Sicilian Defense, Queen\'s Gambit (comma-separated)')).toBeInTheDocument();
        expect(screen.getByText('Filter by opening names or variations')).toBeInTheDocument();
      });

      test('ECO codes filter accepts input', () => {
        const ecoInput = screen.getByLabelText('ECO Codes');
        fireEvent.change(ecoInput, { target: { value: 'A00, B01, C20' } });
        expect(ecoInput).toHaveValue('A00, B01, C20');
      });

      test('opening names filter accepts input', () => {
        const openingInput = screen.getByLabelText('Opening Names');
        fireEvent.change(openingInput, { target: { value: 'Sicilian Defense, Queen\'s Gambit' } });
        expect(openingInput).toHaveValue('Sicilian Defense, Queen\'s Gambit');
      });
    });

    describe('Player Matchup Filtering', () => {
      test('renders player matchup filter', () => {
        expect(screen.getByText('Player Matchups')).toBeInTheDocument();
        expect(screen.getByLabelText('Head-to-Head Analysis')).toBeInTheDocument();
        expect(screen.getByPlaceholderText('player1 vs player2')).toBeInTheDocument();
        expect(screen.getByText('Find games between specific players (e.g., "gpt-4 vs claude-3")')).toBeInTheDocument();
      });

      test('player matchup filter accepts input', () => {
        const matchupInput = screen.getByLabelText('Head-to-Head Analysis');
        fireEvent.change(matchupInput, { target: { value: 'gpt-4 vs claude-3' } });
        expect(matchupInput).toHaveValue('gpt-4 vs claude-3');
      });
    });

    describe('Game Length Filtering', () => {
      test('renders duration range filter', () => {
        expect(screen.getByText('Game Length Analysis')).toBeInTheDocument();
        expect(screen.getByLabelText('Duration Range')).toBeInTheDocument();
        expect(screen.getByText('Filter by game duration categories')).toBeInTheDocument();
        
        // Check duration options
        const durationSelect = screen.getByLabelText('Duration Range');
        expect(durationSelect).toBeInTheDocument();
        
        // Check if options exist
        fireEvent.click(durationSelect);
        expect(screen.getByText('Blitz (≤ 10 min)')).toBeInTheDocument();
        expect(screen.getByText('Rapid (10-30 min)')).toBeInTheDocument();
        expect(screen.getByText('Classical (30-90 min)')).toBeInTheDocument();
        expect(screen.getByText('Correspondence (> 90 min)')).toBeInTheDocument();
      });

      test('renders move count range filter', () => {
        expect(screen.getByLabelText('Move Count Range')).toBeInTheDocument();
        expect(screen.getByText('Filter by total number of moves played')).toBeInTheDocument();
        
        // Check move count options
        const moveCountSelect = screen.getByLabelText('Move Count Range');
        expect(moveCountSelect).toBeInTheDocument();
        
        // Check if options exist
        fireEvent.click(moveCountSelect);
        expect(screen.getByText('Short games (≤ 20 moves)')).toBeInTheDocument();
        expect(screen.getByText('Medium games (21-40 moves)')).toBeInTheDocument();
        expect(screen.getByText('Long games (41-60 moves)')).toBeInTheDocument();
        expect(screen.getByText('Very long games (> 60 moves)')).toBeInTheDocument();
      });

      test('duration range filter selection works', () => {
        const durationSelect = screen.getByLabelText('Duration Range');
        fireEvent.change(durationSelect, { target: { value: 'blitz' } });
        expect(durationSelect).toHaveValue('blitz');
      });

      test('move count range filter selection works', () => {
        const moveCountSelect = screen.getByLabelText('Move Count Range');
        fireEvent.change(moveCountSelect, { target: { value: 'short' } });
        expect(moveCountSelect).toHaveValue('short');
      });
    });

    describe('Result-based Filtering', () => {
      test('renders game results checkboxes', () => {
        expect(screen.getByText('Game Results')).toBeInTheDocument();
        
        // Check for result options
        expect(screen.getByText('White Wins')).toBeInTheDocument();
        expect(screen.getByText('Black Wins')).toBeInTheDocument();
        expect(screen.getByText('Draw')).toBeInTheDocument();
        expect(screen.getByText('Ongoing')).toBeInTheDocument();
      });

      test('renders termination reasons checkboxes', () => {
        expect(screen.getByText('Termination Reasons')).toBeInTheDocument();
        
        // Check for some termination reasons
        expect(screen.getByText('Checkmate')).toBeInTheDocument();
        expect(screen.getByText('Resignation')).toBeInTheDocument();
        expect(screen.getByText('Stalemate')).toBeInTheDocument();
        expect(screen.getByText('Time Forfeit')).toBeInTheDocument();
      });

      test('game result checkboxes can be selected', () => {
        const whiteWinsCheckbox = screen.getByRole('checkbox', { name: /White Wins/ });
        fireEvent.click(whiteWinsCheckbox);
        expect(whiteWinsCheckbox).toBeChecked();
      });

      test('termination reason checkboxes can be selected', () => {
        const checkmateCheckbox = screen.getByRole('checkbox', { name: /Checkmate/ });
        fireEvent.click(checkmateCheckbox);
        expect(checkmateCheckbox).toBeChecked();
      });
    });
  });

  describe('Filter Application', () => {
    test('apply filters button processes all filter types', () => {
      render(
        <FilterPanel
          filters={mockFilters}
          onFiltersChange={mockOnFiltersChange}
          onClearFilters={mockOnClearFilters}
        />
      );

      // Expand filters
      const filterToggle = screen.getByText('Filters');
      fireEvent.click(filterToggle);

      // Set various filter values
      const ecoInput = screen.getByLabelText('ECO Codes');
      fireEvent.change(ecoInput, { target: { value: 'A00, B01' } });

      const openingInput = screen.getByLabelText('Opening Names');
      fireEvent.change(openingInput, { target: { value: 'Sicilian Defense' } });

      const matchupInput = screen.getByLabelText('Head-to-Head Analysis');
      fireEvent.change(matchupInput, { target: { value: 'gpt-4 vs claude-3' } });

      const durationSelect = screen.getByLabelText('Duration Range');
      fireEvent.change(durationSelect, { target: { value: 'blitz' } });

      const moveCountSelect = screen.getByLabelText('Move Count Range');
      fireEvent.change(moveCountSelect, { target: { value: 'short' } });

      // Apply filters
      const applyButton = screen.getByText('Apply Filters');
      fireEvent.click(applyButton);

      // Check that onFiltersChange was called with correct parameters
      expect(mockOnFiltersChange).toHaveBeenCalledWith(
        expect.objectContaining({
          page: 1,
          opening_eco_codes: ['A00', 'B01'],
          opening_names: ['Sicilian Defense'],
          player_matchup: 'gpt-4 vs claude-3',
          duration_range: 'blitz',
          move_count_range: 'short'
        })
      );
    });

    test('clear filters resets all advanced filter fields', () => {
      const filtersWithAdvancedData = {
        ...mockFilters,
        opening_eco_codes: ['A00', 'B01'],
        opening_names: ['Sicilian Defense'],
        player_matchup: 'gpt-4 vs claude-3',
        duration_range: 'blitz',
        move_count_range: 'short'
      };

      render(
        <FilterPanel
          filters={filtersWithAdvancedData}
          onFiltersChange={mockOnFiltersChange}
          onClearFilters={mockOnClearFilters}
        />
      );

      // Clear filters
      const clearButton = screen.getByText('Clear All');
      fireEvent.click(clearButton);

      expect(mockOnClearFilters).toHaveBeenCalledTimes(1);

      // Expand filters to check if fields are cleared
      const filterToggle = screen.getByText('Filters');
      fireEvent.click(filterToggle);

      // Check that advanced filter fields are cleared
      expect(screen.getByLabelText('ECO Codes')).toHaveValue('');
      expect(screen.getByLabelText('Opening Names')).toHaveValue('');
      expect(screen.getByLabelText('Head-to-Head Analysis')).toHaveValue('');
      expect(screen.getByLabelText('Duration Range')).toHaveValue('');
      expect(screen.getByLabelText('Move Count Range')).toHaveValue('');
    });
  });

  describe('Filter Performance', () => {
    test('handles empty filter inputs gracefully', () => {
      render(
        <FilterPanel
          filters={mockFilters}
          onFiltersChange={mockOnFiltersChange}
          onClearFilters={mockOnClearFilters}
        />
      );

      // Expand filters
      const filterToggle = screen.getByText('Filters');
      fireEvent.click(filterToggle);

      // Apply filters without setting any values
      const applyButton = screen.getByText('Apply Filters');
      fireEvent.click(applyButton);

      // Should not include empty filter properties
      expect(mockOnFiltersChange).toHaveBeenCalledWith(
        expect.objectContaining({
          page: 1,
          limit: 50
        })
      );

      // Should not have advanced filter properties
      const callArgs = mockOnFiltersChange.mock.calls[0][0];
      expect(callArgs).not.toHaveProperty('opening_eco_codes');
      expect(callArgs).not.toHaveProperty('opening_names');
      expect(callArgs).not.toHaveProperty('player_matchup');
    });

    test('trims whitespace from comma-separated inputs', () => {
      render(
        <FilterPanel
          filters={mockFilters}
          onFiltersChange={mockOnFiltersChange}
          onClearFilters={mockOnClearFilters}
        />
      );

      // Expand filters
      const filterToggle = screen.getByText('Filters');
      fireEvent.click(filterToggle);

      // Set ECO codes with extra whitespace
      const ecoInput = screen.getByLabelText('ECO Codes');
      fireEvent.change(ecoInput, { target: { value: ' A00 , B01 , C20 ' } });

      // Apply filters
      const applyButton = screen.getByText('Apply Filters');
      fireEvent.click(applyButton);

      // Should trim whitespace
      expect(mockOnFiltersChange).toHaveBeenCalledWith(
        expect.objectContaining({
          opening_eco_codes: ['A00', 'B01', 'C20']
        })
      );
    });
  });
});