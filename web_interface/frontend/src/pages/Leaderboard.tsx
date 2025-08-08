import React from 'react';
import { LeaderboardView } from '../components/LeaderboardView';

export const Leaderboard: React.FC = () => {
  return (
    <div className="leaderboard-page">
      <div className="page-container">
        <div className="page-header">
          <h1 className="page-title">Leaderboard</h1>
          <p className="page-description">
            Compare player performance with rankings, win rates, and detailed metrics.
          </p>
        </div>
        
        <LeaderboardView />
      </div>

      <style jsx>{`
        .leaderboard-page {
          padding: 2rem 1rem;
          min-height: calc(100vh - 200px);
        }

        .page-container {
          max-width: 1200px;
          margin: 0 auto;
        }

        .page-header {
          text-align: center;
          margin-bottom: 3rem;
        }

        .page-title {
          font-size: 2rem;
          font-weight: 700;
          color: #1f2937;
          margin-bottom: 0.5rem;
        }

        .page-description {
          font-size: 1.125rem;
          color: #6b7280;
          max-width: 600px;
          margin: 0 auto;
        }
      `}</style>
    </div>
  );
};