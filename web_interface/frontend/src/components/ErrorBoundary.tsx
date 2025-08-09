import React, { Component, ErrorInfo, ReactNode } from 'react';

interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
  resetOnPropsChange?: boolean;
  resetKeys?: Array<string | number>;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
  eventId: string | null;
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  private resetTimeoutId: number | null = null;

  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
      eventId: null,
    };
  }

  static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
    return {
      hasError: true,
      error,
      eventId: `error_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
    };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo);
    
    this.setState({
      error,
      errorInfo,
    });

    // Call custom error handler if provided
    if (this.props.onError) {
      this.props.onError(error, errorInfo);
    }

    // Log error to monitoring service (placeholder)
    this.logErrorToService(error, errorInfo);
  }

  componentDidUpdate(prevProps: ErrorBoundaryProps) {
    const { resetKeys, resetOnPropsChange } = this.props;
    const { hasError } = this.state;

    if (hasError && prevProps.resetKeys !== resetKeys) {
      if (resetKeys) {
        const hasResetKeyChanged = resetKeys.some(
          (resetKey, idx) => prevProps.resetKeys?.[idx] !== resetKey
        );
        if (hasResetKeyChanged) {
          this.resetErrorBoundary();
        }
      }
    }

    if (hasError && resetOnPropsChange && prevProps.children !== this.props.children) {
      this.resetErrorBoundary();
    }
  }

  resetErrorBoundary = () => {
    if (this.resetTimeoutId) {
      clearTimeout(this.resetTimeoutId);
    }

    this.resetTimeoutId = window.setTimeout(() => {
      this.setState({
        hasError: false,
        error: null,
        errorInfo: null,
        eventId: null,
      });
    }, 100);
  };

  private logErrorToService(error: Error, errorInfo: ErrorInfo) {
    // In a real application, you would send this to your monitoring service
    // e.g., Sentry, LogRocket, Bugsnag, etc.
    const errorData = {
      message: error.message,
      stack: error.stack,
      componentStack: errorInfo.componentStack,
      timestamp: new Date().toISOString(),
      url: window.location.href,
      userAgent: navigator.userAgent,
      eventId: this.state.eventId,
    };

    // For development, log to console
    if (process.env.NODE_ENV === 'development') {
      console.group('🚨 Error Boundary - Full Error Details');
      console.error('Error:', error);
      console.error('Error Info:', errorInfo);
      console.table(errorData);
      console.groupEnd();
    }

    // In production, send to monitoring service
    // monitoringService.captureException(error, { extra: errorData });
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <ErrorFallback
          error={this.state.error}
          errorInfo={this.state.errorInfo}
          resetError={this.resetErrorBoundary}
          eventId={this.state.eventId}
        />
      );
    }

    return this.props.children;
  }
}

// Default error fallback component
interface ErrorFallbackProps {
  error: Error | null;
  errorInfo: ErrorInfo | null;
  resetError: () => void;
  eventId: string | null;
}

export const ErrorFallback: React.FC<ErrorFallbackProps> = ({
  error,
  errorInfo,
  resetError,
  eventId,
}) => {
  const [showDetails, setShowDetails] = React.useState(false);
  const isDevelopment = process.env.NODE_ENV === 'development';

  const handleReportError = () => {
    // In a real app, this would open a support ticket or send feedback
    const subject = encodeURIComponent(`Error Report - ${eventId}`);
    const body = encodeURIComponent(
      `Error ID: ${eventId}\n\nError: ${error?.message}\n\nPlease describe what you were doing when this error occurred:`
    );
    window.open(`mailto:support@example.com?subject=${subject}&body=${body}`);
  };

  return (
    <div className="error-boundary">
      <div className="error-container">
        <div className="error-icon">⚠️</div>
        <h2 className="error-title">Oops! Something went wrong</h2>
        <p className="error-description">
          We're sorry, but something unexpected happened. This error has been logged and we're working to fix it.
        </p>

        {eventId && (
          <p className="error-id">
            Error ID: <code>{eventId}</code>
          </p>
        )}

        <div className="error-actions">
          <button onClick={resetError} className="retry-button">
            Try Again
          </button>
          <button onClick={() => window.location.reload()} className="reload-button">
            Reload Page
          </button>
          <button onClick={handleReportError} className="report-button">
            Report Issue
          </button>
        </div>

        {isDevelopment && (
          <div className="error-development">
            <button 
              onClick={() => setShowDetails(!showDetails)} 
              className="toggle-details-button"
            >
              {showDetails ? 'Hide' : 'Show'} Technical Details
            </button>
            
            {showDetails && (
              <div className="error-details">
                <div className="error-section">
                  <h4>Error Message:</h4>
                  <pre className="error-message">{error?.message}</pre>
                </div>
                
                {error?.stack && (
                  <div className="error-section">
                    <h4>Stack Trace:</h4>
                    <pre className="error-stack">{error.stack}</pre>
                  </div>
                )}
                
                {errorInfo?.componentStack && (
                  <div className="error-section">
                    <h4>Component Stack:</h4>
                    <pre className="error-component-stack">{errorInfo.componentStack}</pre>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      <style jsx>{`
        .error-boundary {
          display: flex;
          align-items: center;
          justify-content: center;
          min-height: 400px;
          padding: 2rem;
          background-color: #fef2f2;
        }

        .error-container {
          max-width: 600px;
          width: 100%;
          text-align: center;
          background-color: white;
          border-radius: 0.75rem;
          padding: 2.5rem;
          box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1);
          border: 1px solid #fecaca;
        }

        .error-icon {
          font-size: 4rem;
          margin-bottom: 1.5rem;
        }

        .error-title {
          font-size: 1.875rem;
          font-weight: 700;
          color: #dc2626;
          margin-bottom: 1rem;
        }

        .error-description {
          font-size: 1rem;
          color: #6b7280;
          margin-bottom: 1.5rem;
          line-height: 1.6;
        }

        .error-id {
          font-size: 0.875rem;
          color: #9ca3af;
          margin-bottom: 2rem;
        }

        .error-id code {
          background-color: #f3f4f6;
          padding: 0.25rem 0.5rem;
          border-radius: 0.25rem;
          font-family: 'SF Mono', 'Monaco', 'Inconsolata', 'Roboto Mono', monospace;
        }

        .error-actions {
          display: flex;
          gap: 1rem;
          justify-content: center;
          margin-bottom: 2rem;
          flex-wrap: wrap;
        }

        .retry-button,
        .reload-button,
        .report-button {
          padding: 0.75rem 1.5rem;
          border-radius: 0.5rem;
          font-weight: 500;
          font-size: 0.875rem;
          cursor: pointer;
          transition: all 0.2s;
          border: 1px solid transparent;
        }

        .retry-button {
          background-color: #dc2626;
          color: white;
          border-color: #dc2626;
        }

        .retry-button:hover {
          background-color: #b91c1c;
          border-color: #b91c1c;
        }

        .reload-button {
          background-color: #6b7280;
          color: white;
          border-color: #6b7280;
        }

        .reload-button:hover {
          background-color: #4b5563;
          border-color: #4b5563;
        }

        .report-button {
          background-color: white;
          color: #6b7280;
          border-color: #d1d5db;
        }

        .report-button:hover {
          background-color: #f9fafb;
          border-color: #9ca3af;
        }

        .error-development {
          border-top: 1px solid #e5e7eb;
          padding-top: 2rem;
          text-align: left;
        }

        .toggle-details-button {
          background-color: #f3f4f6;
          color: #374151;
          border: 1px solid #d1d5db;
          padding: 0.5rem 1rem;
          border-radius: 0.375rem;
          font-size: 0.875rem;
          cursor: pointer;
          transition: background-color 0.2s;
          margin-bottom: 1rem;
        }

        .toggle-details-button:hover {
          background-color: #e5e7eb;
        }

        .error-details {
          background-color: #f9fafb;
          border: 1px solid #e5e7eb;
          border-radius: 0.5rem;
          padding: 1.5rem;
          margin-top: 1rem;
        }

        .error-section {
          margin-bottom: 1.5rem;
        }

        .error-section:last-child {
          margin-bottom: 0;
        }

        .error-section h4 {
          font-size: 0.875rem;
          font-weight: 600;
          color: #374151;
          margin-bottom: 0.5rem;
        }

        .error-message,
        .error-stack,
        .error-component-stack {
          background-color: #1f2937;
          color: #f9fafb;
          padding: 1rem;
          border-radius: 0.375rem;
          font-size: 0.75rem;
          font-family: 'SF Mono', 'Monaco', 'Inconsolata', 'Roboto Mono', monospace;
          overflow-x: auto;
          white-space: pre-wrap;
          word-break: break-word;
          margin: 0;
        }

        @media (max-width: 640px) {
          .error-container {
            padding: 1.5rem;
            margin: 1rem;
          }

          .error-actions {
            flex-direction: column;
          }

          .retry-button,
          .reload-button,
          .report-button {
            width: 100%;
          }
        }
      `}</style>
    </div>
  );
};

// Specialized error boundaries for different parts of the app
export const GameListErrorBoundary: React.FC<{ children: ReactNode }> = ({ children }) => (
  <ErrorBoundary
    fallback={
      <div className="game-list-error">
        <div className="error-content">
          <h3>Unable to load games</h3>
          <p>There was a problem loading the game list. Please try refreshing the page.</p>
        </div>
        <style jsx>{`
          .game-list-error {
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 300px;
            background-color: #fef2f2;
            border-radius: 0.75rem;
            border: 1px solid #fecaca;
          }
          .error-content {
            text-align: center;
            padding: 2rem;
          }
          .error-content h3 {
            color: #dc2626;
            margin-bottom: 0.5rem;
          }
          .error-content p {
            color: #6b7280;
          }
        `}</style>
      </div>
    }
  >
    {children}
  </ErrorBoundary>
);

export const StatisticsErrorBoundary: React.FC<{ children: ReactNode }> = ({ children }) => (
  <ErrorBoundary
    fallback={
      <div className="statistics-error">
        <div className="error-content">
          <h3>Unable to load statistics</h3>
          <p>There was a problem loading the statistics data. Please try again later.</p>
        </div>
        <style jsx>{`
          .statistics-error {
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 200px;
            background-color: #fef2f2;
            border-radius: 0.75rem;
            border: 1px solid #fecaca;
          }
          .error-content {
            text-align: center;
            padding: 2rem;
          }
          .error-content h3 {
            color: #dc2626;
            margin-bottom: 0.5rem;
          }
          .error-content p {
            color: #6b7280;
          }
        `}</style>
      </div>
    }
  >
    {children}
  </ErrorBoundary>
);

export const ChartErrorBoundary: React.FC<{ children: ReactNode }> = ({ children }) => (
  <ErrorBoundary
    fallback={
      <div className="chart-error">
        <div className="error-content">
          <span className="error-icon">📊</span>
          <h4>Chart Error</h4>
          <p>Unable to render chart data</p>
        </div>
        <style jsx>{`
          .chart-error {
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 200px;
            background-color: #f9fafb;
            border: 2px dashed #e5e7eb;
            border-radius: 0.5rem;
          }
          .error-content {
            text-align: center;
            padding: 1.5rem;
          }
          .error-icon {
            font-size: 2rem;
            margin-bottom: 0.5rem;
            display: block;
          }
          .error-content h4 {
            color: #6b7280;
            margin-bottom: 0.25rem;
            font-size: 1rem;
          }
          .error-content p {
            color: #9ca3af;
            font-size: 0.875rem;
          }
        `}</style>
      </div>
    }
  >
    {children}
  </ErrorBoundary>
);

// Game Detail Error Boundary
export const GameDetailErrorBoundary: React.FC<{ children: ReactNode; gameId?: string }> = ({ 
  children, 
  gameId 
}) => (
  <ErrorBoundary
    fallback={
      <div className="game-detail-error">
        <div className="error-content">
          <div className="error-icon">🎯</div>
          <h3>Unable to load game details</h3>
          <p>
            {gameId 
              ? `There was a problem loading game ${gameId.slice(0, 8)}...`
              : 'There was a problem loading the game details.'
            }
          </p>
          <button 
            onClick={() => window.location.reload()} 
            className="reload-button"
          >
            Reload Game
          </button>
        </div>
        <style jsx>{`
          .game-detail-error {
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 400px;
            background-color: #fef2f2;
            border-radius: 0.75rem;
            border: 1px solid #fecaca;
            margin: 1rem 0;
          }
          .error-content {
            text-align: center;
            padding: 2rem;
            max-width: 400px;
          }
          .error-icon {
            font-size: 3rem;
            margin-bottom: 1rem;
          }
          .error-content h3 {
            color: #dc2626;
            margin-bottom: 0.5rem;
            font-size: 1.25rem;
          }
          .error-content p {
            color: #6b7280;
            margin-bottom: 1.5rem;
            line-height: 1.5;
          }
          .reload-button {
            background-color: #dc2626;
            color: white;
            border: none;
            padding: 0.75rem 1.5rem;
            border-radius: 0.5rem;
            font-weight: 500;
            cursor: pointer;
            transition: background-color 0.2s;
          }
          .reload-button:hover {
            background-color: #b91c1c;
          }
        `}</style>
      </div>
    }
    resetKeys={gameId ? [gameId] : []}
  >
    {children}
  </ErrorBoundary>
);

// Move List Error Boundary
export const MoveListErrorBoundary: React.FC<{ children: ReactNode }> = ({ children }) => (
  <ErrorBoundary
    fallback={
      <div className="move-list-error">
        <div className="error-content">
          <span className="error-icon">♟️</span>
          <h4>Move List Error</h4>
          <p>Unable to display game moves</p>
          <button 
            onClick={() => window.location.reload()} 
            className="retry-small-button"
          >
            Retry
          </button>
        </div>
        <style jsx>{`
          .move-list-error {
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 150px;
            background-color: #f9fafb;
            border: 1px solid #e5e7eb;
            border-radius: 0.5rem;
          }
          .error-content {
            text-align: center;
            padding: 1rem;
          }
          .error-icon {
            font-size: 1.5rem;
            margin-bottom: 0.5rem;
            display: block;
          }
          .error-content h4 {
            color: #6b7280;
            margin-bottom: 0.25rem;
            font-size: 0.875rem;
          }
          .error-content p {
            color: #9ca3af;
            font-size: 0.75rem;
            margin-bottom: 1rem;
          }
          .retry-small-button {
            background-color: #6b7280;
            color: white;
            border: none;
            padding: 0.5rem 1rem;
            border-radius: 0.375rem;
            font-size: 0.75rem;
            cursor: pointer;
            transition: background-color 0.2s;
          }
          .retry-small-button:hover {
            background-color: #4b5563;
          }
        `}</style>
      </div>
    }
  >
    {children}
  </ErrorBoundary>
);

// API Error Boundary for handling data fetch errors
export const ApiErrorBoundary: React.FC<{ 
  children: ReactNode; 
  fallbackTitle?: string;
  fallbackMessage?: string;
  onRetry?: () => void;
}> = ({ 
  children, 
  fallbackTitle = "Data Load Error",
  fallbackMessage = "Unable to load data. Please try again.",
  onRetry 
}) => (
  <ErrorBoundary
    fallback={
      <div className="api-error">
        <div className="error-content">
          <div className="error-icon">🌐</div>
          <h3>{fallbackTitle}</h3>
          <p>{fallbackMessage}</p>
          <div className="error-actions">
            {onRetry && (
              <button onClick={onRetry} className="retry-button">
                Try Again
              </button>
            )}
            <button onClick={() => window.location.reload()} className="refresh-button">
              Refresh Page
            </button>
          </div>
        </div>
        <style jsx>{`
          .api-error {
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 200px;
            background-color: #fefbff;
            border: 1px solid #e0e7ff;
            border-radius: 0.75rem;
            margin: 1rem 0;
          }
          .error-content {
            text-align: center;
            padding: 2rem;
            max-width: 400px;
          }
          .error-icon {
            font-size: 2.5rem;
            margin-bottom: 1rem;
          }
          .error-content h3 {
            color: #1e40af;
            margin-bottom: 0.5rem;
            font-size: 1.125rem;
          }
          .error-content p {
            color: #64748b;
            margin-bottom: 1.5rem;
            line-height: 1.5;
          }
          .error-actions {
            display: flex;
            gap: 1rem;
            justify-content: center;
            flex-wrap: wrap;
          }
          .retry-button, .refresh-button {
            padding: 0.5rem 1rem;
            border-radius: 0.375rem;
            font-size: 0.875rem;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s;
            border: 1px solid transparent;
          }
          .retry-button {
            background-color: #1e40af;
            color: white;
            border-color: #1e40af;
          }
          .retry-button:hover {
            background-color: #1d4ed8;
            border-color: #1d4ed8;
          }
          .refresh-button {
            background-color: white;
            color: #64748b;
            border-color: #cbd5e1;
          }
          .refresh-button:hover {
            background-color: #f8fafc;
            border-color: #94a3b8;
          }
        `}</style>
      </div>
    }
  >
    {children}
  </ErrorBoundary>
);

// Route Error Boundary for handling routing errors
export const RouteErrorBoundary: React.FC<{ children: ReactNode }> = ({ children }) => (
  <ErrorBoundary
    fallback={
      <div className="route-error">
        <div className="error-content">
          <div className="error-icon">🧭</div>
          <h2>Page Error</h2>
          <p>There was a problem loading this page.</p>
          <div className="error-actions">
            <button onClick={() => window.history.back()} className="back-button">
              Go Back
            </button>
            <button onClick={() => window.location.href = '/'} className="home-button">
              Go Home
            </button>
          </div>
        </div>
        <style jsx>{`
          .route-error {
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 500px;
            background-color: #fefbff;
            margin: 2rem;
            border-radius: 1rem;
            border: 2px solid #e0e7ff;
          }
          .error-content {
            text-align: center;
            padding: 3rem;
            max-width: 500px;
          }
          .error-icon {
            font-size: 4rem;
            margin-bottom: 1.5rem;
          }
          .error-content h2 {
            color: #1e40af;
            margin-bottom: 1rem;
            font-size: 1.5rem;
          }
          .error-content p {
            color: #64748b;
            margin-bottom: 2rem;
            font-size: 1.125rem;
            line-height: 1.6;
          }
          .error-actions {
            display: flex;
            gap: 1rem;
            justify-content: center;
            flex-wrap: wrap;
          }
          .back-button, .home-button {
            padding: 0.75rem 1.5rem;
            border-radius: 0.5rem;
            font-size: 1rem;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s;
            border: 1px solid transparent;
          }
          .back-button {
            background-color: #6b7280;
            color: white;
            border-color: #6b7280;
          }
          .back-button:hover {
            background-color: #4b5563;
            border-color: #4b5563;
          }
          .home-button {
            background-color: #1e40af;
            color: white;
            border-color: #1e40af;
          }
          .home-button:hover {
            background-color: #1d4ed8;
            border-color: #1d4ed8;
          }
        `}</style>
      </div>
    }
  >
    {children}
  </ErrorBoundary>
);

// Async Error Boundary for handling async operations
export const AsyncErrorBoundary: React.FC<{ 
  children: ReactNode;
  asyncError?: Error | null;
  onClearError?: () => void;
}> = ({ children, asyncError, onClearError }) => {
  const [hasAsyncError, setHasAsyncError] = React.useState(false);

  React.useEffect(() => {
    if (asyncError) {
      setHasAsyncError(true);
    }
  }, [asyncError]);

  const handleClearError = () => {
    setHasAsyncError(false);
    onClearError?.();
  };

  if (hasAsyncError && asyncError) {
    return (
      <div className="async-error">
        <div className="error-content">
          <div className="error-icon">⚡</div>
          <h3>Operation Failed</h3>
          <p>An error occurred during the operation: {asyncError.message}</p>
          <button onClick={handleClearError} className="clear-error-button">
            Dismiss
          </button>
        </div>
        <style jsx>{`
          .async-error {
            background-color: #fef2f2;
            border: 1px solid #fecaca;
            border-radius: 0.5rem;
            padding: 1rem;
            margin: 1rem 0;
          }
          .error-content {
            display: flex;
            align-items: center;
            gap: 1rem;
          }
          .error-icon {
            font-size: 1.5rem;
            flex-shrink: 0;
          }
          .error-content h3 {
            color: #dc2626;
            margin: 0 0 0.25rem 0;
            font-size: 1rem;
          }
          .error-content p {
            color: #7f1d1d;
            margin: 0 0 0.5rem 0;
            font-size: 0.875rem;
          }
          .clear-error-button {
            background-color: #dc2626;
            color: white;
            border: none;
            padding: 0.375rem 0.75rem;
            border-radius: 0.25rem;
            font-size: 0.75rem;
            cursor: pointer;
            transition: background-color 0.2s;
            margin-left: auto;
          }
          .clear-error-button:hover {
            background-color: #b91c1c;
          }
        `}</style>
      </div>
    );
  }

  return (
    <ErrorBoundary>
      {children}
    </ErrorBoundary>
  );
};

// Global Error Handler Hook
export const useErrorHandler = () => {
  const [error, setError] = React.useState<Error | null>(null);

  const handleError = React.useCallback((error: Error) => {
    setError(error);
    console.error('Handled error:', error);
  }, []);

  const clearError = React.useCallback(() => {
    setError(null);
  }, []);

  const throwError = React.useCallback((error: Error) => {
    throw error;
  }, []);

  return {
    error,
    handleError,
    clearError,
    throwError
  };
};