// Mock implementation of performance optimization utilities for testing
export const usePerformanceMonitor = jest.fn();
export const useMemoryMonitor = jest.fn();

export const withPerformanceMonitoring = jest.fn((Component) => Component);

export const useStableCallback = jest.fn((callback) => callback);
export const useStableValue = jest.fn((value) => value);
export const usePrevious = jest.fn((value) => value);
export const useDebounce = jest.fn((value) => value);

export const useIntersectionObserver = jest.fn(() => false);

export const useMemoizedSort = jest.fn((array) => array);
export const useMemoizedFilter = jest.fn((array) => array);
export const useMemoizedMap = jest.fn((array) => array);

export const useVirtualScrollOptimization = jest.fn(() => ({
  visibleItemCount: 10,
  overscan: 2,
  bufferSize: 14
}));