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

"""Tests for GUI protocol and utilities."""

from unittest import mock

from absl.testing import absltest
from game_arena.harness import gui


class MockGUI:
  """Mock GUI implementation for testing."""
  
  def __init__(self, should_fail: bool = False):
    self.should_fail = should_fail
    self.started = False
    self.terminated = False
    self.updates = []
    self.captions = []
    
  def start(self, game_state: str, *, caption=None):
    if self.should_fail:
      raise gui.GUIError("Mock GUI start failure")
    self.started = True
    return MockBoardHandle()
    
  def update(self, game_state: str, board):
    if self.should_fail:
      raise gui.GUIError("Mock GUI update failure")
    self.updates.append(game_state)
    
  def check_for_quit(self, board):
    return False
    
  def set_caption(self, board, caption: str):
    self.captions.append(caption)
    
  def terminate(self, board):
    self.terminated = True


class MockBoardHandle:
  """Mock board handle for testing."""
  pass


class NoOpGUITest(absltest.TestCase):
  """Test suite for NoOpGUI."""

  def test_noop_gui_operations(self):
    """Test that NoOpGUI operations work without errors."""
    gui_impl = gui.NoOpGUI()
    
    # Test start
    board = gui_impl.start("test_state", caption="Test Caption")
    self.assertIsInstance(board, gui.NoOpBoardHandle)
    
    # Test update
    gui_impl.update("new_state", board)  # Should not raise
    
    # Test check_for_quit
    result = gui_impl.check_for_quit(board)
    self.assertFalse(result)
    
    # Test set_caption
    gui_impl.set_caption(board, "New Caption")  # Should not raise
    
    # Test terminate
    gui_impl.terminate(board)  # Should not raise


class GUIManagerTest(absltest.TestCase):
  """Test suite for GUIManager."""

  def test_gui_manager_with_working_gui(self):
    """Test GUIManager with a working GUI implementation."""
    mock_gui = MockGUI()
    manager = gui.GUIManager(mock_gui)
    
    # Test is_active
    self.assertTrue(manager.is_active)
    
    # Test start
    manager.start("initial_state", caption="Test Game")
    self.assertTrue(mock_gui.started)
    
    # Test update
    manager.update("new_state")
    self.assertEqual(mock_gui.updates, ["new_state"])
    
    # Test check_for_quit
    result = manager.check_for_quit()
    self.assertFalse(result)
    
    # Test set_caption
    manager.set_caption("New Title")
    self.assertEqual(mock_gui.captions, ["New Title"])
    
    # Test terminate
    manager.terminate()
    self.assertTrue(mock_gui.terminated)

  def test_gui_manager_with_failing_gui(self):
    """Test GUIManager handles GUI failures gracefully."""
    mock_gui = MockGUI(should_fail=True)
    manager = gui.GUIManager(mock_gui)
    
    # Start should fallback to NoOpGUI on failure
    manager.start("initial_state")
    self.assertFalse(manager.is_active)  # Should have fallen back to NoOp
    
    # Operations should continue to work (with NoOp)
    manager.update("new_state")  # Should not raise
    manager.set_caption("Test")  # Should not raise
    manager.terminate()  # Should not raise

  def test_gui_manager_with_none_gui(self):
    """Test GUIManager with None (defaults to NoOpGUI)."""
    manager = gui.GUIManager(None)
    
    self.assertFalse(manager.is_active)
    
    manager.start("test_state")
    manager.update("new_state")
    self.assertFalse(manager.check_for_quit())
    manager.set_caption("Test")
    manager.terminate()

  def test_gui_manager_double_start(self):
    """Test that starting GUI twice doesn't create multiple instances."""
    mock_gui = MockGUI()
    manager = gui.GUIManager(mock_gui)
    
    # First start
    manager.start("state1")
    self.assertTrue(mock_gui.started)
    
    # Second start should be ignored
    mock_gui.started = False
    manager.start("state2")
    self.assertFalse(mock_gui.started)  # Should not have started again

  def test_operations_before_start(self):
    """Test that operations before start() are handled gracefully."""
    mock_gui = MockGUI()
    manager = gui.GUIManager(mock_gui)
    
    # These should not raise errors
    manager.update("state")
    self.assertFalse(manager.check_for_quit())
    manager.set_caption("Test")
    manager.terminate()


class CreateGUIManagerTest(absltest.TestCase):
  """Test suite for create_gui_manager function."""

  def test_create_none_gui(self):
    """Test creating a no-op GUI manager."""
    manager = gui.create_gui_manager("none")
    self.assertFalse(manager.is_active)

  def test_create_auto_gui_without_chess(self):
    """Test auto GUI creation when chess GUI is not available."""
    with mock.patch('game_arena.harness.gui.logging'):
      manager = gui.create_gui_manager("auto")
      # Should fallback to NoOpGUI when chess GUI import fails
      self.assertFalse(manager.is_active)

  def test_create_chess_gui_without_dependencies(self):
    """Test chess GUI creation when dependencies are not available."""
    with mock.patch('game_arena.harness.gui.logging'):
      manager = gui.create_gui_manager("chess")
      # Should fallback to NoOpGUI when chess GUI import fails
      self.assertFalse(manager.is_active)

  @mock.patch('game_arena.harness.gui_chess.ChessGUI')
  @mock.patch('game_arena.harness.gui.gui_chess')
  def test_create_auto_gui_with_chess(self, mock_gui_chess, mock_chess_gui):
    """Test auto GUI creation when chess GUI is available."""
    # Mock successful import
    mock_chess_gui.return_value = MockGUI()
    
    manager = gui.create_gui_manager("auto")
    self.assertTrue(manager.is_active)

  def test_create_invalid_gui_type(self):
    """Test that invalid GUI type raises ValueError."""
    with self.assertRaises(ValueError) as context:
      gui.create_gui_manager("invalid_type")
    
    self.assertIn("Unknown GUI type", str(context.exception))


class GUIErrorTest(absltest.TestCase):
  """Test suite for GUIError exception."""

  def test_gui_error_creation(self):
    """Test GUIError exception creation and inheritance."""
    error = gui.GUIError("Test error message")
    self.assertIsInstance(error, Exception)
    self.assertEqual(str(error), "Test error message")

  def test_gui_error_with_cause(self):
    """Test GUIError with underlying cause."""
    cause = ValueError("Original error")
    error = gui.GUIError("Wrapper error") from cause
    
    self.assertEqual(str(error), "Wrapper error")
    self.assertIs(error.__cause__, cause)


if __name__ == "__main__":
  absltest.main()