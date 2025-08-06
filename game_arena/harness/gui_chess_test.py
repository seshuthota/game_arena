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

"""Tests for Chess GUI implementation."""

from unittest import mock

from absl.testing import absltest
from game_arena.harness import gui
from game_arena.harness import gui_chess


class ChessGUITest(absltest.TestCase):
  """Test suite for ChessGUI."""

  def setUp(self):
    super().setUp()
    # Mock the chess GUI availability
    self.chess_available_patcher = mock.patch.object(
        gui_chess, 'CHESS_GUI_AVAILABLE', True
    )
    self.chess_available_patcher.start()
    
    # Mock the chessboard display module
    self.mock_display = mock.MagicMock()
    self.display_patcher = mock.patch.object(gui_chess, 'display', self.mock_display)
    self.display_patcher.start()
    
    # Mock pygame
    self.mock_pygame = mock.MagicMock()
    self.pygame_patcher = mock.patch.object(gui_chess, 'pygame', self.mock_pygame)
    self.pygame_patcher.start()

  def tearDown(self):
    self.pygame_patcher.stop()
    self.display_patcher.stop()
    self.chess_available_patcher.stop()
    super().tearDown()

  def test_chess_gui_init_success(self):
    """Test successful ChessGUI initialization."""
    chess_gui = gui_chess.ChessGUI()
    self.assertIsInstance(chess_gui, gui_chess.ChessGUI)

  def test_chess_gui_init_without_dependencies(self):
    """Test ChessGUI initialization fails without dependencies."""
    with mock.patch.object(gui_chess, 'CHESS_GUI_AVAILABLE', False):
      with self.assertRaises(gui.GUIError) as context:
        gui_chess.ChessGUI()
      
      self.assertIn("Chess GUI dependencies not available", str(context.exception))

  def test_start_with_default_caption(self):
    """Test starting chess GUI with default caption."""
    chess_gui = gui_chess.ChessGUI()
    mock_board_handle = mock.MagicMock()
    self.mock_display.start.return_value = mock_board_handle
    
    fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    board_handle = chess_gui.start(fen)
    
    self.assertIsInstance(board_handle, gui_chess.ChessBoardHandle)
    self.mock_display.start.assert_called_once_with(fen, caption="Game Arena Chess")

  def test_start_with_custom_caption(self):
    """Test starting chess GUI with custom caption."""
    chess_gui = gui_chess.ChessGUI()
    mock_board_handle = mock.MagicMock()
    self.mock_display.start.return_value = mock_board_handle
    
    fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    custom_caption = "Custom Chess Game"
    board_handle = chess_gui.start(fen, caption=custom_caption)
    
    self.assertIsInstance(board_handle, gui_chess.ChessBoardHandle)
    self.mock_display.start.assert_called_once_with(fen, caption=custom_caption)

  def test_start_failure(self):
    """Test start failure handling."""
    chess_gui = gui_chess.ChessGUI()
    self.mock_display.start.side_effect = Exception("Display start failed")
    
    fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    
    with self.assertRaises(gui.GUIError) as context:
      chess_gui.start(fen)
    
    self.assertIn("Failed to start chess GUI", str(context.exception))

  def test_update_success(self):
    """Test successful board update."""
    chess_gui = gui_chess.ChessGUI()
    mock_board_handle = mock.MagicMock()
    board_handle = gui_chess.ChessBoardHandle(mock_board_handle)
    
    new_fen = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1"
    chess_gui.update(new_fen, board_handle)
    
    self.mock_display.update.assert_called_once_with(new_fen, mock_board_handle)

  def test_update_failure(self):
    """Test update failure handling."""
    chess_gui = gui_chess.ChessGUI()
    mock_board_handle = mock.MagicMock()
    board_handle = gui_chess.ChessBoardHandle(mock_board_handle)
    
    self.mock_display.update.side_effect = Exception("Update failed")
    
    with self.assertRaises(gui.GUIError) as context:
      chess_gui.update("test_fen", board_handle)
    
    self.assertIn("Failed to update chess board", str(context.exception))

  def test_check_for_quit_success(self):
    """Test successful quit check."""
    chess_gui = gui_chess.ChessGUI()
    board_handle = gui_chess.ChessBoardHandle(mock.MagicMock())
    
    self.mock_display.check_for_quit.return_value = True
    result = chess_gui.check_for_quit(board_handle)
    
    self.assertTrue(result)
    self.mock_display.check_for_quit.assert_called_once()

  def test_check_for_quit_failure(self):
    """Test quit check with exception."""
    chess_gui = gui_chess.ChessGUI()
    board_handle = gui_chess.ChessBoardHandle(mock.MagicMock())
    
    self.mock_display.check_for_quit.side_effect = Exception("Quit check failed")
    result = chess_gui.check_for_quit(board_handle)
    
    self.assertFalse(result)  # Should return False on error

  def test_set_caption_success(self):
    """Test successful caption setting."""
    chess_gui = gui_chess.ChessGUI()
    board_handle = gui_chess.ChessBoardHandle(mock.MagicMock())
    
    chess_gui.set_caption(board_handle, "New Caption")
    
    self.mock_pygame.display.set_caption.assert_called_once_with("New Caption")

  def test_set_caption_failure(self):
    """Test caption setting with exception."""
    chess_gui = gui_chess.ChessGUI()
    board_handle = gui_chess.ChessBoardHandle(mock.MagicMock())
    
    self.mock_pygame.display.set_caption.side_effect = Exception("Caption failed")
    
    # Should not raise exception, just log warning
    chess_gui.set_caption(board_handle, "New Caption")

  def test_terminate_success(self):
    """Test successful termination."""
    chess_gui = gui_chess.ChessGUI()
    board_handle = gui_chess.ChessBoardHandle(mock.MagicMock())
    
    chess_gui.terminate(board_handle)
    
    self.mock_display.terminate.assert_called_once()

  def test_terminate_failure(self):
    """Test termination with exception."""
    chess_gui = gui_chess.ChessGUI()
    board_handle = gui_chess.ChessBoardHandle(mock.MagicMock())
    
    self.mock_display.terminate.side_effect = Exception("Terminate failed")
    
    # Should not raise exception, just log warning
    chess_gui.terminate(board_handle)


class ChessGUIWithPlayerInfoTest(absltest.TestCase):
  """Test suite for ChessGUIWithPlayerInfo."""

  def setUp(self):
    super().setUp()
    # Mock dependencies like in ChessGUITest
    self.chess_available_patcher = mock.patch.object(
        gui_chess, 'CHESS_GUI_AVAILABLE', True
    )
    self.chess_available_patcher.start()
    
    self.mock_display = mock.MagicMock()
    self.display_patcher = mock.patch.object(gui_chess, 'display', self.mock_display)
    self.display_patcher.start()
    
    self.mock_pygame = mock.MagicMock()
    self.pygame_patcher = mock.patch.object(gui_chess, 'pygame', self.mock_pygame)
    self.pygame_patcher.start()

  def tearDown(self):
    self.pygame_patcher.stop()
    self.display_patcher.stop()
    self.chess_available_patcher.stop()
    super().tearDown()

  def test_init_with_player_names(self):
    """Test initialization with custom player names."""
    chess_gui = gui_chess.ChessGUIWithPlayerInfo(
        player1_name="Claude", 
        player2_name="GPT-4"
    )
    
    self.assertEqual(chess_gui.player1_name, "Claude")
    self.assertEqual(chess_gui.player2_name, "GPT-4")

  def test_init_with_default_names(self):
    """Test initialization with default player names."""
    chess_gui = gui_chess.ChessGUIWithPlayerInfo()
    
    self.assertEqual(chess_gui.player1_name, "Player 1")
    self.assertEqual(chess_gui.player2_name, "Player 2")

  def test_start_with_player_info_caption(self):
    """Test start generates caption with player info."""
    chess_gui = gui_chess.ChessGUIWithPlayerInfo(
        player1_name="Claude", 
        player2_name="GPT-4"
    )
    mock_board_handle = mock.MagicMock()
    self.mock_display.start.return_value = mock_board_handle
    
    fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    chess_gui.start(fen)
    
    expected_caption = "Game Arena Chess - White: GPT-4 vs Black: Claude"
    self.mock_display.start.assert_called_once_with(fen, caption=expected_caption)

  def test_update_with_move_info(self):
    """Test update with move information."""
    chess_gui = gui_chess.ChessGUIWithPlayerInfo(
        player1_name="Claude", 
        player2_name="GPT-4"
    )
    mock_board_handle = mock.MagicMock()
    board_handle = gui_chess.ChessBoardHandle(mock_board_handle)
    
    new_fen = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1"
    chess_gui.update_with_move_info(new_fen, board_handle, current_player=1, move_number=1)
    
    # Should update board
    self.mock_display.update.assert_called_once_with(new_fen, mock_board_handle)
    
    # Should set caption with move info
    expected_caption = "Game Arena Chess - White: GPT-4 | Move 1 | White to move"
    self.mock_pygame.display.set_caption.assert_called_with(expected_caption)

  def test_update_with_move_info_and_status(self):
    """Test update with move information and custom status."""
    chess_gui = gui_chess.ChessGUIWithPlayerInfo(
        player1_name="Claude", 
        player2_name="GPT-4"
    )
    board_handle = gui_chess.ChessBoardHandle(mock.MagicMock())
    
    chess_gui.update_with_move_info(
        "test_fen", board_handle, 
        current_player=0, move_number=5, status="Thinking..."
    )
    
    expected_caption = "Game Arena Chess - Black: Claude | Move 5 | Thinking..."
    self.mock_pygame.display.set_caption.assert_called_with(expected_caption)

  def test_show_game_result(self):
    """Test showing game result."""
    chess_gui = gui_chess.ChessGUIWithPlayerInfo()
    board_handle = gui_chess.ChessBoardHandle(mock.MagicMock())
    
    chess_gui.show_game_result(board_handle, "Claude (Black) WINS!")
    
    expected_caption = "Game Arena Chess - GAME OVER: Claude (Black) WINS!"
    self.mock_pygame.display.set_caption.assert_called_with(expected_caption)


class CreateChessGUITest(absltest.TestCase):
  """Test suite for create_chess_gui function."""

  def test_create_basic_chess_gui(self):
    """Test creating basic chess GUI without player names."""
    with mock.patch.object(gui_chess, 'CHESS_GUI_AVAILABLE', True):
      chess_gui = gui_chess.create_chess_gui()
      self.assertIsInstance(chess_gui, gui_chess.ChessGUI)
      self.assertNotIsInstance(chess_gui, gui_chess.ChessGUIWithPlayerInfo)

  def test_create_chess_gui_with_player_names(self):
    """Test creating chess GUI with player names."""
    with mock.patch.object(gui_chess, 'CHESS_GUI_AVAILABLE', True):
      chess_gui = gui_chess.create_chess_gui("Alice", "Bob")
      self.assertIsInstance(chess_gui, gui_chess.ChessGUIWithPlayerInfo)
      self.assertEqual(chess_gui.player1_name, "Alice")
      self.assertEqual(chess_gui.player2_name, "Bob")

  def test_create_chess_gui_with_partial_names(self):
    """Test creating chess GUI with only one player name."""
    with mock.patch.object(gui_chess, 'CHESS_GUI_AVAILABLE', True):
      chess_gui = gui_chess.create_chess_gui(player1_name="Alice")
      self.assertIsInstance(chess_gui, gui_chess.ChessGUIWithPlayerInfo)
      self.assertEqual(chess_gui.player1_name, "Alice")
      self.assertEqual(chess_gui.player2_name, "Player 2 (White)")

  def test_create_chess_gui_not_available(self):
    """Test creating chess GUI when not available."""
    with mock.patch.object(gui_chess, 'CHESS_GUI_AVAILABLE', False):
      with self.assertRaises(gui.GUIError) as context:
        gui_chess.create_chess_gui()
      
      self.assertIn("Chess GUI not available", str(context.exception))


class IsChessGUIAvailableTest(absltest.TestCase):
  """Test suite for is_chess_gui_available function."""

  def test_chess_gui_available(self):
    """Test when chess GUI is available."""
    with mock.patch.object(gui_chess, 'CHESS_GUI_AVAILABLE', True):
      self.assertTrue(gui_chess.is_chess_gui_available())

  def test_chess_gui_not_available(self):
    """Test when chess GUI is not available."""
    with mock.patch.object(gui_chess, 'CHESS_GUI_AVAILABLE', False):
      self.assertFalse(gui_chess.is_chess_gui_available())


if __name__ == "__main__":
  absltest.main()