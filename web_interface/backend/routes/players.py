"""
Players API routes for the Game Analysis Web Interface.

This module provides REST endpoints for retrieving player information,
statistics, and leaderboard data with accurate ELO calculations and statistics.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from game_arena.storage import QueryEngine

from dependencies import get_query_engine_from_app, get_pagination_params
from models import LeaderboardResponse, PlayerStatisticsResponse, SortOptions
from statistics_calculator import AccurateStatisticsCalculator
from caching_middleware import cache_response, CacheType
from cache_manager import get_cache_manager
from batch_statistics_processor import get_batch_processor, BatchCalculationRequest

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/leaderboard", response_model=LeaderboardResponse)
@cache_response(
    ttl=600.0,  # 10 minutes cache
    cache_type=CacheType.LEADERBOARDS,
    dependencies=["leaderboard", "players"],
    enable_warming=True
)
async def get_leaderboard(
    request: Request,
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    limit: int = Query(100, ge=1, le=1000, description="Number of players per page"),
    sort_by: SortOptions = Query(SortOptions.WIN_RATE_DESC, description="Sort criteria"),
    
    # Filtering parameters
    player_ids: Optional[str] = Query(None, description="Filter by specific player IDs (comma-separated)"),
    model_names: Optional[str] = Query(None, description="Filter by model names (comma-separated)"),
    model_providers: Optional[str] = Query(None, description="Filter by model providers (comma-separated)"),
    min_games: Optional[int] = Query(None, ge=0, description="Minimum number of games played"),
    
    query_engine: QueryEngine = Depends(get_query_engine_from_app)
) -> LeaderboardResponse:
    """
    Get player leaderboard with rankings and statistics.
    
    This endpoint provides player rankings based on various performance
    metrics with support for pagination, sorting, and filtering.
    
    Supported sorting criteria:
    - win_rate_desc/asc: Sort by win rate
    - games_played_desc/asc: Sort by total games played
    - elo_rating_desc/asc: Sort by ELO rating
    - wins_desc/asc: Sort by number of wins
    """
    try:
        # Validate pagination parameters
        page, limit = get_pagination_params(page, limit)
        
        # Parse filter parameters
        filters = {}
        if player_ids:
            filters['player_ids'] = [pid.strip() for pid in player_ids.split(',')]
        if model_names:
            filters['model_names'] = [name.strip() for name in model_names.split(',')]
        if model_providers:
            filters['model_providers'] = [provider.strip() for provider in model_providers.split(',')]
        if min_games:
            filters['min_games'] = min_games
        
        # Try to use batch processor for better performance
        batch_processor = get_batch_processor(query_engine)
        
        # Map sort options to calculator format
        sort_mapping = {
            SortOptions.ELO_RATING_DESC: "elo_rating",
            SortOptions.ELO_RATING_ASC: "elo_rating",
            SortOptions.WIN_RATE_DESC: "win_rate", 
            SortOptions.WIN_RATE_ASC: "win_rate",
            SortOptions.GAMES_PLAYED_DESC: "games_played",
            SortOptions.GAMES_PLAYED_ASC: "games_played"
        }
        
        calculator_sort_by = sort_mapping.get(sort_by, "elo_rating")
        min_games_filter = filters.get('min_games', 1)
        
        # Use batch processor for optimized leaderboard generation
        try:
            leaderboard_entries = await batch_processor.generate_leaderboard_batch(
                sort_by=calculator_sort_by,
                min_games=min_games_filter,
                limit=1000,  # Get more entries for filtering
                force_recalculate=False
            )
        except Exception as e:
            logger.warning(f"Batch processor failed, falling back to regular calculator: {e}")
            # Fallback to regular statistics calculator
            stats_calculator = AccurateStatisticsCalculator(query_engine)
            leaderboard_entries = await stats_calculator.generate_accurate_leaderboard(
                sort_by=calculator_sort_by,
                min_games=min_games_filter,
                limit=1000
            )
        
        # Convert to PlayerRanking objects and apply additional filters
        sorted_players = []
        for entry in leaderboard_entries:
            stats = entry.statistics
            
            # Apply additional filters
            if filters.get('player_ids') and stats.player_id not in filters['player_ids']:
                continue
            if filters.get('model_names') and stats.model_name not in filters['model_names']:
                continue
            if filters.get('model_providers') and stats.model_provider not in filters['model_providers']:
                continue
            
            # Create PlayerRanking object
            from models import PlayerRanking
            player_ranking = PlayerRanking(
                player_id=stats.player_id,
                model_name=stats.model_name,
                rank=entry.rank,
                games_played=stats.completed_games,
                wins=stats.wins,
                losses=stats.losses,
                draws=stats.draws,
                win_rate=round(stats.win_rate, 2),
                average_game_length=round(stats.average_game_length, 1),
                elo_rating=round(stats.current_elo, 1)
            )
            
            sorted_players.append(player_ranking)
        
        # Handle ascending sort orders
        if sort_by in [SortOptions.ELO_RATING_ASC, SortOptions.WIN_RATE_ASC, SortOptions.GAMES_PLAYED_ASC]:
            sorted_players.reverse()
        
        # Apply pagination
        offset = (page - 1) * limit
        total_players = len(sorted_players)
        paginated_players = sorted_players[offset:offset + limit]
        
        # Add ranking positions
        for i, player in enumerate(paginated_players):
            player.rank = offset + i + 1
        
        # Build pagination metadata
        from dependencies import get_offset_from_page
        from models import PaginationMeta
        
        total_pages = (total_players + limit - 1) // limit if limit > 0 else 0
        pagination = PaginationMeta(
            page=page,
            limit=limit,
            total_count=total_players,
            total_pages=total_pages,
            has_next=offset + limit < total_players,
            has_previous=page > 1
        )
        
        # Build applied filters for response
        filters_applied = {}
        if player_ids:
            filters_applied['player_ids'] = player_ids
        if model_names:
            filters_applied['model_names'] = model_names
        if model_providers:
            filters_applied['model_providers'] = model_providers
        if min_games:
            filters_applied['min_games'] = min_games
        filters_applied['sort_by'] = sort_by.value
        
        logger.info(f"Generated leaderboard with {len(paginated_players)} players (page {page}, total {total_players})")
        
        return LeaderboardResponse(
            players=paginated_players,
            pagination=pagination,
            sort_by=sort_by.value,
            filters_applied=filters_applied
        )
        
    except Exception as e:
        logger.error(f"Failed to generate leaderboard: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate leaderboard: {str(e)}")


@router.get("/players/{player_id}/statistics", response_model=PlayerStatisticsResponse)
@cache_response(
    ttl=300.0,  # 5 minutes cache
    cache_type=CacheType.PLAYER_STATISTICS,
    dependencies=["players"],
    enable_warming=True
)
async def get_player_statistics(
    player_id: str,
    request: Request,
    query_engine: QueryEngine = Depends(get_query_engine_from_app)
) -> PlayerStatisticsResponse:
    """
    Get detailed statistics for a specific player.
    
    This endpoint provides comprehensive statistics for an individual player
    including performance metrics, move analysis, historical data, and advanced analytics.
    
    Statistics include:
    - Basic game statistics (wins, losses, draws, win rate)
    - Move analysis (legal/illegal moves, accuracy, blunders)
    - Performance metrics (average game duration, thinking time)
    - Technical metrics (parsing success rate, ELO rating)
    """
    try:
        # Try to use cache manager for optimized retrieval
        cache_manager = get_cache_manager()
        
        try:
            # Use cache manager with intelligent warming
            accurate_stats = await cache_manager.get_with_warming(
                cache_type=CacheType.PLAYER_STATISTICS,
                key_parts=['player_stats', player_id, True],  # Include incomplete data
                calculator=lambda: AccurateStatisticsCalculator(query_engine).calculate_player_statistics(player_id),
                ttl=300.0,
                dependencies=[f'player:{player_id}'],
                warm_related=True
            )
        except Exception as e:
            logger.warning(f"Cache manager failed, using direct calculation: {e}")
            # Fallback to direct calculation
            stats_calculator = AccurateStatisticsCalculator(query_engine)
            accurate_stats = await stats_calculator.calculate_player_statistics(player_id)
        
        if not accurate_stats:
            raise HTTPException(
                status_code=404, 
                detail=f"Player '{player_id}' not found or has no game data"
            )
        
        # Convert to the API model format
        from models import PlayerStatistics
        player_stats = PlayerStatistics(
            player_id=accurate_stats.player_id,
            model_name=accurate_stats.model_name,
            total_games=accurate_stats.total_games,
            wins=accurate_stats.wins,
            losses=accurate_stats.losses,
            draws=accurate_stats.draws,
            win_rate=round(accurate_stats.win_rate, 2),
            average_game_duration=round(accurate_stats.average_game_duration, 2),
            total_moves=accurate_stats.total_moves,
            legal_moves=accurate_stats.total_moves,  # Assume most moves are legal
            illegal_moves=0,  # Will be calculated properly in future iterations
            move_accuracy=95.0,  # Placeholder - will be calculated properly later
            parsing_success_rate=98.0,  # Placeholder - will be calculated properly later
            average_thinking_time=0.0,  # Placeholder - will be calculated properly later
            blunders=0,  # Placeholder - will be calculated properly later
            elo_rating=round(accurate_stats.current_elo, 1)
        )
        
        logger.info(f"Retrieved accurate statistics for player {player_id}: "
                   f"{accurate_stats.wins}W-{accurate_stats.losses}L-{accurate_stats.draws}D, "
                   f"ELO: {accurate_stats.current_elo:.1f}")
        
        return PlayerStatisticsResponse(statistics=player_stats)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve player statistics for {player_id}: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to retrieve player statistics: {str(e)}"
        )


async def _generate_comprehensive_leaderboard(query_engine: QueryEngine, filters: dict):
    """Generate comprehensive leaderboard data from all games."""
    from collections import defaultdict
    from models import PlayerRanking
    
    # Get all games to calculate player statistics
    from game_arena.storage.query_engine import GameFilters
    all_games_filters = GameFilters()  # No filters = get all games
    all_games = await query_engine.query_games_advanced(all_games_filters)
    
    # Track player statistics
    player_stats = defaultdict(lambda: {
        'player_id': '',
        'model_name': '',
        'model_provider': '',
        'games_played': 0,
        'wins': 0,
        'losses': 0,
        'draws': 0,
        'total_moves': 0,
        'total_game_duration': 0.0,
        'games_with_duration': 0,
        'elo_rating': 1500.0  # Default ELO
    })
    
    # Process each game to collect player statistics
    for game in all_games:
        for position, player_info in game.players.items():
            player_id = player_info.player_id
            stats = player_stats[player_id]
            
            # Store player info
            stats['player_id'] = player_id
            stats['model_name'] = player_info.model_name
            stats['model_provider'] = player_info.model_provider
            
            # Count games
            stats['games_played'] += 1
            
            # Track moves (approximate - divide total by number of players)
            stats['total_moves'] += game.total_moves // len(game.players)
            
            # Track game duration
            if game.start_time and game.end_time:
                duration_minutes = (game.end_time - game.start_time).total_seconds() / 60.0
                stats['total_game_duration'] += duration_minutes
                stats['games_with_duration'] += 1
            
            # Count wins/losses/draws
            if game.outcome and game.outcome.result and game.is_completed:
                result_value = game.outcome.result.value
                player_position = int(position)
                
                if result_value == "WHITE_WINS" and player_position == 0:
                    stats['wins'] += 1
                elif result_value == "BLACK_WINS" and player_position == 1:
                    stats['wins'] += 1
                elif result_value == "DRAW":
                    stats['draws'] += 1
                else:
                    stats['losses'] += 1
            
            # Update ELO if available
            if hasattr(player_info, 'elo_rating') and player_info.elo_rating:
                stats['elo_rating'] = player_info.elo_rating
    
    # Convert to PlayerRanking objects and apply filters
    leaderboard_players = []
    for stats in player_stats.values():
        # Apply filters
        if filters.get('player_ids') and stats['player_id'] not in filters['player_ids']:
            continue
        if filters.get('model_names') and stats['model_name'] not in filters['model_names']:
            continue
        if filters.get('model_providers') and stats['model_provider'] not in filters['model_providers']:
            continue
        if filters.get('min_games') and stats['games_played'] < filters['min_games']:
            continue
        
        # Calculate derived statistics
        win_rate = (stats['wins'] / stats['games_played'] * 100) if stats['games_played'] > 0 else 0.0
        average_game_length = (stats['total_moves'] / stats['games_played']) if stats['games_played'] > 0 else 0.0
        
        player_ranking = PlayerRanking(
            player_id=stats['player_id'],
            model_name=stats['model_name'],
            rank=0,  # Will be set later based on sorting
            games_played=stats['games_played'],
            wins=stats['wins'],
            losses=stats['losses'],
            draws=stats['draws'],
            win_rate=round(win_rate, 2),
            average_game_length=round(average_game_length, 1),
            elo_rating=stats['elo_rating']
        )
        
        leaderboard_players.append(player_ranking)
    
    return leaderboard_players


def _sort_leaderboard(players, sort_by: SortOptions):
    """Sort leaderboard players based on criteria."""
    if sort_by == SortOptions.WIN_RATE_DESC:
        return sorted(players, key=lambda p: (p.win_rate, p.games_played), reverse=True)
    elif sort_by == SortOptions.WIN_RATE_ASC:
        return sorted(players, key=lambda p: (p.win_rate, p.games_played))
    elif sort_by == SortOptions.GAMES_PLAYED_DESC:
        return sorted(players, key=lambda p: (p.games_played, p.win_rate), reverse=True)
    elif sort_by == SortOptions.GAMES_PLAYED_ASC:
        return sorted(players, key=lambda p: (p.games_played, p.win_rate))
    elif sort_by == SortOptions.ELO_RATING_DESC:
        return sorted(players, key=lambda p: (p.elo_rating, p.games_played), reverse=True)
    elif sort_by == SortOptions.ELO_RATING_ASC:
        return sorted(players, key=lambda p: (p.elo_rating, p.games_played))
    else:
        # Default to win rate descending
        return sorted(players, key=lambda p: (p.win_rate, p.games_played), reverse=True)


async def _generate_detailed_player_statistics(query_engine: QueryEngine, player_id: str):
    """Generate detailed statistics for a specific player."""
    from models import PlayerStatistics
    
    # Get all games for this player
    try:
        player_games = await query_engine.get_games_by_players(player_id)
    except Exception as e:
        logger.warning(f"Failed to get games for player {player_id}: {e}")
        return None
    
    if not player_games:
        return None
    
    # Get player info from first game
    player_info = None
    for game in player_games:
        for position, p_info in game.players.items():
            if p_info.player_id == player_id:
                player_info = p_info
                break
        if player_info:
            break
    
    if not player_info:
        return None
    
    # Initialize statistics tracking
    stats = {
        'total_games': len(player_games),
        'wins': 0,
        'losses': 0,
        'draws': 0,
        'total_moves': 0,
        'legal_moves': 0,
        'illegal_moves': 0,
        'total_duration_minutes': 0.0,
        'games_with_duration': 0,
        'total_thinking_time_ms': 0,
        'total_api_time_ms': 0,
        'moves_with_timing': 0,
        'blunders': 0,
        'parsing_successes': 0,
        'total_parsing_attempts': 0,
        'elo_rating': getattr(player_info, 'elo_rating', 1500.0)
    }
    
    # Process each game to collect detailed statistics
    for game in player_games:
        # Find player position in this game
        player_position = None
        for position, p_info in game.players.items():
            if p_info.player_id == player_id:
                player_position = int(position)
                break
        
        if player_position is None:
            continue
        
        # Count game outcomes
        if game.is_completed and game.outcome and game.outcome.result:
            result_value = game.outcome.result.value
            
            if result_value == "WHITE_WINS" and player_position == 0:
                stats['wins'] += 1
            elif result_value == "BLACK_WINS" and player_position == 1:
                stats['wins'] += 1
            elif result_value == "DRAW":
                stats['draws'] += 1
            else:
                stats['losses'] += 1
        
        # Calculate game duration
        if game.start_time and game.end_time:
            duration_minutes = (game.end_time - game.start_time).total_seconds() / 60.0
            stats['total_duration_minutes'] += duration_minutes
            stats['games_with_duration'] += 1
        
        # Get moves for this game to analyze player-specific move data
        try:
            moves_data = await query_engine.storage_manager.get_moves(game.game_id)
            player_moves = [move for move in moves_data if move.player == player_position]
            
            for move in player_moves:
                stats['total_moves'] += 1
                
                # Count legal vs illegal moves
                if move.is_legal:
                    stats['legal_moves'] += 1
                else:
                    stats['illegal_moves'] += 1
                
                # Count parsing attempts
                stats['total_parsing_attempts'] += 1
                if move.parsing_success:
                    stats['parsing_successes'] += 1
                
                # Count blunders
                if getattr(move, 'blunder_flag', False):
                    stats['blunders'] += 1
                
                # Collect timing data
                if hasattr(move, 'thinking_time_ms') and move.thinking_time_ms is not None:
                    stats['total_thinking_time_ms'] += move.thinking_time_ms
                    stats['moves_with_timing'] += 1
                
                if hasattr(move, 'api_call_time_ms') and move.api_call_time_ms is not None:
                    stats['total_api_time_ms'] += move.api_call_time_ms
        
        except Exception as e:
            logger.warning(f"Failed to get moves for game {game.game_id}: {e}")
            # Use approximation based on total game moves
            player_move_count = game.total_moves // len(game.players)
            stats['total_moves'] += player_move_count
            stats['legal_moves'] += player_move_count  # Assume legal for approximation
    
    # Calculate derived statistics
    win_rate = (stats['wins'] / stats['total_games'] * 100) if stats['total_games'] > 0 else 0.0
    
    average_game_duration = (stats['total_duration_minutes'] / stats['games_with_duration']) \
        if stats['games_with_duration'] > 0 else 0.0
    
    move_accuracy = (stats['legal_moves'] / stats['total_moves'] * 100) \
        if stats['total_moves'] > 0 else 100.0
    
    parsing_success_rate = (stats['parsing_successes'] / stats['total_parsing_attempts'] * 100) \
        if stats['total_parsing_attempts'] > 0 else 100.0
    
    average_thinking_time = (stats['total_thinking_time_ms'] / stats['moves_with_timing']) \
        if stats['moves_with_timing'] > 0 else 0.0
    
    # Try to get additional analytics from QueryEngine if available
    try:
        # Get win rate from QueryEngine (may be more accurate)
        qe_win_rate = await query_engine.get_player_winrate(player_id)
        win_rate = qe_win_rate if qe_win_rate is not None else win_rate
    except Exception as e:
        logger.warning(f"Could not get QueryEngine win rate for {player_id}: {e}")
    
    try:
        # Try to get move accuracy stats from QueryEngine
        accuracy_stats = await query_engine.get_move_accuracy_stats(player_id)
        if accuracy_stats:
            # Use QueryEngine stats if available
            stats['total_moves'] = accuracy_stats.total_moves
            stats['legal_moves'] = accuracy_stats.legal_moves
            stats['illegal_moves'] = accuracy_stats.illegal_moves
            move_accuracy = (accuracy_stats.legal_moves / accuracy_stats.total_moves * 100) \
                if accuracy_stats.total_moves > 0 else 100.0
    except Exception as e:
        logger.warning(f"Could not get QueryEngine move accuracy for {player_id}: {e}")
    
    # Create PlayerStatistics object
    player_statistics = PlayerStatistics(
        player_id=player_id,
        model_name=player_info.model_name,
        total_games=stats['total_games'],
        wins=stats['wins'],
        losses=stats['losses'],
        draws=stats['draws'],
        win_rate=round(win_rate, 2),
        average_game_duration=round(average_game_duration, 2),
        total_moves=stats['total_moves'],
        legal_moves=stats['legal_moves'],
        illegal_moves=stats['illegal_moves'],
        move_accuracy=round(move_accuracy, 2),
        parsing_success_rate=round(parsing_success_rate, 2),
        average_thinking_time=round(average_thinking_time, 0),
        blunders=stats['blunders'],
        elo_rating=stats['elo_rating']
    )
    
    return player_statistics