import React, { useMemo, useCallback, memo } from 'react';
import { FixedSizeList as List } from 'react-window';
import InfiniteLoader from 'react-window-infinite-loader';
import { Link } from 'react-router-dom';
import { GameSummary } from '../types/api';

interface VirtualizedGameListProps {
  games: GameSummary[];
  isLoading: boolean;
  hasNextPage: boolean;
  loadMore: () => void;
  itemHeight?: number;
  height?: number;
  className?: string;
}

interface GameRowProps {
  index: number;
  style: React.CSSProperties;
  data: {
    games: GameSummary[];
    isLoading: boolean;
  };
}

// Individual game row component for virtual scrolling
const VirtualGameRow: React.FC<GameRowProps> = memo(({ index, style, data }) => {
  const { games, isLoading } = data;
  const game = games[index];

  // Loading placeholder for items that haven't loaded yet
  if (!game && isLoading) {
    return (
      <div style={style} className="virtual-game-row loading-row">
        <div className="loading-skeleton">
          <div className="skeleton-game-id"></div>
          <div className="skeleton-players"></div>
          <div className="skeleton-result"></div>
          <div className="skeleton-duration"></div>
          <div className="skeleton-moves"></div>
          <div className="skeleton-date"></div>
        </div>
      </div>
    );
  }

  // Empty row if no game data
  if (!game) {
    return <div style={style} className="virtual-game-row empty-row"></div>;
  }

  const formatDuration = (minutes: number | null) => {
    if (!minutes) return 'Ongoing';
    if (minutes < 60) return `${Math.round(minutes)}m`;
    const hours = Math.floor(minutes / 60);
    const mins = Math.round(minutes % 60);
    return `${hours}h ${mins}m`;
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getGameResult = (game: GameSummary) => {
    if (!game.outcome) return { text: 'Ongoing', className: 'result-ongoing' };
    
    switch (game.outcome.result) {
      case 'white_wins':
        return { text: 'White Wins', className: 'result-white' };
      case 'black_wins':
        return { text: 'Black Wins', className: 'result-black' };
      case 'draw':
        return { text: 'Draw', className: 'result-draw' };
      default:
        return { text: 'Ongoing', className: 'result-ongoing' };
    }
  };

  const result = getGameResult(game);

  return (
    <div style={style} className="virtual-game-row">
      <Link to={`/games/${game.game_id}`} className="game-row-link">
        <div className="game-row-content">
          <div className="game-cell game-id">
            <div className="game-id-text">
              {game.game_id.substring(0, 8)}...
            </div>
            <div className="tournament-id">
              {game.tournament_id ? `Tournament: ${game.tournament_id.substring(0, 8)}...` : 'Single Game'}
            </div>
          </div>
          
          <div className="game-cell players">
            {Object.entries(game.players).map(([color, player], idx) => (
              <div key={color} className={`player player-${color}`}>
                <span className="player-color">{color}:</span>
                <span className="player-name">{player.model_name}</span>
              </div>
            ))}
          </div>
          
          <div className="game-cell result">
            <span className={`result-badge ${result.className}`}>
              {result.text}
            </span>
            {game.outcome?.termination && (
              <div className="termination-reason">
                {game.outcome.termination.replace(/_/g, ' ')}
              </div>
            )}
          </div>
          
          <div className="game-cell duration">
            {formatDuration(game.duration_minutes)}
          </div>
          
          <div className="game-cell moves">
            {game.total_moves} moves
          </div>
          
          <div className="game-cell date">
            {formatDate(game.start_time)}
          </div>
        </div>
      </Link>
    </div>
  );
});

export const VirtualizedGameList: React.FC<VirtualizedGameListProps> = ({
  games,
  isLoading,
  hasNextPage,
  loadMore,
  itemHeight = 80,
  height = 600,
  className
}) => {
  const itemCount = hasNextPage ? games.length + 1 : games.length;
  
  // Check if an item is loaded
  const isItemLoaded = useCallback((index: number) => {
    return !!games[index];
  }, [games]);

  // Memoized data for virtual list
  const itemData = useMemo(() => ({
    games,
    isLoading
  }), [games, isLoading]);

  return (
    <div className={`virtualized-game-list ${className || ''}`}>
      {/* Virtual List Header */}
      <div className="virtual-list-header">
        <div className="header-cell game-id-header">Game</div>
        <div className="header-cell players-header">Players</div>
        <div className="header-cell result-header">Result</div>
        <div className="header-cell duration-header">Duration</div>
        <div className="header-cell moves-header">Moves</div>
        <div className="header-cell date-header">Started</div>
      </div>

      {/* Virtual List */}
      <InfiniteLoader
        isItemLoaded={isItemLoaded}
        itemCount={itemCount}
        loadMoreItems={loadMore}
      >
        {({ onItemsRendered, ref }) => (
          <List
            ref={ref}
            height={height}
            width="100%"
            itemCount={itemCount}
            itemSize={itemHeight}
            itemData={itemData}
            onItemsRendered={onItemsRendered}
            overscanCount={5}
          >
            {VirtualGameRow}
          </List>
        )}
      </InfiniteLoader>

      <style jsx>{`
        .virtualized-game-list {
          display: flex;
          flex-direction: column;
          border: 1px solid #e5e7eb;
          border-radius: 0.75rem;
          overflow: hidden;
          background-color: white;
        }

        .virtual-list-header {
          display: grid;
          grid-template-columns: 1fr 2fr 1.5fr 1fr 1fr 1.5fr;
          background-color: #f8fafc;
          border-bottom: 2px solid #e5e7eb;
          padding: 1rem;
          font-weight: 600;
          color: #374151;
          font-size: 0.875rem;
        }

        .header-cell {
          text-align: left;
          padding: 0 0.5rem;
        }

        .virtual-game-row {
          border-bottom: 1px solid #f3f4f6;
          transition: background-color 0.15s ease;
        }

        .virtual-game-row:hover {
          background-color: #f8fafc;
        }

        .game-row-link {
          display: block;
          text-decoration: none;
          color: inherit;
          height: 100%;
        }

        .game-row-content {
          display: grid;
          grid-template-columns: 1fr 2fr 1.5fr 1fr 1fr 1.5fr;
          align-items: center;
          padding: 1rem;
          height: 100%;
        }

        .game-cell {
          padding: 0 0.5rem;
        }

        .game-id {
          display: flex;
          flex-direction: column;
          gap: 0.25rem;
        }

        .game-id-text {
          font-weight: 600;
          font-family: 'SF Mono', 'Monaco', 'Inconsolata', 'Roboto Mono', monospace;
          color: #1f2937;
        }

        .tournament-id {
          font-size: 0.75rem;
          color: #6b7280;
        }

        .players {
          display: flex;
          flex-direction: column;
          gap: 0.25rem;
        }

        .player {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          font-size: 0.875rem;
        }

        .player-color {
          font-weight: 600;
          width: 50px;
        }

        .player-white .player-color {
          color: #374151;
        }

        .player-black .player-color {
          color: #1f2937;
        }

        .player-name {
          color: #4b5563;
        }

        .result {
          text-align: center;
        }

        .result-badge {
          padding: 0.25rem 0.75rem;
          border-radius: 9999px;
          font-size: 0.75rem;
          font-weight: 600;
          text-transform: uppercase;
          letter-spacing: 0.05em;
        }

        .result-white {
          background-color: #dcfce7;
          color: #166534;
        }

        .result-black {
          background-color: #f3f4f6;
          color: #1f2937;
        }

        .result-draw {
          background-color: #fef3c7;
          color: #92400e;
        }

        .result-ongoing {
          background-color: #dbeafe;
          color: #1e40af;
        }

        .termination-reason {
          font-size: 0.625rem;
          color: #6b7280;
          text-transform: capitalize;
          margin-top: 0.25rem;
        }

        .duration,
        .moves {
          font-family: 'SF Mono', 'Monaco', 'Inconsolata', 'Roboto Mono', monospace;
          font-size: 0.875rem;
          color: #4b5563;
        }

        .date {
          font-size: 0.875rem;
          color: #6b7280;
        }

        /* Loading skeleton styles */
        .loading-row {
          background-color: #f9fafb;
        }

        .loading-skeleton {
          display: grid;
          grid-template-columns: 1fr 2fr 1.5fr 1fr 1fr 1.5fr;
          align-items: center;
          padding: 1rem;
          height: 100%;
          gap: 1rem;
        }

        .loading-skeleton > div {
          background-color: #e5e7eb;
          border-radius: 0.375rem;
          height: 1rem;
          animation: pulse 1.5s ease-in-out infinite;
        }

        .skeleton-game-id {
          height: 2rem;
        }

        .skeleton-players {
          height: 2rem;
        }

        .skeleton-result {
          height: 1.5rem;
          border-radius: 9999px;
        }

        @keyframes pulse {
          0%, 100% {
            opacity: 1;
          }
          50% {
            opacity: 0.5;
          }
        }

        .empty-row {
          background-color: transparent;
        }

        /* Responsive design */
        @media (max-width: 1024px) {
          .virtual-list-header,
          .game-row-content {
            grid-template-columns: 1fr 1.5fr 1fr 0.8fr 0.8fr 1fr;
            font-size: 0.75rem;
          }

          .header-cell,
          .game-cell {
            padding: 0 0.25rem;
          }
        }

        @media (max-width: 768px) {
          .virtual-list-header,
          .game-row-content {
            grid-template-columns: 1fr 1.5fr 1fr 0.8fr;
          }

          .moves-header,
          .date-header,
          .moves,
          .date {
            display: none;
          }
        }

        @media (max-width: 640px) {
          .virtual-list-header,
          .game-row-content {
            grid-template-columns: 1fr 1fr;
          }

          .duration-header,
          .result-header,
          .duration,
          .result {
            display: none;
          }

          .players {
            font-size: 0.75rem;
          }

          .player {
            gap: 0.25rem;
          }

          .player-color {
            width: 30px;
          }
        }
      `}</style>
    </div>
  );
};