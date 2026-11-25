import { defineConfig } from "vitest/config";

// The handler is a plain fetch function: tests call it directly with fake KV, fake rate limiters
// and a stubbed global fetch standing in for the Courthouse.
export default defineConfig({
  test: { include: ["test/**/*.test.ts"], environment: "node" },
});
