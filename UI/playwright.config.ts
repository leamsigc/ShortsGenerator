import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  reporter: 'html',
  timeout: 300_000,
  expect: { timeout: 15_000 },
  use: {
    baseURL: 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: [
    {
      command: 'npm run dev -- --port 3000 --host 0.0.0.0',
      url: 'http://localhost:3000',
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
      cwd: '/home/leamsigc/Documents/learn/ShortsGenerator/UI',
      env: { ...process.env, NUXT_PORT: '3000' },
    },
    {
      command: 'python main.py',
      url: 'http://localhost:8080/api/clipper/projects',
      reuseExistingServer: !process.env.CI,
      timeout: 30_000,
      cwd: '/home/leamsigc/Documents/learn/ShortsGenerator/Backend',
    },
  ],
});
