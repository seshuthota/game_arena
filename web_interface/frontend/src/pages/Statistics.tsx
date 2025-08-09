import React from 'react';
import { StatisticsDashboard } from '../components/StatisticsDashboard';

export const Statistics: React.FC = () => {
  return (
    <div className="statistics-page">
      <div className="page-container">
        <div className="page-header">
          <h1 className="page-title">Statistics</h1>
          <p className="page-description">
            View comprehensive statistics and trends across all games and players.
          </p>
        </div>
        
        <StatisticsDashboard />
      </div>

      <style jsx>{`
        .statistics-page {
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