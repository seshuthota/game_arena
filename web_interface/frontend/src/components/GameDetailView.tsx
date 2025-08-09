import React, { memo } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useGame } from '../hooks/useApi';
import { GameDetail, GameDetailResponse } from '../types/api';
import { MoveDetailsPanel } from './MoveDetailsPanel';
import { GameDetailSkeleton } from './LoadingSkeleton';

interface GameDetailViewProps {
  gameId?: string;
}

export const GameDetailView: React.FC<GameDetailViewProps> = ({ gameId }) => {
  const { gameId: routeGameId } = useParams<{ gameId: string }>();
  const finalGameId = gameId || routeGameId;

  const {
    data: gameData,
    isLoading,
    error,
    refetch
  } = useGame(finalGameId!) as { data: GameDetailResponse | undefined, isLoading: boolean, error: unknown, refetch: () => void };

  // Loading State
  if (isLoading) {
    return (
      <div className="game-detail-view">
        <GameDetailSkeleton />
      </div>
    );
  }

  // Error State
  if (error) {
    return (
      <div className="game-detail-view">
        <div className="error-container">
          <div className="error-icon">⚠️</div>
          <h3 className="error-title">Failed to load game</h3>
          <p className="error-message">
            {error instanceof Error ? error.message : 'An unexpected error occurred'}
          </p>
          <div className="error-actions">
            <button onClick={() => refetch()} className="retry-button">
              Try Again
            </button>
            <Link to="/games" className="back-button">
              ← Back to Games
            </Link>
          </div>
        </div>
        <style jsx>{`
          .game-detail-view {
            padding: 1rem;
          }

          @media (min-width: 640px) {
            .game-detail-view {
              padding: 1.5rem;
            }
          }

          @media (min-width: 1024px) {
            .game-detail-view {
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

          .error-actions {
            display: flex;
            gap: 1rem;
            flex-wrap: wrap;
            justify-content: center;
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
            text-decoration: none;
          }

          .retry-button:hover {
            background-color: #b91c1c;
          }

          .back-button {
            background-color: #6b7280;
            color: white;
            border: none;
            padding: 0.75rem 1.5rem;
            border-radius: 0.5rem;
            font-weight: 500;
            text-decoration: none;
            transition: background-color 0.2s;
          }

          .back-button:hover {
            background-color: #4b5563;
          }
        `}</style>
      </div>
    );
  }

  // Game not found
  if (!gameData) {
    return (
      <div className="game-detail-view">
        <div className="not-found-container">
          <div className="not-found-icon">🎯</div>
          <h3 className="not-found-title">Game not found</h3>
          <p className="not-found-message">
            The requested game could not be found. It may have been deleted or the ID is incorrect.
          </p>
          <Link to="/games" className="back-button">
            ← Back to Games
          </Link>
        </div>
        <style jsx>{`
          .game-detail-view {
            padding: 2rem;
          }

          .not-found-container {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 4rem 2rem;
            text-align: center;
            background-color: #f9fafb;
            border: 2px dashed #e5e7eb;
            border-radius: 0.75rem;
          }

          .not-found-icon {
            font-size: 3rem;
            margin-bottom: 1rem;
          }

          .not-found-title {
            font-size: 1.5rem;
            font-weight: 600;
            color: #1f2937;
            margin-bottom: 0.5rem;
          }

          .not-found-message {
            color: #6b7280;
            max-width: 400px;
            line-height: 1.5;
            margin-bottom: 2rem;
          }

          .back-button {
            background-color: #3b82f6;
            color: white;
            border: none;
            padding: 0.75rem 1.5rem;
            border-radius: 0.5rem;
            font-weight: 500;
            text-decoration: none;
            transition: background-color 0.2s;
          }

          .back-button:hover {
            background-color: #2563eb;
          }
        `}</style>
      </div>
    );
  }

  return (
    <div className="game-detail-view">
      <div className="page-container">
        {/* Breadcrumb Navigation */}
        <nav className="breadcrumb">
          <Link to="/games" className="breadcrumb-link">Games</Link>
          <span className="breadcrumb-separator">/</span>
          <span className="breadcrumb-current">Game Details</span>
        </nav>

        {/* Game Header */}
        {gameData?.game && <GameHeader game={gameData.game} />}

        {/* Move History */}
        {gameData?.game && gameData.game.moves && (
          <MoveList moves={gameData.game.moves} game={gameData.game} />
        )}
      </div>

      <style jsx>{`
        .game-detail-view {
          padding: 2rem 1rem;
          min-height: calc(100vh - 200px);
        }

        .page-container {
          max-width: 1200px;
          margin: 0 auto;
        }

        .breadcrumb {
          display: flex;
          align-items: center;
          margin-bottom: 2rem;
          font-size: 0.875rem;
        }

        .breadcrumb-link {
          color: #3b82f6;
          text-decoration: none;
          font-weight: 500;
          transition: color 0.2s;
        }

        .breadcrumb-link:hover {
          color: #1d4ed8;
          text-decoration: underline;
        }

        .breadcrumb-separator {
          margin: 0 0.5rem;
          color: #9ca3af;
        }

        .breadcrumb-current {
          color: #374151;
          font-weight: 500;
        }

        .game-header {
          margin: 2rem 0;
          text-align: center;
        }

        .game-header h1 {
          color: #1f2937;
          margin: 0;
        }

        .game-info {
          background: white;
          border-radius: 0.75rem;
          padding: 2rem;
          box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
          margin-top: 2rem;
        }

        .info-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
          gap: 1rem;
          margin-bottom: 2rem;
        }

        .info-item {
          display: flex;
          flex-direction: column;
          gap: 0.25rem;
        }

        .info-item label {
          font-weight: 600;
          color: #374151;
          font-size: 0.875rem;
        }

        .info-item span {
          color: #6b7280;
        }

        .outcome.win {
          color: #059669;
          font-weight: 600;
        }

        .outcome.loss {
          color: #dc2626;
          font-weight: 600;
        }

        .outcome.draw {
          color: #d97706;
          font-weight: 600;
        }

        .players-section {
          border-top: 1px solid #e5e7eb;
          padding-top: 2rem;
        }

        .players-section h3 {
          margin-bottom: 1rem;
          color: #1f2937;
        }

        .players-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
          gap: 1rem;
        }

        .player-card {
          background: #f9fafb;
          border-radius: 0.5rem;
          padding: 1rem;
          border: 1px solid #e5e7eb;
        }

        .player-position {
          font-weight: 700;
          color: #1f2937;
          margin-bottom: 0.5rem;
          text-transform: capitalize;
        }

        .player-model {
          font-weight: 600;
          color: #3b82f6;
          margin-bottom: 0.25rem;
        }

        .player-provider {
          font-size: 0.875rem;
          color: #6b7280;
          margin-bottom: 0.25rem;
        }

        .player-elo {
          font-size: 0.75rem;
          color: #9ca3af;
        }
      `}</style>
    </div>
  );
};

// Game Header Component
interface GameHeaderProps {
  game: GameDetail;
}

const GameHeader: React.FC<GameHeaderProps> = memo(({ game }) => {
  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const formatDuration = (minutes: number | null) => {
    if (!minutes) return 'N/A';
    if (minutes < 60) return `${Math.round(minutes)} minutes`;
    const hours = Math.floor(minutes / 60);
    const remainingMinutes = Math.round(minutes % 60);
    return `${hours}h ${remainingMinutes}m`;
  };

  const getResultDisplay = () => {
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

  const playerEntries = Object.entries(game.players);
  // Fix: Based on move data, player 1 is White and player 0 is Black
  const whitePlayer = playerEntries.find(([position]) => position === "1");
  const blackPlayer = playerEntries.find(([position]) => position === "0");
  const result = getResultDisplay();

  return (
    <div className="game-header">
      <div className="game-header-main">
        <div className="game-title-section">
          <h1 className="game-title">Game {game.game_id.slice(0, 8)}</h1>
          <div className="game-id-full">
            Full ID: <code className="game-id-code">{game.game_id}</code>
          </div>
          {game.tournament_id && (
            <div className="tournament-info">
              Tournament: <span className="tournament-id">{game.tournament_id}</span>
            </div>
          )}
        </div>

        <div className="game-result-section">
          <div className={`game-result ${result.className}`}>
            {result.text}
          </div>
          {game.outcome?.termination && (
            <div className="game-termination">
              by {game.outcome.termination.replace('_', ' ')}
            </div>
          )}
        </div>
      </div>

      <div className="game-players">
        <div className="player-card white-player">
          <div className="player-header">
            <span className="player-color-indicator">⚪</span>
            <span className="player-color-text">White</span>
          </div>
          <div className="player-name">{whitePlayer?.[1]?.model_name || 'Unknown'}</div>
          <div className="player-details">
            <div className="player-detail">
              <span className="detail-label">Provider:</span>
              <span className="detail-value">{whitePlayer?.[1]?.model_provider || 'N/A'}</span>
            </div>
            <div className="player-detail">
              <span className="detail-label">Agent:</span>
              <span className="detail-value">{whitePlayer?.[1]?.agent_type || 'N/A'}</span>
            </div>
            {whitePlayer?.[1]?.elo_rating && (
              <div className="player-detail">
                <span className="detail-label">ELO:</span>
                <span className="detail-value">{whitePlayer[1].elo_rating}</span>
              </div>
            )}
          </div>
        </div>

        <div className="vs-section">
          <div className="vs-text">VS</div>
        </div>

        <div className="player-card black-player">
          <div className="player-header">
            <span className="player-color-indicator">⚫</span>
            <span className="player-color-text">Black</span>
          </div>
          <div className="player-name">{blackPlayer?.[1]?.model_name || 'Unknown'}</div>
          <div className="player-details">
            <div className="player-detail">
              <span className="detail-label">Provider:</span>
              <span className="detail-value">{blackPlayer?.[1]?.model_provider || 'N/A'}</span>
            </div>
            <div className="player-detail">
              <span className="detail-label">Agent:</span>
              <span className="detail-value">{blackPlayer?.[1]?.agent_type || 'N/A'}</span>
            </div>
            {blackPlayer?.[1]?.elo_rating && (
              <div className="player-detail">
                <span className="detail-label">ELO:</span>
                <span className="detail-value">{blackPlayer[1].elo_rating}</span>
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="game-metadata">
        <div className="metadata-card">
          <h3 className="metadata-title">Game Information</h3>
          <div className="metadata-grid">
            <div className="metadata-item">
              <span className="metadata-label">Started:</span>
              <span className="metadata-value">{formatDate(game.start_time)}</span>
            </div>
            {game.end_time && (
              <div className="metadata-item">
                <span className="metadata-label">Ended:</span>
                <span className="metadata-value">{formatDate(game.end_time)}</span>
              </div>
            )}
            <div className="metadata-item">
              <span className="metadata-label">Duration:</span>
              <span className="metadata-value">{formatDuration(game.duration_minutes)}</span>
            </div>
            <div className="metadata-item">
              <span className="metadata-label">Total Moves:</span>
              <span className="metadata-value">{game.total_moves}</span>
            </div>
            <div className="metadata-item">
              <span className="metadata-label">Status:</span>
              <span className="metadata-value">
                {game.is_completed ? 'Completed' : 'In Progress'}
              </span>
            </div>
          </div>
        </div>
      </div>

      <style jsx>{`
        .game-header {
          background-color: #ffffff;
          border: 1px solid #e5e7eb;
          border-radius: 0.75rem;
          padding: 2rem;
          margin-bottom: 2rem;
          box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
        }

        .game-header-main {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          margin-bottom: 2rem;
          flex-wrap: wrap;
          gap: 1rem;
        }

        .game-title {
          font-size: 2rem;
          font-weight: 700;
          color: #1f2937;
          margin-bottom: 0.5rem;
        }

        .game-id-full {
          font-size: 0.875rem;
          color: #6b7280;
          margin-bottom: 0.25rem;
        }

        .game-id-code {
          background-color: #f3f4f6;
          padding: 0.25rem 0.5rem;
          border-radius: 0.25rem;
          font-family: 'Monaco', 'Courier New', monospace;
          font-size: 0.8125rem;
        }

        .tournament-info {
          font-size: 0.875rem;
          color: #6b7280;
        }

        .tournament-id {
          font-weight: 500;
          color: #3b82f6;
        }

        .game-result-section {
          text-align: right;
        }

        .game-result {
          font-size: 1.5rem;
          font-weight: 700;
          margin-bottom: 0.25rem;
        }

        .result-white {
          color: #059669;
        }

        .result-black {
          color: #1f2937;
        }

        .result-draw {
          color: #d97706;
        }

        .result-ongoing {
          color: #6b7280;
        }

        .game-termination {
          font-size: 0.875rem;
          color: #6b7280;
          text-transform: capitalize;
        }

        .game-players {
          display: flex;
          gap: 2rem;
          margin-bottom: 2rem;
          align-items: center;
          flex-wrap: wrap;
        }

        .player-card {
          flex: 1;
          min-width: 250px;
          background-color: #f9fafb;
          border: 1px solid #e5e7eb;
          border-radius: 0.5rem;
          padding: 1.5rem;
        }

        .player-header {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          margin-bottom: 0.75rem;
        }

        .player-color-indicator {
          font-size: 1.25rem;
        }

        .player-color-text {
          font-size: 0.875rem;
          font-weight: 600;
          color: #6b7280;
          text-transform: uppercase;
          letter-spacing: 0.025em;
        }

        .player-name {
          font-size: 1.25rem;
          font-weight: 600;
          color: #1f2937;
          margin-bottom: 1rem;
        }

        .player-details {
          display: flex;
          flex-direction: column;
          gap: 0.5rem;
        }

        .player-detail {
          display: flex;
          justify-content: space-between;
          font-size: 0.875rem;
        }

        .detail-label {
          color: #6b7280;
          font-weight: 500;
        }

        .detail-value {
          color: #374151;
          font-weight: 600;
        }

        .vs-section {
          display: flex;
          align-items: center;
          justify-content: center;
          flex-shrink: 0;
        }

        .vs-text {
          font-size: 1.5rem;
          font-weight: 700;
          color: #9ca3af;
          padding: 1rem;
        }

        .game-metadata {
          border-top: 1px solid #e5e7eb;
          padding-top: 2rem;
        }

        .metadata-card {
          background-color: #f9fafb;
          border-radius: 0.5rem;
          padding: 1.5rem;
        }

        .metadata-title {
          font-size: 1.125rem;
          font-weight: 600;
          color: #1f2937;
          margin-bottom: 1rem;
        }

        .metadata-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
          gap: 1rem;
        }

        .metadata-item {
          display: flex;
          flex-direction: column;
          gap: 0.25rem;
        }

        .metadata-label {
          font-size: 0.8125rem;
          font-weight: 500;
          color: #6b7280;
          text-transform: uppercase;
          letter-spacing: 0.025em;
        }

        .metadata-value {
          font-size: 0.875rem;
          font-weight: 600;
          color: #374151;
        }

        @media (max-width: 768px) {
          .game-header {
            padding: 1.5rem;
          }

          .game-header-main {
            flex-direction: column;
            align-items: stretch;
          }

          .game-result-section {
            text-align: left;
          }

          .game-players {
            flex-direction: column;
            align-items: stretch;
          }

          .player-card {
            min-width: auto;
          }

          .vs-section {
            order: -1;
            margin-bottom: 1rem;
          }

          .metadata-grid {
            grid-template-columns: 1fr;
          }
        }
      `}</style>
    </div>
  );
});

// Move List Component
interface MoveListProps {
  moves: any[];
  game: GameDetail;
}

const MoveList: React.FC<MoveListProps> = memo(({ moves, game }) => {
  const [selectedMoveIndex, setSelectedMoveIndex] = React.useState<number | null>(null);
  
  // Keyboard navigation
  React.useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (moves.length === 0) return;
      
      switch (event.key) {
        case 'ArrowLeft':
          event.preventDefault();
          setSelectedMoveIndex(prev => 
            prev === null ? moves.length - 1 : Math.max(0, prev - 1)
          );
          break;
        case 'ArrowRight':
          event.preventDefault();
          setSelectedMoveIndex(prev => 
            prev === null ? 0 : Math.min(moves.length - 1, prev + 1)
          );
          break;
        case 'Home':
          event.preventDefault();
          setSelectedMoveIndex(0);
          break;
        case 'End':
          event.preventDefault();
          setSelectedMoveIndex(moves.length - 1);
          break;
        case 'Escape':
          event.preventDefault();
          setSelectedMoveIndex(null);
          break;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [moves.length]);

  const handleMoveClick = (index: number) => {
    setSelectedMoveIndex(selectedMoveIndex === index ? null : index);
  };
  return (
    <div className="move-list-container">
      <div className="move-list-header">
        <h2 className="move-list-title">Move History</h2>
        <div className="move-count-badge">
          {moves.length} moves
        </div>
      </div>

      <div className="move-list-content">
        {moves.length === 0 ? (
          <div className="no-moves">
            <div className="no-moves-icon">♟️</div>
            <p className="no-moves-text">No moves recorded yet.</p>
          </div>
        ) : (
          <div className="move-analysis-container">
            <div className="moves-section">
              <div className="move-navigation-controls">
                <button
                  onClick={() => setSelectedMoveIndex(0)}
                  disabled={moves.length === 0}
                  className="nav-button"
                  title="First move (Home)"
                >
                  ⏮
                </button>
                <button
                  onClick={() => setSelectedMoveIndex(prev => 
                    prev === null ? moves.length - 1 : Math.max(0, prev - 1)
                  )}
                  disabled={moves.length === 0}
                  className="nav-button"
                  title="Previous move (←)"
                >
                  ⏪
                </button>
                <button
                  onClick={() => setSelectedMoveIndex(prev => 
                    prev === null ? 0 : Math.min(moves.length - 1, prev + 1)
                  )}
                  disabled={moves.length === 0}
                  className="nav-button"
                  title="Next move (→)"
                >
                  ⏩
                </button>
                <button
                  onClick={() => setSelectedMoveIndex(moves.length - 1)}
                  disabled={moves.length === 0}
                  className="nav-button"
                  title="Last move (End)"
                >
                  ⏭
                </button>
                <span className="move-indicator">
                  {selectedMoveIndex !== null 
                    ? `Move ${selectedMoveIndex + 1} of ${moves.length}` 
                    : `${moves.length} moves total`}
                </span>
              </div>
              
              <div className="moves-grid">
                {moves.map((move, index) => (
                  <MoveItem
                    key={`move-${index}`}
                    move={move}
                    moveNumber={index + 1}
                    isWhite={index % 2 === 0}
                    isSelected={selectedMoveIndex === index}
                    onClick={() => handleMoveClick(index)}
                  />
                ))}
              </div>
            </div>
            
            {selectedMoveIndex !== null && (
              <div className="move-details-panel">
                <MoveDetailsPanel 
                  move={moves[selectedMoveIndex]}
                  moveNumber={selectedMoveIndex + 1}
                  isWhite={selectedMoveIndex % 2 === 0}
                />
              </div>
            )}
          </div>
        )}
      </div>

      <style jsx>{`
        .move-list-container {
          background-color: #ffffff;
          border: 1px solid #e5e7eb;
          border-radius: 0.75rem;
          overflow: hidden;
          box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
        }

        .move-list-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 1.5rem 2rem;
          background-color: #f9fafb;
          border-bottom: 1px solid #e5e7eb;
        }

        .move-list-title {
          font-size: 1.25rem;
          font-weight: 600;
          color: #1f2937;
          margin: 0;
        }

        .move-count-badge {
          background-color: #3b82f6;
          color: white;
          padding: 0.5rem 1rem;
          border-radius: 1rem;
          font-size: 0.875rem;
          font-weight: 500;
        }

        .move-list-content {
          padding: 2rem;
        }

        .no-moves {
          text-align: center;
          padding: 3rem 2rem;
          color: #6b7280;
        }

        .no-moves-icon {
          font-size: 3rem;
          margin-bottom: 1rem;
        }

        .no-moves-text {
          font-size: 1.125rem;
          margin: 0;
        }

        .move-analysis-container {
          display: flex;
          gap: 2rem;
          flex-wrap: wrap;
        }

        .moves-section {
          flex: 1;
          min-width: 300px;
        }

        .move-navigation-controls {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          margin-bottom: 1rem;
          padding: 1rem;
          background-color: #f9fafb;
          border-radius: 0.5rem;
          border: 1px solid #e5e7eb;
        }

        .nav-button {
          background-color: #3b82f6;
          color: white;
          border: none;
          padding: 0.5rem 0.75rem;
          border-radius: 0.375rem;
          cursor: pointer;
          transition: background-color 0.2s;
          font-size: 1rem;
          display: flex;
          align-items: center;
          justify-content: center;
          min-width: 2.5rem;
        }

        .nav-button:hover:not(:disabled) {
          background-color: #2563eb;
        }

        .nav-button:disabled {
          background-color: #9ca3af;
          cursor: not-allowed;
        }

        .move-indicator {
          margin-left: auto;
          font-size: 0.875rem;
          color: #6b7280;
          font-weight: 500;
        }

        .moves-grid {
          display: grid;
          gap: 0.5rem;
        }

        .move-details-panel {
          flex: 1;
          min-width: 300px;
          background-color: #f9fafb;
          border: 1px solid #e5e7eb;
          border-radius: 0.5rem;
          padding: 1.5rem;
          max-height: 600px;
          overflow-y: auto;
        }

        @media (max-width: 768px) {
          .move-list-header {
            padding: 1rem 1.5rem;
          }

          .move-list-content {
            padding: 1.5rem;
          }
        }
      `}</style>
    </div>
  );
});

// Move Item Component
interface MoveItemProps {
  move: any;
  moveNumber: number;
  isWhite: boolean;
  isSelected?: boolean;
  onClick?: () => void;
}

const MoveItem: React.FC<MoveItemProps> = memo(({ 
  move, 
  moveNumber, 
  isWhite, 
  isSelected = false,
  onClick 
}) => {
  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  };

  return (
    <div 
      className={`move-item ${isSelected ? 'selected' : ''}`}
      onClick={onClick}
    >
      <div className="move-number">
        {Math.ceil(moveNumber / 2)}{isWhite ? '.' : '...'}
      </div>
      <div className="move-notation">
        {move.move_notation || 'Unknown move'}
      </div>
      <div className="move-metadata">
        <div className="move-player">
          <span className="player-color">{isWhite ? '⚪' : '⚫'}</span>
          <span className="player-text">{isWhite ? 'White' : 'Black'}</span>
        </div>
        {move.timestamp && (
          <div className="move-time">
            {formatTimestamp(move.timestamp)}
          </div>
        )}
      </div>

      <style jsx>{`
        .move-item {
          display: grid;
          grid-template-columns: auto 1fr auto;
          align-items: center;
          padding: 0.75rem 1rem;
          border: 1px solid #e5e7eb;
          border-radius: 0.5rem;
          background-color: ${isWhite ? '#ffffff' : '#f9fafb'};
          transition: background-color 0.15s, box-shadow 0.15s;
          cursor: pointer;
        }

        .move-item:hover {
          background-color: ${isWhite ? '#f9fafb' : '#f3f4f6'};
          box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
        }

        .move-item.selected {
          background-color: #dbeafe !important;
          border-color: #3b82f6 !important;
          box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.2);
        }

        .move-number {
          font-family: 'Monaco', 'Courier New', monospace;
          font-weight: 600;
          color: #6b7280;
          font-size: 0.875rem;
          margin-right: 1rem;
          min-width: 2rem;
        }

        .move-notation {
          font-family: 'Monaco', 'Courier New', monospace;
          font-size: 1rem;
          font-weight: 600;
          color: #1f2937;
        }

        .move-metadata {
          display: flex;
          flex-direction: column;
          align-items: flex-end;
          gap: 0.25rem;
          margin-left: 1rem;
        }

        .move-player {
          display: flex;
          align-items: center;
          gap: 0.25rem;
          font-size: 0.75rem;
          color: #6b7280;
        }

        .player-color {
          font-size: 0.625rem;
        }

        .move-time {
          font-size: 0.75rem;
          color: #9ca3af;
          font-family: 'Monaco', 'Courier New', monospace;
        }

        @media (max-width: 640px) {
          .move-item {
            grid-template-columns: auto 1fr;
            gap: 0.5rem;
          }

          .move-metadata {
            grid-column: 1 / -1;
            flex-direction: row;
            justify-content: space-between;
            align-items: center;
            margin-left: 0;
            margin-top: 0.5rem;
            padding-top: 0.5rem;
            border-top: 1px solid #e5e7eb;
          }
        }
      `}</style>
    </div>
  );
});