import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.js"],
    css: false,
    include: ["src/**/*.{test,spec}.{js,jsx}"],
    coverage: {
      provider: "v8",
      reporter: ["text", "html", "lcov"],
      include: ["src/**/*.{js,jsx}"],
      exclude: [
        "src/main.jsx",
        // App.jsx, pages/ 通过 Playwright E2E 覆盖；store/ 与 hooks/ 与 components/ 是
        // Vitest 的覆盖范围。
        "src/App.jsx",
        "src/pages/**",
        "src/styles/**",
        "src/test/**",
        "**/*.test.{js,jsx}",
        "**/__tests__/**",
      ],
      thresholds: {
        statements: 80,
        branches: 70,
        functions: 80,
        lines: 80,
      },
    },
  },
});
