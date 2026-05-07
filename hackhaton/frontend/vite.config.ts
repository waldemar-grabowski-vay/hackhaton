import path from "node:path";
import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

// In dev the backend's auth dependency requires `X-Vay-User` (FR-026 / R4).
// Production sets the header at the SSO-terminating reverse proxy; in dev
// we inject it from `VAYOBD_DEV_USER` (default `dev@local`) so every
// proxied `/api/*` request looks indistinguishable from a real one.
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), ["VAYOBD_", "VITE_"]);
  const devUser =
    env.VAYOBD_DEV_USER ?? process.env.VAYOBD_DEV_USER ?? "dev@local";

  return {
    plugins: [react()],
    resolve: {
      alias: {
        "@": path.resolve(__dirname, "./src"),
      },
    },
    server: {
      port: 5173,
      proxy: {
        "/api": {
          target: "http://localhost:8000",
          changeOrigin: false,
          configure: (proxy) => {
            proxy.on("proxyReq", (proxyReq) => {
              if (!proxyReq.getHeader("X-Vay-User")) {
                proxyReq.setHeader("X-Vay-User", devUser);
              }
            });
          },
        },
      },
    },
    build: {
      outDir: "dist",
      sourcemap: true,
    },
  };
});
