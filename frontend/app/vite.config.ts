import path from "path"
import react from "@vitejs/plugin-react"
import { defineConfig } from "vite"
import { inspectAttr } from 'kimi-plugin-inspect-react'

// https://vite.dev/config/
export default defineConfig({
  base: './',
  plugins: [inspectAttr(), react()],
  server: {
    host: "0.0.0.0",
    port: 5173,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8001",
        changeOrigin: true,
        configure: (proxy) => {
          // Disable buffering for SSE responses
          proxy.on("proxyRes", (proxyRes, _req, _res) => {
            if (proxyRes.headers["content-type"]?.includes("text/event-stream")) {
              // Ensure no compression/buffering on the proxy side
              proxyRes.headers["cache-control"] = "no-cache";
              proxyRes.headers["x-accel-buffering"] = "no";
            }
          });
        },
      },
    },
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
});
