# Copyright 2025 The game_arena Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Game GUI protocol and utilities for visual game display."""

from typing import Any, Optional, Protocol, runtime_checkable

from absl import logging


@runtime_checkable
class GameBoardHandle(Protocol):
  """Protocol for game board display handles."""
  pass


@runtime_checkable
class GameGUI(Protocol):
  """Protocol for game visualization backends."""

  def start(self, game_state: str, *, caption: Optional[str] = None) -> GameBoardHandle:
    """Start the GUI and return a board handle.
    
    Args:
      game_state: Initial game state (e.g., FEN for chess).
      caption: Optional window caption/title.
      
    Returns:
      A handle for the game board display.
      
    Raises:
      GUIError: If the GUI cannot be initialized.
    """
    ...

  def update(self, game_state: str, board: GameBoardHandle) -> None:
    """Update the board display with new game state.
    
    Args:
      game_state: New game state to display.
      board: Board handle from start().
      
    Raises:
      GUIError: If the update fails.
    """
    ...

  def check_for_quit(self, board: GameBoardHandle) -> bool:
    """Check if the user has requested to quit/close the GUI.
    
    Args:
      board: Board handle from start().
      
    Returns:
      True if user wants to quit, False otherwise.
    """
    ...

  def set_caption(self, board: GameBoardHandle, caption: str) -> None:
    """Set the window caption/title.
    
    Args:
      board: Board handle from start().
      caption: New caption text.
    """
    ...

  def terminate(self, board: GameBoardHandle) -> None:
    """Clean up and close the GUI.
    
    Args:
      board: Board handle from start().
    """
    ...


class GUIError(Exception):
  """Exception raised when GUI operations fail."""
  pass


class NoOpGUI:
  """No-operation GUI implementation for headless operation."""

  def start(self, game_state: str, *, caption: Optional[str] = None) -> 'NoOpBoardHandle':
    """Start no-op GUI."""
    logging.info("NoOpGUI: Starting headless mode")
    return NoOpBoardHandle()

  def update(self, game_state: str, board: 'NoOpBoardHandle') -> None:
    """No-op update."""
    pass

  def check_for_quit(self, board: 'NoOpBoardHandle') -> bool:
    """No-op quit check."""
    return False

  def set_caption(self, board: 'NoOpBoardHandle', caption: str) -> None:
    """No-op caption setting."""
    pass

  def terminate(self, board: 'NoOpBoardHandle') -> None:
    """No-op termination."""
    logging.info("NoOpGUI: Terminating headless mode")


class NoOpBoardHandle:
  """No-operation board handle for headless mode."""
  pass


class GUIManager:
  """Manager for GUI instances with fallback support."""

  def __init__(self, gui: Optional[GameGUI] = None):
    """Initialize GUI manager.
    
    Args:
      gui: GUI implementation to use. If None, uses NoOpGUI.
    """
    self._gui = gui or NoOpGUI()
    self._board_handle: Optional[GameBoardHandle] = None

  @property
  def is_active(self) -> bool:
    """True if GUI is active (not NoOp)."""
    return not isinstance(self._gui, NoOpGUI)

  def start(self, game_state: str, *, caption: Optional[str] = None) -> None:
    """Start the GUI if not already started."""
    if self._board_handle is None:
      try:
        self._board_handle = self._gui.start(game_state, caption=caption)
        if self.is_active:
          logging.info("GUI started successfully")
      except Exception as e:
        logging.warning(f"GUI failed to start: {e}. Falling back to headless mode.")
        self._gui = NoOpGUI()
        self._board_handle = self._gui.start(game_state, caption=caption)

  def update(self, game_state: str) -> None:
    """Update the GUI with new game state."""
    if self._board_handle is not None:
      try:
        self._gui.update(game_state, self._board_handle)
      except Exception as e:
        logging.warning(f"GUI update failed: {e}")

  def check_for_quit(self) -> bool:
    """Check if user wants to quit."""
    if self._board_handle is not None:
      try:
        return self._gui.check_for_quit(self._board_handle)
      except Exception as e:
        logging.warning(f"GUI quit check failed: {e}")
    return False

  def set_caption(self, caption: str) -> None:
    """Set window caption."""
    if self._board_handle is not None:
      try:
        self._gui.set_caption(self._board_handle, caption)
      except Exception as e:
        logging.warning(f"GUI caption setting failed: {e}")

  def terminate(self) -> None:
    """Terminate the GUI."""
    if self._board_handle is not None:
      try:
        self._gui.terminate(self._board_handle)
        if self.is_active:
          logging.info("GUI terminated successfully")
      except Exception as e:
        logging.warning(f"GUI termination failed: {e}")
      finally:
        self._board_handle = None


def create_gui_manager(gui_type: str = "auto") -> GUIManager:
  """Create a GUI manager with the specified type.
  
  Args:
    gui_type: Type of GUI to create. Options:
      - "auto": Auto-detect available GUI
      - "chess": Chess-specific GUI
      - "none": No GUI (headless)
      
  Returns:
    GUIManager instance with appropriate GUI backend.
  """
  if gui_type == "none":
    return GUIManager(NoOpGUI())
  
  if gui_type in ("auto", "chess"):
    # Try to import chess GUI
    try:
      from game_arena.harness import gui_chess
      logging.info("Using chess GUI backend")
      return GUIManager(gui_chess.ChessGUI())
    except ImportError as e:
      logging.info(f"Chess GUI not available: {e}. Using headless mode.")
      return GUIManager(NoOpGUI())
  
  raise ValueError(f"Unknown GUI type: {gui_type}")