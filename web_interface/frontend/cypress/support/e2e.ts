// Import commands.ts using ES2015 syntax:
import './commands';

// Alternatively you can use CommonJS syntax:
// require('./commands')

// Hide fetch/XHR requests from command log
const app = window.top;
if (!app.document.head.querySelector('[data-hide-command-log-request]')) {
  const style = app.document.createElement('style');
  style.innerHTML = '.command-name-request, .command-name-xhr { display: none }';
  style.setAttribute('data-hide-command-log-request', '');
  app.document.head.appendChild(style);
}

// Global before hook to set up test environment
beforeEach(() => {
  // Set up common API intercepts that apply to all tests
  cy.intercept('GET', '/api/health', { body: { status: 'ok' } });
  
  // Handle uncaught exceptions to prevent test failures from expected errors
  cy.on('uncaught:exception', (err) => {
    // Returning false prevents the test from failing on uncaught exceptions
    // This is useful for handling network errors and API failures in error testing scenarios
    if (err.message.includes('Network Error') || 
        err.message.includes('Failed to fetch') ||
        err.message.includes('ERR_NETWORK')) {
      return false;
    }
    // Let other exceptions fail the test
    return true;
  });
});

// Global configuration
Cypress.on('window:before:load', (win) => {
  // Disable service workers during testing
  delete win.navigator.serviceWorker;
  
  // Mock performance.now for consistent timing in tests
  win.performance.now = () => Date.now();
});

// Custom assertion for checking loading states
chai.Assertion.addMethod('toBeLoading', function () {
  const obj = this._obj;
  
  new chai.Assertion(obj).to.exist;
  new chai.Assertion(obj).to.have.attr('data-cy').that.includes('loading');
  
  this.assert(
    obj.is(':visible'),
    'expected #{this} to be a visible loading element',
    'expected #{this} to not be a visible loading element'
  );
});

// Custom assertion for checking error states
chai.Assertion.addMethod('toShowError', function () {
  const obj = this._obj;
  
  new chai.Assertion(obj).to.exist;
  new chai.Assertion(obj).to.have.attr('data-cy', 'error-message');
  
  this.assert(
    obj.is(':visible'),
    'expected #{this} to be a visible error message',
    'expected #{this} to not be a visible error message'
  );
});