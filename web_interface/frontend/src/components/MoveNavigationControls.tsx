import React, { useEffect, useCallback, useRef, useMemo } from 'react';
import PositionCache from '../utils/positionCache';

export interface MoveRecord {
  move_notation: string;
  fen_before?: string;
  fen_after?: string;
  timestamp?: string;
}

export interface MoveNavigationControlsProps {
  currentMoveIndex: number | null;
  totalMoves: number;
  moves?: MoveRecord[]; // For position caching
  onFirst: () => void;
  onPrevious: () => void;
  onNext: () => void;
  onLast: () => void;
  onJumpToMove: (index: number) => void;
  playMode?: boolean;
  onTogglePlay?: () => void;
  playSpeed?: number;
  onSpeedChange?: (speed: number) => void;
  disabled?: boolean;
  onPositionPreload?: (positions: string[]) => void; // For preloading positions
}

export const MoveNavigationControls: React.FC<MoveNavigationControlsProps> = ({
  currentMoveIndex,
  totalMoves,
  moves = [],
  onFirst,
  onPrevious,
  onNext,
  onLast,
  onJumpToMove,
  playMode = false,
  onTogglePlay,
  playSpeed = 1000,
  onSpeedChange,
  disabled = false,
  onPositionPreload
}) => {
  // Position cache for efficient navigation
  const positionCacheRef = useRef<PositionCache>(new PositionCache());
  
  // Memoized position cache to avoid recreation
  const positionCache = useMemo(() => positionCacheRef.current, []);

  // Preload positions around current move for smooth navigation
  useEffect(() => {
    if (moves.length > 0 && currentMoveIndex !== null) {
      const preloadRange = 5; // Preload 5 moves in each direction
      const startIndex = Math.max(0, currentMoveIndex - preloadRange);
      const endIndex = Math.min(moves.length - 1, currentMoveIndex + preloadRange);
      
      // Preload positions in background
      requestIdleCallback(() => {
        positionCache.preloadPositions(startIndex, endIndex, moves);
        
        // Notify parent component of preloaded positions if callback provided
        if (onPositionPreload) {
          const preloadedPositions: string[] = [];
          for (let i = startIndex; i <= endIndex; i++) {
            try {
              const position = positionCache.getPositionAtMove(i, moves);
              preloadedPositions.push(position);
            } catch (error) {
              console.warn(`Failed to preload position at move ${i}:`, error);
            }
          }
          onPositionPreload(preloadedPositions);
        }
      });
    }
  }, [currentMoveIndex, moves, positionCache, onPositionPreload]);

  // Enhanced navigation handlers with position caching
  const handleFirst = useCallback(() => {
    positionCache.preloadPositions(0, Math.min(4, totalMoves - 1), moves);
    onFirst();
  }, [onFirst, positionCache, totalMoves, moves]);

  const handlePrevious = useCallback(() => {
    if (currentMoveIndex !== null && currentMoveIndex > 0) {
      // Preload a few positions before current
      const preloadStart = Math.max(0, currentMoveIndex - 3);
      positionCache.preloadPositions(preloadStart, currentMoveIndex - 1, moves);
    }
    onPrevious();
  }, [onPrevious, currentMoveIndex, positionCache, moves]);

  const handleNext = useCallback(() => {
    if (currentMoveIndex !== null && currentMoveIndex < totalMoves - 1) {
      // Preload a few positions after current
      const preloadEnd = Math.min(totalMoves - 1, currentMoveIndex + 3);
      positionCache.preloadPositions(currentMoveIndex + 1, preloadEnd, moves);
    }
    onNext();
  }, [onNext, currentMoveIndex, totalMoves, positionCache, moves]);

  const handleLast = useCallback(() => {
    const lastIndex = totalMoves - 1;
    positionCache.preloadPositions(Math.max(0, lastIndex - 4), lastIndex, moves);
    onLast();
  }, [onLast, totalMoves, positionCache, moves]);
  // Keyboard shortcuts with cached handlers
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (disabled) return;

      // Don't handle keyboard events if user is typing in an input
      if (event.target instanceof HTMLInputElement || event.target instanceof HTMLTextAreaElement) {
        return;
      }

      switch (event.key) {
        case 'ArrowLeft':
          event.preventDefault();
          handlePrevious();
          break;
        case 'ArrowRight':
          event.preventDefault();
          handleNext();
          break;
        case 'Home':
          event.preventDefault();
          handleFirst();
          break;
        case 'End':
          event.preventDefault();
          handleLast();
          break;
        case ' ':
          event.preventDefault();
          if (onTogglePlay) {
            onTogglePlay();
          }
          break;
        case 'Escape':
          event.preventDefault();
          // Reset to no move selected
          onJumpToMove(-1);
          break;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [disabled, handleFirst, handlePrevious, handleNext, handleLast, onTogglePlay, onJumpToMove]);

  const canGoPrevious = currentMoveIndex !== null && currentMoveIndex > 0;
  const canGoNext = currentMoveIndex !== null && currentMoveIndex < totalMoves - 1;
  const canGoFirst = currentMoveIndex !== null && currentMoveIndex > 0;
  const canGoLast = currentMoveIndex !== null && currentMoveIndex < totalMoves - 1;

  const handleSpeedChange = useCallback((event: React.ChangeEvent<HTMLSelectElement>) => {
    if (onSpeedChange) {
      onSpeedChange(parseInt(event.target.value));
    }
  }, [onSpeedChange]);

  const formatMovePosition = () => {
    if (currentMoveIndex === null) {
      return `${totalMoves} moves total`;
    }
    return `Move ${currentMoveIndex + 1} of ${totalMoves}`;
  };

  return (
    <div className="move-navigation-controls">
      <div className="navigation-buttons">
        <button
          onClick={handleFirst}
          disabled={disabled || !canGoFirst}
          className="nav-button first-button"
          title="First move (Home)"
          data-testid="first-move-button"
        >
          ⏮
        </button>
        
        <button
          onClick={handlePrevious}
          disabled={disabled || !canGoPrevious}
          className="nav-button previous-button"
          title="Previous move (←)"
          data-testid="previous-move-button"
        >
          ⏪
        </button>

        {onTogglePlay && (
          <button
            onClick={onTogglePlay}
            disabled={disabled || totalMoves === 0}
            className={`nav-button play-button ${playMode ? 'playing' : ''}`}
            title={playMode ? 'Pause (Space)' : 'Play (Space)'}
            data-testid="play-pause-button"
          >
            {playMode ? '⏸' : '▶️'}
          </button>
        )}
        
        <button
          onClick={handleNext}
          disabled={disabled || !canGoNext}
          className="nav-button next-button"
          title="Next move (→)"
          data-testid="next-move-button"
        >
          ⏩
        </button>
        
        <button
          onClick={handleLast}
          disabled={disabled || !canGoLast}
          className="nav-button last-button"
          title="Last move (End)"
          data-testid="last-move-button"
        >
          ⏭
        </button>
      </div>

      <div className="move-info">
        <span className="move-indicator" data-testid="move-indicator">
          {formatMovePosition()}
        </span>
      </div>

      {onSpeedChange && (
        <div className="playback-controls">
          <label htmlFor="playback-speed" className="speed-label">
            Speed:
          </label>
          <select
            id="playback-speed"
            value={playSpeed}
            onChange={handleSpeedChange}
            disabled={disabled}
            className="speed-select"
            data-testid="speed-select"
          >
            <option value={2000}>0.5x</option>
            <option value={1000}>1x</option>
            <option value={500}>2x</option>
            <option value={250}>4x</option>
          </select>
        </div>
      )}

      <style jsx>{`
        .move-navigation-controls {
          display: flex;
          align-items: center;
          gap: 1rem;
          padding: 1rem;
          background-color: #f9fafb;
          border-radius: 0.5rem;
          border: 1px solid #e5e7eb;
          flex-wrap: wrap;
        }

        .navigation-buttons {
          display: flex;
          align-items: center;
          gap: 0.5rem;
        }

        .nav-button {
          background-color: #3b82f6;
          color: white;
          border: none;
          padding: 0.5rem 0.75rem;
          border-radius: 0.375rem;
          cursor: pointer;
          transition: all 0.2s;
          font-size: 1rem;
          display: flex;
          align-items: center;
          justify-content: center;
          min-width: 2.5rem;
          height: 2.5rem;
        }

        .nav-button:hover:not(:disabled) {
          background-color: #2563eb;
          transform: translateY(-1px);
        }

        .nav-button:active:not(:disabled) {
          transform: translateY(0);
        }

        .nav-button:disabled {
          background-color: #9ca3af;
          cursor: not-allowed;
          transform: none;
        }

        .play-button.playing {
          background-color: #dc2626;
        }

        .play-button.playing:hover:not(:disabled) {
          background-color: #b91c1c;
        }

        .move-info {
          flex: 1;
          text-align: center;
          min-width: 150px;
        }

        .move-indicator {
          font-size: 0.875rem;
          color: #6b7280;
          font-weight: 500;
        }

        .playback-controls {
          display: flex;
          align-items: center;
          gap: 0.5rem;
        }

        .speed-label {
          font-size: 0.875rem;
          color: #374151;
          font-weight: 500;
        }

        .speed-select {
          padding: 0.25rem 0.5rem;
          border: 1px solid #d1d5db;
          border-radius: 0.375rem;
          background-color: white;
          font-size: 0.875rem;
          color: #374151;
          cursor: pointer;
        }

        .speed-select:disabled {
          background-color: #f3f4f6;
          cursor: not-allowed;
        }

        .speed-select:focus {
          outline: none;
          border-color: #3b82f6;
          box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
        }

        @media (max-width: 640px) {
          .move-navigation-controls {
            flex-direction: column;
            gap: 0.75rem;
          }

          .navigation-buttons {
            justify-content: center;
          }

          .move-info {
            order: -1;
          }

          .playback-controls {
            justify-content: center;
          }
        }

        @media (max-width: 480px) {
          .nav-button {
            min-width: 2rem;
            height: 2rem;
            padding: 0.25rem 0.5rem;
            font-size: 0.875rem;
          }
        }
      `}</style>
    </div>
  );
};

export default MoveNavigationControls;