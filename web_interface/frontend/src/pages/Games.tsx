import React, { useState } from 'react';
import { GameListView } from '../components/GameListView';
import { FilterPanel } from '../components/FilterPanel';
import { GameListParams, SortOptions } from '../types/api';

export const Games: React.FC = () => {
  const [filters, setFilters] = useState<GameListParams>({
    page: 1,
    limit: 50,
    sort_by: SortOptions.START_TIME_DESC,
  });

  const handleFilterChange = (newFilters: GameListParams) => {
    setFilters(newFilters);
  };

  const handleClearFilters = () => {
    const newFilters: GameListParams = {
      page: 1,
    };
    
    if (filters.limit) {
      newFilters.limit = filters.limit;
    }
    
    if (filters.sort_by) {
      newFilters.sort_by = filters.sort_by;
    }
    
    setFilters(newFilters);
  };

  return (
    <div className="games-page">
      <div className="page-container">
        <div className="page-header">
          <h1 className="page-title">Games</h1>
          <p className="page-description">
            Browse and analyze completed games with detailed move-by-move analysis.
          </p>
        </div>
        
        <FilterPanel
          filters={filters}
          onFiltersChange={handleFilterChange}
          onClearFilters={handleClearFilters}
        />
        
        <GameListView 
          filters={filters}
          onFilterChange={handleFilterChange}
        />
      </div>

      <style jsx>{`
        .games-page {
          padding: 2rem 1rem;
          min-height: calc(100vh - 200px);
        }

        .page-container {
          max-width: 1200px;
          margin: 0 auto;
        }

        .page-header {
          text-align: center;
          margin-bottom: 3rem;
        }

        .page-title {
          font-size: 2rem;
          font-weight: 700;
          color: #1f2937;
          margin-bottom: 0.5rem;
        }

        .page-description {
          font-size: 1.125rem;
          color: #6b7280;
          max-width: 600px;
          margin: 0 auto;
        }
      `}</style>
    </div>
  );
};