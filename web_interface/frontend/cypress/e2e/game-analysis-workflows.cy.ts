describe('Game Analysis Web Interface - Critical User Workflows', () => {
  beforeEach(() => {
    // Intercept API calls and provide mock responses
    cy.intercept('GET', '/api/games*', {
      fixture: 'games-list.json'
    }).as('getGames');
    
    cy.intercept('GET', '/api/games/game_1', {
      fixture: 'game-detail.json'
    }).as('getGameDetail');
    
    cy.intercept('GET', '/api/statistics/overview', {
      fixture: 'statistics.json'
    }).as('getStatistics');
    
    cy.intercept('GET', '/api/leaderboard*', {
      fixture: 'leaderboard.json'
    }).as('getLeaderboard');
    
    // Visit the application
    cy.visit('/');
  });

  describe('Navigation and Layout', () => {
    it('should load the main dashboard and navigate between sections', () => {
      // Check that the main dashboard loads
      cy.contains('Game Arena Analytics').should('be.visible');
      
      // Check navigation menu
      cy.get('[data-cy=nav-games]').should('be.visible');
      cy.get('[data-cy=nav-statistics]').should('be.visible');
      cy.get('[data-cy=nav-leaderboard]').should('be.visible');
      
      // Navigate to Games section
      cy.get('[data-cy=nav-games]').click();
      cy.url().should('include', '/games');
      cy.wait('@getGames');
      
      // Navigate to Statistics section
      cy.get('[data-cy=nav-statistics]').click();
      cy.url().should('include', '/statistics');
      cy.wait('@getStatistics');
      
      // Navigate to Leaderboard section
      cy.get('[data-cy=nav-leaderboard]').click();
      cy.url().should('include', '/leaderboard');
      cy.wait('@getLeaderboard');
    });

    it('should be responsive on mobile devices', () => {
      // Test mobile viewport
      cy.viewport('iphone-x');
      
      // Mobile navigation should be collapsed
      cy.get('[data-cy=mobile-menu-button]').should('be.visible');
      cy.get('[data-cy=mobile-menu-button]').click();
      
      // Navigation items should be visible in mobile menu
      cy.get('[data-cy=mobile-nav]').should('be.visible');
      cy.get('[data-cy=mobile-nav] [data-cy=nav-games]').should('be.visible');
    });
  });

  describe('Game List and Filtering Workflow', () => {
    beforeEach(() => {
      cy.visit('/games');
      cy.wait('@getGames');
    });

    it('should display games list and support pagination', () => {
      // Check that games are displayed
      cy.get('[data-cy=games-table]').should('be.visible');
      cy.get('[data-cy=game-row]').should('have.length.at.least', 1);
      
      // Check game information is displayed
      cy.get('[data-cy=game-row]').first().within(() => {
        cy.get('[data-cy=game-id]').should('be.visible');
        cy.get('[data-cy=players]').should('be.visible');
        cy.get('[data-cy=game-result]').should('be.visible');
        cy.get('[data-cy=game-duration]').should('be.visible');
      });
      
      // Test pagination controls
      cy.get('[data-cy=pagination]').should('be.visible');
      cy.get('[data-cy=pagination-info]').should('contain', 'Page 1');
    });

    it('should support search functionality', () => {
      // Find and use search input
      cy.get('[data-cy=search-input]').should('be.visible');
      cy.get('[data-cy=search-input]').type('gpt-4');
      
      // Should trigger search API call
      cy.intercept('GET', '/api/games*search=gpt-4*', {
        fixture: 'games-search-results.json'
      }).as('searchGames');
      
      cy.wait('@searchGames');
      
      // Results should be filtered
      cy.get('[data-cy=games-table]').should('contain', 'gpt-4');
    });

    it('should support advanced filtering', () => {
      // Open filter panel
      cy.get('[data-cy=filter-toggle]').click();
      cy.get('[data-cy=filter-panel]').should('be.visible');
      
      // Apply date range filter
      cy.get('[data-cy=start-date-input]').type('2024-01-01');
      cy.get('[data-cy=end-date-input]').type('2024-01-31');
      
      // Apply result filter
      cy.get('[data-cy=result-filter]').select('white_wins');
      
      // Apply model provider filter
      cy.get('[data-cy=provider-filter]').select('openai');
      
      // Submit filters
      cy.get('[data-cy=apply-filters]').click();
      
      // Should trigger filtered API call
      cy.intercept('GET', '/api/games*result=white_wins*provider=openai*', {
        fixture: 'games-filtered-results.json'
      }).as('filterGames');
      
      cy.wait('@filterGames');
      
      // Clear filters
      cy.get('[data-cy=clear-filters]').click();
      cy.wait('@getGames');
    });

    it('should support sorting options', () => {
      // Test sorting by different criteria
      cy.get('[data-cy=sort-select]').select('duration_desc');
      
      cy.intercept('GET', '/api/games*sort_by=duration_desc*', {
        fixture: 'games-sorted.json'
      }).as('sortGames');
      
      cy.wait('@sortGames');
      
      // Verify sort option is applied
      cy.get('[data-cy=sort-select]').should('have.value', 'duration_desc');
    });
  });

  describe('Game Detail Analysis Workflow', () => {
    beforeEach(() => {
      cy.visit('/games');
      cy.wait('@getGames');
    });

    it('should navigate to game detail and display comprehensive information', () => {
      // Click on first game to view details
      cy.get('[data-cy=game-row]').first().click();
      
      cy.url().should('match', /\/games\/game_\w+/);
      cy.wait('@getGameDetail');
      
      // Check game detail page elements
      cy.get('[data-cy=game-detail-header]').should('be.visible');
      cy.get('[data-cy=game-players]').should('be.visible');
      cy.get('[data-cy=game-result]').should('be.visible');
      cy.get('[data-cy=game-moves-list]').should('be.visible');
    });

    it('should support interactive move analysis', () => {
      // Navigate to game detail
      cy.visit('/games/game_1');
      cy.wait('@getGameDetail');
      
      // Check chess board is displayed
      cy.get('[data-cy=chess-board]').should('be.visible');
      
      // Check moves list
      cy.get('[data-cy=moves-list]').should('be.visible');
      cy.get('[data-cy=move-item]').should('have.length.at.least', 1);
      
      // Click on a move to select it
      cy.get('[data-cy=move-item]').first().click();
      
      // Move details panel should show
      cy.get('[data-cy=move-details-panel]').should('be.visible');
      cy.get('[data-cy=move-details-panel]').within(() => {
        cy.should('contain', 'FEN Position');
        cy.should('contain', 'Thinking Time');
        cy.should('contain', 'LLM Response');
      });
      
      // Test move navigation controls
      cy.get('[data-cy=move-next]').click();
      cy.get('[data-cy=move-previous]').click();
      cy.get('[data-cy=move-first]').click();
      cy.get('[data-cy=move-last]').click();
    });

    it('should support keyboard navigation for moves', () => {
      cy.visit('/games/game_1');
      cy.wait('@getGameDetail');
      
      // Focus on the chess board area
      cy.get('[data-cy=chess-board]').click();
      
      // Test keyboard shortcuts
      cy.get('body').type('{rightarrow}'); // Next move
      cy.get('body').type('{leftarrow}');  // Previous move
      cy.get('body').type('{home}');       // First move
      cy.get('body').type('{end}');        // Last move
    });
  });

  describe('Statistics Dashboard Workflow', () => {
    beforeEach(() => {
      cy.visit('/statistics');
      cy.wait('@getStatistics');
    });

    it('should display comprehensive statistics overview', () => {
      // Check main statistics cards
      cy.get('[data-cy=stats-total-games]').should('be.visible');
      cy.get('[data-cy=stats-total-players]').should('be.visible');
      cy.get('[data-cy=stats-win-rates]').should('be.visible');
      cy.get('[data-cy=stats-avg-duration]').should('be.visible');
      
      // Verify statistics values are displayed
      cy.get('[data-cy=stats-total-games]').should('contain.text', '150');
      cy.get('[data-cy=stats-total-players]').should('contain.text', '12');
    });

    it('should display interactive charts and graphs', () => {
      // Check that charts are rendered
      cy.get('[data-cy=games-over-time-chart]').should('be.visible');
      cy.get('[data-cy=win-rate-chart]').should('be.visible');
      cy.get('[data-cy=performance-trends-chart]').should('be.visible');
      
      // Test chart interactions
      cy.get('[data-cy=chart-time-range]').select('last_7_days');
      cy.get('[data-cy=chart-metric]').select('games_played');
      
      // Charts should update based on selections
      cy.intercept('GET', '/api/statistics/time-series*', {
        fixture: 'time-series-data.json'
      }).as('getTimeSeries');
      
      cy.wait('@getTimeSeries');
    });
  });

  describe('Leaderboard Workflow', () => {
    beforeEach(() => {
      cy.visit('/leaderboard');
      cy.wait('@getLeaderboard');
    });

    it('should display player rankings and support sorting', () => {
      // Check leaderboard table
      cy.get('[data-cy=leaderboard-table]').should('be.visible');
      cy.get('[data-cy=player-row]').should('have.length.at.least', 1);
      
      // Check player information is displayed
      cy.get('[data-cy=player-row]').first().within(() => {
        cy.get('[data-cy=player-rank]').should('be.visible');
        cy.get('[data-cy=player-name]').should('be.visible');
        cy.get('[data-cy=player-winrate]').should('be.visible');
        cy.get('[data-cy=player-elo]').should('be.visible');
      });
      
      // Test sorting options
      cy.get('[data-cy=leaderboard-sort]').select('elo_rating');
      
      cy.intercept('GET', '/api/leaderboard*sort_by=elo_rating*', {
        fixture: 'leaderboard-sorted.json'
      }).as('sortLeaderboard');
      
      cy.wait('@sortLeaderboard');
    });

    it('should support filtering by game type and time period', () => {
      // Apply time period filter
      cy.get('[data-cy=time-period-filter]').select('last_30_days');
      
      // Apply minimum games filter
      cy.get('[data-cy=min-games-filter]').clear().type('10');
      
      // Submit filters
      cy.get('[data-cy=apply-leaderboard-filters]').click();
      
      cy.intercept('GET', '/api/leaderboard*time_period=last_30_days*min_games=10*', {
        fixture: 'leaderboard-filtered.json'
      }).as('filterLeaderboard');
      
      cy.wait('@filterLeaderboard');
    });

    it('should show player detail modal', () => {
      // Click on a player to view details
      cy.get('[data-cy=player-row]').first().click();
      
      // Player detail modal should appear
      cy.get('[data-cy=player-detail-modal]').should('be.visible');
      cy.get('[data-cy=player-detail-modal]').within(() => {
        cy.should('contain', 'Player Statistics');
        cy.should('contain', 'Recent Games');
        cy.should('contain', 'Performance Trends');
      });
      
      // Close modal
      cy.get('[data-cy=close-modal]').click();
      cy.get('[data-cy=player-detail-modal]').should('not.exist');
    });
  });

  describe('Error Handling and Edge Cases', () => {
    it('should handle API errors gracefully', () => {
      // Simulate API error
      cy.intercept('GET', '/api/games*', {
        statusCode: 500,
        body: { detail: 'Internal server error' }
      }).as('getGamesError');
      
      cy.visit('/games');
      cy.wait('@getGamesError');
      
      // Should display error message
      cy.get('[data-cy=error-message]').should('be.visible');
      cy.get('[data-cy=error-message]').should('contain', 'error');
      
      // Should have retry button
      cy.get('[data-cy=retry-button]').should('be.visible');
      cy.get('[data-cy=retry-button]').click();
    });

    it('should handle empty states appropriately', () => {
      // Simulate empty games list
      cy.intercept('GET', '/api/games*', {
        body: {
          success: true,
          games: [],
          pagination: {
            total_count: 0,
            total_pages: 0,
            has_next: false,
            has_previous: false
          }
        }
      }).as('getEmptyGames');
      
      cy.visit('/games');
      cy.wait('@getEmptyGames');
      
      // Should display empty state message
      cy.get('[data-cy=empty-state]').should('be.visible');
      cy.get('[data-cy=empty-state]').should('contain', 'No games found');
    });

    it('should handle network timeouts', () => {
      // Simulate slow/timeout API response
      cy.intercept('GET', '/api/games*', (req) => {
        req.reply((res) => {
          res.delay(15000); // Longer than timeout
        });
      }).as('getGamesTimeout');
      
      cy.visit('/games');
      
      // Should show timeout error message
      cy.get('[data-cy=error-message]', { timeout: 20000 }).should('be.visible');
    });
  });

  describe('Performance and Loading States', () => {
    it('should display appropriate loading states', () => {
      // Simulate slow API response
      cy.intercept('GET', '/api/games*', (req) => {
        req.reply((res) => {
          res.delay(2000);
        });
      }).as('getGamesSlowly');
      
      cy.visit('/games');
      
      // Should show loading skeleton
      cy.get('[data-cy=loading-skeleton]').should('be.visible');
      
      cy.wait('@getGamesSlowly');
      
      // Loading skeleton should disappear
      cy.get('[data-cy=loading-skeleton]').should('not.exist');
      cy.get('[data-cy=games-table]').should('be.visible');
    });

    it('should meet performance requirements', () => {
      cy.visit('/');
      
      // Page should load within 2 seconds
      cy.get('[data-cy=main-content]', { timeout: 2000 }).should('be.visible');
      
      // Navigation should be fast
      const startTime = Date.now();
      cy.get('[data-cy=nav-games]').click();
      cy.get('[data-cy=games-table]').should('be.visible').then(() => {
        const loadTime = Date.now() - startTime;
        expect(loadTime).to.be.lessThan(2000);
      });
    });
  });

  describe('Data Integrity and Consistency', () => {
    it('should maintain data consistency across views', () => {
      // Check that same game appears consistently across different views
      cy.visit('/games');
      cy.wait('@getGames');
      
      // Get game ID from games list
      cy.get('[data-cy=game-row]').first().invoke('attr', 'data-game-id').then((gameId) => {
        // Navigate to statistics that might reference the same game
        cy.visit('/statistics');
        cy.wait('@getStatistics');
        
        // Statistics should reflect the game data
        cy.get('[data-cy=stats-total-games]').should('not.contain', '0');
        
        // Navigate to game detail
        cy.visit(`/games/${gameId}`);
        cy.wait('@getGameDetail');
        
        // Game detail should show consistent information
        cy.get('[data-cy=game-detail-header]').should('contain', gameId);
      });
    });
  });
});