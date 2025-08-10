/**
 * Test wrapper for ChessBoardComponent that accepts gameData
 * This is used by e2e tests to provide a game-data-based interface
 */

import React, { useState, useEffect } from 'react';
import ChessBoardComponent, { ChessBoardComponentProps } from './ChessBoardComponent';

// Game data interface for tests
interface GameData {
  id: number;
  white_player: string;
  black_player: string;
  result: string;
  moves: Array<{ move_number: number; white_move: string; black_move: string }>;
  opening: string;
  date: string;
  duration: number;
  analysis: {
    positions: string[];
    evaluations: number[];
    move_quality: string[];
  };
}

interface ChessBoardComponentWrapperProps {
  gameData: GameData;
  currentMove?: number;
  orientation?: 'white' | 'black';
  interactive?: boolean;
  onMove?: (from: string, to: string) => void;
  onError?: (error: Error) => void;
}

const ChessBoardComponentWrapper: React.FC<ChessBoardComponentWrapperProps> = ({
  gameData,
  currentMove = 0,
  orientation = 'white',
  interactive = false,
  onMove,
  onError
}) => {
  const [position, setPosition] = useState<string>('');

  useEffect(() => {
    try {
      // Use the position from analysis if available, otherwise default
      if (gameData.analysis?.positions && currentMove < gameData.analysis.positions.length) {
        setPosition(gameData.analysis.positions[currentMove]);
      } else {
        // Default starting position
        setPosition('rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1');
      }
    } catch (error) {
      if (onError) {
        onError(error as Error);
      }
      // Fallback to starting position
      setPosition('rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1');
    }
  }, [gameData, currentMove, onError]);

  const handleMoveSelect = (move: any) => {
    if (onMove && interactive) {
      onMove(move.from || 'e2', move.to || 'e4');
    }
  };

  const chessBoardProps: ChessBoardComponentProps = {
    position,
    orientation,
    onMoveSelect: interactive ? handleMoveSelect : undefined,
    showCoordinates: true,
    highlightLastMove: true,
  };

  return <ChessBoardComponent {...chessBoardProps} />;
};

export default ChessBoardComponentWrapper;