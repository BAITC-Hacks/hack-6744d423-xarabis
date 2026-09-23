import { useEffect, useRef, useState, type FormEvent } from 'react';
import type { ConsultantBlock, ConsultantResponse } from './consultant';
import { readReportStream } from './reportStream';

function ResponseGroup({ title, items }: { title: string; items: ConsultantBlock[] }) {
  if (!items.length) return null;
  return <div className="consultant-group"><strong>{title}</strong>{items.map((item, i) => <p key={i}><b>{item.title}</b> — {item.explanation}</p>)}</div>;
}
export function ConsultantPanel({ context, sandbox = false, sandboxVersion = 'v1' }: { context: unknown; sandbox?: boolean; sandboxVersion?: 'v1' | 'v2' }) {
  const [message, setMessage] = useState('');
  const [response, setResponse] = useState<ConsultantResponse | null>(null);
  const [preview, setPreview] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [lastMessage, setLastMessage] = useState('');
  const [history, setHistory] = useState<{role: 'user' | 'assistant'; content: string}[]>([]);
  const pending = useRef<AbortController | null>(null);
  useEffect(() => () => pending.current?.abort(), []);
  async function send(text: string) {
    if (!text.trim() || pending.current || !context) return;
    const controller = new AbortController();
    pending.current = controller;
    const timer = window.setTimeout(() => controller.abort('timeout'), 65_000);
    setBusy(true); setError(''); setPreview(''); setResponse(null); setLastMessage(text.trim());
    try {
      const stream = await fetch(`/api/ai/${sandbox ? sandboxVersion === 'v2' ? 'sandbox/v2/' : 'sandbox/' : ''}chat/stream`, {
        method: 'POST', headers: {'Content-Type': 'application/json', Accept: 'text/event-stream'},
        body: JSON.stringify({message: text.trim(), history, context}), signal: controller.signal,
      });
      const report = await readReportStream(stream, delta => setPreview(old => old + delta));
      setResponse(report); setMessage('');
      setHistory(old => [...old, {role: 'user' as const, content: text.trim()}, {role: 'assistant' as const, content: report.answer.slice(0, 4000)}].slice(-20));
    } catch (reason) {
      setError(controller.signal.aborted ? controller.signal.reason === 'timeout' ? 'Время ожидания истекло. Повтори запрос.' : 'Ответ остановлен.' : reason instanceof Error ? reason.message : 'Нет связи с ИИ-сервисом');
    } finally { window.clearTimeout(timer); pending.current = null; setBusy(false); }
  }
  function submit(event: FormEvent) { event.preventDefault(); void send(message); }
  return <section className="consultant-panel" aria-label="AI-консультант">
    <div className="consultant-head"><div><span className="section-index">ГОРОДСКОЙ СОВЕТНИК</span><h2>Большие решения. Второе мнение.</h2></div><span className="consultant-demo-badge">✦ AI · STREAM</span></div>
    <p className="consultant-intro">{sandbox ? 'Советник видит показатели Нового Берега и доступные улучшения.' : 'Советник получает текущий план и последний расчёт Астаны.'} Числа рассчитывает симулятор.</p>
    <div className="advisor-prompts">{['С чего начать?', 'Какие риски у моего плана?'].map(text => <button key={text} disabled={busy || !context} onClick={() => void send(text)}>{text} ↗</button>)}</div>
    {lastMessage && <p className="advisor-question">{lastMessage}</p>}
    {(preview || busy) && !response && <div className="consultant-response"><p>{preview || 'Советник изучает город…'}{busy && <span className="stream-cursor">▍</span>}</p>{!busy && error && <small>Незавершённый ответ</small>}</div>}
    {response && <div className="consultant-response"><p>{response.answer}</p><ResponseGroup title="Сильные стороны" items={response.strengths}/><ResponseGroup title="Риски" items={response.risks}/><ResponseGroup title="Рекомендации" items={response.recommendations}/>{response.follow_up_question && <p>{response.follow_up_question}</p>}</div>}
    {error && <p className="consultant-error" role="alert">{error}</p>}
    <form className="consultant-form" onSubmit={submit}><label htmlFor={sandbox ? 'sandbox-question' : 'astana-question'}>Вопрос консультанту</label><div><input id={sandbox ? 'sandbox-question' : 'astana-question'} value={message} onChange={e => setMessage(e.target.value)} maxLength={4000} placeholder="Как сделать город лучше?"/>{busy ? <button type="button" onClick={() => pending.current?.abort()}>Стоп</button> : <button disabled={!context || !message.trim()}>Отправить ↗</button>}</div></form>
  </section>;
}
