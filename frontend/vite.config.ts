import { defineConfig } from "vite";
import type { Connect, Plugin } from "vite";
import react from "@vitejs/plugin-react";
import { createReadStream, existsSync, statSync } from "node:fs";
import { resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";

function unityGzipAssets(): Plugin {
  const webRoot = fileURLToPath(new URL(".", import.meta.url));
  const unityRoot = resolve(webRoot, "public/unity");
  const contentTypes: Record<string, string> = {
    "Build/unity.data": "application/octet-stream",
    "Build/unity.framework.js": "application/javascript",
    "Build/unity.loader.js": "application/javascript",
    "Build/unity.wasm": "application/wasm",
    "geo/astana-atlas.json": "application/json; charset=utf-8",
  };

  const serveCompressedAsset: Connect.NextHandleFunction = (request, response, next) => {
    const pathname = new URL(request.url ?? "/", "http://localhost").pathname;
    const prefix = "/unity/";
    if (!pathname.startsWith(prefix)) return next();

    let requestedName: string;
    try { requestedName = decodeURIComponent(pathname.slice(prefix.length)); }
    catch { response.statusCode = 400; response.end(); return; }
    const isExplicitGzip = requestedName.endsWith(".gz");
    const sourceName = isExplicitGzip ? requestedName.slice(0, -3) : requestedName;
    if (!Object.hasOwn(contentTypes, sourceName)) return next();

    const rawPath = resolve(unityRoot, sourceName);
    const gzipPath = `${rawPath}.gz`;
    if (!rawPath.startsWith(`${unityRoot}${sep}`)) return next();
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

export default defineConfig({
  plugins: [react(), unityGzipAssets()],
  server: {
    port: 5173,
    proxy: {
      "/api/v1": {
        target: process.env.PYTHON_API_URL ?? "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
});
