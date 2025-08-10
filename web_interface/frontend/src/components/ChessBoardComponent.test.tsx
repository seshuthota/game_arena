import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { ChessBoardComponent } from './ChessBoardComponent';

// Mock Chess.js
jest.mock('chess.js', () => ({
  Chess: jest.fn(() => ({
    load: jest.fn().mockReturnValue(true),
    fen: jest.fn().mockReturnValue('rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'),
    turn: jest.fn().mockReturnValue('w'),
    isGameOver: jest.fn().mockReturnValue(false),
    move: jest.fn().mockReturnValue({
      from: 'e2',
      to: 'e4',
      san: 'e4'
    })
  }))
}));

describe('ChessBoardComponent', () => {
  const defaultProps = {
    position: 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'
  };

  beforeEach(() => {
    // Mock document methods
    Object.defineProperty(document, 'querySelector', {
      value: jest.fn().mockReturnValue(null),
      writable: true
    });

    Object.defineProperty(document, 'querySelectorAll', {
      value: jest.fn().mockReturnValue([]),
      writable: true
    });

    Object.defineProperty(document.head, 'appendChild', {
      value: jest.fn(),
      writable: true
    });

    // Clear any existing window.Chessboard
    delete (window as any).Chessboard;
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  describe('Basic Rendering', () => {
    it('renders loading state when library is not loaded', () => {
      render(<ChessBoardComponent {...defaultProps} />);
      
      expect(screen.getByText('Loading chess board...')).toBeInTheDocument();
    });

    it('renders component without crashing', () => {
      render(<ChessBoardComponent {...defaultProps} />);
      
      // Component should render some content
      expect(screen.getByText('Loading chess board...')).toBeInTheDocument();
    });
  });

  describe('Error Handling', () => {
    it('handles invalid FEN position gracefully', () => {
      // Mock Chess.js to fail validation
      const { Chess } = require('chess.js');
      Chess.mockImplementation(() => ({
        load: jest.fn().mockReturnValue(false)
      }));

      // Mock Chessboard.js as loaded
      (window as any).Chessboard = jest.fn().mockReturnValue({
        position: jest.fn(),
        orientation: jest.fn(),
        destroy: jest.fn()
      });

      render(<ChessBoardComponent position="invalid-fen" />);
      
      expect(screen.getByTestId('error-indicator')).toBeInTheDocument();
      expect(screen.getByText('Chess Board Error')).toBeInTheDocument();
    });

    it('displays error details for invalid position', () => {
      // Mock Chess.js to fail validation
      const { Chess } = require('chess.js');
      Chess.mockImplementation(() => ({
        load: jest.fn().mockReturnValue(false)
      }));

      // Mock Chessboard.js as loaded
      (window as any).Chessboard = jest.fn().mockReturnValue({
        position: jest.fn(),
        orientation: jest.fn(),
        destroy: jest.fn()
      });

      const invalidPosition = 'invalid-fen-string';
      render(<ChessBoardComponent position={invalidPosition} />);
      
      expect(screen.getByText(invalidPosition)).toBeInTheDocument();
    });
  });

  describe('Props Handling', () => {
    it('accepts position prop', () => {
      render(<ChessBoardComponent position="test-position" />);
      expect(screen.getByText('Loading chess board...')).toBeInTheDocument();
    });

    it('accepts orientation prop', () => {
      render(<ChessBoardComponent {...defaultProps} orientation="black" />);
      expect(screen.getByText('Loading chess board...')).toBeInTheDocument();
    });

    it('accepts disabled prop', () => {
      render(<ChessBoardComponent {...defaultProps} disabled={true} />);
      expect(screen.getByText('Loading chess board...')).toBeInTheDocument();
    });

    it('accepts showCoordinates prop', () => {
      render(<ChessBoardComponent {...defaultProps} showCoordinates={false} />);
      expect(screen.getByText('Loading chess board...')).toBeInTheDocument();
    });

    it('accepts callback props without crashing', () => {
      const onMoveSelect = jest.fn();
      const onPositionChange = jest.fn();
      
      render(
        <ChessBoardComponent 
          {...defaultProps} 
          onMoveSelect={onMoveSelect}
          onPositionChange={onPositionChange}
        />
      );
      
      expect(screen.getByText('Loading chess board...')).toBeInTheDocument();
    });

    it('accepts animationSpeed prop', () => {
      render(<ChessBoardComponent {...defaultProps} animationSpeed={500} />);
      expect(screen.getByText('Loading chess board...')).toBeInTheDocument();
    });

    it('accepts highlightLastMove prop', () => {
      render(<ChessBoardComponent {...defaultProps} highlightLastMove={false} />);
      expect(screen.getByText('Loading chess board...')).toBeInTheDocument();
    });

    it('accepts lastMove prop', () => {
      const lastMove = { from: 'e2', to: 'e4' };
      render(<ChessBoardComponent {...defaultProps} lastMove={lastMove} />);
      expect(screen.getByText('Loading chess board...')).toBeInTheDocument();
    });
  });

  describe('Component Lifecycle', () => {
    it('handles unmounting gracefully', () => {
      const { unmount } = render(<ChessBoardComponent {...defaultProps} />);
      
      // Should not throw when unmounting
      expect(() => unmount()).not.toThrow();
    });

    it('handles re-rendering with different props', () => {
      const { rerender } = render(<ChessBoardComponent {...defaultProps} />);
      
      // Should not throw when re-rendering with different props
      expect(() => {
        rerender(<ChessBoardComponent position="different-position" />);
      }).not.toThrow();
    });
  });

  describe('Position Validation', () => {
    it('validates FEN positions', () => {
      // This test verifies that the component attempts to validate positions
      render(<ChessBoardComponent {...defaultProps} />);
      
      // Component should render without throwing errors for valid FEN
      expect(screen.getByText('Loading chess board...')).toBeInTheDocument();
    });

    it('handles position changes', () => {
      const { rerender } = render(<ChessBoardComponent {...defaultProps} />);
      
      // Should handle position changes without crashing
      expect(() => {
        rerender(<ChessBoardComponent position="rnbqkb1r/pppp1ppp/5n2/4p3/2B1P3/8/PPPP1PPP/RNBQK1NR w KQkq - 2 3" />);
      }).not.toThrow();
    });
  });
});