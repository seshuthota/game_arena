// Mock implementation of responsive utilities for testing
export const BREAKPOINTS = {
  xs: '320px',
  sm: '640px',
  md: '768px',
  lg: '1024px',
  xl: '1280px',
  '2xl': '1536px'
} as const;

export const getDeviceType = jest.fn(() => 'desktop' as const);
export const isMobileDevice = jest.fn(() => false);
export const isTouchDevice = jest.fn(() => false);
export const hasHover = jest.fn(() => true);
export const supportsPointerEvents = jest.fn(() => true);

export const useResponsive = jest.fn(() => ({
  windowSize: { width: 1024, height: 768 },
  deviceType: 'desktop' as const,
  orientation: 'landscape' as const,
  isMobile: false,
  isTablet: false,
  isDesktop: true,
  isPortrait: false,
  isLandscape: true,
  isBreakpoint: jest.fn(() => true),
  isBetweenBreakpoints: jest.fn(() => false),
  isTouchDevice: false,
  hasHover: true,
  aspectRatio: 1.33
}));

export const useMediaQuery = jest.fn(() => false);

export const getSafeAreaInsets = jest.fn(() => ({
  top: '0px',
  right: '0px',
  bottom: '0px',
  left: '0px'
}));

export const createResponsiveValue = jest.fn((values) => (breakpoint) => values.lg || values.md || values.sm || values.xs);

export const createResponsiveStyles = jest.fn(() => '');
export const createResponsiveFontSize = jest.fn(() => ({ fontSize: '16px' }));

export const createTouchHandler = jest.fn(() => ({
  onTouchStart: jest.fn(),
  onTouchMove: jest.fn(),
  onTouchEnd: jest.fn()
}));

export const getViewportInfo = jest.fn(() => ({
  width: 1024,
  height: 768,
  aspectRatio: 1.33,
  isLandscape: true,
  isPortrait: false,
  devicePixelRatio: 1,
  isHighDPI: false
}));

export const debounce = jest.fn((fn) => fn);
export const throttle = jest.fn((fn) => fn);

export const createFocusTrap = jest.fn(() => jest.fn());