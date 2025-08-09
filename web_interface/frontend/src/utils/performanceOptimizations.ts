import React, { useMemo, useCallback, useRef, useEffect } from 'react';

// Performance monitoring utilities
export const usePerformanceMonitor = (componentName: string) => {
  const renderStartRef = useRef<number>(0);
  const renderCountRef = useRef<number>(0);

  useEffect(() => {
    renderStartRef.current = performance.now();
    renderCountRef.current += 1;
  });

  useEffect(() => {
    const renderTime = performance.now() - renderStartRef.current;
    
    if (process.env.NODE_ENV === 'development') {
      console.log(`🎯 ${componentName} render #${renderCountRef.current}: ${renderTime.toFixed(2)}ms`);
    }
  });

  return {
    renderCount: renderCountRef.current,
    logRenderCount: () => {
      if (process.env.NODE_ENV === 'development') {
        console.log(`🔄 ${componentName} total renders: ${renderCountRef.current}`);
      }
    }
  };
};

// Memoized comparison functions
export const shallowCompare = (objA: any, objB: any): boolean => {
  if (objA === objB) return true;
  
  const keysA = Object.keys(objA);
  const keysB = Object.keys(objB);
  
  if (keysA.length !== keysB.length) return false;
  
  for (const key of keysA) {
    if (objA[key] !== objB[key]) return false;
  }
  
  return true;
};

export const deepCompare = (objA: any, objB: any): boolean => {
  if (objA === objB) return true;
  
  if (objA == null || objB == null) return objA === objB;
  
  if (typeof objA !== typeof objB) return false;
  
  if (typeof objA !== 'object') return objA === objB;
  
  const keysA = Object.keys(objA);
  const keysB = Object.keys(objB);
  
  if (keysA.length !== keysB.length) return false;
  
  for (const key of keysA) {
    if (!keysB.includes(key)) return false;
    if (!deepCompare(objA[key], objB[key])) return false;
  }
  
  return true;
};

// Custom hooks for optimized state management
export const useStableCallback = <T extends (...args: any[]) => any>(
  callback: T,
  dependencies: React.DependencyList
): T => {
  const callbackRef = useRef<T>(callback);
  const depsRef = useRef<React.DependencyList>(dependencies);

  if (!shallowCompare(depsRef.current, dependencies)) {
    callbackRef.current = callback;
    depsRef.current = dependencies;
  }

  return callbackRef.current;
};

export const useDebounced = <T>(value: T, delay: number): T => {
  const [debouncedValue, setDebouncedValue] = React.useState<T>(value);

  React.useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);

  return debouncedValue;
};

export const useThrottle = <T extends (...args: any[]) => any>(
  callback: T,
  delay: number
): T => {
  const lastRun = useRef<number>(Date.now());

  return useCallback(
    ((...args: Parameters<T>) => {
      if (Date.now() - lastRun.current >= delay) {
        callback(...args);
        lastRun.current = Date.now();
      }
    }) as T,
    [callback, delay]
  );
};

// Intersection Observer hook for lazy loading
export const useIntersectionObserver = (
  elementRef: React.RefObject<Element>,
  options: IntersectionObserverInit = {}
) => {
  const [isIntersecting, setIsIntersecting] = React.useState(false);

  useEffect(() => {
    const element = elementRef.current;
    if (!element) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        setIsIntersecting(entry.isIntersecting);
      },
      {
        threshold: 0.1,
        rootMargin: '50px',
        ...options,
      }
    );

    observer.observe(element);

    return () => {
      observer.unobserve(element);
    };
  }, [elementRef, options]);

  return isIntersecting;
};

// Optimized scroll handler
export const useOptimizedScroll = (
  callback: (scrollY: number) => void,
  dependencies: React.DependencyList = []
) => {
  const requestRef = useRef<number>();
  const callbackRef = useRef(callback);

  // Update callback ref when dependencies change
  useEffect(() => {
    callbackRef.current = callback;
  }, dependencies);

  useEffect(() => {
    const handleScroll = () => {
      if (requestRef.current) {
        cancelAnimationFrame(requestRef.current);
      }
      
      requestRef.current = requestAnimationFrame(() => {
        callbackRef.current(window.scrollY);
      });
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    
    return () => {
      window.removeEventListener('scroll', handleScroll);
      if (requestRef.current) {
        cancelAnimationFrame(requestRef.current);
      }
    };
  }, []);
};

// Memory usage monitoring
export const useMemoryMonitor = (componentName: string) => {
  const memoryRef = useRef<number>(0);

  useEffect(() => {
    if (process.env.NODE_ENV === 'development' && 'memory' in performance) {
      const memoryInfo = (performance as any).memory;
      const currentUsage = memoryInfo.usedJSHeapSize / 1024 / 1024; // MB
      
      if (currentUsage > memoryRef.current + 10) { // Log if increase > 10MB
        console.warn(`📈 ${componentName} memory usage: ${currentUsage.toFixed(2)}MB (+${(currentUsage - memoryRef.current).toFixed(2)}MB)`);
        memoryRef.current = currentUsage;
      }
    }
  });
};

// Optimized array operations
export const useMemoizedSort = <T>(
  array: T[],
  compareFn: (a: T, b: T) => number,
  dependencies: React.DependencyList = []
): T[] => {
  return useMemo(() => {
    return [...array].sort(compareFn);
  }, [array, compareFn, ...dependencies]);
};

export const useMemoizedFilter = <T>(
  array: T[],
  predicate: (item: T) => boolean,
  dependencies: React.DependencyList = []
): T[] => {
  return useMemo(() => {
    return array.filter(predicate);
  }, [array, predicate, ...dependencies]);
};

export const useMemoizedMap = <T, U>(
  array: T[],
  mapFn: (item: T, index: number) => U,
  dependencies: React.DependencyList = []
): U[] => {
  return useMemo(() => {
    return array.map(mapFn);
  }, [array, mapFn, ...dependencies]);
};

// Virtual scrolling optimizations
export const useVirtualScrollOptimization = (
  itemCount: number,
  itemHeight: number,
  containerHeight: number
) => {
  return useMemo(() => {
    const visibleItemCount = Math.ceil(containerHeight / itemHeight);
    const overscan = Math.min(10, Math.ceil(visibleItemCount * 0.2));
    
    return {
      visibleItemCount,
      overscan,
      bufferSize: visibleItemCount + 2 * overscan,
    };
  }, [itemCount, itemHeight, containerHeight]);
};

// Component factory for creating memoized components
export const createMemoizedComponent = <T extends React.ComponentType<any>>(
  Component: T,
  compareProps?: (prevProps: React.ComponentProps<T>, nextProps: React.ComponentProps<T>) => boolean
): React.NamedExoticComponent<React.ComponentProps<T>> => {
  const MemoizedComponent = React.memo(Component, compareProps);
  MemoizedComponent.displayName = `Memo(${Component.displayName || Component.name})`;
  return MemoizedComponent as any;
};

// Higher-order component for performance monitoring
export const withPerformanceMonitoring = <P extends {}>(
  Component: React.ComponentType<P>,
  componentName?: string
) => {
  const PerformanceMonitoredComponent: React.FC<P> = (props) => {
    const name = componentName || Component.displayName || Component.name || 'Unknown';
    usePerformanceMonitor(name);
    useMemoryMonitor(name);
    
    return React.createElement(Component, props);
  };
  
  PerformanceMonitoredComponent.displayName = `withPerformanceMonitoring(${Component.displayName || Component.name})`;
  
  return PerformanceMonitoredComponent;
};

// Bundle size optimization utilities
export const createLazyComponent = <T extends React.ComponentType<any>>(
  importFn: () => Promise<{ default: T }>,
  fallback?: React.ComponentType
) => {
  const LazyComponent = React.lazy(importFn);
  
  return React.forwardRef<any, React.ComponentProps<T>>((props, ref) =>
    React.createElement(
      React.Suspense,
      { 
        fallback: fallback 
          ? React.createElement(fallback) 
          : React.createElement('div', null, 'Loading...') 
      },
      React.createElement(LazyComponent, { ...props, ref } as any)
    )
  );
};

// CSS-in-JS optimization
export const useOptimizedStyles = (
  stylesFn: () => React.CSSProperties,
  dependencies: React.DependencyList
): React.CSSProperties => {
  return useMemo(stylesFn, dependencies);
};

// Event handler optimization
export const useOptimizedEventHandler = <T extends (...args: any[]) => void>(
  handler: T,
  dependencies: React.DependencyList
): T => {
  return useCallback(handler, dependencies);
};