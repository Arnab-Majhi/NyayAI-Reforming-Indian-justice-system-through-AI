import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./tests", fullyParallel: false, workers: 1,
  timeout: 60000, use: { baseURL: "http://localhost:3000", trace: "retain-on-failure", channel: process.env.PLAYWRIGHT_CHANNEL || undefined },
  reporter: "list",
  webServer: [
    { command: "..\\backend\\.venv\\Scripts\\python.exe -m uvicorn app.main:app --app-dir ..\\backend --host 127.0.0.1 --port 8000", url: "http://127.0.0.1:8000/api/health", reuseExistingServer: !process.env.CI, timeout: 120000 },
    { command: "npm run start", url: "http://localhost:3000", reuseExistingServer: !process.env.CI, timeout: 120000 },
  ],
});