/**
 * Test wrapper for MoveNavigationControls that matches the test interface
 * This is used by e2e tests to provide a simpler API
 */

import React, { useState, useEffect } from 'react';
import { MoveNavigationControls, MoveNavigationControlsProps } from './MoveNavigationControls';

interface MoveNavigationControlsWrapperProps {
  totalMoves: number;
  currentMove: number;
  onMoveChange: (moveIndex: number) => void;
  autoplayInterval?: number;
}

const MoveNavigationControlsWrapper: React.FC<MoveNavigationControlsWrapperProps> = ({
  totalMoves,
  currentMove,
  onMoveChange,
  autoplayInterval = 1000
}) => {
  const [playMode, setPlayMode] = useState(false);
  const [playSpeed, setPlaySpeed] = useState(autoplayInterval);

  // Auto-advance moves when in play mode
  useEffect(() => {
    if (playMode && currentMove < totalMoves) {
      const timer = setTimeout(() => {
        onMoveChange(currentMove + 1);
      }, playSpeed);
      return () => clearTimeout(timer);
    }
    if (playMode && currentMove >= totalMoves) {
      setPlayMode(false); // Stop when reaching the end
    }
  }, [playMode, currentMove, totalMoves, playSpeed, onMoveChange]);

  const handleFirst = () => {
    onMoveChange(0);
  };

  const handlePrevious = () => {
    if (currentMove > 0) {
      onMoveChange(currentMove - 1);
    }
  };

  const handleNext = () => {
    if (currentMove < totalMoves) {
      onMoveChange(currentMove + 1);
    }
  };

  const handleLast = () => {
    onMoveChange(totalMoves);
  };

  const handleJumpToMove = (index: number) => {
    onMoveChange(index);
  };

  const handleTogglePlay = () => {
    setPlayMode(!playMode);
  };

  const handleSpeedChange = (speed: number) => {
    setPlaySpeed(speed);
  };

  const navigationProps: MoveNavigationControlsProps = {
    currentMoveIndex: currentMove,
    totalMoves,
    onFirst: handleFirst,
    onPrevious: handlePrevious,
    onNext: handleNext,
    onLast: handleLast,
    onJumpToMove: handleJumpToMove,
    playMode,
    onTogglePlay: handleTogglePlay,
    playSpeed,
    onSpeedChange: handleSpeedChange,
    disabled: false
  };

  return <MoveNavigationControls {...navigationProps} />;
};

export default MoveNavigationControlsWrapper;