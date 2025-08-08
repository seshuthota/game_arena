// API Response Types based on backend Pydantic models

export interface BaseResponse {
  success: boolean;
  timestamp: string;
}

export interface PaginationMeta {
  page: number;
  limit: number;
  total_count: number;
  total_pages: number;
  has_next: boolean;
  has_previous: boolean;
}

export interface ErrorResponse {
  success: false;
  error: string;
  detail: string;
  error_code: string;
  timestamp: string;
}

// Enums
export enum GameResult {
  WHITE_WINS = 'white_wins',
  BLACK_WINS = 'black_wins',
  DRAW = 'draw',
  ONGOING = 'ongoing',
}

export enum TerminationReason {
  CHECKMATE = 'checkmate',
  STALEMATE = 'stalemate',
  INSUFFICIENT_MATERIAL = 'insufficient_material',
  THREEFOLD_REPETITION = 'threefold_repetition',
  FIFTY_MOVE_RULE = 'fifty_move_rule',
  TIME_FORFEIT = 'time_forfeit',
  RESIGNATION = 'resignation',
  AGREEMENT = 'agreement',
  ABANDONED = 'abandoned',
}

export enum SortOptions {
  START_TIME_ASC = 'start_time_asc',
  START_TIME_DESC = 'start_time_desc',
  DURATION_ASC = 'duration_asc',
  DURATION_DESC = 'duration_desc',
  MOVES_ASC = 'moves_asc',
  MOVES_DESC = 'moves_desc',
  WIN_RATE_ASC = 'win_rate_asc',
  WIN_RATE_DESC = 'win_rate_desc',
  GAMES_PLAYED_ASC = 'games_played_asc',
  GAMES_PLAYED_DESC = 'games_played_desc',
  ELO_RATING_ASC = 'elo_rating_asc',
  ELO_RATING_DESC = 'elo_rating_desc',
}

// Player Models
export interface PlayerInfo {
  player_id: string;
  model_name: string;
  model_provider: string;
  agent_type: string;
  elo_rating: number | null;
}

export interface PlayerRanking {
  player_id: string;
  model_name: string;
  rank: number;
  games_played: number;
  wins: number;
  losses: number;
  draws: number;
  win_rate: number;
  average_game_length: number;
  elo_rating: number;
}

export interface PlayerStatistics {
  player_id: string;
  model_name: string;
  total_games: number;
  wins: number;
  losses: number;
  draws: number;
  win_rate: number;
  average_game_duration: number;
  total_moves: number;
  legal_moves: number;
  illegal_moves: number;
  move_accuracy: number;
  parsing_success_rate: number;
  average_thinking_time: number;
  blunders: number;
  elo_rating: number;
}

// Game Models
export interface GameOutcome {
  result: GameResult;
  winner: number | null;
  termination: TerminationReason;
  termination_details: string | null;
}

export interface GameSummary {
  game_id: string;
  tournament_id: string | null;
  start_time: string;
  end_time: string | null;
  players: Record<string, PlayerInfo>;
  outcome: GameOutcome | null;
  total_moves: number;
  duration_minutes: number | null;
  is_completed: boolean;
}

export interface MoveRecord {
  move_number: number;
  player: number;
  move_notation: string;
  fen_before: string;
  fen_after: string;
  is_legal: boolean;
  parsing_success: boolean;
  thinking_time_ms: number;
  api_call_time_ms: number;
  total_time_ms: number;
  had_rethink: boolean;
  rethink_attempts: number;
  blunder_flag: boolean;
  move_quality_score: number | null;
  llm_response: string | null;
}

export interface GameDetail {
  game_id: string;
  tournament_id: string | null;
  start_time: string;
  end_time: string | null;
  players: Record<string, PlayerInfo>;
  outcome: GameOutcome | null;
  total_moves: number;
  duration_minutes: number | null;
  is_completed: boolean;
  initial_fen: string;
  final_fen: string | null;
  moves: MoveRecord[];
}

// Statistics Models
export interface OverallStatistics {
  total_games: number;
  completed_games: number;
  ongoing_games: number;
  total_players: number;
  total_moves: number;
  average_game_duration: number;
  average_moves_per_game: number;
  games_by_result: Record<string, number>;
  games_by_termination: Record<string, number>;
  most_active_player: string | null;
  longest_game_id: string | null;
  shortest_game_id: string | null;
}

export interface TimeSeriesDataPoint {
  timestamp: string;
  value: number;
  count: number | null;
}

export interface TimeSeriesData {
  metric: string;
  interval: string;
  data_points: TimeSeriesDataPoint[];
  total_count: number;
}

// API Response Models
export interface GameListResponse extends BaseResponse {
  games: GameSummary[];
  pagination: PaginationMeta;
  filters_applied: Record<string, any>;
}

export interface GameDetailResponse extends BaseResponse {
  game: GameDetail;
  moves: MoveRecord[];
}

export interface StatisticsOverviewResponse extends BaseResponse {
  statistics: OverallStatistics;
  filters_applied: Record<string, any>;
}

export interface TimeSeriesResponse extends BaseResponse {
  time_series: TimeSeriesData;
  filters_applied: Record<string, any>;
}

export interface LeaderboardResponse extends BaseResponse {
  players: PlayerRanking[];
  pagination: PaginationMeta;
  sort_by: string;
  filters_applied: Record<string, any>;
}

export interface PlayerStatisticsResponse extends BaseResponse {
  statistics: PlayerStatistics;
}

export interface SearchResponse extends BaseResponse {
  results: (GameSummary | PlayerInfo)[];
  query: string;
  result_count: number;
  search_type: string;
}

// Request Filter Types
export interface GameFilters {
  player_ids?: string[];
  model_names?: string[];
  model_providers?: string[];
  tournament_ids?: string[];
  start_date?: string;
  end_date?: string;
  results?: GameResult[];
  termination_reasons?: TerminationReason[];
  min_moves?: number;
  max_moves?: number;
  min_duration?: number;
  max_duration?: number;
  completed_only?: boolean;
}

export interface SearchFilters {
  query: string;
  search_fields?: string[];
  limit?: number;
}

// API Query Parameters
export interface GameListParams extends GameFilters {
  page?: number;
  limit?: number;
  sort_by?: SortOptions;
  search?: string;
}

export interface LeaderboardParams {
  page?: number;
  limit?: number;
  sort_by?: SortOptions;
  player_ids?: string;
  model_names?: string;
  model_providers?: string;
  min_games?: number;
}

export interface TimeSeriesParams {
  metric: string;
  interval: string;
  start_date?: string;
  end_date?: string;
  days?: number;
}