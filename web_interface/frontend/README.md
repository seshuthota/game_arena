# Game Analysis Web Interface - Frontend

A React-based web interface for analyzing LLM vs LLM chess games with comprehensive statistics and visualization capabilities.

## Features

- **Game Analysis**: Browse and analyze completed games with detailed move-by-move breakdowns
- **Performance Statistics**: View comprehensive statistics and trends across all games and players  
- **Player Leaderboard**: Compare player performance with rankings, win rates, and detailed metrics
- **Responsive Design**: Optimized for desktop, tablet, and mobile devices
- **Real-time Data**: Live updates with React Query caching and API integration

## Technology Stack

- **React 18** with TypeScript for type-safe component development
- **React Router v6** for client-side routing
- **React Query (TanStack Query)** for data fetching, caching, and synchronization
- **Axios** for HTTP client with interceptors and error handling
- **Styled JSX** for component-scoped CSS styling
- **Jest & React Testing Library** for unit and integration testing

## Getting Started

### Prerequisites

- Node.js 18+ and npm/yarn
- Backend API server running on `http://localhost:8000`

### Installation

```bash
# Install dependencies
npm install

# Start development server
npm start
```

The application will open at `http://localhost:3000` and proxy API requests to `http://localhost:8000`.

### Available Scripts

- `npm start` - Start development server
- `npm build` - Build production bundle
- `npm test` - Run test suite
- `npm run lint` - Run ESLint
- `npm run type-check` - Run TypeScript compiler check

## Project Structure

```
src/
├── components/          # Reusable UI components
│   ├── Header.tsx
│   ├── Footer.tsx
│   ├── Layout.tsx
│   └── AppRoutes.tsx
├── pages/              # Page components
│   ├── Dashboard.tsx
│   ├── Games.tsx
│   ├── Statistics.tsx
│   └── Leaderboard.tsx
├── services/           # API services
│   └── api.ts
├── hooks/              # Custom React hooks
│   └── useApi.ts
├── types/              # TypeScript type definitions
│   └── api.ts
├── utils/              # Utility functions and constants
│   └── constants.ts
└── App.tsx             # Main application component
```

## API Integration

The frontend communicates with the FastAPI backend through a comprehensive API client:

- **Games API**: List games, get game details, search and filter
- **Statistics API**: Overview statistics, time-series data
- **Leaderboard API**: Player rankings and individual player statistics
- **Search API**: Search games and players

All API calls are wrapped with React Query for:
- Automatic caching and background updates
- Loading and error states
- Retry logic with exponential backoff
- Optimistic updates where applicable

## Configuration

Environment variables (`.env.development`):
- `REACT_APP_API_BASE_URL` - Backend API URL
- `REACT_APP_ENABLE_DEBUG` - Enable debug features
- `REACT_APP_ENABLE_QUERY_DEVTOOLS` - Enable React Query DevTools

## Development Roadmap

- ✅ **Task 5**: Basic React setup with routing and API client
- 🔄 **Task 6**: Game list and filtering interface
- 📋 **Task 7**: Game detail view with move analysis
- 📋 **Task 8**: Statistics dashboard with charts
- 📋 **Task 9**: Leaderboard interface
- 📋 **Task 10**: Performance optimizations
- 📋 **Task 11**: Error handling and user feedback
- 📋 **Task 12**: Mobile optimization

## Contributing

1. Follow TypeScript strict mode guidelines
2. Use React functional components with hooks
3. Implement responsive design with mobile-first approach
4. Write tests for components and API interactions
5. Follow ESLint configuration for code style consistency