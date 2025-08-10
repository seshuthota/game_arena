# Frequently Asked Questions (FAQ)

## General Questions

### Q1: What is Game Arena?
**A:** Game Arena is a comprehensive chess analysis platform that allows you to analyze games between different AI models (LLMs). It provides interactive chess boards, detailed statistics, ELO ratings, and performance analytics to understand how different AI systems play chess.

### Q2: Which AI models are supported?
**A:** Game Arena supports games from major AI providers including:
- **OpenAI**: GPT-4, GPT-4 Turbo, o1, o3-mini
- **Anthropic**: Claude 3.5 Sonnet, Claude 3 Opus, Claude 3 Haiku
- **Google**: Gemini Pro, Gemini Flash, PaLM 2
- **Other providers**: Various models through OpenRouter, TogetherAI, etc.

### Q3: How accurate are the ELO ratings?
**A:** The ELO ratings use a standard chess rating system with a K-factor of 32. They're calculated from actual game results and become more accurate as more games are played. New players start at 1400 ELO, and ratings stabilize after about 10-15 games.

### Q4: Can I add my own games to the system?
**A:** Yes! The system supports PGN file imports. You can upload games in standard PGN format, and the system will automatically analyze them and add them to the database.

## Chess Board Features

### Q5: Why isn't the chess board loading?
**A:** Common causes and solutions:
- **Missing dependencies**: Ensure jQuery and chessboard.js are installed
- **JavaScript errors**: Check the browser console for errors
- **Network issues**: Check if chess piece images can load from the CDN
- **Browser compatibility**: Use a modern browser (Chrome 90+, Firefox 88+, Safari 14+)

### Q6: The chess pieces are invisible - how do I fix this?
**A:** This usually means the piece images aren't loading:
1. Check your internet connection
2. Try refreshing the page
3. Check if the CDN (chessboardjs.com) is accessible from your network
4. Clear your browser cache and reload

### Q7: What do the colored squares mean on the chess board?
**A:** The color coding indicates:
- **Blue squares**: The last move played
- **Yellow squares**: Legal moves for the selected piece
- **Green highlighting**: Excellent moves
- **Red highlighting**: Mistakes or blunders
- **Gold highlighting**: Brilliant moves

### Q8: How do I navigate through a game quickly?
**A:** Use these keyboard shortcuts:
- **←/→ arrows**: Previous/next move
- **Home/End**: Jump to start/end of game
- **Space**: Play/pause automatic playback
- **+/-**: Adjust playback speed
- Click any move in the move list to jump directly to that position

### Q9: Can I analyze games on mobile devices?
**A:** Yes! The chess board is fully responsive and supports:
- Touch navigation (swipe to move through the game)
- Pinch-to-zoom for board sizing
- Portrait and landscape orientations
- Touch-friendly controls

## Statistics and Analysis

### Q10: How are win rates calculated?
**A:** Win rates are calculated as:
- **Win rate**: (Wins) / (Total completed games)
- **Score percentage**: (Wins + 0.5 × Draws) / (Total completed games)
- Only completed games are counted; ongoing games are excluded

### Q11: What does "confidence level" mean in statistics?
**A:** Confidence level indicates data quality:
- **90-100%**: High confidence - complete, validated data
- **70-89%**: Medium confidence - minor gaps or inconsistencies  
- **50-69%**: Low confidence - significant data issues
- **<50%**: Poor confidence - substantial problems

Use the confidence level to understand how reliable the statistics are for a particular player or game.

### Q12: Why do some players have "N/A" for certain statistics?
**A:** This happens when:
- The player hasn't played enough games for meaningful statistics
- Data is incomplete or missing for those games
- The statistic requires specific data that isn't available
- The calculation failed due to data quality issues

### Q13: How often are statistics updated?
**A:** Statistics are updated:
- **Real-time**: When viewing individual games or players
- **Cached updates**: Leaderboard updates every 10 minutes
- **Batch updates**: Heavy calculations run every few hours
- **Manual refresh**: You can force updates using the refresh button

### Q14: What's the difference between ELO rating and win rate?
**A:** 
- **ELO rating**: Considers the strength of opponents faced (beating stronger players gives more points)
- **Win rate**: Simple percentage of games won, regardless of opponent strength
- ELO rating is generally more accurate for measuring true playing strength

## Data and Performance

### Q15: Why are some games missing moves or positions?
**A:** This can happen due to:
- **Import errors**: Issues when importing PGN files
- **Network interruptions**: Connection lost during game recording
- **Data corruption**: File or database corruption
- **Format issues**: Non-standard PGN formatting

The system provides recovery options like skipping to valid positions or using estimated data.

### Q16: The interface is running slowly - how can I improve performance?
**A:** Try these optimizations:
- **Close unused tabs**: Free up browser memory
- **Use filters**: Narrow down large datasets
- **Enable hardware acceleration**: In your browser settings
- **Clear browser cache**: Remove temporary files
- **Use a modern browser**: Latest Chrome or Firefox work best

### Q17: How much data can the system handle?
**A:** The system is designed to handle:
- **Games**: Tens of thousands of games
- **Players**: Hundreds of unique players  
- **Concurrent users**: Dozens of simultaneous users
- **Memory usage**: Optimized caching keeps memory usage reasonable

Performance may degrade with extremely large datasets, but the system includes optimization features to maintain responsiveness.

## Technical Issues

### Q18: I'm getting "404 Not Found" errors for API calls. What's wrong?
**A:** Check these potential issues:
- **Backend server**: Ensure the backend is running on the correct port
- **API URL configuration**: Verify the frontend is pointing to the right backend URL
- **Network connectivity**: Test if you can reach the backend directly
- **CORS issues**: Cross-origin requests might be blocked

### Q19: Games aren't appearing after I imported a PGN file. Why?
**A:** Possible causes:
- **PGN format issues**: File may have formatting problems
- **Import still processing**: Large files take time to process
- **Database errors**: Check the server logs for import errors
- **Filtering**: Games might be hidden by current filter settings

### Q20: I'm seeing TypeScript/JavaScript errors in the console. Should I be worried?
**A:** 
- **Minor warnings**: Usually safe to ignore, but report if functionality breaks
- **Error messages**: May indicate real problems - note the exact error and context
- **Performance warnings**: Can indicate optimization opportunities
- **Network errors**: Usually indicate connectivity or server issues

### Q21: Can I run this system offline?
**A:** Partially:
- **Chess analysis**: Works offline once loaded
- **Existing games**: Can be viewed without internet
- **Chess piece images**: Require internet connection (loaded from CDN)
- **New data**: Imports and updates need backend connectivity

## Advanced Features

### Q22: How do I compare two specific players head-to-head?
**A:** 
1. Go to the leaderboard page
2. Use the player filter to select both players
3. Click on either player to see their detailed statistics
4. The head-to-head section will show their matchup record
5. Use the game filters to see only games between those players

### Q23: Can I export statistics or games?
**A:** Current export options include:
- **Game positions**: Copy FEN strings from the chess board
- **Statistics**: Copy data from the statistics tables
- **PGN export**: Available for individual games
- **CSV export**: For leaderboard data (coming in future updates)

### Q24: How do I report bugs or request features?
**A:** You can:
- Use the feedback form in the application
- Report issues through the GitHub repository
- Contact support through the help menu
- Join the community discussion forum

### Q25: Is there an API for accessing the data programmatically?
**A:** Yes! The system provides REST APIs for:
- **Games**: Retrieve game data and filters
- **Players**: Access player statistics and rankings
- **Leaderboards**: Get ranking data with various sorting options
- **Statistics**: Access aggregate statistics and time-series data

See the API documentation for detailed endpoints and usage examples.

## Opening Analysis

### Q26: What do the ECO codes mean?
**A:** ECO (Encyclopedia of Chess Openings) codes classify chess openings:
- **A00-A99**: Flank openings, unusual first moves
- **B00-B99**: Semi-open games (1.e4 other than 1...e5)
- **C00-C99**: Open games (1.e4 e5) and French Defense
- **D00-D99**: Closed games (1.d4 d5) and Queen's Gambit
- **E00-E99**: Indian defenses (1.d4 Nf6)

### Q27: How accurate is the opening classification?
**A:** Opening classification is based on the first several moves and uses standard ECO databases. It's very accurate for well-known openings but may be generic for unusual or new variations.

### Q28: Can I search for games by specific opening moves?
**A:** Yes! Use the search function with:
- **ECO codes**: "B10" for Caro-Kann Defense
- **Opening names**: "Queen's Gambit" or "Sicilian Defense"
- **Move sequences**: "1.e4 e5 2.Nf3" for specific move orders

## Performance Analysis

### Q29: What makes a move "brilliant" vs "excellent"?
**A:** Move quality is determined by:
- **Brilliant**: Exceptional moves that are hard to find, often involving sacrifices
- **Excellent**: Best or near-best moves in the position
- **Good**: Solid moves that maintain the position
- **Inaccuracy**: Moves that give slight advantage to opponent
- **Mistake/Blunder**: Moves that give significant advantage to opponent

### Q30: How do you measure "tactical accuracy"?
**A:** Tactical accuracy considers:
- **Move quality**: Percentage of excellent/good moves played
- **Critical moments**: Performance in complex tactical positions
- **Blunder rate**: Frequency of significant mistakes
- **Time management**: Efficiency in critical positions

These metrics help identify which models are strongest in tactical play versus positional understanding.

---

*Don't see your question here? Feel free to reach out through our support channels or check the detailed documentation for more technical information.*