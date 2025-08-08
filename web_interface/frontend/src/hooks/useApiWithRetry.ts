import React, { useCallback, useState } from 'react';
import { useQuery, useMutation, UseQueryOptions, UseMutationOptions } from '@tanstack/react-query';
import { useToastHelpers } from '../components/Toast';

// Enhanced error types
export interface ApiError extends Error {
  status?: number;
  code?: string;
  details?: any;
  retryable?: boolean;
}

// Retry configuration
interface RetryConfig {
  maxRetries?: number;
  baseDelay?: number;
  maxDelay?: number;
  backoffFactor?: number;
  retryCondition?: (error: ApiError, retryCount: number) => boolean;
}

const DEFAULT_RETRY_CONFIG: Required<RetryConfig> = {
  maxRetries: 3,
  baseDelay: 1000,
  maxDelay: 30000,
  backoffFactor: 2,
  retryCondition: (error: ApiError, retryCount: number) => {
    // Don't retry client errors (4xx) except for specific cases
    if (error.status && error.status >= 400 && error.status < 500) {
      // Retry on 408 (timeout), 429 (rate limit), 503 (service unavailable)
      return [408, 429, 503].includes(error.status);
    }
    
    // Retry server errors (5xx) and network errors
    if (!error.status || error.status >= 500) {
      return retryCount < DEFAULT_RETRY_CONFIG.maxRetries;
    }
    
    return false;
  },
};

// Calculate exponential backoff delay
const calculateDelay = (retryCount: number, config: Required<RetryConfig>): number => {
  const delay = config.baseDelay * Math.pow(config.backoffFactor, retryCount);
  return Math.min(delay, config.maxDelay);
};

// Enhanced API error creator
const createApiError = (error: any): ApiError => {
  const apiError = new Error(error.message || 'An unexpected error occurred') as ApiError;
  
  if (error.response) {
    apiError.status = error.response.status;
    apiError.details = error.response.data;
    
    // Set user-friendly messages based on status codes
    switch (error.response.status) {
      case 400:
        apiError.message = 'Invalid request. Please check your input.';
        break;
      case 401:
        apiError.message = 'Authentication required. Please log in again.';
        break;
      case 403:
        apiError.message = 'You do not have permission to perform this action.';
        break;
      case 404:
        apiError.message = 'The requested resource was not found.';
        break;
      case 408:
        apiError.message = 'Request timed out. Please try again.';
        apiError.retryable = true;
        break;
      case 429:
        apiError.message = 'Too many requests. Please wait a moment and try again.';
        apiError.retryable = true;
        break;
      case 500:
        apiError.message = 'Internal server error. Please try again later.';
        apiError.retryable = true;
        break;
      case 502:
        apiError.message = 'Service temporarily unavailable. Please try again.';
        apiError.retryable = true;
        break;
      case 503:
        apiError.message = 'Service unavailable. Please try again later.';
        apiError.retryable = true;
        break;
      default:
        if (error.response.status >= 500) {
          apiError.message = 'Server error. Please try again later.';
          apiError.retryable = true;
        }
    }
  } else if (error.request) {
    apiError.message = 'Network error. Please check your connection and try again.';
    apiError.retryable = true;
  }
  
  return apiError;
};

// Enhanced useQuery with retry logic and error handling
export function useApiQuery<TData = unknown, TError = ApiError>(
  queryKey: unknown[],
  queryFn: () => Promise<TData>,
  options: Omit<UseQueryOptions<TData, TError>, 'queryKey' | 'queryFn'> & {
    retryConfig?: RetryConfig;
    showErrorToast?: boolean;
    errorToastTitle?: string;
  } = {}
) {
  const { showError } = useToastHelpers();
  const { retryConfig = {}, showErrorToast = true, errorToastTitle = 'Error', ...queryOptions } = options;
  
  const config = { ...DEFAULT_RETRY_CONFIG, ...retryConfig };

  const query = useQuery({
    queryKey,
    queryFn: async () => {
      try {
        return await queryFn();
      } catch (error) {
        throw createApiError(error);
      }
    },
    retry: (failureCount, error) => {
      const apiError = error as ApiError;
      return config.retryCondition(apiError, failureCount);
    },
    retryDelay: (failureCount) => {
      return calculateDelay(failureCount - 1, config);
    },
    ...queryOptions,
  });

  // Handle error toast separately using useEffect
  React.useEffect(() => {
    if (query.error && showErrorToast) {
      const apiError = query.error as unknown as ApiError;
      showError(
        errorToastTitle,
        apiError.message || 'An unexpected error occurred',
        !apiError.retryable
      );
    }
  }, [query.error, showErrorToast, showError, errorToastTitle]);

  return query;
}

// Enhanced useMutation with retry logic and error handling
export function useApiMutation<TData = unknown, TError = ApiError, TVariables = void>(
  mutationFn: (variables: TVariables) => Promise<TData>,
  options: UseMutationOptions<TData, TError, TVariables> & {
    retryConfig?: RetryConfig;
    showErrorToast?: boolean;
    showSuccessToast?: boolean;
    errorToastTitle?: string;
    successToastTitle?: string;
  } = {}
) {
  const { showError, showSuccess } = useToastHelpers();
  const [retryCount, setRetryCount] = useState(0);
  
  const {
    retryConfig = {},
    showErrorToast = true,
    showSuccessToast = false,
    errorToastTitle = 'Error',
    successToastTitle = 'Success',
    ...mutationOptions
  } = options;
  
  const config = { ...DEFAULT_RETRY_CONFIG, ...retryConfig };

  const retryMutation = useCallback(async (variables: TVariables, currentRetryCount = 0): Promise<TData> => {
    try {
      return await mutationFn(variables);
    } catch (error) {
      const apiError = createApiError(error);
      
      if (config.retryCondition(apiError, currentRetryCount) && currentRetryCount < config.maxRetries) {
        const delay = calculateDelay(currentRetryCount, config);
        setRetryCount(currentRetryCount + 1);
        
        await new Promise(resolve => setTimeout(resolve, delay));
        return retryMutation(variables, currentRetryCount + 1);
      }
      
      throw apiError;
    }
  }, [mutationFn, config]);

  const mutation = useMutation({
    mutationFn: (variables: TVariables) => {
      setRetryCount(0);
      return retryMutation(variables);
    },
    ...mutationOptions,
  });

  // Handle success and error toasts using useEffect
  React.useEffect(() => {
    if (mutation.isSuccess && showSuccessToast && !mutation.isPending) {
      showSuccess(successToastTitle);
    }
  }, [mutation.isSuccess, mutation.isPending, showSuccessToast, showSuccess, successToastTitle]);

  React.useEffect(() => {
    if (mutation.error && showErrorToast) {
      const apiError = mutation.error as unknown as ApiError;
      showError(
        errorToastTitle,
        apiError.message || 'An unexpected error occurred',
        !apiError.retryable
      );
    }
  }, [mutation.error, showErrorToast, showError, errorToastTitle]);

  // Call original success/error handlers if provided
  React.useEffect(() => {
    if (mutation.isSuccess && mutationOptions.onSuccess && mutation.data) {
      mutationOptions.onSuccess(mutation.data, mutation.variables as TVariables, mutation.context);
    }
  }, [mutation.isSuccess, mutation.data, mutation.variables, mutation.context, mutationOptions]);

  React.useEffect(() => {
    if (mutation.error && mutationOptions.onError) {
      mutationOptions.onError(mutation.error, mutation.variables as TVariables, mutation.context);
    }
  }, [mutation.error, mutation.variables, mutation.context, mutationOptions]);

  return mutation;
}

// Manual retry hook for user-initiated retries
export function useManualRetry() {
  const [isRetrying, setIsRetrying] = useState(false);

  const retry = useCallback(async (retryFn: () => Promise<any>) => {
    if (isRetrying) return;
    
    setIsRetrying(true);
    try {
      await retryFn();
    } finally {
      setIsRetrying(false);
    }
  }, [isRetrying]);

  return { retry, isRetrying };
}

// Connection status hook
export function useConnectionStatus() {
  const [isOnline, setIsOnline] = useState(navigator.onLine);

  React.useEffect(() => {
    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  return isOnline;
}

// Error reporting hook
export function useErrorReporting() {
  const reportError = useCallback((error: Error, context?: Record<string, any>) => {
    const errorReport = {
      message: error.message,
      stack: error.stack,
      timestamp: new Date().toISOString(),
      url: window.location.href,
      userAgent: navigator.userAgent,
      context,
    };

    // In development, log to console
    if (process.env.NODE_ENV === 'development') {
      console.group('🚨 Error Report');
      console.error('Error:', error);
      console.table(errorReport);
      console.groupEnd();
    }

    // In production, send to monitoring service
    // monitoringService.captureException(error, { extra: errorReport });
  }, []);

  return { reportError };
}