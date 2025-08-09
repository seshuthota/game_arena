import React, { useState, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useConnectionStatus } from '../hooks/useApiWithRetry';
import { useResponsive, createTouchHandler, createFocusTrap, getSafeAreaInsets } from '../utils/responsive';

interface NavigationItem {
  name: string;
  href: string;
  icon: string;
  current?: boolean;
}

interface MobileDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  navigation: NavigationItem[];
}

// Mobile Drawer Navigation
export const MobileDrawer: React.FC<MobileDrawerProps> = ({ isOpen, onClose, navigation }) => {
  const isOnline = useConnectionStatus();
  const { isTouchDevice } = useResponsive();
  const [drawerRef, setDrawerRef] = useState<HTMLDivElement | null>(null);

  // Enhanced keyboard and focus management
  useEffect(() => {
    let cleanupFocusTrap: (() => void) | null = null;

    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        onClose();
      }
    };

    if (isOpen && drawerRef) {
      document.addEventListener('keydown', handleEscape);
      document.body.style.overflow = 'hidden';
      
      // Set up focus trap for better accessibility
      cleanupFocusTrap = createFocusTrap(drawerRef);
    }

    return () => {
      document.removeEventListener('keydown', handleEscape);
      document.body.style.overflow = 'unset';
      cleanupFocusTrap?.();
    };
  }, [isOpen, onClose, drawerRef]);

  // Touch swipe to close gesture
  const touchHandlers = isTouchDevice ? createTouchHandler({
    onSwipeLeft: () => {
      if (isOpen && isTouchDevice) {
        onClose();
      }
    },
    swipeThreshold: 100
  }) : {};

  return (
    <>
      {/* Backdrop */}
      {isOpen && (
        <div
          className="drawer-backdrop"
          onClick={onClose}
          role="button"
          tabIndex={-1}
          aria-label="Close navigation"
        />
      )}

      {/* Drawer */}
      <div 
        ref={setDrawerRef}
        className={`drawer ${isOpen ? 'drawer-open' : ''}`}
        {...touchHandlers}
      >
        <div className="drawer-content">
          {/* Drawer Header */}
          <div className="drawer-header">
            <div className="drawer-brand">
              <span className="brand-icon">⚡</span>
              <h2 className="brand-title">Game Analysis</h2>
            </div>
            <button
              onClick={onClose}
              className="drawer-close"
              aria-label="Close navigation"
            >
              ✕
            </button>
          </div>

          {/* Status Indicator */}
          <div className="drawer-status">
            <div className={`status-dot ${isOnline ? 'status-online' : 'status-offline'}`} />
            <span className="status-text">
              {isOnline ? 'Connected' : 'Offline'}
            </span>
          </div>

          {/* Navigation Links */}
          <nav className="drawer-nav">
            <ul className="drawer-nav-list">
              {navigation.map((item) => (
                <li key={item.name}>
                  <Link
                    to={item.href}
                    className={`drawer-nav-link ${item.current ? 'drawer-nav-link-active' : ''}`}
                    onClick={onClose}
                  >
                    <span className="nav-icon">{item.icon}</span>
                    <span className="nav-text">{item.name}</span>
                    {item.current && <span className="nav-indicator" />}
                  </Link>
                </li>
              ))}
            </ul>
          </nav>

          {/* Drawer Footer */}
          <div className="drawer-footer">
            <div className="footer-info">
              <p className="footer-text">LLM Chess Arena</p>
              <p className="footer-version">v1.0.0</p>
            </div>
          </div>
        </div>
      </div>

      <style jsx>{`
        .drawer-backdrop {
          position: fixed;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          background-color: rgba(0, 0, 0, 0.5);
          z-index: 998;
          animation: fadeIn 0.3s ease-out;
        }

        .drawer {
          position: fixed;
          top: 0;
          left: 0;
          bottom: 0;
          width: min(280px, 85vw);
          background-color: #ffffff;
          z-index: 999;
          transform: translateX(-100%);
          transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
          box-shadow: 2px 0 20px rgba(0, 0, 0, 0.15);
          display: flex;
          flex-direction: column;
          backdrop-filter: blur(10px);
          background-color: rgba(255, 255, 255, 0.95);
          will-change: transform;
        }

        .drawer-open {
          transform: translateX(0);
        }

        .drawer-content {
          display: flex;
          flex-direction: column;
          height: 100%;
        }

        .drawer-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: max(1.5rem, env(safe-area-inset-top) + 1rem) 1.25rem 1.5rem;
          border-bottom: 1px solid rgba(229, 231, 235, 0.3);
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          color: white;
          backdrop-filter: blur(10px);
        }

        .drawer-brand {
          display: flex;
          align-items: center;
          gap: 0.75rem;
        }

        .brand-icon {
          font-size: 1.75rem;
          filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.2));
        }

        .brand-title {
          font-size: 1.25rem;
          font-weight: 600;
          margin: 0;
        }

        .drawer-close {
          background: none;
          border: none;
          color: white;
          font-size: 1.25rem;
          cursor: pointer;
          padding: 0.5rem;
          border-radius: 0.375rem;
          transition: background-color 0.2s;
        }

        .drawer-close:hover {
          background-color: rgba(255, 255, 255, 0.1);
        }

        .drawer-status {
          display: flex;
          align-items: center;
          gap: 0.75rem;
          padding: 1rem 1.25rem;
          background-color: #f8fafc;
          border-bottom: 1px solid #e5e7eb;
        }

        .status-dot {
          width: 10px;
          height: 10px;
          border-radius: 50%;
          animation: pulse 2s infinite;
        }

        .status-online {
          background-color: #10b981;
        }

        .status-offline {
          background-color: #ef4444;
        }

        .status-text {
          font-size: 0.875rem;
          color: #6b7280;
          font-weight: 500;
        }

        .drawer-nav {
          flex: 1;
          padding: 1rem 0;
          overflow-y: auto;
        }

        .drawer-nav-list {
          list-style: none;
          margin: 0;
          padding: 0;
        }

        .drawer-nav-link {
          display: flex;
          align-items: center;
          gap: 1rem;
          padding: 1rem 1.25rem;
          text-decoration: none;
          color: #374151;
          font-weight: 500;
          transition: all 0.2s;
          position: relative;
          border-left: 3px solid transparent;
        }

        .drawer-nav-link:hover {
          background-color: #f3f4f6;
          color: #3b82f6;
        }

        .drawer-nav-link-active {
          background-color: #eff6ff;
          color: #3b82f6;
          border-left-color: #3b82f6;
          font-weight: 600;
        }

        .nav-icon {
          font-size: 1.25rem;
          width: 1.5rem;
          text-align: center;
          filter: grayscale(0.3);
          transition: filter 0.2s;
        }

        .drawer-nav-link:hover .nav-icon,
        .drawer-nav-link-active .nav-icon {
          filter: grayscale(0);
        }

        .nav-text {
          flex: 1;
        }

        .nav-indicator {
          width: 6px;
          height: 6px;
          background-color: #3b82f6;
          border-radius: 50%;
        }

        .drawer-footer {
          padding: 1.25rem;
          border-top: 1px solid #e5e7eb;
          background-color: #f9fafb;
        }

        .footer-info {
          text-align: center;
        }

        .footer-text {
          font-size: 0.875rem;
          color: #6b7280;
          margin: 0 0 0.25rem 0;
          font-weight: 500;
        }

        .footer-version {
          font-size: 0.75rem;
          color: #9ca3af;
          margin: 0;
          font-family: 'SF Mono', 'Monaco', 'Inconsolata', 'Roboto Mono', monospace;
        }

        @keyframes fadeIn {
          from {
            opacity: 0;
          }
          to {
            opacity: 1;
          }
        }

        @keyframes pulse {
          0%, 100% {
            opacity: 1;
          }
          50% {
            opacity: 0.7;
          }
        }

        @media (min-width: 768px) {
          .drawer {
            display: none;
          }
          .drawer-backdrop {
            display: none;
          }
        }
      `}</style>
    </>
  );
};

// Bottom Navigation for Mobile
interface BottomNavigationProps {
  navigation: NavigationItem[];
  className?: string;
}

export const BottomNavigation: React.FC<BottomNavigationProps> = ({ navigation, className }) => {
  const location = useLocation();
  const { isMobile, windowSize, isTouchDevice } = useResponsive();

  // Enhanced visibility management with responsive behavior
  const [isVisible, setIsVisible] = useState(true);
  const [lastScrollY, setLastScrollY] = useState(0);
  const [isKeyboardVisible, setIsKeyboardVisible] = useState(false);

  // Enhanced scroll behavior with better performance
  useEffect(() => {
    let ticking = false;
    
    const handleScroll = () => {
      if (!ticking) {
        requestAnimationFrame(() => {
          const currentScrollY = window.scrollY;
          
          // More sophisticated visibility logic
          if (currentScrollY > lastScrollY && currentScrollY > 150) {
            setIsVisible(false); // Hide on scroll down
          } else if (currentScrollY < lastScrollY || currentScrollY < 50) {
            setIsVisible(true); // Show on scroll up or near top
          }
          
          setLastScrollY(currentScrollY);
          ticking = false;
        });
        ticking = true;
      }
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, [lastScrollY]);

  // Detect virtual keyboard on mobile
  useEffect(() => {
    if (isTouchDevice && isMobile) {
      const handleResize = () => {
        const heightDiff = window.screen.height - windowSize.height;
        setIsKeyboardVisible(heightDiff > 150);
      };

      window.addEventListener('resize', handleResize, { passive: true });
      return () => window.removeEventListener('resize', handleResize);
    }
    return undefined;
  }, [isTouchDevice, isMobile, windowSize.height]);

  // Hide on desktop or when keyboard is visible
  if (!isMobile || isKeyboardVisible) {
    return null;
  }

  return (
    <nav className={`bottom-nav ${isVisible ? 'bottom-nav-visible' : 'bottom-nav-hidden'} ${className || ''}`}>
      <div className="bottom-nav-container">
        {navigation.map((item) => {
          const isActive = location.pathname.startsWith(item.href) || 
                          (item.href === '/' && location.pathname === '/');
          
          return (
            <Link
              key={item.name}
              to={item.href}
              className={`bottom-nav-link ${isActive ? 'bottom-nav-link-active' : ''}`}
              {...(isTouchDevice ? {
                onTouchStart: (e) => {
                  // Enhanced touch feedback
                  const target = e.currentTarget;
                  target.style.transform = 'scale(0.95)';
                },
                onTouchEnd: (e) => {
                  const target = e.currentTarget;
                  target.style.transform = 'scale(1)';
                }
              } : {})}
            >
              <span className="bottom-nav-icon">{item.icon}</span>
              <span className="bottom-nav-text">{item.name}</span>
              {isActive && <span className="bottom-nav-indicator" />}
            </Link>
          );
        })}
      </div>

      <style jsx>{`
        .bottom-nav {
          position: fixed;
          bottom: 0;
          left: 0;
          right: 0;
          background-color: #ffffff;
          border-top: 1px solid #e5e7eb;
          z-index: 50;
          transition: transform 0.3s ease-in-out;
          box-shadow: 0 -2px 10px rgba(0, 0, 0, 0.1);
          backdrop-filter: blur(10px);
          background-color: rgba(255, 255, 255, 0.95);
        }

        .bottom-nav-visible {
          transform: translateY(0);
        }

        .bottom-nav-hidden {
          transform: translateY(100%);
        }

        .bottom-nav-container {
          display: flex;
          max-width: 100%;
          margin: 0 auto;
          padding: 0.5rem 0;
        }

        .bottom-nav-link {
          flex: 1;
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 0.25rem;
          padding: 0.75rem 0.5rem;
          text-decoration: none;
          color: #6b7280;
          font-weight: 500;
          transition: all 0.2s;
          position: relative;
          min-height: 60px;
          justify-content: center;
        }

        .bottom-nav-link:hover {
          color: #3b82f6;
          background-color: rgba(59, 130, 246, 0.05);
        }

        .bottom-nav-link-active {
          color: #3b82f6;
          background-color: rgba(59, 130, 246, 0.1);
        }

        .bottom-nav-icon {
          font-size: 1.25rem;
          transition: transform 0.2s;
        }

        .bottom-nav-link:active .bottom-nav-icon {
          transform: scale(0.9);
        }

        .bottom-nav-text {
          font-size: 0.75rem;
          line-height: 1;
          text-align: center;
          max-width: 100%;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }

        .bottom-nav-indicator {
          position: absolute;
          top: 0;
          left: 50%;
          transform: translateX(-50%);
          width: 24px;
          height: 3px;
          background-color: #3b82f6;
          border-radius: 0 0 3px 3px;
        }

        /* Add bottom padding to body when bottom nav is present */
        :global(body) {
          padding-bottom: 80px;
        }

        @media (min-width: 768px) {
          .bottom-nav {
            display: none;
          }
          
          :global(body) {
            padding-bottom: 0;
          }
        }

        /* Safe area support for devices with notches */
        @supports (padding: max(0px)) {
          .bottom-nav-container {
            padding-bottom: max(0.5rem, env(safe-area-inset-bottom));
          }
        }
      `}</style>
    </nav>
  );
};

// Mobile-optimized Fab (Floating Action Button)
interface FloatingActionButtonProps {
  onClick: () => void;
  icon: string;
  label: string;
  variant?: 'primary' | 'secondary';
  className?: string;
}

export const FloatingActionButton: React.FC<FloatingActionButtonProps> = ({
  onClick,
  icon,
  label,
  variant = 'primary',
  className
}) => {
  const [isVisible, setIsVisible] = useState(true);
  const [lastScrollY, setLastScrollY] = useState(0);

  useEffect(() => {
    const handleScroll = () => {
      const currentScrollY = window.scrollY;
      
      if (currentScrollY > lastScrollY && currentScrollY > 100) {
        setIsVisible(false);
      } else {
        setIsVisible(true);
      }
      
      setLastScrollY(currentScrollY);
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, [lastScrollY]);

  return (
    <button
      onClick={onClick}
      className={`fab ${variant} ${isVisible ? 'fab-visible' : 'fab-hidden'} ${className || ''}`}
      aria-label={label}
      title={label}
    >
      <span className="fab-icon">{icon}</span>

      <style jsx>{`
        .fab {
          position: fixed;
          bottom: 100px;
          right: 1rem;
          width: 56px;
          height: 56px;
          border-radius: 50%;
          border: none;
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
          transition: all 0.3s ease;
          z-index: 40;
          backdrop-filter: blur(10px);
        }

        .fab.primary {
          background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
          color: white;
        }

        .fab.secondary {
          background: rgba(255, 255, 255, 0.9);
          color: #374151;
          border: 1px solid #e5e7eb;
        }

        .fab:hover {
          transform: scale(1.1);
          box-shadow: 0 6px 16px rgba(0, 0, 0, 0.2);
        }

        .fab:active {
          transform: scale(0.95);
        }

        .fab-visible {
          transform: translateY(0) scale(1);
          opacity: 1;
        }

        .fab-hidden {
          transform: translateY(20px) scale(0.8);
          opacity: 0;
          pointer-events: none;
        }

        .fab-icon {
          font-size: 1.5rem;
          line-height: 1;
        }

        @media (min-width: 768px) {
          .fab {
            display: none;
          }
        }

        /* Safe area support */
        @supports (padding: max(0px)) {
          .fab {
            bottom: max(100px, calc(100px + env(safe-area-inset-bottom)));
          }
        }
      `}</style>
    </button>
  );
};