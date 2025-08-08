"""
Statistics API routes for the Game Analysis Web Interface.

This module provides REST endpoints for retrieving game statistics,
analytics, and time-series data for visualization and reporting.
"""

import logging
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from game_arena.storage import QueryEngine

from dependencies import get_query_engine_from_app
from models import StatisticsOverviewResponse, TimeSeriesResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/statistics/overview", response_model=StatisticsOverviewResponse)
async def get_statistics_overview(
    request: Request,
    query_engine: QueryEngine = Depends(get_query_engine_from_app)
) -> StatisticsOverviewResponse:
    """
    Get overall game statistics and metrics.
    
    This endpoint provides aggregate statistics across all games including
    totals, averages, and breakdowns by various categories.
    """
    try:
        # Get all games to calculate statistics
        from game_arena.storage.query_engine import GameFilters
        all_games_filters = GameFilters()  # No filters = get all games
        all_games = await query_engine.query_games_advanced(all_games_filters)
        
        # Calculate basic counts
        total_games = len(all_games)
        completed_games = len([game for game in all_games if game.is_completed])
        ongoing_games = total_games - completed_games
        
        # Calculate player statistics
        unique_players = set()
        total_moves = 0
        total_duration_minutes = 0
        games_with_duration = 0
        
        games_by_result = {"white_wins": 0, "black_wins": 0, "draw": 0, "ongoing": 0}
        games_by_termination = {}
        player_game_count = {}
        
        longest_game_moves = 0
        longest_game_id = None
        shortest_game_moves = float('inf')
        shortest_game_id = None
        
        for game in all_games:
            # Track unique players
            for player_info in game.players.values():
                unique_players.add(player_info.player_id)
                player_game_count[player_info.player_id] = player_game_count.get(player_info.player_id, 0) + 1
            
            # Track moves
            total_moves += game.total_moves
            
            # Track game duration
            if game.start_time and game.end_time:
                duration_seconds = (game.end_time - game.start_time).total_seconds()
                total_duration_minutes += duration_seconds / 60.0
                games_with_duration += 1
            
            # Track results
            if game.outcome and game.outcome.result:
                result_str = game.outcome.result.value.lower()
                if result_str in games_by_result:
                    games_by_result[result_str] += 1
                
                # Track termination reasons
                if game.outcome.termination:
                    termination_str = game.outcome.termination.value.lower()
                    games_by_termination[termination_str] = games_by_termination.get(termination_str, 0) + 1
            else:
                games_by_result["ongoing"] += 1
            
            # Track longest/shortest games
            if game.total_moves > longest_game_moves:
                longest_game_moves = game.total_moves
                longest_game_id = game.game_id
            
            if game.total_moves < shortest_game_moves and game.total_moves > 0:
                shortest_game_moves = game.total_moves
                shortest_game_id = game.game_id
        
        # Calculate averages
        average_game_duration = total_duration_minutes / games_with_duration if games_with_duration > 0 else 0.0
        average_moves_per_game = total_moves / total_games if total_games > 0 else 0.0
        
        # Find most active player
        most_active_player = None
        if player_game_count:
            most_active_player = max(player_game_count, key=player_game_count.get)
        
        # Create OverallStatistics object
        from models import OverallStatistics
        statistics = OverallStatistics(
            total_games=total_games,
            completed_games=completed_games,
            ongoing_games=ongoing_games,
            total_players=len(unique_players),
            total_moves=total_moves,
            average_game_duration=round(average_game_duration, 2),
            average_moves_per_game=round(average_moves_per_game, 2),
            games_by_result=games_by_result,
            games_by_termination=games_by_termination,
            most_active_player=most_active_player,
            longest_game_id=longest_game_id,
            shortest_game_id=shortest_game_id
        )
        
        logger.info(f"Generated statistics overview: {total_games} games, {len(unique_players)} players")
        
        return StatisticsOverviewResponse(
            statistics=statistics,
            filters_applied={}  # No filters applied for overview
        )
        
    except Exception as e:
        logger.error(f"Failed to generate statistics overview: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve statistics: {str(e)}")


@router.get("/statistics/time-series", response_model=TimeSeriesResponse)
async def get_time_series_data(
    request: Request,
    metric: str = Query(..., description="Metric to retrieve (games, moves, duration, players)"),
    interval: str = Query("daily", description="Time interval (daily, weekly, monthly)"),
    start_date: Optional[datetime] = Query(None, description="Start date for time series (ISO format)"),
    end_date: Optional[datetime] = Query(None, description="End date for time series (ISO format)"),
    query_engine: QueryEngine = Depends(get_query_engine_from_app)
) -> TimeSeriesResponse:
    """
    Get time-series data for charts and trend analysis.
    
    This endpoint provides temporal data for various metrics that can be
    used to create charts and analyze trends over time.
    
    Supported metrics:
    - games: Number of games started per interval
    - moves: Total moves per interval  
    - duration: Average game duration per interval
    - players: Number of active players per interval
    
    Supported intervals:
    - daily: Data points for each day
    - weekly: Data points for each week
    - monthly: Data points for each month
    """
    try:
        # Validate parameters
        valid_metrics = {'games', 'moves', 'duration', 'players'}
        if metric not in valid_metrics:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid metric '{metric}'. Valid metrics: {', '.join(valid_metrics)}"
            )
        
        valid_intervals = {'daily', 'weekly', 'monthly'}
        if interval not in valid_intervals:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid interval '{interval}'. Valid intervals: {', '.join(valid_intervals)}"
            )
        
        # Get all games for time-series analysis
        from game_arena.storage.query_engine import GameFilters
        filters = GameFilters()
        
        # Apply date filters if provided
        if start_date:
            filters.start_time_after = start_date
        if end_date:
            filters.start_time_before = end_date
        
        all_games = await query_engine.query_games_advanced(filters)
        
        # Generate time series data
        time_series_data = _generate_time_series_data(all_games, metric, interval, start_date, end_date)
        
        logger.info(f"Generated time series for metric '{metric}' with {len(time_series_data.data_points)} data points")
        
        # Build applied filters for response
        filters_applied = {}
        if start_date:
            filters_applied["start_date"] = start_date.isoformat()
        if end_date:
            filters_applied["end_date"] = end_date.isoformat()
        filters_applied["metric"] = metric
        filters_applied["interval"] = interval
        
        return TimeSeriesResponse(
            time_series=time_series_data,
            filters_applied=filters_applied
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate time series data: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate time series data: {str(e)}")


def _generate_time_series_data(games, metric: str, interval: str, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None):
    """Generate time series data from games list."""
    from collections import defaultdict
    from datetime import timedelta
    from models import TimeSeriesData, TimeSeriesDataPoint
    
    if not games:
        return TimeSeriesData(
            metric=metric,
            interval=interval,
            data_points=[],
            total_count=0
        )
    
    # Determine date range
    if start_date is None:
        start_date = min(game.start_time for game in games if game.start_time)
    if end_date is None:
        end_date = max(game.start_time for game in games if game.start_time)
    
    # Generate time buckets based on interval
    time_buckets = _generate_time_buckets(start_date, end_date, interval)
    
    # Initialize data structure
    bucket_data = defaultdict(lambda: {"games": [], "total_moves": 0, "total_duration": 0.0, "players": set()})
    
    # Aggregate games into time buckets
    for game in games:
        if not game.start_time:
            continue
            
        bucket_key = _get_time_bucket_key(game.start_time, interval)
        if bucket_key in time_buckets:
            bucket_data[bucket_key]["games"].append(game)
            bucket_data[bucket_key]["total_moves"] += game.total_moves
            
            # Calculate duration if available
            if game.start_time and game.end_time:
                duration_minutes = (game.end_time - game.start_time).total_seconds() / 60.0
                bucket_data[bucket_key]["total_duration"] += duration_minutes
            
            # Track unique players
            for player_info in game.players.values():
                bucket_data[bucket_key]["players"].add(player_info.player_id)
    
    # Generate data points
    data_points = []
    for bucket_time in sorted(time_buckets.keys()):
        data = bucket_data[bucket_time]
        
        if metric == "games":
            value = len(data["games"])
            count = len(data["games"])
        elif metric == "moves":
            value = data["total_moves"]
            count = len(data["games"])
        elif metric == "duration":
            # Average duration per game in the bucket
            if data["games"]:
                completed_games = [g for g in data["games"] if g.is_completed and g.start_time and g.end_time]
                if completed_games:
                    total_duration = sum((g.end_time - g.start_time).total_seconds() / 60.0 for g in completed_games)
                    value = total_duration / len(completed_games)
                else:
                    value = 0.0
                count = len(completed_games)
            else:
                value = 0.0
                count = 0
        elif metric == "players":
            value = len(data["players"])
            count = len(data["players"])
        else:
            value = 0.0
            count = 0
        
        data_points.append(TimeSeriesDataPoint(
            timestamp=bucket_time,
            value=round(value, 2),
            count=count
        ))
    
    return TimeSeriesData(
        metric=metric,
        interval=interval,
        data_points=data_points,
        total_count=len(data_points)
    )


def _generate_time_buckets(start_date: datetime, end_date: datetime, interval: str):
    """Generate time buckets based on interval."""
    from datetime import timedelta
    
    buckets = {}
    current_date = start_date
    
    if interval == "daily":
        # Round to start of day
        current_date = current_date.replace(hour=0, minute=0, second=0, microsecond=0)
        while current_date <= end_date:
            buckets[current_date] = current_date
            current_date += timedelta(days=1)
    
    elif interval == "weekly":
        # Round to start of week (Monday)
        days_since_monday = current_date.weekday()
        current_date = current_date.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=days_since_monday)
        while current_date <= end_date:
            buckets[current_date] = current_date
            current_date += timedelta(weeks=1)
    
    elif interval == "monthly":
        # Round to start of month
        current_date = current_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        while current_date <= end_date:
            buckets[current_date] = current_date
            # Move to next month
            if current_date.month == 12:
                current_date = current_date.replace(year=current_date.year + 1, month=1)
            else:
                current_date = current_date.replace(month=current_date.month + 1)
    
    return buckets


def _get_time_bucket_key(timestamp: datetime, interval: str):
    """Get the appropriate time bucket key for a timestamp."""
    from datetime import timedelta
    
    if interval == "daily":
        return timestamp.replace(hour=0, minute=0, second=0, microsecond=0)
    elif interval == "weekly":
        days_since_monday = timestamp.weekday()
        return timestamp.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=days_since_monday)
    elif interval == "monthly":
        return timestamp.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        return timestamp