import React, { memo, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { GameSummary, GameResult, TerminationReason } from '../types/api';
import { useQueryClient } from '@tanstack/react-query';
import { cacheUtils } from '../hooks/useApi';

interface GameCardProps {
  game: GameSummary;
}

export const GameCard: React.FC<GameCardProps> = memo(({ game }) => {
  const queryClient = useQueryClient();

  // Memoize expensive calculations
  const gameInfo = useMemo(() => {
    const formatDuration = (minutes: number | null) => {
      if (!minutes) return 'N/A';
      if (minutes < 60) return `${Math.round(minutes)}m`;
      const hours = Math.floor(minutes / 60);
      const remainingMinutes = Math.round(minutes % 60);
      return `${hours}h ${remainingMinutes}m`;
    };

    const formatDate = (dateString: string) => {
      const date = new Date(dateString);
      const now = new Date();
      const diffTime = Math.abs(now.getTime() - date.getTime());
      const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
      
      if (diffDays === 1) return 'Yesterday';
      if (diffDays <= 7) return `${diffDays} days ago`;
      return date.toLocaleDateString();
    };

    const getResultInfo = () => {
      if (!game.outcome) {
        return {
          status: 'ongoing',
          winner: null,
          loser: null,
          isDraw: false,
          resultText: 'Game in progress',
          resultClass: 'result-ongoing'
        };
      }

      const playerEntries = Object.entries(game.players);
      // Based on move data: player 1 is White, player 0 is Black
      const whitePlayer = playerEntries.find(([position]) => position === "1");
      const blackPlayer = playerEntries.find(([position]) => position === "0");

      const formatTermination = (termination?: TerminationReason) => {
        if (!termination) return '';
        switch (termination) {
          case TerminationReason.CHECKMATE: return 'by checkmate';
          case TerminationReason.RESIGNATION: return 'by resignation';
          case TerminationReason.TIME_FORFEIT: return 'on time';
          case TerminationReason.STALEMATE: return 'by stalemate';
          case TerminationReason.AGREEMENT: return 'by agreement';
          case TerminationReason.ABANDONED: return 'game abandoned';
          case TerminationReason.INSUFFICIENT_MATERIAL: return 'insufficient material';
          case TerminationReason.THREEFOLD_REPETITION: return 'threefold repetition';
          case TerminationReason.FIFTY_MOVE_RULE: return 'fifty-move rule';
          default: return termination.toLowerCase().replace('_', ' ');
        }
      };

      switch (game.outcome.result) {
        case GameResult.WHITE_WINS:
          return {
            status: 'white_wins',
            winner: whitePlayer?.[1],
            loser: blackPlayer?.[1],
            isDraw: false,
            resultText: `${whitePlayer?.[1]?.model_name || 'White'} won ${formatTermination(game.outcome.termination)}`,
            resultClass: 'result-white-wins'
          };
        case GameResult.BLACK_WINS:
          return {
            status: 'black_wins',
            winner: blackPlayer?.[1],
            loser: whitePlayer?.[1],
            isDraw: false,
            resultText: `${blackPlayer?.[1]?.model_name || 'Black'} won ${formatTermination(game.outcome.termination)}`,
            resultClass: 'result-black-wins'
          };
        case GameResult.DRAW:
          return {
            status: 'draw',
            winner: null,
            loser: null,
            isDraw: true,
            resultText: `Draw ${formatTermination(game.outcome.termination)}`,
            resultClass: 'result-draw'
          };
        default:
          return {
            status: 'ongoing',
            winner: null,
            loser: null,
            isDraw: false,
            resultText: 'Game in progress',
            resultClass: 'result-ongoing'
          };
      }
    };

    const playerEntries = Object.entries(game.players);
    const whitePlayer = playerEntries.find(([position]) => position === "1");
    const blackPlayer = playerEntries.find(([position]) => position === "0");

    return {
      formattedDuration: formatDuration(game.duration_minutes),
      formattedDate: formatDate(game.start_time),
      resultInfo: getResultInfo(),
      whitePlayer: whitePlayer?.[1],
      blackPlayer: blackPlayer?.[1],
      gameIdShort: game.game_id.slice(0, 8)
    };
  }, [game]);

  const handleCardHover = () => {
    // Prefetch game details on hover for better UX
    cacheUtils.prefetchGame(queryClient, game.game_id).catch(() => {});
  };

  return (
    <Link 
      to={`/games/${game.game_id}`} 
      className="game-card-link"
      onMouseEnter={handleCardHover}
    >
      <div className="game-card">
        {/* Header with game ID and status */}
        <div className="card-header">
          <div className="game-id-section">
            <span className="game-id">{gameInfo.gameIdShort}...</span>
            {game.tournament_id && (
              <span className="tournament-badge">Tournament</span>
            )}
          </div>
          <div className={`status-indicator ${gameInfo.resultInfo.resultClass}`}>
            {gameInfo.resultInfo.status === 'ongoing' ? '⏳' : 
             gameInfo.resultInfo.isDraw ? '🤝' :
             gameInfo.resultInfo.status === 'white_wins' ? '⚪' : '⚫'}
          </div>
        </div>

        {/* Players section */}
        <div className="players-section">
          <div className="player-row">
            <div className="player-info">
              <span className="player-color-icon">⚪</span>
              <span className="player-name">{gameInfo.whitePlayer?.model_name || 'Unknown'}</span>
              {gameInfo.resultInfo.winner?.player_id === gameInfo.whitePlayer?.player_id && (
                <span className="winner-crown">👑</span>
              )}
            </div>
            <div className="player-rating">
              {gameInfo.whitePlayer?.elo_rating ? `${Math.round(gameInfo.whitePlayer.elo_rating)}` : 'Unrated'}
            </div>
          </div>
          
          <div className="vs-divider">vs</div>
          
          <div className="player-row">
            <div className="player-info">
              <span className="player-color-icon">⚫</span>
              <span className="player-name">{gameInfo.blackPlayer?.model_name || 'Unknown'}</span>
              {gameInfo.resultInfo.winner?.player_id === gameInfo.blackPlayer?.player_id && (
                <span className="winner-crown">👑</span>
              )}
            </div>
            <div className="player-rating">
              {gameInfo.blackPlayer?.elo_rating ? `${Math.round(gameInfo.blackPlayer.elo_rating)}` : 'Unrated'}
            </div>
          </div>
        </div>

        {/* Result section */}
        <div className="result-section">
          <div className={`result-text ${gameInfo.resultInfo.resultClass}`}>
            {gameInfo.resultInfo.resultText}
          </div>
        </div>

        {/* Game metadata */}
        <div className="metadata-section">
          <div className="metadata-row">
            <div className="metadata-item">
              <span className="metadata-icon">🕐</span>
              <span className="metadata-value">{gameInfo.formattedDuration}</span>
            </div>
            <div className="metadata-item">
              <span className="metadata-icon">♟️</span>
              <span className="metadata-value">{game.total_moves} moves</span>
            </div>
          </div>
          <div className="metadata-row">
            <div className="metadata-item">
              <span className="metadata-icon">📅</span>
              <span className="metadata-value">{gameInfo.formattedDate}</span>
            </div>
            {game.is_completed && (
              <div className="completion-badge">Completed</div>
            )}
          </div>
        </div>
      </div>

      <style jsx>{`
        .game-card-link {
          text-decoration: none;
          color: inherit;
          display: block;
        }

        .game-card {
          background: #ffffff;
          border: 1px solid #e5e7eb;
          border-radius: 0.75rem;
          padding: 1.25rem;
          transition: all 0.2s ease;
          box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
          height: 100%;
          display: flex;
          flex-direction: column;
          gap: 1rem;
        }

        .game-card:hover {
          transform: translateY(-2px);
          box-shadow: 0 4px 12px 0 rgba(0, 0, 0, 0.15);
          border-color: #d1d5db;
        }

        .card-header {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
        }

        .game-id-section {
          display: flex;
          flex-direction: column;
          gap: 0.25rem;
        }

        .game-id {
          font-family: 'Monaco', 'Courier New', monospace;
          font-weight: 600;
          color: #3b82f6;
          font-size: 0.875rem;
        }

        .tournament-badge {
          background: #dbeafe;
          color: #1e40af;
          padding: 0.125rem 0.5rem;
          border-radius: 0.375rem;
          font-size: 0.75rem;
          font-weight: 500;
          width: fit-content;
        }

        .status-indicator {
          font-size: 1.25rem;
          padding: 0.25rem;
          border-radius: 0.375rem;
          display: flex;
          align-items: center;
          justify-content: center;
        }

        .players-section {
          display: flex;
          flex-direction: column;
          gap: 0.5rem;
        }

        .player-row {
          display: flex;
          justify-content: space-between;
          align-items: center;
        }

        .player-info {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          flex: 1;
        }

        .player-color-icon {
          font-size: 1rem;
        }

        .player-name {
          font-weight: 500;
          color: #374151;
          font-size: 0.875rem;
          flex: 1;
        }

        .winner-crown {
          font-size: 0.875rem;
        }

        .player-rating {
          font-size: 0.75rem;
          color: #6b7280;
          font-weight: 500;
          background: #f3f4f6;
          padding: 0.125rem 0.5rem;
          border-radius: 0.25rem;
        }

        .vs-divider {
          text-align: center;
          color: #9ca3af;
          font-size: 0.75rem;
          font-weight: 500;
          margin: 0.25rem 0;
        }

        .result-section {
          padding: 0.75rem;
          border-radius: 0.5rem;
          text-align: center;
        }

        .result-text {
          font-weight: 600;
          font-size: 0.875rem;
        }

        .result-white-wins {
          background: #f0fdf4;
          color: #166534;
        }

        .result-black-wins {
          background: #f9fafb;
          color: #1f2937;
        }

        .result-draw {
          background: #fef3c7;
          color: #92400e;
        }

        .result-ongoing {
          background: #eff6ff;
          color: #1e40af;
        }

        .metadata-section {
          display: flex;
          flex-direction: column;
          gap: 0.5rem;
          margin-top: auto;
        }

        .metadata-row {
          display: flex;
          justify-content: space-between;
          align-items: center;
        }

        .metadata-item {
          display: flex;
          align-items: center;
          gap: 0.375rem;
        }

        .metadata-icon {
          font-size: 0.875rem;
        }

        .metadata-value {
          font-size: 0.75rem;
          color: #6b7280;
          font-weight: 500;
        }

        .completion-badge {
          background: #dcfce7;
          color: #166534;
          padding: 0.125rem 0.5rem;
          border-radius: 0.25rem;
          font-size: 0.75rem;
          font-weight: 500;
        }

        @media (max-width: 640px) {
          .game-card {
            padding: 1rem;
          }

          .player-name {
            font-size: 0.8125rem;
          }

          .metadata-row {
            flex-direction: column;
            align-items: flex-start;
            gap: 0.25rem;
          }
        }
      `}</style>
    </Link>
  );
});

GameCard.displayName = 'GameCard';