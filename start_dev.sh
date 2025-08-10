#!/bin/bash

# Game Arena Development Starter Script
# Starts both frontend and backend servers concurrently

echo "🚀 Starting Game Arena Development Servers..."

# Check if we're in the right directory
if [ ! -d "web_interface/frontend" ] || [ ! -d "web_interface/backend" ]; then
    echo "❌ Error: Please run this script from the game_arena root directory"
    echo "Current directory: $(pwd)"
    echo "Looking for: web_interface/frontend and web_interface/backend directories"
    exit 1
fi

# Function to handle cleanup
cleanup() {
    echo "🛑 Shutting down servers..."
    kill $(jobs -p) 2>/dev/null
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

echo "📦 Starting backend server..."
cd web_interface/backend
conda run -n game_arena python main.py &
BACKEND_PID=$!

echo "⚛️  Starting frontend server..."
cd ../frontend
npm start &
FRONTEND_PID=$!

# Go back to root directory
cd ../..

echo "✅ Servers started!"
echo "   - Backend: http://localhost:5000"
echo "   - Frontend: http://localhost:3000"
echo ""
echo "Press Ctrl+C to stop both servers"

# Wait for both processes
wait $BACKEND_PID $FRONTEND_PID