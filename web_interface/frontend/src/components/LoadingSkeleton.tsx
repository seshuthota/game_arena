import React from 'react';

interface LoadingSkeletonProps {
  width?: string;
  height?: string;
  className?: string;
  variant?: 'text' | 'rectangular' | 'circular';
  animation?: 'pulse' | 'wave' | 'none';
}

export const LoadingSkeleton: React.FC<LoadingSkeletonProps> = ({
  width = '100%',
  height = '1rem',
  className = '',
  variant = 'rectangular',
  animation = 'pulse'
}) => {
  return (
    <div
      className={`loading-skeleton ${variant} ${animation} ${className}`}
      style={{ width, height }}
    >
      <style jsx>{`
        .loading-skeleton {
          background-color: #e5e7eb;
          border-radius: ${variant === 'circular' ? '50%' : variant === 'text' ? '0.25rem' : '0.375rem'};
          display: inline-block;
        }

        .loading-skeleton.pulse {
          animation: pulse 1.5s ease-in-out infinite;
        }

        .loading-skeleton.wave {
          background: linear-gradient(90deg, #e5e7eb 25%, #d1d5db 50%, #e5e7eb 75%);
          background-size: 200% 100%;
          animation: wave 1.5s ease-in-out infinite;
        }

        .loading-skeleton.text {
          height: 1em;
          margin-bottom: 0.5rem;
        }

        @keyframes pulse {
          0%, 100% {
            opacity: 1;
          }
          50% {
            opacity: 0.5;
          }
        }

        @keyframes wave {
          0% {
            background-position: 200% 0;
          }
          100% {
            background-position: -200% 0;
          }
        }
      `}</style>
    </div>
  );
};

// Game List Loading Skeletons
export const GameListSkeleton: React.FC = () => {
  return (
    <div className="game-list-skeleton">
      {/* Controls Bar Skeleton */}
      <div className="skeleton-controls">
        <LoadingSkeleton width="200px" height="1.5rem" />
        <div className="skeleton-controls-group">
          <LoadingSkeleton width="120px" height="2rem" />
          <LoadingSkeleton width="100px" height="2rem" />
        </div>
      </div>

      {/* Table Header Skeleton */}
      <div className="skeleton-table-header">
        <LoadingSkeleton width="100px" height="1rem" />
        <LoadingSkeleton width="150px" height="1rem" />
        <LoadingSkeleton width="80px" height="1rem" />
        <LoadingSkeleton width="70px" height="1rem" />
        <LoadingSkeleton width="60px" height="1rem" />
        <LoadingSkeleton width="120px" height="1rem" />
      </div>

      {/* Game Rows Skeletons */}
      {Array.from({ length: 10 }).map((_, index) => (
        <div key={index} className="skeleton-game-row">
          <LoadingSkeleton width="120px" height="1.5rem" />
          <div className="skeleton-players">
            <LoadingSkeleton width="140px" height="1rem" />
            <LoadingSkeleton width="140px" height="1rem" />
          </div>
          <LoadingSkeleton width="80px" height="1.5rem" variant="rectangular" />
          <LoadingSkeleton width="60px" height="1rem" />
          <LoadingSkeleton width="50px" height="1rem" />
          <LoadingSkeleton width="100px" height="1rem" />
        </div>
      ))}

      <style jsx>{`
        .game-list-skeleton {
          background-color: white;
          border: 1px solid #e5e7eb;
          border-radius: 0.5rem;
          overflow: hidden;
        }

        .skeleton-controls {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 1rem;
          background-color: #ffffff;
          border-bottom: 1px solid #e5e7eb;
        }

        .skeleton-controls-group {
          display: flex;
          gap: 1rem;
          align-items: center;
        }

        .skeleton-table-header {
          display: grid;
          grid-template-columns: 1fr 2fr 1.5fr 1fr 1fr 1.5fr;
          align-items: center;
          padding: 0.75rem 1rem;
          background-color: #f9fafb;
          border-bottom: 1px solid #e5e7eb;
          gap: 1rem;
        }

        .skeleton-game-row {
          display: grid;
          grid-template-columns: 1fr 2fr 1.5fr 1fr 1fr 1.5fr;
          align-items: center;
          padding: 0.75rem 1rem;
          border-bottom: 1px solid #e5e7eb;
          gap: 1rem;
        }

        .skeleton-players {
          display: flex;
          flex-direction: column;
          gap: 0.25rem;
        }

        @media (max-width: 768px) {
          .skeleton-table-header,
          .skeleton-game-row {
            grid-template-columns: 1fr 1.5fr 1fr 0.8fr;
          }

          .skeleton-game-row > :nth-child(5),
          .skeleton-game-row > :nth-child(6),
          .skeleton-table-header > :nth-child(5),
          .skeleton-table-header > :nth-child(6) {
            display: none;
          }
        }
      `}</style>
    </div>
  );
};

// Statistics Dashboard Loading Skeleton
export const StatisticsSkeleton: React.FC = () => {
  return (
    <div className="statistics-skeleton">
      {/* Metrics Cards Skeleton */}
      <div className="skeleton-metrics-grid">
        {Array.from({ length: 4 }).map((_, index) => (
          <div key={index} className="skeleton-metric-card">
            <div className="skeleton-metric-header">
              <LoadingSkeleton width="2rem" height="2rem" variant="circular" />
              <LoadingSkeleton width="60px" height="1.5rem" />
            </div>
            <LoadingSkeleton width="80px" height="2.5rem" />
            <LoadingSkeleton width="120px" height="1rem" />
            <LoadingSkeleton width="100px" height="0.875rem" />
          </div>
        ))}
      </div>

      {/* Chart Section Skeleton */}
      <div className="skeleton-chart-section">
        <div className="skeleton-chart-header">
          <LoadingSkeleton width="200px" height="1.5rem" />
          <div className="skeleton-chart-controls">
            <LoadingSkeleton width="120px" height="2rem" />
            <LoadingSkeleton width="120px" height="2rem" />
          </div>
        </div>
        <LoadingSkeleton width="100%" height="300px" />
      </div>

      {/* Charts Grid Skeleton */}
      <div className="skeleton-charts-grid">
        <div className="skeleton-chart-card">
          <LoadingSkeleton width="150px" height="1.125rem" />
          <LoadingSkeleton width="100%" height="250px" />
        </div>
        <div className="skeleton-chart-card">
          <LoadingSkeleton width="120px" height="1.125rem" />
          <LoadingSkeleton width="100%" height="250px" />
        </div>
      </div>

      <style jsx>{`
        .statistics-skeleton {
          display: flex;
          flex-direction: column;
          gap: 2rem;
        }

        .skeleton-metrics-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
          gap: 1.5rem;
        }

        .skeleton-metric-card {
          background-color: #ffffff;
          border: 1px solid #e5e7eb;
          border-radius: 0.75rem;
          padding: 1.5rem;
          display: flex;
          flex-direction: column;
          gap: 1rem;
        }

        .skeleton-metric-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
        }

        .skeleton-chart-section {
          background-color: #ffffff;
          border: 1px solid #e5e7eb;
          border-radius: 0.75rem;
          padding: 1.5rem;
        }

        .skeleton-chart-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 1.5rem;
          flex-wrap: wrap;
          gap: 1rem;
        }

        .skeleton-chart-controls {
          display: flex;
          gap: 1rem;
          align-items: center;
        }

        .skeleton-charts-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
          gap: 2rem;
        }

        .skeleton-chart-card {
          background-color: #ffffff;
          border: 1px solid #e5e7eb;
          border-radius: 0.75rem;
          padding: 1.5rem;
          display: flex;
          flex-direction: column;
          gap: 1rem;
        }

        @media (max-width: 768px) {
          .skeleton-metrics-grid {
            grid-template-columns: 1fr;
          }

          .skeleton-charts-grid {
            grid-template-columns: 1fr;
          }

          .skeleton-chart-header {
            flex-direction: column;
            align-items: stretch;
          }
        }
      `}</style>
    </div>
  );
};

// Game Detail Loading Skeleton
export const GameDetailSkeleton: React.FC = () => {
  return (
    <div className="game-detail-skeleton">
      {/* Breadcrumb Skeleton */}
      <div className="skeleton-breadcrumb">
        <LoadingSkeleton width="60px" height="1rem" />
        <span>/</span>
        <LoadingSkeleton width="100px" height="1rem" />
      </div>

      {/* Game Header Skeleton */}
      <div className="skeleton-game-header">
        <div className="skeleton-header-main">
          <div className="skeleton-title-section">
            <LoadingSkeleton width="200px" height="2rem" />
            <LoadingSkeleton width="300px" height="1rem" />
            <LoadingSkeleton width="180px" height="1rem" />
          </div>
          <div className="skeleton-result-section">
            <LoadingSkeleton width="120px" height="1.5rem" />
            <LoadingSkeleton width="80px" height="1rem" />
          </div>
        </div>

        {/* Players Skeleton */}
        <div className="skeleton-players">
          <div className="skeleton-player-card">
            <div className="skeleton-player-header">
              <LoadingSkeleton width="1.25rem" height="1.25rem" variant="circular" />
              <LoadingSkeleton width="60px" height="1rem" />
            </div>
            <LoadingSkeleton width="150px" height="1.25rem" />
            <div className="skeleton-player-details">
              <LoadingSkeleton width="100%" height="0.875rem" />
              <LoadingSkeleton width="100%" height="0.875rem" />
              <LoadingSkeleton width="80%" height="0.875rem" />
            </div>
          </div>

          <LoadingSkeleton width="40px" height="1.5rem" />

          <div className="skeleton-player-card">
            <div className="skeleton-player-header">
              <LoadingSkeleton width="1.25rem" height="1.25rem" variant="circular" />
              <LoadingSkeleton width="60px" height="1rem" />
            </div>
            <LoadingSkeleton width="150px" height="1.25rem" />
            <div className="skeleton-player-details">
              <LoadingSkeleton width="100%" height="0.875rem" />
              <LoadingSkeleton width="100%" height="0.875rem" />
              <LoadingSkeleton width="80%" height="0.875rem" />
            </div>
          </div>
        </div>

        {/* Metadata Skeleton */}
        <div className="skeleton-metadata">
          <LoadingSkeleton width="150px" height="1.125rem" />
          <div className="skeleton-metadata-grid">
            {Array.from({ length: 5 }).map((_, index) => (
              <div key={index} className="skeleton-metadata-item">
                <LoadingSkeleton width="80px" height="0.8125rem" />
                <LoadingSkeleton width="120px" height="0.875rem" />
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Move List Skeleton */}
      <div className="skeleton-move-list">
        <div className="skeleton-move-header">
          <LoadingSkeleton width="150px" height="1.25rem" />
          <LoadingSkeleton width="80px" height="1.5rem" variant="rectangular" />
        </div>

        <div className="skeleton-move-content">
          <div className="skeleton-nav-controls">
            {Array.from({ length: 4 }).map((_, index) => (
              <LoadingSkeleton key={index} width="2.5rem" height="2rem" />
            ))}
            <LoadingSkeleton width="150px" height="1rem" />
          </div>

          <div className="skeleton-moves-grid">
            {Array.from({ length: 12 }).map((_, index) => (
              <div key={index} className="skeleton-move-item">
                <LoadingSkeleton width="2rem" height="1rem" />
                <LoadingSkeleton width="80px" height="1rem" />
                <div className="skeleton-move-meta">
                  <LoadingSkeleton width="40px" height="0.75rem" />
                  <LoadingSkeleton width="60px" height="0.75rem" />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <style jsx>{`
        .game-detail-skeleton {
          padding: 2rem 1rem;
          min-height: calc(100vh - 200px);
          max-width: 1200px;
          margin: 0 auto;
        }

        .skeleton-breadcrumb {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          margin-bottom: 2rem;
          color: #9ca3af;
        }

        .skeleton-game-header {
          background-color: #ffffff;
          border: 1px solid #e5e7eb;
          border-radius: 0.75rem;
          padding: 2rem;
          margin-bottom: 2rem;
          display: flex;
          flex-direction: column;
          gap: 2rem;
        }

        .skeleton-header-main {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          flex-wrap: wrap;
          gap: 1rem;
        }

        .skeleton-title-section {
          display: flex;
          flex-direction: column;
          gap: 0.5rem;
        }

        .skeleton-result-section {
          display: flex;
          flex-direction: column;
          align-items: flex-end;
          gap: 0.25rem;
        }

        .skeleton-players {
          display: flex;
          gap: 2rem;
          align-items: center;
          flex-wrap: wrap;
        }

        .skeleton-player-card {
          flex: 1;
          min-width: 250px;
          background-color: #f9fafb;
          border: 1px solid #e5e7eb;
          border-radius: 0.5rem;
          padding: 1.5rem;
          display: flex;
          flex-direction: column;
          gap: 1rem;
        }

        .skeleton-player-header {
          display: flex;
          align-items: center;
          gap: 0.5rem;
        }

        .skeleton-player-details {
          display: flex;
          flex-direction: column;
          gap: 0.5rem;
        }

        .skeleton-metadata {
          background-color: #f9fafb;
          border-radius: 0.5rem;
          padding: 1.5rem;
          display: flex;
          flex-direction: column;
          gap: 1rem;
        }

        .skeleton-metadata-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
          gap: 1rem;
        }

        .skeleton-metadata-item {
          display: flex;
          flex-direction: column;
          gap: 0.25rem;
        }

        .skeleton-move-list {
          background-color: #ffffff;
          border: 1px solid #e5e7eb;
          border-radius: 0.75rem;
          overflow: hidden;
        }

        .skeleton-move-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 1.5rem 2rem;
          background-color: #f9fafb;
          border-bottom: 1px solid #e5e7eb;
        }

        .skeleton-move-content {
          padding: 2rem;
          display: flex;
          flex-direction: column;
          gap: 1rem;
        }

        .skeleton-nav-controls {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          padding: 1rem;
          background-color: #f9fafb;
          border-radius: 0.5rem;
          border: 1px solid #e5e7eb;
        }

        .skeleton-nav-controls > :last-child {
          margin-left: auto;
        }

        .skeleton-moves-grid {
          display: grid;
          gap: 0.5rem;
        }

        .skeleton-move-item {
          display: grid;
          grid-template-columns: auto 1fr auto;
          align-items: center;
          padding: 0.75rem 1rem;
          border: 1px solid #e5e7eb;
          border-radius: 0.5rem;
          background-color: #ffffff;
        }

        .skeleton-move-meta {
          display: flex;
          flex-direction: column;
          align-items: flex-end;
          gap: 0.25rem;
        }

        @media (max-width: 768px) {
          .skeleton-game-header {
            padding: 1.5rem;
          }

          .skeleton-header-main {
            flex-direction: column;
            align-items: stretch;
          }

          .skeleton-result-section {
            align-items: flex-start;
          }

          .skeleton-players {
            flex-direction: column;
            align-items: stretch;
          }

          .skeleton-player-card {
            min-width: auto;
          }

          .skeleton-metadata-grid {
            grid-template-columns: 1fr;
          }
        }
      `}</style>
    </div>
  );
};