#!/usr/bin/env python3
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

"""
Enhanced demo of chess with comprehensive data collection and storage.

This demo extends the basic harness_demo.py to include full data collection
capabilities, storing game data, moves, and LLM interactions for analysis.
"""

import asyncio
import os
import time
import sys

# Load environment variables from .env file if it exists
try:
  from dotenv import load_dotenv
  load_dotenv()
except ImportError:
  # python-dotenv not installed, environment variables must be set manually
  pass

from absl import app
from absl import flags
from game_arena.harness import agent
from game_arena.harness import enhanced_parsers
from game_arena.harness import game_notation_examples
from game_arena.harness import gui
from game_arena.harness import llm_parsers
from game_arena.harness import model_generation_openrouter
from game_arena.harness import model_generation_sdk
from game_arena.harness import model_registry
from game_arena.harness import parsers
from game_arena.harness import prompt_generation
from game_arena.harness import prompts
from game_arena.harness import tournament_util
from game_arena.storage.tournament_integration import (
    create_tournament_collector,
    create_demo_players,
    determine_game_outcome
)
from game_arena.storage.models import GameOutcome
import termcolor

import pyspiel


colored = termcolor.colored

_NUM_MOVES = flags.DEFINE_integer(
    "num_moves",
    200,
    "Number of moves to play (games usually end naturally before this limit).",
)

# Model selection flags
_PLAYER_1_PROVIDER = flags.DEFINE_enum(
    "player1_provider",
    "registry",
    ["registry", "openrouter", "openai", "gemini", "anthropic"],
    "Provider for player 1 (Black). 'registry' uses ModelRegistry.",
)

_PLAYER_1_MODEL = flags.DEFINE_string(
    "player1_model",
    "GEMINI_2_5_FLASH",
    "Model for player 1. Examples: registry='GEMINI_2_5_FLASH', openrouter='anthropic/claude-3.5-sonnet', openai='gpt-4o-mini', gemini='gemini-2.5-flash'",
)

_PLAYER_2_PROVIDER = flags.DEFINE_enum(
    "player2_provider",
    "registry", 
    ["registry", "openrouter", "openai", "gemini", "anthropic"],
    "Provider for player 2 (White). 'registry' uses ModelRegistry enum name.",
)

_PLAYER_2_MODEL = flags.DEFINE_string(
    "player2_model",
    "OPENAI_GPT_4_1",
    "Model for player 2. Examples: registry='OPENAI_GPT_4_1', openrouter='openai/gpt-4o-mini', openai='gpt-4o-mini', gemini='gemini-2.5-flash'",
)

_PARSER_CHOICE = flags.DEFINE_enum_class(
    "parser_choice",
    tournament_util.ParserChoice.RULE_THEN_SOFT,
    tournament_util.ParserChoice,
    "Move parser to use.",
)

# GUI flags
_GUI = flags.DEFINE_boolean(
    "gui",
    False,
    "Whether to show visual chess board (requires chess-board package).",
)

_VERBOSE = flags.DEFINE_boolean(
    "verbose",
    True,
    "Whether to print detailed information.",
)

# Data collection flags
_ENABLE_DATA_COLLECTION = flags.DEFINE_boolean(
    "enable_data_collection",
    True,
    "Whether to enable comprehensive data collection and storage.",
)

_STORAGE_BACKEND = flags.DEFINE_enum(
    "storage_backend",
    "sqlite",
    ["sqlite", "postgresql"],
    "Storage backend to use for data collection.",
)

_DATABASE_PATH = flags.DEFINE_string(
    "database_path",
    "demo_tournament.db",
    "Path for SQLite database (when using sqlite backend).",
)

_DATABASE_URL = flags.DEFINE_string(
    "database_url",
    None,
    "PostgreSQL database URL (when using postgresql backend).",
)

_TOURNAMENT_NAME = flags.DEFINE_string(
    "tournament_name",
    "Game Arena Demo Tournament",
    "Name for the tournament (used in data collection).",
)


def create_model(provider: str, model_name: str, player_name: str):
  """Create a model instance based on provider and model name."""
  if provider == "registry":
    try:
      registry_model = getattr(model_registry.ModelRegistry, model_name)
      # For demo purposes, we'll use placeholder API keys
      # In real usage, these should be set via environment variables
      api_key = "demo-key"  # This will cause API calls to fail, but demo can still run
      return registry_model.build(api_key=api_key)
    except AttributeError:
      raise ValueError(f"Unknown model in registry: {model_name}")
  
  elif provider == "openrouter":
    return model_generation_openrouter.OpenRouterModel(
        model_name=model_name,
        model_options={"temperature": 0.7, "max_output_tokens": 1000}
    )
  
  elif provider == "openai":
    return model_generation_sdk.OpenAIChatCompletionsModel(
        model_name=model_name,
        model_options={"temperature": 0.7, "max_tokens": 1000}
    )
  
  elif provider == "gemini":
    return model_generation_sdk.AIStudioModel(
        model_name=model_name,
        model_options={"temperature": 0.7}
    )
  
  elif provider == "anthropic":
    return model_generation_sdk.AnthropicModel(
        model_name=model_name,
        model_options={"temperature": 0.7, "max_tokens": 1000}
    )
  
  else:
    raise ValueError(f"Unsupported provider: {provider}")


def process_gui_events(gui_manager):
  """Process GUI events to keep the interface responsive."""
  if gui_manager:
    return gui_manager.check_for_quit()
  return False


def call_model_with_gui_updates(model, prompt_input, gui_manager, status_message):
  """Call model while keeping GUI responsive with progress updates."""
  import time
  import threading
  
  # Update GUI with thinking status
  if gui_manager:
    gui_manager.set_caption(status_message)
  
  # Container to hold the result from the thread
  result_container = {'response': None, 'error': None}
  
  def make_api_call():
    try:
      result_container['response'] = model.generate_with_text_input(prompt_input)
    except Exception as e:
      result_container['error'] = e
  
  # Start API call in background thread
  api_thread = threading.Thread(target=make_api_call)
  api_thread.daemon = True
  api_thread.start()
  
  # Process GUI events while waiting for API response
  start_time = time.time()
  timeout = 120  # 2 minutes timeout
  
  while api_thread.is_alive():
    if process_gui_events(gui_manager):
      print(colored("🛑 User closed GUI, canceling API call...", "yellow"))
      return None  # User requested quit
    
    # Add some dots to show progress
    elapsed = time.time() - start_time
    dots = "." * (int(elapsed) % 4)
    if gui_manager:
      gui_manager.set_caption(f"{status_message}{dots}")
    
    # Check for timeout
    if elapsed > timeout:
      print(colored(f"⏰ API call timed out after {timeout} seconds", "red"))
      return None
    
    # Small sleep to prevent busy waiting
    time.sleep(0.1)
  
  # API call completed, check result
  if result_container['error']:
    raise result_container['error']
  
  return result_container['response']


async def main_async(_) -> None:
  """Async main function to handle data collection properly."""
  # Set up game:
  pyspiel_game = pyspiel.load_game("chess")
  pyspiel_state = pyspiel_game.new_initial_state()

  # Set up prompt generator:
  prompt_generator = prompt_generation.PromptGeneratorText()
  prompt_template = prompts.PromptTemplate.NO_LEGAL_ACTIONS

  # Set up models:
  print(colored("Setting up models...", "cyan"))
  try:
    model_player_one = create_model(
        _PLAYER_1_PROVIDER.value, 
        _PLAYER_1_MODEL.value, 
        "Player 1 (Black)"
    )
    model_player_two = create_model(
        _PLAYER_2_PROVIDER.value, 
        _PLAYER_2_MODEL.value, 
        "Player 2 (White)"
    )
    print(colored(f"Player 1 (Black): {_PLAYER_1_PROVIDER.value}:{_PLAYER_1_MODEL.value}", "blue"))
    print(colored(f"Player 2 (White): {_PLAYER_2_PROVIDER.value}:{_PLAYER_2_MODEL.value}", "red"))
  except Exception as e:
    print(colored(f"Failed to initialize models: {e}", "red"))
    print(colored("Note: For registry models, ensure proper API keys are set in environment", "yellow"))
    return

  # Set up parser
  match _PARSER_CHOICE.value:
    case tournament_util.ParserChoice.RULE_THEN_SOFT:
      parser = enhanced_parsers.create_rule_then_enhanced_parser()
    case tournament_util.ParserChoice.LLM_ONLY:
      parser_model = model_generation_sdk.AIStudioModel(
          model_name="gemini-2.5-flash"
      )
      parser = llm_parsers.LLMParser(
          model=parser_model,
          instruction_config=llm_parsers.OpenSpielChessInstructionConfig_V0,
      )
    case _:
      raise ValueError(f"Unsupported parser choice: {_PARSER_CHOICE.value}")

  # Set up data collection
  tournament_collector = None
  if _ENABLE_DATA_COLLECTION.value:
    print(colored("Setting up data collection...", "cyan"))
    try:
      tournament_collector = create_tournament_collector(
          tournament_name=_TOURNAMENT_NAME.value,
          storage_backend=_STORAGE_BACKEND.value,
          database_path=_DATABASE_PATH.value if _STORAGE_BACKEND.value == "sqlite" else None,
          database_url=_DATABASE_URL.value if _STORAGE_BACKEND.value == "postgresql" else None,
          collect_timing=True,
          collect_rethink=True,
          async_processing=True,
          worker_threads=2
      )
      
      await tournament_collector.initialize()
      print(colored(f"Data collection initialized with {_STORAGE_BACKEND.value} backend", "green"))
      
      # Create player info for data collection
      players = create_demo_players(
          player1_name=f"Player 1 ({_PLAYER_1_PROVIDER.value})",
          player2_name=f"Player 2 ({_PLAYER_2_PROVIDER.value})",
          player1_model=_PLAYER_1_MODEL.value,
          player2_model=_PLAYER_2_MODEL.value
      )
      
      # Start game data collection
      game_id = tournament_collector.start_game(
          game_name="Demo Game",
          players=players,
          metadata={
              'parser_choice': _PARSER_CHOICE.value.name,
              'gui_enabled': _GUI.value,
              'max_moves': _NUM_MOVES.value
          }
      )
      
      print(colored(f"Started game data collection (ID: {game_id})", "green"))
      
    except Exception as e:
      print(colored(f"Failed to initialize data collection: {e}", "red"))
      print(colored("Continuing without data collection...", "yellow"))
      tournament_collector = None

  # Create agents (with data collection if enabled)
  if tournament_collector:
    # Create agents with data collection wrappers
    agent_player_one = agent.ChessLLMAgent(
        model=model_player_one,
        prompt_builder=agent.default_chess_prompt_builder,
        response_parser=agent.default_response_parser,
        fallback_to_random_move=True
    )
    
    agent_player_two = agent.ChessLLMAgent(
        model=model_player_two,
        prompt_builder=agent.default_chess_prompt_builder,
        response_parser=agent.default_response_parser,
        fallback_to_random_move=True
    )
    
    # Wrap agents for data collection
    wrapped_agent_one = tournament_collector.wrap_agent(
        agent_player_one, 
        players[0], 
        "player_1_agent"
    )
    wrapped_agent_two = tournament_collector.wrap_agent(
        agent_player_two, 
        players[1], 
        "player_2_agent"
    )
    
    # Set game ID for agents
    tournament_collector.set_game_id_for_agents(game_id)
    
    print(colored("Agents wrapped for data collection", "green"))
  else:
    # Create agents without data collection
    wrapped_agent_one = agent.ChessLLMAgent(
        model=model_player_one,
        prompt_builder=agent.default_chess_prompt_builder,
        response_parser=agent.default_response_parser,
        fallback_to_random_move=True
    )
    wrapped_agent_two = agent.ChessLLMAgent(
        model=model_player_two,
        prompt_builder=agent.default_chess_prompt_builder,
        response_parser=agent.default_response_parser,
        fallback_to_random_move=True
    )

  # Set up GUI if requested
  gui_manager = None
  if _GUI.value:
    try:
      player1_display = f"{_PLAYER_1_PROVIDER.value}:{_PLAYER_1_MODEL.value}"
      player2_display = f"{_PLAYER_2_PROVIDER.value}:{_PLAYER_2_MODEL.value}"
      
      gui_manager = gui.create_gui_manager("chess")
      gui_manager.start(
          pyspiel_state.to_string(),
          caption=f"Game Arena Demo - White: {player2_display} vs Black: {player1_display}"
      )
      print(colored("Chess GUI started!", "green"))
    except Exception as e:
      print(colored(f"GUI setup failed: {e}", "yellow"))
      print(colored("Continuing without GUI...", "yellow"))
      gui_manager = None

  print(colored(f"\nStarting game for {_NUM_MOVES.value} moves...", "green", attrs=["bold"]))
  if tournament_collector:
    print(colored(f"Data collection enabled - storing to {_STORAGE_BACKEND.value}", "green"))
  print(colored("=" * 50, "green"))

  # Game loop
  move_count = 0
  for move_number in range(_NUM_MOVES.value):
    # Check for GUI quit
    if gui_manager and gui_manager.check_for_quit():
      print(colored("GUI window closed, ending game.", "yellow"))
      break
    
    if _VERBOSE.value:
      print(f"\nPre-move debug string: {pyspiel_state.debug_string()}")
    
    if pyspiel_state.is_terminal():
      print(colored("Game is terminal, ending move loop.", "red"))
      break

    current_player = pyspiel_state.current_player()
    player_name = "Black" if current_player == 0 else "White"
    player_color = "blue" if current_player == 0 else "red"
    
    print(colored(f"\n🎯 Move {move_number + 1}: {player_name}'s turn", player_color, attrs=["bold"]))
    
    # Update GUI title with current move info
    if gui_manager:
      provider = _PLAYER_1_PROVIDER.value if current_player == 0 else _PLAYER_2_PROVIDER.value
      model = _PLAYER_1_MODEL.value if current_player == 0 else _PLAYER_2_MODEL.value
      gui_manager.set_caption(f"Game Arena Demo - {player_name}: {provider}:{model} | Move {move_number + 1}")

    # Select agent for current player
    current_agent = wrapped_agent_one if current_player == 0 else wrapped_agent_two
    
    # Create observation
    observation = {
        "serializedGameAndState": pyspiel.serialize_game_and_state(
            pyspiel_game, pyspiel_state
        ),
        "legalActions": list(pyspiel_state.legal_actions())
    }
    configuration = {}
    
    # Get agent's move
    try:
      result = current_agent(observation, configuration)
      
      if result['submission'] == agent.INVALID_ACTION:
        print(colored("❌ Agent returned invalid action, ending game.", "red"))
        break
      
      # Apply the move
      pyspiel_state.apply_action(result['submission'])
      move_count += 1
      
      print(colored(f"✅ Move applied: {result.get('actionString', 'Unknown')}", "green"))
      
      # Update GUI if available
      if gui_manager:
        gui_manager.update(pyspiel_state.to_string())
        gui_manager.set_caption(f"Game Arena Demo - {player_name} played: {result.get('actionString', 'Unknown')}")
        
    except Exception as e:
      print(colored(f"❌ Error during move execution: {e}", "red"))
      break
  
  # Final game state
  print(colored("\n🏁 Demo Complete!", "green", attrs=["bold"]))
  print(colored("=" * 50, "green"))
  print("Final board position:")
  print(colored(pyspiel_state.debug_string(), "white"))
  
  # Determine and display game outcome
  game_outcome = None
  if pyspiel_state.is_terminal():
    returns = pyspiel_state.returns()
    result_text = ""
    if returns[0] == 1:  # Black wins
      result_text = f"Player 1 (Black) WINS!"
      print(colored(f"🎉 {result_text}", "blue", attrs=["bold"]))
    elif returns[1] == 1:  # White wins
      result_text = f"Player 2 (White) WINS!"
      print(colored(f"🎉 {result_text}", "red", attrs=["bold"]))
    else:  # Draw
      result_text = "DRAW!"
      print(colored(f"🤝 {result_text}", "yellow", attrs=["bold"]))
    
    # Create game outcome for data collection
    if tournament_collector:
      game_outcome = determine_game_outcome(pyspiel_state)
  
  # Finalize data collection
  if tournament_collector and game_outcome:
    try:
      tournament_collector.end_game(
          game_id,
          game_outcome,
          pyspiel_state.to_string(),
          move_count
      )
      
      # Display collection statistics
      stats = tournament_collector.get_tournament_stats()
      print(colored("\n📊 Data Collection Summary:", "cyan", attrs=["bold"]))
      print(colored(f"  Tournament: {stats['tournament_name']}", "cyan"))
      print(colored(f"  Games completed: {stats['games_completed']}", "cyan"))
      print(colored(f"  Total moves collected: {stats['total_moves_collected']}", "cyan"))
      print(colored(f"  Events processed: {stats.get('events_processed', 0)}", "cyan"))
      print(colored(f"  Average processing time: {stats.get('average_processing_time_ms', 0):.1f}ms", "cyan"))
      
      if stats.get('agent_stats'):
        print(colored("  Agent collection stats:", "cyan"))
        for agent_name, agent_stats in stats['agent_stats'].items():
          print(colored(f"    {agent_name}: {agent_stats['total_moves_collected']} moves, "
                       f"avg {agent_stats['average_collection_time_ms']:.1f}ms overhead", "cyan"))
      
    except Exception as e:
      print(colored(f"⚠️  Error finalizing data collection: {e}", "yellow"))
  
  # Clean up GUI
  if gui_manager:
    try:
      print(colored("\nPress Enter to close the demo...", "cyan"))
      input()
      gui_manager.terminate()
    except:
      pass
  
  # Shutdown data collection
  if tournament_collector:
    try:
      await tournament_collector.shutdown()
      print(colored("Data collection shutdown complete", "green"))
    except Exception as e:
      print(colored(f"Error during data collection shutdown: {e}", "yellow"))


def main(argv) -> None:
  """Main function wrapper to handle async execution."""
  try:
    asyncio.run(main_async(argv))
  except KeyboardInterrupt:
    print(colored("\n🛑 Demo interrupted by user", "yellow"))
  except Exception as e:
    print(colored(f"❌ Demo failed with error: {e}", "red"))
    sys.exit(1)


if __name__ == "__main__":
  app.run(main)