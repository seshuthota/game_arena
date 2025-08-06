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

"""Demo of chess, prompt generation, model generation, and parser together."""

import os
import time

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


def main(_) -> None:
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

  # Set up parser;
  # RULE_THEN_SOFT: rule-based (regex, replace, strip) then soft-matching
  # against legal moves
  # LLM_ONLY: feed the game-playing model's response to a separate LLM for
  # move parsing
  match _PARSER_CHOICE.value:
    case tournament_util.ParserChoice.RULE_THEN_SOFT:
      # Use our proper enhanced parser with comprehensive pattern matching
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
  print(colored("=" * 50, "green"))

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
        if provider in ["openrouter", "gemini", "openai", "anthropic"]:
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
          # TODO(google-deepmind): raw state str and readable state str should be
          # differentiated in signatures.
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
      pyspiel_state.apply_action(pyspiel_state.string_to_action(parser_output))
      print(colored("✅ Move applied successfully!", "green"))
      
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
    
  
  # Clean up GUI
  if gui_manager:
    try:
      print(colored("\nPress Enter to close the demo...", "cyan"))
      input()
      gui_manager.terminate()
    except:
      pass


if __name__ == "__main__":
  app.run(main)
