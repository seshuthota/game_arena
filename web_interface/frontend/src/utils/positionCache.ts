import { Chess } from 'chess.js';

export interface CachedPosition {
  fen: string;
  moveNumber: number;
  timestamp: number;
}

export interface MoveRecord {
  move_notation: string;
  fen_before?: string;
  fen_after?: string;
  timestamp?: string;
}

export class PositionCache {
  private cache = new Map<number, CachedPosition>();
  private readonly maxCacheSize = 100;
  private readonly cacheTimeout = 5 * 60 * 1000; // 5 minutes

  constructor(private initialPosition: string = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1') {}

  /**
   * Get position at a specific move index
   */
  getPositionAtMove(moveIndex: number, moves: MoveRecord[]): string {
    // Check cache first
    const cached = this.cache.get(moveIndex);
    if (cached && Date.now() - cached.timestamp < this.cacheTimeout) {
      return cached.fen;
    }

    // Calculate position
    const position = this.calculatePositionAtMove(moveIndex, moves);
    
    // Cache the result
    this.cachePosition(moveIndex, position);
    
    return position;
  }

  /**
   * Calculate position at a specific move index
   */
  private calculatePositionAtMove(moveIndex: number, moves: MoveRecord[]): string {
    try {
      // Start from initial position
      const chess = new Chess(this.initialPosition);
      
      // If moveIndex is -1 or 0, return initial position
      if (moveIndex < 0) {
        return this.initialPosition;
      }

      // Apply moves up to the specified index
      for (let i = 0; i <= moveIndex && i < moves.length; i++) {
        const move = moves[i];
        
        // Try to use cached FEN if available
        if (move.fen_after && i === moveIndex) {
          // Validate the FEN before returning it
          const testChess = new Chess();
          try {
            testChess.load(move.fen_after);
            return move.fen_after;
          } catch {
            // Invalid FEN, continue with move calculation
          }
        }

        // Try to make the move using notation
        if (move.move_notation) {
          try {
            const moveResult = chess.move(move.move_notation);
            if (!moveResult) {
              // If move fails, try alternative notations or skip
              console.warn(`Failed to apply move: ${move.move_notation} at index ${i}`);
              continue;
            }
          } catch (error) {
            console.warn(`Error applying move: ${move.move_notation} at index ${i}`, error);
            continue;
          }
        }
      }

      return chess.fen();
    } catch (error) {
      console.error('Error calculating position at move', moveIndex, error);
      return this.initialPosition;
    }
  }

  /**
   * Cache a position
   */
  private cachePosition(moveIndex: number, fen: string): void {
    // Clean old entries if cache is too large
    if (this.cache.size >= this.maxCacheSize) {
      this.cleanOldEntries();
    }

    this.cache.set(moveIndex, {
      fen,
      moveNumber: moveIndex,
      timestamp: Date.now()
    });
  }

  /**
   * Clean old cache entries
   */
  private cleanOldEntries(): void {
    const now = Date.now();
    const entriesToDelete: number[] = [];

    this.cache.forEach((cached, moveIndex) => {
      if (now - cached.timestamp > this.cacheTimeout) {
        entriesToDelete.push(moveIndex);
      }
    });

    // Delete expired entries
    entriesToDelete.forEach(moveIndex => {
      this.cache.delete(moveIndex);
    });

    // If still too large, delete oldest entries
    if (this.cache.size >= this.maxCacheSize) {
      const entries = Array.from(this.cache.entries())
        .sort((a, b) => a[1].timestamp - b[1].timestamp);
      
      const toDelete = entries.slice(0, Math.floor(this.maxCacheSize / 2));
      toDelete.forEach(([moveIndex]) => {
        this.cache.delete(moveIndex);
      });
    }
  }

  /**
   * Clear the entire cache
   */
  clearCache(): void {
    this.cache.clear();
  }

  /**
   * Get cache statistics
   */
  getCacheStats(): { size: number; maxSize: number; hitRate?: number } {
    return {
      size: this.cache.size,
      maxSize: this.maxCacheSize
    };
  }

  /**
   * Preload positions for a range of moves
   */
  preloadPositions(startIndex: number, endIndex: number, moves: MoveRecord[]): void {
    for (let i = startIndex; i <= endIndex && i < moves.length; i++) {
      if (!this.cache.has(i)) {
        this.getPositionAtMove(i, moves);
      }
    }
  }

  /**
   * Validate a FEN position
   */
  static validateFEN(fen: string): boolean {
    try {
      const chess = new Chess();
      chess.load(fen);
      return true;
    } catch {
      return false;
    }
  }

  /**
   * Get the last valid position before a given move index
   */
  getLastValidPosition(moveIndex: number, moves: MoveRecord[]): string {
    for (let i = moveIndex - 1; i >= 0; i--) {
      try {
        const position = this.getPositionAtMove(i, moves);
        if (PositionCache.validateFEN(position)) {
          return position;
        }
      } catch {
        continue;
      }
    }
    return this.initialPosition;
  }
}

export default PositionCache;