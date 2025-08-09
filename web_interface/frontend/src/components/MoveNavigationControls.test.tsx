import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { MoveNavigationControls, MoveNavigationControlsProps } from './MoveNavigationControls';

describe('MoveNavigationControls', () => {
  const defaultProps: MoveNavigationControlsProps = {
    currentMoveIndex: 0,
    totalMoves: 10,
    onFirst: jest.fn(),
    onPrevious: jest.fn(),
    onNext: jest.fn(),
    onLast: jest.fn(),
    onJumpToMove: jest.fn()
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Basic Rendering', () => {
    it('renders all navigation buttons', () => {
      render(<MoveNavigationControls {...defaultProps} />);
      
      expect(screen.getByTestId('first-move-button')).toBeInTheDocument();
      expect(screen.getByTestId('previous-move-button')).toBeInTheDocument();
      expect(screen.getByTestId('next-move-button')).toBeInTheDocument();
      expect(screen.getByTestId('last-move-button')).toBeInTheDocument();
    });

    it('displays move indicator correctly', () => {
      render(<MoveNavigationControls {...defaultProps} />);
      
      expect(screen.getByTestId('move-indicator')).toHaveTextContent('Move 1 of 10');
    });

    it('displays total moves when no move is selected', () => {
      render(<MoveNavigationControls {...defaultProps} currentMoveIndex={null} />);
      
      expect(screen.getByTestId('move-indicator')).toHaveTextContent('10 moves total');
    });

    it('renders play/pause button when onTogglePlay is provided', () => {
      const onTogglePlay = jest.fn();
      render(<MoveNavigationControls {...defaultProps} onTogglePlay={onTogglePlay} />);
      
      expect(screen.getByTestId('play-pause-button')).toBeInTheDocument();
    });

    it('does not render play/pause button when onTogglePlay is not provided', () => {
      render(<MoveNavigationControls {...defaultProps} />);
      
      expect(screen.queryByTestId('play-pause-button')).not.toBeInTheDocument();
    });

    it('renders speed control when onSpeedChange is provided', () => {
      const onSpeedChange = jest.fn();
      render(<MoveNavigationControls {...defaultProps} onSpeedChange={onSpeedChange} />);
      
      expect(screen.getByTestId('speed-select')).toBeInTheDocument();
    });
  });

  describe('Button States', () => {
    it('disables first and previous buttons when at first move', () => {
      render(<MoveNavigationControls {...defaultProps} currentMoveIndex={0} />);
      
      expect(screen.getByTestId('first-move-button')).toBeDisabled();
      expect(screen.getByTestId('previous-move-button')).toBeDisabled();
      expect(screen.getByTestId('next-move-button')).not.toBeDisabled();
      expect(screen.getByTestId('last-move-button')).not.toBeDisabled();
    });

    it('disables next and last buttons when at last move', () => {
      render(<MoveNavigationControls {...defaultProps} currentMoveIndex={9} />);
      
      expect(screen.getByTestId('first-move-button')).not.toBeDisabled();
      expect(screen.getByTestId('previous-move-button')).not.toBeDisabled();
      expect(screen.getByTestId('next-move-button')).toBeDisabled();
      expect(screen.getByTestId('last-move-button')).toBeDisabled();
    });

    it('enables all buttons when in middle of moves', () => {
      render(<MoveNavigationControls {...defaultProps} currentMoveIndex={5} />);
      
      expect(screen.getByTestId('first-move-button')).not.toBeDisabled();
      expect(screen.getByTestId('previous-move-button')).not.toBeDisabled();
      expect(screen.getByTestId('next-move-button')).not.toBeDisabled();
      expect(screen.getByTestId('last-move-button')).not.toBeDisabled();
    });

    it('disables all buttons when disabled prop is true', () => {
      render(<MoveNavigationControls {...defaultProps} disabled={true} />);
      
      expect(screen.getByTestId('first-move-button')).toBeDisabled();
      expect(screen.getByTestId('previous-move-button')).toBeDisabled();
      expect(screen.getByTestId('next-move-button')).toBeDisabled();
      expect(screen.getByTestId('last-move-button')).toBeDisabled();
    });
  });

  describe('Button Interactions', () => {
    it('calls onFirst when first button is clicked', () => {
      render(<MoveNavigationControls {...defaultProps} currentMoveIndex={5} />);
      
      fireEvent.click(screen.getByTestId('first-move-button'));
      
      expect(defaultProps.onFirst).toHaveBeenCalledTimes(1);
    });

    it('calls onPrevious when previous button is clicked', () => {
      render(<MoveNavigationControls {...defaultProps} currentMoveIndex={5} />);
      
      fireEvent.click(screen.getByTestId('previous-move-button'));
      
      expect(defaultProps.onPrevious).toHaveBeenCalledTimes(1);
    });

    it('calls onNext when next button is clicked', () => {
      render(<MoveNavigationControls {...defaultProps} currentMoveIndex={5} />);
      
      fireEvent.click(screen.getByTestId('next-move-button'));
      
      expect(defaultProps.onNext).toHaveBeenCalledTimes(1);
    });

    it('calls onLast when last button is clicked', () => {
      render(<MoveNavigationControls {...defaultProps} currentMoveIndex={5} />);
      
      fireEvent.click(screen.getByTestId('last-move-button'));
      
      expect(defaultProps.onLast).toHaveBeenCalledTimes(1);
    });

    it('calls onTogglePlay when play/pause button is clicked', () => {
      const onTogglePlay = jest.fn();
      render(<MoveNavigationControls {...defaultProps} onTogglePlay={onTogglePlay} />);
      
      fireEvent.click(screen.getByTestId('play-pause-button'));
      
      expect(onTogglePlay).toHaveBeenCalledTimes(1);
    });
  });

  describe('Play Mode', () => {
    it('shows play icon when not in play mode', () => {
      const onTogglePlay = jest.fn();
      render(<MoveNavigationControls {...defaultProps} onTogglePlay={onTogglePlay} playMode={false} />);
      
      expect(screen.getByTestId('play-pause-button')).toHaveTextContent('▶️');
    });

    it('shows pause icon when in play mode', () => {
      const onTogglePlay = jest.fn();
      render(<MoveNavigationControls {...defaultProps} onTogglePlay={onTogglePlay} playMode={true} />);
      
      expect(screen.getByTestId('play-pause-button')).toHaveTextContent('⏸');
    });

    it('applies playing class when in play mode', () => {
      const onTogglePlay = jest.fn();
      render(<MoveNavigationControls {...defaultProps} onTogglePlay={onTogglePlay} playMode={true} />);
      
      expect(screen.getByTestId('play-pause-button')).toHaveClass('playing');
    });
  });

  describe('Speed Control', () => {
    it('displays current speed value', () => {
      const onSpeedChange = jest.fn();
      render(<MoveNavigationControls {...defaultProps} onSpeedChange={onSpeedChange} playSpeed={500} />);
      
      expect(screen.getByTestId('speed-select')).toHaveValue('500');
    });

    it('calls onSpeedChange when speed is changed', () => {
      const onSpeedChange = jest.fn();
      render(<MoveNavigationControls {...defaultProps} onSpeedChange={onSpeedChange} />);
      
      fireEvent.change(screen.getByTestId('speed-select'), { target: { value: '2000' } });
      
      expect(onSpeedChange).toHaveBeenCalledWith(2000);
    });

    it('disables speed select when disabled', () => {
      const onSpeedChange = jest.fn();
      render(<MoveNavigationControls {...defaultProps} onSpeedChange={onSpeedChange} disabled={true} />);
      
      expect(screen.getByTestId('speed-select')).toBeDisabled();
    });
  });

  describe('Keyboard Navigation', () => {
    it('calls onPrevious when left arrow key is pressed', () => {
      render(<MoveNavigationControls {...defaultProps} />);
      
      fireEvent.keyDown(window, { key: 'ArrowLeft' });
      
      expect(defaultProps.onPrevious).toHaveBeenCalledTimes(1);
    });

    it('calls onNext when right arrow key is pressed', () => {
      render(<MoveNavigationControls {...defaultProps} />);
      
      fireEvent.keyDown(window, { key: 'ArrowRight' });
      
      expect(defaultProps.onNext).toHaveBeenCalledTimes(1);
    });

    it('calls onFirst when Home key is pressed', () => {
      render(<MoveNavigationControls {...defaultProps} />);
      
      fireEvent.keyDown(window, { key: 'Home' });
      
      expect(defaultProps.onFirst).toHaveBeenCalledTimes(1);
    });

    it('calls onLast when End key is pressed', () => {
      render(<MoveNavigationControls {...defaultProps} />);
      
      fireEvent.keyDown(window, { key: 'End' });
      
      expect(defaultProps.onLast).toHaveBeenCalledTimes(1);
    });

    it('calls onTogglePlay when space key is pressed', () => {
      const onTogglePlay = jest.fn();
      render(<MoveNavigationControls {...defaultProps} onTogglePlay={onTogglePlay} />);
      
      fireEvent.keyDown(window, { key: ' ' });
      
      expect(onTogglePlay).toHaveBeenCalledTimes(1);
    });

    it('calls onJumpToMove(-1) when Escape key is pressed', () => {
      render(<MoveNavigationControls {...defaultProps} />);
      
      fireEvent.keyDown(window, { key: 'Escape' });
      
      expect(defaultProps.onJumpToMove).toHaveBeenCalledWith(-1);
    });

    it('does not handle keyboard events when disabled', () => {
      render(<MoveNavigationControls {...defaultProps} disabled={true} />);
      
      fireEvent.keyDown(window, { key: 'ArrowLeft' });
      
      expect(defaultProps.onPrevious).not.toHaveBeenCalled();
    });

    it('does not handle keyboard events when typing in input', () => {
      render(
        <div>
          <input data-testid="text-input" />
          <MoveNavigationControls {...defaultProps} />
        </div>
      );
      
      const input = screen.getByTestId('text-input');
      input.focus();
      
      fireEvent.keyDown(input, { key: 'ArrowLeft' });
      
      expect(defaultProps.onPrevious).not.toHaveBeenCalled();
    });
  });

  describe('Edge Cases', () => {
    it('handles zero total moves', () => {
      render(<MoveNavigationControls {...defaultProps} totalMoves={0} currentMoveIndex={null} />);
      
      expect(screen.getByTestId('move-indicator')).toHaveTextContent('0 moves total');
      expect(screen.getByTestId('first-move-button')).toBeDisabled();
      expect(screen.getByTestId('previous-move-button')).toBeDisabled();
      expect(screen.getByTestId('next-move-button')).toBeDisabled();
      expect(screen.getByTestId('last-move-button')).toBeDisabled();
    });

    it('handles single move', () => {
      render(<MoveNavigationControls {...defaultProps} totalMoves={1} currentMoveIndex={0} />);
      
      expect(screen.getByTestId('move-indicator')).toHaveTextContent('Move 1 of 1');
      expect(screen.getByTestId('first-move-button')).toBeDisabled();
      expect(screen.getByTestId('previous-move-button')).toBeDisabled();
      expect(screen.getByTestId('next-move-button')).toBeDisabled();
      expect(screen.getByTestId('last-move-button')).toBeDisabled();
    });

    it('handles null currentMoveIndex correctly', () => {
      render(<MoveNavigationControls {...defaultProps} currentMoveIndex={null} />);
      
      expect(screen.getByTestId('move-indicator')).toHaveTextContent('10 moves total');
      expect(screen.getByTestId('first-move-button')).toBeDisabled();
      expect(screen.getByTestId('previous-move-button')).toBeDisabled();
      expect(screen.getByTestId('next-move-button')).toBeDisabled();
      expect(screen.getByTestId('last-move-button')).toBeDisabled();
    });
  });

  describe('Accessibility', () => {
    it('has proper button titles for accessibility', () => {
      render(<MoveNavigationControls {...defaultProps} />);
      
      expect(screen.getByTestId('first-move-button')).toHaveAttribute('title', 'First move (Home)');
      expect(screen.getByTestId('previous-move-button')).toHaveAttribute('title', 'Previous move (←)');
      expect(screen.getByTestId('next-move-button')).toHaveAttribute('title', 'Next move (→)');
      expect(screen.getByTestId('last-move-button')).toHaveAttribute('title', 'Last move (End)');
    });

    it('has proper play/pause button titles', () => {
      const onTogglePlay = jest.fn();
      
      const { rerender } = render(
        <MoveNavigationControls {...defaultProps} onTogglePlay={onTogglePlay} playMode={false} />
      );
      
      expect(screen.getByTestId('play-pause-button')).toHaveAttribute('title', 'Play (Space)');
      
      rerender(
        <MoveNavigationControls {...defaultProps} onTogglePlay={onTogglePlay} playMode={true} />
      );
      
      expect(screen.getByTestId('play-pause-button')).toHaveAttribute('title', 'Pause (Space)');
    });

    it('has proper label for speed select', () => {
      const onSpeedChange = jest.fn();
      render(<MoveNavigationControls {...defaultProps} onSpeedChange={onSpeedChange} />);
      
      expect(screen.getByLabelText('Speed:')).toBeInTheDocument();
    });
  });
});