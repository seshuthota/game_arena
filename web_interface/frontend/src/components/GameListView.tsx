import React, { useState, useMemo, useCallback, memo } from 'react';
import { Link } from 'react-router-dom';
import { useGames, cacheUtils } from '../hooks/useApi';
import { GameListParams, GameSummary, SortOptions } from '../types/api';
import { VirtualizedGameList } from './VirtualizedGameList';
import { GameListSkeleton } from './LoadingSkeleton';
import { GameListErrorBoundary } from './ErrorBoundary';
import { LoadingButton } from './LoadingStates';
import { GameCard } from './GameCard';
import { useQueryClient } from '@tanstack/react-query';
import { 
  usePerformanceMonitor, 
  useStableCallback, 
  useIntersectionObserver
} from '../utils/performanceOptimizations';

interface GameListViewProps {
  filters?: GameListParams;
  onFilterChange?: (filters: GameListParams) => void;
  enableVirtualScrolling?: boolean;
  virtualListHeight?: number;
}

export const GameListView: React.FC<GameListViewProps> = ({ 
  filters = {}, 
  onFilterChange,
  enableVirtualScrolling = false,
  virtualListHeight = 600 
}) => {
  // Performance monitoring
  usePerformanceMonitor('GameListView');
  const [page, setPage] = useState(filters.page || 1);
  const [limit, setLimit] = useState(enableVirtualScrolling ? 100 : filters.limit || 50);
  const [sortBy, setSortBy] = useState(filters.sort_by || SortOptions.START_TIME_DESC);
  const queryClient = useQueryClient();

  // Combine all filters for the API call
  const apiFilters = useMemo(() => ({
    ...filters,
    page,
    limit,
    sort_by: sortBy,
  }), [filters, page, limit, sortBy]);

  const { 
    data: gamesData, 
    isLoading, 
    error, 
    refetch 
  } = useGames(apiFilters) as { data: any, isLoading: boolean, error: unknown, refetch: () => void };

  // Extract data for easier access
  const games = gamesData?.games || [];
  const pagination = gamesData?.pagination;

  // Optimized event handlers with useStableCallback
  const handlePageChange = useStableCallback((newPage: number) => {
    setPage(newPage);
    onFilterChange?.({ ...filters, page: newPage });
  }, [filters, onFilterChange]);

  const handleLimitChange = useStableCallback((newLimit: number) => {
    setLimit(newLimit);
    setPage(1); // Reset to first page when changing limit
    onFilterChange?.({ ...filters, limit: newLimit, page: 1 });
  }, [filters, onFilterChange]);

  const handleSortChange = useStableCallback((newSort: SortOptions) => {
    setSortBy(newSort);
    onFilterChange?.({ ...filters, sort_by: newSort });
  }, [filters, onFilterChange]);

  // Optimized load more for virtual scrolling
  const loadMore = useStableCallback(async () => {
    if (enableVirtualScrolling && pagination?.has_next) {
      const nextPage = page + 1;
      setPage(nextPage);
      
      // Prefetch next batch of games with error handling
      try {
        await cacheUtils.prefetchGames(queryClient, {
          ...apiFilters,
          page: nextPage
        });
      } catch (error) {
        if (process.env.NODE_ENV === 'development') {
          console.warn('Failed to prefetch games:', error);
        }
      }
    }
  }, [enableVirtualScrolling, pagination?.has_next, page, apiFilters, queryClient]);

  // For virtual scrolling, we accumulate all games from all pages
  const allGames = useMemo(() => {
    if (!enableVirtualScrolling) return games;
    
    // In a real implementation, you'd want to accumulate games from all loaded pages
    // This is a simplified version - you might need a more sophisticated approach
    return games;
  }, [games, enableVirtualScrolling]);

  // Loading State
  if (isLoading && !gamesData) {
    return (
      <div className="game-list-view">
        <GameListSkeleton />
      </div>
    );
  }

  // Error State
  if (error) {
    return (
      <div className="game-list-view">
        <div className="error-container">
          <div className="error-icon">⚠️</div>
          <h3 className="error-title">Failed to load games</h3>
          <p className="error-message">
            {error instanceof Error ? error.message : 'An unexpected error occurred'}
          </p>
          <button onClick={() => refetch()} className="retry-button">
            Try Again
          </button>
        </div>
        <style jsx>{`
          .game-list-view {
            padding: 1rem;
          }

          @media (min-width: 640px) {
            .game-list-view {
              padding: 1.5rem;
            }
          }

          @media (min-width: 1024px) {
            .game-list-view {
              padding: 2rem;
            }
          }

          .error-container {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 2rem 1rem;
            text-align: center;
            background-color: #fef2f2;
            border: 1px solid #fecaca;
            border-radius: 0.75rem;
            margin: 0 auto;
            max-width: 600px;
          }

          @media (min-width: 640px) {
            .error-container {
              padding: 3rem 2rem;
            }
          }

          @media (min-width: 1024px) {
            .error-container {
              padding: 4rem 2rem;
            }
          }

          .error-icon {
            font-size: 2.5rem;
            margin-bottom: 1rem;
          }

          @media (min-width: 640px) {
            .error-icon {
              font-size: 3rem;
            }
          }

          .error-title {
            font-size: 1.25rem;
            font-weight: 600;
            color: #dc2626;
            margin: 0 0 0.5rem 0;
          }

          @media (min-width: 640px) {
            .error-title {
              font-size: 1.5rem;
            }
          }

          .error-message {
            color: #7f1d1d;
            margin-bottom: 1.5rem;
            max-width: 500px;
            line-height: 1.5;
          }

          .retry-button {
            background-color: #dc2626;
            color: white;
            border: none;
            padding: 0.75rem 1.5rem;
            border-radius: 0.5rem;
            font-weight: 500;
            cursor: pointer;
            transition: background-color 0.2s;
          }

          .retry-button:hover {
            background-color: #b91c1c;
          }
        `}</style>
      </div>
    );
  }

  // Empty State
  if (gamesData && gamesData.games.length === 0) {
    return (
      <div className="game-list-view">
        <div className="empty-container">
          <div className="empty-icon">🎯</div>
          <h3 className="empty-title">No games found</h3>
          <p className="empty-message">
            {Object.keys(filters).length > 2 ? (
              'Try adjusting your filters to see more results.'
            ) : (
              'No games have been played yet. Start a game to see results here.'
            )}
          </p>
        </div>
        <style jsx>{`
          .game-list-view {
            padding: 1rem;
          }

          @media (min-width: 640px) {
            .game-list-view {
              padding: 1.5rem;
            }
          }

          @media (min-width: 1024px) {
            .game-list-view {
              padding: 2rem;
            }
          }

          .empty-container {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 2rem 1rem;
            text-align: center;
            margin: 0 auto;
            max-width: 600px;
          }

          @media (min-width: 640px) {
            .empty-container {
              padding: 3rem 2rem;
            }
          }

          @media (min-width: 1024px) {
            .empty-container {
              padding: 4rem 2rem;
            }
          }
            background-color: #f9fafb;
            border: 2px dashed #e5e7eb;
            border-radius: 0.75rem;
          }

          .empty-icon {
            font-size: 3rem;
            margin-bottom: 1rem;
          }

          .empty-title {
            font-size: 1.5rem;
            font-weight: 600;
            color: #1f2937;
            margin-bottom: 0.5rem;
          }

          .empty-message {
            color: #6b7280;
            max-width: 400px;
            line-height: 1.5;
            margin: 0;
          }
        `}</style>
      </div>
    );
  }


  return (
    <GameListErrorBoundary>
      <div className="game-list-view">

        {/* Controls */}
        <div className="controls-bar">
        <div className="results-info">
          {pagination && (
            <span className="results-count">
              Showing {((pagination.page - 1) * pagination.limit) + 1}-{Math.min(pagination.page * pagination.limit, pagination.total_count)} of {pagination.total_count} games
            </span>
          )}
        </div>

        <div className="controls-group">
          {/* Sort Control */}
          <div className="control-item">
            <label htmlFor="sort-select" className="control-label">Sort by:</label>
            <select
              id="sort-select"
              value={sortBy}
              onChange={(e) => handleSortChange(e.target.value as SortOptions)}
              className="control-select"
            >
              <option value={SortOptions.START_TIME_DESC}>Newest First</option>
              <option value={SortOptions.START_TIME_ASC}>Oldest First</option>
              <option value={SortOptions.DURATION_DESC}>Longest Games</option>
              <option value={SortOptions.DURATION_ASC}>Shortest Games</option>
              <option value={SortOptions.MOVES_DESC}>Most Moves</option>
              <option value={SortOptions.MOVES_ASC}>Fewest Moves</option>
            </select>
          </div>

          {/* Items per page */}
          <div className="control-item">
            <label htmlFor="limit-select" className="control-label">Show:</label>
            <select
              id="limit-select"
              value={limit}
              onChange={(e) => handleLimitChange(Number(e.target.value))}
              className="control-select"
            >
              <option value={25}>25</option>
              <option value={50}>50</option>
              <option value={100}>100</option>
            </select>
          </div>
        </div>
      </div>

      {/* Games Display - Virtual or Card-based Layout */}
      {enableVirtualScrolling ? (
        <VirtualizedGameList
          games={allGames}
          isLoading={isLoading}
          hasNextPage={pagination?.has_next || false}
          loadMore={loadMore}
          height={virtualListHeight}
          className="virtual-games-container"
        />
      ) : (
        <div className="games-grid-container">
          <div className="games-grid">
            {games.map((game: GameSummary) => (
              <GameCard key={game.game_id} game={game} />
            ))}
          </div>
        </div>
      )}

      {/* Pagination - Only show for traditional table view */}
      {!enableVirtualScrolling && pagination && pagination.total_pages > 1 && (
        <div className="pagination-container">
          <PaginationControls
            currentPage={pagination.page}
            totalPages={pagination.total_pages}
            hasNext={pagination.has_next}
            hasPrevious={pagination.has_previous}
            onPageChange={handlePageChange}
          />
        </div>
      )}

      {/* Loading overlay for subsequent loads */}
      {isLoading && (
        <div className="loading-overlay">
          <div className="loading-spinner-small"></div>
        </div>
      )}

      <style jsx>{`
        .game-list-view {
          position: relative;
        }

        .controls-bar {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 1.5rem;
          padding: 1rem;
          background-color: #ffffff;
          border: 1px solid #e5e7eb;
          border-radius: 0.5rem;
          flex-wrap: wrap;
          gap: 1rem;
        }

        .results-info {
          font-size: 0.875rem;
          color: #6b7280;
        }

        .controls-group {
          display: flex;
          gap: 1rem;
          align-items: center;
        }

        .control-item {
          display: flex;
          align-items: center;
          gap: 0.5rem;
        }

        .control-label {
          font-size: 0.875rem;
          font-weight: 500;
          color: #374151;
        }

        .control-select {
          padding: 0.5rem;
          border: 1px solid #d1d5db;
          border-radius: 0.375rem;
          background-color: #ffffff;
          font-size: 0.875rem;
          cursor: pointer;
        }

        .control-select:focus {
          outline: none;
          border-color: #3b82f6;
          box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
        }

        .games-grid-container {
          margin-bottom: 1.5rem;
        }

        .games-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
          gap: 1.5rem;
          padding: 0;
        }

        .virtual-games-container {
          margin: 0;
        }

        @media (max-width: 640px) {
          .games-grid {
            grid-template-columns: 1fr;
            gap: 1rem;
          }
        }

        @media (min-width: 1024px) {
          .games-grid {
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 2rem;
          }
        }

        .pagination-container {
          margin-top: 1.5rem;
          display: flex;
          justify-content: center;
        }

        .loading-overlay {
          position: absolute;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          background-color: rgba(255, 255, 255, 0.8);
          display: flex;
          align-items: center;
          justify-content: center;
        }

        .loading-spinner-small {
          width: 24px;
          height: 24px;
          border: 2px solid #e5e7eb;
          border-top: 2px solid #3b82f6;
          border-radius: 50%;
          animation: spin 1s linear infinite;
        }

        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }

        @media (max-width: 768px) {
          .controls-bar {
            flex-direction: column;
            align-items: stretch;
          }

          .controls-group {
            justify-content: space-between;
          }

          .games-table-scroll {
            -webkit-overflow-scrolling: touch;
          }
        }
      `}</style>
      </div>
    </GameListErrorBoundary>
  );
};



// Pagination Controls Component
interface PaginationControlsProps {
  currentPage: number;
  totalPages: number;
  hasNext: boolean;
  hasPrevious: boolean;
  onPageChange: (page: number) => void;
}

const PaginationControls: React.FC<PaginationControlsProps> = ({
  currentPage,
  totalPages,
  hasNext,
  hasPrevious,
  onPageChange,
}) => {
  const getPageNumbers = () => {
    const delta = 2;
    const pages = [];
    const left = Math.max(1, currentPage - delta);
    const right = Math.min(totalPages, currentPage + delta);

    // Always show first page
    if (left > 1) {
      pages.push(1);
      if (left > 2) pages.push('...');
    }

    // Show pages around current
    for (let i = left; i <= right; i++) {
      pages.push(i);
    }

    // Always show last page
    if (right < totalPages) {
      if (right < totalPages - 1) pages.push('...');
      pages.push(totalPages);
    }

    return pages;
  };

  return (
    <div className="pagination">
      <button
        onClick={() => onPageChange(currentPage - 1)}
        disabled={!hasPrevious}
        className="pagination-button"
      >
        ← Previous
      </button>

      <div className="pagination-pages">
        {getPageNumbers().map((page, index) => (
          page === '...' ? (
            <span key={index} className="pagination-ellipsis">...</span>
          ) : (
            <button
              key={index}
              onClick={() => onPageChange(page as number)}
              className={`pagination-number ${page === currentPage ? 'active' : ''}`}
            >
              {page}
            </button>
          )
        ))}
      </div>

      <button
        onClick={() => onPageChange(currentPage + 1)}
        disabled={!hasNext}
        className="pagination-button"
      >
        Next →
      </button>

      <style jsx>{`
        .pagination {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          flex-wrap: wrap;
        }

        .pagination-button {
          padding: 0.5rem 1rem;
          border: 1px solid #d1d5db;
          background-color: #ffffff;
          color: #374151;
          border-radius: 0.375rem;
          font-size: 0.875rem;
          font-weight: 500;
          cursor: pointer;
          transition: all 0.2s;
        }

        .pagination-button:hover:not(:disabled) {
          background-color: #f9fafb;
          border-color: #9ca3af;
        }

        .pagination-button:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        .pagination-pages {
          display: flex;
          gap: 0.25rem;
        }

        .pagination-number {
          padding: 0.5rem 0.75rem;
          border: 1px solid #d1d5db;
          background-color: #ffffff;
          color: #374151;
          border-radius: 0.375rem;
          font-size: 0.875rem;
          cursor: pointer;
          transition: all 0.2s;
          min-width: 2.5rem;
        }

        .pagination-number:hover {
          background-color: #f3f4f6;
        }

        .pagination-number.active {
          background-color: #3b82f6;
          color: #ffffff;
          border-color: #3b82f6;
        }

        .pagination-ellipsis {
          padding: 0.5rem 0.25rem;
          color: #9ca3af;
        }

        @media (max-width: 640px) {
          .pagination {
            justify-content: center;
          }
        }
      `}</style>
    </div>
  );
};