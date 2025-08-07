#!/usr/bin/env python3
"""
Example usage of the PostgreSQL storage backend.

This example demonstrates how to configure and use the PostgreSQL backend
for the Game Arena storage system.
"""

import asyncio
import os
from datetime import datetime

from game_arena.storage.backends.postgresql_backend import PostgreSQLBackend
from game_arena.storage.config import DatabaseConfig, StorageBackendType
from game_arena.storage.models import GameRecord, PlayerInfo


async def main():
    """Example usage of PostgreSQL backend."""
    
    # Configuration from environment variables (recommended for production)
    config = DatabaseConfig(
        backend_type=StorageBackendType.POSTGRESQL,
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        database=os.getenv("POSTGRES_DB", "game_arena"),
        username=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD", ""),
        connection_pool_size=10,
        connection_timeout=30,
        enable_ssl=os.getenv("POSTGRES_SSL", "false").lower() == "true"
    )
    
    # Alternative: Configuration from database URL
    # config = DatabaseConfig.from_url(
    #     "postgresql://user:password@localhost:5432/game_arena"
    # )
    
    # Create backend instance
    backend = PostgreSQLBackend(config)
    
    try:
        # Connect to database
        print("Connecting to PostgreSQL database...")
        await backend.connect()
        print("✓ Connected successfully")
        
        # Initialize schema
        print("Initializing database schema...")
        await backend.initialize_schema()
        print("✓ Schema initialized")
        
        # Get storage statistics
        stats = await backend.get_storage_stats()
        print(f"✓ Database stats: {stats}")
        
        # Example: Create a sample game
        players = {
            0: PlayerInfo(
                player_id="black_player",
                model_name="gpt-4",
                model_provider="openai",
                agent_type="ChessLLMAgent",
                agent_config={"temperature": 0.7},
                elo_rating=1500.0
            ),
            1: PlayerInfo(
                player_id="white_player",
                model_name="claude-3",
                model_provider="anthropic",
                agent_type="ChessRethinkAgent",
                agent_config={"max_retries": 3},
                elo_rating=1600.0
            )
        }
        
        game = GameRecord(
            game_id="example_game_001",
            tournament_id="example_tournament",
            start_time=datetime.now(),
            players=players,
            metadata={"example": True, "backend": "postgresql"}
        )
        
        # Create the game
        print("Creating example game...")
        game_id = await backend.create_game(game)
        print(f"✓ Game created with ID: {game_id}")
        
        # Retrieve the game
        retrieved_game = await backend.get_game(game_id)
        print(f"✓ Game retrieved: {retrieved_game.game_id}")
        
        # Query games
        games = await backend.query_games({"tournament_id": "example_tournament"})
        print(f"✓ Found {len(games)} games in tournament")
        
        # Clean up example data
        await backend.delete_game(game_id)
        print("✓ Example game cleaned up")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        
    finally:
        # Always disconnect
        await backend.disconnect()
        print("✓ Disconnected from database")


if __name__ == "__main__":
    asyncio.run(main())