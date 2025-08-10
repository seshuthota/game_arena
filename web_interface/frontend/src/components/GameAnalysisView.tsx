/**
 * Simple GameAnalysisView component for testing purposes
 */

import React from 'react';
import ChessBoardComponentWrapper from './ChessBoardComponentWrapper';

interface GameAnalysisViewProps {
  gameId: number;
}

// Mock game data - in a real app this would be fetched from an API
const mockGameData = {
  id: 1,
  white_player: 'Alice',
  black_player: 'Bob',
  result: 'WHITE_WINS',
  moves: [
    { move_number: 1, white_move: 'e4', black_move: 'e5' },
    { move_number: 2, white_move: 'Nf3', black_move: 'Nc6' },
    { move_number: 3, white_move: 'Bb5', black_move: 'a6' }
  ],
  opening: 'Ruy Lopez',
  date: '2024-01-15',
  duration: 3600,
  analysis: {
    positions: [
      'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1',
      'rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1',
      'rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2'
    ],
    evaluations: [0.0, 0.3, 0.2],
    move_quality: ['book', 'good', 'good']
  }
};

const GameAnalysisView: React.FC<GameAnalysisViewProps> = ({ gameId }) => {
  const [isLoading, setIsLoading] = React.useState(true);
  
  React.useEffect(() => {
    // Simulate loading
    const timer = setTimeout(() => setIsLoading(false), 100);
    return () => clearTimeout(timer);
  }, []);

  if (isLoading) {
    return <div>Loading...</div>;
  }

  return (
    <div>
      <div>{mockGameData.white_player}</div>
      <div>{mockGameData.black_player}</div>
      <div>{mockGameData.opening}</div>
      <ChessBoardComponentWrapper gameData={mockGameData} />
    </div>
  );
};

export default GameAnalysisView;