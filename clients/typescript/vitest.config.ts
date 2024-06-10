import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    mockReset: true,
    coverage: {
      enabled: true,
      include: ["src/**/*.ts"],
      provider: "v8",
      reporter: ["text", "lcov"],
    },
  },
});
