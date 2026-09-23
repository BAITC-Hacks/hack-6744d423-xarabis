import { createReadStream } from "node:fs";
import { stat } from "node:fs/promises";
import { createServer } from "node:http";
import { resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(fileURLToPath(new URL("./dist/", import.meta.url)));
const port = Number(process.env.PORT ?? 3000);
const pythonApiUrl = process.env.PYTHON_API_URL ?? "http://127.0.0.1:8000";
const unityAssets = {
  "unity.loader.js": "application/javascript",
  "unity.data": "application/octet-stream",
  "unity.framework.js": "application/javascript",
  "unity.wasm": "application/wasm",
};
const mimeTypes = {
  ".html": "text/html; charset=utf-8",
  ".js": "application/javascript",
  ".css": "text/css; charset=utf-8",
  ".svg": "image/svg+xml",
  ".geojson": "application/geo+json; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".ico": "image/x-icon",
};

async function sendFile(response, filename, headers = {}) {
  try {
    const info = await stat(filename);
    if (!info.isFile()) return false;
    response.writeHead(200, { "Content-Length": info.size, ...headers });
    createReadStream(filename).pipe(response);
    return true;
  } catch {
    return false;
  }
}

createServer(async (request, response) => {
  const pathname = new URL(request.url ?? "/", "http://localhost").pathname;
  if (pathname.startsWith("/api/v1/")) {
    try {
      const chunks = [];
      for await (const chunk of request) chunks.push(chunk);
      const upstream = await fetch(new URL(request.url, pythonApiUrl), {
        method: request.method,
        headers: { Accept: "application/json", ...(chunks.length ? { "Content-Type": "application/json" } : {}) },
        body: chunks.length ? Buffer.concat(chunks) : undefined,
      });
      response.writeHead(upstream.status, { "Content-Type": upstream.headers.get("content-type") ?? "application/json", "Cache-Control": "no-store" });
      response.end(Buffer.from(await upstream.arrayBuffer()));
    } catch {
      response.writeHead(502, { "Content-Type": "application/json" });
      response.end(JSON.stringify({ error: { code: "upstream_unavailable", message: "Python API сейчас недоступен" } }));
    }
    return;
  }

  const unityName = pathname.startsWith("/unity/Build/") ? pathname.slice("/unity/Build/".length) : "";
  if (Object.hasOwn(unityAssets, unityName)) {
    if (!/\bgzip\b/i.test(request.headers["accept-encoding"] ?? "")) {
      response.writeHead(406).end();
      return;
    }
    const file = resolve(root, "unity/Build", `${unityName}.gz`);
    if (await sendFile(response, file, {
      "Content-Type": unityAssets[unityName],
      "Content-Encoding": "gzip",
      Vary: "Accept-Encoding",
      "Cache-Control": "public, max-age=3600",
    })) return;
    response.writeHead(404).end();
    return;
  }

  let decoded;
  try {
    decoded = decodeURIComponent(pathname);
  } catch {
    response.writeHead(400).end();
    return;
  }
  const target = resolve(root, `.${decoded}`);
  if (!target.startsWith(`${root}${sep}`) && target !== root) {
    response.writeHead(403).end();
    return;
  }
  const extension = target.slice(target.lastIndexOf("."));
  if ((extension === ".geojson" || extension === ".json") && /\bgzip\b/i.test(request.headers["accept-encoding"] ?? "")) {
    if (await sendFile(response, `${target}.gz`, {
      "Content-Type": mimeTypes[extension],
      "Content-Encoding": "gzip",
      Vary: "Accept-Encoding",
    })) return;
  }
  if (await sendFile(response, target, { "Content-Type": mimeTypes[extension] ?? "application/octet-stream" })) return;
  if (pathname.startsWith("/assets/") || pathname.startsWith("/unity/") || pathname.startsWith("/data/")) {
    response.writeHead(404).end();
    return;
  }
  await sendFile(response, resolve(root, "index.html"), { "Content-Type": mimeTypes[".html"] });
}).listen(port, () => {
  console.log(`frontend: http://127.0.0.1:${port}`);
});
