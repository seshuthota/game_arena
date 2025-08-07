"""
Agent wrapper for data collection in the Game Arena storage system.

This module provides the DataCollectingAgent wrapper class that captures
LLM interactions, timing data, and performance measurements while maintaining
compatibility with existing agent interfaces.
"""

import time
import uuid
import logging
from typing import Dict, Any, Mapping, Optional, List
from datetime import datetime
from dataclasses import dataclass

from game_arena.harness.agent import (
    KaggleSpielAgent, 
    KaggleSpielActionWithExtras,
    ChessLLMAgent,
    ChessRethinkAgent,
    INVALID_ACTION,
    ERROR_ACTION_INT
)
from game_arena.harness import tournament_util
from .collector import GameDataCollector
from .models import PlayerInfo, GameOutcome, RethinkAttempt
from .exceptions import ValidationError

import pyspiel


logger = logging.getLogger(__name__)


@dataclass
class TimingData:
    """Container for timing measurements during agent execution."""
    start_time: float
    prompt_generation_time_ms: float = 0.0
    api_call_time_ms: float = 0.0
    parsing_time_ms: float = 0.0
    total_time_ms: float = 0.0
    
    def finish(self) -> None:
        """Calculate total time and finalize measurements."""
        self.total_time_ms = (time.time() - self.start_time) * 1000


class DataCollectingAgent(KaggleSpielAgent[KaggleSpielActionWithExtras]):
    """
    Wrapper agent that collects data from LLM interactions.
    
    This wrapper captures detailed information about agent behavior including:
    - LLM prompts and responses
    - Move parsing attempts and results
    - Timing and performance measurements
    - Rethink attempts (for rethink agents)
    - Error conditions and recovery
    
    The wrapper maintains full compatibility with existing agent interfaces
    and introduces minimal performance overhead.
    """
    
    def __init__(
        self,
        wrapped_agent: KaggleSpielAgent[KaggleSpielActionWithExtras],
        collector: GameDataCollector,
        player_info: PlayerInfo,
        game_id: Optional[str] = None,
        collect_timing: bool = True,
        collect_rethink: bool = True,
        max_collection_latency_ms: float = 50.0
    ):
        """
        Initialize the data collecting agent wrapper.
        
        Args:
            wrapped_agent: The agent to wrap for data collection
            collector: GameDataCollector instance for event capture
            player_info: Information about this player
            game_id: ID of the current game (can be set later)
            collect_timing: Whether to collect detailed timing data
            collect_rethink: Whether to collect rethink attempt data
            max_collection_latency_ms: Maximum allowed collection latency
        """
        self.wrapped_agent = wrapped_agent
        self.collector = collector
        self.player_info = player_info
        self.game_id = game_id
        self.collect_timing = collect_timing
        self.collect_rethink = collect_rethink
        self.max_collection_latency_ms = max_collection_latency_ms
        
        # State tracking
        self._move_number = 0
        self._game_started = False
        self._last_state_str = None
        
        # Performance monitoring
        self._collection_times: List[float] = []
        self._max_collection_times = 100  # Keep last 100 measurements
        
        # Setup logging
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Validate wrapped agent type
        if not isinstance(wrapped_agent, (ChessLLMAgent, ChessRethinkAgent)):
            self.logger.warning(
                f"Wrapped agent type {type(wrapped_agent)} may not be fully supported"
            )
    
    def set_game_id(self, game_id: str) -> None:
        """Set the game ID for data collection."""
        self.game_id = game_id
        self._game_started = False
        self._move_number = 0
        self._last_state_str = None
    
    def __call__(
        self,
        observation: Mapping[str, Any],
        configuration: Mapping[str, Any],
        **kwargs,
    ) -> KaggleSpielActionWithExtras:
        """
        Execute the wrapped agent with data collection.
        
        This method captures all relevant data about the agent's execution
        including timing, LLM interactions, and move generation details.
        """
        collection_start = time.time()
        timing = TimingData(start_time=time.time())
        
        try:
            # Extract game state information
            serialized_game_and_state = observation.get("serializedGameAndState")
            if not serialized_game_and_state:
                # Setup step - no data collection needed
                return self.wrapped_agent(observation, configuration, **kwargs)
            
            # Parse game state
            _, pyspiel_state = pyspiel.deserialize_game_and_state(serialized_game_and_state)
            current_player = pyspiel_state.current_player()
            
            # Initialize game if needed
            if not self._game_started and self.game_id:
                self._initialize_game_collection(pyspiel_state)
            
            # Determine if this is our move
            player_index = self._get_player_index(current_player)
            if player_index is None:
                # Not our move, just pass through
                return self.wrapped_agent(observation, configuration, **kwargs)
            
            # Capture pre-move state
            fen_before = pyspiel_state.to_string()
            legal_moves = [pyspiel_state.action_to_string(action) 
                          for action in pyspiel_state.legal_actions()]
            
            # Execute wrapped agent with timing
            agent_start = time.time()
            result = self.wrapped_agent(observation, configuration, **kwargs)
            agent_end = time.time()
            
            timing.api_call_time_ms = (agent_end - agent_start) * 1000
            timing.finish()
            
            # Ensure result has the required submission key
            if not isinstance(result, dict) or 'submission' not in result:
                self.logger.error(f"Wrapped agent returned invalid result: {result}")
                return KaggleSpielActionWithExtras(
                    submission=ERROR_ACTION_INT,
                    actionString=None,
                    thoughts="Invalid result from wrapped agent",
                    status="Error: Invalid result format",
                    generate_returns=[]
                )
            
            # Capture post-move state and data
            if result['submission'] not in [INVALID_ACTION, ERROR_ACTION_INT]:
                self._move_number += 1
                
                # Calculate post-move state
                fen_after = self._calculate_post_move_fen(pyspiel_state, result)
                
                # Store generate_returns for rethink extraction
                self._current_generate_returns = result.get('generate_returns', [])
                
                # Extract LLM interaction data
                prompt_text, raw_response, rethink_attempts = self._extract_llm_data(result)
                
                # Record individual rethink attempts if any
                if rethink_attempts and self.collect_rethink:
                    for attempt in rethink_attempts:
                        self.collector.record_rethink_attempt(
                            self.game_id, 
                            self._move_number, 
                            player_index, 
                            {
                                'attempt_number': attempt.attempt_number,
                                'prompt_text': attempt.prompt_text,
                                'raw_response': attempt.raw_response,
                                'parsed_move': attempt.parsed_move,
                                'was_legal': attempt.was_legal
                            }
                        )
                
                # Collect move data
                move_data = {
                    'move_number': self._move_number,
                    'player': player_index,
                    'fen_before': fen_before,
                    'fen_after': fen_after,
                    'legal_moves': legal_moves,
                    'move_san': result.get('actionString', '') or "",
                    'move_uci': self._convert_to_uci(pyspiel_state, result),
                    'is_legal': result['submission'] in pyspiel_state.legal_actions(),
                    'prompt_text': prompt_text,
                    'raw_response': raw_response,
                    'parsed_move': result.get('actionString'),
                    'parsing_success': result['submission'] != INVALID_ACTION,
                    'parsing_attempts': 1,  # Could be enhanced based on agent type
                    'thinking_time_ms': int(timing.total_time_ms),
                    'api_call_time_ms': int(timing.api_call_time_ms),
                    'parsing_time_ms': int(timing.parsing_time_ms),
                    'rethink_attempts': rethink_attempts,
                    'error_type': self._extract_error_type(result),
                    'error_message': self._extract_error_message(result)
                }
                
                # Record the move asynchronously
                self._record_move_async(move_data)
            
            # Monitor collection performance
            collection_time = (time.time() - collection_start) * 1000
            self._monitor_collection_performance(collection_time)
            
            return result
            
        except Exception as e:
            # Log error but don't interrupt game execution
            self.logger.error(f"Error in data collection wrapper: {e}")
            if self.game_id:
                self.collector.record_error(
                    self.game_id,
                    "wrapper_error",
                    str(e),
                    {"player": self.player_info.player_id}
                )
            
            # Fall back to wrapped agent execution
            try:
                return self.wrapped_agent(observation, configuration, **kwargs)
            except Exception as agent_error:
                self.logger.error(f"Wrapped agent also failed: {agent_error}")
                # Return error action as last resort
                return KaggleSpielActionWithExtras(
                    submission=ERROR_ACTION_INT,
                    actionString=None,
                    thoughts=f"Agent wrapper error: {str(e)}",
                    status=f"Error: {str(agent_error)}",
                    generate_returns=[]
                )
    
    def _initialize_game_collection(self, pyspiel_state: pyspiel.State) -> None:
        """Initialize game data collection."""
        try:
            if self._game_started:
                return
            
            # Create players dictionary (we only know about ourselves)
            players = {
                self._get_player_index(pyspiel_state.current_player()): self.player_info
            }
            
            # Start game collection
            self.collector.start_game(
                self.game_id,
                players,
                {
                    'initial_fen': pyspiel_state.to_string(),
                    'agent_wrapper_version': '1.0'
                }
            )
            
            self._game_started = True
            self.logger.info(f"Initialized game collection for {self.game_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize game collection: {e}")
    
    def _get_player_index(self, current_player: int) -> Optional[int]:
        """
        Determine if the current player matches our player info.
        
        This is a simplified implementation - in practice, you'd need
        a way to map the current player to the correct player index.
        """
        # For now, assume we're always the current player when called
        # This would need to be enhanced based on tournament setup
        return current_player
    
    def _calculate_post_move_fen(
        self, 
        pyspiel_state: pyspiel.State, 
        result: Dict[str, Any]
    ) -> str:
        """Calculate the FEN position after the move."""
        try:
            if result['submission'] == INVALID_ACTION or result['submission'] == ERROR_ACTION_INT:
                return pyspiel_state.to_string()  # No change
            
            # Clone state and apply move
            new_state = pyspiel_state.clone()
            new_state.apply_action(result['submission'])
            return new_state.to_string()
            
        except Exception as e:
            self.logger.warning(f"Failed to calculate post-move FEN: {e}")
            return pyspiel_state.to_string()
    
    def _convert_to_uci(
        self, 
        pyspiel_state: pyspiel.State, 
        result: Dict[str, Any]
    ) -> str:
        """Convert move to UCI notation."""
        try:
            if result['submission'] == INVALID_ACTION or result['submission'] == ERROR_ACTION_INT:
                return ""
            
            # For chess, the action string is typically already in a usable format
            # This would need enhancement for proper UCI conversion
            return result.get('actionString', '') or ""
            
        except Exception as e:
            self.logger.warning(f"Failed to convert to UCI: {e}")
            return ""
    
    def _extract_llm_data(
        self, 
        result: Dict[str, Any]
    ) -> tuple[str, str, List[RethinkAttempt]]:
        """Extract LLM interaction data from agent result."""
        prompt_text = ""
        raw_response = result.get('thoughts', '') or ""
        rethink_attempts = []
        
        try:
            # Extract data from generate_returns if available
            if result.get('generate_returns'):
                # Handle both string and object formats
                if isinstance(result['generate_returns'][0], str):
                    # JSON string format
                    import json
                    for i, gen_return_str in enumerate(result['generate_returns']):
                        try:
                            gen_return_data = json.loads(gen_return_str)
                            if i == 0:
                                raw_response = gen_return_data.get('main_response', raw_response)
                            else:
                                # Additional returns are rethink attempts
                                if self.collect_rethink:
                                    rethink_attempt = RethinkAttempt(
                                        attempt_number=i,
                                        prompt_text="Rethink prompt (not captured)",  # Not available in this format
                                        raw_response=gen_return_data.get('main_response', ''),
                                        parsed_move=None,  # Would need parsing
                                        was_legal=False,  # Would need validation
                                        timestamp=datetime.now()
                                    )
                                    rethink_attempts.append(rethink_attempt)
                        except (json.JSONDecodeError, KeyError) as e:
                            self.logger.warning(f"Failed to parse generate_return {i}: {e}")
                else:
                    # Object format (GenerateReturn instances)
                    for i, gen_return in enumerate(result['generate_returns']):
                        if hasattr(gen_return, 'main_response'):
                            if i == 0:
                                raw_response = gen_return.main_response
                            else:
                                # Additional returns are rethink attempts
                                if self.collect_rethink:
                                    rethink_attempt = RethinkAttempt(
                                        attempt_number=i,
                                        prompt_text="Rethink prompt (not captured)",  # Not directly available
                                        raw_response=gen_return.main_response,
                                        parsed_move=None,
                                        was_legal=False,
                                        timestamp=datetime.now()
                                    )
                                    rethink_attempts.append(rethink_attempt)
            
            # Enhanced rethink data extraction for ChessRethinkAgent
            if isinstance(self.wrapped_agent, ChessRethinkAgent) and self.collect_rethink:
                # Try to extract rethink data from auxiliary outputs if available
                auxiliary_outputs = getattr(result, 'auxiliary_outputs', {}) if hasattr(result, 'auxiliary_outputs') else result.get('auxiliary_outputs', {})
                if isinstance(auxiliary_outputs, dict) and auxiliary_outputs:
                    extracted_rethinks = self._extract_rethink_from_auxiliary_outputs(auxiliary_outputs)
                    if extracted_rethinks:
                        rethink_attempts = extracted_rethinks
            
            # For ChessLLMAgent, we could potentially extract prompt from the agent
            if isinstance(self.wrapped_agent, ChessLLMAgent):
                # The prompt would have been generated by the prompt_builder
                # but we don't have direct access to it here
                prompt_text = "LLM prompt (not captured)"
            elif isinstance(self.wrapped_agent, ChessRethinkAgent):
                prompt_text = "Rethink prompt (not captured)"
            
        except Exception as e:
            self.logger.warning(f"Failed to extract LLM data: {e}")
        
        return prompt_text, raw_response, rethink_attempts
    
    def _extract_rethink_from_auxiliary_outputs(self, auxiliary_outputs: Dict[str, Any]) -> List[RethinkAttempt]:
        """Extract rethink attempts from auxiliary outputs of RethinkSampler."""
        rethink_attempts = []
        
        try:
            # RethinkSampler stores data in auxiliary_outputs with keys like:
            # - parsed_action_attempt_0, parsed_action_attempt_1, etc.
            # - maybe_legal_action_attempt_0, maybe_legal_action_attempt_1, etc.
            # - rethink_prompt_attempt_0, rethink_prompt_attempt_1, etc.
            
            attempt_number = 1  # Start from 1 since attempt 0 is the initial attempt
            
            while f'parsed_action_attempt_{attempt_number}' in auxiliary_outputs:
                parsed_action = auxiliary_outputs.get(f'parsed_action_attempt_{attempt_number}')
                maybe_legal_action = auxiliary_outputs.get(f'maybe_legal_action_attempt_{attempt_number}')
                rethink_prompt = auxiliary_outputs.get(f'rethink_prompt_attempt_{attempt_number}', '')
                
                # The raw response for rethink attempts is not directly available in auxiliary_outputs
                # We'll need to get it from generate_returns if available
                raw_response = f"Rethink attempt {attempt_number} response (not captured)"
                
                # Try to get the actual response from generate_returns
                if hasattr(self, '_current_generate_returns') and self._current_generate_returns:
                    if attempt_number < len(self._current_generate_returns):
                        gen_return = self._current_generate_returns[attempt_number]
                        if hasattr(gen_return, 'main_response'):
                            raw_response = gen_return.main_response
                
                rethink_attempt = RethinkAttempt(
                    attempt_number=attempt_number,
                    prompt_text=rethink_prompt or f"Rethink prompt {attempt_number} (not captured)",
                    raw_response=raw_response,
                    parsed_move=parsed_action,
                    was_legal=maybe_legal_action is not None,
                    timestamp=datetime.now()
                )
                
                rethink_attempts.append(rethink_attempt)
                attempt_number += 1
            
            self.logger.debug(f"Extracted {len(rethink_attempts)} rethink attempts from auxiliary outputs")
            
        except Exception as e:
            self.logger.warning(f"Failed to extract rethink attempts from auxiliary outputs: {e}")
        
        return rethink_attempts
    
    def _extract_error_type(self, result: Dict[str, Any]) -> Optional[str]:
        """Extract error type from agent result."""
        if result['submission'] == ERROR_ACTION_INT:
            return "agent_error"
        elif result['submission'] == INVALID_ACTION:
            return "invalid_move"
        elif result.get('status') and "error" in result['status'].lower():
            return "execution_error"
        return None
    
    def _extract_error_message(self, result: Dict[str, Any]) -> Optional[str]:
        """Extract error message from agent result."""
        status = result.get('status')
        if status and ("error" in status.lower() or 
                      result['submission'] in [INVALID_ACTION, ERROR_ACTION_INT]):
            return status
        return None
    
    def _record_move_async(self, move_data: Dict[str, Any]) -> None:
        """Record move data asynchronously."""
        try:
            if self.game_id:
                self.collector.record_move(self.game_id, move_data)
        except Exception as e:
            self.logger.error(f"Failed to record move data: {e}")
    
    def _monitor_collection_performance(self, collection_time_ms: float) -> None:
        """Monitor data collection performance."""
        try:
            # Track collection times
            self._collection_times.append(collection_time_ms)
            if len(self._collection_times) > self._max_collection_times:
                self._collection_times.pop(0)
            
            # Check performance constraint
            if collection_time_ms > self.max_collection_latency_ms:
                self.logger.warning(
                    f"Data collection took {collection_time_ms:.1f}ms, "
                    f"exceeding limit of {self.max_collection_latency_ms}ms"
                )
            
            # Log performance statistics periodically
            if len(self._collection_times) % 50 == 0:
                avg_time = sum(self._collection_times) / len(self._collection_times)
                max_time = max(self._collection_times)
                self.logger.info(
                    f"Collection performance: avg={avg_time:.1f}ms, max={max_time:.1f}ms"
                )
                
        except Exception as e:
            self.logger.warning(f"Failed to monitor collection performance: {e}")
    
    # Delegate properties and methods to wrapped agent
    
    @property
    def num_model_calls(self) -> int:
        """Get number of model calls from wrapped agent."""
        if hasattr(self.wrapped_agent, 'num_model_calls'):
            return self.wrapped_agent.num_model_calls
        return 0
    
    @property
    def num_sampler_calls(self) -> int:
        """Get number of sampler calls from wrapped agent."""
        if hasattr(self.wrapped_agent, 'num_sampler_calls'):
            return self.wrapped_agent.num_sampler_calls
        return 0
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get data collection statistics."""
        if not self._collection_times:
            return {
                'total_moves_collected': self._move_number,
                'average_collection_time_ms': 0.0,
                'max_collection_time_ms': 0.0,
                'collection_overhead_violations': 0
            }
        
        avg_time = sum(self._collection_times) / len(self._collection_times)
        max_time = max(self._collection_times)
        violations = sum(1 for t in self._collection_times if t > self.max_collection_latency_ms)
        
        return {
            'total_moves_collected': self._move_number,
            'average_collection_time_ms': avg_time,
            'max_collection_time_ms': max_time,
            'collection_overhead_violations': violations,
            'collection_samples': len(self._collection_times)
        }


def create_data_collecting_agent(
    agent: KaggleSpielAgent[KaggleSpielActionWithExtras],
    collector: GameDataCollector,
    player_info: PlayerInfo,
    **kwargs
) -> DataCollectingAgent:
    """
    Factory function to create a data collecting agent wrapper.
    
    Args:
        agent: The agent to wrap
        collector: GameDataCollector instance
        player_info: Information about the player
        **kwargs: Additional arguments for DataCollectingAgent
        
    Returns:
        DataCollectingAgent wrapper instance
    """
    return DataCollectingAgent(
        wrapped_agent=agent,
        collector=collector,
        player_info=player_info,
        **kwargs
    )