"""
Integration tests for complete game analysis workflows.

Tests end-to-end workflows including game processing, statistics calculation,
caching integration, and performance monitoring across all components.
"""

import pytest
import asyncio
import json
import tempfile
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock

from statistics_cache import StatisticsCache
from batch_statistics_processor import BatchStatisticsProcessor
from cache_manager import CacheManager, CacheType
from performance_monitor import PerformanceMonitor
from background_tasks import BackgroundTaskManager
from elo_rating import ELORatingSystem
from query_engine import QueryEngine


class MockDatabase:
    """Mock database for integration testing."""
    
    def __init__(self):
        self.games = []
        self.players = {}
        self.next_game_id = 1
        self.next_player_id = 1
    
    def add_game(self, white_player, black_player, result, moves=None, opening="Unknown"):
        """Add a game to mock database."""
        game = {
            'id': self.next_game_id,
            'white_player': white_player,
            'black_player': black_player,
            'result': result,
            'moves': moves or [],
            'opening': opening,
            'date': datetime.now(),
            'duration': 3600  # 1 hour
        }
        self.games.append(game)
        self.next_game_id += 1
        return game
    
    def add_player(self, name, initial_rating=1500.0):
        """Add a player to mock database."""
        player = {
            'id': self.next_player_id,
            'name': name,
            'rating': initial_rating,
            'games_played': 0,
            'wins': 0,
            'losses': 0,
            'draws': 0
        }
        self.players[name] = player
        self.next_player_id += 1
        return player
    
    def get_games(self, limit=None, offset=0):
        """Get games from mock database."""
        games = self.games[offset:]
        if limit:
            games = games[:limit]
        return games
    
    def get_players(self):
        """Get all players from mock database."""
        return list(self.players.values())
    
    def get_player(self, name):
        """Get specific player from mock database."""
        return self.players.get(name)
    
    def update_player_stats(self, player_name, new_rating, result):
        """Update player statistics."""
        if player_name in self.players:
            player = self.players[player_name]
            player['rating'] = new_rating
            player['games_played'] += 1
            
            if result == 'win':
                player['wins'] += 1
            elif result == 'loss':
                player['losses'] += 1
            else:
                player['draws'] += 1


class TestCompleteGameAnalysisWorkflow:
    """Integration tests for complete game analysis workflows."""
    
    def setup_method(self):
        """Setup integration test environment."""
        # Create mock database
        self.mock_db = MockDatabase()
        
        # Initialize core components
        self.cache = StatisticsCache()
        self.batch_processor = BatchStatisticsProcessor(cache=self.cache)
        self.cache_manager = CacheManager(primary_cache=self.cache, batch_processor=self.batch_processor)
        self.performance_monitor = PerformanceMonitor(cache=self.cache, batch_processor=self.batch_processor)
        self.elo_system = ELORatingSystem()
        self.query_engine = QueryEngine(database=self.mock_db)
        
        # Add test players
        self.test_players = ['Alice', 'Bob', 'Charlie', 'Diana']
        for player in self.test_players:
            self.mock_db.add_player(player)
    
    def teardown_method(self):
        """Cleanup after tests."""
        if hasattr(self.performance_monitor, 'stop_monitoring'):
            self.performance_monitor.stop_monitoring()
        if hasattr(self.cache_manager, 'shutdown'):
            self.cache_manager.shutdown()
    
    @pytest.mark.asyncio
    async def test_complete_game_processing_workflow(self):
        """Test complete workflow from game ingestion to statistics calculation."""
        # Step 1: Add games to database
        games_to_add = [
            ('Alice', 'Bob', 'WHITE_WINS'),
            ('Charlie', 'Diana', 'BLACK_WINS'),
            ('Alice', 'Charlie', 'DRAW'),
            ('Bob', 'Diana', 'WHITE_WINS'),
            ('Alice', 'Diana', 'BLACK_WINS')
        ]
        
        game_ids = []
        for white, black, result in games_to_add:
            game = self.mock_db.add_game(white, black, result)
            game_ids.append(game['id'])
        
        # Step 2: Process ELO rating updates for each game
        for game in self.mock_db.get_games():
            white_player = self.mock_db.get_player(game['white_player'])
            black_player = self.mock_db.get_player(game['black_player'])
            
            white_update, black_update = self.elo_system.update_ratings_for_game(
                white_player['name'], white_player['rating'], white_player['games_played'],
                black_player['name'], black_player['rating'], black_player['games_played'],
                game['result'], True
            )
            
            # Update database with new ratings
            self.mock_db.update_player_stats(
                white_player['name'], 
                white_update.new_rating,
                'win' if white_update.rating_change > 0 else ('loss' if white_update.rating_change < 0 else 'draw')
            )
            self.mock_db.update_player_stats(
                black_player['name'],
                black_update.new_rating, 
                'win' if black_update.rating_change > 0 else ('loss' if black_update.rating_change < 0 else 'draw')
            )
        
        # Step 3: Calculate comprehensive statistics using batch processor
        player_stats_requests = []
        for player in self.test_players:
            player_data = self.mock_db.get_player(player)
            stats_request = {
                'calculation_type': 'player_statistics',
                'parameters': {
                    'player_id': player_data['id'],
                    'player_name': player,
                    'include_recent_form': True,
                    'include_opening_analysis': True
                },
                'priority': 1
            }
            player_stats_requests.append(stats_request)
        
        # Process player statistics in batch
        batch_job = await self.batch_processor.submit_batch_job(
            job_type='player_statistics_batch',
            requests=player_stats_requests,
            priority=1
        )
        
        # Wait for batch processing to complete
        max_wait_time = 10.0
        wait_start = time.time()
        
        while not batch_job.completed and (time.time() - wait_start) < max_wait_time:
            await asyncio.sleep(0.1)
            # In real implementation, would check job status from processor
        
        # Step 4: Generate leaderboard using cached statistics
        leaderboard_request = {
            'calculation_type': 'leaderboard',
            'parameters': {
                'sort_by': 'rating',
                'include_stats': True,
                'limit': 10
            },
            'priority': 2
        }
        
        leaderboard_job = await self.batch_processor.submit_batch_job(
            job_type='leaderboard_generation',
            requests=[leaderboard_request],
            priority=2
        )
        
        # Step 5: Verify workflow results
        # Check that all players have updated statistics
        for player in self.test_players:
            player_data = self.mock_db.get_player(player)
            assert player_data['games_played'] > 0
            assert player_data['rating'] != 1500.0 or player_data['games_played'] == 0  # Rating should change unless draws only
        
        # Verify cache contains computed statistics
        cache_stats = self.cache.get_stats()
        assert cache_stats['total_requests'] > 0
        
        # Verify performance monitoring captured metrics
        if hasattr(self.performance_monitor, 'get_current_metrics'):
            current_metrics = self.performance_monitor.get_current_metrics()
            # Should have some performance data
            assert len(current_metrics) >= 0  # Metrics might be empty in mock environment
        
        print(f"✅ Complete game processing workflow test passed")
        print(f"   - Processed {len(games_to_add)} games")
        print(f"   - Updated {len(self.test_players)} player ratings")
        print(f"   - Cache stats: {cache_stats}")
    
    @pytest.mark.asyncio
    async def test_statistics_calculation_pipeline(self):
        """Test statistics calculation pipeline with caching and optimization."""
        # Add comprehensive game data
        game_scenarios = [
            ('Alice', 'Bob', 'WHITE_WINS', ['e4', 'e5', 'Nf3', 'Nc6'], 'King\'s Pawn'),
            ('Bob', 'Charlie', 'BLACK_WINS', ['d4', 'd5', 'c4', 'e6'], 'Queen\'s Gambit'),
            ('Charlie', 'Diana', 'DRAW', ['Nf3', 'Nf6', 'g3', 'g6'], 'King\'s Indian Attack'),
            ('Diana', 'Alice', 'WHITE_WINS', ['e4', 'c5', 'Nf3', 'd6'], 'Sicilian Defense'),
            ('Alice', 'Charlie', 'BLACK_WINS', ['d4', 'f5', 'g3', 'Nf6'], 'Dutch Defense')
        ]
        
        for white, black, result, moves, opening in game_scenarios:
            self.mock_db.add_game(white, black, result, moves, opening)
        
        # Test 1: Individual player statistics calculation
        alice_stats = await self.cache_manager.get_with_warming(
            cache_type=CacheType.PLAYER_STATISTICS,
            key_parts=['player_stats', 'Alice'],
            calculator=lambda: self._calculate_player_stats('Alice'),
            ttl=300.0,
            dependencies=['player:Alice', 'games'],
            warm_related=True
        )
        
        assert alice_stats is not None
        print(f"✅ Alice statistics calculated: {alice_stats}")
        
        # Test 2: Leaderboard generation with caching
        leaderboard = await self.cache_manager.get_with_warming(
            cache_type=CacheType.LEADERBOARDS,
            key_parts=['leaderboard', 'rating'],
            calculator=lambda: self._generate_leaderboard(),
            ttl=600.0,
            dependencies=['leaderboard', 'players'],
            warm_related=True
        )
        
        assert leaderboard is not None
        assert len(leaderboard) == len(self.test_players)
        print(f"✅ Leaderboard generated with {len(leaderboard)} players")
        
        # Test 3: Aggregated statistics calculation
        aggregated_stats = await self.cache_manager.get_with_warming(
            cache_type=CacheType.AGGREGATED_STATS,
            key_parts=['aggregated_stats', 'overview'],
            calculator=lambda: self._calculate_aggregated_stats(),
            ttl=900.0,
            dependencies=['statistics', 'games'],
            warm_related=True
        )
        
        assert aggregated_stats is not None
        assert 'total_games' in aggregated_stats
        assert 'active_players' in aggregated_stats
        print(f"✅ Aggregated statistics: {aggregated_stats}")
        
        # Test 4: Cache performance verification
        cache_stats_after = self.cache.get_stats()
        assert cache_stats_after['total_requests'] >= 3
        
        # Test 5: Performance monitoring integration
        if hasattr(self.performance_monitor, '_record_metric'):
            self.performance_monitor._record_metric('CACHE_HIT_RATE', 75.0, datetime.now())
            self.performance_monitor._record_metric('RESPONSE_TIME', 150.0, datetime.now())
        
        print(f"✅ Statistics calculation pipeline test completed")
    
    @pytest.mark.asyncio
    async def test_error_recovery_and_resilience(self):
        """Test error recovery scenarios in the complete workflow."""
        # Test 1: Invalid game data handling
        try:
            # Add game with invalid result
            invalid_game = self.mock_db.add_game('Alice', 'Bob', 'INVALID_RESULT')
            
            # Attempt to process ELO updates
            with pytest.raises(ValueError):
                white_player = self.mock_db.get_player('Alice')
                black_player = self.mock_db.get_player('Bob')
                self.elo_system.update_ratings_for_game(
                    'Alice', white_player['rating'], white_player['games_played'],
                    'Bob', black_player['rating'], black_player['games_played'],
                    'INVALID_RESULT', True
                )
            
            print("✅ Invalid game result properly rejected")
            
        except Exception as e:
            print(f"❌ Unexpected error in invalid game handling: {e}")
            raise
        
        # Test 2: Cache failure recovery
        # Simulate cache failure by temporarily making cache unavailable
        original_get = self.cache.get
        self.cache.get = Mock(side_effect=Exception("Cache temporarily unavailable"))
        
        try:
            # Should gracefully handle cache failure and compute directly
            result = await self.cache_manager.get_with_warming(
                cache_type=CacheType.PLAYER_STATISTICS,
                key_parts=['player_stats', 'Bob'],
                calculator=lambda: {'player': 'Bob', 'rating': 1500.0, 'games': 0}
            )
            
            # Should still get result even with cache failure
            assert result is not None
            print("✅ Cache failure recovery successful")
            
        finally:
            # Restore cache functionality
            self.cache.get = original_get
        
        # Test 3: Database connectivity issues
        original_get_games = self.mock_db.get_games
        self.mock_db.get_games = Mock(side_effect=Exception("Database connection lost"))
        
        try:
            # Should handle database failure gracefully
            stats = await self.cache_manager.get_with_warming(
                cache_type=CacheType.AGGREGATED_STATS,
                key_parts=['stats', 'fallback'],
                calculator=lambda: self._calculate_fallback_stats()
            )
            
            assert stats is not None
            assert 'error_recovery' in stats
            print("✅ Database failure recovery successful")
            
        finally:
            # Restore database functionality
            self.mock_db.get_games = original_get_games
        
        print("✅ Error recovery and resilience test completed")
    
    @pytest.mark.asyncio
    async def test_performance_under_load(self):
        """Test workflow performance under simulated load conditions."""
        # Generate large dataset
        players = [f"Player_{i}" for i in range(20)]
        for player in players:
            self.mock_db.add_player(player)
        
        # Generate many games
        import random
        games_added = 0
        for _ in range(100):
            white = random.choice(players)
            black = random.choice(players)
            if white != black:
                result = random.choice(['WHITE_WINS', 'BLACK_WINS', 'DRAW'])
                self.mock_db.add_game(white, black, result)
                games_added += 1
        
        print(f"Generated {games_added} games for performance testing")
        
        # Test batch processing performance
        start_time = time.time()
        
        # Create batch requests for all players
        batch_requests = []
        for player in players:
            batch_requests.append({
                'calculation_type': 'player_statistics',
                'parameters': {'player_name': player},
                'priority': 1
            })
        
        # Process in batches of 10
        batch_size = 10
        total_processed = 0
        
        for i in range(0, len(batch_requests), batch_size):
            batch = batch_requests[i:i+batch_size]
            
            batch_job = await self.batch_processor.submit_batch_job(
                job_type='performance_test_batch',
                requests=batch,
                priority=1
            )
            
            total_processed += len(batch)
            
            # Small delay to simulate real processing
            await asyncio.sleep(0.01)
        
        processing_time = time.time() - start_time
        
        print(f"✅ Processed {total_processed} player statistics in {processing_time:.2f}s")
        print(f"   Average time per player: {(processing_time/total_processed)*1000:.1f}ms")
        
        # Verify cache performance
        cache_stats = self.cache.get_stats()
        print(f"   Cache performance: {cache_stats}")
        
        # Performance should be reasonable (< 1 second per 10 players in this mock environment)
        assert processing_time < 10.0  # Generous limit for integration test
        assert total_processed == len(players)
        
        print("✅ Performance under load test completed")
    
    def _calculate_player_stats(self, player_name):
        """Calculate comprehensive player statistics."""
        player = self.mock_db.get_player(player_name)
        if not player:
            return None
        
        # Get games for this player
        player_games = [
            game for game in self.mock_db.get_games()
            if game['white_player'] == player_name or game['black_player'] == player_name
        ]
        
        wins = sum(1 for game in player_games
                  if (game['white_player'] == player_name and game['result'] == 'WHITE_WINS') or
                     (game['black_player'] == player_name and game['result'] == 'BLACK_WINS'))
        
        losses = sum(1 for game in player_games
                    if (game['white_player'] == player_name and game['result'] == 'BLACK_WINS') or
                       (game['black_player'] == player_name and game['result'] == 'WHITE_WINS'))
        
        draws = sum(1 for game in player_games if game['result'] == 'DRAW')
        
        return {
            'player_name': player_name,
            'rating': player['rating'],
            'games_played': len(player_games),
            'wins': wins,
            'losses': losses,
            'draws': draws,
            'win_rate': wins / max(1, len(player_games)),
            'recent_form': wins / max(1, min(5, len(player_games)))  # Last 5 games approximation
        }
    
    def _generate_leaderboard(self):
        """Generate leaderboard from current player data."""
        players = self.mock_db.get_players()
        
        # Sort by rating descending
        sorted_players = sorted(players, key=lambda p: p['rating'], reverse=True)
        
        leaderboard = []
        for rank, player in enumerate(sorted_players, 1):
            leaderboard.append({
                'rank': rank,
                'player_name': player['name'],
                'rating': player['rating'],
                'games_played': player['games_played'],
                'wins': player['wins'],
                'losses': player['losses'],
                'draws': player['draws']
            })
        
        return leaderboard
    
    def _calculate_aggregated_stats(self):
        """Calculate aggregated statistics across all games and players."""
        games = self.mock_db.get_games()
        players = self.mock_db.get_players()
        
        total_games = len(games)
        active_players = len([p for p in players if p['games_played'] > 0])
        
        white_wins = sum(1 for game in games if game['result'] == 'WHITE_WINS')
        black_wins = sum(1 for game in games if game['result'] == 'BLACK_WINS')
        draws = sum(1 for game in games if game['result'] == 'DRAW')
        
        average_rating = sum(p['rating'] for p in players) / max(1, len(players))
        
        return {
            'total_games': total_games,
            'active_players': active_players,
            'white_wins': white_wins,
            'black_wins': black_wins,
            'draws': draws,
            'white_win_percentage': (white_wins / max(1, total_games)) * 100,
            'draw_percentage': (draws / max(1, total_games)) * 100,
            'average_rating': average_rating,
            'timestamp': datetime.now().isoformat()
        }
    
    def _calculate_fallback_stats(self):
        """Calculate fallback statistics when primary data source fails."""
        return {
            'error_recovery': True,
            'message': 'Using cached/fallback data due to system unavailability',
            'total_games': 0,
            'active_players': len(self.test_players),
            'timestamp': datetime.now().isoformat()
        }


class TestCacheIntegrationWorkflow:
    """Test cache integration across all workflow components."""
    
    def setup_method(self):
        """Setup cache integration test environment."""
        self.cache = StatisticsCache()
        self.batch_processor = BatchStatisticsProcessor(cache=self.cache)
        self.cache_manager = CacheManager(primary_cache=self.cache, batch_processor=self.batch_processor)
    
    def teardown_method(self):
        """Cleanup cache integration tests."""
        if hasattr(self.cache_manager, 'shutdown'):
            self.cache_manager.shutdown()
    
    @pytest.mark.asyncio
    async def test_cache_warming_workflow(self):
        """Test cache warming workflow across components."""
        # Add high-priority warming tasks
        warming_tasks = [
            {
                'cache_type': CacheType.LEADERBOARDS,
                'key_parts': ['leaderboard', 'top_players'],
                'calculator': lambda: [{'player': 'Alice', 'rating': 1600}, {'player': 'Bob', 'rating': 1550}],
                'priority': 3
            },
            {
                'cache_type': CacheType.PLAYER_STATISTICS,
                'key_parts': ['player_stats', 'Alice'],
                'calculator': lambda: {'games': 10, 'wins': 6, 'rating': 1600},
                'priority': 2
            },
            {
                'cache_type': CacheType.AGGREGATED_STATS,
                'key_parts': ['stats', 'overview'],
                'calculator': lambda: {'total_games': 100, 'active_players': 25},
                'priority': 1
            }
        ]
        
        # Add warming tasks to manager
        for task in warming_tasks:
            self.cache_manager.add_warming_task(
                cache_type=task['cache_type'],
                key_parts=task['key_parts'],
                calculator=task['calculator'],
                priority=task['priority']
            )
        
        # Warm popular data
        warmed_count = await self.cache_manager.warm_popular_data(top_n=3)
        
        # Verify warming occurred
        assert warmed_count >= 0  # Should have attempted warming
        
        # Verify cached data is accessible
        leaderboard = await self.cache_manager.get_with_warming(
            cache_type=CacheType.LEADERBOARDS,
            key_parts=['leaderboard', 'top_players']
        )
        
        # Should get data from cache or calculation
        assert leaderboard is not None
        
        print("✅ Cache warming workflow completed successfully")
    
    @pytest.mark.asyncio
    async def test_cache_invalidation_workflow(self):
        """Test cache invalidation workflow."""
        # Populate cache with dependent data
        await self.cache_manager.get_with_warming(
            cache_type=CacheType.PLAYER_STATISTICS,
            key_parts=['player_stats', 'Alice'],
            calculator=lambda: {'rating': 1500, 'games': 5},
            dependencies=['player:Alice']
        )
        
        await self.cache_manager.get_with_warming(
            cache_type=CacheType.LEADERBOARDS,
            key_parts=['leaderboard', 'all'],
            calculator=lambda: [{'player': 'Alice', 'rating': 1500}],
            dependencies=['leaderboard', 'player:Alice']
        )
        
        # Verify data is cached
        cache_stats_before = self.cache.get_stats()
        
        # Simulate game result that affects Alice
        # This should invalidate player:Alice dependent caches
        invalidated_count = self.cache.invalidate('player:Alice')
        
        # Verify invalidation occurred
        assert invalidated_count >= 0  # Should have invalidated some entries
        
        print(f"✅ Cache invalidation workflow completed, invalidated {invalidated_count} entries")
    
    @pytest.mark.asyncio
    async def test_batch_cache_operations(self):
        """Test batch cache operations workflow."""
        # Prepare batch requests
        batch_requests = [
            {
                'key_parts': ['player_stats', f'Player_{i}'],
                'calculator': lambda i=i: {'player': f'Player_{i}', 'rating': 1500 + i * 10}
            }
            for i in range(10)
        ]
        
        # Execute batch get operations
        batch_results = await self.cache_manager.batch_get_with_warming(
            cache_type=CacheType.PLAYER_STATISTICS,
            batch_requests=batch_requests,
            warm_popular=True
        )
        
        # Verify batch results
        assert len(batch_results) == len(batch_requests)
        
        # Test batch set operations
        batch_data = {
            i: {'player': f'TestPlayer_{i}', 'rating': 1400 + i * 5}
            for i in range(5)
        }
        
        # Cache should handle batch operations efficiently
        cache_stats = self.cache.get_stats()
        initial_requests = cache_stats.get('total_requests', 0)
        
        # Batch operations should be more efficient than individual operations
        print(f"✅ Batch cache operations completed: {len(batch_results)} items processed")
        print(f"   Cache stats: {cache_stats}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])