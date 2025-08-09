"""
Pydantic models for API request/response serialization.

This module defines the data models used for API requests and responses,
providing validation, serialization, and documentation for the web interface.
"""

from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from enum import Enum

from pydantic import BaseModel, Field, field_validator


# Enums for API models
class GameResultEnum(str, Enum):
    """Game result enumeration for API responses."""
    WHITE_WINS = "white_wins"
    BLACK_WINS = "black_wins"
    DRAW = "draw"
    ONGOING = "ongoing"


class TerminationReasonEnum(str, Enum):
    """Game termination reason enumeration."""
    CHECKMATE = "checkmate"
    STALEMATE = "stalemate"
    INSUFFICIENT_MATERIAL = "insufficient_material"
    THREEFOLD_REPETITION = "threefold_repetition"
    FIFTY_MOVE_RULE = "fifty_move_rule"
    TIME_FORFEIT = "time_forfeit"
    RESIGNATION = "resignation"
    AGREEMENT = "agreement"
    ABANDONED = "abandoned"


# Base response models
class BaseResponse(BaseModel):
    """Base response model with common fields."""
    success: bool = True
    timestamp: datetime = Field(default_factory=datetime.now)


class ErrorResponse(BaseModel):
    """Error response model."""
    success: bool = False
    error: str
    detail: str
    error_code: str
    timestamp: datetime = Field(default_factory=datetime.now)


class PaginationMeta(BaseModel):
    """Pagination metadata for list responses."""
    page: int = Field(..., description="Current page number (1-based)")
    limit: int = Field(..., description="Number of items per page")
    total_count: int = Field(..., description="Total number of items")
    total_pages: int = Field(..., description="Total number of pages")
    has_next: bool = Field(..., description="Whether there are more pages")
    has_previous: bool = Field(..., description="Whether there are previous pages")
    
    @field_validator('total_pages')
    @classmethod
    def calculate_total_pages(cls, v, info):
        """Calculate total pages from total_count and limit."""
        if info.data and 'total_count' in info.data and 'limit' in info.data:
            limit = info.data['limit']
            total_count = info.data['total_count']
            return (total_count + limit - 1) // limit if limit > 0 else 0
        return v
    
    @field_validator('has_next')
    @classmethod
    def calculate_has_next(cls, v, info):
        """Calculate if there are more pages."""
        if info.data and 'page' in info.data and 'total_pages' in info.data:
            return info.data['page'] < info.data['total_pages']
        return False
    
    @field_validator('has_previous')
    @classmethod
    def calculate_has_previous(cls, v, info):
        """Calculate if there are previous pages."""
        if info.data and 'page' in info.data:
            return info.data['page'] > 1
        return False


# Player models
class PlayerInfo(BaseModel):
    """Player information model."""
    player_id: str = Field(..., description="Unique player identifier")
    model_name: str = Field(..., description="Name of the AI model")
    model_provider: str = Field(..., description="Provider of the AI model")
    agent_type: str = Field(..., description="Type of agent implementation")
    elo_rating: Optional[float] = Field(None, description="Current ELO rating")


class PlayerRanking(BaseModel):
    """Player ranking information for leaderboards."""
    player_id: str = Field(..., description="Unique player identifier")
    model_name: str = Field(..., description="Name of the AI model")
    rank: int = Field(..., description="Current ranking position")
    games_played: int = Field(..., description="Total number of games played")
    wins: int = Field(..., description="Number of wins")
    losses: int = Field(..., description="Number of losses")
    draws: int = Field(..., description="Number of draws")
    win_rate: float = Field(..., description="Win rate as percentage (0-100)")
    average_game_length: float = Field(..., description="Average game length in moves")
    elo_rating: float = Field(..., description="Current ELO rating")


class PlayerStatistics(BaseModel):
    """Detailed player statistics."""
    player_id: str = Field(..., description="Unique player identifier")
    model_name: str = Field(..., description="Name of the AI model")
    total_games: int = Field(..., description="Total number of games played")
    wins: int = Field(..., description="Number of wins")
    losses: int = Field(..., description="Number of losses")
    draws: int = Field(..., description="Number of draws")
    win_rate: float = Field(..., description="Win rate as percentage (0-100)")
    average_game_duration: float = Field(..., description="Average game duration in minutes")
    total_moves: int = Field(..., description="Total number of moves made")
    legal_moves: int = Field(..., description="Number of legal moves")
    illegal_moves: int = Field(..., description="Number of illegal moves")
    move_accuracy: float = Field(..., description="Move accuracy as percentage (0-100)")
    parsing_success_rate: float = Field(..., description="Parsing success rate as percentage (0-100)")
    average_thinking_time: float = Field(..., description="Average thinking time in milliseconds")
    blunders: int = Field(..., description="Number of moves marked as blunders")
    elo_rating: float = Field(..., description="Current ELO rating")


# Game models
class GameOutcome(BaseModel):
    """Game outcome information."""
    result: GameResultEnum = Field(..., description="Game result")
    winner: Optional[int] = Field(None, description="Winner player index (0 or 1), None for draws")
    termination: TerminationReasonEnum = Field(..., description="How the game ended")
    termination_details: Optional[str] = Field(None, description="Additional termination details")


class GameSummary(BaseModel):
    """Summary information for game list views."""
    game_id: str = Field(..., description="Unique game identifier")
    tournament_id: Optional[str] = Field(None, description="Tournament identifier if applicable")
    start_time: datetime = Field(..., description="Game start timestamp")
    end_time: Optional[datetime] = Field(None, description="Game end timestamp")
    players: Dict[str, PlayerInfo] = Field(..., description="Player information by position")
    outcome: Optional[GameOutcome] = Field(None, description="Game outcome if completed")
    total_moves: int = Field(..., description="Total number of moves played")
    duration_minutes: Optional[float] = Field(None, description="Game duration in minutes")
    is_completed: bool = Field(..., description="Whether the game is completed")


class MoveRecord(BaseModel):
    """Individual move record."""
    move_number: int = Field(..., description="Move number in the game")
    player: int = Field(..., description="Player who made the move (0 or 1)")
    move_notation: str = Field(..., description="Move in algebraic notation")
    fen_before: str = Field(..., description="Board position before the move")
    fen_after: str = Field(..., description="Board position after the move")
    is_legal: bool = Field(..., description="Whether the move was legal")
    parsing_success: bool = Field(..., description="Whether move parsing succeeded")
    thinking_time_ms: int = Field(..., description="Time spent thinking about the move")
    api_call_time_ms: int = Field(..., description="Time spent on API call")
    total_time_ms: int = Field(..., description="Total time for the move")
    had_rethink: bool = Field(..., description="Whether the player had to rethink")
    rethink_attempts: int = Field(..., description="Number of rethink attempts")
    blunder_flag: bool = Field(..., description="Whether the move was marked as a blunder")
    move_quality_score: Optional[float] = Field(None, description="Quality score of the move")
    llm_response: Optional[str] = Field(None, description="Raw LLM response")


class GameDetail(BaseModel):
    """Detailed game information."""
    game_id: str = Field(..., description="Unique game identifier")
    tournament_id: Optional[str] = Field(None, description="Tournament identifier if applicable")
    start_time: datetime = Field(..., description="Game start timestamp")
    end_time: Optional[datetime] = Field(None, description="Game end timestamp")
    players: Dict[str, PlayerInfo] = Field(..., description="Player information by position")
    outcome: Optional[GameOutcome] = Field(None, description="Game outcome if completed")
    total_moves: int = Field(..., description="Total number of moves played")
    duration_minutes: Optional[float] = Field(None, description="Game duration in minutes")
    is_completed: bool = Field(..., description="Whether the game is completed")
    initial_fen: str = Field(..., description="Initial board position")
    final_fen: Optional[str] = Field(None, description="Final board position")
    moves: List[MoveRecord] = Field(..., description="List of all moves in the game")


# Statistics models
class OverallStatistics(BaseModel):
    """Overall game statistics."""
    total_games: int = Field(..., description="Total number of games")
    completed_games: int = Field(..., description="Number of completed games")
    ongoing_games: int = Field(..., description="Number of ongoing games")
    total_players: int = Field(..., description="Total number of unique players")
    total_moves: int = Field(..., description="Total number of moves across all games")
    average_game_duration: float = Field(..., description="Average game duration in minutes")
    average_moves_per_game: float = Field(..., description="Average number of moves per game")
    games_by_result: Dict[str, int] = Field(..., description="Game count by result type")
    games_by_termination: Dict[str, int] = Field(..., description="Game count by termination reason")
    most_active_player: Optional[str] = Field(None, description="Player with most games")
    longest_game_id: Optional[str] = Field(None, description="ID of the longest game")
    shortest_game_id: Optional[str] = Field(None, description="ID of the shortest game")


class TimeSeriesDataPoint(BaseModel):
    """Single data point in time series."""
    timestamp: datetime = Field(..., description="Data point timestamp")
    value: float = Field(..., description="Metric value")
    count: Optional[int] = Field(None, description="Count of items for this data point")


class TimeSeriesData(BaseModel):
    """Time series data for charts."""
    metric: str = Field(..., description="Name of the metric")
    interval: str = Field(..., description="Time interval (daily, weekly, monthly)")
    data_points: List[TimeSeriesDataPoint] = Field(..., description="Time series data points")
    total_count: int = Field(..., description="Total number of data points")


# API Response models
class GameListResponse(BaseResponse):
    """Response model for game list endpoint."""
    games: List[GameSummary] = Field(..., description="List of game summaries")
    pagination: PaginationMeta = Field(..., description="Pagination metadata")
    filters_applied: Dict[str, Any] = Field(default_factory=dict, description="Applied filters")


class GameDetailResponse(BaseResponse):
    """Response model for game detail endpoint."""
    game: GameDetail = Field(..., description="Detailed game information")


class StatisticsOverviewResponse(BaseResponse):
    """Response model for statistics overview endpoint."""
    statistics: OverallStatistics = Field(..., description="Overall statistics")
    filters_applied: Dict[str, Any] = Field(default_factory=dict, description="Applied filters")


class TimeSeriesResponse(BaseResponse):
    """Response model for time series data endpoint."""
    time_series: TimeSeriesData = Field(..., description="Time series data")
    filters_applied: Dict[str, Any] = Field(default_factory=dict, description="Applied filters")


class LeaderboardResponse(BaseResponse):
    """Response model for leaderboard endpoint."""
    players: List[PlayerRanking] = Field(..., description="Player rankings")
    pagination: PaginationMeta = Field(..., description="Pagination metadata")
    sort_by: str = Field(..., description="Sorting criteria used")
    filters_applied: Dict[str, Any] = Field(default_factory=dict, description="Applied filters")


class PlayerStatisticsResponse(BaseResponse):
    """Response model for player statistics endpoint."""
    statistics: PlayerStatistics = Field(..., description="Player statistics")


class SearchResponse(BaseResponse):
    """Response model for search endpoints."""
    results: List[Union[GameSummary, PlayerInfo]] = Field(..., description="Search results")
    query: str = Field(..., description="Search query used")
    result_count: int = Field(..., description="Number of results found")
    search_type: str = Field(..., description="Type of search performed")


# Request models for filtering
class GameFiltersRequest(BaseModel):
    """Request model for game filtering parameters."""
    player_ids: Optional[List[str]] = Field(None, description="Filter by player IDs")
    model_names: Optional[List[str]] = Field(None, description="Filter by model names")
    model_providers: Optional[List[str]] = Field(None, description="Filter by model providers")
    tournament_ids: Optional[List[str]] = Field(None, description="Filter by tournament IDs")
    start_date: Optional[datetime] = Field(None, description="Filter games started after this date")
    end_date: Optional[datetime] = Field(None, description="Filter games started before this date")
    results: Optional[List[GameResultEnum]] = Field(None, description="Filter by game results")
    termination_reasons: Optional[List[TerminationReasonEnum]] = Field(None, description="Filter by termination reasons")
    min_moves: Optional[int] = Field(None, ge=0, description="Minimum number of moves")
    max_moves: Optional[int] = Field(None, ge=0, description="Maximum number of moves")
    min_duration: Optional[float] = Field(None, ge=0, description="Minimum game duration in minutes")
    max_duration: Optional[float] = Field(None, ge=0, description="Maximum game duration in minutes")
    completed_only: bool = Field(True, description="Only include completed games")

    @field_validator('start_date', 'end_date')
    @classmethod
    def validate_dates(cls, v):
        """Validate date formats."""
        if v and isinstance(v, str):
            from datetime import datetime
            try:
                return datetime.fromisoformat(v.replace('Z', '+00:00'))
            except ValueError:
                raise ValueError("Date must be in ISO format (YYYY-MM-DDTHH:MM:SSZ)")
        return v
    
    @field_validator('max_moves')
    @classmethod
    def validate_max_moves(cls, v, info):
        """Validate that max_moves is greater than min_moves."""
        if v is not None and 'min_moves' in info.data and info.data['min_moves'] is not None:
            if v < info.data['min_moves']:
                raise ValueError("max_moves must be greater than or equal to min_moves")
        return v


class SearchRequest(BaseModel):
    """Request model for search operations."""
    query: str = Field(..., min_length=1, max_length=500, description="Search query")
    search_fields: Optional[List[str]] = Field(None, description="Fields to search in")
    limit: Optional[int] = Field(50, ge=1, le=1000, description="Maximum number of results")
    
    @field_validator('search_fields')
    @classmethod
    def validate_search_fields(cls, v):
        """Validate search field names."""
        if v:
            valid_fields = {'player_names', 'game_id', 'tournament_id', 'all'}
            invalid_fields = set(v) - valid_fields
            if invalid_fields:
                raise ValueError(f"Invalid search fields: {', '.join(invalid_fields)}. Valid fields: {', '.join(valid_fields)}")
        return v


class SortOptions(str, Enum):
    """Sorting options for various endpoints."""
    START_TIME_ASC = "start_time_asc"
    START_TIME_DESC = "start_time_desc"
    DURATION_ASC = "duration_asc"
    DURATION_DESC = "duration_desc"
    MOVES_ASC = "moves_asc"
    MOVES_DESC = "moves_desc"
    WIN_RATE_ASC = "win_rate_asc"
    WIN_RATE_DESC = "win_rate_desc"
    GAMES_PLAYED_ASC = "games_played_asc"
    GAMES_PLAYED_DESC = "games_played_desc"
    ELO_RATING_ASC = "elo_rating_asc"
    ELO_RATING_DESC = "elo_rating_desc"


class AdvancedGameFiltersRequest(BaseModel):
    """Advanced request model for comprehensive game filtering."""
    # Search
    search: Optional[str] = Field(None, max_length=500, description="Search query")
    search_fields: Optional[List[str]] = Field(None, description="Fields to search in")
    
    # Basic filters
    player_id: Optional[str] = Field(None, description="Single player ID filter")
    player_ids: Optional[List[str]] = Field(None, description="Multiple player IDs filter")
    model_name: Optional[str] = Field(None, description="Single model name filter")
    model_names: Optional[List[str]] = Field(None, description="Multiple model names filter")
    model_provider: Optional[str] = Field(None, description="Single model provider filter")
    model_providers: Optional[List[str]] = Field(None, description="Multiple model providers filter")
    tournament_id: Optional[str] = Field(None, description="Single tournament ID filter")
    tournament_ids: Optional[List[str]] = Field(None, description="Multiple tournament IDs filter")
    
    # Date filters
    start_date: Optional[datetime] = Field(None, description="Filter games started after this date")
    end_date: Optional[datetime] = Field(None, description="Filter games started before this date")
    
    # Game outcome filters
    result: Optional[GameResultEnum] = Field(None, description="Game result filter")
    results: Optional[List[GameResultEnum]] = Field(None, description="Multiple game results filter")
    termination: Optional[TerminationReasonEnum] = Field(None, description="Termination reason filter")
    termination_reasons: Optional[List[TerminationReasonEnum]] = Field(None, description="Multiple termination reasons filter")
    
    # Numeric filters
    min_moves: Optional[int] = Field(None, ge=0, description="Minimum number of moves")
    max_moves: Optional[int] = Field(None, ge=0, description="Maximum number of moves")
    min_duration: Optional[float] = Field(None, ge=0, description="Minimum game duration in minutes")
    max_duration: Optional[float] = Field(None, ge=0, description="Maximum game duration in minutes")
    
    # Status filters
    completed_only: Optional[bool] = Field(True, description="Only include completed games")
    ongoing_only: Optional[bool] = Field(False, description="Only include ongoing games")
    
    # Pagination
    page: Optional[int] = Field(1, ge=1, description="Page number")
    limit: Optional[int] = Field(50, ge=1, le=1000, description="Items per page")
    sort_by: Optional[SortOptions] = Field(SortOptions.START_TIME_DESC, description="Sort order")
    
    @field_validator('end_date')
    @classmethod
    def validate_end_date(cls, v, info):
        """Validate that end_date is after start_date."""
        if v and 'start_date' in info.data and info.data['start_date']:
            if v < info.data['start_date']:
                raise ValueError("end_date must be after start_date")
        return v
    
    @field_validator('max_moves')
    @classmethod
    def validate_max_moves(cls, v, info):
        """Validate that max_moves is greater than min_moves."""
        if v is not None and 'min_moves' in info.data and info.data['min_moves'] is not None:
            if v < info.data['min_moves']:
                raise ValueError("max_moves must be greater than or equal to min_moves")
        return v
    
    @field_validator('max_duration')
    @classmethod
    def validate_max_duration(cls, v, info):
        """Validate that max_duration is greater than min_duration."""
        if v is not None and 'min_duration' in info.data and info.data['min_duration'] is not None:
            if v < info.data['min_duration']:
                raise ValueError("max_duration must be greater than or equal to min_duration")
        return v
    
    @field_validator('ongoing_only')
    @classmethod
    def validate_status_filters(cls, v, info):
        """Validate that completed_only and ongoing_only are not both True."""
        if v is True and 'completed_only' in info.data and info.data['completed_only'] is True:
            raise ValueError("completed_only and ongoing_only cannot both be True")
        return v