import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// El backend sirve el build desde frontend/dist. base relativo para servirlo
// correctamente bajo cualquier ruta. En dev, proxy del WebSocket al backend.
export default defineConfig({
  plugins: [react()],
  base: "./",
  server: {
    port: 5173,
    proxy: {
      "/ws": { target: "ws://127.0.0.1:8000", ws: true },
      "/api": { target: "http://127.0.0.1:8000", changeOrigin: true },
    },
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
  },
});
