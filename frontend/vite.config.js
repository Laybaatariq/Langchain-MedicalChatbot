import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The browser only talks to this dev server (same origin). Requests to /chat and
// /health are forwarded by Vite to the FastAPI backend running on port 8000 in the
// same machine, so there is no CORS setup and the backend port can stay private
// (this is what makes it work in GitHub Codespaces).
export default defineConfig({
  plugins: [react()],
  server: {
    host: true, // listen on all interfaces so Codespaces can forward the port
    port: 5173,
    strictPort: true,
    allowedHosts: [".app.github.dev"], // Codespaces forwarded-port domains
    proxy: {
      "/chat": { target: "http://127.0.0.1:8000", changeOrigin: true },
      "/health": { target: "http://127.0.0.1:8000", changeOrigin: true },
    },
  },
});
