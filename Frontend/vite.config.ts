import { defineConfig } from "vite";
import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react-swc";
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
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
});
