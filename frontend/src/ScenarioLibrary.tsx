import { useEffect, useState } from "react";
import { cityApi, type ScenarioPage } from "./cityApi";

export function ScenarioLibrary({
  live,
  currentId,
  locked,
  onOpen,
  onExample,
}: {
  live: boolean;
  currentId?: string;
  locked: boolean;
  onOpen: (id?: string) => Promise<void>;
  onExample: () => void;
}) {
  const [page, setPage] = useState<ScenarioPage | null>(null);
  const [offset, setOffset] = useState(0);
  const [attempt, setAttempt] = useState(0);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  useEffect(() => {
    if (!live) return;
    let active = true;
    setLoading(true);
    setError("");
    cityApi
      .listScenarios(12, offset)
      .then((data) => {
        if (active) setPage(data);
      })
      .catch(() => {
        if (active) setError("Не удалось загрузить сценарии. Повтори запрос.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [live, currentId, offset, attempt]);
  return (
    <section className="scenario-library" aria-label="Сценарии">
      <div className="page-intro">
        <div>
          <span className="section-index">РАБОЧИЕ ПЛАНЫ</span>
          <h1>Сценарии развития</h1>
          <p>Возвращайся к сохранённым решениям и их результатам.</p>
        </div>
        <button
          className="primary-action"
          disabled={!live || locked}
          onClick={() => {
            void onOpen();
          }}
        >
          + Новый сценарий
        </button>
      </div>
      {locked && (
        <p className="inline-note">
          Сначала сохрани текущий план, чтобы переключиться на другой сценарий.
        </p>
      )}
      {!live ? (
        <div className="empty-workspace">
          <span className="empty-symbol">01</span>
          <h2>Начни с примера</h2>
          <p>
            Без подключения к серверу доступен контрольный сценарий. Сохранённые
            сценарии появятся после подключения.
          </p>
          <button className="primary-action" onClick={onExample}>
            Открыть контрольный пример
          </button>
        </div>
      ) : (
        <>
          {loading && <p role="status">Загружаем сценарии…</p>}
          {error && (
            <p role="alert">
              {error}{" "}
              <button
                className="text-action"
                onClick={() => setAttempt((value) => value + 1)}
              >
                Повторить
              </button>
            </p>
          )}
          {!loading && !error && page?.items.length === 0 && (
            <p>Сохранённых сценариев пока нет. Создай первый план.</p>
          )}
          <div className="scenario-grid">
            {!error &&
              page?.items.map((scenario) => (
                <article
                  key={scenario.id}
                  className={`scenario-item ${currentId === scenario.id ? "is-current" : ""}`}
                >
                  <span className="section-index">
                    {currentId === scenario.id
                      ? "ТЕКУЩИЙ"
                      : scenario.status === "calculated"
                        ? "РАССЧИТАН"
                        : "ЧЕРНОВИК"}
                  </span>
                  <h2>План · {scenario.id.slice(0, 8)}</h2>
                  <p>
                    {scenario.decisions.length} решений · версия{" "}
                    {scenario.version}
                  </p>
                  <time dateTime={scenario.updated_at}>
                    {new Date(scenario.updated_at).toLocaleString("ru-RU")}
                  </time>
                  <button
                    className="secondary-action"
                    disabled={locked || loading}
                    onClick={() => {
                      void onOpen(scenario.id);
                    }}
                  >
                    Открыть сценарий →
                  </button>
                </article>
              ))}
          </div>
          {page && page.total > page.limit && (
            <div className="scenario-pagination">
              <button
                className="secondary-action"
                disabled={loading || offset === 0}
                onClick={() => setOffset(Math.max(0, offset - 12))}
              >
                Назад
              </button>
              <span>
                {offset + 1}–{Math.min(offset + 12, page.total)} из {page.total}
              </span>
              <button
                className="secondary-action"
                disabled={loading || offset + 12 >= page.total}
                onClick={() => setOffset(offset + 12)}
              >
                Далее
              </button>
            </div>
          )}
        </>
      )}
    </section>
  );
}
