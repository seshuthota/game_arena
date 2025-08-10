/**
 * Tests for ErrorDisplay component.
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import ErrorDisplay, { ValidationError, RecoveryAction } from './ErrorDisplay';

describe('ErrorDisplay', () => {
  const mockError: ValidationError = {
    field: 'test_field',
    message: 'Test error message',
    severity: 'major',
    error_code: 'TEST_ERROR',
    suggested_fix: 'Try fixing this way',
    raw_value: 'invalid_value'
  };

  const mockRecoveryActions: RecoveryAction[] = [
    {
      type: 'retry',
      description: 'Retry the operation',
      confidence: 0.9,
      requires_user_input: false
    },
    {
      type: 'skip',
      description: 'Skip this step',
      confidence: 0.8,
      requires_user_input: false
    },
    {
      type: 'manual_fix',
      description: 'Fix manually',
      confidence: 0.6,
      requires_user_input: true,
      estimated_data: { fixed_value: 'corrected' }
    }
  ];

  it('renders error message and basic information', () => {
    render(<ErrorDisplay error={mockError} />);
    
    expect(screen.getByText('Major Error')).toBeInTheDocument();
    expect(screen.getByText('Test error message')).toBeInTheDocument();
    expect(screen.getByText('TEST_ERROR')).toBeInTheDocument();
    expect(screen.getByText(/Try fixing this way/)).toBeInTheDocument();
  });

  it('displays correct severity styling for critical errors', () => {
    const criticalError = { ...mockError, severity: 'critical' as const };
    const { container } = render(<ErrorDisplay error={criticalError} />);
    
    const errorContainer = container.firstChild as HTMLElement;
    expect(errorContainer).toHaveClass('border-red-500', 'bg-red-50', 'text-red-800');
  });

  it('displays correct severity styling for warning errors', () => {
    const warningError = { ...mockError, severity: 'warning' as const };
    const { container } = render(<ErrorDisplay error={warningError} />);
    
    const errorContainer = container.firstChild as HTMLElement;
    expect(errorContainer).toHaveClass('border-blue-500', 'bg-blue-50', 'text-blue-800');
  });

  it('shows recovery actions when expanded', () => {
    render(<ErrorDisplay error={mockError} recoveryActions={mockRecoveryActions} />);
    
    // Initially collapsed
    expect(screen.queryByText('Recovery Options')).not.toBeInTheDocument();
    
    // Expand
    const expandButton = screen.getByTitle('Show options');
    fireEvent.click(expandButton);
    
    expect(screen.getByText('Recovery Options')).toBeInTheDocument();
    expect(screen.getByText('Retry the operation')).toBeInTheDocument();
    expect(screen.getByText('Skip this step')).toBeInTheDocument();
    expect(screen.getByText('Fix manually')).toBeInTheDocument();
  });

  it('shows confidence levels for recovery actions', () => {
    render(<ErrorDisplay error={mockError} recoveryActions={mockRecoveryActions} showDetails={true} />);
    
    expect(screen.getByText('90% confidence')).toBeInTheDocument();
    expect(screen.getByText('80% confidence')).toBeInTheDocument();
    expect(screen.getByText('60% confidence')).toBeInTheDocument();
  });

  it('indicates when user input is required', () => {
    render(<ErrorDisplay error={mockError} recoveryActions={mockRecoveryActions} showDetails={true} />);
    
    expect(screen.getByText('Requires user input')).toBeInTheDocument();
  });

  it('calls onRetry when retry action is clicked', async () => {
    const onRetry = jest.fn();
    render(
      <ErrorDisplay 
        error={mockError} 
        recoveryActions={mockRecoveryActions} 
        onRetry={onRetry}
        showDetails={true}
      />
    );
    
    const retryButton = screen.getByText('retry');
    fireEvent.click(retryButton);
    
    await waitFor(() => {
      expect(onRetry).toHaveBeenCalledTimes(1);
    });
  });

  it('calls onSkip when skip action is clicked', async () => {
    const onSkip = jest.fn();
    render(
      <ErrorDisplay 
        error={mockError} 
        recoveryActions={mockRecoveryActions} 
        onSkip={onSkip}
        showDetails={true}
      />
    );
    
    const skipButton = screen.getByText('skip');
    fireEvent.click(skipButton);
    
    await waitFor(() => {
      expect(onSkip).toHaveBeenCalledTimes(1);
    });
  });

  it('calls onManualFix with estimated data when manual fix is clicked', async () => {
    const onManualFix = jest.fn();
    render(
      <ErrorDisplay 
        error={mockError} 
        recoveryActions={mockRecoveryActions} 
        onManualFix={onManualFix}
        showDetails={true}
      />
    );
    
    const manualFixButton = screen.getByText('manual fix');
    fireEvent.click(manualFixButton);
    
    await waitFor(() => {
      expect(onManualFix).toHaveBeenCalledWith({ fixed_value: 'corrected' });
    });
  });

  it('shows raw value when expanded', () => {
    render(<ErrorDisplay error={mockError} showDetails={true} />);
    
    expect(screen.getByText('Raw Value')).toBeInTheDocument();
    expect(screen.getByText('invalid_value')).toBeInTheDocument();
  });

  it('formats complex raw values as JSON', () => {
    const errorWithComplexValue = {
      ...mockError,
      raw_value: { complex: 'object', with: ['array', 'values'] }
    };
    
    render(<ErrorDisplay error={errorWithComplexValue} showDetails={true} />);
    
    expect(screen.getByText('Raw Value')).toBeInTheDocument();
    expect(screen.getByText(/"complex": "object"/)).toBeInTheDocument();
  });

  it('calls onDismiss when dismiss button is clicked', () => {
    const onDismiss = jest.fn();
    render(<ErrorDisplay error={mockError} onDismiss={onDismiss} />);
    
    const dismissButton = screen.getByTitle('Dismiss error');
    fireEvent.click(dismissButton);
    
    expect(onDismiss).toHaveBeenCalledTimes(1);
  });

  it('applies custom className', () => {
    const { container } = render(<ErrorDisplay error={mockError} className="custom-class" />);
    
    const errorContainer = container.firstChild as HTMLElement;
    expect(errorContainer).toHaveClass('custom-class');
  });

  it('calls action handlers correctly', async () => {
    const onRetry = jest.fn();
    render(
      <ErrorDisplay 
        error={mockError} 
        recoveryActions={mockRecoveryActions} 
        onRetry={onRetry}
        showDetails={true}
      />
    );
    
    const retryButton = screen.getByText('retry').closest('button') as HTMLButtonElement;
    fireEvent.click(retryButton);
    
    // Verify the handler was called
    expect(onRetry).toHaveBeenCalledTimes(1);
  });

  it('applies correct button styling based on confidence level', () => {
    render(<ErrorDisplay error={mockError} recoveryActions={mockRecoveryActions} showDetails={true} />);
    
    // High confidence (90%) - green
    const retryButton = screen.getByText('retry').closest('button') as HTMLButtonElement;
    expect(retryButton).toHaveClass('bg-green-100', 'text-green-800');
    
    // Medium confidence (80%) - green
    const skipButton = screen.getByText('skip').closest('button') as HTMLButtonElement;
    expect(skipButton).toHaveClass('bg-green-100', 'text-green-800');
    
    // Lower confidence (60%) - yellow
    const manualFixButton = screen.getByText('manual fix').closest('button') as HTMLButtonElement;
    expect(manualFixButton).toHaveClass('bg-yellow-100', 'text-yellow-800');
  });

  it('toggles expansion state correctly', () => {
    render(<ErrorDisplay error={mockError} recoveryActions={mockRecoveryActions} />);
    
    const expandButton = screen.getByTitle('Show options');
    
    // Initially collapsed
    expect(screen.queryByText('Recovery Options')).not.toBeInTheDocument();
    
    // Expand
    fireEvent.click(expandButton);
    expect(screen.getByText('Recovery Options')).toBeInTheDocument();
    expect(screen.getByTitle('Hide options')).toBeInTheDocument();
    
    // Collapse
    fireEvent.click(screen.getByTitle('Hide options'));
    expect(screen.queryByText('Recovery Options')).not.toBeInTheDocument();
    expect(screen.getByTitle('Show options')).toBeInTheDocument();
  });

  it('handles errors without recovery actions', () => {
    render(<ErrorDisplay error={mockError} />);
    
    // Should not show expand button if no recovery actions
    expect(screen.queryByTitle('Show options')).not.toBeInTheDocument();
    expect(screen.queryByTitle('Hide options')).not.toBeInTheDocument();
  });

  it('handles errors without suggested fix', () => {
    const errorWithoutFix = { ...mockError, suggested_fix: undefined };
    render(<ErrorDisplay error={errorWithoutFix} />);
    
    expect(screen.getByText('Test error message')).toBeInTheDocument();
    expect(screen.queryByText(/Suggested fix:/)).not.toBeInTheDocument();
  });
});