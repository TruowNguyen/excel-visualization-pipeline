import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './benchmarks',
  workers: 1,
  timeout: 180_000,
  reporter: 'line',
  use: {
    baseURL: process.env.EVP_PERF_BASE_URL || 'http://127.0.0.1:8001',
    channel: 'chrome',
    headless: true,
    viewport: { width: 1440, height: 900 },
  },
});
