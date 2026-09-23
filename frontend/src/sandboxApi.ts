export type ZoneId = 'transport' | 'air' | 'education';
export type UpgradeId = 'bus' | 'signals' | 'park' | 'filter' | 'school';
export interface Zone {id: ZoneId; name: string; value: number; description: string}
export interface Upgrade {id: UpgradeId; name: string; description: string; cost: number; zone_id: ZoneId; gain: number}
export interface SandboxCatalog {city_name: string; starting_budget: number; quarterly_income: number; max_turns: number; critical_threshold: number; target_value: number; improvements: Upgrade[]}
export interface SandboxState {city_name: string; quarter: number; budget: number; score: number; zones: Zone[]; built: UpgradeId[]; turns: UpgradeId[][]; status: 'playing' | 'won' | 'finished'; last_changes: {zone_id: ZoneId; before: number; after: number}[]; last_income: number}
async function request<T>(path: string, body?: unknown, signal?: AbortSignal): Promise<T> {
  const response = await fetch(`/api/v1/sandbox/${path}`, {method: body === undefined ? 'GET' : 'POST', headers: {'Content-Type':'application/json'}, body: body === undefined ? undefined : JSON.stringify(body), signal});
  const payload = await response.json().catch(() => null);
  if (!response.ok || !payload) throw new Error(payload?.error?.message ?? 'Нет связи с API города. Запусти Python backend и нажми «Повторить».');
  return payload;
}
export const sandboxApi = {
  catalog: (signal?: AbortSignal) => request<SandboxCatalog>('catalog', undefined, signal),
  simulate: (turns: UpgradeId[][], signal?: AbortSignal) => request<SandboxState>('simulate', {turns}, signal),
};
export async function loadSandbox(turns: UpgradeId[][], signal?: AbortSignal): Promise<{catalog: SandboxCatalog; city: SandboxState}> {
  const [catalog, city] = await Promise.all([sandboxApi.catalog(signal), sandboxApi.simulate(turns, signal)]);
  return {catalog, city};
}
