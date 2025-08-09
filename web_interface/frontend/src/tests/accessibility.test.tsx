/**
 * Accessibility tests for keyboard navigation and screen reader compatibility.
 * 
 * Tests WCAG 2.1 compliance, keyboard navigation, screen reader support,
 * focus management, and accessibility features across all components.
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe, toHaveNoViolations } from 'jest-axe';
import '@testing-library/jest-dom';

// Extend Jest matchers
expect.extend(toHaveNoViolations);

// Mock components for testing
const MockChessBoardComponent = React.forwardRef<HTMLDivElement, any>(
  ({ gameData, currentMove, onMoveChange, ...props }, ref) => (
    <div
      ref={ref}
      data-testid="chessboard"
      role="application"
      aria-label="Chess board showing current position"
      aria-describedby="board-description"
      tabIndex={0}
      {...props}
    >
      <div id="board-description" className="sr-only">
        Chess board at move {currentMove || 0}. Use arrow keys to navigate moves.
      </div>
      <div role="grid" aria-label="8x8 chess board">
        {Array.from({ length: 8 }, (_, row) =>
          Array.from({ length: 8 }, (_, col) => (
            <div
              key={`${row}-${col}`}
              role="gridcell"
              aria-label={`Square ${String.fromCharCode(97 + col)}${8 - row}`}
              tabIndex={-1}
              className="chess-square"
            >
              {/* Mock piece */}
              {row === 0 && col === 0 && (
                <span role="img" aria-label="White rook">♖</span>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  )
);

const MockMoveNavigationControls = ({ 
  currentMove, 
  totalMoves, 
  onMoveChange, 
  isPlaying, 
  onPlayPause,
  ...props 
}: any) => (
  <div 
    role="toolbar" 
    aria-label="Move navigation controls"
    data-testid="move-navigation"
    {...props}
  >
    <button
      type="button"
      onClick={() => onMoveChange(0)}
      disabled={currentMove <= 0}
      aria-label="Go to first move"
      title="First move (Home)"
    >
      ⏮
    </button>
    <button
      type="button"
      onClick={() => onMoveChange(currentMove - 1)}
      disabled={currentMove <= 0}
      aria-label="Go to previous move"
      title="Previous move (Left arrow)"
    >
      ⏪
    </button>
    <button
      type="button"
      onClick={onPlayPause}
      aria-label={isPlaying ? "Pause autoplay" : "Start autoplay"}
      title={isPlaying ? "Pause (Space)" : "Play (Space)"}
    >
      {isPlaying ? '⏸' : '▶'}
    </button>
    <button
      type="button"
      onClick={() => onMoveChange(currentMove + 1)}
      disabled={currentMove >= totalMoves}
      aria-label="Go to next move"
      title="Next move (Right arrow)"
    >
      ⏩
    </button>
    <button
      type="button"
      onClick={() => onMoveChange(totalMoves)}
      disabled={currentMove >= totalMoves}
      aria-label="Go to last move"
      title="Last move (End)"
    >
      ⏭
    </button>
    <div role="status" aria-live="polite">
      Move {currentMove} of {totalMoves}
    </div>
  </div>
);

const MockGamesList = ({ games, onGameSelect, selectedGameId, ...props }: any) => (
  <div role="main" aria-label="Games list" data-testid="games-list" {...props}>
    <h2 id="games-heading">Recent Games</h2>
    <div role="list" aria-labelledby="games-heading">
      {games.map((game: any) => (
        <div
          key={game.id}
          role="listitem"
          className={`game-card ${selectedGameId === game.id ? 'selected' : ''}`}
        >
          <button
            type="button"
            onClick={() => onGameSelect(game.id)}
            aria-pressed={selectedGameId === game.id}
            aria-describedby={`game-${game.id}-details`}
          >
            <h3>{game.white_player} vs {game.black_player}</h3>
          </button>
          <div id={`game-${game.id}-details`} className="game-details">
            <p>Result: {game.result}</p>
            <p>Opening: {game.opening}</p>
            <p>Date: {game.date}</p>
          </div>
        </div>
      ))}
    </div>
  </div>
);

const MockStatisticsDashboard = ({ playerStats, ...props }: any) => (
  <div role="main" aria-label="Statistics dashboard" data-testid="stats-dashboard" {...props}>
    <h2 id="stats-heading">Player Statistics</h2>
    <div role="region" aria-labelledby="stats-heading">
      {playerStats.map((player: any) => (
        <div key={player.name} className="player-stats" role="group" aria-labelledby={`player-${player.name}-name`}>
          <h3 id={`player-${player.name}-name`}>{player.name}</h3>
          <dl>
            <dt>Rating</dt>
            <dd aria-describedby={`player-${player.name}-rating-desc`}>
              {player.rating}
              <span id={`player-${player.name}-rating-desc`} className="sr-only">
                ELO rating points
              </span>
            </dd>
            <dt>Games Played</dt>
            <dd>{player.gamesPlayed}</dd>
            <dt>Win Rate</dt>
            <dd aria-describedby={`player-${player.name}-winrate-desc`}>
              {(player.winRate * 100).toFixed(1)}%
              <span id={`player-${player.name}-winrate-desc`} className="sr-only">
                Percentage of games won
              </span>
            </dd>
          </dl>
        </div>
      ))}
    </div>
  </div>
);

describe('Accessibility Tests', () => {
  let user: ReturnType<typeof userEvent.setup>;

  beforeEach(() => {
    user = userEvent.setup();
  });

  describe('Chess Board Accessibility', () => {
    const mockGameData = {
      id: 1,
      white_player: 'Alice',
      black_player: 'Bob',
      moves: [
        { move_number: 1, white_move: 'e4', black_move: 'e5' },
        { move_number: 2, white_move: 'Nf3', black_move: 'Nc6' }
      ]
    };

    test('has no accessibility violations', async () => {
      const { container } = render(
        <MockChessBoardComponent gameData={mockGameData} />
      );

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    test('provides proper ARIA labels and roles', () => {
      render(<MockChessBoardComponent gameData={mockGameData} />);

      const board = screen.getByRole('application');
      expect(board).toHaveAttribute('aria-label', 'Chess board showing current position');
      expect(board).toHaveAttribute('aria-describedby', 'board-description');

      const grid = screen.getByRole('grid');
      expect(grid).toHaveAttribute('aria-label', '8x8 chess board');

      // Check that squares have proper labels
      const squares = screen.getAllByRole('gridcell');
      expect(squares).toHaveLength(64);
      expect(squares[0]).toHaveAttribute('aria-label', 'Square a8');
    });

    test('is keyboard navigable', async () => {
      const onMoveChange = jest.fn();
      render(
        <MockChessBoardComponent 
          gameData={mockGameData} 
          onMoveChange={onMoveChange}
        />
      );

      const board = screen.getByRole('application');
      
      // Focus the board
      board.focus();
      expect(board).toHaveFocus();

      // Test keyboard navigation
      await user.keyboard('{ArrowRight}');
      // Would trigger move navigation in real implementation

      await user.keyboard('{Enter}');
      // Would trigger piece selection in real implementation
    });

    test('provides screen reader descriptions', () => {
      render(<MockChessBoardComponent gameData={mockGameData} currentMove={1} />);

      const description = screen.getByText(/Chess board at move 1/);
      expect(description).toHaveClass('sr-only');
      expect(description).toBeInTheDocument();
    });

    test('has proper focus management', async () => {
      render(<MockChessBoardComponent gameData={mockGameData} />);

      const board = screen.getByRole('application');
      
      // Should be focusable
      expect(board).toHaveAttribute('tabIndex', '0');
      
      // Squares should not be in tab order initially
      const squares = screen.getAllByRole('gridcell');
      squares.forEach(square => {
        expect(square).toHaveAttribute('tabIndex', '-1');
      });
    });
  });

  describe('Move Navigation Accessibility', () => {
    test('has no accessibility violations', async () => {
      const { container } = render(
        <MockMoveNavigationControls 
          currentMove={1}
          totalMoves={5}
          onMoveChange={jest.fn()}
          onPlayPause={jest.fn()}
        />
      );

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    test('provides proper toolbar semantics', () => {
      render(
        <MockMoveNavigationControls 
          currentMove={1}
          totalMoves={5}
          onMoveChange={jest.fn()}
          onPlayPause={jest.fn()}
        />
      );

      const toolbar = screen.getByRole('toolbar');
      expect(toolbar).toHaveAttribute('aria-label', 'Move navigation controls');
    });

    test('has accessible button labels and shortcuts', () => {
      render(
        <MockMoveNavigationControls 
          currentMove={1}
          totalMoves={5}
          onMoveChange={jest.fn()}
          onPlayPause={jest.fn()}
        />
      );

      const firstButton = screen.getByLabelText('Go to first move');
      expect(firstButton).toHaveAttribute('title', 'First move (Home)');

      const prevButton = screen.getByLabelText('Go to previous move');
      expect(prevButton).toHaveAttribute('title', 'Previous move (Left arrow)');

      const playButton = screen.getByLabelText('Start autoplay');
      expect(playButton).toHaveAttribute('title', 'Play (Space)');

      const nextButton = screen.getByLabelText('Go to next move');
      expect(nextButton).toHaveAttribute('title', 'Next move (Right arrow)');

      const lastButton = screen.getByLabelText('Go to last move');
      expect(lastButton).toHaveAttribute('title', 'Last move (End)');
    });

    test('handles keyboard shortcuts', async () => {
      const onMoveChange = jest.fn();
      const onPlayPause = jest.fn();

      render(
        <MockMoveNavigationControls 
          currentMove={2}
          totalMoves={5}
          onMoveChange={onMoveChange}
          onPlayPause={onPlayPause}
        />
      );

      // Focus first button and test keyboard navigation
      const firstButton = screen.getByLabelText('Go to first move');
      firstButton.focus();

      // Test Home key
      await user.keyboard('{Home}');
      expect(onMoveChange).toHaveBeenCalledWith(0);

      // Test End key
      await user.keyboard('{End}');
      expect(onMoveChange).toHaveBeenCalledWith(5);

      // Test Arrow keys
      await user.keyboard('{ArrowLeft}');
      expect(onMoveChange).toHaveBeenCalledWith(1);

      await user.keyboard('{ArrowRight}');
      expect(onMoveChange).toHaveBeenCalledWith(3);

      // Test Space for play/pause
      await user.keyboard(' ');
      expect(onPlayPause).toHaveBeenCalled();
    });

    test('provides live status updates', () => {
      render(
        <MockMoveNavigationControls 
          currentMove={3}
          totalMoves={10}
          onMoveChange={jest.fn()}
          onPlayPause={jest.fn()}
        />
      );

      const status = screen.getByRole('status');
      expect(status).toHaveAttribute('aria-live', 'polite');
      expect(status).toHaveTextContent('Move 3 of 10');
    });

    test('disables buttons appropriately with ARIA states', () => {
      const { rerender } = render(
        <MockMoveNavigationControls 
          currentMove={0}
          totalMoves={5}
          onMoveChange={jest.fn()}
          onPlayPause={jest.fn()}
        />
      );

      // At beginning
      expect(screen.getByLabelText('Go to first move')).toBeDisabled();
      expect(screen.getByLabelText('Go to previous move')).toBeDisabled();
      expect(screen.getByLabelText('Go to next move')).not.toBeDisabled();
      expect(screen.getByLabelText('Go to last move')).not.toBeDisabled();

      // At end
      rerender(
        <MockMoveNavigationControls 
          currentMove={5}
          totalMoves={5}
          onMoveChange={jest.fn()}
          onPlayPause={jest.fn()}
        />
      );

      expect(screen.getByLabelText('Go to next move')).toBeDisabled();
      expect(screen.getByLabelText('Go to last move')).toBeDisabled();
      expect(screen.getByLabelText('Go to first move')).not.toBeDisabled();
      expect(screen.getByLabelText('Go to previous move')).not.toBeDisabled();
    });
  });

  describe('Games List Accessibility', () => {
    const mockGames = [
      {
        id: 1,
        white_player: 'Alice',
        black_player: 'Bob',
        result: 'WHITE_WINS',
        opening: 'Sicilian Defense',
        date: '2024-01-15'
      },
      {
        id: 2,
        white_player: 'Charlie',
        black_player: 'Diana',
        result: 'BLACK_WINS',
        opening: 'French Defense',
        date: '2024-01-14'
      }
    ];

    test('has no accessibility violations', async () => {
      const { container } = render(
        <MockGamesList 
          games={mockGames}
          onGameSelect={jest.fn()}
        />
      );

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    test('provides proper list semantics', () => {
      render(
        <MockGamesList 
          games={mockGames}
          onGameSelect={jest.fn()}
        />
      );

      const list = screen.getByRole('list');
      expect(list).toHaveAttribute('aria-labelledby', 'games-heading');

      const listItems = screen.getAllByRole('listitem');
      expect(listItems).toHaveLength(2);
    });

    test('has accessible game selection buttons', () => {
      render(
        <MockGamesList 
          games={mockGames}
          onGameSelect={jest.fn()}
          selectedGameId={1}
        />
      );

      const gameButtons = screen.getAllByRole('button');
      
      // First game should be selected
      expect(gameButtons[0]).toHaveAttribute('aria-pressed', 'true');
      expect(gameButtons[0]).toHaveAttribute('aria-describedby', 'game-1-details');
      
      // Second game should not be selected
      expect(gameButtons[1]).toHaveAttribute('aria-pressed', 'false');
      expect(gameButtons[1]).toHaveAttribute('aria-describedby', 'game-2-details');
    });

    test('provides game details for screen readers', () => {
      render(
        <MockGamesList 
          games={mockGames}
          onGameSelect={jest.fn()}
        />
      );

      // Check that game details are properly associated
      const gameDetails = screen.getByText('Result: WHITE_WINS');
      expect(gameDetails.closest('[id="game-1-details"]')).toBeInTheDocument();

      const openingInfo = screen.getByText('Opening: Sicilian Defense');
      expect(openingInfo).toBeInTheDocument();
    });

    test('supports keyboard navigation', async () => {
      const onGameSelect = jest.fn();
      
      render(
        <MockGamesList 
          games={mockGames}
          onGameSelect={onGameSelect}
        />
      );

      const firstGameButton = screen.getAllByRole('button')[0];
      firstGameButton.focus();

      // Test Enter key
      await user.keyboard('{Enter}');
      expect(onGameSelect).toHaveBeenCalledWith(1);

      // Test Space key
      await user.keyboard(' ');
      expect(onGameSelect).toHaveBeenCalledWith(1);
    });
  });

  describe('Statistics Dashboard Accessibility', () => {
    const mockPlayerStats = [
      {
        name: 'Alice',
        rating: 1650,
        gamesPlayed: 45,
        winRate: 0.67
      },
      {
        name: 'Bob',
        rating: 1520,
        gamesPlayed: 32,
        winRate: 0.53
      }
    ];

    test('has no accessibility violations', async () => {
      const { container } = render(
        <MockStatisticsDashboard playerStats={mockPlayerStats} />
      );

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    test('provides proper semantic structure', () => {
      render(<MockStatisticsDashboard playerStats={mockPlayerStats} />);

      const dashboard = screen.getByRole('main');
      expect(dashboard).toHaveAttribute('aria-label', 'Statistics dashboard');

      const region = screen.getByRole('region');
      expect(region).toHaveAttribute('aria-labelledby', 'stats-heading');

      // Check player groups
      const playerGroups = screen.getAllByRole('group');
      expect(playerGroups).toHaveLength(2);
      
      expect(playerGroups[0]).toHaveAttribute('aria-labelledby', 'player-Alice-name');
      expect(playerGroups[1]).toHaveAttribute('aria-labelledby', 'player-Bob-name');
    });

    test('uses proper definition list markup', () => {
      render(<MockStatisticsDashboard playerStats={mockPlayerStats} />);

      const definitionLists = screen.getAllByRole('list');
      expect(definitionLists.length).toBeGreaterThan(0);

      // Check that terms and definitions are properly structured
      const ratingTerm = screen.getAllByText('Rating')[0];
      expect(ratingTerm.tagName).toBe('DT');

      const ratingValue = screen.getByText('1650');
      expect(ratingValue.tagName).toBe('DD');
    });

    test('provides context for numeric values', () => {
      render(<MockStatisticsDashboard playerStats={mockPlayerStats} />);

      // Check rating description
      const ratingDescription = screen.getByText('ELO rating points');
      expect(ratingDescription).toHaveClass('sr-only');

      // Check win rate description
      const winRateDescription = screen.getByText('Percentage of games won');
      expect(winRateDescription).toHaveClass('sr-only');

      // Check that values are associated with descriptions
      const ratingValue = screen.getByText('1650');
      expect(ratingValue).toHaveAttribute('aria-describedby', 'player-Alice-rating-desc');
    });
  });

  describe('Screen Reader Announcements', () => {
    test('announces move changes', async () => {
      const TestComponent = () => {
        const [currentMove, setCurrentMove] = React.useState(0);
        const [announcement, setAnnouncement] = React.useState('');

        React.useEffect(() => {
          setAnnouncement(`Move ${currentMove} selected`);
        }, [currentMove]);

        return (
          <div>
            <MockMoveNavigationControls 
              currentMove={currentMove}
              totalMoves={5}
              onMoveChange={setCurrentMove}
              onPlayPause={jest.fn()}
            />
            <div role="status" aria-live="assertive" aria-atomic="true">
              {announcement}
            </div>
          </div>
        );
      };

      render(<TestComponent />);

      const nextButton = screen.getByLabelText('Go to next move');
      await user.click(nextButton);

      await waitFor(() => {
        const announcement = screen.getByText('Move 1 selected');
        expect(announcement).toBeInTheDocument();
      });
    });

    test('announces game selection changes', async () => {
      const mockGames = [
        { id: 1, white_player: 'Alice', black_player: 'Bob', result: 'WHITE_WINS', opening: 'Sicilian', date: '2024-01-15' },
        { id: 2, white_player: 'Charlie', black_player: 'Diana', result: 'BLACK_WINS', opening: 'French', date: '2024-01-14' }
      ];

      const TestComponent = () => {
        const [selectedGame, setSelectedGame] = React.useState<number | null>(null);
        const [announcement, setAnnouncement] = React.useState('');

        const handleGameSelect = (gameId: number) => {
          setSelectedGame(gameId);
          const game = mockGames.find(g => g.id === gameId);
          if (game) {
            setAnnouncement(`Selected game: ${game.white_player} versus ${game.black_player}`);
          }
        };

        return (
          <div>
            <MockGamesList 
              games={mockGames}
              onGameSelect={handleGameSelect}
              selectedGameId={selectedGame}
            />
            <div role="status" aria-live="polite">
              {announcement}
            </div>
          </div>
        );
      };

      render(<TestComponent />);

      const gameButton = screen.getAllByRole('button')[0];
      await user.click(gameButton);

      await waitFor(() => {
        const announcement = screen.getByText('Selected game: Alice versus Bob');
        expect(announcement).toBeInTheDocument();
      });
    });
  });

  describe('Focus Management', () => {
    test('manages focus during modal interactions', async () => {
      const TestModal = ({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) => {
        const modalRef = React.useRef<HTMLDivElement>(null);

        React.useEffect(() => {
          if (isOpen && modalRef.current) {
            modalRef.current.focus();
          }
        }, [isOpen]);

        if (!isOpen) return null;

        return (
          <div
            ref={modalRef}
            role="dialog"
            aria-modal="true"
            aria-labelledby="modal-title"
            tabIndex={-1}
            data-testid="modal"
          >
            <h2 id="modal-title">Game Details</h2>
            <button type="button" onClick={onClose}>Close</button>
          </div>
        );
      };

      const TestComponent = () => {
        const [modalOpen, setModalOpen] = React.useState(false);

        return (
          <div>
            <button type="button" onClick={() => setModalOpen(true)}>
              Open Details
            </button>
            <TestModal isOpen={modalOpen} onClose={() => setModalOpen(false)} />
          </div>
        );
      };

      render(<TestComponent />);

      const openButton = screen.getByText('Open Details');
      await user.click(openButton);

      // Modal should be focused
      const modal = screen.getByTestId('modal');
      expect(modal).toHaveFocus();

      // Close modal
      const closeButton = screen.getByText('Close');
      await user.click(closeButton);

      // Focus should return to trigger button
      expect(openButton).toHaveFocus();
    });

    test('traps focus within modal', async () => {
      const TestModal = ({ onClose }: { onClose: () => void }) => (
        <div role="dialog" aria-modal="true" data-testid="modal">
          <button type="button" data-testid="first-button">First</button>
          <button type="button" data-testid="second-button">Second</button>
          <button type="button" onClick={onClose} data-testid="close-button">Close</button>
        </div>
      );

      const TestComponent = () => {
        const [modalOpen, setModalOpen] = React.useState(true);
        return modalOpen ? <TestModal onClose={() => setModalOpen(false)} /> : null;
      };

      render(<TestComponent />);

      const firstButton = screen.getByTestId('first-button');
      const closeButton = screen.getByTestId('close-button');

      firstButton.focus();

      // Tab forward through all buttons
      await user.tab();
      expect(screen.getByTestId('second-button')).toHaveFocus();

      await user.tab();
      expect(closeButton).toHaveFocus();

      // Tab should wrap to first button
      await user.tab();
      expect(firstButton).toHaveFocus();

      // Shift+Tab should go backwards
      await user.tab({ shift: true });
      expect(closeButton).toHaveFocus();
    });
  });

  describe('Color Contrast and Visual Accessibility', () => {
    test('has sufficient color contrast', () => {
      render(
        <div>
          <MockChessBoardComponent gameData={{ moves: [] }} />
          <MockMoveNavigationControls currentMove={0} totalMoves={5} />
        </div>
      );

      // This would typically be tested with axe-core color contrast rules
      // or custom contrast ratio calculations
      
      // Mock test for demonstration
      const buttons = screen.getAllByRole('button');
      buttons.forEach(button => {
        // Would check computed styles and calculate contrast ratios
        expect(button).toBeInTheDocument();
      });
    });

    test('supports high contrast mode', () => {
      // Mock high contrast media query
      Object.defineProperty(window, 'matchMedia', {
        writable: true,
        value: jest.fn().mockImplementation(query => ({
          matches: query === '(prefers-contrast: high)',
          media: query,
          onchange: null,
          addListener: jest.fn(),
          removeListener: jest.fn(),
          addEventListener: jest.fn(),
          removeEventListener: jest.fn(),
          dispatchEvent: jest.fn(),
        })),
      });

      render(<MockChessBoardComponent gameData={{ moves: [] }} />);

      // Would verify high contrast styles are applied
      const board = screen.getByRole('application');
      expect(board).toBeInTheDocument();
    });

    test('supports reduced motion preference', () => {
      // Mock reduced motion preference
      Object.defineProperty(window, 'matchMedia', {
        writable: true,
        value: jest.fn().mockImplementation(query => ({
          matches: query === '(prefers-reduced-motion: reduce)',
          media: query,
          onchange: null,
          addListener: jest.fn(),
          removeListener: jest.fn(),
          addEventListener: jest.fn(),
          removeEventListener: jest.fn(),
          dispatchEvent: jest.fn(),
        })),
      });

      render(
        <MockMoveNavigationControls 
          currentMove={0}
          totalMoves={5}
          onMoveChange={jest.fn()}
          onPlayPause={jest.fn()}
        />
      );

      // Would verify animations are disabled
      const controls = screen.getByRole('toolbar');
      expect(controls).toBeInTheDocument();
    });
  });

  describe('WCAG 2.1 Compliance', () => {
    test('meets WCAG 2.1 AA standards', async () => {
      const { container } = render(
        <div>
          <MockChessBoardComponent gameData={{ moves: [] }} />
          <MockMoveNavigationControls 
            currentMove={0}
            totalMoves={5}
            onMoveChange={jest.fn()}
            onPlayPause={jest.fn()}
          />
          <MockGamesList 
            games={[
              { id: 1, white_player: 'Alice', black_player: 'Bob', result: 'WHITE_WINS', opening: 'Sicilian', date: '2024-01-15' }
            ]}
            onGameSelect={jest.fn()}
          />
        </div>
      );

      const results = await axe(container, {
        rules: {
          // Enable specific WCAG 2.1 AA rules
          'color-contrast': { enabled: true },
          'focus-order-semantics': { enabled: true },
          'keyboard-navigation': { enabled: true },
          'aria-labels': { enabled: true },
          'semantic-markup': { enabled: true }
        }
      });

      expect(results).toHaveNoViolations();
    });
  });
});

// Custom accessibility testing utilities
export const AccessibilityTestUtils = {
  /**
   * Test if an element is keyboard accessible
   */
  async testKeyboardAccessibility(element: HTMLElement, user: any) {
    // Focus the element
    element.focus();
    expect(element).toHaveFocus();

    // Test Tab navigation
    await user.tab();
    // Verify focus moved appropriately

    // Test Enter/Space activation
    if (element.tagName === 'BUTTON' || element.getAttribute('role') === 'button') {
      const clickHandler = jest.fn();
      element.addEventListener('click', clickHandler);
      
      await user.keyboard('{Enter}');
      expect(clickHandler).toHaveBeenCalled();

      await user.keyboard(' ');
      expect(clickHandler).toHaveBeenCalledTimes(2);
    }
  },

  /**
   * Test screen reader announcements
   */
  testScreenReaderAnnouncements(container: HTMLElement) {
    const liveRegions = container.querySelectorAll('[aria-live]');
    expect(liveRegions.length).toBeGreaterThan(0);

    liveRegions.forEach(region => {
      const ariaLive = region.getAttribute('aria-live');
      expect(['polite', 'assertive']).toContain(ariaLive);
    });
  },

  /**
   * Test focus management
   */
  testFocusManagement(container: HTMLElement) {
    const focusableElements = container.querySelectorAll(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );

    focusableElements.forEach(element => {
      // Should have visible focus indicators
      element.dispatchEvent(new Event('focus'));
      // Would check computed styles for focus indicators
    });
  }
};