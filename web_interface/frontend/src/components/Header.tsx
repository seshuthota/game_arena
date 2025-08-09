import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useHealthCheck } from '../hooks/useApi';
import { MobileDrawer } from './MobileNavigation';

interface HeaderProps {
  onToggleSidebar?: () => void;
}

export const Header: React.FC<HeaderProps> = ({ onToggleSidebar }) => {
  const location = useLocation();
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const { data: healthData, isError: healthError } = useHealthCheck();

  const navigation = [
    { name: 'Games', href: '/games', icon: '🎮', current: location.pathname.startsWith('/games') },
    { name: 'Statistics', href: '/statistics', icon: '📊', current: location.pathname.startsWith('/statistics') },
    { name: 'Leaderboard', href: '/leaderboard', icon: '🏆', current: location.pathname.startsWith('/leaderboard') },
  ];

  const toggleMenu = () => {
    setIsMenuOpen(!isMenuOpen);
  };

  return (
    <header className="header">
      <div className="header-container">
        {/* Logo and Title */}
        <div className="header-brand">
          <Link to="/" className="brand-link">
            <div className="brand-icon">⚡</div>
            <h1 className="brand-title">Game Analysis</h1>
          </Link>
        </div>

        {/* Desktop Navigation */}
        <nav className="desktop-nav">
          <ul className="nav-list">
            {navigation.map((item) => (
              <li key={item.name}>
                <Link
                  to={item.href}
                  className={`nav-link ${item.current ? 'nav-link-active' : ''}`}
                >
                  {item.name}
                </Link>
              </li>
            ))}
          </ul>
        </nav>

        {/* Status Indicator and Mobile Menu Button */}
        <div className="header-actions">
          {/* API Status Indicator */}
          <div className="status-indicator">
            <div 
              className={`status-dot ${healthError ? 'status-error' : 'status-healthy'}`}
              title={healthError ? 'API Unavailable' : 'API Connected'}
            />
            <span className="status-text">
              {healthError ? 'Offline' : 'Online'}
            </span>
          </div>

          {/* Mobile Menu Button */}
          <button
            className="mobile-menu-button"
            onClick={toggleMenu}
            aria-label="Toggle navigation menu"
          >
            <span className={`menu-icon ${isMenuOpen ? 'menu-icon-open' : ''}`}>
              <span></span>
              <span></span>
              <span></span>
            </span>
          </button>
        </div>
      </div>

      {/* Mobile Drawer Navigation */}
      <MobileDrawer 
        isOpen={isMenuOpen} 
        onClose={() => setIsMenuOpen(false)} 
        navigation={navigation}
      />

      <style jsx>{`
        .header {
          background-color: #ffffff;
          box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
          position: sticky;
          top: 0;
          z-index: 50;
          border-bottom: 1px solid #e5e7eb;
        }

        .header-container {
          max-width: 1200px;
          margin: 0 auto;
          padding: 0 1rem;
          display: flex;
          justify-content: space-between;
          align-items: center;
          height: 4rem;
        }

        .header-brand {
          display: flex;
          align-items: center;
        }

        .brand-link {
          display: flex;
          align-items: center;
          text-decoration: none;
          color: #1f2937;
          transition: color 0.2s;
        }

        .brand-link:hover {
          color: #3b82f6;
        }

        .brand-icon {
          font-size: 1.5rem;
          margin-right: 0.75rem;
        }

        .brand-title {
          font-size: 1.25rem;
          font-weight: 600;
          margin: 0;
        }

        .desktop-nav {
          display: none;
        }

        @media (min-width: 768px) {
          .desktop-nav {
            display: block;
          }
        }

        .nav-list {
          display: flex;
          list-style: none;
          margin: 0;
          padding: 0;
          gap: 2rem;
        }

        .nav-link {
          text-decoration: none;
          color: #6b7280;
          font-weight: 500;
          padding: 0.5rem 0;
          transition: color 0.2s;
          position: relative;
        }

        .nav-link:hover {
          color: #3b82f6;
        }

        .nav-link-active {
          color: #3b82f6;
        }

        .nav-link-active::after {
          content: '';
          position: absolute;
          bottom: -0.5rem;
          left: 0;
          right: 0;
          height: 2px;
          background-color: #3b82f6;
        }

        .header-actions {
          display: flex;
          align-items: center;
          gap: 1rem;
        }

        .status-indicator {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          font-size: 0.875rem;
        }

        .status-dot {
          width: 8px;
          height: 8px;
          border-radius: 50%;
          transition: background-color 0.2s;
        }

        .status-healthy {
          background-color: #10b981;
        }

        .status-error {
          background-color: #ef4444;
        }

        .status-text {
          color: #6b7280;
          font-weight: 500;
        }

        .mobile-menu-button {
          display: flex;
          align-items: center;
          padding: 0.5rem;
          background: none;
          border: none;
          cursor: pointer;
        }

        @media (min-width: 768px) {
          .mobile-menu-button {
            display: none;
          }
        }

        .menu-icon {
          width: 24px;
          height: 24px;
          position: relative;
          transform: rotate(0deg);
          transition: 0.3s ease-in-out;
        }

        .menu-icon span {
          display: block;
          position: absolute;
          height: 2px;
          width: 100%;
          background: #374151;
          border-radius: 2px;
          opacity: 1;
          left: 0;
          transform: rotate(0deg);
          transition: 0.2s ease-in-out;
        }

        .menu-icon span:nth-child(1) {
          top: 6px;
        }

        .menu-icon span:nth-child(2) {
          top: 12px;
        }

        .menu-icon span:nth-child(3) {
          top: 18px;
        }

        .menu-icon-open span:nth-child(1) {
          top: 12px;
          transform: rotate(135deg);
        }

        .menu-icon-open span:nth-child(2) {
          opacity: 0;
          left: -24px;
        }

        .menu-icon-open span:nth-child(3) {
          top: 12px;
          transform: rotate(-135deg);
        }

        .mobile-nav {
          display: block;
          background-color: #ffffff;
          border-top: 1px solid #e5e7eb;
          padding: 1rem;
        }

        .header {
          backdrop-filter: blur(10px);
          background-color: rgba(255, 255, 255, 0.95);
          position: sticky;
          top: 0;
          z-index: 100;
        }
      `}</style>
    </header>
  );
};