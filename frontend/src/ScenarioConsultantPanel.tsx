import { useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import { ApiRequestError } from "./cityApi";
import {
  createConsultantClient,
  type ChatMessage,
  type ConsultantBlock,
  type ConsultantResponse,
} from "./consultant";
import { DISTRICTS, MEASURES, type DistrictId } from "./caseData";
import { getScenarioAutomaticAnalysis } from "./automaticAnalysis";
const AUTO_QUESTION = "Оцени мой сценарий по последнему расчёту: проанализируй выбранные решения, их стоимость и влияние на показатели. Дай итоговую оценку, сильные стороны, риски, возможные последствия и рекомендации. Отделяй результаты модели от предположений.";

function ResponseGroup({
  title,
  items,
}: {
  title: string;
  items: ConsultantBlock[];
}) {
  if (items.length === 0) return null;
  return (
    <div className="consultant-group">
      <strong>{title}</strong>
      {items.map((item, index) => (
        <p key={`${index}-${item.title}`}>
          <b>{item.title}</b> — {item.explanation}
        </p>
      ))}
    </div>
  );
}

function Report({ response }: { response: ConsultantResponse }) {
  return (
    <div className="consultant-response">
      <p>{response.answer}</p>
      <ResponseGroup title="Сильные стороны" items={response.strengths} />
      <ResponseGroup title="Риски" items={response.risks} />
      <ResponseGroup title="Возможные последствия" items={response.consequences} />
      <ResponseGroup title="Рекомендации" items={response.recommendations} />
      {response.follow_up_question && (
        <p className="consultant-followup">{response.follow_up_question}</p>
      )}
    </div>
  );
}

function describeChatError(reason: unknown) {
  if (reason instanceof ApiRequestError) {
    if (reason.code === "ai_not_configured")
      return "AI-сервис ещё не настроен на Python-сервере. Сообщи команде backend.";
    if (reason.code === "ai_timeout")
      return "AI-сервис не ответил вовремя. Можно повторить запрос вручную.";
    if (reason.code === "ai_unavailable")
      return "AI-сервис временно недоступен. Попробуй позже.";
    if (reason.code === "scenario_not_found")
      return "Сценарий не найден. Переподключи API и открой новый сценарий.";
    return reason.message;
  }
  if (reason instanceof DOMException && reason.name === "AbortError")
    return "Время ожидания ответа истекло. Проверь историю перед повтором.";
  return "Не удалось связаться с консультантом. Проверь Python API и повтори запрос вручную.";
}

export function ScenarioConsultantPanel({
  scenarioId,
  live,
  scenarioVersion,
  automaticAnalysis,
  onSelectDistrict,
  onSelectMeasure,
}: {
  scenarioId: string | null;
  live: boolean;
  scenarioVersion: number | null;
  automaticAnalysis: {scenarioId: string; version: number} | null;
  onSelectDistrict?: (id: DistrictId) => void;
  onSelectMeasure?: (id: string) => void;
}) {
  const client = useMemo(
    () => (scenarioId ? createConsultantClient(scenarioId) : null),
    [scenarioId],
  );
  const contextKey = `${scenarioId}:${scenarioVersion}`;
  const scenarioRef = useRef(contextKey);
  scenarioRef.current = contextKey;
  const mounted = useRef(true);
  const pendingRequest = useRef<AbortController | null>(null);
  const automatic = getScenarioAutomaticAnalysis();
  const [message, setMessage] = useState("");
  const [lastMessage, setLastMessage] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [pendingAnswer, setPendingAnswer] = useState<{
    question: string;
    report: ConsultantResponse;
  } | null>(null);
  const [historyBusy, setHistoryBusy] = useState(false);
  const [historyError, setHistoryError] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    mounted.current = true;
    pendingRequest.current?.abort();
    pendingRequest.current = null;
    setMessages([]);
    setPendingAnswer(null);
    setError("");
    setHistoryError("");
    setHistoryBusy(false);
    setBusy(false);
    setLastMessage("");
    if (!live || !client) return () => { mounted.current = false; };
    const controller = new AbortController();
    setHistoryBusy(true);
    client
      .getMessages(controller.signal)
      .then((history) => {
        if (!controller.signal.aborted) setMessages(history);
      })
      .catch((reason) => {
        if (!controller.signal.aborted)
          setHistoryError(describeChatError(reason));
      })
      .finally(() => {
        if (!controller.signal.aborted) setHistoryBusy(false);
      });
    return () => { mounted.current = false; controller.abort(); pendingRequest.current?.abort(); };
  }, [client, live, scenarioVersion]);

  async function refreshHistory() {
    if (!client || !live || !scenarioId) return;
    const id = contextKey;
    setHistoryBusy(true);
    setHistoryError("");
    try {
      const history = await client.getMessages();
      if (!mounted.current || scenarioRef.current !== id) return;
      setMessages(history);
      setPendingAnswer(null);
    } catch (reason) {
      if (mounted.current && scenarioRef.current === id)
        setHistoryError(describeChatError(reason));
    } finally {
      if (mounted.current && scenarioRef.current === id) setHistoryBusy(false);
    }
  }

  async function send(text: string) {
    if (!text.trim() || pendingRequest.current || !live || !client || !scenarioId) return;
    const id = contextKey;
    const question = text.trim();
    setBusy(true);
    setError("");
    setLastMessage(question);
    const controller = new AbortController();
    pendingRequest.current = controller;
    const timer = window.setTimeout(() => controller.abort(), 65_000);
    try {
      const report = await client.sendMessage(question, controller.signal);
      if (!mounted.current || scenarioRef.current !== id) return;
      setPendingAnswer({ question, report });
      setMessage("");
      await refreshHistory();
    } catch (reason) {
      if (mounted.current && scenarioRef.current === id) setError(describeChatError(reason));
    } finally {
      window.clearTimeout(timer);
      if (pendingRequest.current === controller) pendingRequest.current = null;
      if (mounted.current && scenarioRef.current === id) setBusy(false);
    }
  }

  useEffect(() => {
    if (!automaticAnalysis || !live || busy || historyBusy
      || automaticAnalysis.scenarioId !== scenarioId
      || automaticAnalysis.version !== scenarioVersion) return;
    // Only explicit successful calculation supplies this trigger, never restore/render.
    void automatic.run(contextKey, () => send(AUTO_QUESTION));
  }, [automaticAnalysis, scenarioId, scenarioVersion, live, busy, historyBusy]);

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void send(message);
  }

  function contextLinks(text: string) {
    const mentionedDistricts = DISTRICTS.filter((district) =>
      text
        .toLocaleLowerCase("ru-RU")
        .includes(district.name.toLocaleLowerCase("ru-RU")),
    );
    const mentionedMeasures = MEASURES.filter((measure) =>
      new RegExp(`\\b${measure.id}\\b`).test(text),
    );
    return (
      <div className="consultant-context-links">
        {onSelectDistrict &&
          mentionedDistricts.map((district) => (
            <button
              type="button"
              key={district.id}
              onClick={() => onSelectDistrict(district.id)}
            >
              На карте: {district.name}
            </button>
          ))}
        {onSelectMeasure &&
          mentionedMeasures.map((measure) => (
            <button
              type="button"
              key={measure.id}
              onClick={() => onSelectMeasure(measure.id)}
            >
              Мера {measure.id}
            </button>
          ))}
      </div>
    );
  }

  return (
    <section className="consultant-panel" aria-label="AI-консультант">
      <div className="consultant-head">
        <div>
          <span className="section-index">04 / КОНСУЛЬТАНТ</span>
          <h2>Спроси о своём плане</h2>
        </div>
        <span
          className={`consultant-demo-badge ${live && scenarioId ? "is-live" : ""}`}
        >
          {live && scenarioId ? "AI · PYTHON API" : "API НЕДОСТУПЕН"}
        </span>
      </div>
      <p className="consultant-intro">
        {live && scenarioId
          ? "Вопрос и история хранятся в сценарии. Контекст плана и расчёта собирает сервер; ответ может занять до 45 секунд."
          : "Для разговора с AI запусти Python API и подключи его в шапке. Деморежим не выдумывает ответ консультанта."}
      </p>
      {automaticAnalysis?.scenarioId === scenarioId
        && automaticAnalysis?.version === scenarioVersion && live && (
        <div className="advisor-prompts">
          <button disabled={busy || historyBusy} onClick={() => void send(AUTO_QUESTION)}>
            Повторить оценку сценария
          </button>
        </div>
      )}
      {live && scenarioId && (
        <div className="consultant-history" aria-live="polite">
          {historyBusy && messages.length === 0 && (
            <p className="consultant-empty">Загружаем историю…</p>
          )}
          {!historyBusy &&
            messages.length === 0 &&
            !pendingAnswer &&
            !historyError && (
              <p className="consultant-empty">
                В этом сценарии диалог ещё не начат.
              </p>
            )}
          {messages.map((item) => (
            <article
              className={`consultant-message is-${item.role}`}
              key={item.id}
            >
              <span className="consultant-speaker">
                {item.role === "user" ? "Твой вопрос" : "AI-консультант"}
              </span>
              {item.role === "assistant" && item.report ? (
                <Report response={item.report} />
              ) : (
                <p>{item.content}</p>
              )}
              {item.role === "assistant" &&
                contextLinks(
                  item.report ? JSON.stringify(item.report) : item.content,
                )}
            </article>
          ))}
          {pendingAnswer && (
            <>
              <article className="consultant-message is-user">
                <span className="consultant-speaker">Твой вопрос</span>
                <p>{pendingAnswer.question}</p>
              </article>
              <article className="consultant-message is-assistant">
                <span className="consultant-speaker">
                  AI-консультант · ответ получен
                </span>
                <Report response={pendingAnswer.report} />
              </article>
            </>
          )}
        </div>
      )}
      {historyError && (
        <div className="consultant-error" role="alert">
          История: {historyError}{" "}
          <button
            type="button"
            onClick={() => {
              void refreshHistory();
            }}
          >
            Обновить
          </button>
        </div>
      )}
      <form onSubmit={onSubmit} className="consultant-form">
        <label htmlFor="consultant-message">Вопрос консультанту</label>
        <div>
          <input
            id="consultant-message"
            value={message}
            onChange={(event) => setMessage(event.target.value)}
            placeholder="Какие риски у моего плана?"
            maxLength={4000}
          />
          <button disabled={busy || !message.trim() || !live || !scenarioId}>
            {busy ? "Ждём…" : "Отправить"}
          </button>
        </div>
      </form>
      {error && (
        <div className="consultant-error" role="alert">
          {error}{" "}
          {lastMessage && (
            <button
              type="button"
              onClick={() => {
                void send(lastMessage);
              }}
            >
              Повторить вручную
            </button>
          )}
        </div>
      )}
    </section>
  );
}
