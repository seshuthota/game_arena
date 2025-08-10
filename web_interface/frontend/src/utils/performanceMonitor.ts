/**
 * Performance monitoring utilities for chess board and statistics
 */

import { LayoutShiftEntry } from '../types/performance';

export interface PerformanceMetric {
  name: string;
  value: number;
  timestamp: number;
  category: 'chess_board' | 'statistics' | 'api' | 'user_interaction';
  metadata?: Record<string, any>;
}

export interface ChessBoardPerformance {
  renderTime: number;
  moveNavigationTime: number;
  positionValidationTime: number;
  animationFrameTime: number;
  cacheHitRate: number;
}

export interface StatisticsPerformance {
  calculationTime: number;
  apiResponseTime: number;
  dataProcessingTime: number;
  cacheHitRate: number;
  queryComplexity: number;
}

class PerformanceMonitor {
  private metrics: PerformanceMetric[] = [];
  private startTimes: Map<string, number> = new Map();
  private observers: Map<string, PerformanceObserver> = new Map();
  
  constructor() {
    this.initializeBrowserAPIs();
    this.setupPerformanceObservers();
  }

  private initializeBrowserAPIs() {
    // Web Vitals monitoring
    if ('web-vitals' in window) {
      import('web-vitals').then(({ getCLS, getFID, getFCP, getLCP, getTTFB }) => {
        getCLS(this.recordWebVital.bind(this));
        getFID(this.recordWebVital.bind(this));
        getFCP(this.recordWebVital.bind(this));
        getLCP(this.recordWebVital.bind(this));
        getTTFB(this.recordWebVital.bind(this));
      });
    }
  }

  private setupPerformanceObservers() {
    // Long Task Observer
    if ('PerformanceObserver' in window) {
      try {
        const longTaskObserver = new PerformanceObserver((list) => {
          for (const entry of list.getEntries()) {
            this.recordMetric({
              name: 'long_task',
              value: entry.duration,
              timestamp: entry.startTime,
              category: 'user_interaction',
              metadata: {
                type: entry.entryType,
                startTime: entry.startTime,
              }
            });
          }
        });
        
        longTaskObserver.observe({ entryTypes: ['longtask'] });
        this.observers.set('longtask', longTaskObserver);
        
        // Layout Shift Observer
        const layoutShiftObserver = new PerformanceObserver((list) => {
          for (const entry of list.getEntries()) {
            // Type guard to ensure this is a LayoutShiftEntry
            const layoutShiftEntry = entry as LayoutShiftEntry;
            
            // Check if the properties exist (for browser compatibility)
            if (typeof layoutShiftEntry.hadRecentInput === 'boolean' && !layoutShiftEntry.hadRecentInput) {
              this.recordMetric({
                name: 'layout_shift',
                value: layoutShiftEntry.value || 0,
                timestamp: entry.startTime,
                category: 'user_interaction',
                metadata: {
                  lastInputTime: layoutShiftEntry.lastInputTime || 0,
                  sources: layoutShiftEntry.sources?.length || 0,
                }
              });
            }
          }
        });
        
        layoutShiftObserver.observe({ entryTypes: ['layout-shift'] });
        this.observers.set('layout-shift', layoutShiftObserver);
        
      } catch (error) {
        console.warn('Performance Observer not supported:', error);
      }
    }
  }

  private recordWebVital(metric: any) {
    this.recordMetric({
      name: metric.name.toLowerCase(),
      value: metric.value,
      timestamp: metric.entries?.[0]?.startTime || performance.now(),
      category: 'user_interaction',
      metadata: {
        id: metric.id,
        delta: metric.delta,
        rating: metric.rating,
      }
    });
  }

  startTiming(operationId: string): void {
    this.startTimes.set(operationId, performance.now());
  }

  endTiming(operationId: string, category: PerformanceMetric['category'], metadata?: Record<string, any>): number {
    const startTime = this.startTimes.get(operationId);
    if (!startTime) {
      console.warn(`No start time found for operation: ${operationId}`);
      return 0;
    }

    const duration = performance.now() - startTime;
    this.startTimes.delete(operationId);

    this.recordMetric({
      name: operationId,
      value: duration,
      timestamp: startTime,
      category,
      metadata,
    });

    return duration;
  }

  recordMetric(metric: PerformanceMetric): void {
    this.metrics.push(metric);
    
    // Keep only recent metrics (last hour)
    const oneHourAgo = Date.now() - 3600000;
    this.metrics = this.metrics.filter(m => m.timestamp > oneHourAgo);
    
    // Report to backend if enabled
    if (process.env.REACT_APP_PERFORMANCE_REPORTING === 'true') {
      this.reportToBackend(metric);
    }
    
    // Log performance warnings
    this.checkPerformanceThresholds(metric);
  }

  private checkPerformanceThresholds(metric: PerformanceMetric): void {
    const thresholds: Record<string, number> = {
      'chess_board_render': 100,        // 100ms
      'move_navigation': 50,            // 50ms
      'position_validation': 10,        // 10ms
      'statistics_calculation': 500,    // 500ms
      'api_response': 1000,            // 1s
      'long_task': 50,                 // 50ms
    };

    const threshold = thresholds[metric.name];
    if (threshold && metric.value > threshold) {
      console.warn(`Performance threshold exceeded for ${metric.name}: ${metric.value}ms > ${threshold}ms`, metric);
      
      // Report critical performance issues
      this.recordMetric({
        name: 'performance_warning',
        value: metric.value,
        timestamp: metric.timestamp,
        category: 'user_interaction',
        metadata: {
          originalMetric: metric.name,
          threshold,
          severity: metric.value > threshold * 2 ? 'high' : 'medium',
        }
      });
    }
  }

  private async reportToBackend(metric: PerformanceMetric): Promise<void> {
    try {
      await fetch('/api/v1/performance/metrics', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...metric,
          userAgent: navigator.userAgent,
          url: window.location.href,
          sessionId: this.getSessionId(),
        }),
      });
    } catch (error) {
      // Silently fail - don't impact user experience
      console.debug('Failed to report performance metric:', error);
    }
  }

  private getSessionId(): string {
    let sessionId = sessionStorage.getItem('performance_session_id');
    if (!sessionId) {
      sessionId = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      sessionStorage.setItem('performance_session_id', sessionId);
    }
    return sessionId;
  }

  // Chess Board specific monitoring
  measureChessBoardRender<T>(fn: () => T, metadata?: Record<string, any>): T {
    const operationId = `chess_board_render_${Date.now()}`;
    this.startTiming(operationId);
    
    try {
      const result = fn();
      this.endTiming(operationId, 'chess_board', metadata);
      return result;
    } catch (error) {
      this.endTiming(operationId, 'chess_board', { ...metadata, error: error.message });
      throw error;
    }
  }

  async measureChessBoardRenderAsync<T>(fn: () => Promise<T>, metadata?: Record<string, any>): Promise<T> {
    const operationId = `chess_board_render_async_${Date.now()}`;
    this.startTiming(operationId);
    
    try {
      const result = await fn();
      this.endTiming(operationId, 'chess_board', metadata);
      return result;
    } catch (error) {
      this.endTiming(operationId, 'chess_board', { ...metadata, error: error.message });
      throw error;
    }
  }

  measureMoveNavigation(fromMove: number, toMove: number, fn: () => void): void {
    const operationId = `move_navigation_${Date.now()}`;
    this.startTiming(operationId);
    
    try {
      fn();
      this.endTiming(operationId, 'chess_board', {
        fromMove,
        toMove,
        moveDelta: Math.abs(toMove - fromMove),
      });
    } catch (error) {
      this.endTiming(operationId, 'chess_board', {
        fromMove,
        toMove,
        error: error.message,
      });
      throw error;
    }
  }

  // Statistics monitoring
  async measureStatisticsCalculation<T>(
    calculationType: string,
    fn: () => Promise<T>,
    metadata?: Record<string, any>
  ): Promise<T> {
    const operationId = `statistics_${calculationType}_${Date.now()}`;
    this.startTiming(operationId);
    
    try {
      const result = await fn();
      this.endTiming(operationId, 'statistics', {
        calculationType,
        ...metadata,
      });
      return result;
    } catch (error) {
      this.endTiming(operationId, 'statistics', {
        calculationType,
        error: error.message,
        ...metadata,
      });
      throw error;
    }
  }

  async measureAPICall<T>(
    endpoint: string,
    fn: () => Promise<T>,
    metadata?: Record<string, any>
  ): Promise<T> {
    const operationId = `api_${endpoint.replace(/[^a-zA-Z0-9]/g, '_')}_${Date.now()}`;
    this.startTiming(operationId);
    
    try {
      const result = await fn();
      this.endTiming(operationId, 'api', {
        endpoint,
        ...metadata,
      });
      return result;
    } catch (error) {
      this.endTiming(operationId, 'api', {
        endpoint,
        error: error.message,
        ...metadata,
      });
      throw error;
    }
  }

  // Analytics and reporting
  getMetrics(category?: PerformanceMetric['category'], timeWindow?: number): PerformanceMetric[] {
    const cutoff = timeWindow ? Date.now() - timeWindow : 0;
    return this.metrics.filter(m => 
      m.timestamp > cutoff && 
      (!category || m.category === category)
    );
  }

  getAverageMetric(name: string, timeWindow: number = 300000): number {
    const metrics = this.getMetrics(undefined, timeWindow)
      .filter(m => m.name === name)
      .map(m => m.value);
    
    return metrics.length > 0 
      ? metrics.reduce((a, b) => a + b, 0) / metrics.length
      : 0;
  }

  getPerformanceSummary(): {
    chessBoardPerformance: ChessBoardPerformance;
    statisticsPerformance: StatisticsPerformance;
    userExperience: Record<string, number>;
  } {
    const fiveMinutesAgo = 300000;
    
    return {
      chessBoardPerformance: {
        renderTime: this.getAverageMetric('chess_board_render', fiveMinutesAgo),
        moveNavigationTime: this.getAverageMetric('move_navigation', fiveMinutesAgo),
        positionValidationTime: this.getAverageMetric('position_validation', fiveMinutesAgo),
        animationFrameTime: this.getAverageMetric('animation_frame', fiveMinutesAgo),
        cacheHitRate: this.getCacheHitRate('chess_board', fiveMinutesAgo),
      },
      statisticsPerformance: {
        calculationTime: this.getAverageMetric('statistics_calculation', fiveMinutesAgo),
        apiResponseTime: this.getAverageMetric('api_response', fiveMinutesAgo),
        dataProcessingTime: this.getAverageMetric('data_processing', fiveMinutesAgo),
        cacheHitRate: this.getCacheHitRate('statistics', fiveMinutesAgo),
        queryComplexity: this.getAverageMetric('query_complexity', fiveMinutesAgo),
      },
      userExperience: {
        cls: this.getAverageMetric('cls', fiveMinutesAgo),
        fid: this.getAverageMetric('fid', fiveMinutesAgo),
        lcp: this.getAverageMetric('lcp', fiveMinutesAgo),
        longTasks: this.getMetrics(undefined, fiveMinutesAgo)
          .filter(m => m.name === 'long_task').length,
        layoutShifts: this.getMetrics(undefined, fiveMinutesAgo)
          .filter(m => m.name === 'layout_shift').length,
      },
    };
  }

  private getCacheHitRate(category: string, timeWindow: number): number {
    const categoryMetrics = this.getMetrics(category as PerformanceMetric['category'], timeWindow);
    const cacheHits = categoryMetrics.filter(m => m.metadata?.cacheHit === true).length;
    const totalRequests = categoryMetrics.filter(m => m.metadata?.hasOwnProperty('cacheHit')).length;
    
    return totalRequests > 0 ? cacheHits / totalRequests : 0;
  }

  // Memory monitoring
  recordMemoryUsage(): void {
    if ('memory' in performance) {
      const memory = (performance as any).memory;
      this.recordMetric({
        name: 'memory_usage',
        value: memory.usedJSHeapSize,
        timestamp: performance.now(),
        category: 'user_interaction',
        metadata: {
          totalJSHeapSize: memory.totalJSHeapSize,
          jsHeapSizeLimit: memory.jsHeapSizeLimit,
        },
      });
    }
  }

  // Cleanup
  destroy(): void {
    this.observers.forEach(observer => observer.disconnect());
    this.observers.clear();
    this.metrics = [];
    this.startTimes.clear();
  }
}

// Global performance monitor instance
export const performanceMonitor = new PerformanceMonitor();

// React hook for performance monitoring
export const usePerformanceMonitor = () => {
  return {
    measureChessBoardRender: performanceMonitor.measureChessBoardRender.bind(performanceMonitor),
    measureMoveNavigation: performanceMonitor.measureMoveNavigation.bind(performanceMonitor),
    measureStatisticsCalculation: performanceMonitor.measureStatisticsCalculation.bind(performanceMonitor),
    measureAPICall: performanceMonitor.measureAPICall.bind(performanceMonitor),
    getPerformanceSummary: performanceMonitor.getPerformanceSummary.bind(performanceMonitor),
    recordMemoryUsage: performanceMonitor.recordMemoryUsage.bind(performanceMonitor),
  };
};