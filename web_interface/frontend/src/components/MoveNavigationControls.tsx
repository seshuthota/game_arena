import React, { useEffect, useCallback } from 'react';

export interface MoveNavigationControlsProps {
  currentMoveIndex: number | null;
  totalMoves: number;
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
}

export const MoveNavigationControls: React.FC<MoveNavigationControlsProps> = ({
  currentMoveIndex,
  totalMoves,
  onFirst,
  onPrevious,
  onNext,
  onLast,
  onJumpToMove,
  playMode = false,
  onTogglePlay,
  playSpeed = 1000,
  onSpeedChange,
  disabled = false
}) => {
  // Keyboard shortcuts
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
          onPrevious();
          break;
        case 'ArrowRight':
          event.preventDefault();
          onNext();
          break;
        case 'Home':
          event.preventDefault();
          onFirst();
          break;
        case 'End':
          event.preventDefault();
          onLast();
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
  }, [disabled, onFirst, onPrevious, onNext, onLast, onTogglePlay, onJumpToMove]);

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
          onClick={onFirst}
          disabled={disabled || !canGoFirst}
          className="nav-button first-button"
          title="First move (Home)"
          data-testid="first-move-button"
        >
          ⏮
        </button>
        
        <button
          onClick={onPrevious}
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
          onClick={onNext}
          disabled={disabled || !canGoNext}
          className="nav-button next-button"
          title="Next move (→)"
          data-testid="next-move-button"
        >
          ⏩
        </button>
        
        <button
          onClick={onLast}
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