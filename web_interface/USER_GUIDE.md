# Game Analysis Web Interface - User Guide

Welcome to the Game Analysis Web Interface! This comprehensive guide will help you navigate and use all the features of the web interface for analyzing games stored in the game-data-storage system.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Interface Overview](#interface-overview)
3. [Game List View](#game-list-view)
4. [Game Detail Analysis](#game-detail-analysis)
5. [Statistics Dashboard](#statistics-dashboard)
6. [Leaderboard](#leaderboard)
7. [Search and Filtering](#search-and-filtering)
8. [Keyboard Shortcuts](#keyboard-shortcuts)
9. [Advanced Features](#advanced-features)
10. [Mobile Usage](#mobile-usage)
11. [Troubleshooting](#troubleshooting)

---

## Getting Started

### Accessing the Interface

1. **Open your web browser** and navigate to: `http://localhost:3000`
2. **Wait for the interface to load** - you should see the main dashboard
3. **Verify connection** - if you see game data, you're ready to go!

### First Steps

1. **Explore the navigation** - Use the top navigation bar to switch between views
2. **Try the search** - Use the search bar to find specific games
3. **Browse games** - Click on any game in the list to see detailed analysis

---

## Interface Overview

### Main Navigation

The interface consists of four main sections accessible from the top navigation:

- **🎯 Games** - Browse and analyze individual games
- **📊 Statistics** - View aggregate statistics and trends
- **🏆 Leaderboard** - See player rankings and performance
- **📈 Dashboard** - Overview of key metrics (home page)

### Layout Components

```
┌─────────────────────────────────────────────────────────────┐
│ Header: Game Arena Analysis | Search Bar | Navigation       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ Main Content Area                                           │
│ ┌─────────────────┐ ┌─────────────────────────────────────┐ │
│ │ Filters/Controls│ │ Content View                        │ │
│ │                 │ │ - Game List / Detail / Stats        │ │
│ │                 │ │ - Interactive Elements              │ │
│ │                 │ │ - Pagination                        │ │
│ └─────────────────┘ └─────────────────────────────────────┘ │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│ Footer: Status Information                                  │
└─────────────────────────────────────────────────────────────┘
```

---

## Game List View

### Overview

The Games section displays a comprehensive list of all games in your database with powerful filtering and search capabilities.

### Game List Features

#### Game Information Display
Each game entry shows:
- **Game ID** (shortened for display, full ID available in details)
- **Players** - White and Black player information
- **Models** - AI models used by each player
- **Game Result** - Winner and termination reason
- **Duration** - How long the game lasted
- **Move Count** - Total number of moves
- **Start Time** - When the game began

#### Sorting Options
Click on column headers to sort by:
- **Start Time** (newest/oldest first)
- **Duration** (shortest/longest first)
- **Move Count** (fewest/most moves)
- **Player Names** (alphabetical)

#### Pagination
- **Page Navigation** - Use the pagination controls at the bottom
- **Items Per Page** - Choose 10, 25, 50, or 100 games per page
- **Quick Navigation** - Jump to first/last page with arrow buttons

### Using the Game List

1. **Browse Games**
   - Scroll through the list to see all available games
   - Use pagination to navigate through large datasets

2. **Sort Games**
   - Click any column header to sort by that field
   - Click again to reverse the sort order
   - Look for the sort indicator (▲▼) next to column names

3. **View Game Details**
   - Click on any game row to open the detailed analysis view
   - Use the browser back button or breadcrumb to return to the list

---

## Game Detail Analysis

### Overview

The Game Detail view provides comprehensive analysis of individual games, including complete move history, player information, and interactive move exploration.

### Game Header Information

#### Game Metadata
- **Game ID** - Full unique identifier
- **Tournament ID** - If part of a tournament
- **Players** - Detailed information about White and Black players
- **Game Result** - Final outcome and termination reason
- **Timing** - Start time, end time, and total duration
- **Move Statistics** - Total moves and game status

#### Player Cards
Each player card displays:
- **Color** - White (⚪) or Black (⚫)
- **Model Name** - AI model used (e.g., gpt-4, claude-3)
- **Provider** - Model provider (OpenAI, Anthropic, etc.)
- **Agent Type** - Type of game-playing agent
- **ELO Rating** - Player's rating (if available)

### Move History Analysis

#### Move List Features
- **Chronological Display** - All moves shown in order
- **Move Numbers** - Standard chess notation (1., 1..., 2., 2...)
- **Player Indicators** - Color indicators for each move
- **Timestamps** - When each move was made
- **Selection** - Click any move to see detailed analysis

#### Move Navigation Controls
Use the navigation buttons to move through the game:
- **⏮ First** - Jump to the first move
- **⏪ Previous** - Go to the previous move
- **⏩ Next** - Go to the next move
- **⏭ Last** - Jump to the last move
- **Move Counter** - Shows current position (e.g., "Move 15 of 44")

#### Keyboard Navigation
- **← Left Arrow** - Previous move
- **→ Right Arrow** - Next move
- **Home** - First move
- **End** - Last move
- **Escape** - Deselect current move

### Move Details Panel

When you select a move, the details panel shows:

#### Move Information
- **Notation** - Chess move in standard algebraic notation
- **Legal Move** - Whether the move was legal (✅/❌)
- **Parsing Success** - Whether the move was parsed correctly
- **Timestamp** - Exact time the move was made

#### Board Positions (FEN)
- **Before Move** - Board position before the move
- **After Move** - Board position after the move
- **Copy Button** - Copy FEN notation to clipboard

#### LLM Response
- **AI Thinking** - The AI's reasoning for the move
- **Response Text** - Complete response from the language model

#### Timing Information
- **Thinking Time** - Time spent analyzing the position
- **API Call Time** - Time for the API request/response
- **Total Time** - Complete time for the move

#### Move Analysis
- **Quality Score** - Numerical assessment of move quality
- **Blunder Flag** - Whether the move was identified as a blunder
- **Rethink Information** - If the AI reconsidered the move

### Using Game Detail View

1. **Navigate to a Game**
   - Click on any game from the Games list
   - Or use a direct game URL

2. **Explore Move History**
   - Use keyboard arrows or navigation buttons
   - Click on specific moves in the list
   - Review the detailed analysis in the side panel

3. **Analyze Positions**
   - Copy FEN positions to analyze in external tools
   - Review AI reasoning for each move
   - Check timing and quality metrics

---

## Statistics Dashboard

### Overview

The Statistics section provides comprehensive analytics and insights across all games in your database.

### Overview Metrics

#### Key Statistics Cards
- **Total Games** - Number of games in the database
- **Total Players** - Unique players/models
- **Average Duration** - Mean game length
- **Win Rate Distribution** - Breakdown by game results

#### Game Result Analysis
- **White Wins** - Games won by White
- **Black Wins** - Games won by Black
- **Draws** - Games ending in a draw
- **Ongoing** - Games still in progress

### Time Series Analysis

#### Games Over Time
- **Daily Activity** - Games played each day
- **Weekly Trends** - Weekly game volume
- **Monthly Patterns** - Long-term activity trends

#### Interactive Charts
- **Zoom** - Click and drag to zoom into time periods
- **Hover** - Hover over data points for exact values
- **Legend** - Click legend items to show/hide data series

### Model Performance

#### Win Rate by Model
- **Model Comparison** - Performance across different AI models
- **Provider Analysis** - Statistics by model provider
- **Head-to-Head** - Direct comparisons between models

### Using Statistics

1. **View Overview**
   - Check the main statistics cards for quick insights
   - Compare different metrics side by side

2. **Analyze Trends**
   - Use time series charts to identify patterns
   - Look for seasonal or periodic trends

3. **Compare Models**
   - Review win rates across different AI models
   - Identify top-performing models and providers

---

## Leaderboard

### Overview

The Leaderboard ranks players by various performance metrics and provides detailed player statistics.

### Ranking Metrics

#### Default Rankings
- **Win Rate** - Percentage of games won
- **Games Played** - Total number of games
- **ELO Rating** - Chess rating system (if available)
- **Average Game Length** - Mean duration of games

#### Player Information
Each leaderboard entry shows:
- **Rank** - Current position in the leaderboard
- **Player/Model Name** - Identifier for the player
- **Games Played** - Total game count
- **Wins/Losses/Draws** - Game results breakdown
- **Win Percentage** - Success rate
- **Average Duration** - Mean game length

### Filtering Options

#### Game Type Filters
- **All Games** - Include all game types
- **Tournament Games** - Only tournament games
- **Casual Games** - Non-tournament games

#### Time Period Filters
- **All Time** - Complete history
- **Last 30 Days** - Recent performance
- **Last 7 Days** - Very recent activity
- **Custom Range** - Specify exact date range

### Using the Leaderboard

1. **View Rankings**
   - Browse the default win rate rankings
   - Check different sorting options

2. **Filter Results**
   - Use time period filters to see recent performance
   - Filter by game type for specific analysis

3. **Player Details**
   - Click on any player to see detailed statistics
   - Compare performance across different metrics

---

## Search and Filtering

### Overview

Powerful search and filtering capabilities help you find specific games and analyze subsets of your data.

### Search Functionality

#### Global Search Bar
Located at the top of the interface, the search bar finds:
- **Player Names** - Search by model names or identifiers
- **Game IDs** - Find specific games by ID
- **Tournament IDs** - Locate tournament games

#### Search Features
- **Real-time Results** - Results update as you type
- **Fuzzy Matching** - Finds partial matches
- **Clear Button** - Quickly clear search terms

### Advanced Filtering

#### Filter Panel
Click the "Filters" button to access advanced filtering options:

#### Player Filters
- **Player IDs** - Comma-separated list of player identifiers
- **Model Names** - Filter by specific AI models
- **Model Providers** - Filter by provider (OpenAI, Anthropic, etc.)

#### Date Range Filters
- **Start Date** - Games after this date
- **End Date** - Games before this date
- **Date Picker** - Visual calendar selection

#### Game Result Filters
Select specific outcomes:
- **White Wins** - Games won by White
- **Black Wins** - Games won by Black
- **Draws** - Drawn games
- **Ongoing** - Games in progress

#### Game Metrics Filters
- **Move Count Range** - Minimum and maximum moves
- **Duration Range** - Game length in minutes
- **Numeric Inputs** - Precise value specification

#### Termination Reason Filters
Filter by how games ended:
- **Checkmate** - Games ending in checkmate
- **Resignation** - Player resigned
- **Timeout** - Time control violations
- **Draw Agreement** - Mutual draw
- **Stalemate** - Stalemate position

### Using Search and Filters

1. **Quick Search**
   - Type in the search bar for immediate results
   - Use partial names or IDs

2. **Advanced Filtering**
   - Click "Filters" to open the filter panel
   - Select multiple criteria
   - Click "Apply Filters" to update results

3. **Clear Filters**
   - Use "Clear All" to remove all filters
   - Individual filter fields can be cleared separately

---

## Keyboard Shortcuts

### Global Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl + /` | Focus search bar |
| `Ctrl + F` | Open filters panel |
| `Esc` | Close modals/panels |

### Game List Navigation

| Shortcut | Action |
|----------|--------|
| `↑` / `↓` | Navigate between games |
| `Enter` | Open selected game |
| `Page Up` / `Page Down` | Navigate pages |

### Game Detail View

| Shortcut | Action |
|----------|--------|
| `←` | Previous move |
| `→` | Next move |
| `Home` | First move |
| `End` | Last move |
| `Esc` | Deselect move |
| `Space` | Toggle move selection |

### Statistics View

| Shortcut | Action |
|----------|--------|
| `R` | Refresh data |
| `T` | Toggle time period |
| `M` | Switch metric view |

---

## Advanced Features

### Data Export

#### Export Options
- **CSV Export** - Game data in spreadsheet format
- **JSON Export** - Raw data for analysis
- **Filtered Exports** - Export only filtered results

#### Export Process
1. Apply desired filters
2. Click the export button
3. Choose format (CSV/JSON)
4. Download begins automatically

### URL Sharing

#### Shareable Links
- **Game Links** - Direct links to specific games
- **Filtered Views** - Share filtered game lists
- **Statistics Views** - Share specific chart configurations

#### Creating Shareable Links
1. Navigate to desired view
2. Apply filters or select game
3. Copy URL from browser address bar
4. Share with others

### Performance Optimization

#### Virtual Scrolling
- **Large Lists** - Efficiently handles thousands of games
- **Smooth Scrolling** - Maintains performance with large datasets
- **Memory Management** - Optimized memory usage

#### Caching
- **API Responses** - Cached for faster loading
- **Smart Refresh** - Updates only when necessary
- **Offline Capability** - Limited functionality when offline

### Real-time Updates

#### Live Data
- **New Games** - Automatically appear in lists
- **Status Updates** - Game completion updates
- **Statistics Refresh** - Metrics update automatically

---

## Mobile Usage

### Responsive Design

The interface automatically adapts to different screen sizes:

#### Mobile Layout (< 768px)
- **Stacked Layout** - Vertical arrangement of components
- **Drawer Navigation** - Slide-out menu for navigation
- **Touch Optimization** - Larger touch targets
- **Simplified Views** - Reduced information density

#### Tablet Layout (768px - 1199px)
- **Collapsible Sidebar** - Expandable filter panel
- **Adaptive Grid** - Flexible column layouts
- **Touch-Friendly** - Optimized for touch interaction

### Mobile-Specific Features

#### Touch Gestures
- **Swipe Navigation** - Swipe between moves in game detail
- **Pull to Refresh** - Refresh data with pull gesture
- **Pinch to Zoom** - Zoom charts and diagrams

#### Mobile Navigation
- **Bottom Navigation** - Easy thumb access
- **Hamburger Menu** - Compact navigation option
- **Back Button** - Browser back button support

### Mobile Usage Tips

1. **Portrait Mode** - Optimized for portrait orientation
2. **Landscape Support** - Works in landscape for charts
3. **Zoom Support** - Pinch to zoom on detailed content
4. **Offline Viewing** - Limited functionality when offline

---

## Troubleshooting

### Common Issues

#### Interface Won't Load
**Symptoms:** Blank page or loading spinner
**Solutions:**
1. Check that backend server is running (`http://localhost:8000`)
2. Verify network connection
3. Clear browser cache and cookies
4. Try a different browser

#### No Game Data Visible
**Symptoms:** Empty game list or "No games found"
**Solutions:**
1. Verify database contains game data
2. Check API connection (`http://localhost:8000/api/games`)
3. Clear all filters
4. Refresh the page

#### Slow Performance
**Symptoms:** Slow loading, laggy interactions
**Solutions:**
1. Check system resources (RAM, CPU)
2. Close other browser tabs
3. Reduce page size (use fewer items per page)
4. Clear browser cache

#### Search Not Working
**Symptoms:** Search returns no results
**Solutions:**
1. Check spelling and try partial terms
2. Clear search and try again
3. Verify data exists for search terms
4. Try different search criteria

### Error Messages

#### "Failed to load game"
- **Cause:** Game not found or API error
- **Solution:** Check game ID, refresh page, verify backend

#### "Network Error"
- **Cause:** Backend server not responding
- **Solution:** Restart backend server, check network connection

#### "Invalid Filter Parameters"
- **Cause:** Incorrect filter values
- **Solution:** Clear filters, use valid date formats

### Getting Help

#### Debug Information
To help with troubleshooting:
1. **Browser Console** - Press F12, check Console tab
2. **Network Tab** - Check for failed API requests
3. **Error Messages** - Note exact error text
4. **Browser Version** - Include browser and version info

#### Support Resources
- **API Documentation:** `http://localhost:8000/docs`
- **Backend Logs:** Check terminal where backend is running
- **Frontend Logs:** Browser developer console

---

## Tips for Power Users

### Efficient Workflows

#### Game Analysis Workflow
1. **Filter by criteria** (date range, players, etc.)
2. **Sort by relevance** (duration, moves, etc.)
3. **Open interesting games** in new tabs
4. **Use keyboard shortcuts** for navigation
5. **Export data** for external analysis

#### Statistical Analysis Workflow
1. **Start with overview** statistics
2. **Drill down** into specific metrics
3. **Use time filters** to identify trends
4. **Compare models** side by side
5. **Export charts** for presentations

### Advanced Search Techniques

#### Complex Filters
- **Combine multiple criteria** for precise results
- **Use date ranges** to analyze specific periods
- **Filter by termination** to study game endings
- **Combine player and model filters** for head-to-head analysis

#### Search Operators
- **Partial matching** - Use partial names or IDs
- **Case insensitive** - Search is not case sensitive
- **Multiple terms** - Space-separated terms work as AND

### Data Analysis Tips

#### Identifying Patterns
- **Look for trends** in time series data
- **Compare win rates** across different models
- **Analyze game lengths** by termination type
- **Study move timing** patterns

#### Performance Analysis
- **Track model improvements** over time
- **Identify problematic positions** through move analysis
- **Compare thinking times** across models
- **Analyze blunder patterns**

---

## Conclusion

The Game Analysis Web Interface provides powerful tools for analyzing chess games and AI performance. Whether you're researching AI behavior, comparing models, or studying specific games, the interface offers the flexibility and depth needed for comprehensive analysis.

### Key Takeaways

1. **Navigation** - Use the main navigation to switch between views
2. **Search & Filter** - Powerful tools to find specific data
3. **Game Analysis** - Detailed move-by-move analysis with AI insights
4. **Statistics** - Comprehensive metrics and trend analysis
5. **Keyboard Shortcuts** - Efficient navigation for power users
6. **Mobile Support** - Full functionality on all devices

### Next Steps

1. **Explore the interface** - Try all the different views and features
2. **Analyze your data** - Use filters to find interesting patterns
3. **Share insights** - Use URL sharing to collaborate with others
4. **Export data** - Take your analysis to external tools
5. **Provide feedback** - Help improve the interface with your suggestions

Happy analyzing! 🎯♟️📊
--
-

## Appendix A: Complete Keyboard Shortcuts Reference

### Global Application Shortcuts

| Shortcut | Action | Context |
|----------|--------|---------|
| `Ctrl + /` | Focus search bar | Any page |
| `Ctrl + K` | Open command palette | Any page |
| `Ctrl + F` | Open filters panel | Game list |
| `Ctrl + R` | Refresh current view | Any page |
| `Ctrl + H` | Go to home/dashboard | Any page |
| `Ctrl + G` | Go to games list | Any page |
| `Ctrl + S` | Go to statistics | Any page |
| `Ctrl + L` | Go to leaderboard | Any page |
| `Esc` | Close modals/panels | Any page |
| `F1` | Open help/documentation | Any page |
| `F5` | Hard refresh page | Any page |

### Game List Navigation

| Shortcut | Action | Description |
|----------|--------|-------------|
| `↑` / `↓` | Navigate between games | Move selection up/down |
| `Enter` | Open selected game | View game details |
| `Space` | Toggle game selection | Multi-select mode |
| `Ctrl + A` | Select all visible games | Bulk operations |
| `Delete` | Remove from selection | Multi-select mode |
| `Page Up` / `Page Down` | Navigate pages | Jump between pages |
| `Home` / `End` | First/last page | Quick navigation |
| `Ctrl + ↑` / `Ctrl + ↓` | Sort by column | Change sort order |
| `Tab` | Navigate between controls | Accessibility |
| `Shift + Tab` | Reverse tab navigation | Accessibility |

### Game Detail View Navigation

| Shortcut | Action | Description |
|----------|--------|-------------|
| `←` / `→` | Previous/next move | Move navigation |
| `Shift + ←` / `Shift + →` | Jump 5 moves | Fast navigation |
| `Ctrl + ←` / `Ctrl + →` | Jump 10 moves | Very fast navigation |
| `Home` / `End` | First/last move | Jump to extremes |
| `Space` | Play/pause auto-play | Automatic move progression |
| `+` / `-` | Speed up/slow down | Auto-play speed |
| `Enter` | Select current move | Show move details |
| `Esc` | Deselect move | Hide move details |
| `C` | Copy current FEN | Clipboard operation |
| `M` | Toggle move list | Show/hide moves |
| `D` | Toggle details panel | Show/hide analysis |
| `F` | Toggle fullscreen | Immersive mode |

### Statistics View Shortcuts

| Shortcut | Action | Description |
|----------|--------|-------------|
| `R` | Refresh statistics | Update data |
| `T` | Toggle time period | Switch time range |
| `M` | Switch metric view | Change displayed metric |
| `E` | Export current view | Download data |
| `Z` | Zoom chart | Chart interaction |
| `Ctrl + Z` | Reset zoom | Chart reset |
| `1-9` | Quick time filters | Predefined ranges |
| `Shift + 1-9` | Quick metric filters | Predefined metrics |

### Leaderboard Shortcuts

| Shortcut | Action | Description |
|----------|--------|-------------|
| `S` | Change sort criteria | Cycle through options |
| `F` | Apply filters | Open filter menu |
| `P` | View player profile | Selected player |
| `C` | Compare players | Multi-select mode |
| `E` | Export leaderboard | Download rankings |
| `1-8` | Sort by rank column | Quick sort options |

### Filter Panel Shortcuts

| Shortcut | Action | Description |
|----------|--------|-------------|
| `Ctrl + Enter` | Apply filters | Execute filter |
| `Ctrl + Backspace` | Clear all filters | Reset filters |
| `Tab` | Navigate filter fields | Move between inputs |
| `Shift + Tab` | Reverse navigation | Previous field |
| `Enter` | Apply current filter | Single filter |
| `Esc` | Cancel filter changes | Revert changes |
| `Ctrl + D` | Duplicate last filter | Repeat filter |
| `Alt + 1-9` | Quick filter presets | Predefined filters |

### Advanced Power User Shortcuts

| Shortcut | Action | Description |
|----------|--------|-------------|
| `Ctrl + Shift + D` | Developer tools | Debug mode |
| `Ctrl + Shift + R` | Force refresh | Clear cache |
| `Ctrl + Shift + I` | Inspect element | Browser dev tools |
| `Ctrl + Shift + C` | Copy debug info | Support information |
| `Ctrl + Shift + E` | Export all data | Bulk export |
| `Ctrl + Shift + L` | Toggle logs | Show/hide logs |
| `Ctrl + Alt + R` | Reset application | Clear all data |
| `Ctrl + Alt + T` | Toggle theme | Light/dark mode |

---

## Appendix B: Advanced Power User Features

### URL Parameters and Deep Linking

#### Game List URLs
```
# Filter by date range
/games?start_date=2024-01-01&end_date=2024-01-31

# Filter by players
/games?player_ids=gpt-4,claude-3&results=white_wins

# Sort and paginate
/games?sort_by=duration&page=2&limit=50

# Complex filters
/games?model_names=gpt-4&min_moves=50&termination_reasons=checkmate
```

#### Game Detail URLs
```
# Direct game access
/games/abc123def456789

# Game with specific move
/games/abc123def456789?move=23

# Game with analysis panel
/games/abc123def456789?move=23&details=true
```

#### Statistics URLs
```
# Specific time range
/statistics?start_date=2024-01-01&end_date=2024-01-31

# Specific metrics
/statistics?metrics=win_rate,avg_duration&models=gpt-4,claude-3

# Chart configuration
/statistics?chart=time_series&interval=daily&metric=games_count
```

### Browser Local Storage Usage

#### Stored Preferences
- **Theme Settings** - Light/dark mode preference
- **Filter Presets** - Saved filter combinations
- **View Preferences** - Column widths, sort orders
- **Recent Searches** - Search history
- **Pagination Settings** - Items per page preference

#### Accessing Stored Data
```javascript
// View stored preferences
console.log(localStorage.getItem('gameAnalysis_preferences'));

// Clear all stored data
localStorage.clear();

// Export preferences
const prefs = JSON.parse(localStorage.getItem('gameAnalysis_preferences'));
console.log(JSON.stringify(prefs, null, 2));
```

### Advanced Search Techniques

#### Search Operators
```
# Exact phrase matching
"gpt-4 vs claude-3"

# Wildcard matching
gpt-* (matches gpt-4, gpt-3.5, etc.)

# Date range searches
date:2024-01-01..2024-01-31

# Numeric range searches
moves:50..100
duration:30..60

# Boolean operators
gpt-4 AND checkmate
claude OR anthropic
NOT timeout
```

#### Complex Filter Combinations
```
# High-quality long games
min_moves=80 AND min_duration=45 AND NOT termination_reasons=timeout

# Model comparison
(model_names=gpt-4 OR model_names=claude-3) AND results=white_wins

# Tournament analysis
tournament_id=* AND start_date=2024-01-01 AND end_date=2024-01-31
```

### Data Export and Analysis

#### Export Formats
- **CSV** - Spreadsheet-compatible format
- **JSON** - Raw data for programming
- **XML** - Structured data format
- **PDF** - Formatted reports

#### Export Options
```javascript
// Export filtered game list
/api/games/export?format=csv&filters={...}

# Export game details with moves
/api/games/{id}/export?format=json&include_moves=true

# Export statistics
/api/statistics/export?format=csv&metrics=all&time_range=30d

# Export leaderboard
/api/leaderboard/export?format=pdf&sort_by=win_rate&limit=50
```

### Performance Optimization Tips

#### For Large Datasets
1. **Use Pagination** - Keep page sizes reasonable (25-50 items)
2. **Apply Filters** - Narrow down results before viewing
3. **Sort Efficiently** - Use indexed columns for sorting
4. **Cache Results** - Browser caches frequently accessed data
5. **Limit Time Ranges** - Use specific date ranges for better performance

#### Browser Optimization
1. **Close Unused Tabs** - Free up memory
2. **Clear Cache** - Refresh cached data periodically
3. **Update Browser** - Use latest browser versions
4. **Disable Extensions** - Reduce browser overhead
5. **Monitor Memory** - Check browser task manager

### API Integration for Developers

#### Direct API Access
```bash
# Get games with curl
curl "http://localhost:8000/api/games?limit=10" | jq

# Get game details
curl "http://localhost:8000/api/games/abc123def456" | jq

# Get statistics
curl "http://localhost:8000/api/statistics/overview" | jq

# Search games
curl "http://localhost:8000/api/search/games?query=gpt-4" | jq
```

#### JavaScript API Client
```javascript
// Custom API client
class GameAnalysisAPI {
  constructor(baseURL = 'http://localhost:8000/api') {
    this.baseURL = baseURL;
  }
  
  async getGames(params = {}) {
    const url = new URL(`${this.baseURL}/games`);
    Object.entries(params).forEach(([key, value]) => {
      url.searchParams.append(key, value);
    });
    
    const response = await fetch(url);
    return response.json();
  }
  
  async getGame(gameId) {
    const response = await fetch(`${this.baseURL}/games/${gameId}`);
    return response.json();
  }
  
  async getStatistics(params = {}) {
    const url = new URL(`${this.baseURL}/statistics/overview`);
    Object.entries(params).forEach(([key, value]) => {
      url.searchParams.append(key, value);
    });
    
    const response = await fetch(url);
    return response.json();
  }
}

// Usage example
const api = new GameAnalysisAPI();
const games = await api.getGames({ limit: 10, sort_by: 'start_time' });
console.log(games);
```

### Custom Styling and Themes

#### CSS Custom Properties
```css
/* Override default theme colors */
:root {
  --primary-color: #your-brand-color;
  --secondary-color: #your-secondary-color;
  --background-color: #your-background;
  --text-color: #your-text-color;
  --border-color: #your-border-color;
}
```

#### Dark Mode Support
```css
/* Dark mode overrides */
@media (prefers-color-scheme: dark) {
  :root {
    --background-color: #1a1a1a;
    --text-color: #ffffff;
    --border-color: #333333;
  }
}
```

### Automation and Scripting

#### Browser Automation
```javascript
// Puppeteer script for automated analysis
const puppeteer = require('puppeteer');

async function analyzeGames() {
  const browser = await puppeteer.launch();
  const page = await browser.newPage();
  
  await page.goto('http://localhost:3000/games');
  
  // Apply filters
  await page.click('[data-testid="filter-toggle"]');
  await page.type('[data-testid="player-filter"]', 'gpt-4');
  await page.click('[data-testid="apply-filters"]');
  
  // Extract game data
  const games = await page.evaluate(() => {
    return Array.from(document.querySelectorAll('[data-testid="game-row"]'))
      .map(row => ({
        id: row.dataset.gameId,
        players: row.querySelector('.players').textContent,
        result: row.querySelector('.result').textContent
      }));
  });
  
  console.log('Found games:', games);
  await browser.close();
}
```

#### Data Analysis Scripts
```python
# Python script for advanced analysis
import requests
import pandas as pd
import matplotlib.pyplot as plt

# Fetch game data
response = requests.get('http://localhost:8000/api/games?limit=1000')
games = response.json()['games']

# Convert to DataFrame
df = pd.DataFrame(games)

# Analyze win rates by model
win_rates = df.groupby('model_name').agg({
    'result': lambda x: (x == 'white_wins').mean()
}).round(3)

# Create visualization
win_rates.plot(kind='bar', title='Win Rates by Model')
plt.ylabel('Win Rate')
plt.xlabel('Model')
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig('win_rates.png')
plt.show()
```

---

## Appendix C: Troubleshooting Advanced Issues

### Performance Issues

#### Slow Loading Times
**Symptoms:** Pages take more than 5 seconds to load
**Diagnosis:**
1. Check network tab in browser dev tools
2. Look for slow API responses (>2 seconds)
3. Check for large bundle sizes
4. Monitor memory usage

**Solutions:**
1. Reduce page size (use fewer items per page)
2. Apply more specific filters
3. Clear browser cache and cookies
4. Restart backend server
5. Check database performance

#### Memory Leaks
**Symptoms:** Browser becomes slow over time, high memory usage
**Diagnosis:**
1. Open browser task manager (Shift+Esc in Chrome)
2. Monitor memory usage over time
3. Check for increasing memory consumption

**Solutions:**
1. Refresh the page periodically
2. Close unused browser tabs
3. Disable browser extensions
4. Use incognito/private browsing mode

### Data Synchronization Issues

#### Stale Data
**Symptoms:** Data doesn't update, shows old information
**Diagnosis:**
1. Check if backend is running
2. Verify API responses in network tab
3. Check browser cache settings

**Solutions:**
1. Hard refresh (Ctrl+Shift+R)
2. Clear browser cache
3. Check cache headers in API responses
4. Restart backend server

#### Missing Data
**Symptoms:** Expected games/data not showing
**Diagnosis:**
1. Check database for data existence
2. Verify API filters and parameters
3. Check for API errors in console

**Solutions:**
1. Verify data exists in database
2. Clear all filters
3. Check API endpoint directly
4. Restart storage services

### Browser Compatibility Issues

#### Feature Not Working
**Symptoms:** Specific features don't work in certain browsers
**Diagnosis:**
1. Check browser version and compatibility
2. Look for JavaScript errors in console
3. Test in different browsers

**Solutions:**
1. Update browser to latest version
2. Enable JavaScript if disabled
3. Clear browser data
4. Try different browser

#### Display Issues
**Symptoms:** Layout broken, elements misaligned
**Diagnosis:**
1. Check CSS support in browser
2. Look for CSS errors in dev tools
3. Test responsive design

**Solutions:**
1. Update browser
2. Reset zoom level (Ctrl+0)
3. Clear CSS cache
4. Check viewport settings

### API Integration Issues

#### CORS Errors
**Symptoms:** "Cross-origin request blocked" errors
**Diagnosis:**
1. Check browser console for CORS errors
2. Verify API server CORS configuration
3. Check request headers

**Solutions:**
1. Configure CORS in backend
2. Use proper API endpoints
3. Check request methods and headers

#### Authentication Issues
**Symptoms:** 401/403 errors, access denied
**Diagnosis:**
1. Check API authentication requirements
2. Verify credentials and tokens
3. Check request headers

**Solutions:**
1. Refresh authentication tokens
2. Check API key configuration
3. Verify user permissions

---

This comprehensive appendix provides advanced features, troubleshooting guides, and power user capabilities for the Game Analysis Web Interface.