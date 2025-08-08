import React, { createContext, useContext, useReducer, useCallback, ReactNode } from 'react';
import { 
  StandardizedError, 
  ErrorCode, 
  createStandardizedError, 
  shouldReportError, 
  ErrorContextType 
} from '../utils/errorSystem';

// Error state management
interface ErrorState {
  errors: StandardizedError[];
  currentError: StandardizedError | null;
  errorHistory: StandardizedError[];
  isReporting: boolean;
}

type ErrorAction = 
  | { type: 'ADD_ERROR'; payload: StandardizedError }
  | { type: 'CLEAR_ERROR'; payload?: string }
  | { type: 'CLEAR_ALL_ERRORS' }
  | { type: 'SET_REPORTING'; payload: boolean }
  | { type: 'SET_CURRENT_ERROR'; payload: StandardizedError | null };

const initialState: ErrorState = {
  errors: [],
  currentError: null,
  errorHistory: [],
  isReporting: false
};

const errorReducer = (state: ErrorState, action: ErrorAction): ErrorState => {
  switch (action.type) {
    case 'ADD_ERROR':
      return {
        ...state,
        errors: [...state.errors, action.payload],
        errorHistory: [...state.errorHistory, action.payload].slice(-50), // Keep last 50 errors
        currentError: action.payload
      };
      
    case 'CLEAR_ERROR':
      if (action.payload) {
        // Clear specific error by ID
        return {
          ...state,
          errors: state.errors.filter(error => error.errorId !== action.payload),
          currentError: state.currentError?.errorId === action.payload ? null : state.currentError
        };
      } else {
        // Clear current error
        return {
          ...state,
          currentError: null
        };
      }
      
    case 'CLEAR_ALL_ERRORS':
      return {
        ...state,
        errors: [],
        currentError: null
      };
      
    case 'SET_REPORTING':
      return {
        ...state,
        isReporting: action.payload
      };
      
    case 'SET_CURRENT_ERROR':
      return {
        ...state,
        currentError: action.payload
      };
      
    default:
      return state;
  }
};

// Error Context
const ErrorContext = createContext<ErrorContextType & {
  errors: StandardizedError[];
  errorHistory: StandardizedError[];
  isReporting: boolean;
  addError: (error: StandardizedError | Error) => void;
  clearError: (errorId?: string) => void;
  clearAllErrors: () => void;
  reportError: (error: StandardizedError | Error) => Promise<void>;
  getErrorStats: () => { total: number; byCategory: Record<string, number>; bySeverity: Record<string, number> };
} | null>(null);

// Error monitoring and reporting service
class ErrorReportingService {
  private static instance: ErrorReportingService;
  private reportQueue: StandardizedError[] = [];
  private isProcessing = false;

  static getInstance(): ErrorReportingService {
    if (!ErrorReportingService.instance) {
      ErrorReportingService.instance = new ErrorReportingService();
    }
    return ErrorReportingService.instance;
  }

  async reportError(error: StandardizedError): Promise<void> {
    // In development, just log to console
    if (process.env.NODE_ENV === 'development') {
      console.group(`🚨 Error Report - ${error.details.code}`);
      console.error('Error Details:', error.toReportData());
      console.error('User Message:', error.toUserMessage());
      console.error('Suggested Actions:', error.getSuggestedActions());
      console.groupEnd();
      return;
    }

    // Add to queue for batch processing
    this.reportQueue.push(error);
    
    if (!this.isProcessing) {
      this.processQueue();
    }
  }

  private async processQueue(): Promise<void> {
    if (this.reportQueue.length === 0) return;

    this.isProcessing = true;
    
    try {
      // In a real application, send to monitoring service
      // Example: Sentry, LogRocket, Bugsnag, etc.
      const errorsToReport = [...this.reportQueue];
      this.reportQueue = [];

      // Mock API call to error reporting service
      await this.sendToMonitoringService(errorsToReport);
      
    } catch (reportingError) {
      console.error('Failed to report errors:', reportingError);
      // Put errors back in queue for retry
      this.reportQueue = [...this.reportQueue, ...this.reportQueue];
    } finally {
      this.isProcessing = false;
      
      // Process any new errors that came in
      if (this.reportQueue.length > 0) {
        setTimeout(() => this.processQueue(), 5000); // Retry after 5 seconds
      }
    }
  }

  private async sendToMonitoringService(errors: StandardizedError[]): Promise<void> {
    // Mock implementation - replace with actual service
    const payload = {
      timestamp: new Date().toISOString(),
      errors: errors.map(error => error.toReportData()),
      sessionId: this.getSessionId(),
      userId: this.getUserId(),
      appVersion: process.env.REACT_APP_VERSION || 'unknown'
    };

    // In production, send to your monitoring service
    // await fetch('/api/errors/report', {
    //   method: 'POST',
    //   headers: { 'Content-Type': 'application/json' },
    //   body: JSON.stringify(payload)
    // });

    console.log('Would send error report:', payload);
  }

  private getSessionId(): string {
    // Get or create session ID
    let sessionId = sessionStorage.getItem('errorSessionId');
    if (!sessionId) {
      sessionId = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      sessionStorage.setItem('errorSessionId', sessionId);
    }
    return sessionId;
  }

  private getUserId(): string | null {
    // Get user ID from your auth system
    return localStorage.getItem('userId') || null;
  }
}

// Error Provider Component
interface ErrorProviderProps {
  children: ReactNode;
  onError?: (error: StandardizedError) => void;
  maxErrors?: number;
}

export const ErrorProvider: React.FC<ErrorProviderProps> = ({ 
  children, 
  onError,
  maxErrors = 10 
}) => {
  const [state, dispatch] = useReducer(errorReducer, initialState);
  const reportingService = ErrorReportingService.getInstance();

  const addError = useCallback((error: StandardizedError | Error) => {
    let standardizedError: StandardizedError;
    
    if (error instanceof StandardizedError) {
      standardizedError = error;
    } else {
      // Convert regular Error to StandardizedError
      standardizedError = createStandardizedError(
        ErrorCode.UNKNOWN_ERROR, 
        error, 
        { source: 'ErrorProvider' }
      );
    }

    dispatch({ type: 'ADD_ERROR', payload: standardizedError });

    // Call custom error handler if provided
    onError?.(standardizedError);

    // Auto-report if configured
    if (standardizedError.shouldReport()) {
      reportError(standardizedError);
    }

    // Limit number of stored errors to prevent memory issues
    if (state.errors.length >= maxErrors) {
      // Remove oldest errors
      const errorsToRemove = state.errors.slice(0, state.errors.length - maxErrors + 1);
      errorsToRemove.forEach(err => {
        dispatch({ type: 'CLEAR_ERROR', payload: err.errorId });
      });
    }
  }, [state.errors.length, maxErrors, onError]);

  const clearError = useCallback((errorId?: string) => {
    if (errorId) {
      dispatch({ type: 'CLEAR_ERROR', payload: errorId });
    } else {
      dispatch({ type: 'CLEAR_ERROR' });
    }
  }, []);

  const clearAllErrors = useCallback(() => {
    dispatch({ type: 'CLEAR_ALL_ERRORS' });
  }, []);

  const reportError = useCallback(async (error: StandardizedError | Error) => {
    let standardizedError: StandardizedError;
    
    if (error instanceof StandardizedError) {
      standardizedError = error;
    } else if (shouldReportError(error)) {
      standardizedError = createStandardizedError(
        ErrorCode.UNKNOWN_ERROR,
        error,
        { source: 'manual_report' }
      );
    } else {
      return; // Don't report non-reportable errors
    }

    dispatch({ type: 'SET_REPORTING', payload: true });
    
    try {
      await reportingService.reportError(standardizedError);
    } catch (reportingError) {
      console.error('Failed to report error:', reportingError);
    } finally {
      dispatch({ type: 'SET_REPORTING', payload: false });
    }
  }, []);

  const getErrorStats = useCallback(() => {
    const byCategory: Record<string, number> = {};
    const bySeverity: Record<string, number> = {};

    state.errorHistory.forEach(error => {
      byCategory[error.details.category] = (byCategory[error.details.category] || 0) + 1;
      bySeverity[error.details.severity] = (bySeverity[error.details.severity] || 0) + 1;
    });

    return {
      total: state.errorHistory.length,
      byCategory,
      bySeverity
    };
  }, [state.errorHistory]);

  const contextValue = {
    errors: state.errors,
    currentError: state.currentError,
    errorHistory: state.errorHistory,
    isReporting: state.isReporting,
    addError,
    clearError,
    clearAllErrors,
    reportError,
    getErrorStats
  };

  return (
    <ErrorContext.Provider value={contextValue}>
      {children}
    </ErrorContext.Provider>
  );
};

// Hook to use error context
export const useErrorContext = () => {
  const context = useContext(ErrorContext);
  if (!context) {
    throw new Error('useErrorContext must be used within an ErrorProvider');
  }
  return context;
};

// Hook for convenient error handling
export const useErrorHandler = () => {
  const { addError, clearError, currentError } = useErrorContext();

  const handleError = useCallback((error: Error | StandardizedError) => {
    addError(error);
  }, [addError]);

  const handleAsyncError = useCallback(async (asyncFn: () => Promise<any>) => {
    try {
      return await asyncFn();
    } catch (error) {
      handleError(error as Error);
      throw error; // Re-throw for caller to handle
    }
  }, [handleError]);

  const createErrorHandler = useCallback((errorCode: ErrorCode, metadata?: Record<string, any>) => {
    return (error: Error) => {
      const standardizedError = createStandardizedError(errorCode, error, metadata);
      addError(standardizedError);
    };
  }, [addError]);

  return {
    handleError,
    handleAsyncError,
    createErrorHandler,
    clearError,
    currentError
  };
};

// HOC for error boundary integration
export const withErrorHandling = <P extends object>(
  Component: React.ComponentType<P>,
  errorCode: ErrorCode = ErrorCode.COMPONENT_CRASH,
  metadata?: Record<string, any>
) => {
  const WrappedComponent: React.FC<P> = (props) => {
    const { addError } = useErrorContext();

    const handleComponentError = useCallback((error: Error) => {
      const standardizedError = createStandardizedError(errorCode, error, {
        componentName: Component.displayName || Component.name,
        ...metadata
      });
      addError(standardizedError);
    }, [addError]);

    return (
      <ErrorBoundaryWrapper onError={handleComponentError}>
        <Component {...props} />
      </ErrorBoundaryWrapper>
    );
  };

  WrappedComponent.displayName = `withErrorHandling(${Component.displayName || Component.name})`;
  
  return WrappedComponent;
};

// Simple error boundary for HOC
interface ErrorBoundaryWrapperProps {
  children: ReactNode;
  onError: (error: Error) => void;
}

interface ErrorBoundaryWrapperState {
  hasError: boolean;
}

class ErrorBoundaryWrapper extends React.Component<ErrorBoundaryWrapperProps, ErrorBoundaryWrapperState> {
  constructor(props: ErrorBoundaryWrapperProps) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(_error: Error): ErrorBoundaryWrapperState {
    return { hasError: true };
  }

  componentDidCatch(error: Error) {
    this.props.onError(error);
  }

  render() {
    if (this.state.hasError) {
      return null; // Let parent error boundary handle display
    }

    return this.props.children;
  }
}

export default ErrorProvider;