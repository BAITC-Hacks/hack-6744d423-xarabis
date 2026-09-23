export type UUID = string;
export type DistrictId = "esil" | "almaty" | "saryarka" | "baikonur" | "nura";
export type IndicatorId = "T1" | "T2" | "E1" | "E2" | "S1" | "S2" | "B1" | "B2" | "C1" | "C2";
export type Direction = "transport" | "ecology" | "social" | "safety" | "services";

export interface CatalogMetadata {
  dataset_version: string;
  formula_version: string;
  budget: number;
  horizon_quarters: number;
  required_decisions: number;
  critical_threshold: number;
}

export interface Indicator {
  id: IndicatorId;
  direction: Direction;
  name: string;
  weight: number;
}

export interface ApiDistrict {
  id: DistrictId;
  name: string;
  population_share: number;
  profile: string;
  indicators: Record<IndicatorId, number>;
}

export interface ApiMeasure {
  id: string;
  direction: Direction;
  name: string;
  scope: "district" | "city";
  cost: number;
  lag_quarters: number;
  effects: Partial<Record<IndicatorId, number>>;
}

export interface ApiDecision {
  measure_id: string;
  district_id: DistrictId | null;
}

export interface DraftValidation {
  valid: true;
  decision_count: number;
  total_cost: number;
  remaining_budget: number;
  ready_for_calculation: boolean;
}

export interface Scenario {
  id: UUID;
  status: "draft" | "calculated" | "completed";
  version: number;
  budget_limit: number;
  decisions: ApiDecision[];
  created_at: string;
  updated_at: string;
}

export interface ScenarioPage {
  items: Scenario[];
  total: number;
  limit: number;
  offset: number;
}

export interface ConsultantBlock {
  title: string;
  explanation: string;
}

export interface ConsultantResponse {
  answer: string;
  strengths: ConsultantBlock[];
  risks: ConsultantBlock[];
  consequences: ConsultantBlock[];
  recommendations: ConsultantBlock[];
  follow_up_question: string | null;
}

export interface ChatMessage {
  id: UUID;
  scenario_id: UUID;
  sequence: number;
  role: "user" | "assistant";
  content: string;
  report: ConsultantResponse | null;
  created_at: string;
}

export interface CriticalIndicator {
  district_id: DistrictId;
  indicator_id: IndicatorId;
  value: number;
}

export interface AppliedEffect {
  measure_ids: string[];
  district_id: DistrictId;
  indicator_id: IndicatorId;
  delta: number;
  kind: "direct" | "synergy";
}

export interface DistrictResult {
  district_id: DistrictId;
  score_before: number;
  score_after: number;
  indicators_before: Record<IndicatorId, number>;
  indicators_after: Record<IndicatorId, number>;
}

export interface SimulationResult {
  dataset_version: string;
  formula_version: string;
  total_cost: number;
  remaining_budget: number;
  score_before: number;
  score_after: number;
  score_delta: number;
  city_average: number;
  weakest_district_score: number;
  districts: DistrictResult[];
  critical_before: CriticalIndicator[];
  critical_after: CriticalIndicator[];
  effects: AppliedEffect[];
}

export interface StoredSimulationResult {
  id: UUID;
  scenario_id: UUID;
  scenario_version: number;
  created_at: string;
  simulation: SimulationResult;
}

export class ApiRequestError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string,
    message: string,
    public readonly details?: unknown,
  ) {
    super(message);
  }
}

const API_BASE = "/api/v1";

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      Accept: "application/json",
      ...(init.body ? { "Content-Type": "application/json" } : {}),
      ...init.headers,
    },
  });
  const payload: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const body = payload as { error?: { code?: string; message?: string; details?: unknown } } | null;
    throw new ApiRequestError(response.status, body?.error?.code ?? "unknown_error", body?.error?.message ?? `Ошибка API (${response.status})`, body?.error?.details);
  }
  if (response.status === 204) return undefined as T;
  if (payload === null) throw new ApiRequestError(response.status, "invalid_response", "Сервер вернул ответ не в формате JSON");
  return payload as T;
}

export const cityApi = {
  getCatalog: () => request<CatalogMetadata>("/catalog"),
  getIndicators: () => request<Indicator[]>("/indicators"),
  getDistricts: () => request<ApiDistrict[]>("/districts"),
  getMeasures: () => request<ApiMeasure[]>("/measures"),
  createScenario: () => request<Scenario>("/scenarios", { method: "POST" }),
  listScenarios: (limit = 20, offset = 0) => request<ScenarioPage>(`/scenarios?limit=${limit}&offset=${offset}`),
  getScenario: (id: UUID) => request<Scenario>(`/scenarios/${encodeURIComponent(id)}`),
  validate: (decisions: ApiDecision[], signal?: AbortSignal) => request<DraftValidation>("/scenarios/validate", { method: "POST", body: JSON.stringify({ decisions }), signal }),
  replaceDecisions: (id: UUID, version: number, decisions: ApiDecision[]) => request<Scenario>(`/scenarios/${encodeURIComponent(id)}/decisions`, { method: "PUT", body: JSON.stringify({ expected_version: version, decisions }) }),
  calculate: (id: UUID, version: number) => request<StoredSimulationResult>(`/scenarios/${encodeURIComponent(id)}/calculate`, { method: "POST", body: JSON.stringify({ expected_version: version }) }),
  getCurrentResult: (id: UUID) => request<StoredSimulationResult>(`/scenarios/${encodeURIComponent(id)}/result`),
  getResults: (id: UUID) => request<StoredSimulationResult[]>(`/scenarios/${encodeURIComponent(id)}/results`),
  resetScenario: (id: UUID, version: number) => request<Scenario>(`/scenarios/${encodeURIComponent(id)}/reset`, { method: "POST", body: JSON.stringify({ expected_version: version }) }),
  deleteScenario: (id: UUID, version: number) => request<void>(`/scenarios/${encodeURIComponent(id)}?expected_version=${version}`, { method: "DELETE" }),
  sendChatMessage: (id: UUID, message: string, signal?: AbortSignal) => request<ConsultantResponse>(`/scenarios/${encodeURIComponent(id)}/chat/messages`, { method: "POST", body: JSON.stringify({ message }), signal }),
  getChatMessages: (id: UUID, signal?: AbortSignal) => request<ChatMessage[]>(`/scenarios/${encodeURIComponent(id)}/chat/messages`, { signal }),
};
