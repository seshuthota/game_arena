import React, { useState, useMemo } from 'react';
import { useLeaderboard, usePlayerStatistics } from '../hooks/useApi';
import { LeaderboardResponse, PlayerStatisticsResponse } from '../types/api';
import { LoadingSkeleton } from './LoadingSkeleton';

interface HeadToHeadComparisonProps {
  className?: string;
  initialPlayer1?: string;
  initialPlayer2?: string;
}

interface PlayerSummary {
  playerId: string;
  modelName: string;
  totalGames: number;
  winRate: number;
  averageGameLength: number;
  eloRating: number;
}

interface HeadToHeadStats {
  totalGames: number;
  player1Wins: number;
  player2Wins: number;
  draws: number;
  averageGameLength: number;
}

interface OpeningComparison {
  opening: string;
  player1Frequency: number;
  player2Frequency: number;
  player1WinRate: number;
  player2WinRate: number;
}

interface PhaseStrengthComparison {
  opening: { player1: number; player2: number };
  middlegame: { player1: number; player2: number };
  endgame: { player1: number; player2: number };
}

interface TacticalComparison {
  moveAccuracy: { player1: number; player2: number };
  blunderRate: { player1: number; player2: number };
  averageThinkingTime: { player1: number; player2: number };
}

interface FormComparison {
  last10Games: { player1: number; player2: number };
  winStreak: { player1: number; player2: number };
  recentTrend: { player1: 'improving' | 'declining' | 'stable'; player2: 'improving' | 'declining' | 'stable' };
}

interface PerformanceHistory {
  period: string;
  player1WinRate: number;
  player2WinRate: number;
}

interface HeadToHeadComparison {
  player1: PlayerSummary;
  player2: PlayerSummary;
  matchupStats: HeadToHeadStats;
  playingStyleComparison: {
    openingPreferences: OpeningComparison[];
    gamePhaseStrengths: PhaseStrengthComparison;
    tacticalDifferences: TacticalComparison;
  };
  performanceTrends: {
    recentForm: FormComparison;
    historicalPerformance: PerformanceHistory[];
  };
}

export const HeadToHeadComparison: React.FC<HeadToHeadComparisonProps> = ({ 
  className,
  initialPlayer1,
  initialPlayer2
}) => {
  const [selectedPlayer1, setSelectedPlayer1] = useState<string>(initialPlayer1 || '');
  const [selectedPlayer2, setSelectedPlayer2] = useState<string>(initialPlayer2 || '');
  const [comparisonMode, setComparisonMode] = useState<'overview' | 'detailed' | 'historical'>('overview');

  const {
    data: leaderboardData,
    isLoading: leaderboardLoading,
    error: leaderboardError
  } = useLeaderboard({ limit: 50 });

  const {
    data: player1StatsData,
    isLoading: player1StatsLoading,
    error: player1StatsError
  } = usePlayerStatistics(selectedPlayer1 || '');

  const {
    data: player2StatsData,
    isLoading: player2StatsLoading,
    error: player2StatsError
  } = usePlayerStatistics(selectedPlayer2 || '');

  const isLoading = leaderboardLoading || player1StatsLoading || player2StatsLoading;
  const hasError = leaderboardError || player1StatsError || player2StatsError;

  // Generate head-to-head comparison data
  const comparisonData = useMemo((): HeadToHeadComparison | null => {
    const leaderboard = leaderboardData as LeaderboardResponse;
    if (!leaderboard?.players || !selectedPlayer1 || !selectedPlayer2) return null;

    const player1Data = leaderboard.players.find(p => p.player_id === selectedPlayer1);
    const player2Data = leaderboard.players.find(p => p.player_id === selectedPlayer2);

    if (!player1Data || !player2Data) return null;

    // Create player summaries
    const player1: PlayerSummary = {
      playerId: player1Data.player_id,
      modelName: player1Data.model_name,
      totalGames: player1Data.games_played,
      winRate: player1Data.win_rate,
      averageGameLength: player1Data.average_game_length,
      eloRating: player1Data.elo_rating
    };

    const player2: PlayerSummary = {
      playerId: player2Data.player_id,
      modelName: player2Data.model_name,
      totalGames: player2Data.games_played,
      winRate: player2Data.win_rate,
      averageGameLength: player2Data.average_game_length,
      eloRating: player2Data.elo_rating
    };

    // Mock head-to-head stats (would come from backend in real implementation)
    const totalHeadToHeadGames = Math.min(player1.totalGames, player2.totalGames) / 3;
    const player1Wins = Math.floor(totalHeadToHeadGames * (player1.winRate / 100) * 0.8);
    const player2Wins = Math.floor(totalHeadToHeadGames * (player2.winRate / 100) * 0.8);
    const draws = Math.max(0, totalHeadToHeadGames - player1Wins - player2Wins);

    const matchupStats: HeadToHeadStats = {
      totalGames: Math.floor(totalHeadToHeadGames),
      player1Wins,
      player2Wins,
      draws,
      averageGameLength: (player1.averageGameLength + player2.averageGameLength) / 2
    };

    // Mock opening preferences comparison
    const openingPreferences: OpeningComparison[] = [
      {
        opening: 'Sicilian Defense',
        player1Frequency: 35 + Math.random() * 10,
        player2Frequency: 25 + Math.random() * 10,
        player1WinRate: player1.winRate + Math.random() * 10 - 5,
        player2WinRate: player2.winRate + Math.random() * 10 - 5
      },
      {
        opening: 'Queen\'s Gambit',
        player1Frequency: 25 + Math.random() * 10,
        player2Frequency: 30 + Math.random() * 10,
        player1WinRate: player1.winRate + Math.random() * 10 - 5,
        player2WinRate: player2.winRate + Math.random() * 10 - 5
      },
      {
        opening: 'King\'s Indian Defense',
        player1Frequency: 20 + Math.random() * 10,
        player2Frequency: 15 + Math.random() * 10,
        player1WinRate: player1.winRate + Math.random() * 10 - 5,
        player2WinRate: player2.winRate + Math.random() * 10 - 5
      }
    ];

    // Mock game phase strengths
    const gamePhaseStrengths: PhaseStrengthComparison = {
      opening: {
        player1: 70 + Math.random() * 20,
        player2: 65 + Math.random() * 20
      },
      middlegame: {
        player1: player1.winRate + Math.random() * 15 - 7.5,
        player2: player2.winRate + Math.random() * 15 - 7.5
      },
      endgame: {
        player1: 60 + Math.random() * 25,
        player2: 55 + Math.random() * 25
      }
    };

    // Mock tactical differences
    const tacticalDifferences: TacticalComparison = {
      moveAccuracy: {
        player1: Math.min(98, player1.winRate + 20 + Math.random() * 10),
        player2: Math.min(98, player2.winRate + 20 + Math.random() * 10)
      },
      blunderRate: {
        player1: Math.max(1, 15 - player1.winRate / 5 + Math.random() * 3),
        player2: Math.max(1, 15 - player2.winRate / 5 + Math.random() * 3)
      },
      averageThinkingTime: {
        player1: 15 + Math.random() * 20,
        player2: 15 + Math.random() * 20
      }
    };

    // Mock recent form comparison
    const recentForm: FormComparison = {
      last10Games: {
        player1: Math.floor(player1.winRate / 10),
        player2: Math.floor(player2.winRate / 10)
      },
      winStreak: {
        player1: Math.floor(Math.random() * 5),
        player2: Math.floor(Math.random() * 5)
      },
      recentTrend: {
        player1: player1.winRate > 60 ? 'improving' : player1.winRate < 40 ? 'declining' : 'stable',
        player2: player2.winRate > 60 ? 'improving' : player2.winRate < 40 ? 'declining' : 'stable'
      }
    };

    // Mock historical performance
    const historicalPerformance: PerformanceHistory[] = [
      { period: 'Last 30 days', player1WinRate: player1.winRate + Math.random() * 10 - 5, player2WinRate: player2.winRate + Math.random() * 10 - 5 },
      { period: 'Last 90 days', player1WinRate: player1.winRate + Math.random() * 15 - 7.5, player2WinRate: player2.winRate + Math.random() * 15 - 7.5 },
      { period: 'Last 6 months', player1WinRate: player1.winRate + Math.random() * 20 - 10, player2WinRate: player2.winRate + Math.random() * 20 - 10 }
    ];

    return {
      player1,
      player2,
      matchupStats,
      playingStyleComparison: {
        openingPreferences,
        gamePhaseStrengths,
        tacticalDifferences
      },
      performanceTrends: {
        recentForm,
        historicalPerformance
      }
    };
  }, [leaderboardData, selectedPlayer1, selectedPlayer2]);

  if (isLoading) {
    return (
      <div className={`head-to-head-comparison ${className || ''}`}>
        <LoadingSkeleton />
      </div>
    );
  }

  if (hasError) {
    return (
      <div className={`head-to-head-comparison ${className || ''}`}>
        <div className="error-container">
          <div className="error-icon">⚠️</div>
          <h3 className="error-title">Failed to load comparison data</h3>
          <p className="error-message">
            Unable to retrieve player comparison data. Please try again later.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className={`head-to-head-comparison ${className || ''}`}>
      {/* Header with player selection */}
      <div className="comparison-header">
        <h2 className="comparison-title">Head-to-Head Player Comparison</h2>
        <div className="player-selectors">
          <div className="player-selector">
            <label htmlFor="player1-select" className="selector-label">Player 1:</label>
            <select
              id="player1-select"
              value={selectedPlayer1}
              onChange={(e) => setSelectedPlayer1(e.target.value)}
              className="player-select"
            >
              <option value="">Select Player 1...</option>
              {(leaderboardData as LeaderboardResponse)?.players?.map(player => (
                <option key={player.player_id} value={player.player_id}>
                  {player.model_name} ({player.games_played} games)
                </option>
              ))}
            </select>
          </div>
          
          <div className="vs-indicator">VS</div>
          
          <div className="player-selector">
            <label htmlFor="player2-select" className="selector-label">Player 2:</label>
            <select
              id="player2-select"
              value={selectedPlayer2}
              onChange={(e) => setSelectedPlayer2(e.target.value)}
              className="player-select"
            >
              <option value="">Select Player 2...</option>
              {(leaderboardData as LeaderboardResponse)?.players?.map(player => (
                <option key={player.player_id} value={player.player_id}>
                  {player.model_name} ({player.games_played} games)
                </option>
              ))}
            </select>
          </div>
        </div>
        
        <div className="comparison-mode-selector">
          <label htmlFor="mode-select" className="mode-label">View Mode:</label>
          <select
            id="mode-select"
            value={comparisonMode}
            onChange={(e) => setComparisonMode(e.target.value as typeof comparisonMode)}
            className="mode-select"
          >
            <option value="overview">Overview</option>
            <option value="detailed">Detailed Analysis</option>
            <option value="historical">Historical Trends</option>
          </select>
        </div>
      </div>

      {/* Comparison Content */}
      {!selectedPlayer1 || !selectedPlayer2 ? (
        <div className="selection-prompt">
          <div className="prompt-content">
            <div className="prompt-icon">🥊</div>
            <h3>Select Two Players to Compare</h3>
            <p>Choose two players from the dropdowns above to see their head-to-head comparison, playing styles, and performance metrics.</p>
          </div>
        </div>
      ) : !comparisonData ? (
        <div className="no-data-message">
          <div className="no-data-content">
            <div className="no-data-icon">📊</div>
            <h3>No Comparison Data Available</h3>
            <p>Unable to generate comparison data for the selected players.</p>
          </div>
        </div>
      ) : (
        <div className="comparison-content">
          {/* Overview Mode */}
          {comparisonMode === 'overview' && (
            <div className="overview-mode">
              {/* Player Summary Cards */}
              <div className="player-summary-cards">
                <div className="player-card player1">
                  <div className="player-header">
                    <h3 className="player-name">{comparisonData.player1.modelName}</h3>
                    <div className="player-elo">ELO: {comparisonData.player1.eloRating.toFixed(0)}</div>
                  </div>
                  <div className="player-stats">
                    <div className="stat-item">
                      <span className="stat-label">Win Rate</span>
                      <span className="stat-value">{comparisonData.player1.winRate.toFixed(1)}%</span>
                    </div>
                    <div className="stat-item">
                      <span className="stat-label">Total Games</span>
                      <span className="stat-value">{comparisonData.player1.totalGames}</span>
                    </div>
                    <div className="stat-item">
                      <span className="stat-label">Avg Game Length</span>
                      <span className="stat-value">{comparisonData.player1.averageGameLength.toFixed(0)} moves</span>
                    </div>
                  </div>
                </div>

                <div className="matchup-summary">
                  <h4>Head-to-Head Record</h4>
                  <div className="h2h-stats">
                    <div className="h2h-stat">
                      <span className="h2h-label">Total Games</span>
                      <span className="h2h-value">{comparisonData.matchupStats.totalGames}</span>
                    </div>
                    <div className="h2h-record">
                      <span className="player1-wins">{comparisonData.matchupStats.player1Wins}W</span>
                      <span className="draws">{comparisonData.matchupStats.draws}D</span>
                      <span className="player2-wins">{comparisonData.matchupStats.player2Wins}W</span>
                    </div>
                    <div className="h2h-stat">
                      <span className="h2h-label">Avg Length</span>
                      <span className="h2h-value">{comparisonData.matchupStats.averageGameLength.toFixed(0)} moves</span>
                    </div>
                  </div>
                </div>

                <div className="player-card player2">
                  <div className="player-header">
                    <h3 className="player-name">{comparisonData.player2.modelName}</h3>
                    <div className="player-elo">ELO: {comparisonData.player2.eloRating.toFixed(0)}</div>
                  </div>
                  <div className="player-stats">
                    <div className="stat-item">
                      <span className="stat-label">Win Rate</span>
                      <span className="stat-value">{comparisonData.player2.winRate.toFixed(1)}%</span>
                    </div>
                    <div className="stat-item">
                      <span className="stat-label">Total Games</span>
                      <span className="stat-value">{comparisonData.player2.totalGames}</span>
                    </div>
                    <div className="stat-item">
                      <span className="stat-label">Avg Game Length</span>
                      <span className="stat-value">{comparisonData.player2.averageGameLength.toFixed(0)} moves</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Quick Comparison Metrics */}
              <div className="quick-metrics">
                <div className="metric-comparison">
                  <h4>Tactical Comparison</h4>
                  <div className="metric-bars">
                    <div className="metric-bar">
                      <span className="metric-name">Move Accuracy</span>
                      <div className="bar-container">
                        <div className="bar player1-bar" style={{ width: `${comparisonData.playingStyleComparison.tacticalDifferences.moveAccuracy.player1}%` }}>
                          {comparisonData.playingStyleComparison.tacticalDifferences.moveAccuracy.player1.toFixed(1)}%
                        </div>
                        <div className="bar player2-bar" style={{ width: `${comparisonData.playingStyleComparison.tacticalDifferences.moveAccuracy.player2}%` }}>
                          {comparisonData.playingStyleComparison.tacticalDifferences.moveAccuracy.player2.toFixed(1)}%
                        </div>
                      </div>
                    </div>
                    <div className="metric-bar">
                      <span className="metric-name">Blunder Rate</span>
                      <div className="bar-container">
                        <div className="bar player1-bar inverse" style={{ width: `${Math.min(100, comparisonData.playingStyleComparison.tacticalDifferences.blunderRate.player1 * 5)}%` }}>
                          {comparisonData.playingStyleComparison.tacticalDifferences.blunderRate.player1.toFixed(1)}%
                        </div>
                        <div className="bar player2-bar inverse" style={{ width: `${Math.min(100, comparisonData.playingStyleComparison.tacticalDifferences.blunderRate.player2 * 5)}%` }}>
                          {comparisonData.playingStyleComparison.tacticalDifferences.blunderRate.player2.toFixed(1)}%
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Detailed Mode */}
          {comparisonMode === 'detailed' && (
            <div className="detailed-mode">
              {/* Opening Preferences */}
              <div className="analysis-section">
                <h4>Opening Preferences</h4>
                <div className="opening-comparison-table">
                  <div className="table-header">
                    <span>Opening</span>
                    <span>{comparisonData.player1.modelName}</span>
                    <span>{comparisonData.player2.modelName}</span>
                  </div>
                  {comparisonData.playingStyleComparison.openingPreferences.map(opening => (
                    <div key={opening.opening} className="table-row">
                      <span className="opening-name">{opening.opening}</span>
                      <div className="player-opening-stats">
                        <span className="frequency">{opening.player1Frequency.toFixed(1)}% freq</span>
                        <span className="win-rate">{opening.player1WinRate.toFixed(1)}% win</span>
                      </div>
                      <div className="player-opening-stats">
                        <span className="frequency">{opening.player2Frequency.toFixed(1)}% freq</span>
                        <span className="win-rate">{opening.player2WinRate.toFixed(1)}% win</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Game Phase Strengths */}
              <div className="analysis-section">
                <h4>Game Phase Strengths</h4>
                <div className="phase-comparison">
                  {Object.entries(comparisonData.playingStyleComparison.gamePhaseStrengths).map(([phase, scores]) => (
                    <div key={phase} className="phase-item">
                      <span className="phase-name">{phase.charAt(0).toUpperCase() + phase.slice(1)}</span>
                      <div className="phase-scores">
                        <div className="player-score player1">
                          <span className="score-value">{scores.player1.toFixed(1)}</span>
                          <span className="player-name">{comparisonData.player1.modelName}</span>
                        </div>
                        <div className="player-score player2">
                          <span className="score-value">{scores.player2.toFixed(1)}</span>
                          <span className="player-name">{comparisonData.player2.modelName}</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Tactical Metrics */}
              <div className="analysis-section">
                <h4>Detailed Tactical Analysis</h4>
                <div className="tactical-grid">
                  <div className="tactical-metric">
                    <h5>Move Accuracy</h5>
                    <div className="metric-comparison-detailed">
                      <div className="player-metric player1">
                        <span className="metric-value">{comparisonData.playingStyleComparison.tacticalDifferences.moveAccuracy.player1.toFixed(1)}%</span>
                        <span className="player-name">{comparisonData.player1.modelName}</span>
                      </div>
                      <div className="player-metric player2">
                        <span className="metric-value">{comparisonData.playingStyleComparison.tacticalDifferences.moveAccuracy.player2.toFixed(1)}%</span>
                        <span className="player-name">{comparisonData.player2.modelName}</span>
                      </div>
                    </div>
                  </div>
                  <div className="tactical-metric">
                    <h5>Blunder Rate</h5>
                    <div className="metric-comparison-detailed">
                      <div className="player-metric player1">
                        <span className="metric-value">{comparisonData.playingStyleComparison.tacticalDifferences.blunderRate.player1.toFixed(1)}%</span>
                        <span className="player-name">{comparisonData.player1.modelName}</span>
                      </div>
                      <div className="player-metric player2">
                        <span className="metric-value">{comparisonData.playingStyleComparison.tacticalDifferences.blunderRate.player2.toFixed(1)}%</span>
                        <span className="player-name">{comparisonData.player2.modelName}</span>
                      </div>
                    </div>
                  </div>
                  <div className="tactical-metric">
                    <h5>Avg Thinking Time</h5>
                    <div className="metric-comparison-detailed">
                      <div className="player-metric player1">
                        <span className="metric-value">{comparisonData.playingStyleComparison.tacticalDifferences.averageThinkingTime.player1.toFixed(1)}s</span>
                        <span className="player-name">{comparisonData.player1.modelName}</span>
                      </div>
                      <div className="player-metric player2">
                        <span className="metric-value">{comparisonData.playingStyleComparison.tacticalDifferences.averageThinkingTime.player2.toFixed(1)}s</span>
                        <span className="player-name">{comparisonData.player2.modelName}</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Historical Mode */}
          {comparisonMode === 'historical' && (
            <div className="historical-mode">
              {/* Recent Form */}
              <div className="analysis-section">
                <h4>Recent Form Comparison</h4>
                <div className="form-comparison">
                  <div className="form-metric">
                    <span className="form-label">Last 10 Games Won</span>
                    <div className="form-values">
                      <span className="player1-value">{comparisonData.performanceTrends.recentForm.last10Games.player1}</span>
                      <span className="vs">vs</span>
                      <span className="player2-value">{comparisonData.performanceTrends.recentForm.last10Games.player2}</span>
                    </div>
                  </div>
                  <div className="form-metric">
                    <span className="form-label">Current Win Streak</span>
                    <div className="form-values">
                      <span className="player1-value">{comparisonData.performanceTrends.recentForm.winStreak.player1}</span>
                      <span className="vs">vs</span>
                      <span className="player2-value">{comparisonData.performanceTrends.recentForm.winStreak.player2}</span>
                    </div>
                  </div>
                  <div className="form-metric">
                    <span className="form-label">Recent Trend</span>
                    <div className="form-values">
                      <span className={`trend-value player1 ${comparisonData.performanceTrends.recentForm.recentTrend.player1}`}>
                        {comparisonData.performanceTrends.recentForm.recentTrend.player1}
                      </span>
                      <span className="vs">vs</span>
                      <span className={`trend-value player2 ${comparisonData.performanceTrends.recentForm.recentTrend.player2}`}>
                        {comparisonData.performanceTrends.recentForm.recentTrend.player2}
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Historical Performance */}
              <div className="analysis-section">
                <h4>Historical Performance</h4>
                <div className="historical-table">
                  <div className="table-header">
                    <span>Period</span>
                    <span>{comparisonData.player1.modelName}</span>
                    <span>{comparisonData.player2.modelName}</span>
                    <span>Difference</span>
                  </div>
                  {comparisonData.performanceTrends.historicalPerformance.map(period => {
                    const difference = period.player1WinRate - period.player2WinRate;
                    return (
                      <div key={period.period} className="table-row">
                        <span className="period-name">{period.period}</span>
                        <span className="win-rate player1">{period.player1WinRate.toFixed(1)}%</span>
                        <span className="win-rate player2">{period.player2WinRate.toFixed(1)}%</span>
                        <span className={`difference ${difference > 0 ? 'player1-advantage' : 'player2-advantage'}`}>
                          {difference > 0 ? '+' : ''}{difference.toFixed(1)}%
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      <style jsx>{`
        .head-to-head-comparison {
          display: flex;
          flex-direction: column;
          gap: 2rem;
        }

        .comparison-header {
          background-color: #ffffff;
          border: 1px solid #e5e7eb;
          border-radius: 0.75rem;
          padding: 1.5rem;
          box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
        }

        .comparison-title {
          font-size: 1.5rem;
          font-weight: 600;
          color: #1f2937;
          margin: 0 0 1.5rem 0;
          text-align: center;
        }

        .player-selectors {
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 2rem;
          margin-bottom: 1.5rem;
          flex-wrap: wrap;
        }

        .player-selector {
          display: flex;
          flex-direction: column;
          gap: 0.5rem;
          min-width: 200px;
        }

        .selector-label {
          font-size: 0.875rem;
          font-weight: 500;
          color: #374151;
        }

        .player-select {
          padding: 0.75rem;
          border: 1px solid #d1d5db;
          border-radius: 0.375rem;
          background-color: #ffffff;
          font-size: 0.875rem;
          cursor: pointer;
        }

        .player-select:focus {
          outline: none;
          border-color: #3b82f6;
          box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
        }

        .vs-indicator {
          font-size: 1.5rem;
          font-weight: bold;
          color: #6b7280;
          padding: 0.5rem 1rem;
          background-color: #f3f4f6;
          border-radius: 0.5rem;
          margin-top: 1.5rem;
        }

        .comparison-mode-selector {
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 0.5rem;
        }

        .mode-label {
          font-size: 0.875rem;
          font-weight: 500;
          color: #374151;
        }

        .mode-select {
          padding: 0.5rem;
          border: 1px solid #d1d5db;
          border-radius: 0.375rem;
          background-color: #ffffff;
          font-size: 0.875rem;
          cursor: pointer;
        }

        .mode-select:focus {
          outline: none;
          border-color: #3b82f6;
          box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
        }

        .selection-prompt,
        .no-data-message {
          background-color: #ffffff;
          border: 1px solid #e5e7eb;
          border-radius: 0.75rem;
          padding: 4rem 2rem;
          text-align: center;
          box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
        }

        .prompt-content,
        .no-data-content {
          max-width: 400px;
          margin: 0 auto;
        }

        .prompt-icon,
        .no-data-icon {
          font-size: 3rem;
          margin-bottom: 1rem;
        }

        .prompt-content h3,
        .no-data-content h3 {
          font-size: 1.25rem;
          font-weight: 600;
          color: #1f2937;
          margin: 0 0 0.5rem 0;
        }

        .prompt-content p,
        .no-data-content p {
          color: #6b7280;
          line-height: 1.5;
        }

        .comparison-content {
          background-color: #ffffff;
          border: 1px solid #e5e7eb;
          border-radius: 0.75rem;
          padding: 2rem;
          box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
        }

        .player-summary-cards {
          display: grid;
          grid-template-columns: 1fr auto 1fr;
          gap: 2rem;
          align-items: center;
          margin-bottom: 2rem;
        }

        .player-card {
          background-color: #f9fafb;
          border: 1px solid #e5e7eb;
          border-radius: 0.5rem;
          padding: 1.5rem;
        }

        .player-card.player1 {
          border-left: 4px solid #3b82f6;
        }

        .player-card.player2 {
          border-left: 4px solid #ef4444;
        }

        .player-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 1rem;
        }

        .player-name {
          font-size: 1.125rem;
          font-weight: 600;
          color: #1f2937;
          margin: 0;
        }

        .player-elo {
          font-size: 0.875rem;
          font-weight: 500;
          color: #6b7280;
          background-color: #e5e7eb;
          padding: 0.25rem 0.5rem;
          border-radius: 0.25rem;
        }

        .player-stats {
          display: flex;
          flex-direction: column;
          gap: 0.75rem;
        }

        .stat-item {
          display: flex;
          justify-content: space-between;
          align-items: center;
        }

        .stat-label {
          font-size: 0.875rem;
          color: #6b7280;
        }

        .stat-value {
          font-weight: 600;
          color: #1f2937;
        }

        .matchup-summary {
          background-color: #f3f4f6;
          border: 1px solid #d1d5db;
          border-radius: 0.5rem;
          padding: 1.5rem;
          text-align: center;
          min-width: 200px;
        }

        .matchup-summary h4 {
          font-size: 1rem;
          font-weight: 600;
          color: #1f2937;
          margin: 0 0 1rem 0;
        }

        .h2h-stats {
          display: flex;
          flex-direction: column;
          gap: 0.75rem;
        }

        .h2h-stat {
          display: flex;
          justify-content: space-between;
          align-items: center;
        }

        .h2h-label {
          font-size: 0.875rem;
          color: #6b7280;
        }

        .h2h-value {
          font-weight: 600;
          color: #1f2937;
        }

        .h2h-record {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 0.75rem;
          background-color: #ffffff;
          border-radius: 0.375rem;
          border: 1px solid #e5e7eb;
        }

        .player1-wins {
          color: #3b82f6;
          font-weight: 600;
        }

        .player2-wins {
          color: #ef4444;
          font-weight: 600;
        }

        .draws {
          color: #6b7280;
          font-weight: 600;
        }

        .quick-metrics {
          margin-top: 2rem;
        }

        .metric-comparison h4 {
          font-size: 1rem;
          font-weight: 600;
          color: #1f2937;
          margin: 0 0 1rem 0;
        }

        .metric-bars {
          display: flex;
          flex-direction: column;
          gap: 1rem;
        }

        .metric-bar {
          display: flex;
          flex-direction: column;
          gap: 0.5rem;
        }

        .metric-name {
          font-size: 0.875rem;
          font-weight: 500;
          color: #374151;
        }

        .bar-container {
          display: flex;
          flex-direction: column;
          gap: 0.25rem;
        }

        .bar {
          height: 1.5rem;
          border-radius: 0.25rem;
          display: flex;
          align-items: center;
          justify-content: flex-end;
          padding: 0 0.5rem;
          font-size: 0.75rem;
          font-weight: 600;
          color: white;
          min-width: 60px;
        }

        .player1-bar {
          background-color: #3b82f6;
        }

        .player2-bar {
          background-color: #ef4444;
        }

        .bar.inverse {
          background-color: #f59e0b;
        }

        .analysis-section {
          margin-bottom: 2rem;
        }

        .analysis-section h4 {
          font-size: 1.125rem;
          font-weight: 600;
          color: #1f2937;
          margin: 0 0 1rem 0;
        }

        .opening-comparison-table {
          display: flex;
          flex-direction: column;
          gap: 0.5rem;
        }

        .table-header {
          display: grid;
          grid-template-columns: 2fr 1fr 1fr;
          gap: 1rem;
          padding: 0.75rem;
          background-color: #f9fafb;
          border-radius: 0.375rem;
          font-weight: 600;
          color: #374151;
          font-size: 0.875rem;
        }

        .table-row {
          display: grid;
          grid-template-columns: 2fr 1fr 1fr;
          gap: 1rem;
          padding: 0.75rem;
          background-color: #ffffff;
          border: 1px solid #e5e7eb;
          border-radius: 0.375rem;
          align-items: center;
        }

        .opening-name {
          font-weight: 500;
          color: #1f2937;
        }

        .player-opening-stats {
          display: flex;
          flex-direction: column;
          gap: 0.25rem;
          font-size: 0.75rem;
        }

        .frequency {
          color: #6b7280;
        }

        .win-rate {
          color: #1f2937;
          font-weight: 500;
        }

        .phase-comparison {
          display: flex;
          flex-direction: column;
          gap: 1rem;
        }

        .phase-item {
          display: flex;
          align-items: center;
          gap: 2rem;
          padding: 1rem;
          background-color: #f9fafb;
          border-radius: 0.5rem;
          border: 1px solid #e5e7eb;
        }

        .phase-name {
          font-weight: 600;
          color: #1f2937;
          min-width: 100px;
        }

        .phase-scores {
          display: flex;
          gap: 2rem;
          flex: 1;
        }

        .player-score {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 0.25rem;
        }

        .score-value {
          font-size: 1.25rem;
          font-weight: 600;
        }

        .player-score.player1 .score-value {
          color: #3b82f6;
        }

        .player-score.player2 .score-value {
          color: #ef4444;
        }

        .player-score .player-name {
          font-size: 0.75rem;
          color: #6b7280;
        }

        .tactical-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
          gap: 1.5rem;
        }

        .tactical-metric {
          background-color: #f9fafb;
          border: 1px solid #e5e7eb;
          border-radius: 0.5rem;
          padding: 1.25rem;
        }

        .tactical-metric h5 {
          font-size: 1rem;
          font-weight: 600;
          color: #1f2937;
          margin: 0 0 1rem 0;
        }

        .metric-comparison-detailed {
          display: flex;
          justify-content: space-between;
          align-items: center;
        }

        .player-metric {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 0.25rem;
        }

        .player-metric .metric-value {
          font-size: 1.125rem;
          font-weight: 600;
        }

        .player-metric.player1 .metric-value {
          color: #3b82f6;
        }

        .player-metric.player2 .metric-value {
          color: #ef4444;
        }

        .player-metric .player-name {
          font-size: 0.75rem;
          color: #6b7280;
        }

        .form-comparison {
          display: flex;
          flex-direction: column;
          gap: 1rem;
        }

        .form-metric {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 1rem;
          background-color: #f9fafb;
          border-radius: 0.5rem;
          border: 1px solid #e5e7eb;
        }

        .form-label {
          font-weight: 500;
          color: #1f2937;
        }

        .form-values {
          display: flex;
          align-items: center;
          gap: 1rem;
        }

        .player1-value {
          color: #3b82f6;
          font-weight: 600;
        }

        .player2-value {
          color: #ef4444;
          font-weight: 600;
        }

        .vs {
          color: #6b7280;
          font-size: 0.875rem;
        }

        .trend-value {
          padding: 0.25rem 0.5rem;
          border-radius: 0.25rem;
          font-size: 0.75rem;
          font-weight: 500;
          text-transform: capitalize;
        }

        .trend-value.improving {
          background-color: #d1fae5;
          color: #059669;
        }

        .trend-value.declining {
          background-color: #fee2e2;
          color: #dc2626;
        }

        .trend-value.stable {
          background-color: #fef3c7;
          color: #d97706;
        }

        .historical-table {
          display: flex;
          flex-direction: column;
          gap: 0.5rem;
        }

        .historical-table .table-header {
          grid-template-columns: 1fr 1fr 1fr 1fr;
        }

        .historical-table .table-row {
          grid-template-columns: 1fr 1fr 1fr 1fr;
        }

        .period-name {
          font-weight: 500;
          color: #1f2937;
        }

        .win-rate.player1 {
          color: #3b82f6;
          font-weight: 600;
        }

        .win-rate.player2 {
          color: #ef4444;
          font-weight: 600;
        }

        .difference {
          font-weight: 600;
        }

        .difference.player1-advantage {
          color: #059669;
        }

        .difference.player2-advantage {
          color: #dc2626;
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
          .player-selectors {
            flex-direction: column;
            gap: 1rem;
          }

          .vs-indicator {
            margin-top: 0;
          }

          .player-summary-cards {
            grid-template-columns: 1fr;
            gap: 1rem;
          }

          .matchup-summary {
            order: -1;
          }

          .phase-item {
            flex-direction: column;
            gap: 1rem;
            text-align: center;
          }

          .phase-scores {
            justify-content: center;
          }

          .tactical-grid {
            grid-template-columns: 1fr;
          }

          .form-metric {
            flex-direction: column;
            gap: 0.5rem;
            text-align: center;
          }

          .table-header,
          .table-row {
            grid-template-columns: 1fr;
            gap: 0.5rem;
          }

          .historical-table .table-header,
          .historical-table .table-row {
            grid-template-columns: 1fr;
          }
        }
      `}</style>
    </div>
  );
};