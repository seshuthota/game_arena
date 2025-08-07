"""
Game Data Collector for the Game Arena storage system.

This module provides the GameDataCollector class that captures game events,
processes them asynchronously, and coordinates data storage with validation
and transformation logic.
"""

import asyncio
import logging
import time
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Callable, AsyncGenerator
from queue import Queue, Empty
import threading
import traceback

from .models import GameRecord, MoveRecord, PlayerInfo, GameOutcome, RethinkAttempt
from .manager import StorageManager
from .config import CollectorConfig
from .exceptions import ValidationError, PerformanceError


logger = logging.getLogger(__name__)


class EventType(Enum):
    """Types of game events that can be collected."""
    GAME_START = "game_start"
    MOVE_MADE = "move_made"
    GAME_END = "game_end"
    RETHINK_ATTEMPT = "rethink_attempt"
    ERROR_OCCURRED = "error_occurred"


@dataclass
class GameEvent:
    """Represents a single game event to be processed."""
    event_id: str
    event_type: EventType
    game_id: str
    timestamp: datetime
    data: Dict[str, Any]
    retry_count: int = 0
    
    def __post_init__(self):
        """Validate event data."""
        if not self.event_id:
            raise ValueError("event_id cannot be empty")
        if not self.game_id:
            raise ValueError("game_id cannot be empty")
        if self.retry_count < 0:
            raise ValueError("retry_count cannot be negative")


@dataclass
class ProcessingStats:
    """Statistics about event processing."""
    events_received: int = 0
    events_processed: int = 0
    events_failed: int = 0
    events_retried: int = 0
    processing_errors: List[str] = field(default_factory=list)
    average_processing_time_ms: float = 0.0
    queue_size: int = 0
    last_updated: datetime = field(default_factory=datetime.now)


class GameDataCollector:
    """
    Central component for capturing and processing game events.
    
    Provides event capture, asynchronous processing, data validation,
    and coordination with the storage manager.
    """
    
    def __init__(self, storage_manager: StorageManager, config: CollectorConfig):
        """Initialize the game data collector."""
        self.storage_manager = storage_manager
        self.config = config
        
        # Event processing
        self._event_queue: Queue[GameEvent] = Queue(maxsize=config.queue_size)
        self._processing_workers: List[threading.Thread] = []
        self._shutdown_event = threading.Event()
        self._stats = ProcessingStats()
        self._stats_lock = threading.Lock()
        
        # Active games tracking
        self._active_games: Dict[str, GameRecord] = {}
        self._games_lock = threading.Lock()
        
        # Event handlers
        self._event_handlers: Dict[EventType, Callable] = {
            EventType.GAME_START: self._handle_game_start,
            EventType.MOVE_MADE: self._handle_move_made,
            EventType.GAME_END: self._handle_game_end,
            EventType.RETHINK_ATTEMPT: self._handle_rethink_attempt,
            EventType.ERROR_OCCURRED: self._handle_error,
        }
        
        # Setup logging
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.logger.setLevel(logging.INFO)
        
        # Performance tracking
        self._processing_times: List[float] = []
        self._max_processing_times = 1000  # Keep last 1000 processing times
    
    async def initialize(self) -> None:
        """Initialize the collector and start processing workers."""
        if not self.config.enabled:
            self.logger.info("Data collection is disabled")
            return
        
        try:
            # Start processing workers
            if self.config.async_processing:
                for i in range(self.config.worker_threads):
                    worker = threading.Thread(
                        target=self._processing_worker,
                        name=f"GameDataCollector-Worker-{i}",
                        daemon=True
                    )
                    worker.start()
                    self._processing_workers.append(worker)
                
                self.logger.info(f"Started {len(self._processing_workers)} processing workers")
            
            self.logger.info("Game data collector initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize game data collector: {e}")
            raise
    
    async def shutdown(self) -> None:
        """Shutdown the collector and stop processing workers."""
        try:
            self.logger.info("Shutting down game data collector...")
            
            # Signal shutdown to workers
            self._shutdown_event.set()
            
            # Wait for workers to finish processing current events
            for worker in self._processing_workers:
                worker.join(timeout=5.0)
                if worker.is_alive():
                    self.logger.warning(f"Worker {worker.name} did not shutdown gracefully")
            
            # Process any remaining events synchronously
            remaining_events = []
            try:
                while True:
                    event = self._event_queue.get_nowait()
                    remaining_events.append(event)
            except Empty:
                pass
            
            if remaining_events:
                self.logger.info(f"Processing {len(remaining_events)} remaining events")
                for event in remaining_events:
                    await self._process_event_sync(event)
            
            self.logger.info("Game data collector shutdown complete")
            
        except Exception as e:
            self.logger.error(f"Error during collector shutdown: {e}")
    
    def _processing_worker(self) -> None:
        """Worker thread for processing events asynchronously."""
        worker_name = threading.current_thread().name
        self.logger.debug(f"Started processing worker: {worker_name}")
        
        while not self._shutdown_event.is_set():
            try:
                # Get event from queue with timeout
                try:
                    event = self._event_queue.get(timeout=1.0)
                except Empty:
                    continue
                
                # Process the event
                start_time = time.time()
                try:
                    asyncio.run(self._process_event_sync(event))
                    processing_time = (time.time() - start_time) * 1000  # Convert to ms
                    
                    # Update statistics
                    with self._stats_lock:
                        self._stats.events_processed += 1
                        self._processing_times.append(processing_time)
                        if len(self._processing_times) > self._max_processing_times:
                            self._processing_times.pop(0)
                        self._stats.average_processing_time_ms = sum(self._processing_times) / len(self._processing_times)
                        self._stats.last_updated = datetime.now()
                    
                    # Check performance constraint
                    if processing_time > self.config.max_collection_latency_ms:
                        self.logger.warning(
                            f"Event processing took {processing_time:.1f}ms, "
                            f"exceeding limit of {self.config.max_collection_latency_ms}ms"
                        )
                
                except Exception as e:
                    self.logger.error(f"Error processing event {event.event_id}: {e}")
                    with self._stats_lock:
                        self._stats.events_failed += 1
                        self._stats.processing_errors.append(f"{event.event_type.value}: {str(e)}")
                        # Keep only last 100 errors
                        if len(self._stats.processing_errors) > 100:
                            self._stats.processing_errors.pop(0)
                    
                    # Retry logic
                    if event.retry_count < self.config.max_retry_attempts:
                        event.retry_count += 1
                        time.sleep(self.config.retry_delay_seconds)
                        try:
                            self._event_queue.put_nowait(event)
                            with self._stats_lock:
                                self._stats.events_retried += 1
                        except:
                            self.logger.error(f"Failed to requeue event {event.event_id} for retry")
                
                finally:
                    self._event_queue.task_done()
                    
            except Exception as e:
                self.logger.error(f"Unexpected error in processing worker {worker_name}: {e}")
        
        self.logger.debug(f"Processing worker {worker_name} shutting down")
    
    async def _process_event_sync(self, event: GameEvent) -> None:
        """Process a single event synchronously."""
        try:
            handler = self._event_handlers.get(event.event_type)
            if not handler:
                raise ValueError(f"No handler for event type: {event.event_type}")
            
            await handler(event)
            
        except Exception as e:
            self.logger.error(f"Failed to process event {event.event_id}: {e}")
            raise
    
    def _queue_event(self, event: GameEvent) -> bool:
        """Queue an event for processing."""
        try:
            if self.config.async_processing:
                self._event_queue.put_nowait(event)
            else:
                # Process synchronously - run in current thread
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # If we're already in an async context, schedule the task
                        asyncio.create_task(self._process_event_sync(event))
                    else:
                        # Run synchronously
                        loop.run_until_complete(self._process_event_sync(event))
                except RuntimeError:
                    # No event loop, run with new loop
                    asyncio.run(self._process_event_sync(event))
            
            with self._stats_lock:
                self._stats.events_received += 1
                self._stats.queue_size = self._event_queue.qsize()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to queue event {event.event_id}: {e}")
            if not self.config.continue_on_collection_error:
                raise
            return False
    
    # Public API for event capture
    
    def start_game(self, game_id: str, players: Dict[int, PlayerInfo], 
                   metadata: Dict[str, Any] = None) -> bool:
        """
        Capture a game start event.
        
        Args:
            game_id: Unique identifier for the game
            players: Dictionary mapping player indices to PlayerInfo
            metadata: Additional game metadata
            
        Returns:
            True if event was queued successfully
        """
        try:
            event = GameEvent(
                event_id=str(uuid.uuid4()),
                event_type=EventType.GAME_START,
                game_id=game_id,
                timestamp=datetime.now(),
                data={
                    'players': players,
                    'metadata': metadata or {}
                }
            )
            
            return self._queue_event(event)
            
        except Exception as e:
            self.logger.error(f"Failed to capture game start event for {game_id}: {e}")
            if not self.config.continue_on_collection_error:
                raise
            return False
    
    def record_move(self, game_id: str, move_data: Dict[str, Any]) -> bool:
        """
        Capture a move event.
        
        Args:
            game_id: ID of the game
            move_data: Dictionary containing move information
            
        Returns:
            True if event was queued successfully
        """
        try:
            event = GameEvent(
                event_id=str(uuid.uuid4()),
                event_type=EventType.MOVE_MADE,
                game_id=game_id,
                timestamp=datetime.now(),
                data=move_data
            )
            
            return self._queue_event(event)
            
        except Exception as e:
            self.logger.error(f"Failed to capture move event for {game_id}: {e}")
            if not self.config.continue_on_collection_error:
                raise
            return False
    
    def end_game(self, game_id: str, outcome: GameOutcome, 
                 final_fen: str, total_moves: int) -> bool:
        """
        Capture a game end event.
        
        Args:
            game_id: ID of the game
            outcome: Final game outcome
            final_fen: Final board position
            total_moves: Total number of moves played
            
        Returns:
            True if event was queued successfully
        """
        try:
            event = GameEvent(
                event_id=str(uuid.uuid4()),
                event_type=EventType.GAME_END,
                game_id=game_id,
                timestamp=datetime.now(),
                data={
                    'outcome': outcome,
                    'final_fen': final_fen,
                    'total_moves': total_moves
                }
            )
            
            return self._queue_event(event)
            
        except Exception as e:
            self.logger.error(f"Failed to capture game end event for {game_id}: {e}")
            if not self.config.continue_on_collection_error:
                raise
            return False
    
    def record_rethink_attempt(self, game_id: str, move_number: int, 
                              player: int, attempt_data: Dict[str, Any]) -> bool:
        """
        Capture a rethink attempt event.
        
        Args:
            game_id: ID of the game
            move_number: Move number being rethought
            player: Player making the rethink attempt
            attempt_data: Rethink attempt information
            
        Returns:
            True if event was queued successfully
        """
        try:
            if not self.config.collect_rethink_data:
                return True  # Skip if rethink collection is disabled
            
            event = GameEvent(
                event_id=str(uuid.uuid4()),
                event_type=EventType.RETHINK_ATTEMPT,
                game_id=game_id,
                timestamp=datetime.now(),
                data={
                    'move_number': move_number,
                    'player': player,
                    'attempt_data': attempt_data
                }
            )
            
            return self._queue_event(event)
            
        except Exception as e:
            self.logger.error(f"Failed to capture rethink attempt event for {game_id}: {e}")
            if not self.config.continue_on_collection_error:
                raise
            return False
    
    def record_error(self, game_id: str, error_type: str, 
                     error_message: str, context: Dict[str, Any] = None) -> bool:
        """
        Capture an error event.
        
        Args:
            game_id: ID of the game where error occurred
            error_type: Type of error
            error_message: Error message
            context: Additional error context
            
        Returns:
            True if event was queued successfully
        """
        try:
            event = GameEvent(
                event_id=str(uuid.uuid4()),
                event_type=EventType.ERROR_OCCURRED,
                game_id=game_id,
                timestamp=datetime.now(),
                data={
                    'error_type': error_type,
                    'error_message': error_message,
                    'context': context or {}
                }
            )
            
            return self._queue_event(event)
            
        except Exception as e:
            self.logger.error(f"Failed to capture error event for {game_id}: {e}")
            return False  # Don't raise on error event failures
    
    # Event handlers
    
    async def _handle_game_start(self, event: GameEvent) -> None:
        """Handle game start event."""
        try:
            players = event.data['players']
            metadata = event.data['metadata']
            
            # Validate players data
            if not isinstance(players, dict) or len(players) != 2:
                raise ValidationError("Game must have exactly 2 players")
            
            if 0 not in players or 1 not in players:
                raise ValidationError("Players must be indexed as 0 and 1")
            
            # Create game record
            game_record = GameRecord(
                game_id=event.game_id,
                start_time=event.timestamp,
                players=players,
                tournament_id=metadata.get('tournament_id'),
                metadata=metadata
            )
            
            # Store in active games
            with self._games_lock:
                self._active_games[event.game_id] = game_record
            
            # Store in database
            await self.storage_manager.create_game(game_record)
            
            self.logger.info(f"Started game {event.game_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to handle game start event: {e}")
            raise
    
    async def _handle_move_made(self, event: GameEvent) -> None:
        """Handle move made event."""
        try:
            # Validate required move data
            required_fields = [
                'move_number', 'player', 'fen_before', 'fen_after',
                'move_san', 'move_uci', 'is_legal', 'prompt_text', 'raw_response'
            ]
            
            for field in required_fields:
                if field not in event.data:
                    raise ValidationError(f"Missing required field: {field}")
            
            # Create move record with data transformation
            move_record = MoveRecord(
                game_id=event.game_id,
                move_number=event.data['move_number'],
                player=event.data['player'],
                timestamp=event.timestamp,
                fen_before=event.data['fen_before'],
                fen_after=event.data['fen_after'],
                legal_moves=event.data.get('legal_moves', []),
                move_san=event.data['move_san'],
                move_uci=event.data['move_uci'],
                is_legal=event.data['is_legal'],
                prompt_text=event.data['prompt_text'],
                raw_response=event.data['raw_response'],
                parsed_move=event.data.get('parsed_move'),
                parsing_success=event.data.get('parsing_success', True),
                parsing_attempts=event.data.get('parsing_attempts', 1),
                thinking_time_ms=event.data.get('thinking_time_ms', 0),
                api_call_time_ms=event.data.get('api_call_time_ms', 0),
                parsing_time_ms=event.data.get('parsing_time_ms', 0),
                rethink_attempts=event.data.get('rethink_attempts', []),
                move_quality_score=event.data.get('move_quality_score'),
                blunder_flag=event.data.get('blunder_flag', False),
                error_type=event.data.get('error_type'),
                error_message=event.data.get('error_message')
            )
            
            # Store move in database
            await self.storage_manager.add_move(move_record)
            
            # Update active game move count
            with self._games_lock:
                if event.game_id in self._active_games:
                    self._active_games[event.game_id].total_moves += 1
            
            self.logger.debug(f"Recorded move {move_record.move_number} for game {event.game_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to handle move event: {e}")
            raise
    
    async def _handle_game_end(self, event: GameEvent) -> None:
        """Handle game end event."""
        try:
            outcome = event.data['outcome']
            final_fen = event.data['final_fen']
            total_moves = event.data['total_moves']
            
            # Complete the game in storage
            await self.storage_manager.complete_game(
                event.game_id, outcome, final_fen, total_moves
            )
            
            # Remove from active games
            with self._games_lock:
                self._active_games.pop(event.game_id, None)
            
            self.logger.info(f"Completed game {event.game_id} with outcome {outcome.result.value}")
            
        except Exception as e:
            self.logger.error(f"Failed to handle game end event: {e}")
            raise
    
    async def _handle_rethink_attempt(self, event: GameEvent) -> None:
        """Handle rethink attempt event."""
        try:
            move_number = event.data['move_number']
            player = event.data['player']
            attempt_data = event.data['attempt_data']
            
            # Validate required fields
            required_fields = ['attempt_number', 'prompt_text', 'raw_response']
            for field in required_fields:
                if field not in attempt_data:
                    raise ValidationError(f"Missing required rethink field: {field}")
            
            # Create rethink attempt record
            rethink_attempt = RethinkAttempt(
                attempt_number=attempt_data['attempt_number'],
                prompt_text=attempt_data['prompt_text'],
                raw_response=attempt_data['raw_response'],
                parsed_move=attempt_data.get('parsed_move'),
                was_legal=attempt_data.get('was_legal', False),
                timestamp=event.timestamp
            )
            
            # Store rethink attempt in database
            await self.storage_manager.add_rethink_attempt(
                event.game_id, move_number, player, rethink_attempt
            )
            
            self.logger.debug(
                f"Recorded rethink attempt {rethink_attempt.attempt_number} "
                f"for move {move_number} by player {player} in game {event.game_id}"
            )
            
        except Exception as e:
            self.logger.error(f"Failed to handle rethink attempt event: {e}")
            raise
    
    async def _handle_error(self, event: GameEvent) -> None:
        """Handle error event."""
        try:
            error_type = event.data['error_type']
            error_message = event.data['error_message']
            context = event.data['context']
            
            # Log the error with context
            self.logger.error(
                f"Game error in {event.game_id}: {error_type} - {error_message}. "
                f"Context: {context}"
            )
            
            # Could store error information in database for analysis
            # For now, we just log it
            
        except Exception as e:
            self.logger.error(f"Failed to handle error event: {e}")
            raise
    
    # Statistics and monitoring
    
    def get_stats(self) -> ProcessingStats:
        """Get current processing statistics."""
        with self._stats_lock:
            # Create a copy to avoid race conditions
            stats_copy = ProcessingStats(
                events_received=self._stats.events_received,
                events_processed=self._stats.events_processed,
                events_failed=self._stats.events_failed,
                events_retried=self._stats.events_retried,
                processing_errors=self._stats.processing_errors.copy(),
                average_processing_time_ms=self._stats.average_processing_time_ms,
                queue_size=self._event_queue.qsize(),
                last_updated=datetime.now()
            )
        return stats_copy
    
    def get_active_games(self) -> List[str]:
        """Get list of currently active game IDs."""
        with self._games_lock:
            return list(self._active_games.keys())
    
    def is_game_active(self, game_id: str) -> bool:
        """Check if a game is currently active."""
        with self._games_lock:
            return game_id in self._active_games
    
    def clear_stats(self) -> None:
        """Clear processing statistics."""
        with self._stats_lock:
            self._stats = ProcessingStats()
            self._processing_times.clear()