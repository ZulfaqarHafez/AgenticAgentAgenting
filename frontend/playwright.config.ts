import path from "node:path";

import { defineConfig } from "@playwright/test";

const frontendRoot = __dirname;
const backendRoot = path.resolve(__dirname, "../backend");

export default defineConfig({
  testDir: "./tests",
  fullyParallel: false,
  reporter: "list",
  timeout: 45_000,
  expect: {
    timeout: 10_000,
  },
  use: {
    baseURL: "http://127.0.0.1:3010",
    headless: true,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },
  webServer: [
    {
      command: "cargo run --release",
      cwd: backendRoot,
      env: { HIVE_HOST: "127.0.0.1", HIVE_PORT: "8010" },
      url: "http://127.0.0.1:8010/health",
      reuseExistingServer: false,
      // The first run compiles the backend, which can take a few minutes.
      timeout: 600_000,
    },
    {
      command:
        "powershell -NoProfile -Command \"$env:NEXT_PUBLIC_API_BASE_URL='http://127.0.0.1:8010'; node .\\node_modules\\next\\dist\\bin\\next build; node .\\node_modules\\next\\dist\\bin\\next start --hostname 127.0.0.1 --port 3010\"",
      cwd: frontendRoot,
      url: "http://127.0.0.1:3010",
      reuseExistingServer: false,
      timeout: 180_000,
    },
  ],
});
