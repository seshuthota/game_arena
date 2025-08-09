// Comprehensive retry mechanism with exponential backoff and jitter
export interface RetryConfig {
  maxAttempts: number;
  baseDelay: number; // Initial delay in milliseconds
  maxDelay: number; // Maximum delay between retries
  backoffMultiplier: number; // Multiplier for exponential backoff
  jitter: boolean; // Add random jitter to prevent thundering herd
  retryCondition?: (error: any, attempt: number) => boolean;
  onRetry?: (error: any, attempt: number, delay: number) => void;
  timeout?: number; // Individual request timeout
}

export interface RetryResult<T> {
  data?: T;
  success: boolean;
  attempts: number;
  totalDuration: number;
  lastError?: Error;
}

// Default retry configurations for different scenarios
export const RETRY_CONFIGS = {
  // Network requests - aggressive retry for transient failures
  network: {
    maxAttempts: 3,
    baseDelay: 1000,
    maxDelay: 10000,
    backoffMultiplier: 2,
    jitter: true,
    timeout: 10000,
    retryCondition: (error: any) => {
      // Retry on network errors, timeouts, and 5xx status codes
      if (error?.code === 'NETWORK_ERROR' || error?.message?.includes('network')) return true;
      if (error?.code === 'TIMEOUT' || error?.message?.includes('timeout')) return true;
      if (error?.status >= 500 && error?.status < 600) return true;
      if (error?.status === 429) return true; // Rate limited
      return false;
    }
  },
  
  // API calls - moderate retry for server errors
  api: {
    maxAttempts: 2,
    baseDelay: 2000,
    maxDelay: 8000,
    backoffMultiplier: 2,
    jitter: true,
    timeout: 15000,
    retryCondition: (error: any) => {
      // Only retry server errors and rate limits
      if (error?.status >= 500 && error?.status < 600) return true;
      if (error?.status === 429) return true;
      return false;
    }
  },
  
  // Critical operations - limited retry to prevent infinite loops
  critical: {
    maxAttempts: 1,
    baseDelay: 5000,
    maxDelay: 5000,
    backoffMultiplier: 1,
    jitter: false,
    timeout: 20000,
    retryCondition: (error: any) => {
      // Only retry clear server errors
      return error?.status >= 500 && error?.status < 600;
    }
  },
  
  // Background operations - patient retry
  background: {
    maxAttempts: 5,
    baseDelay: 5000,
    maxDelay: 60000,
    backoffMultiplier: 1.5,
    jitter: true,
    retryCondition: (error: any) => {
      // Retry most transient failures
      if (error?.status >= 500) return true;
      if (error?.status === 429) return true;
      if (error?.code === 'NETWORK_ERROR') return true;
      return false;
    }
  }
} as const;

// Calculate delay with exponential backoff and optional jitter
export const calculateDelay = (
  attempt: number,
  config: RetryConfig
): number => {
  const exponentialDelay = Math.min(
    config.baseDelay * Math.pow(config.backoffMultiplier, attempt),
    config.maxDelay
  );

  if (!config.jitter) {
    return exponentialDelay;
  }

  // Add jitter (±25% of the calculated delay)
  const jitterRange = exponentialDelay * 0.25;
  const jitter = (Math.random() - 0.5) * 2 * jitterRange;
  
  return Math.max(0, exponentialDelay + jitter);
};

// Sleep utility
export const sleep = (ms: number): Promise<void> => {
  return new Promise(resolve => setTimeout(resolve, ms));
};

// Main retry function with comprehensive error handling
export async function retryWithBackoff<T>(
  operation: () => Promise<T>,
  config: RetryConfig
): Promise<RetryResult<T>> {
  const startTime = Date.now();
  let lastError: Error | undefined;
  let attempt = 0;

  while (attempt < config.maxAttempts) {
    try {
      // Add timeout wrapper if configured
      const result = config.timeout 
        ? await withTimeout(operation(), config.timeout)
        : await operation();
        
      return {
        data: result,
        success: true,
        attempts: attempt + 1,
        totalDuration: Date.now() - startTime
      };
    } catch (error) {
      lastError = error as Error;
      attempt++;
      
      // Check if we should retry this error
      if (config.retryCondition && !config.retryCondition(error, attempt)) {
        break;
      }
      
      // Don't retry on the last attempt
      if (attempt >= config.maxAttempts) {
        break;
      }
      
      const delay = calculateDelay(attempt - 1, config);
      
      // Call onRetry callback if provided
      config.onRetry?.(error, attempt, delay);
      
      // Wait before retrying
      await sleep(delay);
    }
  }

  return {
    success: false,
    attempts: attempt,
    totalDuration: Date.now() - startTime,
    lastError
  };
}

// Timeout wrapper utility
export const withTimeout = <T>(
  promise: Promise<T>, 
  timeoutMs: number
): Promise<T> => {
  return new Promise((resolve, reject) => {
    const timeoutId = setTimeout(() => {
      reject(new Error(`Operation timed out after ${timeoutMs}ms`));
    }, timeoutMs);

    promise
      .then(resolve)
      .catch(reject)
      .finally(() => clearTimeout(timeoutId));
  });
};

// Circuit breaker pattern to prevent cascading failures
export class CircuitBreaker {
  private failures = 0;
  private lastFailureTime: number | null = null;
  private state: 'closed' | 'open' | 'half-open' = 'closed';

  constructor(
    private readonly failureThreshold: number = 5,
    private readonly recoveryTimeout: number = 60000, // 1 minute
    private readonly successThreshold: number = 3 // Successes needed to close circuit
  ) {}

  async execute<T>(operation: () => Promise<T>): Promise<T> {
    if (this.state === 'open') {
      if (this.shouldAttemptReset()) {
        this.state = 'half-open';
      } else {
        throw new Error('Circuit breaker is open - operation not attempted');
      }
    }

    try {
      const result = await operation();
      this.onSuccess();
      return result;
    } catch (error) {
      this.onFailure();
      throw error;
    }
  }

  private shouldAttemptReset(): boolean {
    return this.lastFailureTime !== null && 
           Date.now() - this.lastFailureTime >= this.recoveryTimeout;
  }

  private onSuccess(): void {
    this.failures = 0;
    this.state = 'closed';
    this.lastFailureTime = null;
  }

  private onFailure(): void {
    this.failures++;
    this.lastFailureTime = Date.now();
    
    if (this.failures >= this.failureThreshold) {
      this.state = 'open';
    }
  }

  getState(): 'closed' | 'open' | 'half-open' {
    return this.state;
  }

  getFailureCount(): number {
    return this.failures;
  }

  reset(): void {
    this.failures = 0;
    this.state = 'closed';
    this.lastFailureTime = null;
  }
}

// Retry hook for React components
export const useRetry = (config: RetryConfig = RETRY_CONFIGS.api) => {
  const [retryState, setRetryState] = React.useState<{
    isRetrying: boolean;
    attempts: number;
    lastError?: Error;
  }>({
    isRetrying: false,
    attempts: 0
  });

  const executeWithRetry = React.useCallback(async <T>(
    operation: () => Promise<T>
  ): Promise<RetryResult<T>> => {
    setRetryState({ isRetrying: true, attempts: 0 });

    const enhancedConfig = {
      ...config,
      onRetry: (error: any, attempt: number, delay: number) => {
        setRetryState({
          isRetrying: true,
          attempts: attempt,
          lastError: error
        });
        config.onRetry?.(error, attempt, delay);
      }
    };

    const result = await retryWithBackoff(operation, enhancedConfig);
    
    setRetryState({
      isRetrying: false,
      attempts: result.attempts,
      lastError: result.lastError
    });

    return result;
  }, [config]);

  return {
    executeWithRetry,
    ...retryState
  };
};

// Batch retry for multiple operations
export const retryBatch = async <T>(
  operations: Array<() => Promise<T>>,
  config: RetryConfig,
  options: {
    failFast?: boolean; // Stop on first failure
    maxConcurrent?: number; // Limit concurrent operations
  } = {}
): Promise<Array<RetryResult<T>>> => {
  const { failFast = false, maxConcurrent = operations.length } = options;
  const results: Array<RetryResult<T>> = [];
  const errors: Error[] = [];

  // Process operations in batches to limit concurrency
  for (let i = 0; i < operations.length; i += maxConcurrent) {
    const batch = operations.slice(i, i + maxConcurrent);
    const batchPromises = batch.map(operation => 
      retryWithBackoff(operation, config)
    );

    const batchResults = await Promise.all(batchPromises);
    results.push(...batchResults);

    // Check for failures if failFast is enabled
    if (failFast) {
      const failures = batchResults.filter(result => !result.success);
      if (failures.length > 0) {
        failures.forEach(failure => {
          if (failure.lastError) errors.push(failure.lastError);
        });
        // Fallback for environments without AggregateError
        const AggregateErrorPolyfill = (globalThis as any).AggregateError || class extends Error {
          constructor(errors: Error[], message: string) {
            super(message);
            this.name = 'AggregateError';
            (this as any).errors = errors;
          }
        };
        throw new AggregateErrorPolyfill(errors, 'Batch operation failed');
      }
    }
  }

  return results;
};

// Smart retry with adaptive configuration
export class AdaptiveRetry {
  private successRate = 1.0;
  private recentAttempts: boolean[] = [];
  private readonly maxHistory = 100;

  constructor(private baseConfig: RetryConfig) {}

  async execute<T>(operation: () => Promise<T>): Promise<RetryResult<T>> {
    const adaptedConfig = this.adaptConfiguration();
    const result = await retryWithBackoff(operation, adaptedConfig);
    
    this.updateSuccessRate(result.success);
    return result;
  }

  private adaptConfiguration(): RetryConfig {
    // Reduce retries if success rate is low to prevent overwhelming the service
    const successRateMultiplier = Math.max(0.5, this.successRate);
    
    return {
      ...this.baseConfig,
      maxAttempts: Math.ceil(this.baseConfig.maxAttempts * successRateMultiplier),
      baseDelay: Math.ceil(this.baseConfig.baseDelay / successRateMultiplier)
    };
  }

  private updateSuccessRate(success: boolean): void {
    this.recentAttempts.push(success);
    
    if (this.recentAttempts.length > this.maxHistory) {
      this.recentAttempts.shift();
    }
    
    const successes = this.recentAttempts.filter(Boolean).length;
    this.successRate = successes / this.recentAttempts.length;
  }

  getSuccessRate(): number {
    return this.successRate;
  }

  reset(): void {
    this.recentAttempts = [];
    this.successRate = 1.0;
  }
}

// Utility to create a retryable version of an async function
export const createRetryableFunction = <TArgs extends any[], TReturn>(
  fn: (...args: TArgs) => Promise<TReturn>,
  config: RetryConfig
) => {
  return async (...args: TArgs): Promise<RetryResult<TReturn>> => {
    return retryWithBackoff(() => fn(...args), config);
  };
};

// Queue-based retry system for managing multiple operations
export class RetryQueue {
  private queue: Array<{
    id: string;
    operation: () => Promise<any>;
    config: RetryConfig;
    resolve: (value: any) => void;
    reject: (error: any) => void;
  }> = [];
  
  private processing = false;
  private maxConcurrent = 3;

  async add<T>(
    operation: () => Promise<T>,
    config: RetryConfig = RETRY_CONFIGS.api,
    id?: string
  ): Promise<RetryResult<T>> {
    return new Promise((resolve, reject) => {
      this.queue.push({
        id: id || `retry_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
        operation,
        config,
        resolve,
        reject
      });

      if (!this.processing) {
        this.processQueue();
      }
    });
  }

  private async processQueue(): Promise<void> {
    if (this.processing || this.queue.length === 0) return;

    this.processing = true;

    while (this.queue.length > 0) {
      const batch = this.queue.splice(0, this.maxConcurrent);
      
      await Promise.all(
        batch.map(async item => {
          try {
            const result = await retryWithBackoff(item.operation, item.config);
            item.resolve(result);
          } catch (error) {
            item.reject(error);
          }
        })
      );
    }

    this.processing = false;
  }

  getQueueSize(): number {
    return this.queue.length;
  }

  clear(): void {
    this.queue.forEach(item => {
      item.reject(new Error('Queue cleared'));
    });
    this.queue = [];
  }
}

// Export React import for the hook
import React from 'react';