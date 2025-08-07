#!/usr/bin/env python3
"""
Simple script to analyze stored game data using the Game Arena storage system.
"""
import asyncio
import json
from datetime import datetime

from game_arena.storage.config import DatabaseConfig, StorageBackendType, StorageConfig
from game_arena.storage.manager import StorageManager
from game_arena.storage.backends.sqlite_backend import SQLiteBackend
from game_arena.storage.query_engine import QueryEngine
from game_arena.storage.export import GameExporter


async def analyze_game_data():
    """Analyze the game data stored in test_game.db"""
    
    print("🎮 Game Arena Data Analysis")
    print("=" * 50)
    
    # Initialize storage components
    db_config = DatabaseConfig.sqlite_default("demo_tournament.db")
    storage_config = StorageConfig(database=db_config)
    backend = SQLiteBackend(db_config)
    manager = StorageManager(backend, storage_config)
    query_engine = QueryEngine(manager)
    export_service = GameExporter(manager, query_engine)
    
    # Connect to database
    await backend.connect()
    
    try:
        # 1. Basic Statistics
        print("\n📊 Basic Statistics:")
        stats = await backend.get_storage_stats()
        print(f"  • Total Games: {stats.get('game_count', 0)}")
        print(f"  • Total Moves: {stats.get('move_count', 0)}")
        print(f"  • Database Size: {stats.get('database_size_bytes', 0)/1024:.1f} KB")
        
        # Get actual player count from players table
        cursor = backend._connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM players")
        player_count = cursor.fetchone()[0]
        print(f"  • Total Players: {player_count}")
        
        # 2. Game Details
        print("\n🎯 Game Details:")
        # Get recent games (this should return all games in our small dataset)
        games = await query_engine.get_recent_games(limit=10)
        for game in games:
            print(f"  • Game ID: {game.game_id[:8]}...")
            print(f"  • Started: {game.start_time}")
            print(f"  • Duration: {game.game_duration_seconds or 'N/A'} seconds")
            print(f"  • Total Moves: {game.total_moves}")
            
        # 3. Move Analysis
        print("\n♟️  Move Analysis:")
        for game in games:
            # Use storage manager directly for moves
            moves = await manager.get_moves(game.game_id)
            print(f"  Game {game.game_id[:8]}...")
            
            for move in moves:
                legal_status = "✅ Legal" if move.is_legal else "❌ Illegal"
                thinking_time = f"{move.thinking_time_ms}ms"
                print(f"    Move {move.move_number}: {move.move_san} ({legal_status}, {thinking_time})")
        
        # 4. Player Performance
        print("\n👥 Player Performance:")
        # Get players directly from database
        cursor.execute("SELECT * FROM players")
        player_rows = cursor.fetchall()
        print(f"  Found {len(player_rows)} players in database")
        
        for row in player_rows:
            game_id, player_num, player_name, model_name, provider, agent_type, config, elo = row
            print(f"  • Player {player_num} ({player_name}): {model_name}")
            print(f"    - Provider: {provider}")
            print(f"    - Agent Type: {agent_type}")
            print(f"    - ELO Rating: {elo}")
            
            # Get moves for this player
            cursor.execute("SELECT * FROM moves WHERE game_id = ? AND player = ?", (game_id, player_num))
            player_moves = cursor.fetchall()
            
            if player_moves:
                # Calculate stats for this player  
                legal_moves = sum(1 for move in player_moves if move[10])  # is_legal column (0-indexed)
                total_moves = len(player_moves)
                avg_thinking_time = sum(int(move[16] or 0) for move in player_moves) / total_moves  # thinking_time_ms column
                
                print(f"    - Moves Played: {total_moves}")
                print(f"    - Legal Moves: {legal_moves}/{total_moves} ({100*legal_moves/total_moves:.1f}%)")
                print(f"    - Avg Thinking Time: {avg_thinking_time:.0f}ms")
        
        # 5. Performance Metrics
        print("\n⚡ Performance Metrics:")
        all_moves = []
        for game in games:
            game_moves = await manager.get_moves(game.game_id)
            all_moves.extend(game_moves)
        
        if all_moves:
            avg_api_time = sum(m.api_call_time_ms for m in all_moves) / len(all_moves)
            avg_total_time = sum(m.thinking_time_ms for m in all_moves) / len(all_moves)
            legal_rate = sum(1 for m in all_moves if m.is_legal) / len(all_moves)
            
            print(f"  • Average API Call Time: {avg_api_time:.0f}ms")
            print(f"  • Average Total Thinking Time: {avg_total_time:.0f}ms")
            print(f"  • Overall Legal Move Rate: {legal_rate:.2%}")
            
            # Find slowest and fastest moves
            slowest_move = max(all_moves, key=lambda m: m.thinking_time_ms)
            fastest_move = min(all_moves, key=lambda m: m.thinking_time_ms)
            print(f"  • Slowest Move: {slowest_move.move_san} ({slowest_move.thinking_time_ms}ms)")
            print(f"  • Fastest Move: {fastest_move.move_san} ({fastest_move.thinking_time_ms}ms)")
        
        # 6. Export Sample Data
        print("\n📁 Data Export Sample:")
        if games:
            game_id = games[0].game_id
            
            # Export as JSON
            json_data = await export_service.export_game_json(game_id)
            print(f"  • JSON Export Size: {len(json_data)} characters")
            
            # Parse JSON and show structure preview
            try:
                parsed_data = json.loads(json_data)
                print("  • JSON Structure Preview:")
                preview = {
                    "game_id": parsed_data.get("game_id", "")[:8] + "...",
                    "moves_count": len(parsed_data.get("moves", [])),
                    "players_count": len(parsed_data.get("players", [])),
                    "has_metadata": "metadata" in parsed_data
                }
                print(f"    {json.dumps(preview, indent=6)}")
            except json.JSONDecodeError as e:
                print(f"  • JSON Parse Error: {e}")
                print(f"  • Raw Data Preview: {json_data[:200]}...")
        
    except Exception as e:
        print(f"Error analyzing data: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await backend.disconnect()

if __name__ == "__main__":
    asyncio.run(analyze_game_data())