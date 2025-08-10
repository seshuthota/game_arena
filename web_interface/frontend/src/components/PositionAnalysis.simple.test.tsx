import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { PositionAnalysis } from './PositionAnalysis';

// Mock chess.js
const mockChess = {
  turn: jest.fn().mockReturnValue('w'),
  board: jest.fn().mockReturnValue([
    [
      { type: 'r', color: 'b' }, { type: 'n', color: 'b' }, { type: 'b', color: 'b' }, { type: 'q', color: 'b' },
      { type: 'k', color: 'b' }, { type: 'b', color: 'b' }, { type: 'n', color: 'b' }, { type: 'r', color: 'b' }
    ],
    [
      { type: 'p', color: 'b' }, { type: 'p', color: 'b' }, { type: 'p', color: 'b' }, { type: 'p', color: 'b' },
      { type: 'p', color: 'b' }, { type: 'p', color: 'b' }, { type: 'p', color: 'b' }, { type: 'p', color: 'b' }
    ],
    [null, null, null, null, null, null, null, null],
    [null, null, null, null, null, null, null, null],
    [null, null, null, null, null, null, null, null],
    [null, null, null, null, null, null, null, null],
    [
      { type: 'p', color: 'w' }, { type: 'p', color: 'w' }, { type: 'p', color: 'w' }, { type: 'p', color: 'w' },
      { type: 'p', color: 'w' }, { type: 'p', color: 'w' }, { type: 'p', color: 'w' }, { type: 'p', color: 'w' }
    ],
    [
      { type: 'r', color: 'w' }, { type: 'n', color: 'w' }, { type: 'b', color: 'w' }, { type: 'q', color: 'w' },
      { type: 'k', color: 'w' }, { type: 'b', color: 'w' }, { type: 'n', color: 'w' }, { type: 'r', color: 'w' }
    ]
  ]),
  moves: jest.fn().mockReturnValue([
    { from: 'e2', to: 'e4', san: 'e4' },
    { from: 'd2', to: 'd4', san: 'd4' }
  ])
};

jest.mock('chess.js', () => ({
  Chess: jest.fn()
}));

describe('PositionAnalysis Simple', () => {
  const defaultProps = {
    fen: 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1',
    moveNumber: 1
  };

  beforeEach(() => {
    jest.clearAllMocks();
    const { Chess } = require('chess.js');
    Chess.mockImplementation((fen?: string) => {
      if (fen === 'invalid-fen') {
        throw new Error('Invalid FEN');
      }
      return mockChess;
    });
  });

  it('renders position analysis with basic information', () => {
    render(<PositionAnalysis {...defaultProps} />);
    
    expect(screen.getByText('Position Analysis')).toBeInTheDocument();
    expect(screen.getByText('Move 1')).toBeInTheDocument();
    expect(screen.getByText('⚪ to move')).toBeInTheDocument();
  });

  it('displays material balance correctly', () => {
    render(<PositionAnalysis {...defaultProps} />);
    
    expect(screen.getByText('Material Balance')).toBeInTheDocument();
    expect(screen.getByText('White')).toBeInTheDocument();
    expect(screen.getByText('Black')).toBeInTheDocument();
    expect(screen.getByText('Equal')).toBeInTheDocument();
  });

  it('shows material pieces for both sides', () => {
    render(<PositionAnalysis {...defaultProps} />);
    
    // Should show piece counts
    expect(screen.getByText('♕×1')).toBeInTheDocument();
    expect(screen.getByText('♖×2')).toBeInTheDocument();
    expect(screen.getByText('♗×2')).toBeInTheDocument();
    expect(screen.getByText('♘×2')).toBeInTheDocument();
    expect(screen.getByText('♙×8')).toBeInTheDocument();
    expect(screen.getAllByText('39 points')).toHaveLength(2); // Both sides should have 39 points
  });

  it('displays move quality when provided', () => {
    render(
      <PositionAnalysis 
        {...defaultProps} 
        moveQuality="excellent"
        moveQualityScore={1.5}
      />
    );
    
    expect(screen.getByText('!!')).toBeInTheDocument();
    expect(screen.getByText('Excellent')).toBeInTheDocument();
    expect(screen.getByText('(1.5)')).toBeInTheDocument();
  });

  it('shows positional factors', () => {
    render(<PositionAnalysis {...defaultProps} />);
    
    expect(screen.getByText('Positional Factors')).toBeInTheDocument();
    expect(screen.getByText('Development:')).toBeInTheDocument();
    expect(screen.getByText('Center Control:')).toBeInTheDocument();
    expect(screen.getByText('King Safety:')).toBeInTheDocument();
  });

  it('displays LLM reasoning when provided', () => {
    const reasoning = 'This move controls the center and develops the pawn.';
    render(
      <PositionAnalysis 
        {...defaultProps} 
        llmReasoning={reasoning}
      />
    );
    
    expect(screen.getByText('LLM Analysis')).toBeInTheDocument();
    expect(screen.getByText(reasoning)).toBeInTheDocument();
  });

  it('handles invalid FEN gracefully', () => {
    render(
      <PositionAnalysis 
        fen="invalid-fen"
        moveNumber={1}
      />
    );
    
    expect(screen.getByText('⚠️')).toBeInTheDocument();
    expect(screen.getByText('Unable to analyze position')).toBeInTheDocument();
  });

  it('applies custom className', () => {
    const { container } = render(
      <PositionAnalysis 
        {...defaultProps} 
        className="custom-class"
      />
    );
    
    expect(container.firstChild).toHaveClass('position-analysis', 'custom-class');
  });

  it('handles move number calculation correctly', () => {
    render(<PositionAnalysis {...defaultProps} moveNumber={5} />);
    expect(screen.getByText('Move 3')).toBeInTheDocument(); // Math.ceil(5/2) = 3
  });

  it('handles missing move quality score', () => {
    render(
      <PositionAnalysis 
        {...defaultProps} 
        moveQuality="good"
        moveQualityScore={null}
      />
    );
    
    expect(screen.getByText('!')).toBeInTheDocument();
    expect(screen.getByText('Good')).toBeInTheDocument();
    expect(screen.queryByText(/\(/)).not.toBeInTheDocument(); // No score in parentheses
  });
});