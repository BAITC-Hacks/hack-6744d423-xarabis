import {Readable} from 'node:stream';
import {pipeline} from 'node:stream/promises';

export async function proxyRequest(request, response, target, path) {
  const controller = new AbortController();
  const abort = () => controller.abort();
  response.on('close', abort);
  const timer = setTimeout(abort, 70000);
  try {
    const upstreamUrl = new URL(path, target);
    if (!path.startsWith('/') || path.startsWith('//') || path.includes('\\') || upstreamUrl.origin !== new URL(target).origin) {
      response.writeHead(400).end(); return;
    }
    const chunks = []; let length = 0;
    for await (const chunk of request) {
      length += chunk.length;
      if (length > 1_000_000) {response.writeHead(413).end(); return;}
      chunks.push(chunk);
    }
    const upstream = await fetch(upstreamUrl, {
      method: request.method,
      headers: {Accept: request.headers.accept ?? 'application/json', ...(chunks.length ? {'Content-Type':'application/json'} : {})},
      body: chunks.length ? Buffer.concat(chunks) : undefined,
      signal: controller.signal,
    });
    response.writeHead(upstream.status, {
      'Content-Type': upstream.headers.get('content-type') ?? 'application/json',
      'Cache-Control': 'no-cache, no-transform', 'X-Accel-Buffering':'no',
    });
    response.flushHeaders();
    if (upstream.body) await pipeline(Readable.fromWeb(upstream.body), response);
    else response.end();
  } catch {
    if (!response.headersSent && !response.destroyed) {
      response.writeHead(502, {'Content-Type':'application/json'}).end(JSON.stringify({error:{code:'upstream_unavailable',message:'Сервис недоступен. Проверь запуск Python API и адреса в frontend/.env.'}}));
    } else if (!response.destroyed) response.destroy();
  } finally { clearTimeout(timer); response.off('close', abort); }
}
