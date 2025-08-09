import React, { useState, memo, useCallback, useMemo } from 'react';
import {
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { useStatisticsOverview } from '../hooks/useApi';
import { StatisticsSkeleton } from './LoadingSkeleton';
import { StatisticsErrorBoundary, ChartErrorBoundary } from './ErrorBoundary';
import { PlayerPerformanceAnalytics } from './PlayerPerformanceAnalytics';

interface StatisticsDashboardProps {
  className?: string;
  autoRefresh?: boolean;
  refreshInterval?: number;
}

export const StatisticsDashboard: React.FC<StatisticsDashboardProps> = ({ 
  className, 
  autoRefresh = false, 
  refreshInterval = 5 * 60 * 1000 // 5 minutes
}) => {
  const {
    data: statisticsData,
    isLoading: statsLoading,
    error: statsError,
    refetch: refetchStats
  } = useStatisticsOverview() as { data: any, isLoading: boolean, error: unknown, refetch: () => void };

  const isLoading = statsLoading;
  const hasError = statsError;

  const statistics = statisticsData?.statistics;





  // Loading state
  if (isLoading) {
    return (
      <div className={`statistics-dashboard ${className || ''}`}>
        <StatisticsSkeleton />
      </div>
    );
  }

  // Error state
  if (hasError) {
    return (
      <div className={`statistics-dashboard ${className || ''}`}>
        <div className="error-container">
          <div className="error-icon">⚠️</div>
          <h3 className="error-title">Failed to load statistics</h3>
          <p className="error-message">
            {statsError instanceof Error ? statsError.message : 'An unexpected error occurred'}
          </p>
          <button onClick={() => refetchStats()} className="retry-button">
            Try Again
          </button>
        </div>
        <style jsx>{`
          .statistics-dashboard {
            padding: 2rem 0;
          }

          .error-container {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 4rem 2rem;
            text-align: center;
            background-color: #fef2f2;
            border: 1px solid #fecaca;
            border-radius: 0.75rem;
          }

          .error-icon {
            font-size: 3rem;
            margin-bottom: 1rem;
          }

          .error-title {
            font-size: 1.5rem;
            font-weight: 600;
            color: #dc2626;
            margin-bottom: 0.5rem;
          }

          .error-message {
            color: #7f1d1d;
            margin-bottom: 2rem;
            max-width: 500px;
            line-height: 1.5;
          }

          .retry-button {
            background-color: #dc2626;
            color: white;
            border: none;
            padding: 0.75rem 1.5rem;
            border-radius: 0.5rem;
            font-weight: 500;
            cursor: pointer;
            transition: background-color 0.2s;
          }

          .retry-button:hover {
            background-color: #b91c1c;
          }
        `}</style>
      </div>
    );
  }

  // Prepare data for charts
  const gameResultsData = statistics ? [
    { name: 'White Wins', value: statistics.games_by_result.white_wins || 0, color: '#22c55e' },
    { name: 'Black Wins', value: statistics.games_by_result.black_wins || 0, color: '#374151' },
    { name: 'Draws', value: statistics.games_by_result.draw || 0, color: '#f59e0b' }
  ] : [];

  const terminationData = statistics ? Object.entries(statistics.games_by_termination).map(([key, value]) => ({
    name: key.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' '),
    value: value,
    color: getTerminationColor(key)
  })) : [];

  function getTerminationColor(termination: string): string {
    switch (termination) {
      case 'checkmate': return '#dc2626';
      case 'resignation': return '#f59e0b';
      case 'time_forfeit': return '#7c3aed';
      case 'stalemate': return '#6b7280';
      case 'draw_agreement': return '#059669';
      default: return '#3b82f6';
    }
  }

  return (
    <StatisticsErrorBoundary>
      <div className={`statistics-dashboard ${className || ''}`}>
        {/* Overview Cards */}
        <div className="metrics-grid">
        <MetricCard
          title="Total Games"
          value={statistics?.total_games || 0}
          subtitle={`${statistics?.completed_games || 0} completed`}
          icon="🎮"
          trend={{ value: 12, isPositive: true }}
        />
        <MetricCard
          title="Active Players"
          value={statistics?.total_players || 0}
          subtitle="Unique players"
          icon="👥"
          trend={{ value: 5, isPositive: true }}
        />
        <MetricCard
          title="Avg Game Duration"
          value={`${Math.round(statistics?.average_game_duration || 0)}m`}
          subtitle="Per completed game"
          icon="⏱️"
          trend={{ value: 8, isPositive: false }}
        />
        <MetricCard
          title="Avg Moves/Game"
          value={Math.round(statistics?.average_moves_per_game || 0)}
          subtitle="Per completed game"
          icon="♟️"
          trend={{ value: 3, isPositive: true }}
        />
      </div>

      {/* Player Performance Analytics Section */}
      <PlayerPerformanceAnalytics className="player-analytics-section" />

      {/* Charts Grid */}
      <div className="charts-grid">
        {/* Game Results Pie Chart */}
        <div className="chart-card">
          <h4 className="chart-card-title">Game Results</h4>
          <div className="pie-chart-container">
            <ChartErrorBoundary>
              <ResponsiveContainer width="100%" height={250}>
              <PieChart>
                <Pie
                  data={gameResultsData}
                  cx="50%"
                  cy="50%"
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                  label={({ name, percent }) => `${name} ${percent ? (percent * 100).toFixed(0) : 0}%`}
                  labelLine={false}
                >
                  {gameResultsData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
              </ResponsiveContainer>
            </ChartErrorBoundary>
          </div>
        </div>

        {/* Termination Types Bar Chart */}
        <div className="chart-card">
          <h4 className="chart-card-title">Game Endings</h4>
          <div className="bar-chart-container">
            <ChartErrorBoundary>
              <ResponsiveContainer width="100%" height={250}>
              <BarChart data={terminationData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis 
                  dataKey="name" 
                  stroke="#6b7280"
                  fontSize={11}
                  angle={-45}
                  textAnchor="end"
                  height={80}
                />
                <YAxis stroke="#6b7280" fontSize={12} />
                <Tooltip 
                  contentStyle={{
                    backgroundColor: '#ffffff',
                    border: '1px solid #e5e7eb',
                    borderRadius: '0.5rem',
                    fontSize: '0.875rem'
                  }}
                />
                <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                  {terminationData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Bar>
              </BarChart>
              </ResponsiveContainer>
            </ChartErrorBoundary>
          </div>
        </div>
      </div>

      <style jsx>{`
        .statistics-dashboard {
          display: flex;
          flex-direction: column;
          gap: 2rem;
        }

        .metrics-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
          gap: 1.5rem;
        }

        .chart-section {
          background-color: #ffffff;
          border: 1px solid #e5e7eb;
          border-radius: 0.75rem;
          padding: 1.5rem;
          box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
        }

        .chart-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 1.5rem;
          flex-wrap: wrap;
          gap: 1rem;
        }

        .chart-title {
          font-size: 1.25rem;
          font-weight: 600;
          color: #1f2937;
          margin: 0;
        }

        .chart-controls {
          display: flex;
          gap: 1rem;
          align-items: center;
          flex-wrap: wrap;
        }

        .control-group {
          display: flex;
          align-items: center;
          gap: 0.5rem;
        }

        .control-label {
          font-size: 0.875rem;
          font-weight: 500;
          color: #374151;
        }

        .control-select {
          padding: 0.5rem;
          border: 1px solid #d1d5db;
          border-radius: 0.375rem;
          background-color: #ffffff;
          font-size: 0.875rem;
          cursor: pointer;
          min-width: 120px;
        }

        .control-select:focus {
          outline: none;
          border-color: #3b82f6;
          box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
        }

        .checkbox-label {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          font-size: 0.875rem;
          font-weight: 500;
          color: #374151;
          cursor: pointer;
        }

        .checkbox-input {
          width: 1rem;
          height: 1rem;
          border-radius: 0.25rem;
          border: 1px solid #d1d5db;
          cursor: pointer;
        }

        .checkbox-input:checked {
          background-color: #3b82f6;
          border-color: #3b82f6;
        }

        .checkbox-input:focus {
          outline: none;
          box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
        }

        .chart-container {
          margin-top: 1rem;
        }

        .performance-metrics {
          display: flex;
          justify-content: space-around;
          align-items: center;
          margin-top: 1.5rem;
          padding: 1rem;
          background-color: #f9fafb;
          border-radius: 0.5rem;
          border: 1px solid #e5e7eb;
        }

        .metric-item {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 0.25rem;
        }

        .metric-label {
          font-size: 0.75rem;
          color: #6b7280;
          font-weight: 500;
        }

        .metric-value {
          font-size: 1rem;
          font-weight: 600;
          color: #1f2937;
        }

        .charts-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
          gap: 2rem;
        }

        .chart-card {
          background-color: #ffffff;
          border: 1px solid #e5e7eb;
          border-radius: 0.75rem;
          padding: 1.5rem;
          box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
        }

        .chart-card-title {
          font-size: 1.125rem;
          font-weight: 600;
          color: #1f2937;
          margin: 0 0 1rem 0;
          text-align: center;
        }

        .pie-chart-container,
        .bar-chart-container {
          margin-top: 1rem;
        }

        @media (max-width: 768px) {
          .metrics-grid {
            grid-template-columns: 1fr;
          }

          .chart-header {
            flex-direction: column;
            align-items: stretch;
          }

          .chart-controls {
            justify-content: center;
            flex-wrap: wrap;
          }

          .charts-grid {
            grid-template-columns: 1fr;
          }

          .control-select {
            min-width: 100px;
          }

          .performance-metrics {
            flex-wrap: wrap;
            gap: 1rem;
          }

          .metric-item {
            min-width: 80px;
          }
        }
      `}</style>
      </div>
    </StatisticsErrorBoundary>
  );
};

// Metric Card Component
interface MetricCardProps {
  title: string;
  value: number | string;
  subtitle?: string;
  icon?: string;
  trend?: {
    value: number;
    isPositive: boolean;
  };
}

const MetricCard: React.FC<MetricCardProps> = memo(({ title, value, subtitle, icon, trend }) => {
  return (
    <div className="metric-card">
      <div className="metric-header">
        <div className="metric-icon">{icon}</div>
        {trend && (
          <div className={`metric-trend ${trend.isPositive ? 'positive' : 'negative'}`}>
            <span className="trend-icon">{trend.isPositive ? '↗' : '↘'}</span>
            <span className="trend-value">{trend.value}%</span>
          </div>
        )}
      </div>
      <div className="metric-content">
        <div className="metric-value">{value}</div>
        <div className="metric-title">{title}</div>
        {subtitle && <div className="metric-subtitle">{subtitle}</div>}
      </div>

      <style jsx>{`
        .metric-card {
          background-color: #ffffff;
          border: 1px solid #e5e7eb;
          border-radius: 0.75rem;
          padding: 1.5rem;
          box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
          transition: transform 0.2s, box-shadow 0.2s;
        }

        .metric-card:hover {
          transform: translateY(-2px);
          box-shadow: 0 4px 12px 0 rgba(0, 0, 0, 0.15);
        }

        .metric-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 1rem;
        }

        .metric-icon {
          font-size: 2rem;
          opacity: 0.8;
        }

        .metric-trend {
          display: flex;
          align-items: center;
          gap: 0.25rem;
          padding: 0.25rem 0.5rem;
          border-radius: 0.375rem;
          font-size: 0.75rem;
          font-weight: 600;
        }

        .metric-trend.positive {
          background-color: #dcfce7;
          color: #166534;
        }

        .metric-trend.negative {
          background-color: #fef2f2;
          color: #dc2626;
        }

        .trend-icon {
          font-size: 0.875rem;
        }

        .metric-content {
          text-align: left;
        }

        .metric-value {
          font-size: 2.25rem;
          font-weight: 700;
          color: #1f2937;
          line-height: 1;
          margin-bottom: 0.5rem;
        }

        .metric-title {
          font-size: 1rem;
          font-weight: 600;
          color: #374151;
          margin-bottom: 0.25rem;
        }

        .metric-subtitle {
          font-size: 0.875rem;
          color: #6b7280;
        }
      `}</style>
    </div>
  );
});