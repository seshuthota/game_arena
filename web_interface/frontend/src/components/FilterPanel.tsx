import React, { useState, useCallback, useEffect } from 'react';
import { GameListParams, GameResult, TerminationReason } from '../types/api';

interface FilterPanelProps {
  filters: GameListParams;
  onFiltersChange: (filters: GameListParams) => void;
  onClearFilters: () => void;
}

export const FilterPanel: React.FC<FilterPanelProps> = ({
  filters,
  onFiltersChange,
  onClearFilters,
}) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [searchQuery, setSearchQuery] = useState(filters.search || '');
  
  // Local state for filter inputs
  const [localFilters, setLocalFilters] = useState({
    player_ids: filters.player_ids?.join(', ') || '',
    model_names: filters.model_names?.join(', ') || '',
    model_providers: filters.model_providers?.join(', ') || '',
    start_date: filters.start_date ? filters.start_date.split('T')[0] : '',
    end_date: filters.end_date ? filters.end_date.split('T')[0] : '',
    results: filters.results || [],
    termination_reasons: filters.termination_reasons || [],
    min_moves: filters.min_moves || '',
    max_moves: filters.max_moves || '',
    min_duration: filters.min_duration || '',
    max_duration: filters.max_duration || '',
  });

  // Debounced search function
  const debounce = useCallback((func: Function, delay: number) => {
    let timeoutId: NodeJS.Timeout;
    return (...args: any[]) => {
      clearTimeout(timeoutId);
      timeoutId = setTimeout(() => func(...args), delay);
    };
  }, []);

  // Debounced search handler
  const debouncedSearch = useCallback(
    debounce((query: string) => {
      const newFilters = {
        ...filters,
        page: 1, // Reset to first page when searching
      };
      
      if (query) {
        newFilters.search = query;
      } else {
        delete newFilters.search;
      }
      
      onFiltersChange(newFilters);
    }, 300),
    [filters, onFiltersChange]
  );

  // Handle search input change
  const handleSearchChange = (value: string) => {
    setSearchQuery(value);
    debouncedSearch(value);
  };

  // Apply filters
  const applyFilters = () => {
    const newFilters: GameListParams = {
      ...filters,
      page: 1, // Reset to first page when applying filters
    };

    // Process comma-separated lists
    if (localFilters.player_ids.trim()) {
      newFilters.player_ids = localFilters.player_ids.split(',').map(id => id.trim()).filter(id => id);
    } else {
      delete newFilters.player_ids;
    }

    if (localFilters.model_names.trim()) {
      newFilters.model_names = localFilters.model_names.split(',').map(name => name.trim()).filter(name => name);
    } else {
      delete newFilters.model_names;
    }

    if (localFilters.model_providers.trim()) {
      newFilters.model_providers = localFilters.model_providers.split(',').map(provider => provider.trim()).filter(provider => provider);
    } else {
      delete newFilters.model_providers;
    }

    // Process date filters
    if (localFilters.start_date) {
      newFilters.start_date = localFilters.start_date + 'T00:00:00Z';
    } else {
      delete newFilters.start_date;
    }

    if (localFilters.end_date) {
      newFilters.end_date = localFilters.end_date + 'T23:59:59Z';
    } else {
      delete newFilters.end_date;
    }

    // Process enum filters
    if (localFilters.results.length > 0) {
      newFilters.results = localFilters.results;
    } else {
      delete newFilters.results;
    }

    if (localFilters.termination_reasons.length > 0) {
      newFilters.termination_reasons = localFilters.termination_reasons;
    } else {
      delete newFilters.termination_reasons;
    }

    // Process numeric filters
    if (localFilters.min_moves) {
      newFilters.min_moves = Number(localFilters.min_moves);
    } else {
      delete newFilters.min_moves;
    }

    if (localFilters.max_moves) {
      newFilters.max_moves = Number(localFilters.max_moves);
    } else {
      delete newFilters.max_moves;
    }

    if (localFilters.min_duration) {
      newFilters.min_duration = Number(localFilters.min_duration);
    } else {
      delete newFilters.min_duration;
    }

    if (localFilters.max_duration) {
      newFilters.max_duration = Number(localFilters.max_duration);
    } else {
      delete newFilters.max_duration;
    }

    onFiltersChange(newFilters);
  };

  // Clear all filters
  const handleClearFilters = () => {
    setSearchQuery('');
    setLocalFilters({
      player_ids: '',
      model_names: '',
      model_providers: '',
      start_date: '',
      end_date: '',
      results: [],
      termination_reasons: [],
      min_moves: '',
      max_moves: '',
      min_duration: '',
      max_duration: '',
    });
    onClearFilters();
  };

  // Check if any filters are active
  const hasActiveFilters = Object.keys(filters).some(key => 
    key !== 'page' && key !== 'limit' && key !== 'sort_by' && filters[key as keyof GameListParams] !== undefined
  );

  // Handle checkbox changes for multi-select filters
  const handleResultsChange = (result: GameResult, checked: boolean) => {
    const newResults = checked 
      ? [...localFilters.results, result]
      : localFilters.results.filter(r => r !== result);
    
    setLocalFilters({ ...localFilters, results: newResults });
  };

  const handleTerminationReasonsChange = (reason: TerminationReason, checked: boolean) => {
    const newReasons = checked
      ? [...localFilters.termination_reasons, reason]
      : localFilters.termination_reasons.filter(r => r !== reason);
    
    setLocalFilters({ ...localFilters, termination_reasons: newReasons });
  };

  return (
    <div className="filter-panel">
      {/* Search Bar */}
      <div className="search-container">
        <div className="search-input-wrapper">
          <div className="search-icon">🔍</div>
          <input
            type="text"
            placeholder="Search games by player names, game ID, or tournament..."
            value={searchQuery}
            onChange={(e) => handleSearchChange(e.target.value)}
            className="search-input"
          />
          {searchQuery && (
            <button
              onClick={() => handleSearchChange('')}
              className="search-clear"
              aria-label="Clear search"
            >
              ✕
            </button>
          )}
        </div>
      </div>

      {/* Filter Controls */}
      <div className="filter-controls">
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="filter-toggle"
          aria-expanded={isExpanded}
        >
          <span>Filters</span>
          <span className={`filter-arrow ${isExpanded ? 'expanded' : ''}`}>▼</span>
          {hasActiveFilters && <div className="filter-indicator"></div>}
        </button>

        {hasActiveFilters && (
          <button onClick={handleClearFilters} className="clear-filters">
            Clear All
          </button>
        )}
      </div>

      {/* Expanded Filters */}
      {isExpanded && (
        <div className="filter-content">
          <div className="filter-grid">
            {/* Player Filters */}
            <div className="filter-section">
              <h4 className="filter-section-title">Players</h4>
              
              <div className="filter-field">
                <label htmlFor="player_ids" className="filter-label">Player IDs</label>
                <input
                  id="player_ids"
                  type="text"
                  placeholder="alice_gpt4, bob_claude (comma-separated)"
                  value={localFilters.player_ids}
                  onChange={(e) => setLocalFilters({ ...localFilters, player_ids: e.target.value })}
                  className="filter-input"
                />
              </div>

              <div className="filter-field">
                <label htmlFor="model_names" className="filter-label">Model Names</label>
                <input
                  id="model_names"
                  type="text"
                  placeholder="gpt-4, claude-3 (comma-separated)"
                  value={localFilters.model_names}
                  onChange={(e) => setLocalFilters({ ...localFilters, model_names: e.target.value })}
                  className="filter-input"
                />
              </div>

              <div className="filter-field">
                <label htmlFor="model_providers" className="filter-label">Model Providers</label>
                <input
                  id="model_providers"
                  type="text"
                  placeholder="openai, anthropic (comma-separated)"
                  value={localFilters.model_providers}
                  onChange={(e) => setLocalFilters({ ...localFilters, model_providers: e.target.value })}
                  className="filter-input"
                />
              </div>
            </div>

            {/* Date Filters */}
            <div className="filter-section">
              <h4 className="filter-section-title">Date Range</h4>
              
              <div className="filter-field">
                <label htmlFor="start_date" className="filter-label">Start Date</label>
                <input
                  id="start_date"
                  type="date"
                  value={localFilters.start_date}
                  onChange={(e) => setLocalFilters({ ...localFilters, start_date: e.target.value })}
                  className="filter-input"
                />
              </div>

              <div className="filter-field">
                <label htmlFor="end_date" className="filter-label">End Date</label>
                <input
                  id="end_date"
                  type="date"
                  value={localFilters.end_date}
                  onChange={(e) => setLocalFilters({ ...localFilters, end_date: e.target.value })}
                  className="filter-input"
                />
              </div>
            </div>

            {/* Game Results */}
            <div className="filter-section">
              <h4 className="filter-section-title">Game Results</h4>
              <div className="checkbox-group">
                {Object.values(GameResult).map((result) => (
                  <label key={result} className="checkbox-label">
                    <input
                      type="checkbox"
                      checked={localFilters.results.includes(result)}
                      onChange={(e) => handleResultsChange(result, e.target.checked)}
                      className="checkbox-input"
                    />
                    <span className="checkbox-text">
                      {result.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
                    </span>
                  </label>
                ))}
              </div>
            </div>

            {/* Game Metrics */}
            <div className="filter-section">
              <h4 className="filter-section-title">Game Metrics</h4>
              
              <div className="filter-row">
                <div className="filter-field">
                  <label htmlFor="min_moves" className="filter-label">Min Moves</label>
                  <input
                    id="min_moves"
                    type="number"
                    min="0"
                    placeholder="0"
                    value={localFilters.min_moves}
                    onChange={(e) => setLocalFilters({ ...localFilters, min_moves: e.target.value })}
                    className="filter-input"
                  />
                </div>

                <div className="filter-field">
                  <label htmlFor="max_moves" className="filter-label">Max Moves</label>
                  <input
                    id="max_moves"
                    type="number"
                    min="0"
                    placeholder="∞"
                    value={localFilters.max_moves}
                    onChange={(e) => setLocalFilters({ ...localFilters, max_moves: e.target.value })}
                    className="filter-input"
                  />
                </div>
              </div>

              <div className="filter-row">
                <div className="filter-field">
                  <label htmlFor="min_duration" className="filter-label">Min Duration (min)</label>
                  <input
                    id="min_duration"
                    type="number"
                    min="0"
                    step="0.1"
                    placeholder="0"
                    value={localFilters.min_duration}
                    onChange={(e) => setLocalFilters({ ...localFilters, min_duration: e.target.value })}
                    className="filter-input"
                  />
                </div>

                <div className="filter-field">
                  <label htmlFor="max_duration" className="filter-label">Max Duration (min)</label>
                  <input
                    id="max_duration"
                    type="number"
                    min="0"
                    step="0.1"
                    placeholder="∞"
                    value={localFilters.max_duration}
                    onChange={(e) => setLocalFilters({ ...localFilters, max_duration: e.target.value })}
                    className="filter-input"
                  />
                </div>
              </div>
            </div>

            {/* Termination Reasons */}
            <div className="filter-section">
              <h4 className="filter-section-title">Termination Reasons</h4>
              <div className="checkbox-group">
                {Object.values(TerminationReason).map((reason) => (
                  <label key={reason} className="checkbox-label">
                    <input
                      type="checkbox"
                      checked={localFilters.termination_reasons.includes(reason)}
                      onChange={(e) => handleTerminationReasonsChange(reason, e.target.checked)}
                      className="checkbox-input"
                    />
                    <span className="checkbox-text">
                      {reason.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                    </span>
                  </label>
                ))}
              </div>
            </div>
          </div>

          {/* Apply Filters Button */}
          <div className="filter-actions">
            <button onClick={applyFilters} className="apply-filters">
              Apply Filters
            </button>
          </div>
        </div>
      )}

      <style jsx>{`
        .filter-panel {
          background-color: #ffffff;
          border: 1px solid #e5e7eb;
          border-radius: 0.5rem;
          margin-bottom: 1.5rem;
          overflow: hidden;
        }

        .search-container {
          padding: 1rem;
          border-bottom: 1px solid #e5e7eb;
        }

        .search-input-wrapper {
          position: relative;
          display: flex;
          align-items: center;
        }

        .search-icon {
          position: absolute;
          left: 0.75rem;
          color: #6b7280;
          z-index: 1;
        }

        .search-input {
          width: 100%;
          padding: 0.75rem 0.75rem 0.75rem 2.5rem;
          border: 1px solid #d1d5db;
          border-radius: 0.5rem;
          font-size: 0.875rem;
          transition: border-color 0.2s, box-shadow 0.2s;
        }

        .search-input:focus {
          outline: none;
          border-color: #3b82f6;
          box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
        }

        .search-clear {
          position: absolute;
          right: 0.75rem;
          background: none;
          border: none;
          color: #6b7280;
          cursor: pointer;
          padding: 0.25rem;
          border-radius: 0.25rem;
          transition: color 0.2s;
        }

        .search-clear:hover {
          color: #374151;
        }

        .filter-controls {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 1rem;
          background-color: #f9fafb;
        }

        .filter-toggle {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          background: none;
          border: none;
          font-weight: 500;
          color: #374151;
          cursor: pointer;
          position: relative;
        }

        .filter-arrow {
          transition: transform 0.2s;
          color: #6b7280;
        }

        .filter-arrow.expanded {
          transform: rotate(180deg);
        }

        .filter-indicator {
          position: absolute;
          top: -2px;
          right: -8px;
          width: 8px;
          height: 8px;
          background-color: #3b82f6;
          border-radius: 50%;
        }

        .clear-filters {
          background-color: transparent;
          border: 1px solid #d1d5db;
          color: #6b7280;
          padding: 0.5rem 0.75rem;
          border-radius: 0.375rem;
          font-size: 0.875rem;
          cursor: pointer;
          transition: all 0.2s;
        }

        .clear-filters:hover {
          background-color: #f9fafb;
          border-color: #9ca3af;
        }

        .filter-content {
          padding: 1.5rem;
          border-top: 1px solid #e5e7eb;
          background-color: #ffffff;
        }

        .filter-grid {
          display: grid;
          gap: 1.5rem;
          grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
        }

        .filter-section {
        }

        .filter-section-title {
          font-size: 0.875rem;
          font-weight: 600;
          color: #1f2937;
          margin-bottom: 0.75rem;
          padding-bottom: 0.5rem;
          border-bottom: 1px solid #e5e7eb;
        }

        .filter-field {
          margin-bottom: 0.75rem;
        }

        .filter-row {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 0.75rem;
        }

        .filter-label {
          display: block;
          font-size: 0.8125rem;
          font-weight: 500;
          color: #374151;
          margin-bottom: 0.25rem;
        }

        .filter-input {
          width: 100%;
          padding: 0.5rem 0.75rem;
          border: 1px solid #d1d5db;
          border-radius: 0.375rem;
          font-size: 0.875rem;
          transition: border-color 0.2s, box-shadow 0.2s;
        }

        .filter-input:focus {
          outline: none;
          border-color: #3b82f6;
          box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
        }

        .checkbox-group {
          display: flex;
          flex-direction: column;
          gap: 0.5rem;
        }

        .checkbox-label {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          cursor: pointer;
        }

        .checkbox-input {
          margin: 0;
        }

        .checkbox-text {
          font-size: 0.875rem;
          color: #374151;
        }

        .filter-actions {
          margin-top: 1.5rem;
          padding-top: 1.5rem;
          border-top: 1px solid #e5e7eb;
          display: flex;
          justify-content: center;
        }

        .apply-filters {
          background-color: #3b82f6;
          color: #ffffff;
          border: none;
          padding: 0.75rem 2rem;
          border-radius: 0.5rem;
          font-weight: 500;
          cursor: pointer;
          transition: background-color 0.2s;
        }

        .apply-filters:hover {
          background-color: #2563eb;
        }

        @media (max-width: 768px) {
          .filter-grid {
            grid-template-columns: 1fr;
          }

          .filter-row {
            grid-template-columns: 1fr;
          }
        }
      `}</style>
    </div>
  );
};