import React, { useState } from 'react';
import { useLeaderboard } from '../hooks/useApi';
import { PlayerRanking, SortOptions } from '../types/api';

interface LeaderboardViewProps {
  className?: string;
}

interface PlayerDetailModalProps {
  player: PlayerRanking | null;
  isOpen: boolean;
  onClose: () => void;
}

export const LeaderboardView: React.FC<LeaderboardViewProps> = ({ className }) => {
  const [sortBy, setSortBy] = useState<SortOptions>(SortOptions.ELO_RATING_DESC);
  const [page, setPage] = useState(1);
  const [selectedPlayer, setSelectedPlayer] = useState<PlayerRanking | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [minGames, setMinGames] = useState(1);
  const [modelProviderFilter, setModelProviderFilter] = useState<string>('');
  const [modelNameFilter, setModelNameFilter] = useState<string>('');
  const [timePeriod, setTimePeriod] = useState<'all' | '30d' | '7d'>('all');
  const limit = 20;

  const leaderboardParams: {
    page: number;
    limit: number;
    sort_by: SortOptions;
    min_games: number;
    model_providers?: string;
    model_names?: string;
  } = {
    page,
    limit,
    sort_by: sortBy,
    min_games: minGames,
  };

  if (modelProviderFilter) {
    leaderboardParams.model_providers = modelProviderFilter;
  }
  
  if (modelNameFilter) {
    leaderboardParams.model_names = modelNameFilter;
  }

  const {
    data: leaderboardData,
    isLoading,
    error,
    refetch
  } = useLeaderboard(leaderboardParams) as { data: any, isLoading: boolean, error: unknown, refetch: () => void };

  const handleSort = (newSortBy: SortOptions) => {
    setSortBy(newSortBy);
    setPage(1); // Reset to first page when sorting changes
  };

  const handlePlayerClick = (player: PlayerRanking) => {
    setSelectedPlayer(player);
    setIsModalOpen(true);
  };

  const handlePageChange = (newPage: number) => {
    if (newPage >= 1 && leaderboardData?.pagination && newPage <= leaderboardData.pagination.total_pages) {
      setPage(newPage);
    }
  };

  const handleFilterChange = () => {
    setPage(1); // Reset to first page when filters change
  };

  const handleMinGamesChange = (value: number) => {
    setMinGames(value);
    handleFilterChange();
  };

  const handleModelProviderChange = (value: string) => {
    setModelProviderFilter(value);
    handleFilterChange();
  };

  const handleModelNameChange = (value: string) => {
    setModelNameFilter(value);
    handleFilterChange();
  };

  const handleTimePeriodChange = (value: 'all' | '30d' | '7d') => {
    setTimePeriod(value);
    handleFilterChange();
  };

  const clearFilters = () => {
    setMinGames(1);
    setModelProviderFilter('');
    setModelNameFilter('');
    setTimePeriod('all');
    setPage(1);
  };

  // Loading state
  if (isLoading) {
    return (
      <div className={`leaderboard-view ${className || ''}`}>
        <div className="loading-container">
          <div className="loading-spinner"></div>
          <p className="loading-text">Loading leaderboard...</p>
        </div>
        <style jsx>{`
          .leaderboard-view {
            padding: 1rem 0;
          }

          .loading-container {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 4rem 2rem;
            text-align: center;
          }

          .loading-spinner {
            width: 40px;
            height: 40px;
            border: 4px solid #e5e7eb;
            border-top: 4px solid #3b82f6;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin-bottom: 1rem;
          }

          @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
          }

          .loading-text {
            color: #6b7280;
            font-size: 1.125rem;
            margin: 0;
          }
        `}</style>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className={`leaderboard-view ${className || ''}`}>
        <div className="error-container">
          <div className="error-icon">⚠️</div>
          <h3 className="error-title">Failed to load leaderboard</h3>
          <p className="error-message">
            {error instanceof Error ? error.message : 'An unexpected error occurred'}
          </p>
          <button onClick={() => refetch()} className="retry-button">
            Try Again
          </button>
        </div>
        <style jsx>{`
          .leaderboard-view {
            padding: 1rem 0;
          }

          .error-container {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 4rem 2rem;
            text-align: center;
            background-color: #fef2f2;
            border: 1px solid #fecaca;
            border-radius: 0.75rem;
          }

          .error-icon {
            font-size: 3rem;
            margin-bottom: 1rem;
          }

          .error-title {
            font-size: 1.5rem;
            font-weight: 600;
            color: #dc2626;
            margin-bottom: 0.5rem;
          }

          .error-message {
            color: #7f1d1d;
            margin-bottom: 2rem;
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

  const players = leaderboardData?.players || [];
  const pagination = leaderboardData?.pagination;

  return (
    <div className={`leaderboard-view ${className || ''}`}>
      {/* Filter and Sort Controls */}
      <div className="controls-container">
        <div className="filter-controls">
          <h3 className="controls-title">Filters & Sort</h3>
          
          <div className="controls-grid">
            {/* Sort Control */}
            <div className="control-group">
              <label htmlFor="sort-select" className="control-label">Sort by:</label>
              <select
                id="sort-select"
                value={sortBy}
                onChange={(e) => handleSort(e.target.value as SortOptions)}
                className="control-select"
              >
                <option value={SortOptions.ELO_RATING_DESC}>ELO Rating (High to Low)</option>
                <option value={SortOptions.ELO_RATING_ASC}>ELO Rating (Low to High)</option>
                <option value={SortOptions.WIN_RATE_DESC}>Win Rate (High to Low)</option>
                <option value={SortOptions.WIN_RATE_ASC}>Win Rate (Low to High)</option>
                <option value={SortOptions.GAMES_PLAYED_DESC}>Games Played (Most to Least)</option>
                <option value={SortOptions.GAMES_PLAYED_ASC}>Games Played (Least to Most)</option>
              </select>
            </div>

            {/* Minimum Games Filter */}
            <div className="control-group">
              <label htmlFor="min-games-select" className="control-label">Min Games:</label>
              <select
                id="min-games-select"
                value={minGames}
                onChange={(e) => handleMinGamesChange(parseInt(e.target.value))}
                className="control-select"
              >
                <option value={1}>1+ games</option>
                <option value={5}>5+ games</option>
                <option value={10}>10+ games</option>
                <option value={25}>25+ games</option>
                <option value={50}>50+ games</option>
              </select>
            </div>

            {/* Model Provider Filter */}
            <div className="control-group">
              <label htmlFor="provider-filter" className="control-label">Provider:</label>
              <select
                id="provider-filter"
                value={modelProviderFilter}
                onChange={(e) => handleModelProviderChange(e.target.value)}
                className="control-select"
              >
                <option value="">All Providers</option>
                <option value="openai">OpenAI</option>
                <option value="anthropic">Anthropic</option>
                <option value="google">Google</option>
                <option value="openrouter">OpenRouter</option>
                <option value="togetherai">TogetherAI</option>
                <option value="xai">XAI</option>
              </select>
            </div>

            {/* Time Period Filter */}
            <div className="control-group">
              <label htmlFor="time-period-select" className="control-label">Period:</label>
              <select
                id="time-period-select"
                value={timePeriod}
                onChange={(e) => handleTimePeriodChange(e.target.value as 'all' | '30d' | '7d')}
                className="control-select"
              >
                <option value="all">All Time</option>
                <option value="30d">Last 30 Days</option>
                <option value="7d">Last 7 Days</option>
              </select>
            </div>

            {/* Model Name Search */}
            <div className="control-group">
              <label htmlFor="model-name-filter" className="control-label">Model Name:</label>
              <input
                id="model-name-filter"
                type="text"
                value={modelNameFilter}
                onChange={(e) => handleModelNameChange(e.target.value)}
                placeholder="Search models..."
                className="control-input"
              />
            </div>

            {/* Clear Filters Button */}
            <div className="control-group">
              <button
                onClick={clearFilters}
                className="clear-filters-button"
                title="Clear all filters"
              >
                Clear Filters
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Leaderboard Table */}
      <div className="table-container">
        <table className="leaderboard-table">
          <thead>
            <tr>
              <th className="rank-header">Rank</th>
              <th className="player-header">Player</th>
              <th className="elo-header">ELO</th>
              <th className="games-header">Games</th>
              <th className="record-header">W/L/D</th>
              <th className="winrate-header">Win Rate</th>
              <th className="avg-length-header">Avg Length</th>
            </tr>
          </thead>
          <tbody>
            {players.map((player: any) => (
              <tr 
                key={player.player_id} 
                className="player-row"
                onClick={() => handlePlayerClick(player)}
              >
                <td className="rank-cell">#{player.rank}</td>
                <td className="player-cell">
                  <div className="player-info">
                    <div className="player-name">{player.model_name}</div>
                    <div className="player-id">{player.player_id}</div>
                  </div>
                </td>
                <td className="elo-cell">
                  <span className="elo-rating">{Math.round(player.elo_rating)}</span>
                </td>
                <td className="games-cell">{player.games_played}</td>
                <td className="record-cell">
                  <span className="record-stats">
                    <span className="wins">{player.wins}</span>/
                    <span className="losses">{player.losses}</span>/
                    <span className="draws">{player.draws}</span>
                  </span>
                </td>
                <td className="winrate-cell">
                  <span className="win-percentage">{(player.win_rate * 100).toFixed(1)}%</span>
                </td>
                <td className="avg-length-cell">{player.average_game_length.toFixed(0)} moves</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {pagination && pagination.total_pages > 1 && (
        <div className="pagination">
          <button
            onClick={() => handlePageChange(page - 1)}
            disabled={!pagination.has_previous}
            className="pagination-button"
          >
            ← Previous
          </button>
          
          <div className="pagination-info">
            Page {pagination.page} of {pagination.total_pages}
            <span className="total-count">({pagination.total_count} players)</span>
          </div>
          
          <button
            onClick={() => handlePageChange(page + 1)}
            disabled={!pagination.has_next}
            className="pagination-button"
          >
            Next →
          </button>
        </div>
      )}

      {/* Player Detail Modal */}
      <PlayerDetailModal
        player={selectedPlayer}
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
      />

      <style jsx>{`
        .leaderboard-view {
          display: flex;
          flex-direction: column;
          gap: 1.5rem;
        }

        .controls-container {
          background-color: #f8fafc;
          border: 1px solid #e5e7eb;
          border-radius: 0.75rem;
          padding: 1.5rem;
          margin-bottom: 1.5rem;
        }

        .filter-controls {
          width: 100%;
        }

        .controls-title {
          font-size: 1.125rem;
          font-weight: 600;
          color: #1f2937;
          margin: 0 0 1rem 0;
        }

        .controls-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
          gap: 1rem;
          align-items: end;
        }

        .control-group {
          display: flex;
          flex-direction: column;
          gap: 0.5rem;
        }

        .control-label {
          font-size: 0.875rem;
          font-weight: 500;
          color: #374151;
        }

        .control-select, 
        .control-input {
          padding: 0.75rem;
          border: 1px solid #d1d5db;
          border-radius: 0.375rem;
          background-color: white;
          font-size: 0.875rem;
          transition: border-color 0.2s, box-shadow 0.2s;
        }

        .control-select {
          cursor: pointer;
        }

        .control-select:focus,
        .control-input:focus {
          outline: none;
          border-color: #3b82f6;
          box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
        }

        .control-input::placeholder {
          color: #9ca3af;
        }

        .clear-filters-button {
          background-color: #6b7280;
          color: white;
          border: none;
          padding: 0.75rem 1rem;
          border-radius: 0.375rem;
          font-size: 0.875rem;
          font-weight: 500;
          cursor: pointer;
          transition: background-color 0.2s;
        }

        .clear-filters-button:hover {
          background-color: #4b5563;
        }

        .table-container {
          background-color: white;
          border-radius: 0.75rem;
          box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
          overflow: hidden;
        }

        .leaderboard-table {
          width: 100%;
          border-collapse: collapse;
        }

        .leaderboard-table th {
          background-color: #f8fafc;
          padding: 1rem;
          text-align: left;
          font-weight: 600;
          color: #374151;
          border-bottom: 1px solid #e5e7eb;
        }

        .leaderboard-table td {
          padding: 1rem;
          border-bottom: 1px solid #f3f4f6;
        }

        .player-row {
          cursor: pointer;
          transition: background-color 0.2s;
        }

        .player-row:hover {
          background-color: #f8fafc;
        }

        .player-row:last-child td {
          border-bottom: none;
        }

        .rank-cell {
          font-weight: 600;
          color: #1f2937;
          text-align: center;
          width: 80px;
        }

        .player-info {
          display: flex;
          flex-direction: column;
          gap: 0.25rem;
        }

        .player-name {
          font-weight: 600;
          color: #1f2937;
        }

        .player-id {
          font-size: 0.75rem;
          color: #6b7280;
          font-family: monospace;
        }

        .elo-rating {
          font-weight: 600;
          color: #7c3aed;
          font-size: 1.125rem;
        }

        .record-stats {
          font-family: monospace;
          font-size: 0.875rem;
        }

        .wins {
          color: #059669;
          font-weight: 600;
        }

        .losses {
          color: #dc2626;
          font-weight: 600;
        }

        .draws {
          color: #f59e0b;
          font-weight: 600;
        }

        .win-percentage {
          font-weight: 600;
          color: #1f2937;
        }

        .pagination {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 1rem;
          background-color: white;
          border-radius: 0.5rem;
          box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
        }

        .pagination-button {
          padding: 0.5rem 1rem;
          background-color: #3b82f6;
          color: white;
          border: none;
          border-radius: 0.375rem;
          cursor: pointer;
          font-weight: 500;
          transition: background-color 0.2s;
        }

        .pagination-button:hover:not(:disabled) {
          background-color: #2563eb;
        }

        .pagination-button:disabled {
          background-color: #d1d5db;
          cursor: not-allowed;
        }

        .pagination-info {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 0.25rem;
          font-weight: 500;
          color: #374151;
        }

        .total-count {
          font-size: 0.875rem;
          color: #6b7280;
          font-weight: 400;
        }

        /* Responsive Design */
        @media (max-width: 1024px) {
          .controls-grid {
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
          }
        }

        @media (max-width: 768px) {
          .controls-container {
            padding: 1rem;
          }

          .controls-grid {
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 0.75rem;
          }

          .control-select, 
          .control-input {
            padding: 0.625rem;
            font-size: 0.75rem;
          }

          .clear-filters-button {
            padding: 0.625rem 0.75rem;
            font-size: 0.75rem;
          }

          .leaderboard-table {
            font-size: 0.875rem;
          }

          .leaderboard-table th,
          .leaderboard-table td {
            padding: 0.75rem 0.5rem;
          }

          .player-info {
            gap: 0.125rem;
          }

          .player-name {
            font-size: 0.875rem;
          }

          .player-id {
            font-size: 0.625rem;
          }

          .pagination {
            flex-direction: column;
            gap: 1rem;
          }

          .pagination-info {
            order: -1;
          }
        }

        /* Hide less important columns on small screens */
        @media (max-width: 640px) {
          .controls-grid {
            grid-template-columns: 1fr 1fr;
          }

          .avg-length-header,
          .avg-length-cell {
            display: none;
          }
        }

        @media (max-width: 480px) {
          .controls-grid {
            grid-template-columns: 1fr;
          }

          .controls-container {
            padding: 0.75rem;
          }

          .games-header,
          .games-cell {
            display: none;
          }
        }
      `}</style>
    </div>
  );
};

// Player Detail Modal Component
const PlayerDetailModal: React.FC<PlayerDetailModalProps> = ({ player, isOpen, onClose }) => {
  if (!isOpen || !player) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2 className="modal-title">Player Details</h2>
          <button onClick={onClose} className="close-button">×</button>
        </div>
        
        <div className="modal-body">
          <div className="player-summary">
            <h3 className="player-name">{player.model_name}</h3>
            <p className="player-id-modal">{player.player_id}</p>
            <div className="rank-badge">Rank #{player.rank}</div>
          </div>

          <div className="stats-grid">
            <div className="stat-item">
              <div className="stat-label">ELO Rating</div>
              <div className="stat-value elo">{Math.round(player.elo_rating)}</div>
            </div>
            
            <div className="stat-item">
              <div className="stat-label">Games Played</div>
              <div className="stat-value">{player.games_played}</div>
            </div>

            <div className="stat-item">
              <div className="stat-label">Win Rate</div>
              <div className="stat-value win-rate">{(player.win_rate * 100).toFixed(1)}%</div>
            </div>

            <div className="stat-item">
              <div className="stat-label">Wins</div>
              <div className="stat-value wins">{player.wins}</div>
            </div>

            <div className="stat-item">
              <div className="stat-label">Losses</div>
              <div className="stat-value losses">{player.losses}</div>
            </div>

            <div className="stat-item">
              <div className="stat-label">Draws</div>
              <div className="stat-value draws">{player.draws}</div>
            </div>

            <div className="stat-item full-width">
              <div className="stat-label">Average Game Length</div>
              <div className="stat-value">{player.average_game_length.toFixed(0)} moves</div>
            </div>
          </div>
        </div>
      </div>

      <style jsx>{`
        .modal-overlay {
          position: fixed;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          background-color: rgba(0, 0, 0, 0.5);
          display: flex;
          align-items: center;
          justify-content: center;
          z-index: 1000;
          padding: 1rem;
        }

        .modal-content {
          background-color: white;
          border-radius: 0.75rem;
          max-width: 500px;
          width: 100%;
          max-height: 90vh;
          overflow-y: auto;
          box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
        }

        .modal-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 1.5rem 1.5rem 0 1.5rem;
          border-bottom: 1px solid #e5e7eb;
          margin-bottom: 1.5rem;
          padding-bottom: 1rem;
        }

        .modal-title {
          font-size: 1.5rem;
          font-weight: 600;
          color: #1f2937;
          margin: 0;
        }

        .close-button {
          background: none;
          border: none;
          font-size: 1.5rem;
          cursor: pointer;
          padding: 0.25rem;
          color: #6b7280;
          width: 32px;
          height: 32px;
          display: flex;
          align-items: center;
          justify-content: center;
          border-radius: 0.25rem;
          transition: all 0.2s;
        }

        .close-button:hover {
          background-color: #f3f4f6;
          color: #374151;
        }

        .modal-body {
          padding: 0 1.5rem 1.5rem 1.5rem;
        }

        .player-summary {
          text-align: center;
          margin-bottom: 2rem;
        }

        .player-name {
          font-size: 1.25rem;
          font-weight: 600;
          color: #1f2937;
          margin-bottom: 0.5rem;
        }

        .player-id-modal {
          font-family: monospace;
          font-size: 0.875rem;
          color: #6b7280;
          margin-bottom: 1rem;
        }

        .rank-badge {
          display: inline-block;
          background-color: #3b82f6;
          color: white;
          padding: 0.5rem 1rem;
          border-radius: 9999px;
          font-weight: 600;
          font-size: 0.875rem;
        }

        .stats-grid {
          display: grid;
          grid-template-columns: repeat(2, 1fr);
          gap: 1rem;
        }

        .stat-item {
          text-align: center;
          padding: 1rem;
          background-color: #f8fafc;
          border-radius: 0.5rem;
        }

        .stat-item.full-width {
          grid-column: 1 / -1;
        }

        .stat-label {
          font-size: 0.875rem;
          color: #6b7280;
          margin-bottom: 0.5rem;
        }

        .stat-value {
          font-size: 1.5rem;
          font-weight: 700;
          color: #1f2937;
        }

        .stat-value.elo {
          color: #7c3aed;
        }

        .stat-value.win-rate {
          color: #059669;
        }

        .stat-value.wins {
          color: #059669;
        }

        .stat-value.losses {
          color: #dc2626;
        }

        .stat-value.draws {
          color: #f59e0b;
        }

        @media (max-width: 480px) {
          .modal-content {
            margin: 0.5rem;
          }

          .stats-grid {
            grid-template-columns: 1fr;
          }

          .stat-item.full-width {
            grid-column: 1;
          }
        }
      `}</style>
    </div>
  );
};