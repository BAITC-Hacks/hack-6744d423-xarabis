import { useState, type FormEvent } from "react";
import { demoConsultantClient, type ConsultantBlock, type ConsultantClient, type ConsultantResponse } from "./consultant";

function ResponseGroup({ title, items }: { title: string; items: ConsultantBlock[] }) {
  if (items.length === 0) return null;
  return <div className="consultant-group"><strong>{title}</strong>{items.map((item, index) => <p key={`${index}-${item.title}`}><b>{item.title}</b> — {item.explanation}</p>)}</div>;
}

export function ConsultantPanel({ client = demoConsultantClient }: { client?: ConsultantClient }) {
  const [message, setMessage] = useState("");
  const [lastMessage, setLastMessage] = useState("");
  const [response, setResponse] = useState<ConsultantResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function send(text: string) {
    if (!text.trim() || busy) return;
    setBusy(true);
    setError("");
    setLastMessage(text.trim());
    setResponse(null);
    let timer: number | undefined;
    try {
      const next = await Promise.race([
        client.sendMessage(text.trim()),
        new Promise<never>((_, reject) => { timer = window.setTimeout(() => reject(new Error("Ответ не пришёл за 45 секунд. Попробуй снова.")), 45_000); }),
      ]);
      setResponse(next);
      setMessage("");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Консультант не ответил. Попробуй снова.");
    } finally {
      if (timer !== undefined) window.clearTimeout(timer);
      setBusy(false);
    }
  }

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void send(message);
  }

  return <section className="consultant-panel" aria-label="AI-консультант">
    <div className="consultant-head"><div><span className="section-index">04 / КОНСУЛЬТАНТ</span><h2>Спроси о своём плане</h2></div><span className="consultant-demo-badge">МАКЕТ · AI НЕ ПОДКЛЮЧЕН</span></div>
    <p className="consultant-intro">Этот экран готов для ответа агента. До появления маршрута чата в Python API он показывает явно обозначенный макет.</p>
    <form onSubmit={onSubmit} className="consultant-form"><label htmlFor="consultant-message">Вопрос консультанту</label><div><input id="consultant-message" value={message} onChange={(event) => setMessage(event.target.value)} placeholder="Какие риски у моего плана?" maxLength={4000} /><button disabled={busy || !message.trim()}>{busy ? "Ждём…" : "Отправить"}</button></div></form>
    {error && <div className="consultant-error" role="alert">{error} <button onClick={() => { void send(lastMessage); }}>Повторить</button></div>}
    {response && <div className="consultant-response" aria-live="polite"><p>{response.answer}</p><ResponseGroup title="Сильные стороны" items={response.strengths} /><ResponseGroup title="Риски" items={response.risks} /><ResponseGroup title="Рекомендации" items={response.recommendations} />{response.follow_up_question && <p className="consultant-followup">{response.follow_up_question}</p>}</div>}
  </section>;
}
