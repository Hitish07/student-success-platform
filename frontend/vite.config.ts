import react from "@vitejs/plugin-react";
import { loadEnv } from "vite";
import { defineConfig } from "vitest/config";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, ".", "");
  const apiTarget = env.VITE_PROXY_TARGET ?? "http://127.0.0.1:8000";

  return {
    plugins: [react()],
    server: {
      proxy: Object.fromEntries(
        ["/auth", "/portals", "/student", "/faculty", "/analytics", "/principal", "/health"].map((path) => [
          path,
          { target: apiTarget, changeOrigin: true },
        ]),
      ),
    },
    test: {
      environment: "jsdom",
      setupFiles: ["./src/test/setup.ts"],
    },
  };
});
