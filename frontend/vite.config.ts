import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Dev: the FastAPI backend runs on :8000; prod: FastAPI serves dist/ itself.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { "/api": "http://127.0.0.1:8000", "/healthz": "http://127.0.0.1:8000" },
  },
});
