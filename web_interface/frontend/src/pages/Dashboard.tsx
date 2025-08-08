import React from 'react';
import { Link } from 'react-router-dom';
import { useStatisticsOverview, useHealthCheck } from '../hooks/useApi';

export const Dashboard: React.FC = () => {
  const { data: statsData, isLoading: statsLoading, error: statsError } = useStatisticsOverview();
  const { data: healthData, isError: healthError } = useHealthCheck();

  const features = [
    {
      title: 'Game Analysis',
      description: 'Browse and analyze completed games with detailed move-by-move breakdowns',
      icon: '🎯',
      link: '/games',
      color: 'blue',
    },
    {
      title: 'Performance Statistics', 
      description: 'View comprehensive statistics and trends across all games and players',
      icon: '📊',
      link: '/statistics',
      color: 'green',
    },
    {
      title: 'Player Leaderboard',
      description: 'Compare player performance with rankings, win rates, and detailed metrics',
      icon: '🏆',
      link: '/leaderboard',  
      color: 'yellow',
    },
  ];

  return (
    <div className="dashboard">
      <div className="dashboard-container">
        {/* Hero Section */}
        <section className="hero-section">
          <div className="hero-content">
            <h1 className="hero-title">Game Analysis Dashboard</h1>
            <p className="hero-description">
              Comprehensive analytics for LLM vs LLM chess games. Track performance, 
              analyze gameplay patterns, and discover insights from AI-powered chess matches.
            </p>
            
            {/* System Status */}
            <div className="system-status">
              <div className={`status-indicator ${healthError ? 'status-error' : 'status-healthy'}`}>
                <div className="status-dot"></div>
                <span className="status-text">
                  System {healthError ? 'Offline' : 'Online'}
                </span>
              </div>
            </div>
          </div>
        </section>

        {/* Quick Stats */}
        {!statsLoading && !statsError && statsData && (
          <section className="stats-section">
            <h2 className="stats-title">Quick Overview</h2>
            <div className="stats-grid">
              <div className="stat-card">
                <div className="stat-value">{statsData?.statistics?.total_games?.toLocaleString() || '0'}</div>
                <div className="stat-label">Total Games</div>
              </div>
              <div className="stat-card">
                <div className="stat-value">{statsData?.statistics?.completed_games?.toLocaleString() || '0'}</div>
                <div className="stat-label">Completed</div>
              </div>
              <div className="stat-card">
                <div className="stat-value">{statsData?.statistics?.total_players?.toLocaleString() || '0'}</div>
                <div className="stat-label">Active Players</div>
              </div>
              <div className="stat-card">
                <div className="stat-value">
                  {Math.round(statsData?.statistics?.average_game_duration || 0)}m
                </div>
                <div className="stat-label">Avg Duration</div>
              </div>
            </div>
          </section>
        )}

        {/* Features Grid */}
        <section className="features-section">
          <h2 className="features-title">Explore Features</h2>
          <div className="features-grid">
            {features.map((feature) => (
              <Link
                key={feature.title}
                to={feature.link}
                className={`feature-card feature-card-${feature.color}`}
              >
                <div className="feature-icon">{feature.icon}</div>
                <h3 className="feature-title">{feature.title}</h3>
                <p className="feature-description">{feature.description}</p>
                <div className="feature-arrow">→</div>
              </Link>
            ))}
          </div>
        </section>
      </div>

      <style jsx>{`
        .dashboard {
          padding: 2rem 1rem;
        }

        .dashboard-container {
          max-width: 1000px;
          margin: 0 auto;
        }

        .hero-section {
          text-align: center;
          margin-bottom: 3rem;
        }

        .hero-content {
          max-width: 600px;
          margin: 0 auto;
        }

        .hero-title {
          font-size: 2.5rem;
          font-weight: 700;
          color: #1f2937;
          margin-bottom: 1rem;
          line-height: 1.2;
        }

        @media (max-width: 768px) {
          .hero-title {
            font-size: 2rem;
          }
        }

        .hero-description {
          font-size: 1.125rem;
          color: #6b7280;
          line-height: 1.6;
          margin-bottom: 2rem;
        }

        .system-status {
          display: flex;
          justify-content: center;
        }

        .status-indicator {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          padding: 0.5rem 1rem;
          border-radius: 9999px;
          font-size: 0.875rem;
          font-weight: 500;
        }

        .status-healthy {
          background-color: #dcfce7;
          color: #166534;
        }

        .status-error {
          background-color: #fee2e2;
          color: #991b1b;
        }

        .status-dot {
          width: 8px;
          height: 8px;
          border-radius: 50%;
        }

        .status-healthy .status-dot {
          background-color: #10b981;
        }

        .status-error .status-dot {
          background-color: #ef4444;
        }

        .stats-section {
          margin-bottom: 3rem;
        }

        .stats-title {
          font-size: 1.5rem;
          font-weight: 600;
          color: #1f2937;
          text-align: center;
          margin-bottom: 1.5rem;
        }

        .stats-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
          gap: 1rem;
        }

        .stat-card {
          background-color: #ffffff;
          padding: 1.5rem;
          border-radius: 0.75rem;
          text-align: center;
          box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
          border: 1px solid #e5e7eb;
          transition: transform 0.2s, box-shadow 0.2s;
        }

        .stat-card:hover {
          transform: translateY(-2px);
          box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }

        .stat-value {
          font-size: 2rem;
          font-weight: 700;
          color: #3b82f6;
          margin-bottom: 0.25rem;
        }

        .stat-label {
          font-size: 0.875rem;
          color: #6b7280;
          font-weight: 500;
        }

        .features-section {
          margin-bottom: 2rem;
        }

        .features-title {
          font-size: 1.5rem;
          font-weight: 600;
          color: #1f2937;
          text-align: center;
          margin-bottom: 2rem;
        }

        .features-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
          gap: 1.5rem;
        }

        .feature-card {
          background-color: #ffffff;
          padding: 2rem;
          border-radius: 0.75rem;
          text-decoration: none;
          transition: all 0.3s;
          position: relative;
          border: 1px solid #e5e7eb;
          box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        }

        .feature-card:hover {
          transform: translateY(-4px);
          box-shadow: 0 8px 25px rgba(0, 0, 0, 0.15);
        }

        .feature-card-blue:hover {
          border-color: #3b82f6;
        }

        .feature-card-green:hover {
          border-color: #10b981;
        }

        .feature-card-yellow:hover {
          border-color: #f59e0b;
        }

        .feature-icon {
          font-size: 2.5rem;
          margin-bottom: 1rem;
          display: block;
        }

        .feature-title {
          font-size: 1.25rem;
          font-weight: 600;
          color: #1f2937;
          margin-bottom: 0.75rem;
        }

        .feature-description {
          color: #6b7280;
          line-height: 1.6;
          margin-bottom: 1rem;
        }

        .feature-arrow {
          position: absolute;
          top: 1.5rem;
          right: 1.5rem;
          font-size: 1.25rem;
          color: #9ca3af;
          transition: all 0.3s;
        }

        .feature-card:hover .feature-arrow {
          color: #3b82f6;
          transform: translateX(4px);
        }
      `}</style>
    </div>
  );
};