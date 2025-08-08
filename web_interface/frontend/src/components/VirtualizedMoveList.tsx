import React, { useMemo, useCallback, memo } from 'react';
import { FixedSizeList as List } from 'react-window';
import { MoveRecord, GameDetail } from '../types/api';

interface VirtualizedMoveListProps {
  moves: MoveRecord[];
  game: GameDetail;
  selectedMoveIndex: number | null;
  onMoveClick: (index: number) => void;
  itemHeight?: number;
  height?: number;
  className?: string;
}

interface MoveRowProps {
  index: number;
  style: React.CSSProperties;
  data: {
    moves: MoveRecord[];
    selectedMoveIndex: number | null;
    onMoveClick: (index: number) => void;
  };
}

// Individual move row component for virtual scrolling
const VirtualMoveRow: React.FC<MoveRowProps> = memo(({ index, style, data }) => {
  const { moves, selectedMoveIndex, onMoveClick } = data;
  const move = moves[index];

  if (!move) {
    return <div style={style} className="virtual-move-row empty-row"></div>;
  }

  const isWhite = index % 2 === 0;
  const isSelected = selectedMoveIndex === index;
  const moveNumber = index + 1;

  const formatThinkingTime = (timeMs: number) => {
    if (timeMs < 1000) return `${timeMs}ms`;
    const seconds = (timeMs / 1000).toFixed(1);
    return `${seconds}s`;
  };

  const getMoveQualityColor = (score: number | null) => {
    if (!score) return '#6b7280';
    if (score >= 0.8) return '#059669'; // Green - excellent
    if (score >= 0.6) return '#d97706'; // Orange - good
    if (score >= 0.4) return '#dc2626'; // Red - poor
    return '#991b1b'; // Dark red - blunder
  };

  const getMoveQualityText = (score: number | null) => {
    if (!score) return 'Unknown';
    if (score >= 0.8) return 'Excellent';
    if (score >= 0.6) return 'Good';
    if (score >= 0.4) return 'Poor';
    return 'Blunder';
  };

  return (
    <div 
      style={style} 
      className={`virtual-move-row ${isSelected ? 'selected' : ''} ${isWhite ? 'white-move' : 'black-move'}`}
      onClick={() => onMoveClick(index)}
    >
      <div className="move-row-content">
        <div className="move-number">
          <span className="move-num">{Math.ceil(moveNumber / 2)}</span>
          <span className="move-player">{isWhite ? 'W' : 'B'}</span>
        </div>
        
        <div className="move-notation">
          <span className={`notation ${!move.is_legal ? 'illegal-move' : ''}`}>
            {move.move_notation}
          </span>
          {move.blunder_flag && <span className="blunder-flag">!</span>}
        </div>
        
        <div className="move-metrics">
          <div className="thinking-time">
            <span className="metric-label">Think:</span>
            <span className="metric-value">{formatThinkingTime(move.thinking_time_ms)}</span>
          </div>
          
          {move.move_quality_score !== null && (
            <div className="move-quality">
              <span className="metric-label">Quality:</span>
              <span 
                className="quality-score"
                style={{ color: getMoveQualityColor(move.move_quality_score) }}
              >
                {getMoveQualityText(move.move_quality_score)}
              </span>
            </div>
          )}
        </div>
        
        <div className="move-status">
          {!move.is_legal && <span className="illegal-badge">Illegal</span>}
          {!move.parsing_success && <span className="parsing-badge">Parse Error</span>}
          {move.had_rethink && <span className="rethink-badge">Rethink</span>}
        </div>
      </div>
    </div>
  );
});

export const VirtualizedMoveList: React.FC<VirtualizedMoveListProps> = ({
  moves,
  selectedMoveIndex,
  onMoveClick,
  itemHeight = 60,
  height = 400,
  className
}) => {
  const itemCount = moves.length;

  // Memoized data for virtual list
  const itemData = useMemo(() => ({
    moves,
    selectedMoveIndex,
    onMoveClick
  }), [moves, selectedMoveIndex, onMoveClick]);

  // Scroll to selected move
  const listRef = React.useRef<any>(null);
  
  React.useEffect(() => {
    if (listRef.current && selectedMoveIndex !== null) {
      listRef.current.scrollToItem(selectedMoveIndex, 'center');
    }
  }, [selectedMoveIndex]);

  if (moves.length === 0) {
    return (
      <div className={`virtualized-move-list empty ${className || ''}`}>
        <div className="no-moves">
          <div className="no-moves-icon">♟️</div>
          <p className="no-moves-text">No moves to display</p>
        </div>
      </div>
    );
  }

  return (
    <div className={`virtualized-move-list ${className || ''}`}>
      {/* Move List Header */}
      <div className="virtual-move-header">
        <div className="header-section move-number-header">#</div>
        <div className="header-section notation-header">Move</div>
        <div className="header-section metrics-header">Metrics</div>
        <div className="header-section status-header">Status</div>
      </div>

      {/* Virtual List */}
      <List
        ref={listRef}
        height={height}
        width="100%"
        itemCount={itemCount}
        itemSize={itemHeight}
        itemData={itemData}
        overscanCount={10}
      >
        {VirtualMoveRow}
      </List>

      <style jsx>{`
        .virtualized-move-list {
          display: flex;
          flex-direction: column;
          border: 1px solid #e5e7eb;
          border-radius: 0.75rem;
          overflow: hidden;
          background-color: white;
        }

        .virtualized-move-list.empty {
          border: none;
          background: transparent;
        }

        .virtual-move-header {
          display: grid;
          grid-template-columns: 80px 1fr 1.5fr 120px;
          background-color: #f8fafc;
          border-bottom: 2px solid #e5e7eb;
          padding: 1rem;
          font-weight: 600;
          color: #374151;
          font-size: 0.875rem;
        }

        .header-section {
          text-align: left;
          padding: 0 0.5rem;
        }

        .virtual-move-row {
          border-bottom: 1px solid #f3f4f6;
          transition: all 0.15s ease;
          cursor: pointer;
          background-color: white;
        }

        .virtual-move-row:hover {
          background-color: #f8fafc;
        }

        .virtual-move-row.selected {
          background-color: #dbeafe;
          border-left: 4px solid #3b82f6;
        }

        .virtual-move-row.white-move {
          background-color: #ffffff;
        }

        .virtual-move-row.black-move {
          background-color: #fafafa;
        }

        .virtual-move-row.selected.white-move,
        .virtual-move-row.selected.black-move {
          background-color: #dbeafe;
        }

        .move-row-content {
          display: grid;
          grid-template-columns: 80px 1fr 1.5fr 120px;
          align-items: center;
          padding: 1rem;
          height: 100%;
        }

        .move-number {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          padding: 0 0.5rem;
        }

        .move-num {
          font-weight: 700;
          color: #1f2937;
          font-size: 1rem;
        }

        .move-player {
          background-color: #e5e7eb;
          color: #374151;
          padding: 0.25rem 0.5rem;
          border-radius: 0.25rem;
          font-size: 0.75rem;
          font-weight: 600;
        }

        .white-move .move-player {
          background-color: #f3f4f6;
          color: #1f2937;
        }

        .black-move .move-player {
          background-color: #374151;
          color: white;
        }

        .move-notation {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          padding: 0 0.5rem;
        }

        .notation {
          font-family: 'SF Mono', 'Monaco', 'Inconsolata', 'Roboto Mono', monospace;
          font-size: 1rem;
          font-weight: 600;
          color: #1f2937;
        }

        .notation.illegal-move {
          color: #dc2626;
          text-decoration: line-through;
        }

        .blunder-flag {
          color: #dc2626;
          font-weight: 700;
          font-size: 1.2rem;
        }

        .move-metrics {
          display: flex;
          flex-direction: column;
          gap: 0.25rem;
          padding: 0 0.5rem;
        }

        .thinking-time,
        .move-quality {
          display: flex;
          align-items: center;
          gap: 0.5rem;
        }

        .metric-label {
          font-size: 0.75rem;
          color: #6b7280;
          font-weight: 500;
          min-width: 45px;
        }

        .metric-value {
          font-family: 'SF Mono', 'Monaco', 'Inconsolata', 'Roboto Mono', monospace;
          font-size: 0.75rem;
          color: #4b5563;
        }

        .quality-score {
          font-size: 0.75rem;
          font-weight: 600;
        }

        .move-status {
          display: flex;
          flex-direction: column;
          gap: 0.25rem;
          padding: 0 0.5rem;
        }

        .illegal-badge,
        .parsing-badge,
        .rethink-badge {
          font-size: 0.625rem;
          padding: 0.25rem 0.5rem;
          border-radius: 0.25rem;
          font-weight: 600;
          text-transform: uppercase;
          letter-spacing: 0.05em;
          text-align: center;
        }

        .illegal-badge {
          background-color: #fef2f2;
          color: #dc2626;
        }

        .parsing-badge {
          background-color: #fef3c7;
          color: #d97706;
        }

        .rethink-badge {
          background-color: #dbeafe;
          color: #1e40af;
        }

        .no-moves {
          text-align: center;
          padding: 3rem 2rem;
          color: #6b7280;
        }

        .no-moves-icon {
          font-size: 3rem;
          margin-bottom: 1rem;
        }

        .no-moves-text {
          font-size: 1.125rem;
          margin: 0;
        }

        .empty-row {
          background-color: transparent;
        }

        /* Responsive design */
        @media (max-width: 1024px) {
          .virtual-move-header,
          .move-row-content {
            grid-template-columns: 60px 1fr 1fr 100px;
            font-size: 0.75rem;
          }

          .move-metrics {
            gap: 0.125rem;
          }

          .thinking-time,
          .move-quality {
            flex-direction: column;
            align-items: flex-start;
            gap: 0.125rem;
          }

          .metric-label {
            min-width: auto;
          }
        }

        @media (max-width: 768px) {
          .virtual-move-header,
          .move-row-content {
            grid-template-columns: 60px 1fr 80px;
          }

          .metrics-header,
          .move-metrics {
            display: none;
          }

          .move-status {
            align-items: center;
          }
        }

        @media (max-width: 640px) {
          .virtual-move-header,
          .move-row-content {
            grid-template-columns: 50px 1fr 60px;
          }

          .move-number {
            gap: 0.25rem;
          }

          .move-num {
            font-size: 0.875rem;
          }

          .notation {
            font-size: 0.875rem;
          }
        }
      `}</style>
    </div>
  );
};