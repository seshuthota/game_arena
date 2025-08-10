/**
 * Extended Performance API type definitions
 * Adds missing types for Layout Shift and other Performance Observer entries
 */

export interface LayoutShiftEntry extends PerformanceEntry {
  readonly value: number;
  readonly hadRecentInput: boolean;
  readonly lastInputTime: number;
  readonly sources: LayoutShiftAttribution[];
}

interface LayoutShiftAttribution {
  readonly node?: Node;
  readonly currentRect: DOMRectReadOnly;
  readonly previousRect: DOMRectReadOnly;
}

interface LongTaskEntry extends PerformanceEntry {
  readonly attribution: TaskAttributionTiming[];
}

interface TaskAttributionTiming extends PerformanceEntry {
  readonly containerType: string;
  readonly containerSrc: string;
  readonly containerId: string;
  readonly containerName: string;
}

// Extend the global PerformanceObserver types
declare global {
  interface PerformanceObserverEntryList {
    getEntries(): PerformanceEntry[];
    getEntriesByType(type: string): PerformanceEntry[];
    getEntriesByName(name: string, type?: string): PerformanceEntry[];
  }
  
  // Web Vitals types
  interface WebVitalsMetric {
    name: 'CLS' | 'FID' | 'FCP' | 'LCP' | 'TTFB';
    value: number;
    id: string;
    delta: number;
    entries: PerformanceEntry[];
    rating: 'good' | 'needs-improvement' | 'poor';
  }
  
  // Memory API (Chrome specific)
  interface Performance {
    memory?: {
      usedJSHeapSize: number;
      totalJSHeapSize: number;
      jsHeapSizeLimit: number;
    };
  }
}

export {};