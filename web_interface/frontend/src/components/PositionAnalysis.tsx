import React, { memo, useMemo } from 'react';
import { Chess } from 'chess.js';

export interface MaterialCount {
  pawns: number;
  knights: number;
  bishops: number;
  rooks: number;
  queens: number;
  total: number; // Point value
}

export interface PositionAnalysisData {
  fen: string;
  moveNumber: number;
  sideToMove: 'white' | 'black';
  materialBalance: {
    white: MaterialCount;
    black: MaterialCount;
    advantage: number; // Positive for white advantage
  };
  positionEvaluation?: {
    score: number; // Centipawns
    bestMove?: string;
    principalVariation?: string[];
  };
  moveQuality?: {
    classification: 'excellent' | 'good' | 'inaccuracy' | 'mistake' | 'blunder';
    alternativeMoves?: string[];
  };
  pieceActivity?: {
    developedPieces: number;
    totalPieces: number;
    centerControl: number;
    kingSafety: number;
  };
}

interface PositionAnalysisProps {
  fen: string;
  moveNumber: number;
  moveQuality?: 'excellent' | 'good' | 'inaccuracy' | 'mistake' | 'blunder';
  moveQualityScore?: number | null;
  llmReasoning?: string | null;
  className?: string;
}

export const PositionAnalysis: React.FC<PositionAnalysisProps> = memo(({
  fen,
  moveNumber,
  moveQuality,
  moveQualityScore,
  llmReasoning,
  className = ''
}) => {
  const analysisData = useMemo(() => {
    try {
      const chess = new Chess(fen);
      
      // Calculate material balance
      const board = chess.board();
      const whiteMaterial: MaterialCount = { pawns: 0, knights: 0, bishops: 0, rooks: 0, queens: 0, total: 0 };
      const blackMaterial: MaterialCount = { pawns: 0, knights: 0, bishops: 0, rooks: 0, queens: 0, total: 0 };
      
      const pieceValues = { p: 1, n: 3, b: 3, r: 5, q: 9, k: 0 };
      
      board.forEach(row => {
        row.forEach(square => {
          if (square) {
            const piece = square.type;
            const color = square.color;
            const material = color === 'w' ? whiteMaterial : blackMaterial;
            
            switch (piece) {
              case 'p': material.pawns++; break;
              case 'n': material.knights++; break;
              case 'b': material.bishops++; break;
              case 'r': material.rooks++; break;
              case 'q': material.queens++; break;
            }
            material.total += pieceValues[piece];
          }
        });
      });
      
      const materialAdvantage = whiteMaterial.total - blackMaterial.total;
      
      // Calculate basic piece activity metrics
      const moves = chess.moves({ verbose: true });
      const developedPieces = calculateDevelopedPieces(chess);
      const centerControl = calculateCenterControl(chess);
      const kingSafety = calculateKingSafety(chess);
      
      return {
        fen,
        moveNumber,
        sideToMove: chess.turn() === 'w' ? 'white' as const : 'black' as const,
        materialBalance: {
          white: whiteMaterial,
          black: blackMaterial,
          advantage: materialAdvantage
        },
        pieceActivity: {
          developedPieces,
          totalPieces: whiteMaterial.total + blackMaterial.total,
          centerControl,
          kingSafety
        },
        moveQuality: moveQuality ? {
          classification: moveQuality,
          alternativeMoves: []
        } : undefined
      };
    } catch (error) {
      console.error('Error analyzing position:', error);
      return null;
    }
  }, [fen, moveNumber, moveQuality]);

  if (!analysisData) {
    return (
      <div className={`position-analysis error ${className}`}>
        <div className="error-message">
          <span className="error-icon">⚠️</span>
          <span>Unable to analyze position</span>
        </div>
        <style jsx>{`
          .position-analysis.error {
            padding: 1rem;
            background-color: #fef2f2;
            border: 1px solid #fecaca;
            border-radius: 0.5rem;
          }
          
          .error-message {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            color: #dc2626;
            font-size: 0.875rem;
          }
          
          .error-icon {
            font-size: 1rem;
          }
        `}</style>
      </div>
    );
  }

  const getMoveQualityColor = (quality?: string) => {
    switch (quality) {
      case 'excellent': return '#059669';
      case 'good': return '#3b82f6';
      case 'inaccuracy': return '#d97706';
      case 'mistake': return '#dc2626';
      case 'blunder': return '#991b1b';
      default: return '#6b7280';
    }
  };

  const getMoveQualityIcon = (quality?: string) => {
    switch (quality) {
      case 'excellent': return '!!';
      case 'good': return '!';
      case 'inaccuracy': return '?!';
      case 'mistake': return '?';
      case 'blunder': return '??';
      default: return '';
    }
  };

  const formatMaterialAdvantage = (advantage: number) => {
    if (advantage === 0) return 'Equal';
    const abs = Math.abs(advantage);
    const color = advantage > 0 ? 'White' : 'Black';
    return `${color} +${abs}`;
  };

  return (
    <div className={`position-analysis ${className}`}>
      <div className="analysis-header">
        <h3 className="analysis-title">Position Analysis</h3>
        <div className="move-info">
          <span className="move-number">Move {Math.ceil(moveNumber / 2)}</span>
          <span className="side-to-move">
            {analysisData.sideToMove === 'white' ? '⚪' : '⚫'} to move
          </span>
        </div>
      </div>

      {/* Move Quality Indicator */}
      {moveQuality && (
        <div className="move-quality-section">
          <div 
            className="move-quality-indicator"
            style={{ 
              backgroundColor: getMoveQualityColor(moveQuality),
              color: 'white'
            }}
          >
            <span className="quality-icon">{getMoveQualityIcon(moveQuality)}</span>
            <span className="quality-text">{moveQuality.charAt(0).toUpperCase() + moveQuality.slice(1)}</span>
            {moveQualityScore !== null && moveQualityScore !== undefined && (
              <span className="quality-score">({moveQualityScore.toFixed(1)})</span>
            )}
          </div>
        </div>
      )}

      {/* Material Balance */}
      <div className="analysis-section">
        <h4 className="section-title">Material Balance</h4>
        <div className="material-balance">
          <div className="material-side">
            <div className="side-header">
              <span className="side-icon">⚪</span>
              <span className="side-name">White</span>
            </div>
            <div className="material-pieces">
              {analysisData.materialBalance.white.queens > 0 && (
                <span className="piece-count">♕×{analysisData.materialBalance.white.queens}</span>
              )}
              {analysisData.materialBalance.white.rooks > 0 && (
                <span className="piece-count">♖×{analysisData.materialBalance.white.rooks}</span>
              )}
              {analysisData.materialBalance.white.bishops > 0 && (
                <span className="piece-count">♗×{analysisData.materialBalance.white.bishops}</span>
              )}
              {analysisData.materialBalance.white.knights > 0 && (
                <span className="piece-count">♘×{analysisData.materialBalance.white.knights}</span>
              )}
              {analysisData.materialBalance.white.pawns > 0 && (
                <span className="piece-count">♙×{analysisData.materialBalance.white.pawns}</span>
              )}
            </div>
            <div className="material-total">{analysisData.materialBalance.white.total} points</div>
          </div>

          <div className="material-advantage">
            <div className="advantage-text">
              {formatMaterialAdvantage(analysisData.materialBalance.advantage)}
            </div>
          </div>

          <div className="material-side">
            <div className="side-header">
              <span className="side-icon">⚫</span>
              <span className="side-name">Black</span>
            </div>
            <div className="material-pieces">
              {analysisData.materialBalance.black.queens > 0 && (
                <span className="piece-count">♛×{analysisData.materialBalance.black.queens}</span>
              )}
              {analysisData.materialBalance.black.rooks > 0 && (
                <span className="piece-count">♜×{analysisData.materialBalance.black.rooks}</span>
              )}
              {analysisData.materialBalance.black.bishops > 0 && (
                <span className="piece-count">♝×{analysisData.materialBalance.black.bishops}</span>
              )}
              {analysisData.materialBalance.black.knights > 0 && (
                <span className="piece-count">♞×{analysisData.materialBalance.black.knights}</span>
              )}
              {analysisData.materialBalance.black.pawns > 0 && (
                <span className="piece-count">♟×{analysisData.materialBalance.black.pawns}</span>
              )}
            </div>
            <div className="material-total">{analysisData.materialBalance.black.total} points</div>
          </div>
        </div>
      </div>

      {/* Positional Factors */}
      {analysisData.pieceActivity && (
        <div className="analysis-section">
          <h4 className="section-title">Positional Factors</h4>
          <div className="positional-metrics">
            <div className="metric">
              <span className="metric-label">Development:</span>
              <div className="metric-bar">
                <div 
                  className="metric-fill"
                  style={{ 
                    width: `${(analysisData.pieceActivity.developedPieces / 8) * 100}%`,
                    backgroundColor: '#3b82f6'
                  }}
                />
              </div>
              <span className="metric-value">
                {analysisData.pieceActivity.developedPieces}/8
              </span>
            </div>
            
            <div className="metric">
              <span className="metric-label">Center Control:</span>
              <div className="metric-bar">
                <div 
                  className="metric-fill"
                  style={{ 
                    width: `${analysisData.pieceActivity.centerControl}%`,
                    backgroundColor: '#059669'
                  }}
                />
              </div>
              <span className="metric-value">{analysisData.pieceActivity.centerControl}%</span>
            </div>
            
            <div className="metric">
              <span className="metric-label">King Safety:</span>
              <div className="metric-bar">
                <div 
                  className="metric-fill"
                  style={{ 
                    width: `${analysisData.pieceActivity.kingSafety}%`,
                    backgroundColor: '#dc2626'
                  }}
                />
              </div>
              <span className="metric-value">{analysisData.pieceActivity.kingSafety}%</span>
            </div>
          </div>
        </div>
      )}

      {/* LLM Reasoning */}
      {llmReasoning && (
        <div className="analysis-section">
          <h4 className="section-title">LLM Analysis</h4>
          <div className="llm-reasoning">
            <div className="reasoning-content">
              {llmReasoning}
            </div>
          </div>
        </div>
      )}

      <style jsx>{`
        .position-analysis {
          background-color: #ffffff;
          border: 1px solid #e5e7eb;
          border-radius: 0.75rem;
          padding: 1.5rem;
          font-size: 0.875rem;
        }

        .analysis-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
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

        .move-info {
          display: flex;
          align-items: center;
          gap: 0.75rem;
          font-size: 0.875rem;
        }

        .move-number {
          font-weight: 600;
          color: #374151;
        }

        .side-to-move {
          display: flex;
          align-items: center;
          gap: 0.25rem;
          color: #6b7280;
        }

        .move-quality-section {
          margin-bottom: 1.5rem;
        }

        .move-quality-indicator {
          display: inline-flex;
          align-items: center;
          gap: 0.5rem;
          padding: 0.5rem 1rem;
          border-radius: 0.5rem;
          font-weight: 600;
          font-size: 0.875rem;
        }

        .quality-icon {
          font-weight: 700;
        }

        .quality-score {
          font-size: 0.75rem;
          opacity: 0.9;
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

        .material-balance {
          display: flex;
          align-items: center;
          gap: 1rem;
        }

        .material-side {
          flex: 1;
          background-color: #f9fafb;
          border-radius: 0.5rem;
          padding: 1rem;
        }

        .side-header {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          margin-bottom: 0.75rem;
        }

        .side-icon {
          font-size: 1.25rem;
        }

        .side-name {
          font-weight: 600;
          color: #374151;
        }

        .material-pieces {
          display: flex;
          flex-wrap: wrap;
          gap: 0.5rem;
          margin-bottom: 0.75rem;
          min-height: 1.5rem;
        }

        .piece-count {
          background-color: #e5e7eb;
          padding: 0.25rem 0.5rem;
          border-radius: 0.25rem;
          font-size: 0.75rem;
          font-weight: 500;
          color: #374151;
        }

        .material-total {
          font-weight: 600;
          color: #1f2937;
          text-align: center;
        }

        .material-advantage {
          display: flex;
          align-items: center;
          justify-content: center;
          min-width: 80px;
        }

        .advantage-text {
          font-weight: 700;
          color: #374151;
          text-align: center;
          font-size: 0.875rem;
        }

        .positional-metrics {
          display: flex;
          flex-direction: column;
          gap: 1rem;
        }

        .metric {
          display: flex;
          align-items: center;
          gap: 1rem;
        }

        .metric-label {
          min-width: 100px;
          font-weight: 500;
          color: #374151;
        }

        .metric-bar {
          flex: 1;
          height: 0.5rem;
          background-color: #e5e7eb;
          border-radius: 0.25rem;
          overflow: hidden;
        }

        .metric-fill {
          height: 100%;
          transition: width 0.3s ease;
        }

        .metric-value {
          min-width: 50px;
          text-align: right;
          font-weight: 600;
          color: #374151;
        }

        .llm-reasoning {
          background-color: #f9fafb;
          border-radius: 0.5rem;
          padding: 1rem;
        }

        .reasoning-content {
          color: #374151;
          line-height: 1.5;
          white-space: pre-wrap;
        }

        @media (max-width: 768px) {
          .position-analysis {
            padding: 1rem;
          }

          .analysis-header {
            flex-direction: column;
            align-items: flex-start;
            gap: 0.5rem;
          }

          .material-balance {
            flex-direction: column;
            gap: 0.75rem;
          }

          .material-advantage {
            order: -1;
            min-width: auto;
          }

          .metric {
            flex-direction: column;
            align-items: stretch;
            gap: 0.5rem;
          }

          .metric-label {
            min-width: auto;
          }

          .metric-value {
            min-width: auto;
            text-align: left;
          }
        }
      `}</style>
    </div>
  );
});

// Helper functions for position analysis
function calculateDevelopedPieces(chess: Chess): number {
  const board = chess.board();
  let developed = 0;
  
  // Check if knights and bishops are developed (not on starting squares)
  const startingSquares = {
    'wn': ['b1', 'g1'],
    'wb': ['c1', 'f1'],
    'bn': ['b8', 'g8'],
    'bb': ['c8', 'f8']
  };
  
  board.forEach((row, rankIndex) => {
    row.forEach((square, fileIndex) => {
      if (square && (square.type === 'n' || square.type === 'b')) {
        const squareName = String.fromCharCode(97 + fileIndex) + (8 - rankIndex);
        const pieceKey = square.color + square.type as keyof typeof startingSquares;
        
        if (startingSquares[pieceKey] && !startingSquares[pieceKey].includes(squareName)) {
          developed++;
        }
      }
    });
  });
  
  return developed;
}

function calculateCenterControl(chess: Chess): number {
  const centerSquares = ['d4', 'd5', 'e4', 'e5'];
  const moves = chess.moves({ verbose: true });
  
  const controlledSquares = moves.filter(move => 
    centerSquares.includes(move.to)
  ).length;
  
  return Math.min(100, (controlledSquares / centerSquares.length) * 100);
}

function calculateKingSafety(chess: Chess): number {
  // Simple king safety calculation based on whether king has castled
  // and if there are pieces around the king
  const turn = chess.turn();
  const kingSquare = chess.board().flat().find(square => 
    square && square.type === 'k' && square.color === turn
  );
  
  if (!kingSquare) return 0;
  
  // This is a simplified calculation
  // In a real implementation, you'd check for:
  // - Castling rights/status
  // - Pawn shield
  // - Attacking pieces near king
  // - Open files near king
  
  return Math.floor(Math.random() * 100); // Placeholder
}

PositionAnalysis.displayName = 'PositionAnalysis';