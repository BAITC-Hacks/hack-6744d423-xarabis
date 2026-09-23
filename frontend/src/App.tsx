import {
  lazy,
  Suspense,
  useEffect,
  useMemo,
  useRef,
  useState,
  type CSSProperties,
} from "react";
import { useCitySimulator } from "./useCitySimulator";
import { UnityCityView } from "./UnityCityView";
import { ScenarioConsultantPanel } from "./ScenarioConsultantPanel";
import { ScenarioLibrary } from "./ScenarioLibrary";
import { buildProjectPreviews, type ProjectPreview } from "./projectPreview";
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
  type DistrictId,
  type Measure,
  type MetricId,
} from "./caseData";
import "./workspace.css";

const AstanaMap = lazy(() =>
  import("./AstanaMap").then((module) => ({ default: module.AstanaMap })),
);
const format = (value: number | null | undefined) =>
  value == null
    ? "—"
    : value.toLocaleString("ru-RU", { maximumFractionDigits: 2 });
const delta = (value: number) => `${value > 0 ? "+" : ""}${format(value)}`;
const LAYERS = [
  { id: "projects", label: "Проекты плана" },
  { id: "score", label: "Общий индекс" },
  ...METRICS.map((id) => ({ id, label: METRIC_META[id].name })),
];
type Page = "city" | "results" | "scenarios";
type View = "before" | "plan" | "after";

function Icon({
  name,
}: {
  name: "city" | "close" | "chat" | "arrow" | "play" | "layers";
}) {
  const paths = {
    city: (
      <>
        <path d="M3 21h18M5 21V8l7-5v18M12 11h7v10M8 9v1m0 3v1m7 0v1m0 3v1" />
      </>
    ),
    close: <path d="m6 6 12 12M6 18 18 6" />,
    chat: (
      <path d="M21 11a9 9 0 0 1-9 9H4l-2 2V11a9 9 0 0 1 19 0ZM7 10h10M7 14h6" />
    ),
    arrow: <path d="M4 12h16m-6-6 6 6-6 6" />,
    play: <path d="m8 4 12 8-12 8V4Z" />,
    layers: <path d="m12 3 9 5-9 5-9-5 9-5Zm-9 9 9 5 9-5M3 16l9 5 9-5" />,
  };
  return (
    <svg
      width="20"
      height="20"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {paths[name]}
    </svg>
  );
}

export function App() {
  const simulator = useCitySimulator();
  const [page, setPage] = useState<Page>("city");
  const [districtId, setDistrictId] = useState<DistrictId>("nura");
  const [focus, setFocus] = useState<"overview" | "detail">("overview");
  const [cameraRevision, setCameraRevision] = useState(0);
  const [engine, setEngine] = useState<"map" | "unity" | "fallback">("map");
  const [view, setView] = useState<View>("plan");
  const [layer, setLayer] = useState("projects");
  const [panelTab, setPanelTab] = useState<"measures" | "plan">("measures");
  const [category, setCategory] = useState<CategoryId | "all">("all");
  const [mobilePanel, setMobilePanel] = useState(false);
  const [activeMeasure, setActiveMeasure] = useState<string | null>(null);
  const [referenceLoaded, setReferenceLoaded] = useState(false);
  const [referenceCalculated, setReferenceCalculated] = useState(false);
  const [notice, setNotice] = useState("");
  const [consultantOpen, setConsultantOpen] = useState(false);
  const [presentation, setPresentation] = useState<number | null>(null);
  const appRef = useRef<HTMLDivElement>(null);
  const panelRef = useRef<HTMLElement>(null);
  const dialogRef = useRef<HTMLDialogElement>(null);
  const presentationOrigin = useRef({ page, view, layer, engine, focus });
  const live = simulator.mode === "live";
  const result = live ? (simulator.result?.simulation ?? null) : null;
  const reference = !live && referenceCalculated;
  const hasResult = Boolean(result || reference);
  const decisions = simulator.decisions;
  const budget = simulator.catalog?.budget ?? 100;
  const required = simulator.catalog?.required_decisions ?? 5;
  const horizon = simulator.catalog?.horizon_quarters ?? 8;
  const threshold = simulator.catalog?.critical_threshold ?? 40;
  const busy = Boolean(simulator.busy);
  const districts = useMemo(
    () =>
      live
        ? simulator.districts.map((district) => ({
            ...DISTRICTS.find((item) => item.id === district.id)!,
            name: district.name,
            profile: district.profile,
            values: district.indicators,
            score:
              result?.districts.find((item) => item.district_id === district.id)
                ?.score_before ?? null,
          }))
        : DISTRICTS,
    [live, simulator.districts, result],
  );
  const measures = useMemo<Measure[]>(
    () =>
      live
        ? simulator.measures.map((measure) => ({
            id: measure.id,
            name: measure.name,
            category: measure.direction,
            cost: measure.cost,
            lag: measure.lag_quarters,
            scope: measure.scope,
            effects: measure.effects,
          }))
        : MEASURES,
    [live, simulator.measures],
  );
  const metricNames = useMemo(
    () =>
      Object.fromEntries(
        live
          ? simulator.indicators.map((item) => [item.id, item.name])
          : METRICS.map((id) => [id, METRIC_META[id].name]),
      ) as Record<MetricId, string>,
    [live, simulator.indicators],
  );
  const current =
    districts.find((district) => district.id === districtId) ?? DISTRICTS[4];
  const rows = useMemo(
    () =>
      result?.districts ??
      (reference
        ? REFERENCE_RESULT.districts.map((item) => ({
            district_id: item.districtId as DistrictId,
            score_before: item.scoreBefore,
            score_after: item.scoreAfter,
            indicators_before: DISTRICTS.find(
              (district) => district.id === item.districtId,
            )!.values,
            indicators_after: item.after,
          }))
        : []),
    [result, reference],
  );
  const row = rows.find((item) => item.district_id === districtId);
  const values =
    view === "after" && row ? row.indicators_after : current.values;
  const weakest = [...METRICS]
    .sort((a, b) => values[a] - values[b])
    .slice(0, 2);
  const scoreBefore =
    result?.score_before ?? (!live ? REFERENCE_RESULT.scoreBefore : null);
  const scoreAfter =
    result?.score_after ?? (reference ? REFERENCE_RESULT.scoreAfter : null);
  const costEstimate = decisions.reduce(
    (sum, decision) =>
      sum +
      (measures.find((measure) => measure.id === decision.measureId)?.cost ??
        0),
    0,
  );
  const spent = live
    ? (simulator.validation?.total_cost ?? costEstimate)
    : costEstimate;
  const projects = useMemo(
    () => buildProjectPreviews(decisions, measures),
    [decisions, measures],
  );
  const districtValues = useMemo(
    () =>
      layer === "projects"
        ? undefined
        : Object.fromEntries(
            districts.map((district) => {
              const resultRow = rows.find(
                (item) => item.district_id === district.id,
              );
              const indicators =
                view === "after" && resultRow
                  ? resultRow.indicators_after
                  : district.values;
              return [
                district.id,
                layer === "score"
                  ? resultRow
                    ? view === "after"
                      ? resultRow.score_after
                      : resultRow.score_before
                    : district.score
                  : indicators[layer as MetricId],
              ];
            }),
          ),
    [layer, districts, rows, view],
  );
  const shownMeasures =
    category === "all"
      ? measures
      : measures.filter((measure) => measure.category === category);
  const mainDisabled =
    busy ||
    (live
      ? simulator.isValidating ||
        !simulator.validation ||
        (!simulator.hasUnsavedChanges &&
          !simulator.validation.ready_for_calculation)
      : !referenceLoaded || decisions.length !== required);

  useEffect(() => {
    if (simulator.statusMessage) setNotice(simulator.statusMessage);
  }, [simulator.statusMessage]);
  useEffect(() => {
    if (!hasResult && view === "after") setView("plan");
  }, [hasResult, view]);
  useEffect(() => {
    panelRef.current?.scrollTo({ top: 0 });
  }, [page, panelTab, districtId]);
  useEffect(() => {
    if (!activeMeasure) return;
    panelRef.current
      ?.querySelector(".is-focused")
      ?.scrollIntoView({ block: "nearest" });
  }, [activeMeasure, panelTab, consultantOpen]);
  useEffect(() => {
    if (!notice) return;
    const timer = window.setTimeout(() => setNotice(""), 6000);
    return () => window.clearTimeout(timer);
  }, [notice]);
  useEffect(() => {
    const dialog = dialogRef.current;
    if (consultantOpen && dialog && !dialog.open) dialog.showModal();
    else if (!consultantOpen && dialog?.open) dialog.close();
  }, [consultantOpen]);
  useEffect(() => {
    if (presentation === null) return;
    function escape(event: KeyboardEvent) {
      if (event.key === "Escape") stopPresentation();
    }
    window.addEventListener("keydown", escape);
    return () => window.removeEventListener("keydown", escape);
  }, [presentation]);

  function selectDistrict(id: DistrictId) {
    setDistrictId(id);
    setFocus("detail");
    setCameraRevision((value) => value + 1);
  }
  function editPlan(next: Decision[]) {
    simulator.updateDecisions(next);
    setReferenceLoaded(false);
    setReferenceCalculated(false);
    setView("plan");
  }
  function addMeasure(measure: Measure) {
    if (busy || decisions.some((item) => item.measureId === measure.id)) return;
    if (decisions.length >= required) {
      setNotice(
        `В плане уже ${required} решений. Удали одно, чтобы добавить новое.`,
      );
      return;
    }
    editPlan([
      ...decisions,
      {
        measureId: measure.id,
        ...(measure.scope === "district" ? { districtId } : {}),
      },
    ]);
    setActiveMeasure(measure.id);
    setFocus("detail");
    setCameraRevision((value) => value + 1);
    setNotice(
      `«${measure.name}» добавлено в план. На карте — условное размещение проекта.`,
    );
  }
  function removeMeasure(id: string) {
    if (!busy)
      editPlan(decisions.filter((decision) => decision.measureId !== id));
  }
  function loadExample() {
    if (busy) return;
    simulator.updateDecisions(
      REFERENCE_DECISIONS.map((decision) => ({ ...decision })),
    );
    setReferenceLoaded(!live);
    setReferenceCalculated(false);
    setView("plan");
    setPage("city");
    setDistrictId("nura");
    setFocus("detail");
    setPanelTab("plan");
    setLayer("projects");
    setNotice(
      "Загружены пять решений контрольного примера. Можно рассмотреть проекты и запросить результат.",
    );
  }
  async function primaryAction() {
    if (live) {
      if (simulator.hasUnsavedChanges) {
        await simulator.saveDraft();
        return;
      }
      if (!(await simulator.calculate())) return;
    } else {
      if (!referenceLoaded) return;
      setReferenceCalculated(true);
    }
    setView("after");
    setPage("results");
    setLayer("score");
    setEngine("map");
    setMobilePanel(true);
  }
  function selectProject(project: ProjectPreview) {
    selectDistrict(project.districtId);
    setActiveMeasure(project.measureId);
    setPanelTab("plan");
    setMobilePanel(true);
  }
  function navigate(next: Page) {
    setPage(next);
    setMobilePanel(false);
    if (next === "results") {
      setView(hasResult ? "after" : "plan");
      setLayer("score");
      setEngine("map");
    }
    if (next === "city") {
      setView("plan");
      setLayer("projects");
    }
  }
  async function openScenario(id?: string) {
    if (await simulator.openScenario(id)) {
      setPage("city");
      setView("plan");
      setLayer("projects");
      setPanelTab("plan");
      setFocus("overview");
    }
  }
  function presentationStep(step: number) {
    setPresentation(step);
    setView(
      step === 0
        ? "before"
        : step === 1
          ? "plan"
          : hasResult
            ? "after"
            : "plan",
    );
    setLayer(step === 2 && hasResult ? "score" : "projects");
    setFocus(step === 2 ? "overview" : "detail");
    setCameraRevision((value) => value + 1);
  }
  function startPresentation() {
    setNotice("");
    presentationOrigin.current = { page, view, layer, engine, focus };
    setPage("city");
    setEngine("map");
    setMobilePanel(false);
    presentationStep(0);
    void appRef.current?.requestFullscreen?.().catch(() => undefined);
  }
  function stopPresentation() {
    setPresentation(null);
    const previous = presentationOrigin.current;
    setPage(previous.page);
    setView(previous.view);
    setLayer(previous.layer);
    setEngine(previous.engine);
    setFocus(previous.focus);
    if (document.fullscreenElement === appRef.current)
      void document.exitFullscreen();
  }

  if (simulator.mode === "loading")
    return (
      <div className="app-loading" role="status">
        <span className="spinner" />
        Открываем городской пульт…
      </div>
    );

  return (
    <div
      ref={appRef}
      className={`city-workspace ${presentation !== null ? "is-presenting" : ""}`}
    >
      <header className="workspace-header">
        <a className="brand" href="#top" onClick={() => navigate("city")}>
          <span className="brand-mark">
            <Icon name="city" />
          </span>
          <span className="brand-copy">
            <strong>аким</strong>
            <small>ЖИВАЯ КАРТА РЕШЕНИЙ</small>
          </span>
        </a>
        <nav className="workspace-nav" aria-label="Основные разделы">
          {(
            [
              { id: "city", label: "Город" },
              { id: "results", label: "Результаты" },
              { id: "scenarios", label: "Сценарии" },
            ] as const
          ).map((item) => (
            <button
              key={item.id}
              aria-current={page === item.id ? "page" : undefined}
              onClick={() => navigate(item.id)}
            >
              {item.label}
              {item.id === "results" && hasResult && <i />}
            </button>
          ))}
        </nav>
        <div className="workspace-header-actions">
          <button
            className={`connection-indicator ${live ? "is-connected" : ""}`}
            onClick={() => {
              if (!live) simulator.retryConnection();
            }}
            title={
              live ? "Данные подключены" : "Нажми, чтобы повторить подключение"
            }
          >
            <i />
            {live ? "На связи" : "Деморежим"}
          </button>
          <button
            className="secondary-action presentation-trigger"
            onClick={startPresentation}
          >
            <Icon name="play" />
            Показать жюри
          </button>
        </div>
      </header>

      {page === "scenarios" && (
        <ScenarioLibrary
          live={live}
          currentId={simulator.scenario?.id}
          locked={simulator.hasUnsavedChanges || busy}
          onOpen={openScenario}
          onExample={loadExample}
        />
      )}

      <main
        className={`city-workbench ${page === "scenarios" ? "is-hidden" : ""}`}
      >
        <section className="map-workspace" aria-label="Карта решений">
          <div className="workspace-map-top">
            <div>
              <span className="section-index">
                АСТАНА · ГОРИЗОНТ {horizon} КВАРТАЛОВ
              </span>
              <h1>
                {page === "results"
                  ? "Что изменит твой план"
                  : "Город, который меняешь ты"}
              </h1>
            </div>
            <div className="map-scale-switch">
              <button
                aria-pressed={focus === "overview"}
                onClick={() => {
                  setFocus("overview");
                  setCameraRevision((value) => value + 1);
                }}
              >
                Весь город
              </button>
              <button
                aria-pressed={focus === "detail"}
                onClick={() => {
                  setFocus("detail");
                  setCameraRevision((value) => value + 1);
                }}
              >
                Рассмотреть район
              </button>
            </div>
          </div>
          <div
            className="district-ribbon"
            role="group"
            aria-label="Выбрать район"
          >
            {districts.map((district) => (
              <button
                key={district.id}
                aria-pressed={districtId === district.id}
                onClick={() => selectDistrict(district.id)}
              >
                {district.name}
                <small>
                  {projects.filter(
                    (project) => project.districtId === district.id,
                  ).length || ""}
                </small>
              </button>
            ))}
          </div>
          <div className="workspace-map-canvas">
            {engine === "map" ? (
              <Suspense
                fallback={
                  <div className="astana-map-state" role="status">
                    Загружаем карту…
                  </div>
                }
              >
                <AstanaMap
                  selectedDistrict={districtId}
                  onSelectDistrict={selectDistrict}
                  onFallback={() => setEngine("fallback")}
                  projects={projects}
                  projectsVisible={view !== "before"}
                  focus={focus}
                  cameraRevision={cameraRevision}
                  districtValues={districtValues}
                  onSelectProject={selectProject}
                />
              </Suspense>
            ) : engine === "unity" ? (
              <UnityCityView
                selectedDistrict={districtId}
                districtName={current.name}
                onSelectDistrict={selectDistrict}
                projects={projects}
                projectsVisible={view !== "before"}
                initialFocus={focus}
                onFocusChange={setFocus}
              />
            ) : (
              <div className="fallback-map">
                <h2>Обзор районов</h2>
                <p>
                  Карта недоступна. Выбор мер и работа с планом остаются
                  доступны.
                </p>
                {districts.map((district) => (
                  <button
                    key={district.id}
                    onClick={() => selectDistrict(district.id)}
                    aria-pressed={district.id === districtId}
                  >
                    <strong>{district.name}</strong>
                    <span>{district.profile}</span>
                    <small>
                      {
                        projects.filter(
                          (project) => project.districtId === district.id,
                        ).length
                      }{" "}
                      проектов
                    </small>
                  </button>
                ))}
              </div>
            )}
            {presentation === null && (
              <div
                className="map-view-switch"
                role="group"
                aria-label="Состояние города"
              >
                {(
                  [
                    { id: "before", label: "Сейчас" },
                    { id: "plan", label: "Мой план" },
                    { id: "after", label: "После расчёта" },
                  ] as const
                ).map((item) => (
                  <button
                    key={item.id}
                    disabled={item.id === "after" && !hasResult}
                    aria-pressed={view === item.id}
                    onClick={() => {
                      setView(item.id);
                      if (item.id === "after") {
                        setEngine("map");
                        if (layer === "projects") setLayer("score");
                      }
                    }}
                  >
                    {item.label}
                  </button>
                ))}
              </div>
            )}
            {presentation !== null && (
              <section className="presentation-story" aria-live="polite">
                <div className="story-progress">
                  {[0, 1, 2].map((step) => (
                    <i
                      className={step <= presentation ? "is-active" : ""}
                      key={step}
                    />
                  ))}
                </div>
                <span className="section-index">
                  0{presentation + 1} / 03 ·{" "}
                  {presentation === 0
                    ? "ПРОБЛЕМА"
                    : presentation === 1
                      ? "РЕШЕНИЕ"
                      : "РЕЗУЛЬТАТ"}
                </span>
                <h2>
                  {presentation === 0
                    ? `${current.name}: где нужна перемена`
                    : presentation === 1
                      ? `${decisions.length} решений для города`
                      : hasResult
                        ? `${format(scoreBefore)} → ${format(scoreAfter)}`
                        : "План готов к проверке"}
                </h2>
                <p>
                  {presentation === 0
                    ? current.profile
                    : presentation === 1
                      ? "На карте появились выбранные проекты. Их размещение иллюстративное; влияние оценивает симулятор."
                      : hasResult
                        ? `Изменение общего индекса: ${delta((scoreAfter ?? 0) - (scoreBefore ?? 0))}. ${live ? "Результат сервера." : "Контрольный пример задания."}`
                        : "Подключи сервер и рассчитай сценарий, чтобы показать итоговые показатели."}
                </p>
                <div className="story-actions">
                  <button className="text-action" onClick={stopPresentation}>
                    Завершить показ
                  </button>
                  <button
                    className="secondary-action"
                    disabled={presentation === 0}
                    onClick={() => presentationStep(presentation - 1)}
                  >
                    Назад
                  </button>
                  {presentation < 2 ? (
                    <button
                      className="primary-action"
                      onClick={() => presentationStep(presentation + 1)}
                    >
                      Далее <Icon name="arrow" />
                    </button>
                  ) : (
                    <button
                      className="primary-action"
                      onClick={stopPresentation}
                    >
                      К рабочему плану
                    </button>
                  )}
                </div>
              </section>
            )}
          </div>
          <div className="workspace-map-bottom">
            <label>
              <Icon name="layers" />
              <select
                aria-label="Слой карты"
                value={layer}
                onChange={(event) => {
                  setLayer(event.target.value);
                  setEngine("map");
                }}
              >
                {LAYERS.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="map-renderer">
              <span>Вид</span>
              <select
                aria-label="Визуализация карты"
                value={engine}
                onChange={(event) =>
                  setEngine(event.target.value as typeof engine)
                }
              >
                <option value="map">Карта и проекты</option>
                <option value="unity">Объёмный макет</option>
                <option value="fallback">Список районов</option>
              </select>
            </label>
            <button
              className="mobile-panel-trigger secondary-action"
              onClick={() => setMobilePanel(true)}
            >
              {page === "results"
                ? "Результаты"
                : `Решения · ${decisions.length}/${required}`}
            </button>
          </div>
        </section>

        <aside
          ref={panelRef}
          className={`work-panel ${mobilePanel ? "is-open" : ""}`}
          aria-label={
            page === "results" ? "Результаты сценария" : "Решения для района"
          }
        >
          <button
            className="panel-mobile-close"
            onClick={() => setMobilePanel(false)}
            aria-label="Свернуть панель"
          >
            <span />
            Свернуть <Icon name="close" />
          </button>
          {page === "results" ? (
            <>
              <div className="work-panel-heading">
                <span className="section-index">ОЦЕНКА СЦЕНАРИЯ</span>
                <h2>Результаты плана</h2>
                <p>
                  {hasResult
                    ? live
                      ? "Расчёт сервера · горизонт " + horizon + " кварталов"
                      : "Контрольный результат из задания"
                    : "Собери план, сохрани его и запроси расчёт."}
                </p>
              </div>
              {!hasResult ? (
                <div className="panel-empty">
                  <Icon name="layers" />
                  <h3>Результата ещё нет</h3>
                  <p>
                    {live
                      ? "Расчёт появится после сохранения всех решений."
                      : "Для произвольного плана нужен сервер. Можно изучить контрольный пример."}
                  </p>
                  <button
                    className="primary-action"
                    onClick={() => navigate("city")}
                  >
                    Вернуться к решениям
                  </button>
                  {!live && (
                    <button className="text-action" onClick={loadExample}>
                      Загрузить пример
                    </button>
                  )}
                </div>
              ) : (
                <div className="results-content">
                  <div className="result-hero">
                    <span>Общий индекс города</span>
                    <strong>
                      {format(scoreAfter)}
                      <small
                        className={
                          (scoreAfter ?? 0) < (scoreBefore ?? 0)
                            ? "is-negative"
                            : ""
                        }
                      >
                        {delta((scoreAfter ?? 0) - (scoreBefore ?? 0))}
                      </small>
                    </strong>
                    <p>До плана: {format(scoreBefore)}</p>
                  </div>
                  <div className="result-facts">
                    <div>
                      <span>Бюджет</span>
                      <strong>
                        {result?.total_cost ?? 95} / {budget}
                      </strong>
                    </div>
                    <div>
                      <span>Критических показателей</span>
                      <strong>
                        {result?.critical_before.length ??
                          REFERENCE_RESULT.criticalBefore}{" "}
                        →{" "}
                        {result?.critical_after.length ??
                          REFERENCE_RESULT.criticalAfter}
                      </strong>
                    </div>
                  </div>
                  <h3>Изменения по районам</h3>
                  <div className="district-result-list">
                    {rows.map((item) => (
                      <button
                        key={item.district_id}
                        onClick={() => selectDistrict(item.district_id)}
                        aria-pressed={item.district_id === districtId}
                      >
                        <span>
                          {
                            districts.find(
                              (district) => district.id === item.district_id,
                            )?.name
                          }
                          <small>
                            {format(item.score_before)} →{" "}
                            {format(item.score_after)}
                          </small>
                        </span>
                        <strong
                          className={
                            item.score_after < item.score_before
                              ? "is-negative"
                              : ""
                          }
                        >
                          {delta(item.score_after - item.score_before)}
                        </strong>
                      </button>
                    ))}
                  </div>
                  <details className="workspace-details">
                    <summary>Все показатели · {current.name}</summary>
                    {METRICS.map((metric) => (
                      <div className="result-metric" key={metric}>
                        <span>{metricNames[metric]}</span>
                        <strong>
                          {format(row?.indicators_before[metric])} →{" "}
                          {format(row?.indicators_after[metric])}
                        </strong>
                      </div>
                    ))}
                  </details>
                  {result && (
                    <details className="workspace-details">
                      <summary>Почему изменились показатели</summary>
                      {result.effects.map((effect, index) => (
                        <p key={index}>
                          <strong>
                            {effect.kind === "synergy"
                              ? "Совместный эффект"
                              : "Эффект меры"}
                            : {delta(effect.delta)}
                          </strong>
                          <br />
                          {
                            districts.find(
                              (district) => district.id === effect.district_id,
                            )?.name
                          }{" "}
                          · {metricNames[effect.indicator_id]}
                          <br />
                          <small>
                            {effect.measure_ids
                              .map(
                                (id) =>
                                  measures.find((measure) => measure.id === id)
                                    ?.name ?? id,
                              )
                              .join(" + ")}
                          </small>
                        </p>
                      ))}
                    </details>
                  )}
                  {simulator.history.length > 0 && (
                    <details className="workspace-details">
                      <summary>
                        История расчётов · {simulator.history.length}
                      </summary>
                      {simulator.history.map((entry) => (
                        <p key={entry.id}>
                          Версия {entry.scenario_version} ·{" "}
                          {new Date(entry.created_at).toLocaleString("ru-RU")}
                          <br />
                          <strong>
                            {format(entry.simulation.score_before)} →{" "}
                            {format(entry.simulation.score_after)}
                          </strong>
                        </p>
                      ))}
                    </details>
                  )}
                  <button
                    className="secondary-action"
                    onClick={() => setConsultantOpen(true)}
                  >
                    <Icon name="chat" />
                    Обсудить результат
                  </button>
                </div>
              )}
            </>
          ) : (
            <>
              <div className="work-panel-heading">
                <span className="section-index">РАЙОН В ФОКУСЕ</span>
                <div className="district-title">
                  <h2>{current.name}</h2>
                  <span>
                    {format(
                      row
                        ? view === "after"
                          ? row.score_after
                          : row.score_before
                        : current.score,
                    )}
                    <small>индекс</small>
                  </span>
                </div>
                <p>{current.profile}</p>
                <div className="district-priorities">
                  {weakest.map((metric) => (
                    <div
                      key={metric}
                      className={
                        values[metric] < threshold ? "is-critical" : ""
                      }
                    >
                      <span>{metricNames[metric]}</span>
                      <strong>
                        {format(values[metric])}
                        <small>/100</small>
                      </strong>
                    </div>
                  ))}
                </div>
                <details className="workspace-details compact">
                  <summary>Все 10 показателей района</summary>
                  {METRICS.map((metric) => (
                    <div className="result-metric" key={metric}>
                      <span>{metricNames[metric]}</span>
                      <strong>{format(values[metric])}</strong>
                    </div>
                  ))}
                  <p>Критический уровень — ниже {threshold}.</p>
                </details>
              </div>
              <div
                className="panel-tabs"
                role="group"
                aria-label="Содержимое панели"
              >
                <button
                  aria-pressed={panelTab === "measures"}
                  onClick={() => setPanelTab("measures")}
                >
                  Добавить решение
                </button>
                <button
                  aria-pressed={panelTab === "plan"}
                  onClick={() => setPanelTab("plan")}
                >
                  Мой план <span>{decisions.length}</span>
                </button>
              </div>
              {panelTab === "measures" ? (
                <div className="catalog-content">
                  <label className="category-select">
                    Направление
                    <select
                      value={category}
                      aria-label="Направление мер"
                      onChange={(event) =>
                        setCategory(event.target.value as typeof category)
                      }
                    >
                      <option value="all">Все направления</option>
                      {Object.entries(CATEGORY_META).map(([id, meta]) => (
                        <option key={id} value={id}>
                          {meta.name}
                        </option>
                      ))}
                    </select>
                  </label>
                  <div className="workspace-measures">
                    {shownMeasures.map((measure) => {
                      const selected = decisions.find(
                        (decision) => decision.measureId === measure.id,
                      );
                      return (
                        <article
                          className={`workspace-measure ${selected ? "is-added" : ""} ${activeMeasure === measure.id ? "is-focused" : ""}`}
                          key={measure.id}
                          style={
                            {
                              "--measure-color":
                                CATEGORY_META[measure.category].color,
                            } as CSSProperties
                          }
                        >
                          <div className="measure-eyebrow">
                            <span>{CATEGORY_META[measure.category].name}</span>
                            <span>
                              {measure.scope === "city"
                                ? "Все районы"
                                : current.name}
                            </span>
                          </div>
                          <h3>{measure.name}</h3>
                          <div className="measure-summary">
                            <span>
                              <strong>{measure.cost}</strong> ед. бюджета
                            </span>
                            <span>Эффект через {measure.lag} кв.</span>
                          </div>
                          <details>
                            <summary>Ожидаемые эффекты</summary>
                            <p className="effect-disclaimer">
                              Справочные значения каталога; итог определяет
                              расчёт.
                            </p>
                            {Object.entries(measure.effects).map(
                              ([metric, value]) => (
                                <p className="measure-effect" key={metric}>
                                  <span>{metricNames[metric as MetricId]}</span>
                                  <strong>{delta(value!)}</strong>
                                </p>
                              ),
                            )}
                          </details>
                          <button
                            className={
                              selected
                                ? "selected-measure-button"
                                : "add-project-button"
                            }
                            disabled={
                              busy ||
                              (!selected && decisions.length >= required)
                            }
                            onClick={() =>
                              selected
                                ? removeMeasure(measure.id)
                                : addMeasure(measure)
                            }
                            aria-label={`${selected ? "Убрать" : "Добавить"} ${measure.name}`}
                          >
                            {selected
                              ? "✓ В плане · убрать"
                              : "+ Добавить в план"}
                          </button>
                        </article>
                      );
                    })}
                  </div>
                </div>
              ) : (
                <div className="plan-content">
                  {decisions.length === 0 ? (
                    <div className="panel-empty">
                      <h3>С чего начнём?</h3>
                      <p>
                        Выбери район и добавь первое решение. Его проект
                        появится на карте.
                      </p>
                      <button
                        className="primary-action"
                        onClick={() => setPanelTab("measures")}
                      >
                        Выбрать решение
                      </button>
                    </div>
                  ) : (
                    decisions.map((decision, index) => {
                      const measure = measures.find(
                        (item) => item.id === decision.measureId,
                      );
                      if (!measure) return null;
                      return (
                        <article
                          className={`plan-project ${activeMeasure === measure.id ? "is-focused" : ""}`}
                          key={measure.id}
                        >
                          <span className="project-number">0{index + 1}</span>
                          <div>
                            <h3>{measure.name}</h3>
                            <p>
                              {measure.cost} ед. · эффект через {measure.lag}{" "}
                              кв.
                            </p>
                            {measure.scope === "district" ? (
                              <label>
                                Район
                                <select
                                  aria-label={`Район проекта ${measure.name}`}
                                  value={decision.districtId}
                                  disabled={busy}
                                  onChange={(event) => {
                                    const id = event.target.value as DistrictId;
                                    editPlan(
                                      decisions.map((item) =>
                                        item.measureId === decision.measureId
                                          ? { ...item, districtId: id }
                                          : item,
                                      ),
                                    );
                                    selectDistrict(id);
                                  }}
                                >
                                  {districts.map((district) => (
                                    <option
                                      key={district.id}
                                      value={district.id}
                                    >
                                      {district.name}
                                    </option>
                                  ))}
                                </select>
                              </label>
                            ) : (
                              <small>
                                Общегородское решение · все пять районов
                              </small>
                            )}
                            <button
                              className="text-action"
                              onClick={() => {
                                selectDistrict(
                                  decision.districtId ?? districtId,
                                );
                                setView("plan");
                                setLayer("projects");
                                setEngine("map");
                                setMobilePanel(false);
                              }}
                            >
                              Показать на карте →
                            </button>
                          </div>
                          <button
                            className="remove-project-button"
                            aria-label={`Удалить из плана ${measure.name}`}
                            disabled={busy}
                            onClick={() => removeMeasure(measure.id)}
                          >
                            <Icon name="close" />
                          </button>
                        </article>
                      );
                    })
                  )}
                  <div className="plan-helpers">
                    <button
                      className="text-action"
                      disabled={busy}
                      onClick={loadExample}
                    >
                      Загрузить пример
                    </button>
                    {decisions.length > 0 && (
                      <button
                        className="text-action"
                        disabled={busy}
                        onClick={() => {
                          editPlan([]);
                          setNotice("План очищен.");
                        }}
                      >
                        Очистить план
                      </button>
                    )}
                  </div>
                </div>
              )}
              <div className="advisor-entry">
                <button
                  className="secondary-action"
                  onClick={() => setConsultantOpen(true)}
                >
                  <Icon name="chat" />
                  Обсудить план с AI
                </button>
                {panelTab === "measures" && (
                  <button
                    className="text-action"
                    disabled={busy}
                    onClick={loadExample}
                  >
                    Попробовать пример
                  </button>
                )}
              </div>
            </>
          )}
        </aside>
        {mobilePanel && (
          <button
            className="mobile-panel-scrim"
            onClick={() => setMobilePanel(false)}
            aria-label="Закрыть панель"
          />
        )}
      </main>

      {simulator.issues.length > 0 && (
        <div className="workspace-errors" role="alert">
          {simulator.issues.map((issue, index) => (
            <span key={index}>{issue}</span>
          ))}
          {simulator.failedAction && (
            <button
              className="text-action"
              onClick={() => {
                void primaryAction();
              }}
            >
              Повторить
            </button>
          )}
        </div>
      )}
      <footer className="workspace-planbar">
        <button
          className="planbar-count"
          onClick={() => {
            setPage("city");
            setPanelTab("plan");
            setMobilePanel(true);
          }}
        >
          <span className="planbar-dots">
            {Array.from({ length: required }, (_, index) => (
              <i
                key={index}
                className={index < decisions.length ? "filled" : ""}
              />
            ))}
          </span>
          <strong>
            Мой план{" "}
            <span>
              {decisions.length}/{required}
            </span>
          </strong>
          <small>
            {live
              ? simulator.hasUnsavedChanges
                ? "Есть несохранённые изменения"
                : "Сохранён"
              : "Демонстрационный черновик"}
          </small>
        </button>
        <div className="planbar-budget">
          <span>
            {live && simulator.validation
              ? "Бюджет · проверен"
              : "Бюджет · оценка"}
          </span>
          <strong className={spent > budget ? "is-negative" : ""}>
            {spent}
            <small> / {budget}</small>
          </strong>
          <div>
            <i style={{ width: `${Math.min(100, (spent / budget) * 100)}%` }} />
          </div>
        </div>
        <div className="planbar-submit">
          <button
            className="primary-action"
            disabled={mainDisabled}
            onClick={() => {
              void primaryAction();
            }}
          >
            {busy ? (
              <>
                <span className="spinner" />
                {simulator.busy === "saving"
                  ? "Сохраняем…"
                  : simulator.busy === "opening"
                    ? "Открываем…"
                    : "Считаем…"}
              </>
            ) : live && simulator.hasUnsavedChanges ? (
              "Сохранить план"
            ) : (
              "Рассчитать результат"
            )}
            <Icon name="arrow" />
          </button>
          <small>
            {live
              ? simulator.isValidating
                ? "Проверяем план…"
                : simulator.hasUnsavedChanges
                  ? "После сохранения доступен расчёт"
                  : `Нужно ${required} решений без нарушений`
              : referenceLoaded
                ? "Готов контрольный пример"
                : "Для расчёта нужен сервер или пример"}
          </small>
        </div>
      </footer>

      <dialog
        ref={dialogRef}
        aria-label="AI-советник города"
        className="consultant-dialog"
        onCancel={() => setConsultantOpen(false)}
        onClose={() => setConsultantOpen(false)}
      >
        <div className="consultant-dialog-top">
          <span>СОВЕТНИК ГОРОДА</span>
          <button
            className="icon-button"
            onClick={() => setConsultantOpen(false)}
            aria-label="Закрыть советника"
          >
            <Icon name="close" />
          </button>
        </div>
        {simulator.hasUnsavedChanges && (
          <p className="inline-note">
            Советник видит сохранённую версию сценария. Сохрани план, чтобы
            обсудить последние изменения.
          </p>
        )}
        <ScenarioConsultantPanel
          scenarioId={live ? (simulator.scenario?.id ?? null) : null}
          live={live}
          onSelectDistrict={(id) => {
            setConsultantOpen(false);
            setPage("city");
            selectDistrict(id);
          }}
          onSelectMeasure={(id) => {
            setConsultantOpen(false);
            setPage("city");
            setPanelTab("measures");
            setCategory("all");
            setActiveMeasure(id);
            setMobilePanel(true);
          }}
        />
      </dialog>
      {notice && (
        <div className="workspace-toast" role="status">
          {notice}
          <button aria-label="Закрыть сообщение" onClick={() => setNotice("")}>
            <Icon name="close" />
          </button>
        </div>
      )}
    </div>
  );
}
