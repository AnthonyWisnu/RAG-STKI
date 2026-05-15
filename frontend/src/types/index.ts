export type RetrievalStrategy =
  | "kg_only"
  | "vector_only"
  | "hybrid"
  | "valuation_reasoning"
  | string;

export type Citation = {
  source?: string;
  label?: string;
  content?: string;
  metadata?: Record<string, string | number | boolean | null>;
  [key: string]: unknown;
};

export type HealthResponse = {
  status: string;
  last_refresh: string | null;
  data_freshness_badge: string;
  stats_records: number;
  valuation_records: number;
  mapped_players: number;
};

export type RefreshStatus = {
  status: "idle" | "running" | "completed" | "skipped" | "failed" | string;
  mode?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
  failed_at?: string | null;
  error?: string | null;
  skipped_reason?: string | null;
  last_refresh?: string | null;
  last_manual_refresh?: string | null;
  stats_records?: number | null;
  valuation_records?: number | null;
  mapped_players?: number | null;
};

export type RefreshStartResponse = {
  accepted: boolean;
  message: string;
  status: RefreshStatus;
};

export type ChatRequest = {
  question: string;
  use_llm_planner?: boolean;
  use_llm_valuation?: boolean;
};

export type ChatResponse = {
  answer: string;
  strategy_used: RetrievalStrategy;
  language: string;
  data_available: boolean;
  citations: Citation[];
  context: {
    kg_rows?: unknown[];
    vector_documents?: unknown[];
    valuation?: unknown;
    debug?: Record<string, unknown>;
  };
  fallback_signal?: string | null;
};

export type PlayerSummary = {
  player_id: number;
  name: string;
  position?: string | null;
  club?: string | null;
  league?: string | null;
  season?: string | null;
  goals?: number | null;
  assists?: number | null;
  minutes?: number | null;
  market_value_eur?: number | null;
  photo_url?: string | null;
};

export type PlayerSearchResponse = {
  items: PlayerSummary[];
  page: number;
  page_size: number;
  total: number;
  has_next: boolean;
};

export type PlayerSearchParams = {
  q?: string;
  position?: string;
  league?: string;
  season?: string;
  sort?: "name" | "goals" | "assists" | "minutes" | "market_value";
  page?: number;
  page_size?: number;
};

export type CompareRequest = {
  player_ids?: number[];
  player_names?: string[];
  season?: string;
};

export type ComparePlayerRow = {
  player_id: number;
  player: string;
  latest?: {
    season?: string;
    club?: string;
    league?: string;
    minutes?: number | null;
    goals?: number | null;
    assists?: number | null;
    shots_total?: number | null;
    saves?: number | null;
    clean_sheets?: number | null;
  };
};

export type RadarMetricRow = {
  player_id: number;
  player: string;
  goals?: number | null;
  assists?: number | null;
  minutes?: number | null;
  shots_total?: number | null;
  saves?: number | null;
  clean_sheets?: number | null;
};

export type CompareResponse = {
  players: ComparePlayerRow[];
  radar_data: RadarMetricRow[];
  narrative: string;
  citations: Citation[];
};

export type SearchFilterState = {
  q: string;
  position: string;
  league: string;
  season: string;
  sort: PlayerSearchParams["sort"];
  page: number;
  minMinutes: string;
  minValue: string;
  maxValue: string;
  minGoals: string;
  minAssists: string;
};

export type ValuationRow = {
  player?: string;
  market_value_eur: number;
  valuation_date: string;
  source?: string;
};

export type ValuationHistoryResponse = {
  player_id: number;
  player: string;
  valuations: ValuationRow[];
  trend_narrative: string;
};

export type PlayerDetailResponse = {
  player: PlayerSummary & {
    birth_date?: string | null;
    height_cm?: number | null;
    preferred_foot?: string | null;
    nationality?: string | null;
  };
  stats_by_season: Array<Record<string, string | number | null>>;
  valuation_history: ValuationRow[];
};

export type PredictRequest = {
  player_name: string;
  language?: "id" | "en";
  use_llm?: boolean;
};

export type SupportingFactor = {
  factor: string;
  impact?: "positive" | "neutral" | "negative" | string;
  citation_ids?: string[];
};

export type PredictResponse = {
  player: PlayerSummary & {
    birth_date?: string | null;
    height_cm?: number | null;
    preferred_foot?: string | null;
    nationality?: string | null;
  };
  current_value: {
    eur: number;
    label: string;
    date?: string;
  } | null;
  estimated_range: {
    low_eur: number;
    high_eur: number;
    label: string;
  } | null;
  trend_direction: string;
  supporting_factors: SupportingFactor[];
  explanation: string;
  citations: Citation[];
  raw: Record<string, unknown>;
};

export type TopCategory = "goals" | "assists" | "saves" | "clean_sheets" | "minutes";

export type TopPerformerRow = {
  player: string;
  club: string;
  league: string;
  season: string;
  position?: string | null;
  value: number;
  goals?: number | null;
  assists?: number | null;
  minutes?: number | null;
};

export type TopPerformersResponse = {
  category: TopCategory;
  season: string;
  league: string | null;
  items: TopPerformerRow[];
  citations: Citation[];
};

export type ClubSearchItem = {
  club_id: number;
  name: string;
  country?: string | null;
  league?: string | null;
  squad_count: number;
};

export type ClubSearchResponse = {
  items: ClubSearchItem[];
  total: number;
};

export type ClubSquadPlayer = {
  player_id: number;
  name: string;
  position?: string | null;
  minutes?: number | null;
  goals?: number | null;
  assists?: number | null;
  market_value_eur?: number | null;
};

export type ClubDetailResponse = {
  club: {
    club_id: number;
    name: string;
    country?: string | null;
    founded_year?: number | null;
  };
  squad: ClubSquadPlayer[];
  top_scorers: ClubSquadPlayer[];
  total_squad_value: number;
};
