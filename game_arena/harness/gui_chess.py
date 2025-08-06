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

"""Chess-specific GUI implementation using the chess-board package."""

import time
from typing import Optional, List, Tuple

from absl import logging
from game_arena.harness import gui


# Try to import chess GUI dependencies
try:
  from chessboard import display
  import pygame
  import chess
  CHESS_GUI_AVAILABLE = True
except ImportError:
  CHESS_GUI_AVAILABLE = False
  logging.info("Chess GUI dependencies not available. Install with: pip install chess-board")


class ChessBoardHandle(gui.GameBoardHandle):
  """Handle for chess board display."""
  
  def __init__(self, board_handle):
    """Initialize chess board handle.
    
    Args:
      board_handle: The underlying chess board handle from chessboard package.
    """
    self.board_handle = board_handle


class ChessGUI:
  """Chess GUI implementation using chess-board package."""
  
  def __init__(self):
    """Initialize Chess GUI."""
    if not CHESS_GUI_AVAILABLE:
      raise gui.GUIError(
          "Chess GUI dependencies not available. "
          "Install with: pip install chess-board"
      )

  def start(self, game_state: str, *, caption: Optional[str] = None) -> ChessBoardHandle:
    """Start the chess board GUI.
    
    Args:
      game_state: FEN string representing the chess position.
      caption: Optional window caption.
      
    Returns:
      ChessBoardHandle for the created board.
      
    Raises:
      GUIError: If the GUI cannot be started.
    """
    try:
      default_caption = "Game Arena Chess"
      window_caption = caption or default_caption
      
      board_handle = display.start(game_state, caption=window_caption)
      logging.info(f"Chess GUI started with caption: {window_caption}")
      
      return ChessBoardHandle(board_handle)
      
    except Exception as e:
      raise gui.GUIError(f"Failed to start chess GUI: {e}") from e

  def update(self, game_state: str, board: ChessBoardHandle) -> None:
    """Update the chess board with new position.
    
    Args:
      game_state: FEN string representing the new chess position.
      board: Chess board handle from start().
      
    Raises:
      GUIError: If the update fails.
    """
    try:
      display.update(game_state, board.board_handle)
    except Exception as e:
      raise gui.GUIError(f"Failed to update chess board: {e}") from e

  def check_for_quit(self, board: ChessBoardHandle) -> bool:
    """Check if the chess board window was closed.
    
    Args:
      board: Chess board handle from start().
      
    Returns:
      True if the window was closed, False otherwise.
    """
    try:
      return display.check_for_quit()
    except Exception as e:
      logging.warning(f"Error checking for quit: {e}")
      return False

  def set_caption(self, board: ChessBoardHandle, caption: str) -> None:
    """Set the chess board window caption.
    
    Args:
      board: Chess board handle from start().
      caption: New caption text.
    """
    try:
      pygame.display.set_caption(caption)
    except Exception as e:
      logging.warning(f"Failed to set caption: {e}")

  def terminate(self, board: ChessBoardHandle) -> None:
    """Close the chess board GUI.
    
    Args:
      board: Chess board handle from start().
    """
    try:
      display.terminate()
      logging.info("Chess GUI terminated")
    except Exception as e:
      logging.warning(f"Error terminating chess GUI: {e}")


class ChessGUIWithPlayerInfo(ChessGUI):
  """Enhanced chess GUI that shows player information in window titles."""
  
  def __init__(self, player1_name: str = "Player 1", player2_name: str = "Player 2"):
    """Initialize chess GUI with player information.
    
    Args:
      player1_name: Name/model for player 1 (Black).
      player2_name: Name/model for player 2 (White).
    """
    super().__init__()
    self.player1_name = player1_name  # Black
    self.player2_name = player2_name  # White
    self.move_count = 0
    
  def start(self, game_state: str, *, caption: Optional[str] = None) -> ChessBoardHandle:
    """Start chess GUI with player information in title."""
    if caption is None:
      caption = f"Game Arena Chess - White: {self.player2_name} vs Black: {self.player1_name}"
    
    return super().start(game_state, caption=caption)
  
  def update_with_move_info(
      self, 
      game_state: str, 
      board: ChessBoardHandle, 
      current_player: int,
      move_number: int,
      status: str = ""
  ) -> None:
    """Update board and window title with current move information.
    
    Args:
      game_state: FEN string for the new position.
      board: Chess board handle.
      current_player: 0 for Black, 1 for White.
      move_number: Current move number.
      status: Optional status message.
    """
    # Update the board position
    self.update(game_state, board)
    
    # Update window title with current player info
    player_name = "Black" if current_player == 0 else "White"
    player_model = self.player1_name if current_player == 0 else self.player2_name
    
    if status:
      title = f"Game Arena Chess - {player_name}: {player_model} | Move {move_number} | {status}"
    else:
      title = f"Game Arena Chess - {player_name}: {player_model} | Move {move_number} | {player_name} to move"
    
    self.set_caption(board, title)
  
  def show_game_result(self, board: ChessBoardHandle, result: str) -> None:
    """Update window title to show final game result.
    
    Args:
      board: Chess board handle.
      result: Game result description.
    """
    title = f"Game Arena Chess - GAME OVER: {result}"
    self.set_caption(board, title)


def create_chess_gui(
    player1_name: Optional[str] = None, 
    player2_name: Optional[str] = None,
    enhanced: bool = False
) -> gui.GameGUI:
  """Create a chess GUI instance.
  
  Args:
    player1_name: Optional name for player 1 (Black).
    player2_name: Optional name for player 2 (White).
    enhanced: Whether to use the enhanced GUI (ignored, returns ChessGUIWithPlayerInfo).
    
  Returns:
    Chess GUI instance.
    
  Raises:
    GUIError: If chess GUI is not available.
  """
  if not CHESS_GUI_AVAILABLE:
    raise gui.GUIError(
        "Chess GUI not available. Install with: pip install chess-board"
    )
  
  # Always use ChessGUIWithPlayerInfo if player names are provided
  if player1_name or player2_name:
    return ChessGUIWithPlayerInfo(
        player1_name or "Player 1 (Black)",
        player2_name or "Player 2 (White)"
    )
  else:
    return ChessGUI()


def is_chess_gui_available() -> bool:
  """Check if chess GUI dependencies are available.
  
  Returns:
    True if chess GUI can be used, False otherwise.
  """
  return CHESS_GUI_AVAILABLE