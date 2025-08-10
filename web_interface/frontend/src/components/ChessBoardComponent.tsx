import React, { useEffect, useRef, useState, useCallback, useMemo } from 'react';
import { Chess } from 'chess.js';
import PositionCache from '../utils/positionCache';
import { usePerformanceMonitor } from '../utils/performanceMonitor';

// Import CSS directly
import '@chrisoakman/chessboardjs/dist/chessboard-1.0.0.min.css';

// Type declaration for Chessboard.js
declare global {
  interface Window {
    Chessboard: any;
  }
}

// Load chessboard library from npm package
let chessboardLoaded = false;
const loadChessboardLib = (): boolean => {
  if (!chessboardLoaded) {
    try {
      // First, load and set up jQuery globally
      // eslint-disable-next-line @typescript-eslint/no-require-imports
      const $ = require('jquery');
      
      // Make jQuery available globally for chessboard.js
      if (typeof window !== 'undefined') {
        (window as any).$ = $;
        (window as any).jQuery = $;
      }
      
      // Now load chessboard.js
      // eslint-disable-next-line @typescript-eslint/no-require-imports
      require('@chrisoakman/chessboardjs/dist/chessboard-1.0.0.min.js');
      
      chessboardLoaded = true;
      return true;
    } catch (error) {
      console.error('Failed to load chessboard library from npm:', error);
      return false;
    }
  }
  return true;
};


export interface ChessMove {
  from: string;
  to: string;
  promotion?: string;
  san: string;
  fen: string;
}

export interface ChessBoardComponentProps {
  position: string; // FEN string
  orientation?: 'white' | 'black';
  showCoordinates?: boolean;
  highlightLastMove?: boolean;
  highlightLegalMoves?: boolean;
  onMoveSelect?: (move: ChessMove) => void;
  onPositionChange?: (fen: string) => void;
  animationSpeed?: number;
  disabled?: boolean;
  lastMove?: { from: string; to: string } | null;
}

// Optimized ChessBoardComponent with React.memo for performance
const ChessBoardComponentInternal: React.FC<ChessBoardComponentProps> = ({
  position,
  orientation = 'white',
  showCoordinates = true,
  highlightLastMove = true,
  highlightLegalMoves = false,
  onMoveSelect,
  onPositionChange,
  animationSpeed = 200,
  disabled = false,
  lastMove = null
}) => {
  const boardRef = useRef<HTMLDivElement>(null);
  const chessRef = useRef<Chess | null>(null);
  const boardInstanceRef = useRef<any>(null);
  const positionCacheRef = useRef<PositionCache>(new PositionCache());
  const [error, setError] = useState<string | null>(null);
  const [isLibraryLoaded, setIsLibraryLoaded] = useState(false);

  // Validate and set position
  const validatePosition = useCallback((fen: string): { isValid: boolean; chess?: Chess; error?: string } => {
    try {
      const chess = new Chess();
      chess.load(fen);
      // If we get here without throwing, the position is valid
      return { isValid: true, chess };
    } catch (err) {
      return { isValid: false, error: `FEN validation error: ${err instanceof Error ? err.message : 'Unknown error'}` };
    }
  }, []);

  // Load the chessboard library
  useEffect(() => {
    const loaded = loadChessboardLib();
    if (loaded) {
      setIsLibraryLoaded(true);
    } else {
      setError('Failed to load chess library');
    }
  }, []);

  // Initialize chess engine and board
  useEffect(() => {
    if (!isLibraryLoaded || !boardRef.current) return;

    const validation = validatePosition(position);
    if (!validation.isValid) {
      setError(validation.error || 'Invalid position');
      return;
    }

    chessRef.current = validation.chess!;
    setError(null);

    // Board configuration
    const config = {
      position: position,
      orientation: orientation,
      showNotation: showCoordinates,
      draggable: !disabled,
      animationSpeed: animationSpeed,
      pieceTheme: 'https://chessboardjs.com/img/chesspieces/wikipedia/{piece}.png',
      onDragStart: (source: string, piece: string) => {
        // Don't allow moves if disabled or game is over
        if (disabled || chessRef.current?.isGameOver()) {
          return false;
        }

        // Only allow moves for the side to move
        if ((chessRef.current?.turn() === 'w' && piece.search(/^b/) !== -1) ||
            (chessRef.current?.turn() === 'b' && piece.search(/^w/) !== -1)) {
          return false;
        }

        return true;
      },
      onDrop: (source: string, target: string) => {
        if (!chessRef.current) return 'snapback';

        try {
          // Try to make the move
          const move = chessRef.current.move({
            from: source,
            to: target,
            promotion: 'q' // Always promote to queen for simplicity
          });

          if (move === null) {
            return 'snapback';
          }

          // Notify parent of move
          if (onMoveSelect) {
            onMoveSelect({
              from: source,
              to: target,
              san: move.san,
              fen: chessRef.current.fen()
            });
          }

          if (onPositionChange) {
            onPositionChange(chessRef.current.fen());
          }

          return 'snapback'; // We'll update position externally
        } catch (err) {
          return 'snapback';
        }
      },
      onSnapEnd: () => {
        if (boardInstanceRef.current && chessRef.current) {
          boardInstanceRef.current.position(chessRef.current.fen());
        }
      }
    };

    // Create board instance using loaded Chessboard
    try {
      boardInstanceRef.current = window.Chessboard(boardRef.current, config);
    } catch (err) {
      setError(`Failed to create chessboard: ${err instanceof Error ? err.message : 'Unknown error'}`);
    }

    // Cleanup function
    return () => {
      if (boardInstanceRef.current && typeof boardInstanceRef.current.destroy === 'function') {
        boardInstanceRef.current.destroy();
      }
    };
  }, [isLibraryLoaded, position, orientation, showCoordinates, disabled, animationSpeed, onMoveSelect, onPositionChange, validatePosition]);

  // Update position when prop changes
  useEffect(() => {
    if (!boardInstanceRef.current || !chessRef.current) return;

    const validation = validatePosition(position);
    if (validation.isValid && validation.chess) {
      chessRef.current = validation.chess;
      boardInstanceRef.current.position(position);
      setError(null);
    } else {
      setError(validation.error || 'Invalid position');
    }
  }, [position, validatePosition]);

  // Update orientation
  useEffect(() => {
    if (boardInstanceRef.current) {
      boardInstanceRef.current.orientation(orientation);
    }
  }, [orientation]);

  // Highlight last move
  useEffect(() => {
    if (!boardInstanceRef.current || !highlightLastMove || !lastMove) return;

    // Remove previous highlights
    const squares = document.querySelectorAll('.square-55d63');
    squares.forEach(square => {
      square.classList.remove('highlight-last-move');
    });

    // Add new highlights
    const fromSquare = document.querySelector(`[data-square="${lastMove.from}"]`);
    const toSquare = document.querySelector(`[data-square="${lastMove.to}"]`);
    
    if (fromSquare) fromSquare.classList.add('highlight-last-move');
    if (toSquare) toSquare.classList.add('highlight-last-move');
  }, [lastMove, highlightLastMove]);

  if (!isLibraryLoaded) {
    return (
      <div className="chess-board-loading">
        <div className="loading-spinner"></div>
        <p>Loading chess board...</p>
        <style jsx>{`
          .chess-board-loading {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            height: 400px;
            background-color: #f9fafb;
            border: 2px dashed #e5e7eb;
            border-radius: 0.5rem;
            color: #6b7280;
          }

          .loading-spinner {
            width: 2rem;
            height: 2rem;
            border: 2px solid #e5e7eb;
            border-top: 2px solid #3b82f6;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin-bottom: 1rem;
          }

          @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
          }
        `}</style>
      </div>
    );
  }


  if (error) {
    return (
      <div className="chess-board-error" data-testid="error-indicator">
        <div className="error-icon">⚠️</div>
        <h3>Chess Board Error</h3>
        <p>{error}</p>
        <div className="error-details">
          <strong>Position:</strong> {position}
        </div>
        <style jsx>{`
          .chess-board-error {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            height: 400px;
            background-color: #fef2f2;
            border: 2px solid #fecaca;
            border-radius: 0.5rem;
            padding: 2rem;
            text-align: center;
            color: #dc2626;
          }

          .error-icon {
            font-size: 3rem;
            margin-bottom: 1rem;
          }

          .chess-board-error h3 {
            margin: 0 0 1rem 0;
            font-size: 1.25rem;
            font-weight: 600;
          }

          .chess-board-error p {
            margin: 0 0 1rem 0;
            color: #7f1d1d;
          }

          .error-details {
            font-size: 0.875rem;
            color: #7f1d1d;
            background-color: #fee2e2;
            padding: 0.5rem 1rem;
            border-radius: 0.25rem;
            font-family: monospace;
            word-break: break-all;
          }
        `}</style>
      </div>
    );
  }

  return (
    <div className="chess-board-container">
      <div 
        ref={boardRef} 
        className="chess-board"
        data-testid="chess-board"
        data-position={position}
      />
      <style jsx>{`
        .chess-board-container {
          display: flex;
          justify-content: center;
          align-items: center;
          padding: 1rem;
          background-color: #f9fafb;
          border-radius: 0.5rem;
          border: 1px solid #e5e7eb;
        }

        .chess-board {
          width: 400px;
          height: 400px;
        }

        @media (max-width: 768px) {
          .chess-board {
            width: 320px;
            height: 320px;
          }
        }

        @media (max-width: 480px) {
          .chess-board {
            width: 280px;
            height: 280px;
          }
        }

        /* Custom highlight styles */
        :global(.highlight-last-move) {
          background-color: rgba(255, 255, 0, 0.4) !important;
        }

        :global(.square-55d63.highlight-last-move) {
          background-color: rgba(255, 255, 0, 0.4) !important;
        }
      `}</style>
    </div>
  );
};

// Memoized component to prevent unnecessary re-renders
export const ChessBoardComponent = React.memo(ChessBoardComponentInternal, (prevProps, nextProps) => {
  // Custom comparison function for optimal re-rendering
  return (
    prevProps.position === nextProps.position &&
    prevProps.orientation === nextProps.orientation &&
    prevProps.showCoordinates === nextProps.showCoordinates &&
    prevProps.highlightLastMove === nextProps.highlightLastMove &&
    prevProps.highlightLegalMoves === nextProps.highlightLegalMoves &&
    prevProps.animationSpeed === nextProps.animationSpeed &&
    prevProps.disabled === nextProps.disabled &&
    // Deep comparison for lastMove object
    JSON.stringify(prevProps.lastMove) === JSON.stringify(nextProps.lastMove)
  );
});

ChessBoardComponent.displayName = 'ChessBoardComponent';

export default ChessBoardComponent;