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
from game_arena.harness import model_generation_ollama
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
    ["registry", "openrouter", "openai", "gemini", "anthropic", "ollama"],
    "Provider for player 1 (Black). 'registry' uses ModelRegistry.",
)

_PLAYER_1_MODEL = flags.DEFINE_string(
    "player1_model",
    "GEMINI_2_5_FLASH",
    "Model for player 1. Examples: registry='GEMINI_2_5_FLASH', openrouter='anthropic/claude-3.5-sonnet', openai='gpt-4o-mini', gemini='gemini-2.5-flash', ollama='llama3'",
)

_PLAYER_2_PROVIDER = flags.DEFINE_enum(
    "player2_provider",
    "registry", 
    ["registry", "openrouter", "openai", "gemini", "anthropic", "ollama"],
    "Provider for player 2 (White). 'registry' uses ModelRegistry enum name.",
)

_PLAYER_2_MODEL = flags.DEFINE_string(
    "player2_model",
    "OPENAI_GPT_4_1",
    "Model for player 2. Examples: registry='OPENAI_GPT_4_1', openrouter='openai/gpt-4o-mini', openai='gpt-4o-mini', gemini='gemini-2.5-flash', ollama='llama3'",
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
  
  elif provider == "ollama":
    return model_generation_ollama.OllamaModel(
        model_name=model_name,
        model_options={"temperature": 0.7, "max_output_tokens": 1000}
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
          async_processing=False,
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

  # Game loop using the original harness_demo.py approach with enhanced parsing
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

    # 1. Generate the prompt from the game state:
    prompt_substitutions = {
        "readable_state_str": tournament_util.convert_to_readable_state(
            game_short_name="chess",
            state_str=pyspiel_state.to_string(),
            current_player=pyspiel_state.current_player(),
        ),
        "move_history": (
            tournament_util.get_action_string_history(pyspiel_state) or "None"
        ),
        "player_name": game_notation_examples.GAME_SPECIFIC_NOTATIONS["chess"][
            "player_map"
        ][pyspiel_state.current_player()],
        "move_notation": game_notation_examples.GAME_SPECIFIC_NOTATIONS[
            "chess"
        ]["move_notation"],
        "notation": game_notation_examples.GAME_SPECIFIC_NOTATIONS["chess"][
            "state_notation"
        ],
    }
    prompt = prompt_generator.generate_prompt_with_text_only(
        prompt_template=prompt_template,
        game_short_name="chess",
        **prompt_substitutions,
    )
    if _VERBOSE.value:
      print(colored(f"Formatted prompt: {prompt.prompt_text[:200]}...", "blue"))

    # 2. Call the model with retry logic:
    model = model_player_one if current_player == 0 else model_player_two
    provider = _PLAYER_1_PROVIDER.value if current_player == 0 else _PLAYER_2_PROVIDER.value
    model_name = _PLAYER_1_MODEL.value if current_player == 0 else _PLAYER_2_MODEL.value
    
    parser_output = None
    max_retries = 3
    
    for attempt in range(max_retries):
      if attempt == 0:
        print(colored(f"🤖 Calling {provider}:{model_name}...", "cyan"))
        current_prompt = prompt
      else:
        print(colored(f"🔄 Retry attempt {attempt} - asking for legal move...", "yellow"))
        # Create rethink prompt
        legal_moves_str = ', '.join(parsers.get_legal_action_strings(pyspiel_state)[:10])
        if len(parsers.get_legal_action_strings(pyspiel_state)) > 10:
          legal_moves_str += "..."
        
        rethink_text = f"Your previous response could not be parsed or was illegal. Please respond with ONLY a legal chess move. Legal moves available: {legal_moves_str}"
        current_prompt = tournament_util.ModelTextInput(prompt_text=rethink_text)
      
      try:
        # Prepare status message for GUI
        if attempt == 0:
          status_message = f"🤖 {player_name}: {provider}:{model_name} thinking..."
        else:
          status_message = f"🔄 {player_name}: {provider}:{model_name} retry {attempt}..."
        
        # Add system instruction for cleaner responses from all models except registry
        if provider in ["openrouter", "gemini", "openai", "anthropic", "ollama"]:
          chess_system_instruction = "You are a chess expert. Respond ONLY with the chess move in standard algebraic notation (e.g., e4, Nf3, O-O). No explanation or additional text."
          prompt_with_system = tournament_util.ModelTextInput(
              prompt_text=current_prompt.prompt_text,
              system_instruction=chess_system_instruction
          )
          response = call_model_with_gui_updates(model, prompt_with_system, gui_manager, status_message)
        else:
          # Registry models handle system instructions internally
          response = call_model_with_gui_updates(model, current_prompt, gui_manager, status_message)
        
        # Check if user quit during API call
        if response is None:
          print(colored("🛑 Stopping game due to user quit or timeout", "yellow"))
          parser_output = None  # Signal to exit both loops
          break
        
        # Show full response in verbose mode, truncated response otherwise
        if _VERBOSE.value:
          print(colored(f"💭 Full Response: {response.main_response}", "yellow"))
        else:
          print(colored(f"💭 Response: {response.main_response[:100]}...", "yellow"))
          
      except Exception as e:
        print(colored(f"❌ Model call failed: {e}", "red"))
        print(colored("This is expected in demo mode without proper API keys", "yellow"))
        break

      # 3. Parse the model response:
      parser_input = parsers.TextParserInput(
          text=response.main_response,
          state_str=pyspiel_state.to_string(),
          legal_moves=parsers.get_legal_action_strings(pyspiel_state),
          player_number=pyspiel_state.current_player(),
      )
      parser_output = parser.parse(parser_input)
      
      if parser_output is not None:
        print(colored(f"♟️  Parsed move: {parser_output}", "magenta", attrs=["bold"]))
        
        # Check if the parsed move is actually legal by testing conversion to action
        try:
          action_int = pyspiel_state.string_to_action(parser_output)
          if action_int in pyspiel_state.legal_actions():
            # Move is legal, break out of retry loop
            break
          else:
            print(colored(f"⚠️  Parsed move {parser_output} is not in legal moves list", "yellow"))
            parser_output = None  # Force retry
        except Exception as e:
          print(colored(f"⚠️  Parsed move {parser_output} is invalid: {e}", "yellow"))
          parser_output = None  # Force retry
      
      if parser_output is None:
        print(colored(f"❌ Parse attempt {attempt + 1} failed or move illegal", "red"))
        if _VERBOSE.value:
          print(colored(f"🔍 Parser failed to extract legal move from: '{response.main_response}'", "red"))
          print(colored(f"🎯 Legal moves available: {parser_input.legal_moves[:10]}{'...' if len(parser_input.legal_moves) > 10 else ''}", "red"))
        
        if attempt == max_retries - 1:
          print(colored("❌ All retry attempts failed, ending game.", "red"))
          break
    
    # Exit move loop if parsing ultimately failed
    if parser_output is None:
      break

    # 4. Apply the move:
    try:
      action_int = pyspiel_state.string_to_action(parser_output)
      pyspiel_state.apply_action(action_int)
      move_count += 1
      print(colored("✅ Move applied successfully!", "green"))
      
      # Collect move data if tournament collector is enabled
      if tournament_collector:
        try:
          # Calculate pre-move FEN (we need to reconstruct this)
          # Note: We can't easily get the pre-move state, so we'll use current state
          # In a real implementation, we'd capture this before applying the move
          fen_before = pyspiel_state.to_string()  # This is post-move, but better than crashing
          
          # Create move data for collection
          move_data = {
              'move_number': move_count,
              'player': current_player,
              'fen_before': fen_before,
              'fen_after': pyspiel_state.to_string(),
              'legal_moves': parsers.get_legal_action_strings(pyspiel_state)[:20],  # Limit for performance
              'move_san': parser_output,
              'move_uci': parser_output,
              'is_legal': True,
              'prompt_text': prompt.prompt_text[:1000],
              'raw_response': response.main_response[:2000] if response else "",
              'parsed_move': parser_output,
              'parsing_success': True,
              'parsing_attempts': attempt + 1,
              'thinking_time_ms': 0,  # Not measured in this approach
              'api_call_time_ms': 0,
              'parsing_time_ms': 0,
              'rethink_attempts': [],
              'error_type': None,
              'error_message': None
          }
          
          # Record move in background to avoid blocking
          import threading
          def record_move_background():
            try:
              success = tournament_collector.game_collector.record_move(game_id, move_data)
              if success:
                print(colored(f"✅ Move {move_count} data collected", "green"))
              else:
                print(colored(f"⚠️  Move {move_count} data collection failed", "yellow"))
            except Exception as e:
              print(colored(f"⚠️  Background data collection failed: {e}", "yellow"))
              import traceback
              traceback.print_exc()
          
          thread = threading.Thread(target=record_move_background, daemon=True)
          thread.start()
          
        except Exception as e:
          print(colored(f"⚠️  Data collection setup failed: {e}", "yellow"))
      
      # Update GUI if available
      if gui_manager:
        gui_manager.update(pyspiel_state.to_string())
        # Update caption to show the move was played
        gui_manager.set_caption(f"Game Arena Demo - {player_name} played: {parser_output}")
        
    except Exception as e:
      print(colored(f"❌ Failed to apply move: {e}", "red"))
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
      print(colored(f"    {_PLAYER_1_PROVIDER.value}:{_PLAYER_1_MODEL.value} defeats {_PLAYER_2_PROVIDER.value}:{_PLAYER_2_MODEL.value}", "blue"))
    elif returns[1] == 1:  # White wins
      result_text = f"Player 2 (White) WINS!"
      print(colored(f"🎉 {result_text}", "red", attrs=["bold"]))
      print(colored(f"    {_PLAYER_2_PROVIDER.value}:{_PLAYER_2_MODEL.value} defeats {_PLAYER_1_PROVIDER.value}:{_PLAYER_1_MODEL.value}", "red"))
    else:  # Draw
      result_text = "DRAW!"
      print(colored(f"🤝 {result_text}", "yellow", attrs=["bold"]))
      print(colored(f"    {_PLAYER_1_PROVIDER.value}:{_PLAYER_1_MODEL.value} vs {_PLAYER_2_PROVIDER.value}:{_PLAYER_2_MODEL.value}", "yellow"))
    
    # Create game outcome for data collection
    if tournament_collector:
      game_outcome = determine_game_outcome(pyspiel_state)
  else:
    # Game was not completed normally
    print(colored("🚫 Game ended without completion", "yellow", attrs=["bold"]))
    print(colored(f"    Final position after {move_count} moves", "yellow"))
  
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