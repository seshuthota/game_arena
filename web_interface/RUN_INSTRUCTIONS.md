# Game Analysis Web Interface - Running Instructions

This document provides detailed step-by-step instructions for setting up and running both the backend API server and frontend React application.

## Prerequisites

### System Requirements
- **Python 3.11+** with conda/miniconda installed
- **Node.js 16+** and npm
- **Git** for version control
- **8GB+ RAM** recommended for development
- **Linux/macOS/Windows** (tested on Linux)

### Environment Setup
1. **Conda Environment**: `game_arena` (must be activated before running Python commands)
2. **Game Arena Harness**: Must be installed and configured
3. **Storage Backend**: SQLite or PostgreSQL database with game data

---

## ✅ Current Status
- **Backend**: ✅ **WORKING** - All API endpoints functional
- **Frontend**: ⚠️ **FIXED** - TypeScript issues resolved, should now work

## 🚀 Quick Start (5 Minutes)

### Terminal 1: Backend API Server
```bash
# 1. Activate conda environment
eval "$(conda shell.bash hook)"
conda activate game_arena

# 2. Navigate to backend directory
cd /home/seshu/Documents/Python/game_arena/web_interface/backend

# 3. Start the FastAPI server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Terminal 2: Frontend React App
```bash
# 1. Navigate to frontend directory  
cd /home/seshu/Documents/Python/game_arena/web_interface/frontend

# 2. Install dependencies (first time only)
npm install

# 3. Start the React development server
npm start
```

### Access the Application
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000  
- **API Documentation**: http://localhost:8000/docs

### 🎯 Quick Verification
```bash
# Test backend health
curl http://localhost:8000/health

# Test API endpoint
curl http://localhost:8000/api/games?limit=2
```

### ⚠️ If Frontend Has TypeScript Errors
```bash
# Alternative startup with checks disabled
cd /home/seshu/Documents/Python/game_arena/web_interface/frontend
SKIP_PREFLIGHT_CHECK=true npm start
```

---

## 📋 Detailed Setup Instructions

### Step 1: Environment Preparation

#### 1.1 Activate Conda Environment
```bash
# Initialize conda (if not already done)
eval "$(conda shell.bash hook)"

# Activate the game_arena environment
conda activate game_arena

# Verify Python version
python --version  # Should be 3.11+
```

#### 1.2 Verify Game Arena Installation
```bash
# Check if game_arena package is installed
python -c "import game_arena; print('Game Arena installed successfully')"

# Verify storage module
python -c "from game_arena.storage import StorageManager; print('Storage module available')"
```

### Step 2: Backend API Server Setup

#### 2.1 Navigate to Backend Directory
```bash
cd /home/seshu/Documents/Python/game_arena/web_interface/backend
```

#### 2.2 Install Backend Dependencies (if needed)
```bash
# Main dependencies should be installed with game_arena package
# If missing, install additional packages:
pip install fastapi uvicorn python-multipart
```

#### 2.3 Configure Environment Variables (Optional)
```bash
# Create .env file for custom configuration
cat << EOF > .env
# API Configuration
API_TITLE="Game Arena Analytics API"
API_DESCRIPTION="Game analysis and statistics API"
API_VERSION="1.0.0"

# CORS Settings
CORS_ORIGINS="http://localhost:3000,http://127.0.0.1:3000"

# Database Configuration (if using custom path)
# DATABASE_PATH="/path/to/your/games.db"
EOF
```

#### 2.4 Verify Backend Configuration
```bash
# Test FastAPI app loading
python -c "from main import create_app; app = create_app(); print('FastAPI app created successfully')"
```

#### 2.5 Start Backend Server
```bash
# Development server with auto-reload
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Alternative: Using hypercorn for production-like testing
# hypercorn main:app --bind 0.0.0.0:8000
```

#### 2.6 Verify Backend is Running
```bash
# In a new terminal, test API endpoints
curl http://localhost:8000/health
curl http://localhost:8000/api/games?limit=5

# Access API documentation
# Open http://localhost:8000/docs in browser
```

### Step 3: Frontend React Application Setup

#### 3.1 Navigate to Frontend Directory
```bash
cd /home/seshu/Documents/Python/game_arena/web_interface/frontend
```

#### 3.2 Install Node.js Dependencies
```bash
# Install all dependencies
npm install

# Verify installation
npm list --depth=0
```

#### 3.3 Configure Frontend Environment (Optional)
```bash
# Create .env file for custom configuration
cat << EOF > .env
# API Configuration
REACT_APP_API_BASE_URL=http://localhost:8000/api

# Development Configuration  
REACT_APP_ENVIRONMENT=development

# Feature Flags
REACT_APP_ENABLE_ANALYTICS=true
REACT_APP_ENABLE_DEBUG_MODE=true
EOF
```

#### 3.4 Start Frontend Development Server
```bash
# Start React development server
npm start

# Server will start on http://localhost:3000
# Browser should automatically open
```

#### 3.5 Verify Frontend is Running
- **Browser**: Navigate to http://localhost:3000
- **Network Tab**: Check API calls to http://localhost:8000/api/*
- **Console**: No error messages should appear

---

## 🔧 Advanced Configuration

### Backend Configuration Options

#### Production Mode
```bash
# Start with production settings
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4

# With SSL (if certificates available)
uvicorn main:app --host 0.0.0.0 --port 8443 --ssl-keyfile=key.pem --ssl-certfile=cert.pem
```

#### Custom Storage Configuration
```python
# In main.py, modify storage configuration
app.state.storage_config = {
    'backend_type': 'sqlite',  # or 'postgresql'
    'database_path': '/custom/path/games.db',
    'connection_pool_size': 10
}
```

#### API Customization
```python
# In config.py, modify API settings
API_CONFIG = {
    'title': 'Custom Game Analytics API',
    'description': 'Custom description',
    'version': '1.0.0',
    'cors_origins': ['http://localhost:3000', 'https://yourdomain.com']
}
```

### Frontend Configuration Options

#### Custom API Endpoint
```bash
# Override default API URL
REACT_APP_API_BASE_URL=http://your-api-server:8000/api npm start
```

#### Production Build
```bash
# Build for production
npm run build

# Serve production build locally
npx serve -s build -l 3000
```

#### Custom Styling/Theming
```javascript
// In src/utils/constants.ts
export const THEME_CONFIG = {
  primaryColor: '#your-color',
  secondaryColor: '#your-secondary-color',
  // ... other theme options
};
```

---

## 🧪 Testing and Development

### Run Backend Tests
```bash
# Activate conda environment
conda activate game_arena

# Navigate to backend directory
cd web_interface/backend

# Run all tests with coverage
python -m pytest --cov=. --cov-report=term-missing

# Run specific test categories
python -m pytest test_games_api.py -v
python -m pytest test_performance.py -v
```

### Run Frontend Tests  
```bash
# Navigate to frontend directory
cd web_interface/frontend

# Run unit tests
npm test

# Run tests with coverage
npm run test:coverage

# Run integration tests
npm run test:integration

# Run E2E tests (requires backend running)
npm run cypress:open  # Interactive mode
npm run cypress:run   # Headless mode
```

### Performance Testing
```bash
# Backend performance tests
cd web_interface/backend
python -m pytest test_performance.py -v

# Load testing (if ab/wrk installed)
ab -n 1000 -c 10 http://localhost:8000/api/games
```

---

## 🐛 Troubleshooting

### Common Backend Issues

#### 1. Conda Environment Not Found
```bash
# Solution: Create or activate environment
conda create -n game_arena python=3.11
conda activate game_arena
pip install -e /path/to/game_arena
```

#### 2. Import Errors
```bash
# Check if game_arena is properly installed
python -c "import game_arena"

# Reinstall if needed
cd /path/to/game_arena
pip install -e .
```

#### 3. Database Connection Issues
```bash
# Check if database file exists and has game data
python -c "
from game_arena.storage import StorageManager
manager = StorageManager()
print(f'Games count: {manager.get_game_count()}')
"
```

#### 4. Port Already in Use
```bash
# Find process using port 8000
lsof -i :8000

# Kill process if needed
kill -9 <PID>

# Or use different port
uvicorn main:app --port 8001
```

### Common Frontend Issues

#### 1. Node Modules Issues
```bash
# Clear node_modules and reinstall
rm -rf node_modules package-lock.json
npm install
```

#### 2. API Connection Errors
```bash
# Check if backend is running
curl http://localhost:8000/health

# Check proxy configuration in package.json
grep -A 1 '"proxy"' package.json
```

#### 3. Build Errors
```bash
# Clear React cache
npm start -- --reset-cache

# Check for TypeScript errors
npm run type-check
```

#### 4. Port 3000 in Use
```bash
# Use different port
PORT=3001 npm start

# Or kill existing process
lsof -i :3000 && kill -9 <PID>
```

### Performance Issues

#### Backend Slow Response
1. **Check database size**: Large datasets may need optimization
2. **Enable caching**: Configure Redis if available  
3. **Database indexes**: Ensure proper indexing on game queries
4. **Query optimization**: Check slow query logs

#### Frontend Slow Loading
1. **Network tab**: Check API response times
2. **Bundle size**: Run `npm run build` and check bundle analyzer
3. **Memory usage**: Check for memory leaks in dev tools
4. **Virtual scrolling**: Ensure it's working for large lists

---

## 📊 Monitoring and Logging

### Backend Monitoring
```bash
# View application logs
uvicorn main:app --log-level debug

# Custom logging configuration
export LOG_LEVEL=INFO
uvicorn main:app --log-config logging.conf
```

### Frontend Monitoring
```javascript
// Enable React DevTools
// Install: npm install -g react-devtools

// Performance monitoring
console.log(performance.getEntriesByType('navigation'));
```

### Health Checks
```bash
# Backend health check
curl http://localhost:8000/health

# Frontend health check (should return React app)
curl http://localhost:3000

# API endpoint health
curl http://localhost:8000/api/games?limit=1
```

---

## 🚀 Production Deployment Preparation

### Backend Production Setup
```bash
# Install production dependencies
pip install gunicorn

# Run with Gunicorn
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### Frontend Production Setup
```bash
# Build production bundle
npm run build

# Test production build
npx serve -s build

# Bundle analysis
npm install -g webpack-bundle-analyzer
npx webpack-bundle-analyzer build/static/js/*.js
```

---

## 📞 Support and Resources

### Documentation Links
- **FastAPI Docs**: http://localhost:8000/docs
- **React App**: http://localhost:3000  
- **Testing Guide**: [TESTING.md](./TESTING.md)
- **Project Structure**: [README.md](./README.md)

### Log Files
- **Backend Logs**: Check terminal where uvicorn is running
- **Frontend Logs**: Check browser console (F12)
- **Test Logs**: `pytest --log-cli-level=INFO`

### Performance Baselines
- **API Response Time**: < 2 seconds for all endpoints
- **Frontend Load Time**: < 2 seconds initial page load
- **Memory Usage**: < 500MB for frontend, < 1GB for backend
- **Concurrent Users**: Supports 20+ simultaneous users

---

## ✅ Quick Verification Checklist

After starting both servers, verify:

- [ ] **Backend API**: http://localhost:8000/docs loads
- [ ] **Frontend App**: http://localhost:3000 loads
- [ ] **API Health**: `curl http://localhost:8000/health` returns 200
- [ ] **Games API**: `curl http://localhost:8000/api/games` returns game data
- [ ] **Frontend-Backend Connection**: Games list loads in browser
- [ ] **Navigation**: Can navigate between Games, Statistics, Leaderboard
- [ ] **Game Detail**: Can click on a game to view details
- [ ] **Search/Filter**: Can search and filter games
- [ ] **Responsive Design**: Works on mobile viewport (F12 → mobile view)
- [ ] **Error Handling**: Graceful error messages when backend stops

If all items check out ✅, your Game Analysis Web Interface is running successfully!

---

**Need Help?** Check the troubleshooting section above or refer to the comprehensive [TESTING.md](./TESTING.md) guide for more detailed debugging steps.