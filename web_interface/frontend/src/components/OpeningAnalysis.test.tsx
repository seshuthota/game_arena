import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { OpeningAnalysis } from './OpeningAnalysis';

// Mock the opening database
jest.mock('../utils/openingDatabase', () => ({
  identifyOpening: jest.fn((moves: string[]) => {
    if (moves.includes('e4') && moves.includes('e5')) {
      return {
        eco: 'C20',
        name: 'King\'s Pawn Game',
        moves: ['e4', 'e5']
      };
    }
    if (moves.includes('d4')) {
      return {
        eco: 'D00',
        name: 'Queen\'s Pawn Game',
        moves: ['d4']
      };
    }
    return null;
  }),
  identifyGamePhase: jest.fn((moveNumber: number) => {
    if (moveNumber <= 15) return 'opening';
    if (moveNumber <= 40) return 'middlegame';
    return 'endgame';
  }),
  identifyKeyMoments: jest.fn(() => [
    {
      moveNumber: 12,
      type: 'tactical_shot',
      description: 'Tactical opportunity seized',
      significance: 7,
      evaluationChange: 150
    },
    {
      moveNumber: 25,
      type: 'blunder',
      description: 'Major blunder - significant material loss',
      significance: 9,
      evaluationChange: -300
    }
  ]),
  GamePhase: {
    OPENING: 'opening',
    MIDDLEGAME: 'middlegame',
    ENDGAME: 'endgame'
  }
}));

describe('OpeningAnalysis', () => {
  const defaultProps = {
    moves: ['e4', 'e5', 'Nf3', 'Nc6'],
    currentMoveNumber: 4,
    totalMoves: 50
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders opening analysis with basic information', () => {
    render(<OpeningAnalysis {...defaultProps} />);
    
    expect(screen.getByText('Opening & Game Analysis')).toBeInTheDocument();
  });

  it('displays opening information when available', () => {
    render(<OpeningAnalysis {...defaultProps} />);
    
    expect(screen.getByText('Opening')).toBeInTheDocument();
    expect(screen.getByText('C20')).toBeInTheDocument();
    expect(screen.getByText('King\'s Pawn Game')).toBeInTheDocument();
    expect(screen.getByText('e4 e5')).toBeInTheDocument();
  });

  it('shows current game phase', () => {
    render(<OpeningAnalysis {...defaultProps} />);
    
    expect(screen.getByText('Current Phase')).toBeInTheDocument();
    expect(screen.getByText('Opening')).toBeInTheDocument();
    expect(screen.getByText('Move 4 of 50')).toBeInTheDocument();
  });

  it('displays game phases timeline', () => {
    render(<OpeningAnalysis {...defaultProps} />);
    
    expect(screen.getByText('Game Phases')).toBeInTheDocument();
    expect(screen.getByText('Opening development and initial positioning')).toBeInTheDocument();
    expect(screen.getByText('Strategic maneuvering and tactical complications')).toBeInTheDocument();
  });

  it('shows key moments when available', () => {
    render(<OpeningAnalysis {...defaultProps} />);
    
    expect(screen.getByText('Key Moments')).toBeInTheDocument();
    expect(screen.getByText('Move 12')).toBeInTheDocument();
    expect(screen.getByText('Tactical Shot')).toBeInTheDocument();
    expect(screen.getByText('Tactical opportunity seized')).toBeInTheDocument();
    expect(screen.getByText('Move 25')).toBeInTheDocument();
    expect(screen.getByText('Blunder')).toBeInTheDocument();
    expect(screen.getByText('Major blunder - significant material loss')).toBeInTheDocument();
  });

  it('displays evaluation changes for key moments', () => {
    render(<OpeningAnalysis {...defaultProps} />);
    
    expect(screen.getByText('Evaluation change: +150cp')).toBeInTheDocument();
    expect(screen.getByText('Evaluation change: -300cp')).toBeInTheDocument();
  });

  it('shows significance ratings for key moments', () => {
    render(<OpeningAnalysis {...defaultProps} />);
    
    expect(screen.getByText('7/10')).toBeInTheDocument();
    expect(screen.getByText('9/10')).toBeInTheDocument();
  });

  it('handles games without opening identification', () => {
    const { identifyOpening } = require('../utils/openingDatabase');
    identifyOpening.mockReturnValue(null);

    render(<OpeningAnalysis {...defaultProps} moves={['a3', 'a6']} />);
    
    expect(screen.getByText('Opening & Game Analysis')).toBeInTheDocument();
    expect(screen.queryByText('Opening')).not.toBeInTheDocument();
  });

  it('handles games without key moments', () => {
    const { identifyKeyMoments } = require('../utils/openingDatabase');
    identifyKeyMoments.mockReturnValue([]);

    render(<OpeningAnalysis {...defaultProps} />);
    
    expect(screen.queryByText('Key Moments')).not.toBeInTheDocument();
  });

  it('applies custom className', () => {
    const { container } = render(
      <OpeningAnalysis {...defaultProps} className="custom-class" />
    );
    
    expect(container.firstChild).toHaveClass('opening-analysis', 'custom-class');
  });

  it('handles different game phases correctly', () => {
    const { identifyGamePhase } = require('../utils/openingDatabase');
    
    // Test middlegame
    identifyGamePhase.mockReturnValue('middlegame');
    const { rerender } = render(
      <OpeningAnalysis {...defaultProps} currentMoveNumber={25} />
    );
    expect(screen.getByText('Middlegame')).toBeInTheDocument();
    
    // Test endgame
    identifyGamePhase.mockReturnValue('endgame');
    rerender(<OpeningAnalysis {...defaultProps} currentMoveNumber={45} />);
    expect(screen.getByText('Endgame')).toBeInTheDocument();
  });

  it('handles empty moves array', () => {
    render(<OpeningAnalysis {...defaultProps} moves={[]} />);
    
    expect(screen.getByText('Opening & Game Analysis')).toBeInTheDocument();
    expect(screen.getByText('Current Phase')).toBeInTheDocument();
  });

  it('displays move ranges for game phases', () => {
    render(<OpeningAnalysis {...defaultProps} totalMoves={60} />);
    
    expect(screen.getByText('Moves 1-15')).toBeInTheDocument();
    expect(screen.getByText('Moves 16-42')).toBeInTheDocument();
    expect(screen.getByText('Moves 43-60')).toBeInTheDocument();
  });

  it('handles games with material count information', () => {
    render(<OpeningAnalysis {...defaultProps} materialCount={25} />);
    
    expect(screen.getByText('Opening & Game Analysis')).toBeInTheDocument();
    expect(screen.getByText('Current Phase')).toBeInTheDocument();
  });

  it('displays evaluation information when provided', () => {
    const evaluations = [0, 50, 200, -100, -400];
    render(<OpeningAnalysis {...defaultProps} evaluations={evaluations} />);
    
    expect(screen.getByText('Opening & Game Analysis')).toBeInTheDocument();
  });
});