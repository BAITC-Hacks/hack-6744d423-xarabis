import type { ConsultantResponse } from './consultant';

function validReport(value: unknown): value is ConsultantResponse {
  if (!value || typeof value !== 'object') return false;
  const row = value as Record<string, unknown>;
  return typeof row.answer === 'string' && row.answer.length > 0
    && ['strengths', 'risks', 'consequences', 'recommendations'].every(key => Array.isArray(row[key])
      && (row[key] as unknown[]).every(item => !!item && typeof item === 'object'
        && typeof (item as Record<string, unknown>).title === 'string'
        && typeof (item as Record<string, unknown>).explanation === 'string'))
    && (row.follow_up_question === null || typeof row.follow_up_question === 'string');
}
export async function readReportStream(response: Response, onDelta: (text: string) => void): Promise<ConsultantResponse> {
  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    throw new Error(payload?.error?.message ?? `ИИ-сервис недоступен (${response.status})`);
  }
  if (!response.body || !response.headers.get('content-type')?.includes('text/event-stream')) throw new Error('Некорректный формат потока ИИ');
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  try {
    while (true) {
      const { value, done } = await reader.read();
      buffer += decoder.decode(value, { stream: !done });
      if (buffer.length > 250_000) throw new Error('Ответ ИИ превышает допустимый размер');
      let boundary: RegExpExecArray | null;
      while ((boundary = /\r?\n\r?\n/.exec(buffer))) {
        const frame = buffer.slice(0, boundary.index);
        buffer = buffer.slice(boundary.index + boundary[0].length);
        const lines = frame.split(/\r?\n/);
        const event = lines.find(line => line.startsWith('event:'))?.slice(6).trim();
        const data = lines.filter(line => line.startsWith('data:')).map(line => line.slice(5).trimStart()).join('\n');
        if (!data || !event) continue;
        const payload = JSON.parse(data);
        if (event === 'error') throw new Error(payload?.error?.message ?? 'ИИ не смог завершить ответ');
        if (event === 'answer_delta' && typeof payload.delta === 'string') onDelta(payload.delta);
        if (event === 'complete') {
          if (!validReport(payload)) throw new Error('Некорректный итоговый ответ ИИ');
          return payload;
        }
      }
      if (done) throw new Error('Поток оборвался. Ответ не завершён — повтори запрос.');
    }
  } finally {
    await reader.cancel().catch(() => {});
    reader.releaseLock();
  }
}
