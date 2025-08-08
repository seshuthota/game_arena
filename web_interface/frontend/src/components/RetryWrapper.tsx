import React, { useState, useCallback, useEffect } from 'react';
import { 
  retryWithBackoff, 
  RetryConfig, 
  RetryResult, 
  RETRY_CONFIGS, 
  useRetry 
} from '../utils/retryMechanism';
import { 
  StandardizedError, 
  ErrorCode, 
  createStandardizedError 
} from '../utils/errorSystem';
import { LoadingButton, CircularProgress } from './LoadingStates';

// Retry Button Component
interface RetryButtonProps {
  onRetry: () => Promise<void>;
  retryConfig?: RetryConfig;
  disabled?: boolean;
  children?: React.ReactNode;
  variant?: 'primary' | 'secondary' | 'danger';
  showProgress?: boolean;
  className?: string;
}

export const RetryButton: React.FC<RetryButtonProps> = ({
  onRetry,
  retryConfig = RETRY_CONFIGS.api,
  disabled = false,
  children = 'Retry',
  variant = 'primary',
  showProgress = false,
  className = ''
}) => {
  const { executeWithRetry, isRetrying, attempts } = useRetry(retryConfig);

  const handleRetry = useCallback(async () => {
    try {
      await executeWithRetry(onRetry);
    } catch (error) {
      // Error handling is managed by the retry hook
      console.error('Retry failed after all attempts:', error);
    }
  }, [executeWithRetry, onRetry]);

  return (
    <LoadingButton
      onClick={handleRetry}
      isLoading={isRetrying}
      disabled={disabled || isRetrying}
      variant={variant}
      className={`retry-button ${className}`}
      loadingText={attempts > 0 ? `Retrying (${attempts})...` : 'Retrying...'}
    >
      {children}
      {showProgress && isRetrying && (
        <span className="retry-attempts">
          {attempts > 0 && ` (Attempt ${attempts})`}
        </span>
      )}
    </LoadingButton>
  );
};

// Retry Wrapper for automatic retry of failed operations
interface RetryWrapperProps {
  children: (retry: () => Promise<void>) => React.ReactNode;
  operation: () => Promise<any>;
  retryConfig?: RetryConfig;
  fallback?: React.ReactNode;
  onSuccess?: (data: any, attempts: number) => void;
  onFinalFailure?: (error: Error, attempts: number) => void;
  showRetryButton?: boolean;
  autoRetry?: boolean;
}

export const RetryWrapper: React.FC<RetryWrapperProps> = ({
  children,
  operation,
  retryConfig = RETRY_CONFIGS.api,
  fallback,
  onSuccess,
  onFinalFailure,
  showRetryButton = true,
  autoRetry = false
}) => {
  const [state, setState] = useState<{
    isLoading: boolean;
    error: Error | null;
    data: any;
    attempts: number;
  }>({
    isLoading: true,
    error: null,
    data: null,
    attempts: 0
  });

  const executeOperation = useCallback(async () => {
    setState(prev => ({ ...prev, isLoading: true, error: null }));

    try {
      const result = await retryWithBackoff(operation, {
        ...retryConfig,
        onRetry: (error, attempt, delay) => {
          setState(prev => ({ ...prev, attempts: attempt }));
          (retryConfig as RetryConfig).onRetry?.(error, attempt, delay);
        }
      });

      if (result.success) {
        setState({
          isLoading: false,
          error: null,
          data: result.data,
          attempts: result.attempts
        });
        onSuccess?.(result.data, result.attempts);
      } else {
        setState(prev => ({
          ...prev,
          isLoading: false,
          error: result.lastError || new Error('Operation failed'),
          attempts: result.attempts
        }));
        onFinalFailure?.(result.lastError || new Error('Operation failed'), result.attempts);
      }
    } catch (error) {
      const err = error as Error;
      setState(prev => ({
        ...prev,
        isLoading: false,
        error: err,
        attempts: prev.attempts + 1
      }));
      onFinalFailure?.(err, state.attempts + 1);
    }
  }, [operation, retryConfig, onSuccess, onFinalFailure]);

  useEffect(() => {
    executeOperation();
  }, []);

  // Auto-retry logic
  useEffect(() => {
    if (autoRetry && state.error && state.attempts < retryConfig.maxAttempts) {
      const delay = 5000; // 5 second delay for auto-retry
      const timeoutId = setTimeout(() => {
        executeOperation();
      }, delay);

      return () => clearTimeout(timeoutId);
    }
    return undefined;
  }, [autoRetry, state.error, state.attempts, retryConfig.maxAttempts, executeOperation]);

  if (state.isLoading) {
    return (
      <div className="retry-wrapper-loading">
        <CircularProgress 
          progress={state.attempts > 0 ? (state.attempts / retryConfig.maxAttempts) * 100 : 0}
          size={60}
          showText={false}
        />
        <div className="loading-message">
          {state.attempts > 0 
            ? `Retrying... (Attempt ${state.attempts}/${retryConfig.maxAttempts})`
            : 'Loading...'
          }
        </div>
        <style jsx>{`
          .retry-wrapper-loading {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 2rem;
            gap: 1rem;
          }
          .loading-message {
            font-size: 0.875rem;
            color: #6b7280;
            text-align: center;
          }
        `}</style>
      </div>
    );
  }

  if (state.error) {
    if (fallback) {
      return <>{fallback}</>;
    }

    return (
      <div className="retry-wrapper-error">
        <div className="error-content">
          <div className="error-icon">⚠️</div>
          <h3 className="error-title">Operation Failed</h3>
          <p className="error-message">
            {state.error.message}
          </p>
          <p className="error-attempts">
            Failed after {state.attempts} attempt{state.attempts !== 1 ? 's' : ''}
          </p>
          {showRetryButton && (
            <RetryButton
              onRetry={executeOperation}
              retryConfig={retryConfig}
              showProgress={true}
            />
          )}
        </div>
        <style jsx>{`
          .retry-wrapper-error {
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 2rem;
            background-color: #fef2f2;
            border: 1px solid #fecaca;
            border-radius: 0.75rem;
            margin: 1rem 0;
          }
          .error-content {
            text-align: center;
            max-width: 400px;
          }
          .error-icon {
            font-size: 2.5rem;
            margin-bottom: 1rem;
          }
          .error-title {
            color: #dc2626;
            margin-bottom: 0.5rem;
            font-size: 1.125rem;
          }
          .error-message {
            color: #7f1d1d;
            margin-bottom: 0.5rem;
            line-height: 1.5;
          }
          .error-attempts {
            color: #9ca3af;
            font-size: 0.875rem;
            margin-bottom: 1.5rem;
          }
        `}</style>
      </div>
    );
  }

  return <>{children(executeOperation)}</>;
};

// Smart Retry Component that adapts based on error types
interface SmartRetryProps {
  children: React.ReactNode;
  onError?: (error: StandardizedError) => void;
  maxRetries?: number;
}

export const SmartRetry: React.FC<SmartRetryProps> = ({
  children,
  onError,
  maxRetries = 3
}) => {
  const [retryCount, setRetryCount] = useState(0);
  const [lastError, setLastError] = useState<StandardizedError | null>(null);

  const getRetryConfigForError = (error: StandardizedError): RetryConfig => {
    switch (error.details.category) {
      case 'network':
        return RETRY_CONFIGS.network;
      case 'data':
        return RETRY_CONFIGS.api;
      case 'system':
        return RETRY_CONFIGS.background;
      default:
        return RETRY_CONFIGS.api;
    }
  };

  const handleRetry = useCallback(async () => {
    if (!lastError || retryCount >= maxRetries) return;

    const config = getRetryConfigForError(lastError);
    setRetryCount(prev => prev + 1);

    try {
      // Clear error and retry
      setLastError(null);
      // The retry logic would be handled by the parent component
    } catch (error) {
      const standardizedError = error instanceof StandardizedError 
        ? error 
        : createStandardizedError(ErrorCode.UNKNOWN_ERROR, error as Error);
      
      setLastError(standardizedError);
      onError?.(standardizedError);
    }
  }, [lastError, retryCount, maxRetries, onError]);

  const shouldShowRetryButton = lastError?.details.retryable && retryCount < maxRetries;

  if (lastError && shouldShowRetryButton) {
    return (
      <div className="smart-retry-error">
        <div className="error-info">
          <h4>{lastError.details.title}</h4>
          <p>{lastError.details.userMessage}</p>
          <div className="error-meta">
            <span>Attempt {retryCount}/{maxRetries}</span>
            <span>•</span>
            <span>{lastError.details.category} error</span>
          </div>
        </div>
        <RetryButton
          onRetry={handleRetry}
          retryConfig={getRetryConfigForError(lastError)}
          showProgress={true}
        />
        <style jsx>{`
          .smart-retry-error {
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 1.5rem;
            padding: 2rem;
            background-color: #fefbff;
            border: 1px solid #e0e7ff;
            border-radius: 0.75rem;
            text-align: center;
          }
          .error-info h4 {
            color: #1e40af;
            margin-bottom: 0.5rem;
          }
          .error-info p {
            color: #64748b;
            margin-bottom: 1rem;
            line-height: 1.5;
          }
          .error-meta {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            font-size: 0.875rem;
            color: #9ca3af;
          }
        `}</style>
      </div>
    );
  }

  return <>{children}</>;
};

// Retry Status Indicator
interface RetryStatusProps {
  isRetrying: boolean;
  attempts: number;
  maxAttempts: number;
  nextRetryIn?: number; // seconds until next retry
}

export const RetryStatus: React.FC<RetryStatusProps> = ({
  isRetrying,
  attempts,
  maxAttempts,
  nextRetryIn
}) => {
  const [countdown, setCountdown] = useState(nextRetryIn || 0);

  useEffect(() => {
    if (nextRetryIn && nextRetryIn > 0) {
      setCountdown(nextRetryIn);
      const interval = setInterval(() => {
        setCountdown(prev => {
          if (prev <= 1) {
            clearInterval(interval);
            return 0;
          }
          return prev - 1;
        });
      }, 1000);

      return () => clearInterval(interval);
    }
    return undefined;
  }, [nextRetryIn]);

  if (!isRetrying && attempts === 0) return null;

  return (
    <div className="retry-status">
      <div className="retry-indicator">
        {isRetrying && <div className="retry-spinner" />}
        <div className="retry-text">
          {isRetrying 
            ? `Retrying... (${attempts}/${maxAttempts})`
            : countdown > 0 
              ? `Retrying in ${countdown}s`
              : `Retry attempt ${attempts}/${maxAttempts}`
          }
        </div>
      </div>
      <div className="retry-progress">
        <div 
          className="retry-progress-bar"
          style={{ width: `${(attempts / maxAttempts) * 100}%` }}
        />
      </div>

      <style jsx>{`
        .retry-status {
          background-color: #f0f9ff;
          border: 1px solid #bae6fd;
          border-radius: 0.5rem;
          padding: 1rem;
          margin: 0.5rem 0;
        }

        .retry-indicator {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          margin-bottom: 0.5rem;
        }

        .retry-spinner {
          width: 1rem;
          height: 1rem;
          border: 2px solid #bae6fd;
          border-top: 2px solid #0ea5e9;
          border-radius: 50%;
          animation: spin 1s linear infinite;
        }

        .retry-text {
          font-size: 0.875rem;
          color: #0c4a6e;
          font-weight: 500;
        }

        .retry-progress {
          width: 100%;
          height: 0.25rem;
          background-color: #e0f2fe;
          border-radius: 0.125rem;
          overflow: hidden;
        }

        .retry-progress-bar {
          height: 100%;
          background-color: #0ea5e9;
          transition: width 0.3s ease;
          border-radius: 0.125rem;
        }

        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
};

export default RetryWrapper;