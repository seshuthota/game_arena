"""
Games API routes for the Game Analysis Web Interface.

This module provides REST endpoints for retrieving and filtering game data,
including game lists, detailed game information, and game-related operations.
"""

import logging
from typing import Optional, List
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from game_arena.storage import QueryEngine
from game_arena.storage.query_engine import GameFilters as StorageGameFilters
from game_arena.storage.exceptions import GameNotFoundError as StorageGameNotFoundError

from dependencies import get_query_engine_from_app, get_pagination_params, get_offset_from_page
from exceptions import GameNotFoundError, InvalidFiltersError
from models import (
    GameListResponse, GameDetailResponse, GameSummary, GameDetail,
    GameFiltersRequest, SortOptions, PaginationMeta, PlayerInfo,
    GameOutcome, MoveRecord, GameResultEnum, TerminationReasonEnum
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/games", response_model=GameListResponse)
async def get_games(
    request: Request,
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    limit: int = Query(50, ge=1, le=1000, description="Number of games per page"),
    sort_by: SortOptions = Query(SortOptions.START_TIME_DESC, description="Sort order"),
    
    # Search parameter
    search: Optional[str] = Query(None, description="Search games by text (player names, game ID, tournament ID)"),
    
    # Filter parameters
    player_id: Optional[str] = Query(None, description="Filter by player ID"),
    player_ids: Optional[str] = Query(None, description="Filter by multiple player IDs (comma-separated)"),
    model_name: Optional[str] = Query(None, description="Filter by model name"),
    model_names: Optional[str] = Query(None, description="Filter by multiple model names (comma-separated)"),
    model_provider: Optional[str] = Query(None, description="Filter by model provider"),
    model_providers: Optional[str] = Query(None, description="Filter by multiple model providers (comma-separated)"),
    tournament_id: Optional[str] = Query(None, description="Filter by tournament ID"),
    tournament_ids: Optional[str] = Query(None, description="Filter by multiple tournament IDs (comma-separated)"),
    start_date: Optional[datetime] = Query(None, description="Filter games started after this date"),
    end_date: Optional[datetime] = Query(None, description="Filter games started before this date"),
    result: Optional[GameResultEnum] = Query(None, description="Filter by game result"),
    termination: Optional[TerminationReasonEnum] = Query(None, description="Filter by termination reason"),
    min_moves: Optional[int] = Query(None, ge=0, description="Minimum number of moves"),
    max_moves: Optional[int] = Query(None, ge=0, description="Maximum number of moves"),
    completed_only: bool = Query(True, description="Only include completed games"),
    
    query_engine: QueryEngine = Depends(get_query_engine_from_app)
) -> GameListResponse:
    """
    Get a paginated list of games with optional filtering and sorting.
    
    This endpoint provides the main game browsing functionality with support for
    various filters, pagination, and sorting options.
    """
    try:
        # Validate pagination parameters
        page, limit = get_pagination_params(page, limit)
        offset = get_offset_from_page(page, limit)
        
        # Build filters
        filters = _build_game_filters(
            player_id=player_id,
            player_ids=player_ids,
            model_name=model_name,
            model_names=model_names,
            model_provider=model_provider,
            model_providers=model_providers,
            tournament_id=tournament_id,
            tournament_ids=tournament_ids,
            start_date=start_date,
            end_date=end_date,
            result=result,
            termination=termination,
            min_moves=min_moves,
            max_moves=max_moves,
            completed_only=completed_only
        )
        
        # If search query is provided, first get matching games then apply filters
        if search:
            # Use search to get initial set of games
            search_games = await query_engine.search_games(search)
            
            # Apply filters to search results
            filtered_games = []
            for game in search_games:
                if _game_matches_filters(game, filters):
                    filtered_games.append(game)
            
            # Apply pagination to filtered results
            total_count = len(filtered_games)
            games_data = filtered_games[offset:offset + limit]
        else:
            # Get games and total count using filters only
            games_data = await query_engine.query_games_advanced(filters, limit=limit, offset=offset)
            total_count = await query_engine.count_games_advanced(filters)
        
        # Convert to API models
        games = [_convert_game_to_summary(game) for game in games_data]
        
        # Apply sorting (if not handled by query engine)
        games = _sort_games(games, sort_by)
        
        # Build pagination metadata
        total_pages = (total_count + limit - 1) // limit if limit > 0 else 0
        pagination = PaginationMeta(
            page=page,
            limit=limit,
            total_count=total_count,
            total_pages=total_pages,
            has_next=offset + limit < total_count,
            has_previous=page > 1
        )
        
        # Build applied filters for response
        filters_applied = _build_filters_dict(
            search=search,
            player_id=player_id,
            player_ids=player_ids,
            model_name=model_name,
            model_names=model_names,
            model_provider=model_provider,
            model_providers=model_providers,
            tournament_id=tournament_id,
            tournament_ids=tournament_ids,
            start_date=start_date,
            end_date=end_date,
            result=result,
            termination=termination,
            min_moves=min_moves,
            max_moves=max_moves,
            completed_only=completed_only
        )
        
        logger.info(f"Retrieved {len(games)} games (page {page}, total {total_count})")
        
        return GameListResponse(
            games=games,
            pagination=pagination,
            filters_applied=filters_applied
        )
        
    except Exception as e:
        logger.error(f"Failed to retrieve games: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve games: {str(e)}")


@router.get("/games/{game_id}", response_model=GameDetailResponse)
async def get_game_detail(
    game_id: str,
    request: Request,
    query_engine: QueryEngine = Depends(get_query_engine_from_app)
) -> GameDetailResponse:
    """
    Get detailed information about a specific game including all moves.
    
    This endpoint provides comprehensive game data including metadata,
    player information, outcome, and the complete move sequence.
    """
    try:
        # Get game record
        storage_manager = query_engine.storage_manager
        
        try:
            game_record = await storage_manager.get_game(game_id)
        except StorageGameNotFoundError:
            raise GameNotFoundError(game_id)
        
        # Get moves for the game
        moves_data = await storage_manager.get_moves(game_id)
        
        # Convert to API model
        game_detail = _convert_game_to_detail(game_record, moves_data)
        
        logger.info(f"Retrieved detailed information for game {game_id}")
        
        return GameDetailResponse(game=game_detail)
        
    except GameNotFoundError:
        raise HTTPException(status_code=404, detail=f"Game {game_id} not found")
    except Exception as e:
        logger.error(f"Failed to retrieve game {game_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve game details: {str(e)}")


def _build_game_filters(**kwargs) -> StorageGameFilters:
    """Build StorageGameFilters from API parameters."""
    filters = StorageGameFilters()
    
    # Handle single and multiple player IDs
    player_ids = []
    if kwargs.get('player_id'):
        player_ids.append(kwargs['player_id'])
    if kwargs.get('player_ids'):
        player_ids.extend([pid.strip() for pid in kwargs['player_ids'].split(',')])
    if player_ids:
        filters.player_ids = player_ids
    
    # Handle single and multiple model names
    model_names = []
    if kwargs.get('model_name'):
        model_names.append(kwargs['model_name'])
    if kwargs.get('model_names'):
        model_names.extend([name.strip() for name in kwargs['model_names'].split(',')])
    if model_names:
        filters.model_names = model_names
    
    # Handle single and multiple model providers
    model_providers = []
    if kwargs.get('model_provider'):
        model_providers.append(kwargs['model_provider'])
    if kwargs.get('model_providers'):
        model_providers.extend([provider.strip() for provider in kwargs['model_providers'].split(',')])
    if model_providers:
        filters.model_providers = model_providers
    
    # Handle single and multiple tournament IDs
    tournament_ids = []
    if kwargs.get('tournament_id'):
        tournament_ids.append(kwargs['tournament_id'])
    if kwargs.get('tournament_ids'):
        tournament_ids.extend([tid.strip() for tid in kwargs['tournament_ids'].split(',')])
    if tournament_ids:
        filters.tournament_ids = tournament_ids
    
    if kwargs.get('start_date'):
        filters.start_time_after = kwargs['start_date']
    
    if kwargs.get('end_date'):
        filters.start_time_before = kwargs['end_date']
    
    if kwargs.get('min_moves'):
        filters.min_moves = kwargs['min_moves']
    
    if kwargs.get('max_moves'):
        filters.max_moves = kwargs['max_moves']
    
    filters.completed_only = kwargs.get('completed_only', True)
    
    return filters


def _build_filters_dict(**kwargs) -> dict:
    """Build filters dictionary for response."""
    filters = {}
    
    for key, value in kwargs.items():
        if value is not None:
            if isinstance(value, datetime):
                filters[key] = value.isoformat()
            else:
                filters[key] = value
    
    return filters


def _convert_game_to_summary(game_record) -> GameSummary:
    """Convert storage GameRecord to API GameSummary."""
    # Convert players
    players = {}
    for position, player_info in game_record.players.items():
        players[str(position)] = PlayerInfo(
            player_id=player_info.player_id,
            model_name=player_info.model_name,
            model_provider=player_info.model_provider,
            agent_type=player_info.agent_type,
            elo_rating=getattr(player_info, 'elo_rating', None)
        )
    
    # Convert outcome
    outcome = None
    if game_record.outcome:
        # Map chess notation results to API enums
        result_str = game_record.outcome.result.value if hasattr(game_record.outcome.result, 'value') else str(game_record.outcome.result)
        result_mapping = {
            '1-0': GameResultEnum.WHITE_WINS,
            '0-1': GameResultEnum.BLACK_WINS,
            '1/2-1/2': GameResultEnum.DRAW,
            # Also support enum value names for backward compatibility
            'WHITE_WINS': GameResultEnum.WHITE_WINS,
            'BLACK_WINS': GameResultEnum.BLACK_WINS,
            'DRAW': GameResultEnum.DRAW
        }
        
        termination_str = game_record.outcome.termination.value if hasattr(game_record.outcome.termination, 'value') else str(game_record.outcome.termination)
        termination_mapping = {
            # Handle both lowercase database values and uppercase enum values
            'checkmate': TerminationReasonEnum.CHECKMATE,
            'stalemate': TerminationReasonEnum.STALEMATE,
            'insufficient_material': TerminationReasonEnum.INSUFFICIENT_MATERIAL,
            'threefold_repetition': TerminationReasonEnum.THREEFOLD_REPETITION,
            'fifty_move_rule': TerminationReasonEnum.FIFTY_MOVE_RULE,
            'time_forfeit': TerminationReasonEnum.TIME_FORFEIT,
            'resignation': TerminationReasonEnum.RESIGNATION,
            'agreement': TerminationReasonEnum.AGREEMENT,
            'abandoned': TerminationReasonEnum.ABANDONED,
            # Uppercase versions for enum compatibility
            'CHECKMATE': TerminationReasonEnum.CHECKMATE,
            'STALEMATE': TerminationReasonEnum.STALEMATE,
            'INSUFFICIENT_MATERIAL': TerminationReasonEnum.INSUFFICIENT_MATERIAL,
            'THREEFOLD_REPETITION': TerminationReasonEnum.THREEFOLD_REPETITION,
            'FIFTY_MOVE_RULE': TerminationReasonEnum.FIFTY_MOVE_RULE,
            'TIME_FORFEIT': TerminationReasonEnum.TIME_FORFEIT,
            'RESIGNATION': TerminationReasonEnum.RESIGNATION,
            'AGREEMENT': TerminationReasonEnum.AGREEMENT,
            'ABANDONED': TerminationReasonEnum.ABANDONED
        }
        
        # Fix winner mapping to match chess notation
        winner = game_record.outcome.winner
        if result_str == '1-0':  # White wins
            winner = 0
        elif result_str == '0-1':  # Black wins  
            winner = 1
        elif result_str == '1/2-1/2':  # Draw
            winner = None
        
        outcome = GameOutcome(
            result=result_mapping.get(result_str, GameResultEnum.ONGOING),
            winner=winner,
            termination=termination_mapping.get(
                termination_str, 
                TerminationReasonEnum.ABANDONED
            ),
            termination_details=getattr(game_record.outcome, 'termination_details', None)
        )
    
    # Calculate duration
    duration_minutes = None
    if game_record.end_time and game_record.start_time:
        duration_seconds = (game_record.end_time - game_record.start_time).total_seconds()
        duration_minutes = duration_seconds / 60.0
    
    return GameSummary(
        game_id=game_record.game_id,
        tournament_id=game_record.tournament_id,
        start_time=game_record.start_time,
        end_time=game_record.end_time,
        players=players,
        outcome=outcome,
        total_moves=game_record.total_moves,
        duration_minutes=duration_minutes,
        is_completed=game_record.is_completed
    )


def _convert_game_to_detail(game_record, moves_data) -> GameDetail:
    """Convert storage GameRecord and moves to API GameDetail."""
    # Start with summary conversion
    summary = _convert_game_to_summary(game_record)
    
    # Convert moves
    moves = []
    for move_record in moves_data:
        move = MoveRecord(
            move_number=move_record.move_number,
            player=move_record.player,
            move_notation=getattr(move_record, 'move_san', move_record.move_uci),
            fen_before=move_record.fen_before,
            fen_after=move_record.fen_after,
            is_legal=move_record.is_legal,
            parsing_success=move_record.parsing_success,
            thinking_time_ms=move_record.thinking_time_ms,
            api_call_time_ms=move_record.api_call_time_ms,
            total_time_ms=move_record.total_time_ms,
            had_rethink=move_record.had_rethink,
            rethink_attempts=len(move_record.rethink_attempts),
            blunder_flag=move_record.blunder_flag,
            move_quality_score=getattr(move_record, 'move_quality_score', None),
            llm_response=getattr(move_record, 'raw_response', None)
        )
        moves.append(move)
    
    return GameDetail(
        game_id=summary.game_id,
        tournament_id=summary.tournament_id,
        start_time=summary.start_time,
        end_time=summary.end_time,
        players=summary.players,
        outcome=summary.outcome,
        total_moves=summary.total_moves,
        duration_minutes=summary.duration_minutes,
        is_completed=summary.is_completed,
        initial_fen=getattr(game_record, 'initial_fen', 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'),
        final_fen=getattr(game_record, 'final_fen', None),
        moves=moves
    )


def _sort_games(games: List[GameSummary], sort_by: SortOptions) -> List[GameSummary]:
    """Sort games based on the specified criteria."""
    if sort_by == SortOptions.START_TIME_ASC:
        return sorted(games, key=lambda g: g.start_time)
    elif sort_by == SortOptions.START_TIME_DESC:
        return sorted(games, key=lambda g: g.start_time, reverse=True)
    elif sort_by == SortOptions.DURATION_ASC:
        return sorted(games, key=lambda g: g.duration_minutes or 0)
    elif sort_by == SortOptions.DURATION_DESC:
        return sorted(games, key=lambda g: g.duration_minutes or 0, reverse=True)
    elif sort_by == SortOptions.MOVES_ASC:
        return sorted(games, key=lambda g: g.total_moves)
    elif sort_by == SortOptions.MOVES_DESC:
        return sorted(games, key=lambda g: g.total_moves, reverse=True)
    else:
        # Default to start time descending
        return sorted(games, key=lambda g: g.start_time, reverse=True)


def _game_matches_filters(game_record, filters: StorageGameFilters) -> bool:
    """Check if a game record matches the given filters."""
    # Player filters
    if filters.player_ids:
        game_player_ids = [player.player_id for player in game_record.players.values()]
        if not any(pid in game_player_ids for pid in filters.player_ids):
            return False
    
    if filters.model_names:
        game_model_names = [player.model_name for player in game_record.players.values()]
        if not any(name in game_model_names for name in filters.model_names):
            return False
    
    if filters.model_providers:
        game_providers = [player.model_provider for player in game_record.players.values()]
        if not any(provider in game_providers for provider in filters.model_providers):
            return False
    
    # Tournament filters
    if filters.tournament_ids:
        if game_record.tournament_id not in filters.tournament_ids:
            return False
    
    # Time filters
    if filters.start_time_after and game_record.start_time < filters.start_time_after:
        return False
    
    if filters.start_time_before and game_record.start_time > filters.start_time_before:
        return False
    
    # Move count filters
    if filters.min_moves and game_record.total_moves < filters.min_moves:
        return False
    
    if filters.max_moves and game_record.total_moves > filters.max_moves:
        return False
    
    # Completion status
    if filters.completed_only and not game_record.is_completed:
        return False
    
    if filters.ongoing_only and game_record.is_completed:
        return False
    
    return True