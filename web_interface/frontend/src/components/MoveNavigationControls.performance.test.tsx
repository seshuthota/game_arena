import React from 'react';
import { render, fireEvent, act } from '@testing-library/react';
import MoveNavigationControls, { MoveRecord } from './MoveNavigationControls';
import PositionCache from '../utils/positionCache';

// Mock requestIdleCallback for testing
Object.defineProperty(window, 'requestIdleCallback', {
  value: (callback: Function) => setTimeout(callback, 0),
  writable: true
});

describe('MoveNavigationControls Performance Tests', () => {
  const mockMoves: MoveRecord[] = [
    { move_notation: 'e4', fen_after: 'rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1' },
    { move_notation: 'e5', fen_after: 'rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq e6 0 2' },
    { move_notation: 'Nf3', fen_after: 'rnbqkbnr/pppp1ppp/8/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R b KQkq - 1 2' },
    { move_notation: 'Nc6', fen_after: 'r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3' },
    { move_notation: 'Bb5', fen_after: 'r1bqkbnr/pppp1ppp/2n5/1B2p3/4P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 3 3' }
  ];

  const defaultProps = {
    currentMoveIndex: 0,
    totalMoves: mockMoves.length,
    moves: mockMoves,
    onFirst: jest.fn(),
    onPrevious: jest.fn(),
    onNext: jest.fn(),
    onLast: jest.fn(),
    onJumpToMove: jest.fn()
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Position caching performance', () => {
    test('should preload positions efficiently on mount', async () => {
      const onPositionPreload = jest.fn();
      
      render(
        <MoveNavigationControls
          {...defaultProps}
          currentMoveIndex={2}
          onPositionPreload={onPositionPreload}
        />
      );

      // Wait for preloading to complete
      await act(async () => {
        await new Promise(resolve => setTimeout(resolve, 10));
      });

      expect(onPositionPreload).toHaveBeenCalled();
      const preloadedPositions = onPositionPreload.mock.calls[0][0];
      expect(preloadedPositions).toBeInstanceOf(Array);
      expect(preloadedPositions.length).toBeGreaterThan(0);
    });

    test('should preload positions around current move efficiently', async () => {
      const onPositionPreload = jest.fn();
      const { rerender } = render(
        <MoveNavigationControls
          {...defaultProps}
          currentMoveIndex={0}
          onPositionPreload={onPositionPreload}
        />
      );

      await act(async () => {
        await new Promise(resolve => setTimeout(resolve, 10));
      });

      const initialCallCount = onPositionPreload.mock.calls.length;

      // Move to middle position
      rerender(
        <MoveNavigationControls
          {...defaultProps}
          currentMoveIndex={2}
          onPositionPreload={onPositionPreload}
        />
      );

      await act(async () => {
        await new Promise(resolve => setTimeout(resolve, 10));
      });

      expect(onPositionPreload.mock.calls.length).toBeGreaterThan(initialCallCount);
    });

    test('should handle rapid navigation without performance degradation', async () => {
      const onNext = jest.fn();
      const onPrevious = jest.fn();
      
      const { getByTestId } = render(
        <MoveNavigationControls
          {...defaultProps}
          currentMoveIndex={2} // Set to middle position so both buttons are enabled
          onNext={onNext}
          onPrevious={onPrevious}
        />
      );

      const nextButton = getByTestId('next-move-button');
      const previousButton = getByTestId('previous-move-button');

      const startTime = Date.now();

      // Simulate rapid navigation
      for (let i = 0; i < 5; i++) {
        fireEvent.click(nextButton);
        fireEvent.click(previousButton);
      }

      const endTime = Date.now();
      const duration = endTime - startTime;

      // Should handle rapid clicks efficiently (less than 100ms)
      expect(duration).toBeLessThan(100);
      // Both buttons should be clickable from middle position
      expect(onNext).toHaveBeenCalled();
      expect(onPrevious).toHaveBeenCalled();
    });
  });

  describe('Keyboard navigation performance', () => {
    test('should handle rapid keyboard navigation efficiently', async () => {
      const onNext = jest.fn();
      const onPrevious = jest.fn();
      
      render(
        <MoveNavigationControls
          {...defaultProps}
          onNext={onNext}
          onPrevious={onPrevious}
        />
      );

      const startTime = Date.now();

      // Simulate rapid keyboard navigation
      for (let i = 0; i < 20; i++) {
        fireEvent.keyDown(window, { key: 'ArrowRight' });
        fireEvent.keyDown(window, { key: 'ArrowLeft' });
      }

      const endTime = Date.now();
      const duration = endTime - startTime;

      // Should handle rapid keyboard events efficiently (less than 100ms)
      expect(duration).toBeLessThan(100);
      expect(onNext).toHaveBeenCalledTimes(20);
      expect(onPrevious).toHaveBeenCalledTimes(20);
    });

    test('should not interfere with input field typing', () => {
      const onNext = jest.fn();
      
      const { container } = render(
        <div>
          <input data-testid="test-input" />
          <MoveNavigationControls {...defaultProps} onNext={onNext} />
        </div>
      );

      const input = container.querySelector('[data-testid="test-input"]') as HTMLInputElement;
      input.focus();

      // Simulate typing in input field
      fireEvent.keyDown(input, { key: 'ArrowRight' });
      fireEvent.keyDown(input, { key: 'ArrowLeft' });

      // Should not trigger navigation when typing in input
      expect(onNext).not.toHaveBeenCalled();
    });
  });

  describe('Memory management and cleanup', () => {
    test('should clean up event listeners on unmount', () => {
      const addEventListenerSpy = jest.spyOn(window, 'addEventListener');
      const removeEventListenerSpy = jest.spyOn(window, 'removeEventListener');

      const { unmount } = render(<MoveNavigationControls {...defaultProps} />);

      expect(addEventListenerSpy).toHaveBeenCalledWith('keydown', expect.any(Function));

      unmount();

      expect(removeEventListenerSpy).toHaveBeenCalledWith('keydown', expect.any(Function));

      addEventListenerSpy.mockRestore();
      removeEventListenerSpy.mockRestore();
    });

    test('should not create memory leaks with multiple mounts/unmounts', () => {
      const addEventListenerSpy = jest.spyOn(window, 'addEventListener');
      const removeEventListenerSpy = jest.spyOn(window, 'removeEventListener');

      // Mount and unmount multiple times
      for (let i = 0; i < 5; i++) {
        const { unmount } = render(<MoveNavigationControls {...defaultProps} />);
        unmount();
      }

      // Should add and remove listeners equally
      expect(addEventListenerSpy).toHaveBeenCalledTimes(5);
      expect(removeEventListenerSpy).toHaveBeenCalledTimes(5);

      addEventListenerSpy.mockRestore();
      removeEventListenerSpy.mockRestore();
    });
  });

  describe('Position cache integration performance', () => {
    test('should use position cache efficiently for navigation', () => {
      const cache = new PositionCache();
      const getPositionSpy = jest.spyOn(cache, 'getPositionAtMove');
      const preloadSpy = jest.spyOn(cache, 'preloadPositions');

      // Simulate cache usage during navigation
      const startTime = Date.now();

      // Preload positions
      cache.preloadPositions(0, 4, mockMoves);

      // Access cached positions
      for (let i = 0; i < 5; i++) {
        cache.getPositionAtMove(i, mockMoves);
      }

      const endTime = Date.now();
      const duration = endTime - startTime;

      // Should be very fast with caching (less than 50ms)
      expect(duration).toBeLessThan(50);
      expect(preloadSpy).toHaveBeenCalledWith(0, 4, mockMoves);
      expect(getPositionSpy).toHaveBeenCalled(); // Called at least once
    });

    test('should handle large move sets efficiently', async () => {
      // Create a large move set
      const largeMoveSet: MoveRecord[] = [];
      for (let i = 0; i < 100; i++) {
        largeMoveSet.push({
          move_notation: `move${i}`,
          fen_after: `position${i}`
        });
      }

      const onPositionPreload = jest.fn();
      const startTime = Date.now();

      render(
        <MoveNavigationControls
          {...defaultProps}
          moves={largeMoveSet}
          totalMoves={largeMoveSet.length}
          currentMoveIndex={50}
          onPositionPreload={onPositionPreload}
        />
      );

      await act(async () => {
        await new Promise(resolve => setTimeout(resolve, 20));
      });

      const endTime = Date.now();
      const duration = endTime - startTime;

      // Should handle large datasets efficiently (less than 100ms)
      expect(duration).toBeLessThan(100);
      expect(onPositionPreload).toHaveBeenCalled();
    });
  });

  describe('Button state updates performance', () => {
    test('should update button states efficiently', () => {
      const { rerender, getByTestId } = render(
        <MoveNavigationControls {...defaultProps} currentMoveIndex={0} />
      );

      const startTime = Date.now();

      // Rapidly change current move index
      for (let i = 0; i < mockMoves.length; i++) {
        rerender(
          <MoveNavigationControls {...defaultProps} currentMoveIndex={i} />
        );
      }

      const endTime = Date.now();
      const duration = endTime - startTime;

      // Should update states quickly (less than 50ms)
      expect(duration).toBeLessThan(50);

      // Verify final state
      const previousButton = getByTestId('previous-move-button');
      const nextButton = getByTestId('next-move-button');
      
      expect(previousButton).not.toBeDisabled();
      expect(nextButton).toBeDisabled(); // At last move
    });

    test('should handle disabled state changes efficiently', () => {
      const { rerender } = render(
        <MoveNavigationControls {...defaultProps} disabled={false} />
      );

      const startTime = Date.now();

      // Toggle disabled state multiple times
      for (let i = 0; i < 10; i++) {
        rerender(
          <MoveNavigationControls {...defaultProps} disabled={i % 2 === 0} />
        );
      }

      const endTime = Date.now();
      const duration = endTime - startTime;

      // Should handle state changes efficiently (less than 30ms)
      expect(duration).toBeLessThan(30);
    });
  });

  describe('Play mode performance', () => {
    test('should handle play mode toggles efficiently', () => {
      const onTogglePlay = jest.fn();
      const { getByTestId } = render(
        <MoveNavigationControls
          {...defaultProps}
          playMode={false}
          onTogglePlay={onTogglePlay}
        />
      );

      const playButton = getByTestId('play-pause-button');
      const startTime = Date.now();

      // Rapidly toggle play mode
      for (let i = 0; i < 20; i++) {
        fireEvent.click(playButton);
      }

      const endTime = Date.now();
      const duration = endTime - startTime;

      // Should handle rapid toggles efficiently (less than 50ms)
      expect(duration).toBeLessThan(50);
      expect(onTogglePlay).toHaveBeenCalledTimes(20);
    });

    test('should handle speed changes efficiently', () => {
      const onSpeedChange = jest.fn();
      const { getByTestId } = render(
        <MoveNavigationControls
          {...defaultProps}
          playSpeed={1000}
          onSpeedChange={onSpeedChange}
        />
      );

      const speedSelect = getByTestId('speed-select');
      const startTime = Date.now();

      // Change speed multiple times
      const speeds = ['2000', '1000', '500', '250'];
      speeds.forEach(speed => {
        fireEvent.change(speedSelect, { target: { value: speed } });
      });

      const endTime = Date.now();
      const duration = endTime - startTime;

      // Should handle speed changes efficiently (less than 20ms)
      expect(duration).toBeLessThan(20);
      expect(onSpeedChange).toHaveBeenCalledTimes(speeds.length);
    });
  });
});