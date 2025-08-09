import { useState, useEffect } from 'react';

// Enhanced responsive breakpoints and utilities
export const BREAKPOINTS = {
  xs: '320px',   // Extra small mobile phones
  sm: '640px',   // Small tablets and large phones
  md: '768px',   // Medium tablets
  lg: '1024px',  // Small laptops
  xl: '1280px',  // Large laptops and desktops
  '2xl': '1536px' // Large desktops and monitors
} as const;

export type Breakpoint = keyof typeof BREAKPOINTS;

// Device detection utilities
export const getDeviceType = (): 'mobile' | 'tablet' | 'desktop' => {
  const width = window.innerWidth;
  if (width < 768) return 'mobile';
  if (width < 1024) return 'tablet';
  return 'desktop';
};

export const isMobileDevice = (): boolean => {
  return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent) ||
         (window.innerWidth <= 768);
};

export const isTouchDevice = (): boolean => {
  return 'ontouchstart' in window || navigator.maxTouchPoints > 0;
};

export const hasHover = (): boolean => {
  return window.matchMedia('(hover: hover)').matches;
};

export const supportsPointerEvents = (): boolean => {
  return 'onpointerdown' in window;
};

// Responsive hook for React components

export const useResponsive = () => {
  const [windowSize, setWindowSize] = useState({
    width: typeof window !== 'undefined' ? window.innerWidth : 1024,
    height: typeof window !== 'undefined' ? window.innerHeight : 768
  });

  const [deviceType, setDeviceType] = useState<'mobile' | 'tablet' | 'desktop'>('desktop');
  const [orientation, setOrientation] = useState<'portrait' | 'landscape'>('landscape');

  useEffect(() => {
    const handleResize = () => {
      const width = window.innerWidth;
      const height = window.innerHeight;
      
      setWindowSize({ width, height });
      setDeviceType(getDeviceType());
      setOrientation(width > height ? 'landscape' : 'portrait');
    };

    handleResize(); // Set initial values
    window.addEventListener('resize', handleResize);
    window.addEventListener('orientationchange', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      window.removeEventListener('orientationchange', handleResize);
    };
  }, []);

  const isBreakpoint = (breakpoint: Breakpoint) => {
    const breakpointValue = parseInt(BREAKPOINTS[breakpoint]);
    return windowSize.width >= breakpointValue;
  };

  const isBetweenBreakpoints = (min: Breakpoint, max: Breakpoint) => {
    const minValue = parseInt(BREAKPOINTS[min]);
    const maxValue = parseInt(BREAKPOINTS[max]);
    return windowSize.width >= minValue && windowSize.width < maxValue;
  };

  return {
    windowSize,
    deviceType,
    orientation,
    isMobile: deviceType === 'mobile',
    isTablet: deviceType === 'tablet',
    isDesktop: deviceType === 'desktop',
    isPortrait: orientation === 'portrait',
    isLandscape: orientation === 'landscape',
    isBreakpoint,
    isBetweenBreakpoints,
    isTouchDevice: isTouchDevice(),
    hasHover: hasHover(),
    aspectRatio: windowSize.width / windowSize.height
  };
};

// Media query hook
export const useMediaQuery = (query: string) => {
  const [matches, setMatches] = useState(false);

  useEffect(() => {
    const mediaQuery = window.matchMedia(query);
    setMatches(mediaQuery.matches);

    const handleChange = (event: MediaQueryListEvent) => {
      setMatches(event.matches);
    };

    mediaQuery.addEventListener('change', handleChange);
    return () => mediaQuery.removeEventListener('change', handleChange);
  }, [query]);

  return matches;
};

// Safe area utilities for devices with notches
export const getSafeAreaInsets = () => {
  const computedStyle = getComputedStyle(document.documentElement);
  
  return {
    top: computedStyle.getPropertyValue('env(safe-area-inset-top)') || '0px',
    right: computedStyle.getPropertyValue('env(safe-area-inset-right)') || '0px',
    bottom: computedStyle.getPropertyValue('env(safe-area-inset-bottom)') || '0px',
    left: computedStyle.getPropertyValue('env(safe-area-inset-left)') || '0px'
  };
};

// Responsive values utility
export const createResponsiveValue = <T>(values: {
  xs?: T;
  sm?: T;
  md?: T;
  lg?: T;
  xl?: T;
  '2xl'?: T;
}) => {
  return (currentBreakpoint: Breakpoint): T | undefined => {
    const breakpoints: Breakpoint[] = ['xs', 'sm', 'md', 'lg', 'xl', '2xl'];
    const currentIndex = breakpoints.indexOf(currentBreakpoint);
    
    // Find the closest defined value at or below current breakpoint
    for (let i = currentIndex; i >= 0; i--) {
      const bp = breakpoints[i];
      if (values[bp] !== undefined) {
        return values[bp];
      }
    }
    
    return undefined;
  };
};

// CSS-in-JS responsive utilities
export const createResponsiveStyles = (styles: {
  xs?: React.CSSProperties;
  sm?: React.CSSProperties;
  md?: React.CSSProperties;
  lg?: React.CSSProperties;
  xl?: React.CSSProperties;
  '2xl'?: React.CSSProperties;
}) => {
  const mediaQueries: string[] = [];
  
  Object.entries(styles).forEach(([breakpoint, style]) => {
    if (style && Object.keys(style).length > 0) {
      const bp = breakpoint as Breakpoint;
      const minWidth = BREAKPOINTS[bp];
      const cssProperties = Object.entries(style)
        .map(([prop, value]) => `${prop.replace(/[A-Z]/g, m => `-${m.toLowerCase()}`)}: ${value}`)
        .join('; ');
      
      if (bp === 'xs') {
        mediaQueries.push(cssProperties);
      } else {
        mediaQueries.push(`@media (min-width: ${minWidth}) { ${cssProperties} }`);
      }
    }
  });
  
  return mediaQueries.join(' ');
};

// Responsive font scaling
export const createResponsiveFontSize = (basePx: number, scale: number = 1.2) => {
  const vw = Math.max(document.documentElement.clientWidth || 0, window.innerWidth || 0);
  
  // Calculate responsive font size
  const minSize = basePx;
  const maxSize = basePx * scale;
  const responsive = basePx + (maxSize - basePx) * ((vw - 320) / (1920 - 320));
  
  return {
    fontSize: `clamp(${minSize}px, ${responsive}px, ${maxSize}px)`
  };
};

// Touch/gesture utilities
export const createTouchHandler = (options: {
  onTouchStart?: (e: React.TouchEvent<HTMLElement>) => void;
  onTouchMove?: (e: React.TouchEvent<HTMLElement>) => void;
  onTouchEnd?: (e: React.TouchEvent<HTMLElement>) => void;
  onSwipeLeft?: () => void;
  onSwipeRight?: () => void;
  onSwipeUp?: () => void;
  onSwipeDown?: () => void;
  swipeThreshold?: number;
  preventScroll?: boolean;
}) => {
  const { 
    swipeThreshold = 100,
    preventScroll = false,
    onSwipeLeft,
    onSwipeRight,
    onSwipeUp,
    onSwipeDown,
    ...handlers 
  } = options;

  let startX = 0;
  let startY = 0;
  let startTime = 0;

  const handleTouchStart = (e: React.TouchEvent<HTMLElement>) => {
    const touch = e.touches[0];
    startX = touch.clientX;
    startY = touch.clientY;
    startTime = Date.now();
    
    if (preventScroll) {
      e.preventDefault();
    }
    
    handlers.onTouchStart?.(e);
  };

  const handleTouchMove = (e: React.TouchEvent<HTMLElement>) => {
    if (preventScroll) {
      e.preventDefault();
    }
    
    handlers.onTouchMove?.(e);
  };

  const handleTouchEnd = (e: React.TouchEvent<HTMLElement>) => {
    const touch = e.changedTouches[0];
    const endX = touch.clientX;
    const endY = touch.clientY;
    const endTime = Date.now();
    
    const deltaX = endX - startX;
    const deltaY = endY - startY;
    const deltaTime = endTime - startTime;
    
    // Only trigger swipe if it was fast enough and far enough
    if (deltaTime < 500 && (Math.abs(deltaX) > swipeThreshold || Math.abs(deltaY) > swipeThreshold)) {
      if (Math.abs(deltaX) > Math.abs(deltaY)) {
        // Horizontal swipe
        if (deltaX > 0 && onSwipeRight) {
          onSwipeRight();
        } else if (deltaX < 0 && onSwipeLeft) {
          onSwipeLeft();
        }
      } else {
        // Vertical swipe
        if (deltaY > 0 && onSwipeDown) {
          onSwipeDown();
        } else if (deltaY < 0 && onSwipeUp) {
          onSwipeUp();
        }
      }
    }
    
    handlers.onTouchEnd?.(e);
  };

  return {
    onTouchStart: handleTouchStart,
    onTouchMove: handleTouchMove,
    onTouchEnd: handleTouchEnd
  };
};

// Viewport utilities
export const getViewportInfo = () => {
  const vw = Math.max(document.documentElement.clientWidth || 0, window.innerWidth || 0);
  const vh = Math.max(document.documentElement.clientHeight || 0, window.innerHeight || 0);
  
  return {
    width: vw,
    height: vh,
    aspectRatio: vw / vh,
    isLandscape: vw > vh,
    isPortrait: vh > vw,
    devicePixelRatio: window.devicePixelRatio || 1,
    isHighDPI: window.devicePixelRatio > 1.5
  };
};

// Performance utilities for responsive components
export const debounce = <T extends (...args: any[]) => any>(
  func: T,
  wait: number
): ((...args: Parameters<T>) => void) => {
  let timeout: NodeJS.Timeout;
  
  return (...args: Parameters<T>) => {
    clearTimeout(timeout);
    timeout = setTimeout(() => func.apply(null, args), wait);
  };
};

export const throttle = <T extends (...args: any[]) => any>(
  func: T,
  limit: number
): ((...args: Parameters<T>) => void) => {
  let inThrottle: boolean;
  
  return (...args: Parameters<T>) => {
    if (!inThrottle) {
      func.apply(null, args);
      inThrottle = true;
      setTimeout(() => inThrottle = false, limit);
    }
  };
};

// Accessible focus management
export const createFocusTrap = (container: HTMLElement) => {
  const focusableElements = container.querySelectorAll(
    'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
  );
  
  const firstElement = focusableElements[0] as HTMLElement;
  const lastElement = focusableElements[focusableElements.length - 1] as HTMLElement;
  
  const handleTabKey = (e: KeyboardEvent) => {
    if (e.key === 'Tab') {
      if (e.shiftKey) {
        if (document.activeElement === firstElement) {
          e.preventDefault();
          lastElement.focus();
        }
      } else {
        if (document.activeElement === lastElement) {
          e.preventDefault();
          firstElement.focus();
        }
      }
    }
    
    if (e.key === 'Escape') {
      container.blur();
    }
  };
  
  container.addEventListener('keydown', handleTabKey);
  firstElement?.focus();
  
  return () => {
    container.removeEventListener('keydown', handleTabKey);
  };
};