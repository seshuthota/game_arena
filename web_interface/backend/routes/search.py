"""
Search API routes for the Game Analysis Web Interface.

This module provides REST endpoints for searching games and players
with text-based queries and advanced filtering capabilities.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from game_arena.storage import QueryEngine

from dependencies import get_query_engine_from_app
from models import SearchResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/search/games", response_model=SearchResponse)
async def search_games(
    request: Request,
    query: str = Query(..., description="Search query"),
    limit: int = Query(50, ge=1, le=1000, description="Maximum number of results"),
    search_fields: Optional[str] = Query(None, description="Comma-separated list of fields to search (player_names, game_id, tournament_id)"),
    query_engine: QueryEngine = Depends(get_query_engine_from_app)
) -> SearchResponse:
    """
    Search games by text query.
    
    This endpoint allows searching for games using text queries that match
    against player names, game IDs, tournament IDs, and other searchable fields.
    
    Search fields supported:
    - player_names: Search in player IDs and model names
    - game_id: Search in game IDs 
    - tournament_id: Search in tournament IDs
    - all: Search in all fields (default)
    """
    try:
        # Parse search fields
        fields_to_search = None
        if search_fields:
            fields_to_search = [field.strip() for field in search_fields.split(",")]
            # Validate search fields
            valid_fields = {'player_names', 'game_id', 'tournament_id'}
            invalid_fields = set(fields_to_search) - valid_fields
            if invalid_fields:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid search fields: {', '.join(invalid_fields)}. Valid fields: {', '.join(valid_fields)}"
                )
        
        # Perform search
        matching_games = await query_engine.search_games(
            search_term=query,
            search_fields=fields_to_search
        )
        
        # Limit results
        if limit and len(matching_games) > limit:
            matching_games = matching_games[:limit]
        
        # Convert to GameSummary objects for response
        from .games import _convert_game_to_summary
        game_summaries = [_convert_game_to_summary(game) for game in matching_games]
        
        logger.info(f"Game search for '{query}' returned {len(game_summaries)} results")
        
        return SearchResponse(
            results=game_summaries,
            query=query,
            result_count=len(game_summaries),
            search_type="games"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to search games with query '{query}': {e}")
        raise HTTPException(status_code=500, detail=f"Search operation failed: {str(e)}")


@router.get("/search/players", response_model=SearchResponse)
async def search_players(
    request: Request,
    query: str = Query(..., description="Search query"),
    limit: int = Query(50, ge=1, le=1000, description="Maximum number of results"),
    query_engine: QueryEngine = Depends(get_query_engine_from_app)
) -> SearchResponse:
    """
    Search players by text query.
    
    This endpoint allows searching for players using text queries that match
    against player IDs, model names, model providers, and agent types.
    """
    try:
        # Get all games to extract unique players
        from game_arena.storage.query_engine import GameFilters
        default_filters = GameFilters()  # No filters = get all games
        all_games = await query_engine.query_games_advanced(
            default_filters,
            limit=None
        )
        
        # Extract unique players
        unique_players = {}
        search_term_lower = query.lower()
        
        for game in all_games:
            for position, player_info in game.players.items():
                player_key = (player_info.player_id, player_info.model_name)
                
                # Check if player matches search term
                if (search_term_lower in player_info.player_id.lower() or
                    search_term_lower in player_info.model_name.lower() or
                    search_term_lower in player_info.model_provider.lower() or
                    search_term_lower in player_info.agent_type.lower()):
                    
                    if player_key not in unique_players:
                        from ..models import PlayerInfo
                        unique_players[player_key] = PlayerInfo(
                            player_id=player_info.player_id,
                            model_name=player_info.model_name,
                            model_provider=player_info.model_provider,
                            agent_type=player_info.agent_type,
                            elo_rating=getattr(player_info, 'elo_rating', None)
                        )
        
        # Convert to list and apply limit
        player_results = list(unique_players.values())
        if limit and len(player_results) > limit:
            player_results = player_results[:limit]
        
        logger.info(f"Player search for '{query}' returned {len(player_results)} results")
        
        return SearchResponse(
            results=player_results,
            query=query,
            result_count=len(player_results),
            search_type="players"
        )
        
    except Exception as e:
        logger.error(f"Failed to search players with query '{query}': {e}")
        raise HTTPException(status_code=500, detail=f"Player search operation failed: {str(e)}")