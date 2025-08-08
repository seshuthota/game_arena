// Custom commands for the Game Analysis Web Interface E2E tests

declare global {
  namespace Cypress {
    interface Chainable {
      /**
       * Custom command to select DOM element by data-cy attribute.
       * @param value - The data-cy attribute value
       * @example cy.dataCy('submit-button').click()
       */
      dataCy(value: string): Chainable<JQuery<HTMLElement>>;

      /**
       * Custom command to login with mock authentication
       * @example cy.login()
       */
      login(): Chainable<void>;

      /**
       * Custom command to wait for the page to be fully loaded
       * @example cy.waitForPageLoad()
       */
      waitForPageLoad(): Chainable<void>;

      /**
       * Custom command to check loading states
       * @example cy.checkLoadingState()
       */
      checkLoadingState(): Chainable<void>;

      /**
       * Custom command to navigate and wait for route change
       * @param route - The route to navigate to
       * @example cy.navigateAndWait('/games')
       */
      navigateAndWait(route: string): Chainable<void>;

      /**
       * Custom command to test responsive behavior
       * @param viewport - The viewport size to test
       * @example cy.testResponsive('mobile')
       */
      testResponsive(viewport: 'mobile' | 'tablet' | 'desktop'): Chainable<void>;
    }
  }
}

// Select by data-cy attribute
Cypress.Commands.add('dataCy', (value: string) => {
  return cy.get(`[data-cy="${value}"]`);
});

// Mock login command (for future authentication features)
Cypress.Commands.add('login', () => {
  // Currently no authentication required, but placeholder for future
  cy.window().then((window) => {
    window.localStorage.setItem('isAuthenticated', 'true');
  });
});

// Wait for page to be fully loaded
Cypress.Commands.add('waitForPageLoad', () => {
  cy.get('body').should('be.visible');
  cy.get('[data-cy="loading-skeleton"]').should('not.exist');
  cy.get('[data-cy="main-content"]').should('be.visible');
});

// Check loading states
Cypress.Commands.add('checkLoadingState', () => {
  // First check if loading skeleton appears
  cy.get('[data-cy="loading-skeleton"]').should('be.visible');
  
  // Then check if it disappears and content loads
  cy.get('[data-cy="loading-skeleton"]', { timeout: 10000 }).should('not.exist');
  cy.get('[data-cy="main-content"]').should('be.visible');
});

// Navigate and wait for route change
Cypress.Commands.add('navigateAndWait', (route: string) => {
  cy.visit(route);
  cy.url().should('include', route);
  cy.waitForPageLoad();
});

// Test responsive behavior
Cypress.Commands.add('testResponsive', (viewport: 'mobile' | 'tablet' | 'desktop') => {
  const viewportSizes = {
    mobile: [375, 667] as const,
    tablet: [768, 1024] as const,
    desktop: [1280, 720] as const,
  };

  const [width, height] = viewportSizes[viewport];
  cy.viewport(width, height);
  
  // Wait for responsive styles to take effect
  cy.wait(500);
});

// Add command to handle API errors gracefully
Cypress.Commands.add('handleApiError', () => {
  cy.window().its('console').then((console) => {
    cy.stub(console, 'error').as('consoleError');
  });
});

export {};