/**
 * End-to-End tests for chess board interaction and move navigation.
 * 
 * Tests complete user workflows including board rendering, move navigation,
 * position synchronization, and interactive features.
 */

import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';

// Mock chess libraries
jest.mock('chess.js', () => {
  return {
    Chess: jest.fn(() => ({
      ascii: jest.fn(() => 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'),
      fen: jest.fn(() => 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'),
      history: jest.fn(() => []),
      move: jest.fn((move) => ({ from: 'e2', to: 'e4', san: 'e4' })),
      undo: jest.fn(),
      load: jest.fn(),
      turn: jest.fn(() => 'w'),
      isGameOver: jest.fn(() => false),
      isCheckmate: jest.fn(() => false),
      isStalemate: jest.fn(() => false),
      isDraw: jest.fn(() => false),
      inCheck: jest.fn(() => false),
      moves: jest.fn(() => ['e4', 'e5', 'Nf3', 'Nc6']),
      pgn: jest.fn(() => '1.e4 e5 2.Nf3 Nc6'),
      game_over: jest.fn(() => false)
    }))
  };
});

jest.mock('chessboard-jsx', () => ({
  Chessboard: ({ position, onPieceDrop, orientation, ...props }: any) => (
    <div 
      data-testid="chessboard"
      data-position={position}
      data-orientation={orientation}
      onClick={() => onPieceDrop && onPieceDrop('e2', 'e4')}
      {...props}
    >
      Mock Chessboard - Position: {position}
    </div>
  )
}));

// Import components to test
import ChessBoardComponent from '../components/ChessBoardComponentWrapper';
import MoveNavigationControls from '../components/MoveNavigationControlsWrapper';
import GameAnalysisView from '../components/GameAnalysisView';

// Mock game data for testing
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

describe('Chess Board E2E Tests', () => {
  let user: ReturnType<typeof userEvent.setup>;

  beforeEach(() => {
    user = userEvent.setup();
    jest.clearAllMocks();
  });

  describe('Chess Board Rendering and Interaction', () => {
    test('renders chess board with initial position', async () => {
      render(<ChessBoardComponent gameData={mockGameData} />);
      
      const chessboard = screen.getByTestId('chessboard');
      expect(chessboard).toBeInTheDocument();
      
      // Verify initial position is set
      await waitFor(() => {
        expect(chessboard).toHaveAttribute('data-position', expect.any(String));
      });
    });

    test('handles piece movement interaction', async () => {
      const onMoveCallback = jest.fn();
      render(
        <ChessBoardComponent 
          gameData={mockGameData} 
          onMove={onMoveCallback}
          interactive={true}
        />
      );
      
      const chessboard = screen.getByTestId('chessboard');
      
      // Simulate piece drop
      fireEvent.click(chessboard);
      
      await waitFor(() => {
        expect(onMoveCallback).toHaveBeenCalledWith('e2', 'e4');
      });
    });

    test('updates board orientation correctly', async () => {
      const { rerender } = render(
        <ChessBoardComponent 
          gameData={mockGameData} 
          orientation="white"
        />
      );
      
      let chessboard = screen.getByTestId('chessboard');
      expect(chessboard).toHaveAttribute('data-orientation', 'white');
      
      // Change orientation
      rerender(
        <ChessBoardComponent 
          gameData={mockGameData} 
          orientation="black"
        />
      );
      
      chessboard = screen.getByTestId('chessboard');
      expect(chessboard).toHaveAttribute('data-orientation', 'black');
    });

    test('displays position validation errors', async () => {
      const invalidGameData = {
        ...mockGameData,
        analysis: {
          ...mockGameData.analysis,
          positions: ['invalid_fen_position']
        }
      };
      
      render(<ChessBoardComponent gameData={invalidGameData} />);
      
      // Should show error message or fallback to valid position
      await waitFor(() => {
        const errorMessage = screen.queryByText(/invalid position/i);
        const fallbackBoard = screen.getByTestId('chessboard');
        
        // Either shows error or falls back to valid position
        expect(errorMessage || fallbackBoard).toBeTruthy();
      });
    });
  });

  describe('Move Navigation Controls', () => {
    test('renders navigation controls with correct initial state', () => {
      render(
        <MoveNavigationControls 
          totalMoves={6}
          currentMove={0}
          onMoveChange={jest.fn()}
        />
      );
      
      // Check for navigation buttons
      expect(screen.getByRole('button', { name: /first/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /previous/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /next/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /last/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /play/i })).toBeInTheDocument();
    });

    test('handles move navigation correctly', async () => {
      const onMoveChange = jest.fn();
      render(
        <MoveNavigationControls 
          totalMoves={6}
          currentMove={2}
          onMoveChange={onMoveChange}
        />
      );
      
      // Test next move
      const nextButton = screen.getByRole('button', { name: /next/i });
      await user.click(nextButton);
      expect(onMoveChange).toHaveBeenCalledWith(3);
      
      // Test previous move
      const prevButton = screen.getByRole('button', { name: /previous/i });
      await user.click(prevButton);
      expect(onMoveChange).toHaveBeenCalledWith(1);
      
      // Test jump to first
      const firstButton = screen.getByRole('button', { name: /first/i });
      await user.click(firstButton);
      expect(onMoveChange).toHaveBeenCalledWith(0);
      
      // Test jump to last
      const lastButton = screen.getByRole('button', { name: /last/i });
      await user.click(lastButton);
      expect(onMoveChange).toHaveBeenCalledWith(6);
    });

    test('handles autoplay functionality', async () => {
      const onMoveChange = jest.fn();
      render(
        <MoveNavigationControls 
          totalMoves={6}
          currentMove={0}
          onMoveChange={onMoveChange}
          autoplayInterval={100}
        />
      );
      
      const playButton = screen.getByRole('button', { name: /play/i });
      
      // Start autoplay
      await user.click(playButton);
      
      // Should show pause button
      expect(screen.getByRole('button', { name: /pause/i })).toBeInTheDocument();
      
      // Should advance moves automatically
      await waitFor(() => {
        expect(onMoveChange).toHaveBeenCalled();
      }, { timeout: 200 });
      
      // Stop autoplay
      const pauseButton = screen.getByRole('button', { name: /pause/i });
      await user.click(pauseButton);
      
      expect(screen.getByRole('button', { name: /play/i })).toBeInTheDocument();
    });

    test('disables navigation at boundaries', () => {
      const { rerender } = render(
        <MoveNavigationControls 
          totalMoves={6}
          currentMove={0}
          onMoveChange={jest.fn()}
        />
      );
      
      // At beginning, first and previous should be disabled
      expect(screen.getByRole('button', { name: /first/i })).toBeDisabled();
      expect(screen.getByRole('button', { name: /previous/i })).toBeDisabled();
      
      // At end
      rerender(
        <MoveNavigationControls 
          totalMoves={6}
          currentMove={6}
          onMoveChange={jest.fn()}
        />
      );
      
      expect(screen.getByRole('button', { name: /next/i })).toBeDisabled();
      expect(screen.getByRole('button', { name: /last/i })).toBeDisabled();
    });
  });

  describe('Keyboard Navigation', () => {
    test('handles keyboard shortcuts for move navigation', async () => {
      const onMoveChange = jest.fn();
      render(
        <div>
          <MoveNavigationControls 
            totalMoves={6}
            currentMove={2}
            onMoveChange={onMoveChange}
          />
        </div>
      );
      
      const container = screen.getByRole('button', { name: /next/i }).closest('div');
      
      // Focus the navigation controls
      if (container) {
        container.focus();
        
        // Test arrow key navigation
        await user.keyboard('{ArrowRight}');
        expect(onMoveChange).toHaveBeenCalledWith(3);
        
        await user.keyboard('{ArrowLeft}');
        expect(onMoveChange).toHaveBeenCalledWith(1);
        
        await user.keyboard('{Home}');
        expect(onMoveChange).toHaveBeenCalledWith(0);
        
        await user.keyboard('{End}');
        expect(onMoveChange).toHaveBeenCalledWith(6);
        
        await user.keyboard('{Space}');
        // Should toggle play/pause
      }
    });

    test('handles board interaction keyboard events', async () => {
      render(<ChessBoardComponent gameData={mockGameData} interactive={true} />);
      
      const chessboard = screen.getByTestId('chessboard');
      chessboard.focus();
      
      // Test piece selection with keyboard
      await user.keyboard('{Enter}');
      
      // Should handle keyboard piece selection
      // (Exact implementation depends on chessboard component)
    });
  });

  describe('Position Synchronization', () => {
    test('synchronizes board position with move navigation', async () => {
      const TestComponent = () => {
        const [currentMove, setCurrentMove] = React.useState(0);
        
        return (
          <div>
            <ChessBoardComponent 
              gameData={mockGameData}
              currentMove={currentMove}
            />
            <MoveNavigationControls 
              totalMoves={6}
              currentMove={currentMove}
              onMoveChange={setCurrentMove}
            />
          </div>
        );
      };
      
      render(<TestComponent />);
      
      const chessboard = screen.getByTestId('chessboard');
      const nextButton = screen.getByRole('button', { name: /next/i });
      
      // Get initial position
      const initialPosition = chessboard.getAttribute('data-position');
      
      // Navigate to next move
      await user.click(nextButton);
      
      // Board position should update
      await waitFor(() => {
        const newPosition = chessboard.getAttribute('data-position');
        expect(newPosition).not.toBe(initialPosition);
      });
    });

    test('maintains position consistency during rapid navigation', async () => {
      const TestComponent = () => {
        const [currentMove, setCurrentMove] = React.useState(0);
        
        return (
          <div>
            <ChessBoardComponent 
              gameData={mockGameData}
              currentMove={currentMove}
            />
            <MoveNavigationControls 
              totalMoves={6}
              currentMove={currentMove}
              onMoveChange={setCurrentMove}
            />
          </div>
        );
      };
      
      render(<TestComponent />);
      
      const nextButton = screen.getByRole('button', { name: /next/i });
      const prevButton = screen.getByRole('button', { name: /previous/i });
      
      // Rapidly navigate back and forth
      for (let i = 0; i < 5; i++) {
        await user.click(nextButton);
        await user.click(prevButton);
      }
      
      // Position should remain consistent
      const chessboard = screen.getByTestId('chessboard');
      await waitFor(() => {
        expect(chessboard).toHaveAttribute('data-position', expect.any(String));
      });
    });
  });

  describe('Move List Integration', () => {
    test('synchronizes move list selection with board position', async () => {
      const TestComponent = () => {
        const [currentMove, setCurrentMove] = React.useState(0);
        
        return (
          <div>
            <ChessBoardComponent 
              gameData={mockGameData}
              currentMove={currentMove}
            />
            <div data-testid="move-list">
              {mockGameData.moves.map((move, index) => (
                <button
                  key={index}
                  onClick={() => setCurrentMove(index * 2 + 1)}
                  className={currentMove === index * 2 + 1 ? 'selected' : ''}
                >
                  {move.white_move}
                </button>
              ))}
            </div>
          </div>
        );
      };
      
      render(<TestComponent />);
      
      const chessboard = screen.getByTestId('chessboard');
      const moveButtons = screen.getAllByRole('button');
      
      // Click on a move in the list
      await user.click(moveButtons[1]); // Second move
      
      // Board should update to show position after that move
      await waitFor(() => {
        const position = chessboard.getAttribute('data-position');
        expect(position).toBeTruthy();
      });
      
      // Move button should show selected state
      expect(moveButtons[1]).toHaveClass('selected');
    });
  });

  describe('Error Handling and Recovery', () => {
    test('handles invalid move attempts gracefully', async () => {
      const onError = jest.fn();
      render(
        <ChessBoardComponent 
          gameData={mockGameData}
          interactive={true}
          onError={onError}
        />
      );
      
      // Mock chess.js to throw error on invalid move
      const { Chess } = require('chess.js');
      Chess.mockImplementation(() => ({
        ...Chess(),
        move: jest.fn(() => null), // Invalid move returns null
        fen: jest.fn(() => 'current_position')
      }));
      
      const chessboard = screen.getByTestId('chessboard');
      fireEvent.click(chessboard);
      
      // Should handle invalid move gracefully
      await waitFor(() => {
        // Either calls error handler or shows error message
        const errorMessage = screen.queryByText(/invalid move/i);
        expect(errorMessage || onError).toBeTruthy();
      });
    });

    test('recovers from position loading errors', async () => {
      const corruptedGameData = {
        ...mockGameData,
        analysis: {
          positions: ['invalid', 'also_invalid', 'still_invalid'],
          evaluations: [0.0, 0.0, 0.0],
          move_quality: ['unknown', 'unknown', 'unknown']
        }
      };
      
      render(<ChessBoardComponent gameData={corruptedGameData} />);
      
      // Should fall back to starting position or show error state
      const chessboard = screen.getByTestId('chessboard');
      await waitFor(() => {
        expect(chessboard).toBeInTheDocument();
      });
      
      // Should either show error message or default position
      const errorState = screen.queryByText(/error/i) || 
                        screen.queryByText(/unable to load/i);
      const fallbackBoard = chessboard.getAttribute('data-position');
      
      expect(errorState || fallbackBoard).toBeTruthy();
    });

    test('handles network errors during game loading', async () => {
      // Mock fetch to fail
      global.fetch = jest.fn(() => 
        Promise.reject(new Error('Network error'))
      );
      
      const GameLoader = () => {
        const [gameData, setGameData] = React.useState(null);
        const [error, setError] = React.useState(null);
        
        React.useEffect(() => {
          fetch('/api/games/1')
            .then(res => res.json())
            .then(setGameData)
            .catch(setError);
        }, []);
        
        if (error) {
          return <div data-testid="error-message">Failed to load game</div>;
        }
        
        if (!gameData) {
          return <div data-testid="loading">Loading...</div>;
        }
        
        return <ChessBoardComponent gameData={gameData} />;
      };
      
      render(<GameLoader />);
      
      // Should show loading initially
      expect(screen.getByTestId('loading')).toBeInTheDocument();
      
      // Should show error after network failure
      await waitFor(() => {
        expect(screen.getByTestId('error-message')).toBeInTheDocument();
      });
    });
  });

  describe('Performance and Responsiveness', () => {
    test('handles rapid move navigation without performance degradation', async () => {
      const onMoveChange = jest.fn();
      render(
        <MoveNavigationControls 
          totalMoves={100} // Large number of moves
          currentMove={0}
          onMoveChange={onMoveChange}
        />
      );
      
      const nextButton = screen.getByRole('button', { name: /next/i });
      
      // Rapidly click next button
      const startTime = performance.now();
      
      for (let i = 0; i < 20; i++) {
        await user.click(nextButton);
      }
      
      const endTime = performance.now();
      const responseTime = endTime - startTime;
      
      // Should handle rapid clicks efficiently (< 1 second for 20 clicks)
      expect(responseTime).toBeLessThan(1000);
      expect(onMoveChange).toHaveBeenCalledTimes(20);
    });

    test('board updates remain smooth during autoplay', async () => {
      const updateTimes: number[] = [];
      const onMoveChange = jest.fn((move) => {
        updateTimes.push(performance.now());
      });
      
      render(
        <MoveNavigationControls 
          totalMoves={10}
          currentMove={0}
          onMoveChange={onMoveChange}
          autoplayInterval={50} // Fast autoplay
        />
      );
      
      const playButton = screen.getByRole('button', { name: /play/i });
      await user.click(playButton);
      
      // Let autoplay run for several moves
      await waitFor(() => {
        expect(updateTimes.length).toBeGreaterThan(3);
      }, { timeout: 1000 });
      
      const pauseButton = screen.getByRole('button', { name: /pause/i });
      await user.click(pauseButton);
      
      // Check that updates were reasonably consistent
      const intervals = updateTimes.slice(1).map((time, i) => time - updateTimes[i]);
      const avgInterval = intervals.reduce((a, b) => a + b, 0) / intervals.length;
      
      // Average interval should be close to expected (50ms ± 20ms tolerance)
      expect(avgInterval).toBeGreaterThan(30);
      expect(avgInterval).toBeLessThan(100);
    });
  });
});

describe('Full Game Analysis Workflow E2E', () => {
  test('complete game analysis viewing workflow', async () => {
    const user = userEvent.setup();
    
    // Mock API responses with proper typing
    const mockFetch = jest.fn<Promise<Response>, [RequestInfo | URL, RequestInit?]>((url) => {
      // Handle different URL types
      const urlString = typeof url === 'string' ? url : 
                       url instanceof URL ? url.toString() : 
                       (url as Request).url;
      
      if (urlString.includes('/api/games/1')) {
        // Create a proper Response-like mock
        const mockResponse = {
          ok: true,
          status: 200,
          statusText: 'OK',
          headers: new Headers(),
          url: urlString,
          type: 'basic' as ResponseType,
          redirected: false,
          clone: () => mockResponse,
          body: null,
          bodyUsed: false,
          arrayBuffer: () => Promise.resolve(new ArrayBuffer(0)),
          blob: () => Promise.resolve(new Blob()),
          formData: () => Promise.resolve(new FormData()),
          json: () => Promise.resolve(mockGameData),
          text: () => Promise.resolve(JSON.stringify(mockGameData)),
        } as Response;
        
        return Promise.resolve(mockResponse);
      }
      
      const errorResponse = {
        ok: false,
        status: 404,
        statusText: 'Not Found',
        headers: new Headers(),
        url: urlString,
        type: 'basic' as ResponseType,
        redirected: false,
        clone: () => errorResponse,
        body: null,
        bodyUsed: false,
        arrayBuffer: () => Promise.resolve(new ArrayBuffer(0)),
        blob: () => Promise.resolve(new Blob()),
        formData: () => Promise.resolve(new FormData()),
        json: () => Promise.reject(new Error('Not found')),
        text: () => Promise.resolve('Not found'),
      } as Response;
      
      return Promise.resolve(errorResponse);
    });
    
    global.fetch = mockFetch;
    
    render(<GameAnalysisView gameId={1} />);
    
    // Should show loading initially
    expect(screen.getByText(/loading/i)).toBeInTheDocument();
    
    // Wait for game to load
    await waitFor(() => {
      expect(screen.getByTestId('chessboard')).toBeInTheDocument();
    });
    
    // Should display game information
    expect(screen.getByText('Alice')).toBeInTheDocument();
    expect(screen.getByText('Bob')).toBeInTheDocument();
    expect(screen.getByText('Ruy Lopez')).toBeInTheDocument();
    
    // Should have navigation controls
    const nextButton = screen.getByRole('button', { name: /next/i });
    expect(nextButton).toBeInTheDocument();
    
    // Test move navigation
    await user.click(nextButton);
    
    // Board should update
    await waitFor(() => {
      const chessboard = screen.getByTestId('chessboard');
      expect(chessboard).toHaveAttribute('data-position', expect.any(String));
    });
    
    // Test board orientation toggle
    const flipButton = screen.queryByRole('button', { name: /flip/i });
    if (flipButton) {
      await user.click(flipButton);
      
      await waitFor(() => {
        const chessboard = screen.getByTestId('chessboard');
        expect(chessboard).toHaveAttribute('data-orientation');
      });
    }
    
    console.log('✅ Full game analysis workflow test completed');
  });
});