import { defineConfig } from "vitest/config";
import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { fileURLToPath } from "node:url";

// Même origine que l'API en développement : cookies de session et contrôle CSRF sans CORS.
// `changeOrigin: false` conserve l'en-tête Host d'origine (le backend le compare à Origin).
const apiProxy = {
  "/api": { target: process.env.VITE_PROXY_TARGET ?? "http://127.0.0.1:8000", changeOrigin: false },
};

// https://vitejs.dev/config/
export default defineConfig({
  server: {
    host: "::",
    port: 8080,
    proxy: apiProxy,
  },
  preview: {
    proxy: apiProxy,
  },
  plugins: [react(), tailwindcss()],
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    include: ["src/**/*.test.{ts,tsx}"],
    css: false,
  },
  resolve: {
    alias: [
      { find: "@", replacement: fileURLToPath(new URL("./src", import.meta.url)) },
      // pdf.js « legacy » : fonctionne sans les API JavaScript récentes (Map.getOrInsertComputed…)
      // absentes de certains navigateurs encore répandus
      { find: /^pdfjs-dist$/, replacement: "pdfjs-dist/legacy/build/pdf.mjs" },
    ],
  },
});
