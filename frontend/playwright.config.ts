import path from "node:path";

import { defineConfig } from "@playwright/test";

const frontendRoot = __dirname;
const backendRoot = path.resolve(__dirname, "../backend");
const backendPython = path
  .resolve(backendRoot, ".venv", "Scripts", "python.exe")
  .replace(/\\/g, "/");

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
      command: `powershell -NoProfile -Command "& '${backendPython}' -m uvicorn app.main:app --host 127.0.0.1 --port 8010"`,
      cwd: backendRoot,
      url: "http://127.0.0.1:8010/health",
      reuseExistingServer: false,
      timeout: 120_000,
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
