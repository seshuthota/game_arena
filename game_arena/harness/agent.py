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

"""Agent class for submitting to Kaggle Game Arena Simulation Environments."""

import abc
from collections.abc import Callable, Mapping, Sequence
import dataclasses
import json
import random
import time
import traceback
from typing import Any, Generic, Protocol, TypeAlias, TypeVar, TypedDict, Optional

from absl import logging
from game_arena.harness import enhanced_parsers
from game_arena.harness import game_notation_examples
from game_arena.harness import gui
from game_arena.harness import model_generation
from game_arena.harness import parsers
from game_arena.harness import prompt_generation
from game_arena.harness import prompts
from game_arena.harness import rethink
from game_arena.harness import tournament_util

import pyspiel


INVALID_ACTION = pyspiel.INVALID_ACTION  # -1
ERROR_ACTION_INT = -2


class CustomJSONEncoder(json.JSONEncoder):
  """A custom JSON encoder that handles non-serializable types from various LLM libraries."""

  def default(self, o):
    if dataclasses.is_dataclass(o):
      return dataclasses.asdict(o)
    if hasattr(o, "to_dict") and callable(o.to_dict):
      return o.to_dict()
    try:
      return super().default(o)
    except TypeError:
      return str(o)


KaggleActionT = TypeVar("KaggleActionT")
KaggleSpielActionT = TypeVar(
    "KaggleSpielActionT", "KaggleSpielAction", "KaggleSpielActionWithExtras"
)


PromptBuilder: TypeAlias = Callable[[pyspiel.State], str]
ResponseParser: TypeAlias = Callable[
    [tournament_util.GenerateReturn, pyspiel.State], str
]


class KaggleAgent(Protocol, Generic[KaggleActionT]):
  """Kaggle agent interface."""

  def __call__(
      self,
      observation: Mapping[str, Any],
      configuration: Mapping[str, Any],
      **kwargs,
  ) -> KaggleActionT:
    ...


class KaggleSpielAction(TypedDict):
  """Action required by the Kaggle simulation environment Open Spiel wrapper."""

  submission: int


class KaggleSpielActionWithExtras(KaggleSpielAction):
  """Action with additional information."""

  actionString: str | None  # pylint: disable=invalid-name
  thoughts: str | None  # This goes into the "thoughts" viewer in the Kaggle UI.
  status: str | None  # pylint: disable=invalid-name
  generate_returns: Sequence[str] = dataclasses.field(default_factory=list)


class KaggleSpielAgent(
    KaggleAgent[KaggleSpielActionT], abc.ABC, Generic[KaggleSpielActionT]
):
  """Kaggle agent base class."""

  @abc.abstractmethod
  def __call__(
      self,
      observation: Mapping[str, Any],
      configuration: Mapping[str, Any],
      **kwargs,
  ) -> KaggleSpielActionT:
    ...


class LLMAgent(KaggleAgent[KaggleActionT], Generic[KaggleActionT]):
  """LLM agent for Kaggle Game Arena Simulation Environments."""

  model: model_generation.Model
  # TODO(google-deepmind): Align API with existing abstractions. The goal is to
  # have a generic agent __call__ function that performs three main steps:
  # 1. Map from observation to prompt.
  # 2. Call the model.
  # 3. Parse the model's response into a submittable action.
  # Users need only specify a model, and define the prompt builder and response
  # parser functions. No game specific logic should be required in the agent.
  # TODO(google-deepmind): We currently require access to the pyspiel.State, which
  # is currently not present in the agent observation. For chess, the
  # observation consists of the FEN string, which allows us to reconstruct the
  # pyspiel.State. However, this is not a general approach, and will not work
  # for other games. We can either add the serialized state to the observation
  # in the Kaggle environment, or drop the pyspiel.State dependency which will
  # be possible with the Open Spiel 2.0 updates.
  prompt_builder: PromptBuilder
  response_parser: ResponseParser


# TODO(John Schultz): Make agent fully generic across games.
class ChessLLMAgent(
    KaggleSpielAgent[KaggleSpielActionWithExtras],
    LLMAgent[KaggleSpielActionWithExtras],
):
  """LLM agent for chess.

  An agent that uses a large language model to play chess. It takes an
  observation of the game state, builds a prompt, queries the model, and parses
  the model's response to determine its action.

  Attributes:
    model: The LLM to use for generating actions.
    prompt_builder: A function that takes a `pyspiel.State` and returns a prompt
      string for the model.
    response_parser: A function that parses the model's response and returns an
      action string.
    max_model_calls: If set, the agent will start making random moves after this
      many calls to the model (used for testing).
    fallback_to_random_move: If True, the agent will take a random action if the
      action string returned by the model does not parse to a valid action.
    seed: The seed for the random number generator used for fallbacks.
    num_model_calls: The number of times the model has been called.
    data_collection_enabled: Whether to emit data collection events.
    data_collection_callback: Optional callback for data collection events.
  """

  def __init__(
      self,
      model: model_generation.Model,
      prompt_builder: PromptBuilder,
      response_parser: ResponseParser,
      max_model_calls: int | None = None,
      fallback_to_random_move: bool = False,
      seed: int | None = None,
      data_collection_enabled: bool = False,
      data_collection_callback: Optional[Callable[[str, dict], None]] = None,
  ):
    super().__init__()

    self.model = model
    self.prompt_builder = prompt_builder
    self.response_parser = response_parser
    self.max_model_calls = max_model_calls
    self.fallback_to_random_move = fallback_to_random_move
    self._rng = random.Random(seed)
    self._num_model_calls = 0
    
    # Data collection configuration
    self.data_collection_enabled = data_collection_enabled
    self.data_collection_callback = data_collection_callback
    self._move_number = 0

  @property
  def num_model_calls(self) -> int:
    """The number of times the model (not the agent) has been called."""
    return self._num_model_calls

  def __call__(
      self,
      observation: Mapping[str, Any],
      configuration: Mapping[str, Any],
      **kwargs,
  ) -> KaggleSpielActionWithExtras:
    """Returns an action given an observation of the current game state."""
    del configuration, kwargs
    
    # Start timing for data collection
    start_time = time.time() if self.data_collection_enabled else None
    
    serialized_game_and_state = observation.get("serializedGameAndState")
    if not serialized_game_and_state:
      return KaggleSpielActionWithExtras(
          submission=INVALID_ACTION,
          actionString=None,
          thoughts=None,
          status="Setup step; model not called.",
          generate_returns=[],
      )
    _, pyspiel_state = pyspiel.deserialize_game_and_state(
        serialized_game_and_state
    )

    # Capture pre-move state for data collection
    fen_before = pyspiel_state.to_string() if self.data_collection_enabled else None
    legal_moves_list = [pyspiel_state.action_to_string(action) 
                       for action in pyspiel_state.legal_actions()] if self.data_collection_enabled else []

    if self.max_model_calls and self.num_model_calls >= self.max_model_calls:
      status = (
          f"MAX MODEL CALLS (N={self.num_model_calls}) REACHED;"
          " selecting random move."
      )
      logging.info(status)
      legal_moves = observation.get("legalActions") or []
      action_int = self._rng.choice(legal_moves)
      action_str = pyspiel_state.action_to_string(action_int)
      
      # Emit data collection event for random move fallback
      if self.data_collection_enabled and self.data_collection_callback:
        self._emit_move_data(
            pyspiel_state, action_int, action_str, "", "", 
            fen_before, legal_moves_list, start_time, 
            error_type="max_calls_reached", error_message=status
        )
      
      return KaggleSpielActionWithExtras(
          submission=action_int,
          actionString=action_str,
          thoughts=None,
          status=status,
          generate_returns=[],
      )

    prompt = self.prompt_builder(pyspiel_state)
    model_input = tournament_util.ModelTextInput(prompt_text=prompt)

    parsed_action_str = None
    action_int = INVALID_ACTION
    response = None
    main_response = None
    
    # Time the model call
    model_call_start = time.time() if self.data_collection_enabled else None
    
    try:
      logging.info("CALLING LLM")
      self._num_model_calls += 1
      response = self.model.generate_with_text_input(model_input)
      logging.info("RESPONSE:")
      logging.info(response.main_response)
    except Exception as e:  # pylint: disable=broad-except
      logging.error("ERROR CALLING LLM")
      logging.exception(e)
      
      # Emit data collection event for model call error
      if self.data_collection_enabled and self.data_collection_callback:
        self._emit_move_data(
            pyspiel_state, INVALID_ACTION, None, prompt, "", 
            fen_before, legal_moves_list, start_time,
            model_call_time_ms=(time.time() - model_call_start) * 1000 if model_call_start else 0,
            error_type="model_call_error", error_message=str(e)
        )
      
      pass
    
    model_call_time_ms = (time.time() - model_call_start) * 1000 if model_call_start else 0
    
    if response is None:
      logging.error("NO RESPONSE FROM LLM")
      
      # Emit data collection event for no response
      if self.data_collection_enabled and self.data_collection_callback:
        self._emit_move_data(
            pyspiel_state, INVALID_ACTION, None, prompt, "", 
            fen_before, legal_moves_list, start_time,
            model_call_time_ms=model_call_time_ms,
            error_type="no_response", error_message="Model non-responsive"
        )
      
      return KaggleSpielActionWithExtras(
          submission=INVALID_ACTION,
          actionString=None,
          thoughts=None,
          status="Model non-responsive.",
          generate_returns=[],
      )

    # Time the parsing
    parsing_start = time.time() if self.data_collection_enabled else None
    parsing_success = False
    
    try:
      main_response = response.main_response
      parsed_action_str = self.response_parser(response, pyspiel_state)
      action_int = pyspiel_state.string_to_action(parsed_action_str)
      parsing_success = True
      logging.info("PARSED RESPONSE: %s %s", parsed_action_str, action_int)
    except Exception as e:  # pylint: disable=broad-except
      logging.error("ERROR PARSING LLM RESPONSE")
      logging.exception(e)
      pass

    parsing_time_ms = (time.time() - parsing_start) * 1000 if parsing_start else 0

    legal_actions = observation.get("legalActions") or []
    if not legal_actions:
      logging.warning("NO LEGAL ACTIONS FOUND")
    if (
        self.fallback_to_random_move
        and legal_actions
        and action_int not in legal_actions
    ):
      logging.info("INVALID MOVE FROM LLM; overriding with random move.")
      action_int = self._rng.choice(legal_actions)

    logging.debug(
        "Returning: %s %s %s", action_int, parsed_action_str, main_response
    )

    # Emit data collection event for successful move
    if self.data_collection_enabled and self.data_collection_callback:
      self._emit_move_data(
          pyspiel_state, action_int, parsed_action_str, prompt, 
          main_response or "", fen_before, legal_moves_list, start_time,
          model_call_time_ms=model_call_time_ms,
          parsing_time_ms=parsing_time_ms,
          parsing_success=parsing_success,
          is_legal=action_int in legal_actions if legal_actions else False
      )

    return KaggleSpielActionWithExtras(
        submission=action_int,
        actionString=parsed_action_str,
        thoughts=main_response,
        status=None,
        generate_returns=[response],
    )

  def _emit_move_data(
      self,
      pyspiel_state: pyspiel.State,
      action_int: int,
      action_str: Optional[str],
      prompt: str,
      raw_response: str,
      fen_before: Optional[str],
      legal_moves_list: list,
      start_time: Optional[float],
      model_call_time_ms: float = 0.0,
      parsing_time_ms: float = 0.0,
      parsing_success: bool = False,
      is_legal: bool = False,
      error_type: Optional[str] = None,
      error_message: Optional[str] = None,
  ) -> None:
    """Emit move data for collection."""
    if not self.data_collection_callback:
      return
    
    try:
      self._move_number += 1
      
      # Calculate post-move FEN
      fen_after = fen_before  # Default to no change
      if action_int not in [INVALID_ACTION, ERROR_ACTION_INT]:
        try:
          new_state = pyspiel_state.clone()
          new_state.apply_action(action_int)
          fen_after = new_state.to_string()
        except Exception:
          pass  # Keep fen_before as fallback
      
      # Calculate total time
      total_time_ms = (time.time() - start_time) * 1000 if start_time else 0.0
      
      # Convert action to UCI format (simplified)
      move_uci = action_str or ""
      
      move_data = {
        'move_number': self._move_number,
        'player': pyspiel_state.current_player(),
        'fen_before': fen_before or "",
        'fen_after': fen_after or "",
        'legal_moves': legal_moves_list,
        'move_san': action_str or "",
        'move_uci': move_uci,
        'is_legal': is_legal,
        'prompt_text': prompt,
        'raw_response': raw_response,
        'parsed_move': action_str,
        'parsing_success': parsing_success,
        'parsing_attempts': 1,
        'thinking_time_ms': int(total_time_ms),
        'api_call_time_ms': int(model_call_time_ms),
        'parsing_time_ms': int(parsing_time_ms),
        'rethink_attempts': [],  # ChessLLMAgent doesn't use rethink
        'error_type': error_type,
        'error_message': error_message
      }
      
      self.data_collection_callback('move_made', move_data)
      
    except Exception as e:
      logging.warning(f"Failed to emit move data: {e}")

  def enable_data_collection(
      self, 
      callback: Callable[[str, dict], None]
  ) -> None:
    """Enable data collection with the provided callback."""
    self.data_collection_enabled = True
    self.data_collection_callback = callback

  def disable_data_collection(self) -> None:
    """Disable data collection."""
    self.data_collection_enabled = False
    self.data_collection_callback = None


# TODO(John Schultz): Remove LLMAgent abstraction in favor of a generic Sampler
# agent, and in the process remove these default prompt and response parsers.
prompt_generator = prompt_generation.PromptGeneratorText()
chained_parser = enhanced_parsers.create_rule_then_enhanced_parser()


def default_chess_prompt_builder(
    pyspiel_state: pyspiel.State,
) -> str:
  """Builds the text prompt for the LLM agent."""
  chess_notations = game_notation_examples.GAME_SPECIFIC_NOTATIONS["chess"]
  prompt_substitutions = {
      "readable_state_str": tournament_util.convert_to_readable_state(
          game_short_name="chess",
          state_str=pyspiel_state.to_string(),
          current_player=pyspiel_state.current_player(),
      ),
      "move_history": (
          tournament_util.get_action_string_history(pyspiel_state) or "None"
      ),
      "player_name": chess_notations["player_map"][
          pyspiel_state.current_player()
      ],
      "move_notation": chess_notations["move_notation"],
      "notation": chess_notations["state_notation"],
  }
  prompt = prompt_generator.generate_prompt_with_text_only(
      prompt_template=prompts.PromptTemplate.NO_LEGAL_ACTIONS,
      game_short_name="chess",
      **prompt_substitutions,
  )
  return prompt.prompt_text


def default_response_parser(
    response: tournament_util.GenerateReturn,
    pyspiel_state: pyspiel.State,
) -> str:
  """Parses the response from the LLM."""
  parser_input = parsers.TextParserInput(
      text=response.main_response,
      state_str=pyspiel_state.to_string(),
      legal_moves=parsers.get_legal_action_strings(pyspiel_state),
      player_number=pyspiel_state.current_player(),
  )
  llm_choice_str = chained_parser.parse(parser_input)
  return llm_choice_str or ""


# TODO(John Schultz): Add a generic sampler agent. One problem is that different
# samplers have different call functions.
class ChessRethinkAgent(KaggleSpielAgent[KaggleSpielActionWithExtras]):
  """Rethink agent for chess."""

  def __init__(
      self,
      sampler: rethink.RethinkSampler,
      prompt_template: prompts.PromptTemplate,
      max_sampler_calls: int | None = None,
      random_move_fallback: bool = False,
      seed: int | None = None,
      data_collection_enabled: bool = False,
      data_collection_callback: Optional[Callable[[str, dict], None]] = None,
  ):
    super().__init__()
    self.sampler = sampler
    self.prompt_template = prompt_template
    self.max_sampler_calls = max_sampler_calls
    self.random_move_fallback = random_move_fallback
    self._rng = random.Random(seed)
    self._num_sampler_calls = 0
    
    # Data collection configuration
    self.data_collection_enabled = data_collection_enabled
    self.data_collection_callback = data_collection_callback
    self._move_number = 0

  @property
  def num_sampler_calls(self) -> int:
    """The number of times the sampler (not the model or agent) has been called."""
    return self._num_sampler_calls

  def __call__(
      self,
      observation: Mapping[str, Any],
      configuration: Mapping[str, Any],
      **kwargs,
  ) -> KaggleSpielActionWithExtras:
    """Returns an action given an observation of the current game state."""
    del configuration, kwargs
    
    # Start timing for data collection
    start_time = time.time() if self.data_collection_enabled else None
    
    serialized_game_and_state = observation.get("serializedGameAndState")
    if not serialized_game_and_state:
      return KaggleSpielActionWithExtras(
          submission=INVALID_ACTION,
          actionString=None,
          thoughts=None,
          status="OK; Setup step; model not called.",
          generate_returns=[],
      )
    _, pyspiel_state = pyspiel.deserialize_game_and_state(
        serialized_game_and_state
    )

    # Capture pre-move state for data collection
    fen_before = pyspiel_state.to_string() if self.data_collection_enabled else None
    legal_moves_list = [pyspiel_state.action_to_string(action) 
                       for action in pyspiel_state.legal_actions()] if self.data_collection_enabled else []

    if (
        self.max_sampler_calls
        and self.num_sampler_calls >= self.max_sampler_calls
    ):
      status = (
          f"OK; MAX SAMPLER CALLS (N={self.num_sampler_calls}) REACHED;"
          " selecting random move"
      )
      logging.info(status)
      legal_moves = observation.get("legalActions") or []
      action_int = self._rng.choice(legal_moves)
      action_str = pyspiel_state.action_to_string(action_int)
      
      # Emit data collection event for random move fallback
      if self.data_collection_enabled and self.data_collection_callback:
        self._emit_move_data(
            pyspiel_state, action_int, action_str, "", "", 
            fen_before, legal_moves_list, start_time, [],
            error_type="max_calls_reached", error_message=status
        )
      
      return KaggleSpielActionWithExtras(
          submission=action_int,
          actionString=action_str,
          thoughts=None,
          status=status,
          generate_returns=[],
      )

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

    # Generate initial prompt for data collection
    initial_prompt = ""
    if self.data_collection_enabled:
      try:
        prompt_generator = prompt_generation.PromptGeneratorText()
        prompt_obj = prompt_generator.generate_prompt_with_text_only(
            prompt_template=self.prompt_template,
            game_short_name="chess",
            **prompt_substitutions,
        )
        initial_prompt = prompt_obj.prompt_text
      except Exception as e:
        logging.warning(f"Failed to generate prompt for data collection: {e}")

    # Time the sampler call
    sampler_call_start = time.time() if self.data_collection_enabled else None
    sampler_output = None
    
    try:
      logging.info("CALLING SAMPLER")
      self._num_sampler_calls += 1
      sampler_output = self.sampler.sample_action_with_text_and_state_input(
          pyspiel_state,
          self.prompt_template,
          **prompt_substitutions,
      )
      logging.info("FIRST RESPONSE:")
      logging.info(sampler_output.generate_returns[0].main_response)
      logging.info("SAMPLED ACTION:")
      logging.info(sampler_output.action)
    except Exception as e:  # pylint: disable=broad-except
      logging.error("ERROR CALLING SAMPLER")
      logging.exception(e)
      
      # Emit data collection event for sampler error
      if self.data_collection_enabled and self.data_collection_callback:
        sampler_call_time_ms = (time.time() - sampler_call_start) * 1000 if sampler_call_start else 0
        self._emit_move_data(
            pyspiel_state, ERROR_ACTION_INT, None, initial_prompt, "", 
            fen_before, legal_moves_list, start_time, [],
            model_call_time_ms=sampler_call_time_ms,
            error_type="sampler_error", error_message=str(e)
        )
      
      return KaggleSpielActionWithExtras(
          submission=ERROR_ACTION_INT,
          actionString=None,
          thoughts=None,
          status=f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}",
          generate_returns=[],
      )

    sampler_call_time_ms = (time.time() - sampler_call_start) * 1000 if sampler_call_start else 0

    # Extract rethink attempts for data collection
    rethink_attempts = []
    if self.data_collection_enabled and sampler_output:
      rethink_attempts = self._extract_rethink_attempts(sampler_output)

    main_response = ""
    for i, generate_return in enumerate(sampler_output.generate_returns):
      if i == 0:
        main_response = generate_return.main_response
      else:
        main_response += (
            "\n\n" + "=" * 10 + f" Rethink Attempt #{i} " + "=" * 10
        )
        main_response += f"\n\n{generate_return.main_response}"
    logging.info("--ALL RESPONSES--")
    logging.info(main_response)

    generate_returns_jsons = []
    try:
      generate_returns_jsons = [
          json.dumps(generate_return.to_dict(), indent=2, cls=CustomJSONEncoder)
          for generate_return in sampler_output.generate_returns
      ]
    except Exception as e:  # pylint: disable=broad-except
      logging.error("ERROR DUMPING GENERATE RETURNS")
      logging.exception(e)

    parsed_action_str = sampler_output.action
    if sampler_output.move_type == tournament_util.MoveType.LEGAL:
      try:
        action_int = pyspiel_state.string_to_action(parsed_action_str)
        logging.info("PARSED RESPONSE: %s %s", parsed_action_str, action_int)
        
        # Emit data collection event for successful move
        if self.data_collection_enabled and self.data_collection_callback:
          self._emit_move_data(
              pyspiel_state, action_int, parsed_action_str, initial_prompt, 
              main_response, fen_before, legal_moves_list, start_time, rethink_attempts,
              model_call_time_ms=sampler_call_time_ms,
              parsing_success=True,
              is_legal=True
          )
        
        return KaggleSpielActionWithExtras(
            submission=action_int,
            actionString=parsed_action_str,
            thoughts=main_response,
            status="OK",
            generate_returns=generate_returns_jsons,
        )
      except Exception as e:  # pylint: disable=broad-except
        logging.error("ERROR SHOULD BE LEGAL BUT CONVERSION FAILED")
        logging.exception(e)
        
        # Emit data collection event for conversion error
        if self.data_collection_enabled and self.data_collection_callback:
          self._emit_move_data(
              pyspiel_state, INVALID_ACTION, parsed_action_str, initial_prompt, 
              main_response, fen_before, legal_moves_list, start_time, rethink_attempts,
              model_call_time_ms=sampler_call_time_ms,
              parsing_success=False,
              is_legal=False,
              error_type="conversion_error", error_message=str(e)
          )
        
        return KaggleSpielActionWithExtras(
            submission=INVALID_ACTION,
            actionString=parsed_action_str,
            thoughts=main_response,
            status=f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}",
            generate_returns=generate_returns_jsons,
        )
    else:
      # Emit data collection event for invalid move
      if self.data_collection_enabled and self.data_collection_callback:
        self._emit_move_data(
            pyspiel_state, INVALID_ACTION, parsed_action_str, initial_prompt, 
            main_response, fen_before, legal_moves_list, start_time, rethink_attempts,
            model_call_time_ms=sampler_call_time_ms,
            parsing_success=True,  # Parsing succeeded but move was invalid
            is_legal=False
        )
      
      return KaggleSpielActionWithExtras(
          submission=INVALID_ACTION,
          actionString=parsed_action_str,
          thoughts=main_response,
          status="OK; Submitting invalid action.",
          generate_returns=generate_returns_jsons,
      )

  def _extract_rethink_attempts(self, sampler_output) -> list:
    """Extract rethink attempts from sampler output."""
    rethink_attempts = []
    
    try:
      # Extract rethink data from generate_returns (skip first one which is initial attempt)
      for i, generate_return in enumerate(sampler_output.generate_returns[1:], 1):
        rethink_attempt = {
          'attempt_number': i,
          'prompt_text': f"Rethink prompt {i} (not captured)",  # Not directly available
          'raw_response': generate_return.main_response if hasattr(generate_return, 'main_response') else str(generate_return),
          'parsed_move': None,  # Would need additional parsing
          'was_legal': False,  # Would need validation
          'timestamp': time.time()
        }
        rethink_attempts.append(rethink_attempt)
      
      # Try to extract additional data from auxiliary outputs if available
      if hasattr(sampler_output, 'auxiliary_outputs') and sampler_output.auxiliary_outputs:
        aux_outputs = sampler_output.auxiliary_outputs
        attempt_number = 1
        
        while f'parsed_action_attempt_{attempt_number}' in aux_outputs:
          if attempt_number <= len(rethink_attempts):
            # Update existing attempt with parsed data
            rethink_attempts[attempt_number - 1]['parsed_move'] = aux_outputs.get(f'parsed_action_attempt_{attempt_number}')
            rethink_attempts[attempt_number - 1]['was_legal'] = aux_outputs.get(f'maybe_legal_action_attempt_{attempt_number}') is not None
            
            # Try to get rethink prompt if available
            rethink_prompt = aux_outputs.get(f'rethink_prompt_attempt_{attempt_number}')
            if rethink_prompt:
              rethink_attempts[attempt_number - 1]['prompt_text'] = rethink_prompt
          
          attempt_number += 1
      
    except Exception as e:
      logging.warning(f"Failed to extract rethink attempts: {e}")
    
    return rethink_attempts

  def _emit_move_data(
      self,
      pyspiel_state: pyspiel.State,
      action_int: int,
      action_str: Optional[str],
      prompt: str,
      raw_response: str,
      fen_before: Optional[str],
      legal_moves_list: list,
      start_time: Optional[float],
      rethink_attempts: list,
      model_call_time_ms: float = 0.0,
      parsing_time_ms: float = 0.0,
      parsing_success: bool = False,
      is_legal: bool = False,
      error_type: Optional[str] = None,
      error_message: Optional[str] = None,
  ) -> None:
    """Emit move data for collection."""
    if not self.data_collection_callback:
      return
    
    try:
      self._move_number += 1
      
      # Calculate post-move FEN
      fen_after = fen_before  # Default to no change
      if action_int not in [INVALID_ACTION, ERROR_ACTION_INT]:
        try:
          new_state = pyspiel_state.clone()
          new_state.apply_action(action_int)
          fen_after = new_state.to_string()
        except Exception:
          pass  # Keep fen_before as fallback
      
      # Calculate total time
      total_time_ms = (time.time() - start_time) * 1000 if start_time else 0.0
      
      # Convert action to UCI format (simplified)
      move_uci = action_str or ""
      
      move_data = {
        'move_number': self._move_number,
        'player': pyspiel_state.current_player(),
        'fen_before': fen_before or "",
        'fen_after': fen_after or "",
        'legal_moves': legal_moves_list,
        'move_san': action_str or "",
        'move_uci': move_uci,
        'is_legal': is_legal,
        'prompt_text': prompt,
        'raw_response': raw_response,
        'parsed_move': action_str,
        'parsing_success': parsing_success,
        'parsing_attempts': len(rethink_attempts) + 1,  # Include initial attempt
        'thinking_time_ms': int(total_time_ms),
        'api_call_time_ms': int(model_call_time_ms),
        'parsing_time_ms': int(parsing_time_ms),
        'rethink_attempts': rethink_attempts,
        'error_type': error_type,
        'error_message': error_message
      }
      
      self.data_collection_callback('move_made', move_data)
      
      # Emit individual rethink attempt events
      for attempt in rethink_attempts:
        self.data_collection_callback('rethink_attempt', {
          'game_id': None,  # Will be set by the callback handler
          'move_number': self._move_number,
          'player': pyspiel_state.current_player(),
          'attempt_data': attempt
        })
      
    except Exception as e:
      logging.warning(f"Failed to emit move data: {e}")

  def enable_data_collection(
      self, 
      callback: Callable[[str, dict], None]
  ) -> None:
    """Enable data collection with the provided callback."""
    self.data_collection_enabled = True
    self.data_collection_callback = callback

  def disable_data_collection(self) -> None:
    """Disable data collection."""
    self.data_collection_enabled = False
    self.data_collection_callback = None


def build_default_rethink_agent(
    model: model_generation.Model,
) -> ChessRethinkAgent:
  """Builds a rethink agent with default settings for a given model."""
  sampler = rethink.RethinkSampler(
      model=model,
      strategy=tournament_util.SamplerChoice.RETHINK_WITH_ENV,
      num_max_rethinks=3,
      move_parser=parsers.RuleBasedMoveParser(),
      legality_parser=parsers.SoftMoveParser("chess"),
      game_short_name="chess",
      prompt_generator=prompt_generation.PromptGeneratorText(),
      rethink_template=None,
  )
  agent = ChessRethinkAgent(
      sampler=sampler,
      prompt_template=prompts.PromptTemplate.NO_LEGAL_ACTIONS_RETHINK_APPENDED,
  )
  return agent



class ChessRethinkAgentWithGUI(ChessRethinkAgent):
  """ChessRethinkAgent with GUI support for visual chess board display."""
  
  def __init__(
      self,
      sampler: rethink.RethinkSampler,
      prompt_template: prompts.PromptTemplate,
      gui_manager: gui.GUIManager | None = None,
      player1_name: str = "Player 1 (Black)",
      player2_name: str = "Player 2 (White)",
      max_sampler_calls: int | None = None,
      random_move_fallback: bool = False,
      seed: int | None = None,
  ):
    super().__init__(
        sampler=sampler,
        prompt_template=prompt_template,
        max_sampler_calls=max_sampler_calls,
        random_move_fallback=random_move_fallback,
        seed=seed,
    )
    self.gui_manager = gui_manager
    self.player1_name = player1_name
    self.player2_name = player2_name
    self._move_number = 0
    self._game_started = False

  def __call__(
      self,
      observation: Mapping[str, Any],
      configuration: Mapping[str, Any],
      **kwargs,
  ) -> KaggleSpielActionWithExtras:
    """Returns an action with GUI updates."""
    serialized_game_and_state = observation.get("serializedGameAndState")
    if not serialized_game_and_state:
      return super().__call__(observation, configuration, **kwargs)
    
    _, pyspiel_state = pyspiel.deserialize_game_and_state(
        serialized_game_and_state
    )
    
    # Start GUI on first move
    if self.gui_manager and not self._game_started:
      try:
        caption = f"Game Arena - White: {self.player2_name} vs Black: {self.player1_name}"
        self.gui_manager.start(pyspiel_state.to_string(), caption=caption)
        self._game_started = True
        logging.info("Chess GUI started successfully")
      except Exception as e:
        logging.warning(f"Failed to start GUI: {e}")
        self.gui_manager = None  # Disable GUI on failure
    
    # Update GUI with current player and move status
    if self.gui_manager:
      try:
        current_player = pyspiel_state.current_player()
        player_name = self.player1_name if current_player == 0 else self.player2_name
        status = f"{player_name} | Move {self._move_number + 1} | Thinking..."
        self.gui_manager.set_caption(f"Game Arena - {status}")
        self.gui_manager.update(pyspiel_state.to_string())
      except Exception as e:
        logging.warning(f"GUI update failed: {e}")
    
    # Check for GUI quit
    if self.gui_manager and self.gui_manager.check_for_quit():
      logging.info("GUI quit requested, ending game")
      return KaggleSpielActionWithExtras(
          submission=INVALID_ACTION,
          actionString=None,
          thoughts="Game ended by user (GUI closed)",
          status="OK; User quit via GUI",
          generate_returns=[],
      )
    
    # Call parent implementation
    result = super().__call__(observation, configuration, **kwargs)
    
    # Update move counter and GUI after move
    if result.submission != INVALID_ACTION and result.submission != ERROR_ACTION_INT:
      self._move_number += 1
      
      # Update GUI with move result
      if self.gui_manager:
        try:
          # Re-parse state after move to show updated board
          updated_state = pyspiel_state.clone()
          if result.actionString:
            try:
              action_int = updated_state.string_to_action(result.actionString)
              updated_state.apply_action(action_int)
              self.gui_manager.update(updated_state.to_string())
              
              # Update caption with move info
              current_player = pyspiel_state.current_player()
              player_name = self.player1_name if current_player == 0 else self.player2_name
              self.gui_manager.set_caption(
                  f"Game Arena - {player_name} played: {result.actionString} | Move {self._move_number}"
              )
            except Exception as e:
              logging.warning(f"Failed to update GUI with move: {e}")
        except Exception as e:
          logging.warning(f"GUI move update failed: {e}")
    
    return result

  def terminate_gui(self):
    """Terminate the GUI if active."""
    if self.gui_manager:
      try:
        self.gui_manager.terminate()
        logging.info("GUI terminated successfully")
      except Exception as e:
        logging.warning(f"GUI termination failed: {e}")


