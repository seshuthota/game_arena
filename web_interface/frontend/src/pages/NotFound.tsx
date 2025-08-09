import React from 'react';
import { Link } from 'react-router-dom';

export const NotFound: React.FC = () => {
  return (
    <div className="not-found">
      <div className="not-found-container">
        <div className="not-found-content">
          <div className="error-code">404</div>
          <h1 className="error-title">Page not found</h1>
          <p className="error-description">
            The page you are looking for might have been moved, deleted, or does not exist.
          </p>
          
          <div className="error-actions">
            <Link to="/" className="btn-primary">
              Go to Dashboard
            </Link>
            <button 
              onClick={() => window.history.back()} 
              className="btn-secondary"
            >
              Go Back
            </button>
          </div>

          <div className="helpful-links">
            <h3 className="links-title">Try these instead:</h3>
            <ul className="links-list">
              <li><Link to="/games" className="helpful-link">Browse Games</Link></li>
              <li><Link to="/statistics" className="helpful-link">View Statistics</Link></li>
              <li><Link to="/leaderboard" className="helpful-link">Check Leaderboard</Link></li>
            </ul>
          </div>
        </div>
      </div>

      <style jsx>{`
        .not-found {
          padding: 4rem 1rem;
          min-height: calc(100vh - 200px);
          display: flex;
          align-items: center;
          justify-content: center;
        }

        .not-found-container {
          max-width: 500px;
          text-align: center;
        }

        .error-code {
          font-size: 6rem;
          font-weight: 800;
          color: #3b82f6;
          margin-bottom: 1rem;
          line-height: 1;
        }

        .error-title {
          font-size: 2rem;
          font-weight: 700;
          color: #1f2937;
          margin-bottom: 1rem;
        }

        .error-description {
          font-size: 1.125rem;
          color: #6b7280;
          line-height: 1.6;
          margin-bottom: 2rem;
        }

        .error-actions {
          display: flex;
          gap: 1rem;
          justify-content: center;
          flex-wrap: wrap;
          margin-bottom: 3rem;
        }

        .btn-primary {
          display: inline-flex;
          align-items: center;
          padding: 0.75rem 1.5rem;
          background-color: #3b82f6;
          color: white;
          text-decoration: none;
          border-radius: 0.5rem;
          font-weight: 500;
          transition: background-color 0.2s;
        }

        .btn-primary:hover {
          background-color: #2563eb;
        }

        .btn-secondary {
          display: inline-flex;
          align-items: center;
          padding: 0.75rem 1.5rem;
          background-color: transparent;
          color: #6b7280;
          border: 1px solid #d1d5db;
          border-radius: 0.5rem;
          font-weight: 500;
          cursor: pointer;
          transition: all 0.2s;
        }

        .btn-secondary:hover {
          background-color: #f9fafb;
          color: #374151;
          border-color: #9ca3af;
        }

        .helpful-links {
          padding-top: 2rem;
          border-top: 1px solid #e5e7eb;
        }

        .links-title {
          font-size: 1.125rem;
          font-weight: 600;
          color: #1f2937;
          margin-bottom: 1rem;
        }

        .links-list {
          list-style: none;
          padding: 0;
          margin: 0;
          display: flex;
          flex-direction: column;
          gap: 0.5rem;
        }

        .helpful-link {
          color: #3b82f6;
          text-decoration: none;
          font-weight: 500;
          transition: color 0.2s;
        }

        .helpful-link:hover {
          color: #2563eb;
          text-decoration: underline;
        }

        @media (max-width: 640px) {
          .error-code {
            font-size: 4rem;
          }

          .error-title {
            font-size: 1.5rem;
          }

          .error-actions {
            flex-direction: column;
            align-items: center;
          }

          .btn-primary,
          .btn-secondary {
            width: 100%;
            max-width: 200px;
            justify-content: center;
          }
        }
      `}</style>
    </div>
  );
};