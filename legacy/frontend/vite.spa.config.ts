import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";

// Standalone SPA build of the Procure CRM, bypassing TanStack Start + Cloudflare
// Worker plumbing. Output: dist-spa/{index.html, assets/...} — ready to serve
// from any static host (nginx Docker on Zeabur, etc.).
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  build: {
    outDir: "dist-spa",
    emptyOutDir: true,
    sourcemap: false,
  },
  server: {
    port: 5174,
  },
});
