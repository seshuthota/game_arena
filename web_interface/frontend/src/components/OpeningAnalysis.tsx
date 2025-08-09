import React, { memo, useMemo } from 'react';
import { 
  identifyOpening, 
  identifyGamePhase, 
  identifyKeyMoments,
  GamePhase,
  OpeningInfo,
  KeyMoment
} from '../utils/openingDatabase';

interface OpeningAnalysisProps {
  moves: string[];
  currentMoveNumber: number;
  totalMoves: number;
  materialCount?: number;
  evaluations?: number[];
  className?: string;
}

export const OpeningAnalysis: React.FC<OpeningAnalysisProps> = memo(({
  moves,
  currentMoveNumber,
  totalMoves,
  materialCount,
  evaluations,
  className = ''
}) => {
  const analysisData = useMemo(() => {
    const opening = identifyOpening(moves);
    const currentPhase = identifyGamePhase(currentMoveNumber, totalMoves, materialCount);
    const keyMoments = identifyKeyMoments(moves, evaluations);
    
    // Determine phase transitions
    const phases = [];
    if (totalMoves > 0) {
      phases.push({
        phase: GamePhase.OPENING,
        moveRange: { start: 1, end: Math.min(15, totalMoves) },
        description: 'Opening development and initial positioning'
      });
      
      if (totalMoves > 15) {
        const middlegameEnd = totalMoves > 40 ? Math.floor(totalMoves * 0.7) : totalMoves;
        phases.push({
          phase: GamePhase.MIDDLEGAME,
          moveRange: { start: 16, end: middlegameEnd },
          description: 'Strategic maneuvering and tactical complications'
        });
        
        if (middlegameEnd < totalMoves) {
          phases.push({
            phase: GamePhase.ENDGAME,
            moveRange: { start: middlegameEnd + 1, end: totalMoves },
            description: 'Simplified position with focus on technique'
          });
        }
      }
    }

    return {
      opening,
      currentPhase,
      phases,
      keyMoments: (keyMoments || []).slice(0, 5) // Show top 5 key moments
    };
  }, [moves, currentMoveNumber, totalMoves, materialCount, evaluations]);

  const getPhaseColor = (phase: GamePhase) => {
    switch (phase) {
      case GamePhase.OPENING: return '#3b82f6';
      case GamePhase.MIDDLEGAME: return '#059669';
      case GamePhase.ENDGAME: return '#dc2626';
      default: return '#6b7280';
    }
  };

  const getPhaseIcon = (phase: GamePhase) => {
    switch (phase) {
      case GamePhase.OPENING: return '🏁';
      case GamePhase.MIDDLEGAME: return '⚔️';
      case GamePhase.ENDGAME: return '👑';
      default: return '♟️';
    }
  };

  const getKeyMomentIcon = (type: KeyMoment['type']) => {
    switch (type) {
      case 'brilliant': return '💎';
      case 'blunder': return '💥';
      case 'tactical_shot': return '🎯';
      case 'endgame_technique': return '🔧';
      case 'opening_novelty': return '✨';
      default: return '📍';
    }
  };

  const getKeyMomentColor = (type: KeyMoment['type']) => {
    switch (type) {
      case 'brilliant': return '#059669';
      case 'blunder': return '#dc2626';
      case 'tactical_shot': return '#d97706';
      case 'endgame_technique': return '#3b82f6';
      case 'opening_novelty': return '#7c3aed';
      default: return '#6b7280';
    }
  };

  return (
    <div className={`opening-analysis ${className}`}>
      <div className="analysis-header">
        <h3 className="analysis-title">Opening & Game Analysis</h3>
      </div>

      {/* Opening Information */}
      {analysisData.opening && (
        <div className="analysis-section">
          <h4 className="section-title">Opening</h4>
          <div className="opening-info">
            <div className="opening-header">
              <span className="eco-code">{analysisData.opening.eco}</span>
              <span className="opening-name">{analysisData.opening.name}</span>
            </div>
            <div className="opening-moves">
              <span className="moves-label">Main line:</span>
              <span className="moves-sequence">
                {analysisData.opening.moves.join(' ')}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Current Game Phase */}
      <div className="analysis-section">
        <h4 className="section-title">Current Phase</h4>
        <div className="current-phase">
          <div 
            className="phase-indicator"
            style={{ backgroundColor: getPhaseColor(analysisData.currentPhase) }}
          >
            <span className="phase-icon">{getPhaseIcon(analysisData.currentPhase)}</span>
            <span className="phase-name">
              {analysisData.currentPhase ? analysisData.currentPhase.charAt(0).toUpperCase() + analysisData.currentPhase.slice(1) : 'Unknown'}
            </span>
          </div>
          <div className="phase-description">
            Move {currentMoveNumber} of {totalMoves || '?'}
          </div>
        </div>
      </div>

      {/* Game Phases Timeline */}
      {analysisData.phases.length > 0 && (
        <div className="analysis-section">
          <h4 className="section-title">Game Phases</h4>
          <div className="phases-timeline">
            {analysisData.phases.map((phaseInfo, index) => (
              <div 
                key={index}
                className={`phase-segment ${phaseInfo.phase === analysisData.currentPhase ? 'active' : ''}`}
              >
                <div 
                  className="phase-bar"
                  style={{ backgroundColor: getPhaseColor(phaseInfo.phase) }}
                />
                <div className="phase-info">
                  <div className="phase-header">
                    <span className="phase-icon">{getPhaseIcon(phaseInfo.phase)}</span>
                    <span className="phase-name">
                      {phaseInfo.phase.charAt(0).toUpperCase() + phaseInfo.phase.slice(1)}
                    </span>
                  </div>
                  <div className="phase-range">
                    Moves {phaseInfo.moveRange.start}-{phaseInfo.moveRange.end || '?'}
                  </div>
                  <div className="phase-description">
                    {phaseInfo.description}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Key Moments */}
      {analysisData.keyMoments.length > 0 && (
        <div className="analysis-section">
          <h4 className="section-title">Key Moments</h4>
          <div className="key-moments">
            {analysisData.keyMoments.map((moment, index) => (
              <div key={index} className="key-moment">
                <div 
                  className="moment-indicator"
                  style={{ backgroundColor: getKeyMomentColor(moment.type) }}
                >
                  <span className="moment-icon">{getKeyMomentIcon(moment.type)}</span>
                </div>
                <div className="moment-info">
                  <div className="moment-header">
                    <span className="moment-move">Move {moment.moveNumber}</span>
                    <span className="moment-type">
                      {moment.type.replace('_', ' ').charAt(0).toUpperCase() + moment.type.replace('_', ' ').slice(1)}
                    </span>
                  </div>
                  <div className="moment-description">{moment.description}</div>
                  {moment.evaluationChange && (
                    <div className="moment-eval">
                      Evaluation change: {moment.evaluationChange > 0 ? '+' : ''}{moment.evaluationChange}cp
                    </div>
                  )}
                  <div className="moment-significance">
                    <span className="significance-label">Significance:</span>
                    <div className="significance-bar">
                      <div 
                        className="significance-fill"
                        style={{ 
                          width: `${(moment.significance / 10) * 100}%`,
                          backgroundColor: getKeyMomentColor(moment.type)
                        }}
                      />
                    </div>
                    <span className="significance-value">{moment.significance}/10</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <style jsx>{`
        .opening-analysis {
          background-color: #ffffff;
          border: 1px solid #e5e7eb;
          border-radius: 0.75rem;
          padding: 1.5rem;
          font-size: 0.875rem;
        }

        .analysis-header {
          margin-bottom: 1.5rem;
          padding-bottom: 0.75rem;
          border-bottom: 1px solid #e5e7eb;
        }

        .analysis-title {
          font-size: 1.125rem;
          font-weight: 600;
          color: #1f2937;
          margin: 0;
        }

        .analysis-section {
          margin-bottom: 1.5rem;
        }

        .analysis-section:last-child {
          margin-bottom: 0;
        }

        .section-title {
          font-size: 1rem;
          font-weight: 600;
          color: #374151;
          margin: 0 0 1rem 0;
        }

        .opening-info {
          background-color: #f9fafb;
          border-radius: 0.5rem;
          padding: 1rem;
        }

        .opening-header {
          display: flex;
          align-items: center;
          gap: 0.75rem;
          margin-bottom: 0.75rem;
        }

        .eco-code {
          background-color: #3b82f6;
          color: white;
          padding: 0.25rem 0.5rem;
          border-radius: 0.25rem;
          font-weight: 600;
          font-size: 0.75rem;
        }

        .opening-name {
          font-weight: 600;
          color: #1f2937;
        }

        .opening-moves {
          display: flex;
          flex-direction: column;
          gap: 0.25rem;
        }

        .moves-label {
          font-weight: 500;
          color: #6b7280;
          font-size: 0.8125rem;
        }

        .moves-sequence {
          font-family: 'Monaco', 'Courier New', monospace;
          background-color: #e5e7eb;
          padding: 0.5rem;
          border-radius: 0.25rem;
          color: #374151;
        }

        .current-phase {
          display: flex;
          flex-direction: column;
          gap: 0.75rem;
        }

        .phase-indicator {
          display: inline-flex;
          align-items: center;
          gap: 0.5rem;
          padding: 0.75rem 1rem;
          border-radius: 0.5rem;
          color: white;
          font-weight: 600;
          align-self: flex-start;
        }

        .phase-icon {
          font-size: 1.25rem;
        }

        .phase-name {
          font-size: 1rem;
        }

        .phase-description {
          color: #6b7280;
          font-size: 0.875rem;
        }

        .phases-timeline {
          display: flex;
          flex-direction: column;
          gap: 1rem;
        }

        .phase-segment {
          display: flex;
          align-items: flex-start;
          gap: 1rem;
        }

        .phase-segment.active .phase-bar {
          box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.3);
        }

        .phase-bar {
          width: 4px;
          height: 60px;
          border-radius: 2px;
          flex-shrink: 0;
          margin-top: 0.25rem;
        }

        .phase-info {
          flex: 1;
        }

        .phase-header {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          margin-bottom: 0.25rem;
        }

        .phase-range {
          font-size: 0.75rem;
          color: #6b7280;
          font-weight: 500;
          margin-bottom: 0.25rem;
        }

        .key-moments {
          display: flex;
          flex-direction: column;
          gap: 1rem;
        }

        .key-moment {
          display: flex;
          align-items: flex-start;
          gap: 1rem;
          padding: 1rem;
          background-color: #f9fafb;
          border-radius: 0.5rem;
        }

        .moment-indicator {
          width: 2.5rem;
          height: 2.5rem;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          flex-shrink: 0;
        }

        .moment-icon {
          font-size: 1.25rem;
        }

        .moment-info {
          flex: 1;
        }

        .moment-header {
          display: flex;
          align-items: center;
          gap: 0.75rem;
          margin-bottom: 0.5rem;
        }

        .moment-move {
          font-weight: 600;
          color: #1f2937;
        }

        .moment-type {
          background-color: #e5e7eb;
          padding: 0.25rem 0.5rem;
          border-radius: 0.25rem;
          font-size: 0.75rem;
          font-weight: 500;
          color: #374151;
        }

        .moment-description {
          color: #374151;
          margin-bottom: 0.5rem;
          line-height: 1.4;
        }

        .moment-eval {
          font-size: 0.75rem;
          color: #6b7280;
          margin-bottom: 0.5rem;
          font-family: 'Monaco', 'Courier New', monospace;
        }

        .moment-significance {
          display: flex;
          align-items: center;
          gap: 0.5rem;
        }

        .significance-label {
          font-size: 0.75rem;
          color: #6b7280;
          font-weight: 500;
        }

        .significance-bar {
          flex: 1;
          height: 0.5rem;
          background-color: #e5e7eb;
          border-radius: 0.25rem;
          overflow: hidden;
        }

        .significance-fill {
          height: 100%;
          transition: width 0.3s ease;
        }

        .significance-value {
          font-size: 0.75rem;
          color: #374151;
          font-weight: 600;
          min-width: 2rem;
          text-align: right;
        }

        @media (max-width: 768px) {
          .opening-analysis {
            padding: 1rem;
          }

          .opening-header {
            flex-direction: column;
            align-items: flex-start;
            gap: 0.5rem;
          }

          .moment-header {
            flex-direction: column;
            align-items: flex-start;
            gap: 0.5rem;
          }

          .moment-significance {
            flex-direction: column;
            align-items: stretch;
            gap: 0.25rem;
          }

          .significance-value {
            text-align: left;
          }
        }
      `}</style>
    </div>
  );
});

OpeningAnalysis.displayName = 'OpeningAnalysis';