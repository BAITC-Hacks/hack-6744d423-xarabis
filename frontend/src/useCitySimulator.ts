import { useEffect, useMemo, useRef, useState } from "react";
import type { Decision } from "./caseData";
import {
  ApiRequestError,
  cityApi,
  type ApiDecision,
  type ApiDistrict,
  type ApiMeasure,
  type CatalogMetadata,
  type DraftValidation,
  type Indicator,
  type Scenario,
  type StoredSimulationResult,
} from "./cityApi";

const SCENARIO_KEY = "akim.currentScenarioId";
const DRAFT_KEY = "akim.pendingDraft";

type Bootstrap = {
  catalog: CatalogMetadata;
  indicators: Indicator[];
  districts: ApiDistrict[];
  measures: ApiMeasure[];
  scenario: Scenario;
  decisions: Decision[];
  result: StoredSimulationResult | null;
  history: StoredSimulationResult[];
  scenarioWasLost: boolean;
};

function toApi(decisions: Decision[]): ApiDecision[] {
  return decisions.map((decision) => ({ measure_id: decision.measureId, district_id: decision.districtId ?? null }));
}

function fromApi(decisions: ApiDecision[]): Decision[] {
  return decisions.map((decision) => ({ measureId: decision.measure_id, ...(decision.district_id ? { districtId: decision.district_id } : {}) }));
}

function sameDecisions(local: Decision[], saved: ApiDecision[]) {
  const canonical = (items: ApiDecision[]) => JSON.stringify([...items].sort((a, b) => a.measure_id.localeCompare(b.measure_id)));
  return canonical(toApi(local)) === canonical(saved);
}

function readPendingDraft(scenario: Scenario): Decision[] | null {
  try {
    const raw = window.localStorage.getItem(DRAFT_KEY);
    if (!raw) return null;
    const pending = JSON.parse(raw) as { scenarioId: string; version: number; decisions: ApiDecision[] };
    if (pending.scenarioId !== scenario.id || pending.version !== scenario.version || !Array.isArray(pending.decisions)) return null;
    return fromApi(pending.decisions);
  } catch {
    return null;
  }
}

async function optionalResult(id: string) {
  try {
    return await cityApi.getCurrentResult(id);
  } catch (error) {
    if (error instanceof ApiRequestError && error.status === 404 && error.code === "result_not_found") return null;
    throw error;
  }
}

async function bootstrap(): Promise<Bootstrap> {
  const [catalog, indicators, districts, measures] = await Promise.all([
    cityApi.getCatalog(), cityApi.getIndicators(), cityApi.getDistricts(), cityApi.getMeasures(),
  ]);
  const savedId = window.localStorage.getItem(SCENARIO_KEY);
  let scenario: Scenario;
  let scenarioWasLost = false;
  if (savedId) {
    try {
      scenario = await cityApi.getScenario(savedId);
    } catch (error) {
      if (!(error instanceof ApiRequestError && error.status === 404 && error.code === "scenario_not_found")) throw error;
      window.localStorage.removeItem(SCENARIO_KEY);
      window.localStorage.removeItem(DRAFT_KEY);
      scenario = await cityApi.createScenario();
      scenarioWasLost = true;
    }
  } else {
    scenario = await cityApi.createScenario();
  }
  window.localStorage.setItem(SCENARIO_KEY, scenario.id);
  const [result, history] = await Promise.all([
    optionalResult(scenario.id),
    cityApi.getResults(scenario.id).catch(() => [] as StoredSimulationResult[]),
  ]);
  return {
    catalog, indicators, districts, measures, scenario,
    decisions: readPendingDraft(scenario) ?? fromApi(scenario.decisions),
    result, history, scenarioWasLost,
  };
}

function describeError(error: unknown): string[] {
  if (error instanceof ApiRequestError) {
    if (error.code === "scenario_validation_error" && Array.isArray(error.details)) return error.details.map(String);
    if (error.code === "invalid_request") {
      console.error("Некорректный запрос к City Simulator API", error.details);
      return ["Некорректный запрос к серверу. Обнови страницу или сообщи команде."];
    }
    return [error.message];
  }
  return ["Не удалось связаться с сервером. Проверь подключение и повтори действие."];
}

export function useCitySimulator() {
  const [mode, setMode] = useState<"loading" | "live" | "demo">("loading");
  const [retryKey, setRetryKey] = useState(0);
  const bootstrapRef = useRef<Promise<Bootstrap> | null>(null);
  const [catalog, setCatalog] = useState<CatalogMetadata | null>(null);
  const [indicators, setIndicators] = useState<Indicator[]>([]);
  const [districts, setDistricts] = useState<ApiDistrict[]>([]);
  const [measures, setMeasures] = useState<ApiMeasure[]>([]);
  const [scenario, setScenario] = useState<Scenario | null>(null);
  const [decisions, setDecisions] = useState<Decision[]>([]);
  const [validation, setValidation] = useState<DraftValidation | null>(null);
  const [isValidating, setIsValidating] = useState(false);
  const [result, setResult] = useState<StoredSimulationResult | null>(null);
  const [history, setHistory] = useState<StoredSimulationResult[]>([]);
  const [busy, setBusy] = useState<"saving" | "calculating" | null>(null);
  const [issues, setIssues] = useState<string[]>([]);
  const [failedAction, setFailedAction] = useState<"save" | "calculate" | null>(null);
  const [connectionError, setConnectionError] = useState("");
  const [statusMessage, setStatusMessage] = useState("");

  useEffect(() => {
    let active = true;
    bootstrapRef.current ??= bootstrap();
    bootstrapRef.current.then((loaded) => {
      if (!active) return;
      setCatalog(loaded.catalog);
      setIndicators(loaded.indicators);
      setDistricts(loaded.districts);
      setMeasures(loaded.measures);
      setScenario(loaded.scenario);
      setDecisions(loaded.decisions);
      setResult(loaded.result);
      setHistory(loaded.history);
      setConnectionError("");
      setStatusMessage(loaded.scenarioWasLost ? "Прежний черновик недоступен. Создан новый сценарий." : "");
      setMode("live");
    }).catch((error) => {
      if (!active) return;
      setConnectionError(describeError(error)[0]);
      setMode("demo");
    });
    return () => { active = false; };
  }, [retryKey]);

  const hasUnsavedChanges = useMemo(() => scenario ? !sameDecisions(decisions, scenario.decisions) : false, [decisions, scenario]);

  useEffect(() => {
    if (mode !== "live" || !scenario) return;
    try {
      if (hasUnsavedChanges) {
        window.localStorage.setItem(DRAFT_KEY, JSON.stringify({ scenarioId: scenario.id, version: scenario.version, decisions: toApi(decisions) }));
      } else {
        window.localStorage.removeItem(DRAFT_KEY);
      }
    } catch {
      // The draft remains in memory when browser storage is unavailable.
    }
  }, [mode, scenario, decisions, hasUnsavedChanges]);

  useEffect(() => {
    if (mode !== "live" || !scenario) return;
    const controller = new AbortController();
    setValidation(null);
    setIsValidating(true);
    const timeout = window.setTimeout(() => {
      cityApi.validate(toApi(decisions), controller.signal).then((next) => {
        setValidation(next);
        setIssues([]);
      }).catch((error) => {
        if (controller.signal.aborted) return;
        setValidation(null);
        setIssues(describeError(error));
      }).finally(() => { if (!controller.signal.aborted) setIsValidating(false); });
    }, 320);
    return () => { window.clearTimeout(timeout); controller.abort(); };
  }, [mode, scenario?.id, decisions]);

  function updateDecisions(next: Decision[]) {
    setDecisions(next);
    setValidation(null);
    setIssues([]);
    setResult(null);
    setStatusMessage("");
    setFailedAction(null);
  }

  async function recoverConflict() {
    if (!scenario) return;
    const fresh = await cityApi.getScenario(scenario.id);
    setScenario(fresh);
    setDecisions(fromApi(fresh.decisions));
    setResult(await optionalResult(fresh.id));
    setHistory(await cityApi.getResults(fresh.id).catch(() => [] as StoredSimulationResult[]));
    setIssues(["Сценарий изменился в другом окне. Загружена актуальная версия; проверь план перед повтором."]);
  }

  async function recoverMissingScenario() {
    window.localStorage.removeItem(SCENARIO_KEY);
    window.localStorage.removeItem(DRAFT_KEY);
    const fresh = await cityApi.createScenario();
    window.localStorage.setItem(SCENARIO_KEY, fresh.id);
    setScenario(fresh);
    setResult(null);
    setHistory([]);
    setIssues(["Прежний сценарий недоступен. Создан новый; текущий выбор остался черновиком."]);
  }

  async function saveDraft() {
    if (mode !== "live" || !scenario || !validation || !hasUnsavedChanges || busy) return false;
    setBusy("saving");
    setIssues([]);
    setFailedAction(null);
    try {
      const saved = await cityApi.replaceDecisions(scenario.id, scenario.version, toApi(decisions));
      setScenario(saved);
      setResult(null);
      setStatusMessage("План сохранён. Версия сценария обновлена.");
      return true;
    } catch (error) {
      if (error instanceof ApiRequestError && error.code === "scenario_version_conflict") await recoverConflict();
      else if (error instanceof ApiRequestError && error.code === "scenario_not_found") await recoverMissingScenario();
      else {
        setIssues(describeError(error));
        if (!(error instanceof ApiRequestError) || error.status >= 500) setFailedAction("save");
      }
      return false;
    } finally {
      setBusy(null);
    }
  }

  async function calculate() {
    if (mode !== "live" || !scenario || !validation?.ready_for_calculation || hasUnsavedChanges || busy) return false;
    setBusy("calculating");
    setIssues([]);
    setFailedAction(null);
    try {
      const calculated = await cityApi.calculate(scenario.id, scenario.version);
      setResult(calculated);
      setScenario({ ...scenario, status: "calculated" });
      setHistory(await cityApi.getResults(scenario.id).catch(() => [calculated]));
      setStatusMessage("Расчёт готов. Показаны результаты сервера.");
      return true;
    } catch (error) {
      if (error instanceof ApiRequestError && error.code === "scenario_version_conflict") await recoverConflict();
      else if (error instanceof ApiRequestError && error.code === "scenario_not_found") await recoverMissingScenario();
      else {
        setIssues(describeError(error));
        if (!(error instanceof ApiRequestError) || error.status >= 500) setFailedAction("calculate");
      }
      return false;
    } finally {
      setBusy(null);
    }
  }

  function retryConnection() {
    bootstrapRef.current = null;
    setMode("loading");
    setConnectionError("");
    setRetryKey((current) => current + 1);
  }

  return {
    mode, catalog, indicators, districts, measures, scenario, decisions, validation, isValidating,
    result, history, busy, issues, failedAction, connectionError, statusMessage, hasUnsavedChanges,
    updateDecisions, saveDraft, calculate, retryConnection,
  };
}
