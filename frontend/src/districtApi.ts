export type DistrictId = 'esil' | 'almaty' | 'saryarka' | 'baikonur' | 'nura';
export type IndicatorId = 'transport' | 'air' | 'education';
export type ProjectId = 'bus' | 'signals' | 'park' | 'filter' | 'school' | 'repair';
export interface DistrictDecision {district_id: DistrictId; improvement_id: ProjectId}
export interface DistrictState {id: DistrictId; name: string; description: string; score: number; values: Record<IndicatorId, number>; built: ProjectId[]}
export interface DistrictProject {id: ProjectId; name: string; description: string; cost: number; zone_id: IndicatorId; gain: number}
export interface DistrictCatalog {rules_version: 'districts-v2'; city_name: string; starting_budget:number; quarterly_income:number; max_turns:number; critical_threshold:number; target_value:number; improvements:DistrictProject[]}
export interface DistrictGame {rules_version:'districts-v2'; city_name:string; quarter:number; budget:number; score:number; districts:DistrictState[]; turns:DistrictDecision[][]; status:'playing'|'won'|'finished'; last_changes:{district_id:DistrictId;indicator_id:IndicatorId;before:number;after:number}[];last_income:number}
async function request<T>(path: string, body?: unknown, signal?: AbortSignal): Promise<T> {
  const response = await fetch(`/api/v1/sandbox/v2/${path}`, {method:body === undefined?'GET':'POST', headers:{'Content-Type':'application/json'},body:body === undefined?undefined:JSON.stringify(body),signal});
  const data = await response.json().catch(()=>null);
  if (!response.ok || !data) throw new Error(data?.error?.message ?? 'Не удалось загрузить районы. Проверь Python API и повтори.');
  return data;
}
export const districtApi = {
  catalog: (signal?:AbortSignal)=>request<DistrictCatalog>('catalog',undefined,signal),
  simulate: (turns:DistrictDecision[][],signal?:AbortSignal)=>request<DistrictGame>('simulate',{turns},signal),
};
export async function loadDistrictGame(turns:DistrictDecision[][],signal?:AbortSignal) {
  const [catalog,city]=await Promise.all([districtApi.catalog(signal),districtApi.simulate(turns,signal)]);
  return {catalog,city};
}
