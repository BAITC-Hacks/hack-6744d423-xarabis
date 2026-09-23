import { lazy, Suspense, useEffect, useMemo, useState, type CSSProperties } from "react";
import { UnityCityView } from "./UnityCityView";
import { ConsultantPanel } from "./ConsultantPanel";
import { getCityNetworkDemo } from "./cityNetworkDemo";
import { useCitySimulator } from "./useCitySimulator";
import type { SimulationResult } from "./cityApi";
import {
  CATEGORY_META,
  DISTRICTS,
  MEASURES,
  METRICS,
  METRIC_META,
  REFERENCE_DECISIONS,
  REFERENCE_RESULT,
  type CategoryId,
  type Decision,
  type District,
  type DistrictId,
  type Measure,
  type MetricId,
} from "./caseData";

type LayerId = "score" | CategoryId;
type ViewMode = "before" | "after";
type MapMode = "real" | "schematic" | "unity";

const AstanaMap = lazy(() => import("./AstanaMap").then((module) => ({ default: module.AstanaMap })));

const LAYERS: { id: LayerId; label: string }[] = [
  { id: "score", label: "Общий индекс" },
  { id: "transport", label: "Транспорт" },
  { id: "ecology", label: "Экология" },
  { id: "social", label: "Социальная сфера" },
  { id: "safety", label: "Безопасность" },
  { id: "services", label: "Сервисы" },
];

const LAYER_METRIC: Record<CategoryId, MetricId> = {
  transport: "T1",
  ecology: "E2",
  social: "S1",
  safety: "B1",
  services: "C1",
};

function formatScore(value: number | null) {
  if (value === null) return "—";
  return value.toLocaleString("ru-RU", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function formatDelta(value: number) {
  return `${value > 0 ? "+" : ""}${value.toLocaleString("ru-RU", { maximumFractionDigits: 2 })}`;
}

function scoreFor(district: District, result: SimulationResult | null, referenceResult: boolean, view: ViewMode) {
  const districtResult = result?.districts.find((item) => item.district_id === district.id);
  if (districtResult) return view === "after" ? districtResult.score_after : districtResult.score_before;
  if (view === "after" && referenceResult) {
    return REFERENCE_RESULT.districts.find((result) => result.districtId === district.id)!.scoreAfter;
  }
  return district.score;
}

function valuesFor(district: District, result: SimulationResult | null, referenceResult: boolean, view: ViewMode) {
  const districtResult = result?.districts.find((item) => item.district_id === district.id);
  if (districtResult) return view === "after" ? districtResult.indicators_after : districtResult.indicators_before;
  if (view === "after" && referenceResult) {
    return REFERENCE_RESULT.districts.find((result) => result.districtId === district.id)!.after;
  }
  return district.values;
}

function criticalMetricsFor(district: District, result: SimulationResult | null, referenceResult: boolean, view: ViewMode): readonly MetricId[] {
  if (result) return (view === "after" ? result.critical_after : result.critical_before).filter((item) => item.district_id === district.id).map((item) => item.indicator_id);
  if (view === "after" && referenceResult) return REFERENCE_RESULT.districts.find((result) => result.districtId === district.id)!.criticalMetrics as readonly MetricId[];
  return district.criticalMetrics;
}

function tint(value: number) {
  const stops = [
    { at: 0, rgb: [209, 116, 91] },
    { at: 40, rgb: [211, 177, 102] },
    { at: 70, rgb: [146, 175, 132] },
    { at: 100, rgb: [64, 136, 119] },
  ];
  const valueAt = Math.max(0, Math.min(100, value));
  let lower = stops[0];
  let upper = stops[stops.length - 1];
  for (let index = 1; index < stops.length; index += 1) {
    if (valueAt <= stops[index].at) {
      lower = stops[index - 1];
      upper = stops[index];
      break;
    }
  }
  const progress = (valueAt - lower.at) / (upper.at - lower.at);
  const channels = lower.rgb.map((start, index) => Math.round(start + (upper.rgb[index] - start) * progress));
  return `rgb(${channels[0]}, ${channels[1]}, ${channels[2]})`;
}

function Glyph({ name, size = 18 }: { name: "arrow" | "close" | "reset" | "spark" | "layers" | "check" | "city"; size?: number }) {
  const paths = {
    arrow: <><path d="M4.5 12h15" /><path d="m13.5 5 7 7-7 7" /></>,
    close: <><path d="m18 6-12 12" /><path d="m6 6 12 12" /></>,
    reset: <><path d="M3 11a9 9 0 1 1 2.5 6.2" /><path d="M3 4v7h7" /></>,
    spark: <><path d="m12 3 1.7 5.3L19 10l-5.3 1.7L12 17l-1.7-5.3L5 10l5.3-1.7L12 3Z" /><path d="m19 15 1 3 3 1-3 1-1 3-1-3-3-1 3-1 1-3Z" /></>,
    layers: <><path d="m12 3 9 5-9 5-9-5 9-5Z" /><path d="m3 12 9 5 9-5" /><path d="m3 16 9 5 9-5" /></>,
    check: <path d="m5 12 4 4L19 6" />,
    city: <><path d="M3 21h18" /><path d="M5 21V8l7-5v18" /><path d="M12 11h7v10" /><path d="M8 9v.01M8 13v.01M8 17v.01M15 14v.01M18 14v.01M15 17v.01M18 17v.01" /></>,
  };
  return <svg aria-hidden="true" width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">{paths[name]}</svg>;
}

export function App() {
  const simulator = useCitySimulator();
  const [activeDistrict, setActiveDistrict] = useState<DistrictId>("nura");
  const [activeLayer, setActiveLayer] = useState<LayerId>("score");
  const [mapMode, setMapMode] = useState<MapMode>("real");
  const [viewMode, setViewMode] = useState<ViewMode>("before");
  const [showReferenceResult, setShowReferenceResult] = useState(false);
  const [referencePlanLoaded, setReferencePlanLoaded] = useState(false);
  const [filter, setFilter] = useState<CategoryId | "all">("all");
  const [notice, setNotice] = useState("");
  const [showAnalysis, setShowAnalysis] = useState(false);

  const live = simulator.mode === "live";
  const catalog = live ? simulator.catalog : null;
  const requiredDecisions = catalog?.required_decisions ?? 5;
  const budgetLimit = catalog?.budget ?? 100;
  const threshold = catalog?.critical_threshold ?? 40;
  const horizon = catalog?.horizon_quarters ?? 8;
  const decisions = simulator.decisions;
  const result = live ? simulator.result?.simulation ?? null : null;
  const referenceResult = !live && showReferenceResult;
  const hasResult = Boolean(result || referenceResult);
  const cityDistricts = useMemo<District[]>(() => live
    ? simulator.districts.map((district) => {
      const layout = DISTRICTS.find((item) => item.id === district.id);
      const row = result?.districts.find((item) => item.district_id === district.id);
      return {
        id: district.id, name: district.name, profile: district.profile,
        score: row?.score_before ?? null, values: district.indicators,
        x: layout?.x ?? 360, y: layout?.y ?? 240, accent: layout?.accent ?? "#adc8b6",
        criticalMetrics: (Object.keys(district.indicators) as MetricId[]).filter((id) => district.indicators[id] < threshold),
      };
    })
    : DISTRICTS, [live, simulator.districts, result, threshold]);
  const cityMeasures = useMemo<Measure[]>(() => live
    ? simulator.measures.map((measure) => ({
      id: measure.id, name: measure.name, category: measure.direction,
      scope: measure.scope, cost: measure.cost, lag: measure.lag_quarters, effects: measure.effects,
    }))
    : MEASURES, [live, simulator.measures]);
  const metricNames = useMemo(() => live
    ? Object.fromEntries(simulator.indicators.map((indicator) => [indicator.id, indicator.name])) as Record<MetricId, string>
    : Object.fromEntries(METRICS.map((id) => [id, METRIC_META[id].name])) as Record<MetricId, string>, [live, simulator.indicators]);
  const metricIds = live ? simulator.indicators.map((indicator) => indicator.id) : [...METRICS];
  const activeInfo = cityDistricts.find((district) => district.id === activeDistrict) ?? cityDistricts[0];
  const activeValues = valuesFor(activeInfo, result, referenceResult, viewMode);
  const activeBeforeValues = valuesFor(activeInfo, result, referenceResult, "before");
  const activeCriticalMetrics = criticalMetricsFor(activeInfo, result, referenceResult, viewMode);
  const shownScore = result ? (viewMode === "after" ? result.score_after : result.score_before) : referenceResult && viewMode === "after" ? REFERENCE_RESULT.scoreAfter : live ? null : REFERENCE_RESULT.scoreBefore;
  const spent = live ? simulator.validation?.total_cost ?? null : referencePlanLoaded ? 95 : null;
  const budgetPercent = spent === null ? 0 : Math.min(100, (spent / budgetLimit) * 100);

  useEffect(() => {
    if (simulator.statusMessage) setNotice(simulator.statusMessage);
  }, [simulator.statusMessage]);

  useEffect(() => {
    if (live && !simulator.result) {
      setViewMode("before");
      setShowAnalysis(false);
    }
  }, [live, simulator.result]);

  useEffect(() => {
    if (!notice) return;
    const timeoutId = window.setTimeout(() => setNotice(""), 7000);
    return () => window.clearTimeout(timeoutId);
  }, [notice]);

  const filteredMeasures = useMemo(
    () => filter === "all" ? cityMeasures : cityMeasures.filter((measure) => measure.category === filter),
    [filter, cityMeasures],
  );

  function addMeasure(measure: Measure) {
    if (decisions.some((item) => item.measureId === measure.id)) return;
    if (decisions.length >= requiredDecisions) {
      setNotice(`Все ${requiredDecisions} слотов плана заняты. Удали меру, чтобы добавить другую.`);
      return;
    }
    const next: Decision = measure.scope === "district"
      ? { measureId: measure.id, districtId: activeDistrict }
      : { measureId: measure.id };
    simulator.updateDecisions([...decisions, next]);
    setShowReferenceResult(false);
    setReferencePlanLoaded(false);
    setViewMode("before");
    setShowAnalysis(false);
    setNotice(live ? "Мера добавлена. Сервер проверяет бюджет и правила." : "Мера добавлена в демонстрационный черновик.");
  }

  function removeDecision(measureId: string) {
    simulator.updateDecisions(decisions.filter((item) => item.measureId !== measureId));
    setShowReferenceResult(false);
    setReferencePlanLoaded(false);
    setViewMode("before");
    setShowAnalysis(false);
  }

  function moveDecision(measureId: string, districtId: DistrictId) {
    const measure = cityMeasures.find((item) => item.id === measureId)!;
    if (measure.scope === "city") return;
    const updated = decisions.map((decision) => decision.measureId === measureId ? { ...decision, districtId } : decision);
    simulator.updateDecisions(updated);
    setShowReferenceResult(false);
    setReferencePlanLoaded(false);
    setViewMode("before");
    setShowAnalysis(false);
    setNotice(live ? "Район изменён. Сервер проверяет план." : "Район изменён в демонстрационном черновике.");
  }

  function loadExample() {
    simulator.updateDecisions(REFERENCE_DECISIONS.filter((decision) => cityMeasures.some((measure) => measure.id === decision.measureId)).map((decision) => ({ ...decision })));
    setReferencePlanLoaded(!live);
    setShowReferenceResult(false);
    setActiveDistrict("nura");
    setViewMode("before");
    setShowAnalysis(false);
    setNotice(live ? "Пример загружен. Сохрани план и запроси расчёт сервера." : "Загружен контрольный пример из задания.");
  }

  function clearPlan() {
    simulator.updateDecisions([]);
    setShowReferenceResult(false);
    setReferencePlanLoaded(false);
    setViewMode("before");
    setShowAnalysis(false);
    setNotice("План очищен. Базовые показатели восстановлены.");
  }

  async function calculate() {
    if (decisions.length !== requiredDecisions) {
      setNotice(`Для расчёта заполни ${requiredDecisions} слотов плана.`);
      return;
    }
    if (live) {
      if (await simulator.calculate()) {
        setViewMode("after");
        setShowAnalysis(true);
      }
      return;
    }
    if (referencePlanLoaded) {
      setShowReferenceResult(true);
      setViewMode("after");
      setShowAnalysis(true);
      setNotice("Показан заранее заданный результат из контрольного примера.");
      return;
    }
    setShowReferenceResult(false);
    setViewMode("before");
    setShowAnalysis(false);
    setNotice("Демонстрационный режим: подключи Python API для расчёта произвольного плана.");
  }

  if (simulator.mode === "loading") return <div className="app-loading" role="status"><span className="spinner" />Подключаем городской симулятор…</div>;

  return (
    <div className="sim-app">
      <header className="topbar">
        <a className="brand" href="#top" aria-label="Аким: рабочий стол города">
          <span className="brand-mark"><Glyph name="city" size={20} /></span>
          <span className="brand-copy"><strong>аким</strong><small>ГОРОДСКОЙ ПУЛЬТ</small></span>
        </a>

        <div className="topbar-center">
          <span className="topbar-kicker">СТРАТЕГИЧЕСКАЯ СИМУЛЯЦИЯ</span>
          <span className="topbar-divider" />
          <span className="topbar-period">Горизонт · {horizon} кварталов</span>
        </div>

        <div className="topbar-right">
          <span className="demo-badge"><i />{live ? "API · подключён" : "Демо · API недоступен"}</span>
          {!live && <button className="retry-api" onClick={simulator.retryConnection} title={simulator.connectionError}>Подключить API</button>}
          <button className="icon-button reset-button" onClick={clearPlan} aria-label="Сбросить план" title="Сбросить план"><Glyph name="reset" /></button>
        </div>
      </header>

      <div className="workspace-heading">
        <div>
          <div className="eyebrow">АСТАНА · РЕШЕНИЯ ДЛЯ ГОРОДА</div>
          <h1>Город в фокусе</h1>
          <p>Выбери район, собери план развития и оцени результат.</p>
        </div>
        <div className="city-score-card" aria-live="polite">
          <div className="score-label">ГОРОДСКОЙ SCORE <span>· {viewMode === "after" ? "ПОСЛЕ ПЛАНА" : "БАЗОВЫЙ"}</span></div>
          <div className="score-reading"><strong>{formatScore(shownScore)}</strong>{hasResult && viewMode === "after" && <span className="score-change">{formatDelta(result?.score_delta ?? REFERENCE_RESULT.scoreDelta)}</span>}</div>
        </div>
      </div>

      <main className="dashboard">
        <aside className="district-panel panel">
          <div className="panel-heading">
            <div><div className="section-index">01 / ТЕРРИТОРИИ</div><h2>Районы города</h2></div>
            <span className="small-count">{String(cityDistricts.length).padStart(2, "0")}</span>
          </div>

          <div className="district-list" role="group" aria-label="Выбрать район">
            {cityDistricts.map((district, index) => {
              const isActive = district.id === activeDistrict;
              const criticalCount = criticalMetricsFor(district, result, referenceResult, viewMode).length;
              const score = scoreFor(district, result, referenceResult, viewMode);
              return (
                <button
                  className={`district-row ${isActive ? "is-active" : ""}`}
                  key={district.id}
                  type="button"
                  aria-pressed={isActive}
                  title={district.profile}
                  onClick={() => setActiveDistrict(district.id)}
                >
                  <span className="district-ordinal">0{index + 1}</span>
                  <span className="district-row-info"><strong>{district.name}</strong><small>{district.profile}</small></span>
                  <span className="district-score"><strong>{formatScore(score)}</strong>{criticalCount > 0 && <i title={`${criticalCount} критических показателя`} />}</span>
                </button>
              );
            })}
          </div>

          <div className="district-detail">
            <div className="detail-title-row">
              <div><div className="section-index">ПОКАЗАТЕЛИ РАЙОНА</div><h3>{activeInfo.name}</h3></div>
              <span className={`district-tag ${viewMode === "after" ? "tag-after" : ""}`}>{viewMode === "after" ? "После" : "Исходно"}</span>
            </div>
            <p className="district-profile">{activeInfo.profile}</p>
            <div className="metric-grid">
              {metricIds.map((metric) => {
                const value = activeValues[metric];
                const delta = value - activeBeforeValues[metric];
                return (
                  <div className={`metric-line ${activeCriticalMetrics.includes(metric) ? "is-critical" : ""}`} key={metric}>
                    <span className="metric-code">{metric}</span>
                    <span className="metric-name" title={metricNames[metric]}>{metricNames[metric]}</span>
                    <strong>{value.toLocaleString("ru-RU", { maximumFractionDigits: 2 })}</strong>
                    {hasResult && viewMode === "after" ? <em className={delta < 0 ? "delta-down" : "delta-up"}>{formatDelta(delta)}</em> : activeCriticalMetrics.includes(metric) && <span className="critical-label">Риск</span>}
                  </div>
                );
              })}
            </div>
            <p className="source-note">Показатели 0–100 · критично ниже {threshold}. {live && !result ? "Score появится после расчёта." : ""}</p>
          </div>
        </aside>

        <section className="city-panel panel" aria-label={mapMode === "real" ? "Карта Астаны с объёмными зданиями" : mapMode === "unity" ? "Интерактивная Unity-сцена городской сети" : "Схематическая модель города"}>
          <div className="map-topline">
            <div><div className="section-index">02 / МОДЕЛЬ ГОРОДА</div><h2>Городская модель</h2></div>
            <div className="map-header-actions">
              <div className="renderer-toggle" role="group" aria-label="Режим карты">
                <button type="button" className={mapMode === "real" ? "selected" : ""} aria-pressed={mapMode === "real"} onClick={() => setMapMode("real")}>3D карта</button>
                <button type="button" className={mapMode === "schematic" ? "selected" : ""} aria-pressed={mapMode === "schematic"} onClick={() => setMapMode("schematic")}>Схема</button>
                <button type="button" className={mapMode === "unity" ? "selected" : ""} aria-pressed={mapMode === "unity"} onClick={() => setMapMode("unity")}>Unity <span className="unity-toggle-dot" /></button>
              </div>
              <button className="map-mode-toggle" onClick={() => { setViewMode((current) => current === "before" ? "after" : "before"); }} disabled={!hasResult} aria-pressed={viewMode === "after"} aria-label="Переключить исходный вид и результат">
                <span className={viewMode === "before" ? "selected" : ""}>До</span><span className={viewMode === "after" ? "selected" : ""}>После</span>
              </button>
            </div>
          </div>

          <div className="map-canvas">
            {mapMode === "schematic" && <div className="map-watermark">ASTANA<span>· 2026</span></div>}
            {mapMode === "schematic" && <div className="map-caption"><span className="live-dot" /> СИНТЕТИЧЕСКАЯ СХЕМА</div>}
            {mapMode === "real" ? (
              <Suspense fallback={<div className="astana-map-state" role="status"><strong>Подключаем карту Астаны</strong></div>}>
                <AstanaMap selectedDistrict={activeDistrict} onSelectDistrict={setActiveDistrict} onFallback={() => setMapMode("schematic")} />
              </Suspense>
            ) : mapMode === "unity" ? (
              <UnityCityView selectedDistrict={activeDistrict} districtName={activeInfo.name} onSelectDistrict={setActiveDistrict} sceneData={getCityNetworkDemo(activeDistrict)} />
            ) : (
              <svg className="city-svg" viewBox="0 0 720 500" role="img" aria-label="Пять схематически расположенных районов Астаны. Выбери район для просмотра показателей.">
              <defs>
                <linearGradient id="ground" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stopColor="#f0f2e9" /><stop offset="1" stopColor="#e6ebe1" /></linearGradient>
                <linearGradient id="river" x1="0" x2="1"><stop offset="0" stopColor="#bdd6d4" /><stop offset="1" stopColor="#d2e2dc" /></linearGradient>
                <filter id="soft-shadow" x="-30%" y="-30%" width="160%" height="180%"><feDropShadow dx="0" dy="7" stdDeviation="7" floodColor="#65746a" floodOpacity=".15" /></filter>
              </defs>
              <path className="land-mass" d="M355 20 677 185 360 481 38 319Z" fill="url(#ground)" />
              <path className="city-road road-wide" d="M84 308 352 172 638 317" />
              <path className="city-road" d="M179 175 451 312 578 252" />
              <path className="city-road" d="M239 94 497 222 571 337" />
              <path className="city-river" d="M97 241c74 15 89 101 165 95 70-5 70-112 152-117 66-5 77 67 148 63 28-2 51-14 79-30" />
              <path className="river-highlight" d="M97 241c74 15 89 101 165 95 70-5 70-112 152-117 66-5 77 67 148 63 28-2 51-14 79-30" />
              <g className="road-markers"><circle cx="254" cy="283" r="3" /><circle cx="416" cy="247" r="3" /><circle cx="509" cy="288" r="3" /></g>
              {cityDistricts.map((district, index) => (
                <DistrictTile
                  key={district.id}
                  district={district}
                  order={index}
                  selected={district.id === activeDistrict}
                  value={layerValue(district, activeLayer, result, referenceResult, viewMode)}
                  criticalCount={criticalMetricsFor(district, result, referenceResult, viewMode).length}
                  score={scoreFor(district, result, referenceResult, viewMode)}
                  hasAfter={viewMode === "after"}
                  onSelect={() => setActiveDistrict(district.id)}
                />
              ))}
              <g className="north-indicator" transform="translate(659 46)"><path d="M0 18V0m0 0-6 9m6-9 6 9" /><text x="0" y="31" textAnchor="middle">С</text></g>
              </svg>
            )}
            {mapMode === "schematic" && <div className="map-controls" aria-label="Слои показателей">
              <span className="layer-label"><Glyph name="layers" size={14} /> СЛОЙ</span>
              <div className="layer-buttons">
                {LAYERS.map((layer) => <button key={layer.id} className={activeLayer === layer.id ? "active" : ""} aria-pressed={activeLayer === layer.id} onClick={() => setActiveLayer(layer.id)}>{layer.label}</button>)}
              </div>
            </div>}
            {mapMode === "schematic" && <div className="map-legend"><span><i className="legend-risk" />Ниже {threshold}</span><span><i className="legend-neutral" />Средне</span><span><i className="legend-good" />Сильная сторона</span></div>}
            {mapMode === "schematic" && <span className="schematic-stamp">СХЕМА · НЕ ГЕОГРАФИЧЕСКИЕ ГРАНИЦЫ</span>}
          </div>

          <div className="map-footnote"><span>{mapMode === "real" ? "География OSM · показатели района из симулятора, не из карты" : mapMode === "unity" ? "Unity-макет условный · выбор синхронизирован со списком" : "Нажми на район или выбери его в списке"}</span><span>Сценарий <b>·</b> H = {horizon} кварталов</span></div>
        </section>

        <aside className="initiative-panel panel">
          <div className="panel-heading initiative-heading">
            <div><div className="section-index">03 / ВЫБОР МЕР</div><h2>Портфель решений</h2></div>
            <span className="small-count">{String(cityMeasures.length).padStart(2, "0")}</span>
          </div>

          <div className="budget-card">
            <div className="budget-title"><span>БЮДЖЕТНЫЙ ЛИМИТ</span><span>{spent ?? "—"} <i>/</i> {budgetLimit}</span></div>
            <div className="budget-track"><span style={{ width: `${budgetPercent}%` }} /></div>
            <div className="budget-detail"><span>{live ? "Проверка сервером" : referencePlanLoaded ? "Контрольный пример" : "Демо-черновик"}</span><strong>{live ? simulator.isValidating ? "Проверяется…" : simulator.validation ? `Осталось ${simulator.validation.remaining_budget}` : "Нет подтверждения" : spent === null ? "Без расчёта" : `${spent} усл. ед.`}</strong></div>
          </div>

          <div className="category-filter" role="group" aria-label="Фильтр по направлениям">
            <button className={filter === "all" ? "active" : ""} aria-pressed={filter === "all"} onClick={() => setFilter("all")}>Все <span>{cityMeasures.length}</span></button>
            {(Object.keys(CATEGORY_META) as CategoryId[]).map((category) => (
              <button key={category} className={filter === category ? "active" : ""} aria-pressed={filter === category} onClick={() => setFilter(category)} title={CATEGORY_META[category].name}>
                {CATEGORY_META[category].short}<span>{cityMeasures.filter((measure) => measure.category === category).length}</span>
              </button>
            ))}
          </div>

          <div className="measure-list" role="region" aria-label="Меры городского развития">
            {filteredMeasures.map((measure) => {
              const decision = decisions.find((item) => item.measureId === measure.id);
              const disabled = decisions.length >= requiredDecisions || Boolean(decision);
              return (
                <article className={`measure-card ${decision ? "is-added" : ""}`} key={measure.id}>
                  <span className="measure-icon" style={{ "--category-color": CATEGORY_META[measure.category].color } as CSSProperties}>{CATEGORY_META[measure.category].short}</span>
                  <div className="measure-main">
                    <div className="measure-card-title"><span className="measure-id">{measure.id}</span><strong>{measure.name}</strong></div>
                    <div className="measure-meta"><span>{CATEGORY_META[measure.category].name}</span><i />{measure.scope === "city" ? <span>Весь город</span> : <span>В {activeInfo.name}</span>}<i /><span>Лаг {measure.lag} кв.</span></div>
                    <div className="effect-line">{Object.entries(measure.effects).map(([metric, effect]) => <span key={metric}>{metricNames[metric as MetricId]} {formatDelta(effect)}</span>)} <small>до лага</small></div>
                    {decision && measure.scope === "district" && <label className="assigned-district">Район <select value={decision.districtId ?? ""} aria-label={`Район для ${measure.id}`} onChange={(event) => moveDecision(measure.id, event.target.value as DistrictId)}>{cityDistricts.map((district) => <option key={district.id} value={district.id}>{district.name}</option>)}</select></label>}
                  </div>
                  <div className="measure-action">
                    <strong>{measure.cost}<small>ед.</small></strong>
                    <button
                      className={`add-measure ${decision ? "added" : ""}`}
                      disabled={disabled}
                      onClick={() => addMeasure(measure)}
                      aria-label={decision ? `${measure.name} уже выбрана` : `Добавить ${measure.name}`}
                      title={measure.scope === "district" ? `Добавить в район ${activeInfo.name}` : "Добавить для всего города"}
                    >
                      {decision ? <Glyph name="check" size={16} /> : <span>+</span>}
                    </button>
                  </div>
                </article>
              );
            })}
          </div>

          <div className="catalog-footer"><span>Эффект справочный · итог считает сервер</span><button onClick={loadExample}>Загрузить пример</button></div>
        </aside>
      </main>

      <section className={`plan-tray ${decisions.length === requiredDecisions ? "plan-complete" : ""}`} aria-label="План решений">
        <div className="tray-intro" aria-live="polite"><span className="section-index">ТВОЙ ПЛАН</span><strong>{decisions.length}<i>/</i>{requiredDecisions}</strong><small>{live ? simulator.hasUnsavedChanges ? "Есть несохранённые изменения" : "Сохранён на сервере" : `Выбрано ${decisions.length} из ${requiredDecisions}`}</small></div>
        <div className="decision-slots">
          {Array.from({ length: requiredDecisions }, (_, index) => {
            const decision = decisions[index];
            const measure = decision && cityMeasures.find((item) => item.id === decision.measureId);
            const district = decision?.districtId && cityDistricts.find((item) => item.id === decision.districtId);
            return (
              <div className={`decision-slot ${decision ? "filled" : ""}`} key={index}>
                <span className="slot-number">0{index + 1}</span>
                {measure ? <><span className="slot-details"><strong>{measure.name}</strong><small>{measure.id} · {measure.scope === "city" ? "Весь город" : district?.name}</small></span><button className="remove-decision" aria-label={`Убрать ${measure.id}`} onClick={() => removeDecision(measure.id)}><Glyph name="close" size={15} /></button></> : <span className="slot-placeholder">Добавь меру</span>}
              </div>
            );
          })}
        </div>
        <div className="tray-action">
          {live && <button className="save-button" onClick={() => { void simulator.saveDraft(); }} disabled={!simulator.hasUnsavedChanges || !simulator.validation || Boolean(simulator.busy) || simulator.isValidating}>{simulator.busy === "saving" ? "Сохраняем…" : "Сохранить план"}</button>}
          <button className="calculate-button" onClick={() => { void calculate(); }} disabled={live ? !simulator.validation?.ready_for_calculation || simulator.hasUnsavedChanges || Boolean(simulator.busy) || simulator.isValidating : decisions.length !== requiredDecisions}>
            {simulator.busy === "calculating" ? <><span className="spinner" />Считаем…</> : <>Запросить расчёт <Glyph name="arrow" size={17} /></>}
          </button>
          <small>{live ? simulator.isValidating ? "Проверяем правила…" : simulator.hasUnsavedChanges ? "Сначала сохрани проверенный план" : simulator.validation?.ready_for_calculation ? "План готов к расчёту" : `Выбери ${requiredDecisions} мер без нарушений` : decisions.length === requiredDecisions ? referencePlanLoaded ? "Контрольный результат из задания" : "API не подключён" : `Добавь ещё ${requiredDecisions - decisions.length} мер`}</small>
        </div>
      </section>

      {simulator.issues.length > 0 && live && <section className="api-errors" role="alert"><strong>План требует внимания</strong><ul>{simulator.issues.map((issue, index) => <li key={`${index}-${issue}`}>{issue}</li>)}</ul>{simulator.failedAction && <button onClick={() => { void (simulator.failedAction === "save" ? simulator.saveDraft() : calculate()); }}>Повторить</button>}</section>}

      {hasResult && showAnalysis && (
        <section className="analysis-strip" aria-live="polite">
          <div className="analysis-icon"><Glyph name="spark" /></div>
          <div className="analysis-copy"><strong>{live ? "Результат расчёта сервера" : "Контрольный результат из задания"}</strong><p>{live ? `Бюджет: ${result?.total_cost} из ${budgetLimit}, остаток ${result?.remaining_budget}. Версии данных ${result?.dataset_version}, формулы ${result?.formula_version}.` : "Это фиксированный пример, а не расчёт произвольного плана или ответ AI."}</p></div>
          <div className="analysis-stats"><span><small>КРИТИЧЕСКИХ ПОКАЗАТЕЛЕЙ</small><strong>{result?.critical_before.length ?? REFERENCE_RESULT.criticalBefore} <i>→</i> {result?.critical_after.length ?? REFERENCE_RESULT.criticalAfter}</strong></span><span><small>ИЗМЕНЕНИЕ SCORE</small><strong>{formatScore(result?.score_before ?? REFERENCE_RESULT.scoreBefore)} → {formatScore(result?.score_after ?? REFERENCE_RESULT.scoreAfter)}</strong></span></div>
          <div className="analysis-local-note">{live ? `Δ ${formatDelta(result?.score_delta ?? 0)}` : "Данные задания · не AI-ответ"}</div>
          <button className="analysis-dismiss" onClick={() => setShowAnalysis(false)} aria-label="Скрыть объяснение"><Glyph name="close" size={17} /></button>
        </section>
      )}

      {result && showAnalysis && <section className="result-breakdown" aria-label="Подробности расчёта">
        <div className="result-breakdown-head"><strong>Что изменилось</strong><span>{result.critical_after.length === 0 ? "Критических показателей после расчёта нет" : `Критических показателей осталось: ${result.critical_after.length}`}</span></div>
        <div className="district-result-grid">{result.districts.map((row) => <button key={row.district_id} onClick={() => { setActiveDistrict(row.district_id); setViewMode("after"); }}><span>{cityDistricts.find((district) => district.id === row.district_id)?.name ?? row.district_id}</span><strong>{formatScore(row.score_before)} → {formatScore(row.score_after)}</strong><small>{formatDelta(row.score_after - row.score_before)}</small></button>)}</div>
        {result.critical_after.length > 0 && <div className="critical-results">{result.critical_after.map((item) => <span key={`${item.district_id}-${item.indicator_id}`}>{cityDistricts.find((district) => district.id === item.district_id)?.name}: {metricNames[item.indicator_id]} — {item.value}</span>)}</div>}
        <details className="effects-details"><summary>Применённые эффекты · {result.effects.length}</summary><div>{result.effects.length === 0 ? <p>Дополнительных эффектов нет.</p> : result.effects.map((effect, index) => <p key={`${index}-${effect.district_id}-${effect.indicator_id}`}><b>{effect.kind === "synergy" ? "Синергия" : "Прямой эффект"}</b> · {cityDistricts.find((district) => district.id === effect.district_id)?.name} · {metricNames[effect.indicator_id]} {formatDelta(effect.delta)} <small>({effect.measure_ids.map((id) => cityMeasures.find((measure) => measure.id === id)?.name ?? id).join(" + ")})</small></p>)}</div></details>
      </section>}

      {live && simulator.history.length > 0 && <details className="history-panel"><summary>История расчётов · {simulator.history.length}</summary><div>{simulator.history.map((entry) => <div className="history-row" key={entry.id}><span>Версия {entry.scenario_version} · {new Date(entry.created_at).toLocaleString("ru-RU")}</span><strong>{formatScore(entry.simulation.score_before)} → {formatScore(entry.simulation.score_after)}</strong><small>{formatDelta(entry.simulation.score_delta)}</small></div>)}</div></details>}

      <ConsultantPanel />

      <div className={`toast ${notice ? "visible" : ""}`} role="status" aria-live="polite">{notice}<button onClick={() => setNotice("")} aria-label="Закрыть сообщение"><Glyph name="close" size={15} /></button></div>
      <footer className="app-footer"><span>{live ? "Показатели и меры: Python API · геоподложка OSM" : "Демоданные симуляции · геоподложка OSM"}</span><span>Показатель ниже {threshold} считается критическим</span><span>Горизонт H={horizon} кварталов</span></footer>
    </div>
  );
}

function layerValue(district: District, layer: LayerId, result: SimulationResult | null, referenceResult: boolean, view: ViewMode) {
  if (layer === "score") return scoreFor(district, result, referenceResult, view) ?? 50;
  return valuesFor(district, result, referenceResult, view)[LAYER_METRIC[layer]];
}

function DistrictTile({ district, order, selected, value, criticalCount, score, hasAfter, onSelect }: {
  district: District; order: number; selected: boolean; value: number; criticalCount: number; score: number | null; hasAfter: boolean; onSelect: () => void;
}) {
  const heightA = 34 + (order * 7 % 18);
  const heightB = 43 + (order * 11 % 20);
  const heightC = 27 + (order * 5 % 16);
  const label = `Район ${district.name}, индекс ${formatScore(score)}${criticalCount ? `, критических показателей: ${criticalCount}` : ""}`;
  return (
    <g
      className={`district-tile ${selected ? "selected" : ""}`}
      transform={`translate(${district.x} ${district.y})`}
      tabIndex={0}
      role="button"
      aria-label={label}
      aria-pressed={selected}
      onClick={onSelect}
      onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); onSelect(); } }}
    >
      <polygon className="tile-shadow" points="0,-70 124,-7 0,56 -124,-7" />
      <polygon className="tile-base" points="0,-80 124,-18 0,44 -124,-18" style={{ fill: tint(value) }} />
      <path className="tile-inset" d="M-105-18 0-70 105-18 0 34Z" />
      <path className="block-road" d="M-77-27 0 12 78-27M-31-54 47-15M-51 7 25-32" />

      <Building x={-73} y={-33} height={heightA} tone={district.accent} />
      <Building x={-24} y={-54} height={heightB} tone="#e1d6bd" />
      <Building x={28} y={-31} height={heightC} tone="#aebeb5" />
      <Building x={-5} y={2} height={heightA * 0.72} tone="#c8b9a3" small />
      <Tree x={69} y={-2} />
      <Tree x={-88} y={-4} />
      <path className="district-label-pill" d="M-40 55h80q9 0 9 9v18q0 9-9 9h-80q-9 0-9-9V64q0-9 9-9Z" />
      <text className="district-label" x="0" y="74" textAnchor="middle">{district.name}</text>
      <text className="district-label-score" x="0" y="87" textAnchor="middle">{formatScore(score)}</text>
      {criticalCount > 0 && <g className="critical-pin" transform="translate(101 -61)"><circle r="10" /><text y="4" textAnchor="middle">{criticalCount}</text></g>}
      {hasAfter && score !== null && district.score !== null && score > district.score && <circle className="after-indicator" cx="0" cy="-86" r="5" />}
    </g>
  );
}

function Building({ x, y, height, tone, small = false }: { x: number; y: number; height: number; tone: string; small?: boolean }) {
  const width = small ? 25 : 31;
  const half = width / 2;
  const top = 12;
  const left = x - half;
  const right = x + half;
  const roof = y - height;
  return (
    <g className="building" filter="url(#soft-shadow)">
      <path d={`M${left} ${y} ${x} ${y + 10} ${x} ${roof + 10} ${left} ${roof}Z`} fill={tone} />
      <path d={`M${x} ${y + 10} ${right} ${y} ${right} ${roof} ${x} ${roof + 10}Z`} fill="#9a9c8d" />
      <path d={`M${left} ${roof} ${x} ${roof - 9} ${right} ${roof} ${x} ${roof + 10}Z`} fill="#e8e2d2" />
      {Array.from({ length: small ? 2 : 3 }, (_, index) => {
        const yy = roof + 12 + index * Math.max(7, (height - 14) / 3);
        if (yy > y - 2) return null;
        return <g key={index} className="building-window"><path d={`M${left + 6} ${yy}v4m7-8v4m${x - left - 13} ${yy + 6}v4`} /><path d={`M${x + 7} ${yy}v4m7-8v4m7 ${yy + 6}v4`} /></g>;
      })}
      {height > 50 && <path className="roof-detail" d={`M${x - 4} ${roof - 8}v-6h8v10`} />}
    </g>
  );
}

function Tree({ x, y }: { x: number; y: number }) {
  return <g className="tree" transform={`translate(${x} ${y})`}><path d="M0 0v16" /><circle cx="0" cy="-3" r="7" /><circle cx="-5" cy="0" r="4.5" /><circle cx="5" cy="1" r="4" /></g>;
}
