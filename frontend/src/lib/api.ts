import type {
  ChatRequest,
  ChatResponse,
  ClubDetailResponse,
  ClubSearchResponse,
  CompareRequest,
  CompareResponse,
  HealthResponse,
  PlayerDetailResponse,
  PlayerSearchParams,
  PlayerSearchResponse,
  PredictRequest,
  PredictResponse,
  RefreshStartResponse,
  RefreshStatus,
  TopCategory,
  TopPerformersResponse,
  ValuationHistoryResponse
} from "@/types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {})
    }
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Request gagal dengan status ${response.status}`);
  }

  return (await response.json()) as T;
}

export async function getHealth(): Promise<HealthResponse> {
  return request<HealthResponse>("/api/health");
}

export async function getRefreshStatus(): Promise<RefreshStatus> {
  return request<RefreshStatus>("/api/refresh/status");
}

export async function startRefresh(): Promise<RefreshStartResponse> {
  return request<RefreshStartResponse>("/api/refresh/start", {
    method: "POST",
    body: JSON.stringify({ mode: "all", force: false, dry_run: false })
  });
}

export async function sendChatMessage(payload: ChatRequest): Promise<ChatResponse> {
  return request<ChatResponse>("/api/chat", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function searchPlayers(paramsInput: string | PlayerSearchParams): Promise<PlayerSearchResponse> {
  const normalized =
    typeof paramsInput === "string"
      ? { q: paramsInput, page_size: 8 }
      : paramsInput;
  const params = new URLSearchParams();
  Object.entries(normalized).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      params.set(key, String(value));
    }
  });
  return request<PlayerSearchResponse>(`/api/players/search?${params.toString()}`);
}

export async function comparePlayers(payload: CompareRequest): Promise<CompareResponse> {
  return request<CompareResponse>("/api/compare", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function getPlayerDetail(playerId: number): Promise<PlayerDetailResponse> {
  return request<PlayerDetailResponse>(`/api/players/${playerId}`);
}

export async function getValuationHistory(playerId: number): Promise<ValuationHistoryResponse> {
  return request<ValuationHistoryResponse>(`/api/players/${playerId}/valuation-history`);
}

export async function predictValuation(payload: PredictRequest): Promise<PredictResponse> {
  return request<PredictResponse>("/api/predict", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function getTopPerformers(paramsInput: {
  category: TopCategory;
  season: string;
  league?: string;
  position?: string;
  limit?: number;
}): Promise<TopPerformersResponse> {
  const params = new URLSearchParams({
    category: paramsInput.category,
    season: paramsInput.season,
    limit: String(paramsInput.limit ?? 20)
  });
  if (paramsInput.league) {
    params.set("league", paramsInput.league);
  }
  if (paramsInput.position) {
    params.set("position", paramsInput.position);
  }
  return request<TopPerformersResponse>(`/api/top-performers?${params.toString()}`);
}

export async function searchClubs(query: string, season = "2025-2026"): Promise<ClubSearchResponse> {
  const params = new URLSearchParams({
    q: query,
    season,
    limit: "12"
  });
  return request<ClubSearchResponse>(`/api/clubs/search?${params.toString()}`);
}

export async function getClubDetail(
  clubId: number,
  season = "2025-2026"
): Promise<ClubDetailResponse> {
  const params = new URLSearchParams({ season });
  return request<ClubDetailResponse>(`/api/clubs/${clubId}?${params.toString()}`);
}
