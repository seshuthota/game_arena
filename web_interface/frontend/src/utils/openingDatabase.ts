// Simple opening database with ECO codes
export interface OpeningInfo {
  eco: string;
  name: string;
  moves: string[];
  fen?: string;
}

// Basic opening database - in a real implementation this would be much larger
export const OPENING_DATABASE: OpeningInfo[] = [
  {
    eco: 'B00',
    name: 'King\'s Pawn',
    moves: ['e4']
  },
  {
    eco: 'B20',
    name: 'Sicilian Defence',
    moves: ['e4', 'c5']
  },
  {
    eco: 'B22',
    name: 'Sicilian Defence: Alapin Variation',
    moves: ['e4', 'c5', 'c3']
  },
  {
    eco: 'C20',
    name: 'King\'s Pawn Game',
    moves: ['e4', 'e5']
  },
  {
    eco: 'C25',
    name: 'Vienna Game',
    moves: ['e4', 'e5', 'Nc3']
  },
  {
    eco: 'C30',
    name: 'King\'s Gambit',
    moves: ['e4', 'e5', 'f4']
  },
  {
    eco: 'C44',
    name: 'King\'s Pawn Game: Tayler Opening',
    moves: ['e4', 'e5', 'Nf3', 'Nc6', 'Be2']
  },
  {
    eco: 'C50',
    name: 'Italian Game',
    moves: ['e4', 'e5', 'Nf3', 'Nc6', 'Bc4']
  },
  {
    eco: 'C53',
    name: 'Italian Game: Classical Variation',
    moves: ['e4', 'e5', 'Nf3', 'Nc6', 'Bc4', 'Be7']
  },
  {
    eco: 'C54',
    name: 'Italian Game: Classical Variation, Greco Gambit',
    moves: ['e4', 'e5', 'Nf3', 'Nc6', 'Bc4', 'Be7', 'd3', 'f5']
  },
  {
    eco: 'C60',
    name: 'Ruy Lopez',
    moves: ['e4', 'e5', 'Nf3', 'Nc6', 'Bb5']
  },
  {
    eco: 'C65',
    name: 'Ruy Lopez: Berlin Defence',
    moves: ['e4', 'e5', 'Nf3', 'Nc6', 'Bb5', 'Nf6']
  },
  {
    eco: 'D00',
    name: 'Queen\'s Pawn Game',
    moves: ['d4']
  },
  {
    eco: 'D02',
    name: 'Queen\'s Pawn Game: London System',
    moves: ['d4', 'Nf6', 'Bf4']
  },
  {
    eco: 'D04',
    name: 'Queen\'s Pawn Game: Colle System',
    moves: ['d4', 'Nf6', 'Nf3', 'e6', 'e3']
  },
  {
    eco: 'D06',
    name: 'Queen\'s Gambit Declined',
    moves: ['d4', 'd5', 'c4']
  },
  {
    eco: 'D20',
    name: 'Queen\'s Gambit Accepted',
    moves: ['d4', 'd5', 'c4', 'dxc4']
  },
  {
    eco: 'E00',
    name: 'Queen\'s Pawn Game: Neo-Indian Attack',
    moves: ['d4', 'Nf6', 'c4', 'e6']
  },
  {
    eco: 'E20',
    name: 'Nimzo-Indian Defence',
    moves: ['d4', 'Nf6', 'c4', 'e6', 'Nc3', 'Bb4']
  },
  {
    eco: 'A00',
    name: 'Uncommon Opening',
    moves: ['a3']
  },
  {
    eco: 'A04',
    name: 'Reti Opening',
    moves: ['Nf3']
  },
  {
    eco: 'A10',
    name: 'English Opening',
    moves: ['c4']
  },
  {
    eco: 'A15',
    name: 'English Opening: Anglo-Indian Defence',
    moves: ['c4', 'Nf6']
  }
];

export function identifyOpening(moves: string[]): OpeningInfo | null {
  if (!moves || moves.length === 0) {
    return null;
  }

  // Find the longest matching opening
  let bestMatch: OpeningInfo | null = null;
  let maxMatchLength = 0;

  for (const opening of OPENING_DATABASE) {
    if (opening.moves.length <= moves.length && opening.moves.length > maxMatchLength) {
      // Check if all opening moves match the game moves
      const matches = opening.moves.every((move, index) => {
        return moves[index] === move;
      });

      if (matches) {
        bestMatch = opening;
        maxMatchLength = opening.moves.length;
      }
    }
  }

  return bestMatch;
}

export enum GamePhase {
  OPENING = 'opening',
  MIDDLEGAME = 'middlegame',
  ENDGAME = 'endgame'
}

export interface GamePhaseInfo {
  phase: GamePhase;
  moveRange: {
    start: number;
    end: number | null; // null means current move
  };
  description: string;
}

export function identifyGamePhase(moveNumber: number, totalMoves: number, materialCount?: number): GamePhase {
  // Simple heuristics for game phase identification
  // In a real implementation, this would be more sophisticated
  
  if (moveNumber <= 15) {
    return GamePhase.OPENING;
  }
  
  // If we have material count information, use it
  if (materialCount !== undefined) {
    // Endgame typically starts when there are fewer pieces on the board
    if (materialCount <= 20) { // Rough threshold
      return GamePhase.ENDGAME;
    }
  }
  
  // Simple move-based heuristic
  if (moveNumber > 40 || (totalMoves > 0 && moveNumber > totalMoves * 0.7)) {
    return GamePhase.ENDGAME;
  }
  
  return GamePhase.MIDDLEGAME;
}

export interface KeyMoment {
  moveNumber: number;
  type: 'blunder' | 'brilliant' | 'tactical_shot' | 'endgame_technique' | 'opening_novelty';
  description: string;
  significance: number; // 1-10 scale
  evaluationChange?: number; // Change in evaluation (centipawns)
}

export function identifyKeyMoments(
  moves: any[], 
  evaluations?: number[]
): KeyMoment[] {
  const keyMoments: KeyMoment[] = [];
  
  if (!moves || moves.length === 0) {
    return keyMoments;
  }

  // Look for significant evaluation changes if available
  if (evaluations && evaluations.length > 1) {
    for (let i = 1; i < evaluations.length; i++) {
      const evalChange = Math.abs(evaluations[i] - evaluations[i - 1]);
      
      if (evalChange > 200) { // Significant change (2+ pawns)
        const moveNumber = i + 1;
        let type: KeyMoment['type'] = 'tactical_shot';
        let description = 'Significant position change';
        
        if (evalChange > 500) {
          type = 'blunder';
          description = 'Major blunder - significant material or positional loss';
        } else if (evalChange > 300) {
          type = 'tactical_shot';
          description = 'Tactical opportunity seized or missed';
        }
        
        keyMoments.push({
          moveNumber,
          type,
          description,
          significance: Math.min(10, Math.floor(evalChange / 100)),
          evaluationChange: evaluations[i] - evaluations[i - 1]
        });
      }
    }
  }

  // Look for moves with quality indicators
  moves.forEach((move, index) => {
    if (move.move_quality_score !== null && move.move_quality_score !== undefined) {
      const moveNumber = index + 1;
      
      if (move.blunder_flag) {
        keyMoments.push({
          moveNumber,
          type: 'blunder',
          description: 'Blunder detected by analysis',
          significance: 8,
          evaluationChange: move.move_quality_score
        });
      } else if (move.move_quality_score > 1.5) {
        keyMoments.push({
          moveNumber,
          type: 'brilliant',
          description: 'Excellent move with high quality score',
          significance: 7
        });
      }
    }
  });

  // Sort by move number and limit to most significant
  return keyMoments
    .sort((a, b) => a.moveNumber - b.moveNumber)
    .slice(0, 10); // Limit to top 10 key moments
}

export interface PlayerOpeningStats {
  playerId: string;
  openings: {
    [eco: string]: {
      name: string;
      gamesPlayed: number;
      wins: number;
      losses: number;
      draws: number;
      winRate: number;
      averageLength: number;
    };
  };
  mostPlayedOpening: string | null;
  bestPerformingOpening: string | null;
  repertoireSize: number;
}

// This would typically be calculated from actual game data
export function calculatePlayerOpeningStats(
  playerId: string, 
  games: any[]
): PlayerOpeningStats {
  const stats: PlayerOpeningStats = {
    playerId,
    openings: {},
    mostPlayedOpening: null,
    bestPerformingOpening: null,
    repertoireSize: 0
  };

  // In a real implementation, this would analyze all games for the player
  // For now, return a placeholder
  return stats;
}