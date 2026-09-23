import { defineConfig, loadEnv } from "vite";
import type { Connect, Plugin } from "vite";
import react from "@vitejs/plugin-react";
import { createReadStream, existsSync, statSync } from "node:fs";
import { resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";

function unityGzipAssets(): Plugin {
  const webRoot = fileURLToPath(new URL(".", import.meta.url));
  const buildRoot = resolve(webRoot, "public/unity/Build");
  const contentTypes: Record<string, string> = {
    "unity.data": "application/octet-stream",
    "unity.framework.js": "application/javascript",
    "unity.loader.js": "application/javascript",
    "unity.wasm": "application/wasm",
  };

  const serveCompressedAsset: Connect.NextHandleFunction = (request, response, next) => {
    const pathname = new URL(request.url ?? "/", "http://localhost").pathname;
    const prefix = "/unity/Build/";
    if (!pathname.startsWith(prefix)) return next();

    const requestedName = decodeURIComponent(pathname.slice(prefix.length));
    const isExplicitGzip = requestedName.endsWith(".gz");
    const sourceName = isExplicitGzip ? requestedName.slice(0, -3) : requestedName;
    if (!Object.hasOwn(contentTypes, sourceName)) return next();

    const rawPath = resolve(buildRoot, sourceName);
    const gzipPath = `${rawPath}.gz`;
    if (!rawPath.startsWith(`${buildRoot}${sep}`)) return next();
    const acceptsGzip = /(?:^|,)\s*gzip(?:\s*;[^,]*)?(?:,|$)/i.test(request.headers["accept-encoding"] ?? "");
    const serveGzip = isExplicitGzip || (acceptsGzip && existsSync(gzipPath));
    const filePath = serveGzip ? gzipPath : rawPath;
    if (!existsSync(filePath)) return next();

    response.statusCode = 200;
    response.setHeader("Content-Type", contentTypes[sourceName]);
    response.setHeader("Vary", "Accept-Encoding");
    if (serveGzip) response.setHeader("Content-Encoding", "gzip");
    response.setHeader("Content-Length", statSync(filePath).size);
    response.setHeader("Cache-Control", "public, max-age=3600");
    if (request.method === "HEAD") return response.end();
    createReadStream(filePath).pipe(response);
  };

  return {
    name: "hackalem-unity-gzip-assets",
    configureServer(server) {
      server.middlewares.use(serveCompressedAsset);
    },
    configurePreviewServer(server) {
      server.middlewares.use(serveCompressedAsset);
    },
  };
}

export default defineConfig(({mode}) => {
  const env = {...loadEnv(mode, fileURLToPath(new URL('.', import.meta.url)), ''), ...process.env};
  const proxy = {
    '/api/v1': {target: env.PYTHON_API_URL ?? 'http://127.0.0.1:8000', changeOrigin: true},
    '/api/ai': {target: env.AI_API_URL ?? 'http://127.0.0.1:8001', changeOrigin: true, rewrite: (path: string) => path.replace(/^\/api\/ai/, '')},
  };
  return {
  plugins: [react(), unityGzipAssets()],
  server: {
    port: 5173,
    proxy,
  },
  preview: {proxy},
  };
});
