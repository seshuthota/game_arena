import React from 'react';

interface MoveDetailsPanelProps {
  move: any;
  moveNumber: number;
  isWhite: boolean;
}

export const MoveDetailsPanel: React.FC<MoveDetailsPanelProps> = ({ move, moveNumber, isWhite }) => {
  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  };

  return (
    <div className="move-details">
      <div className="move-details-header">
        <h3 className="details-title">
          Move {moveNumber}: {move.move_notation || 'Unknown'}
        </h3>
        <div className="player-indicator">
          <span className="player-color-icon">{isWhite ? '⚪' : '⚫'}</span>
          <span className="player-text">{isWhite ? 'White' : 'Black'}</span>
        </div>
      </div>

      <div className="details-content">
        <div className="detail-section">
          <h4 className="section-title">Move Information</h4>
          <div className="detail-grid">
            <div className="detail-item">
              <span className="detail-label">Notation:</span>
              <code className="detail-value-code">
                {move.move_notation || 'N/A'}
              </code>
            </div>
            <div className="detail-item">
              <span className="detail-label">Legal Move:</span>
              <span className="detail-value">{move.is_legal ? '✅ Yes' : '❌ No'}</span>
            </div>
            <div className="detail-item">
              <span className="detail-label">Parsing Success:</span>
              <span className="detail-value">{move.parsing_success ? '✅ Yes' : '❌ No'}</span>
            </div>
            {move.timestamp && (
              <div className="detail-item">
                <span className="detail-label">Timestamp:</span>
                <span className="detail-value">{formatTimestamp(move.timestamp)}</span>
              </div>
            )}
          </div>
        </div>

        {(move.fen_before || move.fen_after) && (
          <div className="detail-section">
            <h4 className="section-title">Board Positions (FEN)</h4>
            {move.fen_before && (
              <div className="detail-item">
                <span className="detail-label">Before Move:</span>
                <div className="fen-container">
                  <code className="fen-notation">{move.fen_before}</code>
                  <button className="copy-button" onClick={() => navigator.clipboard?.writeText(move.fen_before)}>
                    📋 Copy
                  </button>
                </div>
              </div>
            )}
            {move.fen_after && (
              <div className="detail-item">
                <span className="detail-label">After Move:</span>
                <div className="fen-container">
                  <code className="fen-notation">{move.fen_after}</code>
                  <button className="copy-button" onClick={() => navigator.clipboard?.writeText(move.fen_after)}>
                    📋 Copy
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {move.llm_response && (
          <div className="detail-section">
            <h4 className="section-title">LLM Response</h4>
            <div className="llm-response-container">
              <div className="detail-item">
                <span className="detail-label">Response:</span>
                <div className="thinking-text">{move.llm_response}</div>
              </div>
            </div>
          </div>
        )}

        {(move.thinking_time_ms || move.api_call_time_ms || move.total_time_ms) && (
          <div className="detail-section">
            <h4 className="section-title">Timing Information</h4>
            <div className="detail-grid">
              {move.thinking_time_ms !== undefined && (
                <div className="detail-item">
                  <span className="detail-label">Thinking Time:</span>
                  <span className="detail-value">{move.thinking_time_ms}ms</span>
                </div>
              )}
              {move.api_call_time_ms !== undefined && (
                <div className="detail-item">
                  <span className="detail-label">API Call Time:</span>
                  <span className="detail-value">{move.api_call_time_ms}ms</span>
                </div>
              )}
              {move.total_time_ms !== undefined && (
                <div className="detail-item">
                  <span className="detail-label">Total Time:</span>
                  <span className="detail-value">{move.total_time_ms}ms</span>
                </div>
              )}
            </div>
          </div>
        )}

        {(move.move_quality_score || move.blunder_flag || move.had_rethink) && (
          <div className="detail-section">
            <h4 className="section-title">Move Analysis</h4>
            <div className="detail-grid">
              {move.move_quality_score !== null && (
                <div className="detail-item">
                  <span className="detail-label">Quality Score:</span>
                  <span className="detail-value">{move.move_quality_score}</span>
                </div>
              )}
              <div className="detail-item">
                <span className="detail-label">Blunder Flag:</span>
                <span className="detail-value">{move.blunder_flag ? '🚨 Yes' : '✅ No'}</span>
              </div>
              <div className="detail-item">
                <span className="detail-label">Had Rethink:</span>
                <span className="detail-value">{move.had_rethink ? `✅ Yes (${move.rethink_attempts} attempts)` : '❌ No'}</span>
              </div>
            </div>
          </div>
        )}
      </div>

      <style jsx>{`
        .move-details {
          height: 100%;
        }

        .move-details-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 1.5rem;
          padding-bottom: 1rem;
          border-bottom: 1px solid #e5e7eb;
        }

        .details-title {
          font-size: 1.25rem;
          font-weight: 600;
          color: #1f2937;
          margin: 0;
        }

        .player-indicator {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          font-size: 0.875rem;
          font-weight: 500;
        }

        .player-color-icon {
          font-size: 1rem;
        }

        .details-content {
          display: flex;
          flex-direction: column;
          gap: 1.5rem;
        }

        .detail-section {
          border: 1px solid #e5e7eb;
          border-radius: 0.5rem;
          padding: 1rem;
          background-color: #ffffff;
        }

        .section-title {
          font-size: 1rem;
          font-weight: 600;
          color: #374151;
          margin: 0 0 0.75rem 0;
        }

        .detail-grid {
          display: flex;
          flex-direction: column;
          gap: 0.5rem;
        }

        .detail-item {
          display: flex;
          flex-direction: column;
          gap: 0.25rem;
        }

        .detail-label {
          font-size: 0.8125rem;
          font-weight: 500;
          color: #6b7280;
          text-transform: uppercase;
          letter-spacing: 0.025em;
        }

        .detail-value {
          font-size: 0.875rem;
          color: #374151;
        }

        .detail-value-code {
          font-family: 'Monaco', 'Courier New', monospace;
          background-color: #f3f4f6;
          padding: 0.25rem 0.5rem;
          border-radius: 0.25rem;
          font-size: 0.8125rem;
          color: #1f2937;
        }

        .fen-container {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          flex-wrap: wrap;
        }

        .fen-notation {
          font-family: 'Monaco', 'Courier New', monospace;
          background-color: #f3f4f6;
          padding: 0.5rem;
          border-radius: 0.375rem;
          font-size: 0.8125rem;
          color: #1f2937;
          flex: 1;
          min-width: 200px;
          word-break: break-all;
        }

        .copy-button {
          background-color: #3b82f6;
          color: white;
          border: none;
          padding: 0.5rem 0.75rem;
          border-radius: 0.375rem;
          font-size: 0.8125rem;
          cursor: pointer;
          transition: background-color 0.2s;
          white-space: nowrap;
        }

        .copy-button:hover {
          background-color: #2563eb;
        }

        .thinking-text {
          font-size: 0.875rem;
          color: #374151;
          line-height: 1.5;
          background-color: #f9fafb;
          padding: 0.75rem;
          border-radius: 0.375rem;
          border: 1px solid #e5e7eb;
        }

        .evaluation-score.positive {
          font-weight: 600;
          color: #059669;
        }

        .evaluation-score.negative {
          font-weight: 600;
          color: #dc2626;
        }

        .evaluation-score.neutral {
          font-weight: 600;
          color: #6b7280;
        }

        .mate-score {
          font-weight: 600;
          color: #dc2626;
        }

        .llm-response-container {
          display: flex;
          flex-direction: column;
          gap: 0.75rem;
        }

        @media (max-width: 640px) {
          .move-details-header {
            flex-direction: column;
            align-items: flex-start;
            gap: 0.5rem;
          }

          .fen-container {
            flex-direction: column;
            align-items: stretch;
          }

          .fen-notation {
            min-width: auto;
          }
        }
      `}</style>
    </div>
  );
};