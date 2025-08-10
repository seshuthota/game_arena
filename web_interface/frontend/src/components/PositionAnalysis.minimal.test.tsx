import React from 'react';
import { render } from '@testing-library/react';
import '@testing-library/jest-dom';
import { PositionAnalysis } from './PositionAnalysis';

// Mock chess.js completely
jest.mock('chess.js', () => ({
  Chess: jest.fn().mockImplementation(() => ({
    turn: () => 'w',
    board: () => [
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
    ],
    moves: () => [
      { from: 'e2', to: 'e4', san: 'e4' },
      { from: 'd2', to: 'd4', san: 'd4' }
    ]
  }))
}));

describe('PositionAnalysis Minimal', () => {
  it('renders without crashing', () => {
    const { container } = render(
      <PositionAnalysis 
        fen="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        moveNumber={1}
      />
    );
    
    expect(container.firstChild).toBeInTheDocument();
  });
});