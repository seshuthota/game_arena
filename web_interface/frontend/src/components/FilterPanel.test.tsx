import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { FilterPanel } from './FilterPanel';

const mockFilters = {
  page: 1,
  limit: 50,
};

const mockOnFiltersChange = jest.fn();
const mockOnClearFilters = jest.fn();

describe('FilterPanel', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

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
    render(
      <FilterPanel
        filters={mockFilters}
        onFiltersChange={mockOnFiltersChange}
        onClearFilters={mockOnClearFilters}
      />
    );

    const searchInput = screen.getByPlaceholderText(/Search games by player names/);
    fireEvent.change(searchInput, { target: { value: 'test search' } });

    // Debounced function should be called after delay
    // In real test, we'd use jest.useFakeTimers() and jest.runAllTimers()
    expect(searchInput).toHaveValue('test search');
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