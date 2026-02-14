import "dotenv/config";
import express from "express";
import { createServer } from "http";
import net from "net";
import { createProxyMiddleware } from "http-proxy-middleware";
import { createExpressMiddleware } from "@trpc/server/adapters/express";
import { registerOAuthRoutes } from "./oauth";
import { appRouter } from "../routers";
import { createContext } from "./context";
import { serveStatic, setupVite } from "./vite";

// CAIP backend: proxy /v1/* to Python FastAPI (port 8000)
const CAIP_BACKEND_URL = process.env.CAIP_BACKEND_URL || "http://127.0.0.1:8000";

function isPortAvailable(port: number): Promise<boolean> {
  return new Promise(resolve => {
    const server = net.createServer();
    server.listen(port, () => {
      server.close(() => resolve(true));
    });
    server.on("error", () => resolve(false));
  });
}

async function findAvailablePort(startPort: number = 3000): Promise<number> {
  for (let port = startPort; port < startPort + 20; port++) {
    if (await isPortAvailable(port)) {
      return port;
    }
  }
  throw new Error(`No available port found starting from ${startPort}`);
}

async function startServer() {
  const app = express();
  const server = createServer(app);
  // Configure body parser with larger size limit for file uploads
  app.use(express.json({ limit: "50mb" }));
  app.use(express.urlencoded({ limit: "50mb", extended: true }));
  // OAuth callback under /api/oauth/callback
  registerOAuthRoutes(app);
  // CAIP: proxy /v1/* to Python FastAPI backend
  // Express strips mount path, so req.url becomes /chat for /v1/chat - restore /v1 prefix
  app.use(
    "/v1",
    createProxyMiddleware({
      target: CAIP_BACKEND_URL,
      changeOrigin: true,
      pathRewrite: { "^/(.*)": "/v1/$1" },
      onError: (err, req, res) => {
        console.error("[CAIP proxy error]", err.message);
        (res as import("express").Response).status(502).json({
          error: "CAIP backend unavailable",
          detail: "Start the Python backend with: python -m uvicorn server.caip_backend:app --host 0.0.0.0 --port 8000",
        });
      },
    })
  );
  // tRPC API
  app.use(
    "/api/trpc",
    createExpressMiddleware({
      router: appRouter,
      createContext,
    })
  );
  // development mode uses Vite, production mode uses static files
  if (process.env.NODE_ENV === "development") {
    await setupVite(app, server);
  } else {
    serveStatic(app);
  }

  const preferredPort = parseInt(process.env.PORT || "3000");
  const port = await findAvailablePort(preferredPort);

  if (port !== preferredPort) {
    console.log(`Port ${preferredPort} is busy, using port ${port} instead`);
  }

  server.listen(port, () => {
    console.log(`Server running on http://localhost:${port}/`);
  });
}

startServer().catch(console.error);
