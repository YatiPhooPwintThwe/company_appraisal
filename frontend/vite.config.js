import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000, // frontend port
    proxy: {
      // no more /api prefix
      "/": {
        target: "http://127.0.0.1:5000",
        changeOrigin: true,
      },
      "/statics": {
        target: "http://127.0.0.1:5000",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/statics/, "/statics"),
      },
    },
  },
});
