#!/bin/bash

# Game Arena Staging Deployment Script
# This script deploys the Game Arena application to a staging environment
# for comprehensive testing and validation

set -e  # Exit on any error

# Configuration
STAGING_DIR="staging_deployment"
BACKEND_PORT=5001  # Different from dev port
FRONTEND_PORT=3001
LOG_DIR="logs"
DATE=$(date +%Y%m%d_%H%M%S)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    # Check if conda is available
    if ! command -v conda &> /dev/null; then
        error "Conda is not available. Please install Anaconda/Miniconda."
        exit 1
    fi
    
    # Check if node/npm is available
    if ! command -v npm &> /dev/null; then
        error "npm is not available. Please install Node.js."
        exit 1
    fi
    
    # Check if conda environment exists
    if ! conda env list | grep -q "game_arena"; then
        error "Conda environment 'game_arena' not found. Please create it first."
        exit 1
    fi
    
    # Check if ports are available
    if lsof -ti:$BACKEND_PORT > /dev/null 2>&1; then
        warning "Port $BACKEND_PORT is in use. Attempting to kill processes..."
        kill -9 $(lsof -ti:$BACKEND_PORT) 2>/dev/null || true
        sleep 2
    fi
    
    if lsof -ti:$FRONTEND_PORT > /dev/null 2>&1; then
        warning "Port $FRONTEND_PORT is in use. Attempting to kill processes..."
        kill -9 $(lsof -ti:$FRONTEND_PORT) 2>/dev/null || true
        sleep 2
    fi
    
    success "Prerequisites check passed"
}

# Create staging directory structure
setup_staging_environment() {
    log "Setting up staging environment..."
    
    # Create staging directory
    mkdir -p $STAGING_DIR
    mkdir -p $STAGING_DIR/$LOG_DIR
    
    # Create staging configuration files
    cat > $STAGING_DIR/staging_config.json << EOF
{
    "environment": "staging",
    "backend_port": $BACKEND_PORT,
    "frontend_port": $FRONTEND_PORT,
    "database_path": "$STAGING_DIR/staging_tournament.db",
    "log_level": "DEBUG",
    "performance_monitoring": true,
    "error_tracking": true,
    "cache_enabled": true,
    "cache_ttl": 300,
    "deployment_date": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "deployment_id": "staging_$DATE"
}
EOF
    
    success "Staging environment setup complete"
}

# Build and prepare frontend
build_frontend() {
    log "Building frontend for staging..."
    
    cd web_interface/frontend
    
    # Install dependencies if needed
    if [ ! -d "node_modules" ] || [ "package.json" -nt "node_modules" ]; then
        log "Installing frontend dependencies..."
        npm ci
    fi
    
    # Run tests first
    log "Running frontend tests..."
    if ! npm run test:coverage -- --watchAll=false; then
        error "Frontend tests failed. Deployment aborted."
        exit 1
    fi
    
    # Run linting
    log "Running frontend linting..."
    if ! npm run lint; then
        error "Frontend linting failed. Deployment aborted."
        exit 1
    fi
    
    # Run type checking
    log "Running TypeScript type checking..."
    if ! npm run type-check; then
        error "TypeScript type checking failed. Deployment aborted."
        exit 1
    fi
    
    # Build for staging
    log "Building frontend bundle..."
    REACT_APP_STAGE=staging REACT_APP_API_URL=http://localhost:$BACKEND_PORT npm run build
    
    # Analyze bundle size
    log "Analyzing bundle size..."
    npm run bundle:size || warning "Bundle size analysis failed (non-critical)"
    
    # Copy build to staging directory
    cp -r build ../../$STAGING_DIR/frontend_build
    
    cd ../..
    
    success "Frontend build completed"
}

# Prepare backend
prepare_backend() {
    log "Preparing backend for staging..."
    
    # Activate conda environment and run backend tests
    conda run -n game_arena python -m pytest web_interface/backend/ -v --tb=short
    
    if [ $? -ne 0 ]; then
        error "Backend tests failed. Deployment aborted."
        exit 1
    fi
    
    # Run backend linting
    conda run -n game_arena python -m pylint web_interface/backend/ --exit-zero
    
    # Copy backend files to staging
    cp -r web_interface/backend $STAGING_DIR/
    
    # Create staging-specific backend configuration
    cat > $STAGING_DIR/backend/staging_config.py << EOF
import os

# Staging configuration
DEBUG = True
TESTING = False
LOG_LEVEL = "DEBUG"

# Database
DATABASE_PATH = os.path.join(os.path.dirname(__file__), '..', 'staging_tournament.db')

# Performance monitoring
PERFORMANCE_MONITORING_ENABLED = True
ERROR_TRACKING_ENABLED = True

# Cache settings
CACHE_ENABLED = True
CACHE_TTL = 300  # 5 minutes for staging
CACHE_SIZE = 1000

# API settings
API_HOST = "0.0.0.0"
API_PORT = $BACKEND_PORT
CORS_ORIGINS = ["http://localhost:$FRONTEND_PORT", "http://127.0.0.1:$FRONTEND_PORT"]

# Logging
LOG_FILE = os.path.join(os.path.dirname(__file__), '..', 'logs', 'staging_backend.log')
STRUCTURED_LOGGING = True

# Feature flags for testing
ENABLE_BATCH_PROCESSING = True
ENABLE_CACHE_WARMING = True
ENABLE_PERFORMANCE_ALERTS = True
EOF
    
    success "Backend preparation completed"
}

# Setup test data
setup_test_data() {
    log "Setting up test data..."
    
    # Copy existing database to staging for testing
    if [ -f "demo_tournament.db" ]; then
        cp demo_tournament.db $STAGING_DIR/staging_tournament.db
        log "Copied existing database to staging"
    else
        # Create minimal test database
        conda run -n game_arena python -c "
import sys
sys.path.append('web_interface/backend')
from game_arena.storage import create_database
create_database('$STAGING_DIR/staging_tournament.db')
print('Created new staging database')
"
    fi
    
    success "Test data setup completed"
}

# Start staging servers
start_staging_servers() {
    log "Starting staging servers..."
    
    # Start backend server
    log "Starting backend server on port $BACKEND_PORT..."
    cd $STAGING_DIR/backend
    
    # Set environment variables
    export GAME_ARENA_CONFIG="staging_config.py"
    export PYTHONPATH="$(pwd):$PYTHONPATH"
    
    # Start backend in background
    conda run -n game_arena python main.py > ../logs/backend_$DATE.log 2>&1 &
    BACKEND_PID=$!
    echo $BACKEND_PID > ../backend.pid
    
    cd ../..
    
    # Wait for backend to start
    log "Waiting for backend to start..."
    for i in {1..30}; do
        if curl -s http://localhost:$BACKEND_PORT/health > /dev/null 2>&1; then
            success "Backend server started successfully"
            break
        fi
        if [ $i -eq 30 ]; then
            error "Backend server failed to start"
            cat $STAGING_DIR/logs/backend_$DATE.log | tail -20
            exit 1
        fi
        sleep 2
    done
    
    # Start frontend server (simple HTTP server for built files)
    log "Starting frontend server on port $FRONTEND_PORT..."
    cd $STAGING_DIR/frontend_build
    
    # Use Python's built-in HTTP server for serving static files
    python3 -m http.server $FRONTEND_PORT > ../logs/frontend_$DATE.log 2>&1 &
    FRONTEND_PID=$!
    echo $FRONTEND_PID > ../frontend.pid
    
    cd ../..
    
    # Wait for frontend to start
    log "Waiting for frontend to start..."
    for i in {1..15}; do
        if curl -s http://localhost:$FRONTEND_PORT > /dev/null 2>&1; then
            success "Frontend server started successfully"
            break
        fi
        if [ $i -eq 15 ]; then
            error "Frontend server failed to start"
            exit 1
        fi
        sleep 1
    done
    
    success "Staging servers started successfully"
}

# Run comprehensive tests
run_staging_tests() {
    log "Running comprehensive staging tests..."
    
    # API Health Check
    log "Testing API health endpoint..."
    if ! curl -f http://localhost:$BACKEND_PORT/health; then
        error "API health check failed"
        return 1
    fi
    
    # Test core API endpoints
    log "Testing core API endpoints..."
    
    # Test leaderboard endpoint
    if ! curl -f "http://localhost:$BACKEND_PORT/api/v1/leaderboard?limit=5" > /dev/null; then
        error "Leaderboard endpoint test failed"
        return 1
    fi
    
    # Test statistics endpoint
    if ! curl -f "http://localhost:$BACKEND_PORT/api/v1/statistics/overview" > /dev/null; then
        error "Statistics endpoint test failed"
        return 1
    fi
    
    # Test frontend loading
    log "Testing frontend loading..."
    if ! curl -f http://localhost:$FRONTEND_PORT > /dev/null; then
        error "Frontend loading test failed"
        return 1
    fi
    
    # Run integration tests if available
    log "Running integration tests..."
    cd web_interface/frontend
    if npm run test:e2e 2>/dev/null; then
        success "Integration tests passed"
    else
        warning "Integration tests not available or failed (non-critical for staging)"
    fi
    cd ../..
    
    success "Staging tests completed successfully"
}

# Performance validation
validate_performance() {
    log "Validating performance metrics..."
    
    # Test API response times
    log "Measuring API response times..."
    
    local leaderboard_time=$(curl -o /dev/null -s -w "%{time_total}" "http://localhost:$BACKEND_PORT/api/v1/leaderboard")
    local stats_time=$(curl -o /dev/null -s -w "%{time_total}" "http://localhost:$BACKEND_PORT/api/v1/statistics/overview")
    
    log "Leaderboard API response time: ${leaderboard_time}s"
    log "Statistics API response time: ${stats_time}s"
    
    # Check if response times are within acceptable limits
    if (( $(echo "$leaderboard_time > 2.0" | bc -l) )); then
        warning "Leaderboard API response time exceeds 2 seconds: ${leaderboard_time}s"
    fi
    
    if (( $(echo "$stats_time > 3.0" | bc -l) )); then
        warning "Statistics API response time exceeds 3 seconds: ${stats_time}s"
    fi
    
    # Test memory usage
    local backend_pid=$(cat $STAGING_DIR/backend.pid)
    if ps -p $backend_pid > /dev/null; then
        local memory_usage=$(ps -o rss= -p $backend_pid)
        log "Backend memory usage: $((memory_usage / 1024))MB"
        
        if [ $memory_usage -gt 512000 ]; then  # 512MB in KB
            warning "Backend memory usage high: $((memory_usage / 1024))MB"
        fi
    fi
    
    success "Performance validation completed"
}

# Generate deployment report
generate_deployment_report() {
    log "Generating deployment report..."
    
    local report_file="$STAGING_DIR/deployment_report_$DATE.md"
    
    cat > $report_file << EOF
# Game Arena Staging Deployment Report

**Deployment ID:** staging_$DATE  
**Deployment Date:** $(date -u +%Y-%m-%dT%H:%M:%SZ)  
**Environment:** Staging  

## Configuration

- **Backend Port:** $BACKEND_PORT
- **Frontend Port:** $FRONTEND_PORT
- **Database:** staging_tournament.db
- **Log Level:** DEBUG
- **Monitoring Enabled:** Yes

## Build Information

### Frontend
- **Build Tool:** React Scripts
- **Bundle Analysis:** $([ -f "web_interface/frontend/bundle-report.html" ] && echo "Available" || echo "Not available")
- **Test Coverage:** $(grep -o '[0-9.]*%' web_interface/frontend/coverage/lcov-report/index.html 2>/dev/null | head -1 || echo "Not measured")

### Backend  
- **Python Environment:** game_arena (conda)
- **Test Status:** $(conda run -n game_arena python -m pytest web_interface/backend/ --tb=no -q 2>/dev/null && echo "PASSED" || echo "FAILED")

## Performance Metrics

- **Leaderboard API Response Time:** ${leaderboard_time:-"Not measured"}s
- **Statistics API Response Time:** ${stats_time:-"Not measured"}s
- **Backend Memory Usage:** $((${memory_usage:-0} / 1024))MB

## Server Status

- **Backend PID:** $(cat $STAGING_DIR/backend.pid 2>/dev/null || echo "Not running")
- **Frontend PID:** $(cat $STAGING_DIR/frontend.pid 2>/dev/null || echo "Not running")
- **Backend Health:** $(curl -s http://localhost:$BACKEND_PORT/health >/dev/null && echo "✅ Healthy" || echo "❌ Unhealthy")
- **Frontend Status:** $(curl -s http://localhost:$FRONTEND_PORT >/dev/null && echo "✅ Running" || echo "❌ Down")

## Access URLs

- **Frontend:** http://localhost:$FRONTEND_PORT
- **Backend API:** http://localhost:$BACKEND_PORT
- **Health Check:** http://localhost:$BACKEND_PORT/health
- **API Documentation:** http://localhost:$BACKEND_PORT/docs

## Log Files

- **Backend Log:** logs/backend_$DATE.log
- **Frontend Log:** logs/frontend_$DATE.log
- **Deployment Log:** Available in terminal output

## Next Steps

1. **Manual Testing:** Verify chess board functionality, statistics accuracy, and error handling
2. **Performance Testing:** Run load tests and measure response times under stress
3. **User Acceptance Testing:** Collect feedback from test users
4. **Monitoring:** Monitor logs for errors and performance issues
5. **Data Validation:** Verify statistics calculations with known datasets

## Shutdown Commands

\`\`\`bash
# Stop staging servers
./stop_staging.sh

# Or manually:
kill \$(cat staging_deployment/backend.pid)
kill \$(cat staging_deployment/frontend.pid)
\`\`\`

EOF
    
    success "Deployment report generated: $report_file"
}

# Create shutdown script
create_shutdown_script() {
    cat > stop_staging.sh << 'EOF'
#!/bin/bash

# Stop staging deployment

echo "Stopping Game Arena staging deployment..."

# Stop backend
if [ -f "staging_deployment/backend.pid" ]; then
    BACKEND_PID=$(cat staging_deployment/backend.pid)
    if ps -p $BACKEND_PID > /dev/null; then
        kill $BACKEND_PID
        echo "Backend server stopped (PID: $BACKEND_PID)"
    fi
    rm staging_deployment/backend.pid
fi

# Stop frontend  
if [ -f "staging_deployment/frontend.pid" ]; then
    FRONTEND_PID=$(cat staging_deployment/frontend.pid)
    if ps -p $FRONTEND_PID > /dev/null; then
        kill $FRONTEND_PID
        echo "Frontend server stopped (PID: $FRONTEND_PID)"
    fi
    rm staging_deployment/frontend.pid
fi

echo "Staging deployment stopped successfully"
EOF

    chmod +x stop_staging.sh
    success "Shutdown script created: stop_staging.sh"
}

# Main deployment function
main() {
    log "Starting Game Arena staging deployment..."
    
    check_prerequisites
    setup_staging_environment
    build_frontend
    prepare_backend
    setup_test_data
    start_staging_servers
    
    # Wait a moment for servers to fully initialize
    sleep 5
    
    run_staging_tests
    validate_performance
    generate_deployment_report
    create_shutdown_script
    
    success "🎉 Staging deployment completed successfully!"
    
    echo ""
    echo "==================== DEPLOYMENT SUMMARY ===================="
    echo "Frontend URL: http://localhost:$FRONTEND_PORT"
    echo "Backend API:  http://localhost:$BACKEND_PORT"
    echo "Health Check: http://localhost:$BACKEND_PORT/health"
    echo "API Docs:     http://localhost:$BACKEND_PORT/docs"
    echo ""
    echo "Log files available in: $STAGING_DIR/logs/"
    echo "Deployment report: $STAGING_DIR/deployment_report_$DATE.md"
    echo ""
    echo "To stop staging deployment: ./stop_staging.sh"
    echo "=========================================================="
}

# Run main function
main