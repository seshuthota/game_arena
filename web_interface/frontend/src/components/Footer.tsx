import React from 'react';
import { Link } from 'react-router-dom';

export const Footer: React.FC = () => {
  const currentYear = new Date().getFullYear();

  const footerLinks = {
    product: [
      { name: 'Games', href: '/games' },
      { name: 'Statistics', href: '/statistics' },
      { name: 'Leaderboard', href: '/leaderboard' },
    ],
    resources: [
      { name: 'API Documentation', href: '/api/docs', external: true },
      { name: 'Health Status', href: '/api/health', external: true },
    ],
  };

  return (
    <footer className="footer">
      <div className="footer-container">
        <div className="footer-content">
          {/* Brand Section */}
          <div className="footer-brand">
            <div className="brand-section">
              <div className="brand-icon">⚡</div>
              <h3 className="brand-name">Game Analysis</h3>
            </div>
            <p className="brand-description">
              Comprehensive analytics for LLM vs LLM chess games. 
              Track performance, analyze moves, and discover insights.
            </p>
          </div>

          {/* Links Sections */}
          <div className="footer-links">
            <div className="link-section">
              <h4 className="link-section-title">Features</h4>
              <ul className="link-list">
                {footerLinks.product.map((link) => (
                  <li key={link.name}>
                    <Link to={link.href} className="footer-link">
                      {link.name}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>

            <div className="link-section">
              <h4 className="link-section-title">Resources</h4>
              <ul className="link-list">
                {footerLinks.resources.map((link) => (
                  <li key={link.name}>
                    {link.external ? (
                      <a 
                        href={link.href} 
                        className="footer-link"
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        {link.name}
                        <span className="external-icon">↗</span>
                      </a>
                    ) : (
                      <Link to={link.href} className="footer-link">
                        {link.name}
                      </Link>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>

        {/* Bottom Section */}
        <div className="footer-bottom">
          <div className="footer-bottom-content">
            <p className="copyright">
              © {currentYear} Game Analysis Dashboard. Built for analyzing LLM chess gameplay.
            </p>
            <div className="footer-meta">
              <span className="meta-item">
                Powered by Google DeepMind Game Arena
              </span>
              <span className="meta-separator">•</span>
              <span className="meta-item">
                React + FastAPI
              </span>
            </div>
          </div>
        </div>
      </div>

      <style jsx>{`
        .footer {
          background-color: #1f2937;
          color: #d1d5db;
          margin-top: auto;
        }

        .footer-container {
          max-width: 1200px;
          margin: 0 auto;
          padding: 3rem 1rem 1rem;
        }

        .footer-content {
          display: grid;
          gap: 2rem;
          grid-template-columns: 1fr;
        }

        @media (min-width: 768px) {
          .footer-content {
            grid-template-columns: 1fr 1fr;
            gap: 3rem;
          }
        }

        @media (min-width: 1024px) {
          .footer-content {
            grid-template-columns: 2fr 1fr;
            gap: 4rem;
          }
        }

        .footer-brand {
          max-width: 400px;
        }

        .brand-section {
          display: flex;
          align-items: center;
          margin-bottom: 1rem;
        }

        .brand-icon {
          font-size: 1.5rem;
          margin-right: 0.75rem;
          color: #3b82f6;
        }

        .brand-name {
          font-size: 1.25rem;
          font-weight: 600;
          color: #f9fafb;
          margin: 0;
        }

        .brand-description {
          font-size: 0.875rem;
          line-height: 1.6;
          color: #9ca3af;
          margin: 0;
        }

        .footer-links {
          display: grid;
          gap: 2rem;
          grid-template-columns: 1fr;
        }

        @media (min-width: 640px) {
          .footer-links {
            grid-template-columns: 1fr 1fr;
          }
        }

        .link-section {
        }

        .link-section-title {
          font-size: 0.875rem;
          font-weight: 600;
          color: #f9fafb;
          margin: 0 0 1rem 0;
          text-transform: uppercase;
          letter-spacing: 0.05em;
        }

        .link-list {
          list-style: none;
          padding: 0;
          margin: 0;
        }

        .link-list li {
          margin-bottom: 0.5rem;
        }

        .footer-link {
          font-size: 0.875rem;
          color: #9ca3af;
          text-decoration: none;
          transition: color 0.2s;
          display: inline-flex;
          align-items: center;
        }

        .footer-link:hover {
          color: #3b82f6;
        }

        .external-icon {
          margin-left: 0.25rem;
          font-size: 0.75rem;
        }

        .footer-bottom {
          border-top: 1px solid #374151;
          margin-top: 2rem;
          padding-top: 2rem;
        }

        .footer-bottom-content {
          display: flex;
          flex-direction: column;
          gap: 0.5rem;
          text-align: center;
        }

        @media (min-width: 768px) {
          .footer-bottom-content {
            flex-direction: row;
            justify-content: space-between;
            align-items: center;
            text-align: left;
          }
        }

        .copyright {
          font-size: 0.875rem;
          color: #9ca3af;
          margin: 0;
        }

        .footer-meta {
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 0.5rem;
          font-size: 0.875rem;
          color: #6b7280;
        }

        @media (min-width: 768px) {
          .footer-meta {
            justify-content: flex-end;
          }
        }

        .meta-item {
        }

        .meta-separator {
          color: #4b5563;
        }
      `}</style>
    </footer>
  );
};