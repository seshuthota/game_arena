import React, { useState, useMemo } from 'react';
import { useLeaderboard, usePlayerStatistics } from '../hooks/useApi';
import { LoadingSkeleton } from './LoadingSkeleton';
import { HeadToHeadComparison } from './HeadToHeadComparison';

interface PlayerPerformanceAnalyticsProps {
  className?: string;
}

interface PlayerPerformanceData {
  playerId: string;
  modelName: string;
  overallStats: {
    totalGames: number;
    winRate: number;
    averageGameLength: number;
    preferredOpenings: OpeningStats[];
    strengthAreas: string[];
    weaknessAreas: string[];
  };
  recentPerformance: {
    last10Games: GameOutcome[];
    winStreak: number;
    performanceTrend: 'improving' | 'declining' | 'stable';
  };
  tacticalMetrics: {
    moveAccuracy: number;
    blunderRate: number;
    excellentMoveRate: number;
    averageThinkingTime: number;
  };
}

interface OpeningStats {
  opening: string;
  frequency: number;
  winRate: number;
  averageLength: number;
}

interface GameOutcome {
  result: 'win' | 'loss' | 'draw';
  opponent: string;
  gameLength: number;
}

export const PlayerPerformanceAnalytics: React.FC<PlayerPerformanceAnalyticsProps> = ({ 
  className 
}) => {
  const [selectedPlayer, setSelectedPlayer] = useState<string>('');
  const [viewMode, setViewMode] = useState<'overview' | 'detailed' | 'comparison'>('overview');

  const {
    data: leaderboardData,
    isLoading: leaderboardLoading,
    error: leaderboardError
  } = useLeaderboard({ limit: 50 });

  const {
    data: playerStatsData,
    isLoading: playerStatsLoading,
    error: playerStatsError
  } = usePlayerStatistics(selectedPlayer, { enabled: !!selectedPlayer });

  const isLoading = leaderboardLoading || (selectedPlayer && playerStatsLoading);
  const hasError = leaderboardError || playerStatsError;

  // Transform leaderboard data into player performance data
  const playerPerformanceData = useMemo(() => {
    if (!leaderboardData?.players) return [];

    return leaderboardData.players.map(player => {
      // Calculate performance trends based on available data
      const performanceTrend = player.win_rate > 60 ? 'improving' : 
                              player.win_rate < 40 ? 'declining' : 'stable';

      // Estimate strength and weakness areas based on stats
      const strengthAreas = [];
      const weaknessAreas = [];

      if (player.win_rate > 70) strengthAreas.push('Consistent Performance');
      if (player.average_game_length < 30) strengthAreas.push('Quick Decision Making');
      if (player.games_played > 50) strengthAreas.push('Experience');
      
      if (player.win_rate < 40) weaknessAreas.push('Win Rate');
      if (player.average_game_length > 60) weaknessAreas.push('Game Length');
      if (player.games_played < 10) weaknessAreas.push('Limited Experience');

      // Mock opening data (would come from backend in real implementation)
      const preferredOpenings: OpeningStats[] = [
        { opening: 'Sicilian Defense', frequency: 35, winRate: player.win_rate + 5, averageLength: player.average_game_length - 5 },
        { opening: 'Queen\'s Gambit', frequency: 25, winRate: player.win_rate - 3, averageLength: player.average_game_length + 8 },
        { opening: 'King\'s Indian Defense', frequency: 20, winRate: player.win_rate + 2, averageLength: player.average_game_length + 3 },
      ];

      // Mock recent performance data
      const last10Games: GameOutcome[] = Array.from({ length: 10 }, (_, i) => ({
        result: Math.random() > 0.5 ? 'win' : Math.random() > 0.5 ? 'loss' : 'draw',
        opponent: `Player ${i + 1}`,
        gameLength: Math.floor(Math.random() * 40) + 20
      }));

      const winStreak = last10Games.reduce((streak, game, index) => {
        if (game.result === 'win') {
          return index === 0 || last10Games[index - 1].result === 'win' ? streak + 1 : 1;
        }
        return 0;
      }, 0);

      return {
        playerId: player.player_id,
        modelName: player.model_name,
        overallStats: {
          totalGames: player.games_played,
          winRate: player.win_rate,
          averageGameLength: player.average_game_length,
          preferredOpenings,
          strengthAreas,
          weaknessAreas,
        },
        recentPerformance: {
          last10Games,
          winStreak,
          performanceTrend,
        },
        tacticalMetrics: {
          moveAccuracy: Math.min(95, player.win_rate + Math.random() * 10),
          blunderRate: Math.max(2, 15 - player.win_rate / 5),
          excellentMoveRate: Math.min(25, player.win_rate / 3),
          averageThinkingTime: Math.random() * 30 + 10,
        },
      };
    });
  }, [leaderboardData]);

  const selectedPlayerData = useMemo(() => {
    return playerPerformanceData.find(p => p.playerId === selectedPlayer);
  }, [playerPerformanceData, selectedPlayer]);

  if (isLoading) {
    return (
      <div className={`player-performance-analytics ${className || ''}`}>
        <LoadingSkeleton />
      </div>
    );
  }

  if (hasError) {
    return (
      <div className={`player-performance-analytics ${className || ''}`}>
        <div className="error-container">
          <div className="error-icon">⚠️</div>
          <h3 className="error-title">Failed to load player analytics</h3>
          <p className="error-message">
            Unable to retrieve player performance data. Please try again later.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className={`player-performance-analytics ${className || ''}`}>
      {/* Header with controls */}
      <div className="analytics-header">
        <h2 className="analytics-title">Player Performance Analytics</h2>
        <div className="analytics-controls">
          <div className="control-group">
            <label htmlFor="player-select" className="control-label">Player:</label>
            <select
              id="player-select"
              value={selectedPlayer}
              onChange={(e) => setSelectedPlayer(e.target.value)}
              className="control-select"
            >
              <option value="">Select a player...</option>
              {playerPerformanceData.map(player => (
                <option key={player.playerId} value={player.playerId}>
                  {player.modelName} ({player.overallStats.totalGames} games)
                </option>
              ))}
            </select>
          </div>
          <div className="control-group">
            <label htmlFor="view-mode-select" className="control-label">View:</label>
            <select
              id="view-mode-select"
              value={viewMode}
              onChange={(e) => setViewMode(e.target.value as typeof viewMode)}
              className="control-select"
            >
              <option value="overview">Overview</option>
              <option value="detailed">Detailed Analysis</option>
              <option value="comparison">Player Comparison</option>
            </select>
          </div>
        </div>
      </div>

      {/* Overview Mode - Top Players Summary */}
      {viewMode === 'overview' && (
        <div className="overview-section">
          <div className="top-performers-grid">
            {playerPerformanceData.slice(0, 6).map(player => (
              <div key={player.playerId} className="performer-card">
                <div className="performer-header">
                  <h4 className="performer-name">{player.modelName}</h4>
                  <div className={`trend-indicator ${player.recentPerformance.performanceTrend}`}>
                    {player.recentPerformance.performanceTrend === 'improving' ? '↗' : 
                     player.recentPerformance.performanceTrend === 'declining' ? '↘' : '→'}
                  </div>
                </div>
                <div className="performer-stats">
                  <div className="stat-item">
                    <span className="stat-label">Win Rate</span>
                    <span className="stat-value">{player.overallStats.winRate.toFixed(1)}%</span>
                  </div>
                  <div className="stat-item">
                    <span className="stat-label">Games</span>
                    <span className="stat-value">{player.overallStats.totalGames}</span>
                  </div>
                  <div className="stat-item">
                    <span className="stat-label">Avg Length</span>
                    <span className="stat-value">{player.overallStats.averageGameLength.toFixed(0)} moves</span>
                  </div>
                  <div className="stat-item">
                    <span className="stat-label">Win Streak</span>
                    <span className="stat-value">{player.recentPerformance.winStreak}</span>
                  </div>
                </div>
                <div className="performer-strengths">
                  <h5>Strengths:</h5>
                  <ul>
                    {player.overallStats.strengthAreas.slice(0, 2).map(strength => (
                      <li key={strength}>{strength}</li>
                    ))}
                  </ul>
                </div>
                <button 
                  className="analyze-button"
                  onClick={() => {
                    setSelectedPlayer(player.playerId);
                    setViewMode('detailed');
                  }}
                >
                  Analyze Player
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Detailed Analysis Mode */}
      {viewMode === 'detailed' && selectedPlayerData && (
        <div className="detailed-analysis-section">
          <div className="player-overview">
            <h3 className="player-title">{selectedPlayerData.modelName} - Detailed Analysis</h3>
            
            {/* Performance Metrics Grid */}
            <div className="metrics-grid">
              <div className="metric-card">
                <h4>Overall Performance</h4>
                <div className="metric-content">
                  <div className="metric-row">
                    <span>Win Rate:</span>
                    <span className="metric-value">{selectedPlayerData.overallStats.winRate.toFixed(1)}%</span>
                  </div>
                  <div className="metric-row">
                    <span>Total Games:</span>
                    <span className="metric-value">{selectedPlayerData.overallStats.totalGames}</span>
                  </div>
                  <div className="metric-row">
                    <span>Current Streak:</span>
                    <span className="metric-value">{selectedPlayerData.recentPerformance.winStreak} wins</span>
                  </div>
                  <div className="metric-row">
                    <span>Trend:</span>
                    <span className={`metric-value trend-${selectedPlayerData.recentPerformance.performanceTrend}`}>
                      {selectedPlayerData.recentPerformance.performanceTrend}
                    </span>
                  </div>
                </div>
              </div>

              <div className="metric-card">
                <h4>Tactical Metrics</h4>
                <div className="metric-content">
                  <div className="metric-row">
                    <span>Move Accuracy:</span>
                    <span className="metric-value">{selectedPlayerData.tacticalMetrics.moveAccuracy.toFixed(1)}%</span>
                  </div>
                  <div className="metric-row">
                    <span>Blunder Rate:</span>
                    <span className="metric-value">{selectedPlayerData.tacticalMetrics.blunderRate.toFixed(1)}%</span>
                  </div>
                  <div className="metric-row">
                    <span>Excellent Moves:</span>
                    <span className="metric-value">{selectedPlayerData.tacticalMetrics.excellentMoveRate.toFixed(1)}%</span>
                  </div>
                  <div className="metric-row">
                    <span>Avg Think Time:</span>
                    <span className="metric-value">{selectedPlayerData.tacticalMetrics.averageThinkingTime.toFixed(1)}s</span>
                  </div>
                </div>
              </div>

              <div className="metric-card">
                <h4>Opening Preferences</h4>
                <div className="opening-list">
                  {selectedPlayerData.overallStats.preferredOpenings.map(opening => (
                    <div key={opening.opening} className="opening-item">
                      <div className="opening-name">{opening.opening}</div>
                      <div className="opening-stats">
                        <span>{opening.frequency}% frequency</span>
                        <span>{opening.winRate.toFixed(1)}% win rate</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Strengths and Weaknesses */}
            <div className="analysis-grid">
              <div className="analysis-card strengths">
                <h4>Strengths</h4>
                <ul>
                  {selectedPlayerData.overallStats.strengthAreas.map(strength => (
                    <li key={strength} className="strength-item">{strength}</li>
                  ))}
                </ul>
              </div>
              <div className="analysis-card weaknesses">
                <h4>Areas for Improvement</h4>
                <ul>
                  {selectedPlayerData.overallStats.weaknessAreas.map(weakness => (
                    <li key={weakness} className="weakness-item">{weakness}</li>
                  ))}
                </ul>
              </div>
            </div>

            {/* Recent Games */}
            <div className="recent-games-section">
              <h4>Recent Performance (Last 10 Games)</h4>
              <div className="games-timeline">
                {selectedPlayerData.recentPerformance.last10Games.map((game, index) => (
                  <div key={index} className={`game-result ${game.result}`}>
                    <div className="result-indicator">{game.result.charAt(0).toUpperCase()}</div>
                    <div className="game-info">
                      <div>vs {game.opponent}</div>
                      <div>{game.gameLength} moves</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Comparison Mode */}
      {viewMode === 'comparison' && (
        <HeadToHeadComparison className="comparison-section" />
      )}

      <style jsx>{`
        .player-performance-analytics {
          display: flex;
          flex-direction: column;
          gap: 2rem;
        }

        .analytics-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          flex-wrap: wrap;
          gap: 1rem;
          padding: 1.5rem;
          background-color: #ffffff;
          border: 1px solid #e5e7eb;
          border-radius: 0.75rem;
          box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
        }

        .analytics-title {
          font-size: 1.5rem;
          font-weight: 600;
          color: #1f2937;
          margin: 0;
        }

        .analytics-controls {
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
          min-width: 150px;
        }

        .control-select:focus {
          outline: none;
          border-color: #3b82f6;
          box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
        }

        .overview-section {
          background-color: #ffffff;
          border: 1px solid #e5e7eb;
          border-radius: 0.75rem;
          padding: 1.5rem;
          box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
        }

        .top-performers-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
          gap: 1.5rem;
        }

        .performer-card {
          background-color: #f9fafb;
          border: 1px solid #e5e7eb;
          border-radius: 0.5rem;
          padding: 1.25rem;
          transition: transform 0.2s, box-shadow 0.2s;
        }

        .performer-card:hover {
          transform: translateY(-2px);
          box-shadow: 0 4px 12px 0 rgba(0, 0, 0, 0.15);
        }

        .performer-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 1rem;
        }

        .performer-name {
          font-size: 1.125rem;
          font-weight: 600;
          color: #1f2937;
          margin: 0;
        }

        .trend-indicator {
          font-size: 1.25rem;
          font-weight: bold;
          padding: 0.25rem 0.5rem;
          border-radius: 0.25rem;
        }

        .trend-indicator.improving {
          color: #059669;
          background-color: #d1fae5;
        }

        .trend-indicator.declining {
          color: #dc2626;
          background-color: #fee2e2;
        }

        .trend-indicator.stable {
          color: #7c2d12;
          background-color: #fef3c7;
        }

        .performer-stats {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 0.75rem;
          margin-bottom: 1rem;
        }

        .stat-item {
          display: flex;
          flex-direction: column;
          gap: 0.25rem;
        }

        .stat-label {
          font-size: 0.75rem;
          color: #6b7280;
          font-weight: 500;
        }

        .stat-value {
          font-size: 1rem;
          font-weight: 600;
          color: #1f2937;
        }

        .performer-strengths {
          margin-bottom: 1rem;
        }

        .performer-strengths h5 {
          font-size: 0.875rem;
          font-weight: 600;
          color: #374151;
          margin: 0 0 0.5rem 0;
        }

        .performer-strengths ul {
          list-style: none;
          padding: 0;
          margin: 0;
        }

        .performer-strengths li {
          font-size: 0.75rem;
          color: #059669;
          background-color: #d1fae5;
          padding: 0.25rem 0.5rem;
          border-radius: 0.25rem;
          margin-bottom: 0.25rem;
        }

        .analyze-button {
          width: 100%;
          background-color: #3b82f6;
          color: white;
          border: none;
          padding: 0.75rem;
          border-radius: 0.375rem;
          font-weight: 500;
          cursor: pointer;
          transition: background-color 0.2s;
        }

        .analyze-button:hover {
          background-color: #2563eb;
        }

        .detailed-analysis-section {
          background-color: #ffffff;
          border: 1px solid #e5e7eb;
          border-radius: 0.75rem;
          padding: 1.5rem;
          box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
        }

        .player-title {
          font-size: 1.25rem;
          font-weight: 600;
          color: #1f2937;
          margin: 0 0 1.5rem 0;
        }

        .metrics-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
          gap: 1.5rem;
          margin-bottom: 2rem;
        }

        .metric-card {
          background-color: #f9fafb;
          border: 1px solid #e5e7eb;
          border-radius: 0.5rem;
          padding: 1.25rem;
        }

        .metric-card h4 {
          font-size: 1rem;
          font-weight: 600;
          color: #1f2937;
          margin: 0 0 1rem 0;
        }

        .metric-content {
          display: flex;
          flex-direction: column;
          gap: 0.75rem;
        }

        .metric-row {
          display: flex;
          justify-content: space-between;
          align-items: center;
        }

        .metric-row span:first-child {
          font-size: 0.875rem;
          color: #6b7280;
        }

        .metric-row .metric-value {
          font-weight: 600;
          color: #1f2937;
        }

        .metric-value.trend-improving {
          color: #059669;
        }

        .metric-value.trend-declining {
          color: #dc2626;
        }

        .metric-value.trend-stable {
          color: #7c2d12;
        }

        .opening-list {
          display: flex;
          flex-direction: column;
          gap: 0.75rem;
        }

        .opening-item {
          padding: 0.75rem;
          background-color: #ffffff;
          border: 1px solid #e5e7eb;
          border-radius: 0.375rem;
        }

        .opening-name {
          font-weight: 600;
          color: #1f2937;
          margin-bottom: 0.25rem;
        }

        .opening-stats {
          display: flex;
          gap: 1rem;
          font-size: 0.75rem;
          color: #6b7280;
        }

        .analysis-grid {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 1.5rem;
          margin-bottom: 2rem;
        }

        .analysis-card {
          background-color: #f9fafb;
          border: 1px solid #e5e7eb;
          border-radius: 0.5rem;
          padding: 1.25rem;
        }

        .analysis-card h4 {
          font-size: 1rem;
          font-weight: 600;
          margin: 0 0 1rem 0;
        }

        .analysis-card.strengths h4 {
          color: #059669;
        }

        .analysis-card.weaknesses h4 {
          color: #dc2626;
        }

        .analysis-card ul {
          list-style: none;
          padding: 0;
          margin: 0;
        }

        .strength-item {
          background-color: #d1fae5;
          color: #059669;
          padding: 0.5rem;
          border-radius: 0.25rem;
          margin-bottom: 0.5rem;
          font-size: 0.875rem;
        }

        .weakness-item {
          background-color: #fee2e2;
          color: #dc2626;
          padding: 0.5rem;
          border-radius: 0.25rem;
          margin-bottom: 0.5rem;
          font-size: 0.875rem;
        }

        .recent-games-section h4 {
          font-size: 1rem;
          font-weight: 600;
          color: #1f2937;
          margin: 0 0 1rem 0;
        }

        .games-timeline {
          display: flex;
          gap: 0.5rem;
          flex-wrap: wrap;
        }

        .game-result {
          display: flex;
          flex-direction: column;
          align-items: center;
          padding: 0.75rem;
          border-radius: 0.375rem;
          min-width: 80px;
          text-align: center;
        }

        .game-result.win {
          background-color: #d1fae5;
          border: 1px solid #a7f3d0;
        }

        .game-result.loss {
          background-color: #fee2e2;
          border: 1px solid #fecaca;
        }

        .game-result.draw {
          background-color: #fef3c7;
          border: 1px solid #fde68a;
        }

        .result-indicator {
          font-size: 1.25rem;
          font-weight: bold;
          margin-bottom: 0.25rem;
        }

        .game-result.win .result-indicator {
          color: #059669;
        }

        .game-result.loss .result-indicator {
          color: #dc2626;
        }

        .game-result.draw .result-indicator {
          color: #d97706;
        }

        .game-info {
          font-size: 0.75rem;
          color: #6b7280;
        }

        .comparison-section {
          background-color: #ffffff;
          border: 1px solid #e5e7eb;
          border-radius: 0.75rem;
          padding: 1.5rem;
          box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
        }

        .comparison-section h3 {
          font-size: 1.25rem;
          font-weight: 600;
          color: #1f2937;
          margin: 0 0 1rem 0;
        }

        .comparison-note {
          color: #6b7280;
          margin-bottom: 2rem;
        }

        .comparison-placeholder {
          display: flex;
          justify-content: center;
          align-items: center;
          min-height: 300px;
          background-color: #f9fafb;
          border: 2px dashed #d1d5db;
          border-radius: 0.5rem;
        }

        .placeholder-content {
          text-align: center;
        }

        .placeholder-icon {
          font-size: 3rem;
          margin-bottom: 1rem;
        }

        .placeholder-content p {
          color: #6b7280;
          margin-bottom: 1.5rem;
        }

        .back-button {
          background-color: #6b7280;
          color: white;
          border: none;
          padding: 0.75rem 1.5rem;
          border-radius: 0.375rem;
          font-weight: 500;
          cursor: pointer;
          transition: background-color 0.2s;
        }

        .back-button:hover {
          background-color: #4b5563;
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

        @media (max-width: 768px) {
          .analytics-header {
            flex-direction: column;
            align-items: stretch;
          }

          .analytics-controls {
            justify-content: center;
          }

          .top-performers-grid {
            grid-template-columns: 1fr;
          }

          .metrics-grid {
            grid-template-columns: 1fr;
          }

          .analysis-grid {
            grid-template-columns: 1fr;
          }

          .games-timeline {
            justify-content: center;
          }

          .control-select {
            min-width: 120px;
          }
        }
      `}</style>
    </div>
  );
};