# Troubleshooting Guide

## Overview

This guide provides comprehensive troubleshooting information for common issues encountered in the Game Arena chess analysis system. It covers both development and production scenarios with step-by-step resolution procedures.

## Common Issues and Solutions

### Chess Board Issues

#### 1. Chess Board Not Loading

**Symptoms:**
- Blank chess board area
- "Loading..." message persists
- Console errors about chessboard.js

**Causes & Solutions:**

**A. jQuery Dependency Missing**
```bash
# Check for jQuery errors in browser console
Cannot read properties of undefined (reading 'fn')
```

**Solution:**
```bash
# Install jQuery dependencies
npm install jquery @types/jquery

# Verify package.json includes:
"dependencies": {
  "jquery": "^3.7.1",
  "@types/jquery": "^3.5.32"
}
```

**B. Chessboard.js Library Loading Failed**
```javascript
// Check browser console for:
Failed to load chessboard library from npm
```

**Solution:**
```typescript
// Verify ChessBoardComponent.tsx has correct imports
import '@chrisoakman/chessboardjs/dist/chessboard-1.0.0.min.css';

// Check if library is installed
npm list @chrisoakman/chessboardjs
```

**C. CSS Styles Not Loading**
```bash
# Ensure CSS import is present
import '@chrisoakman/chessboardjs/dist/chessboard-1.0.0.min.css';
```

#### 2. Chess Pieces Not Displaying

**Symptoms:**
- Chess board renders but pieces are invisible
- Console 404 errors for piece images

**Solution:**
```typescript
// Verify pieceTheme configuration in ChessBoardComponent.tsx
const config = {
  position: position,
  orientation: orientation,
  pieceTheme: 'https://chessboardjs.com/img/chesspieces/wikipedia/{piece}.png',
  // ... other config
};
```

**Alternative piece theme URLs:**
```typescript
// Alternative CDN options
pieceTheme: 'https://chessboardjs.com/img/chesspieces/alpha/{piece}.png'
pieceTheme: 'https://chessboardjs.com/img/chesspieces/uscf/{piece}.png'
```

#### 3. Invalid FEN Position Errors

**Symptoms:**
- Chess board shows error state
- "Invalid FEN" messages in console

**Diagnostic Steps:**
```bash
# Check FEN validation in browser console
chess.js validation error: Invalid FEN string
```

**Solution:**
```typescript
// Use FEN validation utility
const validatePosition = (fen: string): boolean => {
  try {
    const chess = new Chess();
    chess.load(fen);
    return true;
  } catch (error) {
    console.error('Invalid FEN:', fen, error);
    return false;
  }
};

// Fallback to starting position
const STARTING_FEN = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';
```

### Backend API Issues

#### 4. Statistics Not Loading

**Symptoms:**
- Empty leaderboard
- Statistics dashboard shows no data
- API timeouts

**Diagnostic Steps:**
```bash
# Check API endpoint responses
curl -X GET "http://localhost:5000/api/v1/leaderboard" -H "Accept: application/json"

# Check backend logs
tail -f web_interface/backend/server.log

# Verify database connection
python -c "
import asyncio
from game_arena.storage import create_query_engine
async def test():
    engine = await create_query_engine('demo_tournament.db')
    games = await engine.query_games()
    print(f'Found {len(games)} games')
asyncio.run(test())
"
```

**Solutions:**

**A. Database Connection Issues**
```python
# Verify database file exists and is accessible
import os
if os.path.exists('demo_tournament.db'):
    print(f"Database size: {os.path.getsize('demo_tournament.db')} bytes")
else:
    print("Database file not found")
```

**B. Cache Issues**
```bash
# Clear cache if data appears stale
rm -rf /tmp/game_arena_cache_*

# Restart backend with cache clearing
python web_interface/backend/main.py --clear-cache
```

**C. ELO Calculation Errors**
```bash
# Check for ELO calculation issues in logs
grep -i "elo" web_interface/backend/server.log

# Manually recalculate ELO ratings
python -c "
from web_interface.backend.elo_rating import AccurateELOCalculator
calculator = AccurateELOCalculator()
calculator.recalculate_all_ratings()
"
```

#### 5. Game Data Import Issues

**Symptoms:**
- Games not appearing after import
- Import process hangs or fails
- Data corruption errors

**Diagnostic Steps:**
```bash
# Check import logs
grep -i "import\|error" web_interface/backend/server.log

# Validate PGN files
python -c "
import chess.pgn
with open('your_games.pgn', 'r') as f:
    game_count = 0
    while True:
        game = chess.pgn.read_game(f)
        if game is None:
            break
        game_count += 1
    print(f'Found {game_count} games')
"
```

**Solutions:**

**A. PGN Format Issues**
```bash
# Validate PGN format
python -m chess.pgn validate your_games.pgn

# Fix common PGN issues
sed -i 's/\r$//' your_games.pgn  # Remove Windows line endings
sed -i '/^\s*$/d' your_games.pgn  # Remove empty lines
```

**B. Memory Issues During Import**
```python
# Use batch import for large files
from game_arena.storage import GameImporter
importer = GameImporter(batch_size=100)  # Reduce batch size
await importer.import_pgn_file('your_games.pgn')
```

### Frontend Issues

#### 6. Duplicate Search Bars

**Symptoms:**
- Two identical search/filter components visible
- Layout appears broken

**Solution:**
```typescript
// Check for duplicate FilterPanel imports
// Remove from GameListView.tsx if present:
// import { FilterPanel } from './FilterPanel';

// Ensure FilterPanel only appears in Games.tsx:
<FilterPanel
  filters={filters}
  onFiltersChange={handleFiltersChange}
  isLoading={isLoading}
/>
```

#### 7. TypeScript Compilation Errors

**Symptoms:**
- Build fails with TS errors
- Red underlines in IDE

**Common Errors & Solutions:**

**A. JSX Comparison Operators**
```typescript
// Error: TS1382: Unexpected token. Did you mean '{'>'}' or '&gt;'?
// Fix: Escape comparison operators in JSX
<option value="correspondence">Correspondence (&gt; 90 min)</option>
<option value="very_long">Very long games (&gt; 60 moves)</option>
```

**B. Missing Type Definitions**
```bash
# Install missing types
npm install --save-dev @types/node @types/react @types/react-dom

# For jQuery
npm install --save-dev @types/jquery
```

#### 8. Performance Issues

**Symptoms:**
- Slow page loading
- Laggy interactions
- High memory usage

**Diagnostic Steps:**
```bash
# Check browser performance tab
# Look for:
# - Long tasks (>50ms)
# - Memory leaks
# - Excessive re-renders

# Check React DevTools Profiler
# Identify components with expensive renders
```

**Solutions:**

**A. React Component Optimization**
```typescript
// Add React.memo for expensive components
export const ExpensiveComponent = React.memo(({ data }) => {
  // Component logic
}, (prevProps, nextProps) => {
  // Custom comparison function
  return prevProps.data.id === nextProps.data.id;
});

// Use useMemo for expensive calculations
const expensiveValue = useMemo(() => {
  return calculateExpensiveValue(data);
}, [data]);
```

**B. Virtual Scrolling for Large Lists**
```typescript
import { FixedSizeList as List } from 'react-window';

// Replace large lists with virtualized versions
<List
  height={600}
  itemCount={items.length}
  itemSize={50}
>
  {({ index, style }) => (
    <div style={style}>
      {items[index]}
    </div>
  )}
</List>
```

### Development Environment Issues

#### 9. Development Server Won't Start

**Symptoms:**
- `npm start` fails
- Port already in use errors
- Module not found errors

**Solutions:**

**A. Port Conflicts**
```bash
# Find process using port 3000
lsof -ti:3000
kill -9 $(lsof -ti:3000)

# Or use different port
PORT=3001 npm start
```

**B. Node Modules Issues**
```bash
# Clear node modules and reinstall
rm -rf node_modules package-lock.json
npm install

# Clear npm cache
npm cache clean --force
```

**C. Environment Variables**
```bash
# Check required environment variables
echo $NODE_ENV
echo $REACT_APP_API_URL

# Set missing variables
export NODE_ENV=development
export REACT_APP_API_URL=http://localhost:5000
```

#### 10. Backend Server Issues

**Symptoms:**
- Backend fails to start
- Database connection errors
- Python import errors

**Solutions:**

**A. Python Environment**
```bash
# Verify conda environment
conda env list
conda activate game_arena

# Install missing dependencies
pip install -r requirements.txt

# Or install in development mode
pip install -e .
```

**B. Database Issues**
```bash
# Check database file permissions
ls -la demo_tournament.db

# Recreate database if corrupted
rm demo_tournament.db
python -c "
from game_arena.storage import create_database
create_database('demo_tournament.db')
"
```

## Performance Troubleshooting

### 11. Slow API Responses

**Diagnostic Commands:**
```bash
# Test API response times
curl -o /dev/null -s -w "%{time_total}s\n" http://localhost:5000/api/v1/leaderboard

# Check database query performance
python -c "
import time
from web_interface.backend.statistics_calculator import AccurateStatisticsCalculator
start = time.time()
calc = AccurateStatisticsCalculator(query_engine)
result = calc.calculate_leaderboard()
print(f'Leaderboard calculation took {time.time() - start:.2f}s')
"
```

**Optimization Steps:**
```bash
# Enable caching
export CACHE_ENABLED=true

# Increase cache size
export CACHE_SIZE=10000

# Enable batch processing
export BATCH_PROCESSING=true
```

### 12. Memory Leaks

**Detection:**
```bash
# Monitor memory usage
ps -o pid,vsz,rss,comm -p $(pgrep -f "python.*main.py")

# Use memory profiler
pip install memory-profiler
python -m memory_profiler web_interface/backend/main.py
```

**Solutions:**
```python
# Add memory monitoring
import psutil
import gc

def monitor_memory():
    process = psutil.Process()
    memory_mb = process.memory_info().rss / 1024 / 1024
    if memory_mb > 500:  # 500MB threshold
        logger.warning(f"High memory usage: {memory_mb:.1f}MB")
        gc.collect()  # Force garbage collection
```

## Error Code Reference

### HTTP Error Codes

| Code | Description | Common Causes | Solution |
|------|-------------|---------------|----------|
| 400 | Bad Request | Invalid parameters | Check API documentation |
| 404 | Not Found | Invalid player ID or game ID | Verify resource exists |
| 429 | Too Many Requests | Rate limit exceeded | Implement request throttling |
| 500 | Internal Server Error | Backend exception | Check server logs |
| 503 | Service Unavailable | System overload | Scale resources or reduce load |

### Application Error Codes

| Code | Description | Resolution |
|------|-------------|------------|
| FEN_INVALID_FORMAT | Invalid FEN string | Use FEN validator, fallback to starting position |
| MOVE_ILLEGAL | Illegal chess move | Implement move validation |
| CACHE_MISS_CRITICAL | Critical data not in cache | Force cache refresh |
| DB_CONNECTION_FAILED | Database unreachable | Check connection string and permissions |
| BATCH_TIMEOUT | Batch processing timeout | Reduce batch size or increase timeout |

## Log Analysis

### Key Log Patterns

**Success Patterns:**
```bash
# Successful API requests
grep "200\|201" web_interface/backend/server.log

# Cache hits
grep "cache_hit" web_interface/backend/server.log

# Successful batch processing
grep "batch_completed" web_interface/backend/server.log
```

**Error Patterns:**
```bash
# API errors
grep -E "4[0-9][0-9]\|5[0-9][0-9]" web_interface/backend/server.log

# Database errors
grep -i "database\|sql" web_interface/backend/server.log | grep -i error

# Cache misses and errors
grep "cache_miss\|cache_error" web_interface/backend/server.log

# Performance warnings
grep -i "slow\|timeout\|performance" web_interface/backend/server.log
```

## Preventive Measures

### 1. Health Checks

```python
# Add to your application startup
async def health_check():
    """Comprehensive system health check."""
    issues = []
    
    # Check database connection
    try:
        engine = get_query_engine()
        await engine.query_games(limit=1)
    except Exception as e:
        issues.append(f"Database connection failed: {e}")
    
    # Check cache system
    try:
        cache = get_statistics_cache()
        await cache.set("health_check", "ok", ttl=60)
        result = await cache.get("health_check")
        if result != "ok":
            issues.append("Cache system not working")
    except Exception as e:
        issues.append(f"Cache system failed: {e}")
    
    # Check disk space
    disk_usage = psutil.disk_usage('/').percent
    if disk_usage > 90:
        issues.append(f"Low disk space: {disk_usage}%")
    
    return {
        "healthy": len(issues) == 0,
        "issues": issues,
        "timestamp": datetime.now().isoformat()
    }
```

### 2. Monitoring Setup

```python
# Add performance monitoring
import logging
import time
from functools import wraps

def monitor_performance(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            duration = time.time() - start_time
            logger.info(f"{func.__name__} completed in {duration:.3f}s")
            return result
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"{func.__name__} failed after {duration:.3f}s: {e}")
            raise
    return wrapper

# Apply to critical functions
@monitor_performance
async def calculate_leaderboard():
    # Implementation
    pass
```

### 3. Automated Recovery

```python
# Implement circuit breaker pattern
class CircuitBreaker:
    def __init__(self, failure_threshold=5, recovery_timeout=60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'CLOSED'  # CLOSED, OPEN, HALF_OPEN
    
    def call(self, func, *args, **kwargs):
        if self.state == 'OPEN':
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = 'HALF_OPEN'
            else:
                raise Exception("Circuit breaker is OPEN")
        
        try:
            result = func(*args, **kwargs)
            self.on_success()
            return result
        except Exception as e:
            self.on_failure()
            raise
    
    def on_success(self):
        self.failure_count = 0
        self.state = 'CLOSED'
    
    def on_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = 'OPEN'
```

## Emergency Procedures

### System Recovery

```bash
#!/bin/bash
# emergency_recovery.sh

echo "Starting emergency recovery..."

# Stop all services
pkill -f "npm start"
pkill -f "python.*main.py"

# Clear caches
rm -rf /tmp/game_arena_cache_*
rm -rf node_modules/.cache

# Reset database connections
python -c "
from game_arena.storage import reset_connection_pool
reset_connection_pool()
"

# Restart services
cd web_interface/backend && python main.py &
cd web_interface/frontend && npm start &

echo "Recovery complete. Check logs for issues."
```

This troubleshooting guide covers the most common issues encountered in the Game Arena system and provides systematic approaches to diagnosing and resolving problems quickly.